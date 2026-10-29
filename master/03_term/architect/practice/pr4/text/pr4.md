# Практическая работа №4. Архитектура, управляемая моделью (MDA): CIM → PIM → PSM

**Цель работы:** выполнить раздельное моделирование CIM → PIM → PSM, задать правила трансформации PIM → PSM и сгенерировать артефакты из модели.

Для вертикального среза взят сценарий платформы данных из практик №1–3: **загрузка пакета курсов валют** от внешнего источника и **запрос курса на дату**. По модели сгенерированы миграция БД, контракт OpenAPI, DTO и каркас роутера; всё это проверено 33 автоматическими тестами на реальном PostgreSQL 16. Из дополнительных заданий выполнено «OCL-инварианты и их проверка в тестах» (раздел 8.1).

Вместе с отчётом идёт архив проекта `pw4_project.zip` (модель, генератор, `gen/`, тесты, README).

---

## 1. Система и вертикальный срез

Платформа данных из практики №1 принимает данные из источников и отдаёт единые метрики аналитикам. В практике №2 приём пакетных файлов (курсы валют, тарифы) выделен в элемент Э1 «Слой приёма данных» (ФТ-1), а в практике №3 для него выбран Factory Method для коннекторов. Здесь рассматривается один вертикальный срез через этот элемент:

| Сценарий | Суть | Связь с предыдущими практиками |
| --- | --- | --- |
| С1. Загрузка пакета курсов | Источник передаёт пакет курсов; платформа проверяет его и принимает целиком или отклоняет целиком; повторная передача не создаёт дублей | ФТ-1 и КА-1 из ПР №2 («подтверждённое событие не теряется»), валидация из ФТ-1 |
| С2. Запрос курса | Потребитель получает курс валютной пары на дату из принятых пакетов | Цель ПР №1: единая проверяемая версия бизнес-метрик |

---

## 2. CIM — модель предметной области (без техники)

### 2.1. Акторы, цели, ограничения, риски

| Актор | Цель |
| --- | --- |
| Источник курсов (внешний провайдер или загрузчик файлов) | Передать курсы так, чтобы повторная отправка при сбое связи не портила данные |
| Аналитик или BI-слой | Получать одну и ту же проверенную версию курса на дату |
| Дата-инженер (оператор платформы) | Видеть, какой пакет принят, а какой отклонён и почему |

| Ограничения (из ПР №1–2) | Риски |
| --- | --- |
| Платформа работает в закрытом контуре компании | Один и тот же пакет загружен дважды — дубли курсов искажают отчёты |
| Только готовые open-source компоненты, MVP за 4 месяца | Часть пакета принята, часть нет — курсы противоречат друг другу |
| Высокая доступность приёма данных (КА-1 из ПР №2) | Неверные значения (отрицательный курс, неверный код валюты) попадают в витрины |
| | Разные команды берут курсы из разных мест — «теневая отчётность» |

### 2.2. Диаграмма контекста (C4, уровень 0)

```mermaid
flowchart LR
    SRC["Источник курсов<br/>внешний провайдер,<br/>загрузчик файлов"]
    SYS["Платформа данных<br/>подсистема приёма курсов валют"]
    AN["Аналитик<br/>BI-слой"]
    OP["Дата-инженер<br/>оператор платформы"]

    SRC -->|"передаёт пакеты курсов"| SYS
    AN -->|"запрашивает курс на дату"| SYS
    OP -->|"смотрит статус пакетов и причины отказов"| SYS
```

### 2.3. Варианты использования

```mermaid
flowchart LR
    SRC(["Источник курсов"])
    AN(["Аналитик, BI"])
    OP(["Дата-инженер"])

    UC1(["UC-1. Загрузить пакет курсов"])
    UC2(["UC-2. Получить курс на дату"])
    UC3(["UC-3. Узнать причины отказа пакета"])

    SRC --- UC1
    AN --- UC2
    OP --- UC3
    UC3 -.->|"использует результат"| UC1
```

В срез входят UC-1 и UC-2; UC-3 показан для полноты контекста.

### 2.4. Сценарии (Given–When–Then)

**С1. Загрузка пакета.**

- *Given* источник «cbr» передаёт пакет «2026-10-29» с курсами USD/RUB и EUR/RUB, и пакета с таким ключом у этого источника ещё нет,
  *When* платформа получает пакет,
  *Then* все строки проверены, пакет принят целиком, курсы доступны для запроса.
- *Given* пакет «2026-10-29» уже принят, *When* источник из-за сбоя связи передаёт тот же пакет повторно, *Then* данные не меняются, источник получает прежний результат.
- *Given* пакет «2026-10-29» принят, *When* приходит пакет с тем же ключом, но другим содержимым, *Then* платформа сообщает о конфликте и ничего не меняет.
- *Given* в пакете есть строка с отрицательным курсом, *When* платформа проверяет пакет, *Then* пакет отклонён целиком, ни один курс не сохранён, причины отказа записаны.

**С2. Запрос курса.**

- *Given* принято несколько пакетов с курсом USD/RUB на 2026-10-29, *When* аналитик запрашивает курс на эту дату, *Then* он получает значение из последнего принятого пакета; отклонённые пакеты не учитываются.
- *Given* курса на дату нет, *When* аналитик его запрашивает, *Then* платформа сообщает, что курса нет.

---

## 3. PIM — платформенно-независимая модель

Полная модель — в файле `model/pim.yaml`. В ней нет SQL-типов, HTTP-маршрутов, названий СУБД и брокеров: только сущности, инварианты и операции предметной области.

### 3.1. Диаграмма классов

```mermaid
classDiagram
    class Source {
        name : Text
    }
    class IngestionBatch {
        batchKey : Text
        contentDigest : Text
        status : BatchStatus
        rowCount : Integer
        receivedAt : Timestamp
    }
    class ExchangeRate {
        baseCurrency : CurrencyCode
        quoteCurrency : CurrencyCode
        rateDate : Date
        rate : Decimal
    }
    class ValidationIssue {
        rowNumber : Integer
        reason : Text
    }
    class BatchStatus {
        <<enumeration>>
        accepted
        rejected
    }
    Source "1" <-- "0..*" IngestionBatch : от источника
    IngestionBatch "1" <-- "0..*" ExchangeRate : содержит
    IngestionBatch "1" <-- "0..*" ValidationIssue : причины отказа
    IngestionBatch ..> BatchStatus
```

### 3.2. Диаграмма последовательностей: загрузка пакета (С1)

```mermaid
sequenceDiagram
    actor S as Источник курсов
    participant I as Сервис приёма
    participant R as Реестр пакетов
    participant E as Реестр курсов

    S->>I: передать пакет (источник, ключ, строки курсов)
    I->>R: найти пакет по источнику и ключу
    alt пакет с таким ключом уже есть
        R-->>I: прежний пакет
        alt содержимое совпадает
            I-->>S: прежний результат (повтор)
        else содержимое отличается
            I-->>S: конфликт
        end
    else пакета нет
        I->>I: проверить строки
        alt все строки корректны
            I->>R: зарегистрировать пакет со статусом «принят»
            I->>E: сохранить курсы пакета
        else есть ошибки
            I->>R: зарегистрировать пакет со статусом «отклонён» и причины
        end
        I-->>S: результат (статус, причины)
    end
```

### 3.3. Инварианты домена

| № | Сущность | Инвариант |
| --- | --- | --- |
| INV-1 | IngestionBatch | У одного источника не бывает двух пакетов с одним ключом |
| INV-2 | ExchangeRate | Курс строго положителен |
| INV-3 | ExchangeRate | Базовая и котируемая валюты различаются |
| INV-4 | ExchangeRate | В пакете не больше одного курса на пару валют и дату |
| INV-5 | CurrencyCode | Код валюты состоит ровно из трёх заглавных латинских букв |
| INV-6 | IngestionBatch | Пакет принимается целиком или отклоняется целиком: у отклонённого пакета нет курсов, но есть причины отказа |
| INV-7 | IngestionBatch | Повторная передача с тем же ключом и содержимым не меняет данные и возвращает прежний результат; с другим содержимым — конфликт |
| INV-8 | ExchangeRate | Курс задаётся не более чем с 8 знаками после запятой и строго меньше 10^10; значения вне границ отклоняются, а не округляются |

Инварианты, выраженные на OCL (записаны в `model/pim.yaml`):

```
context ExchangeRate inv INV2: self.rate > 0
context ExchangeRate inv INV3: self.baseCurrency <> self.quoteCurrency
context CurrencyCode inv INV5: self.matches('[A-Z]{3}')
context IngestionBatch inv INV1: IngestionBatch.allInstances()->isUnique(b | Tuple{s = b.source, k = b.batchKey})
context ExchangeRate inv INV4: ExchangeRate.allInstances()->isUnique(r | Tuple{b = r.batch, c1 = r.baseCurrency, c2 = r.quoteCurrency, d = r.rateDate})
context IngestionBatch inv INV6: self.status = BatchStatus::rejected implies self.rates->isEmpty()
```

INV-7 (идемпотентность во времени) и INV-8 (точность числа) на OCL не записаны: первое описывает поведение между вызовами, второе в модели задано текстом.

### 3.4. Операции PIM

| Операция | Вид | Вход | Результат | Исходы |
| --- | --- | --- | --- | --- |
| submitBatch | команда, идемпотентная по ключу (источник, batchKey) | источник, ключ пакета, список строк курсов | статус, число строк, причины отказа | создан, повтор, конфликт содержимого |
| getRate | запрос | базовая валюта, котируемая валюта, дата | курс и источник | найден, не найден |

---

## 4. Целевая платформа (PSM)

**Платформа: Python 3.12 + FastAPI + PostgreSQL 16.** Выбор объясняется практикой: команда состоит из дата-инженеров, Python и PostgreSQL — стандартный стек для них; всё это open-source (ограничение ОГР-3 из ПР №2).

| Качество | Цель | Как обеспечивается / проверяется |
| --- | --- | --- |
| Корректность данных | 0 нарушений инвариантов INV-1…INV-7 | Ограничения БД и тесты (раздел 8) |
| Идемпотентность | Повтор не меняет данные, в том числе при одновременных запросах | Уникальный индекс + `ON CONFLICT` (ADR-1); тест на 8 параллельных запросов |
| Время ответа | p95 ≤ 300 мс на запрос курса и на пакет до 1000 строк (допущение) | Индекс `ix_exchange_rate_lookup`; **в песочнице не измерялось** — проверить нагрузочным тестом (задача 8.2 ПР №1) |
| Доступность | 99,999% на пути приёма (КА-1 из ПР №2) | Два экземпляра API и PostgreSQL с синхронной репликой (раздел 6.3); достижимость зависит от автоматического переключения БД |

---

## 5. Правила трансформации PIM → PSM (вариант A: таблица соответствий)

Правила реализованы в `generator/generate.py`; номера совпадают с комментариями в коде.

| № | Элемент PIM | Элемент PSM | Правило |
| --- | --- | --- | --- |
| R1 | Базовые типы | Типы PostgreSQL | Text → `TEXT`, Integer → `INTEGER`, Date → `DATE`, Timestamp → `TIMESTAMPTZ`, Decimal → `NUMERIC(18,8)`, CurrencyCode → `TEXT` (длину и формат держит `CHECK`, см. раздел 8.1) |
| R2 | Базовые типы | Типы Python (DTO) | Text → `str`, Integer → `int`, Date → `date`, Decimal → `Decimal` |
| R3 | Базовые типы | Схемы OpenAPI | Date → `string/date`, Decimal → `string/decimal` (без потери точности) |
| R4 | Перечисление | Колонка + ограничение | `TEXT` + `CHECK (col IN (...))`; в DTO — `Literal[...]` |
| R5 | Сущность и атрибут | Таблица и колонка | Имя в `snake_case`, суррогатный ключ `id`, все колонки `NOT NULL` |
| R6 | Атрибут `auto: creationMoment` | Значение по умолчанию | `DEFAULT now()` |
| R7 | Ассоциация с кратностью 1 | Внешний ключ | `<имя>_id BIGINT NOT NULL REFERENCES ...` |
| R8 | Инвариант типа (INV-5) | Ограничение `CHECK` | `col ~ '^[A-Z]{3}$'`; то же как `pattern` в параметрах OpenAPI |
| R9 | Инвариант сущности (INV-1…INV-4) | `UNIQUE` или `CHECK` | Имя ограничения содержит номер инварианта: `uq_ingestion_batch_inv1` |
| R10 | Внешний ключ | Индекс | Индекс на каждый внешний ключ |
| R11 | Поиск в операции `getRate` | Составной индекс | `(base_currency, quote_currency, rate_date)` |
| R12 | Идемпотентная команда | `PUT`, ключ в пути | Параметры ключа идемпотентности идут в путь, остальное — в тело; запрос → `GET` |
| R13 | Структура | DTO и схема OpenAPI | Поля в `snake_case`, массив → `list[...]` / `array` |
| R14 | Операция | Контракт сервиса и роутер | `Protocol BatchService` + каркас обработчиков FastAPI |
| R15 | Инвариант `behavior` (INV-6, INV-7, INV-8) | Тест и проверка в сервисе | В схеме БД выразить нельзя полностью — проверяется тестами |
| R16 | OCL-инвариант | Исполняемый предикат Python | Подмножество OCL переводится в `gen/invariants.py` (раздел 8.1) |

### Политики

| Политика | Решение |
| --- | --- |
| Транзакции | Один пакет — одна транзакция: регистрация пакета и вставка курсов (или причин отказа) фиксируются вместе |
| Идемпотентность | Ключ `(источник, batch_key)` в пути + уникальный индекс (INV-1) + отпечаток содержимого `content_digest` (ADR-1) |
| Ошибки | 201 — создан, 200 — повтор, 409 — тот же ключ с другим содержимым, 422 — запрос не соответствует схеме; ошибки данных внутри пакета не дают 5xx — пакет получает статус `rejected` и список причин |
| Повторы клиента | Любая ошибка 5xx или обрыв связи безопасно повторяются тем же ключом |

---

## 6. PSM — платформенно-зависимая модель

### 6.1. Схема БД (сгенерирована: `gen/migrations/001_init.sql`)

```sql
-- AUTO-GENERATED из model/pim.yaml (generator/generate.py). Не править вручную.
BEGIN;

CREATE TABLE source (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    CONSTRAINT uq_source_name UNIQUE (name)
);

CREATE TABLE ingestion_batch (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_key TEXT NOT NULL,
    content_digest TEXT NOT NULL,
    status TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_id BIGINT NOT NULL REFERENCES source(id),
    CONSTRAINT ck_ingestion_batch_status_enum CHECK (status IN ('accepted', 'rejected')),
    CONSTRAINT uq_ingestion_batch_inv1 UNIQUE (source_id, batch_key)
);

CREATE TABLE exchange_rate (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate_date DATE NOT NULL,
    rate NUMERIC(18,8) NOT NULL,
    batch_id BIGINT NOT NULL REFERENCES ingestion_batch(id),
    CONSTRAINT ck_exchange_rate_inv5_base_currency CHECK (base_currency ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_exchange_rate_inv5_quote_currency CHECK (quote_currency ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_exchange_rate_inv2 CHECK (rate > 0),
    CONSTRAINT ck_exchange_rate_inv3 CHECK (base_currency <> quote_currency),
    CONSTRAINT uq_exchange_rate_inv4 UNIQUE (batch_id, base_currency, quote_currency, rate_date)
);

CREATE TABLE validation_issue (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    row_number INTEGER NOT NULL,
    reason TEXT NOT NULL,
    batch_id BIGINT NOT NULL REFERENCES ingestion_batch(id)
);

CREATE INDEX ix_ingestion_batch_source_id ON ingestion_batch (source_id);
CREATE INDEX ix_exchange_rate_batch_id ON exchange_rate (batch_id);
CREATE INDEX ix_validation_issue_batch_id ON validation_issue (batch_id);
CREATE INDEX ix_exchange_rate_lookup ON exchange_rate (base_currency, quote_currency, rate_date);

COMMIT;
```

### 6.2. Контракт API (сгенерирован: `gen/openapi.yaml`)

```yaml
openapi: 3.0.3
info:
  title: Currency Rates Ingestion API
  version: 1.0.0
  description: AUTO-GENERATED из model/pim.yaml (generator/generate.py).
paths:
  /v1/sources/{source}/batches/{batch_key}:
    put:
      operationId: submitBatch
      summary: Источник передаёт пакет курсов.
      parameters:
      - name: source
        in: path
        required: true
        schema:
          type: string
      - name: batch_key
        in: path
        required: true
        schema:
          type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SubmitBatchRequest'
      responses:
        '201':
          description: Пакет принят впервые
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BatchResult'
        '200':
          description: 'Повтор: тот же ключ и то же содержимое, данные не изменены'
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BatchResult'
        '409':
          description: Тот же ключ, но другое содержимое
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '422':
          description: Тело или параметры не соответствуют схеме
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
  /v1/rates/{base_currency}/{quote_currency}:
    get:
      operationId: getRate
      summary: Потребитель запрашивает курс на дату.
      parameters:
      - name: base_currency
        in: path
        required: true
        schema:
          type: string
          pattern: ^[A-Z]{3}$
      - name: quote_currency
        in: path
        required: true
        schema:
          type: string
          pattern: ^[A-Z]{3}$
      - name: rate_date
        in: query
        required: true
        schema:
          type: string
          format: date
      responses:
        '200':
          description: Курс найден
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Rate'
        '404':
          description: Курса на эту дату нет
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '422':
          description: Параметры не соответствуют схеме
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
components:
  schemas:
    RateRow:
      type: object
      required:
      - base_currency
      - quote_currency
      - rate_date
      - rate
      properties:
        base_currency:
          type: string
        quote_currency:
          type: string
        rate_date:
          type: string
          format: date
        rate:
          type: string
          format: decimal
    Issue:
      type: object
      required:
      - row_number
      - reason
      properties:
        row_number:
          type: integer
        reason:
          type: string
    BatchResult:
      type: object
      required:
      - batch_key
      - status
      - row_count
      - issues
      properties:
        batch_key:
          type: string
        status:
          type: string
          enum:
          - accepted
          - rejected
        row_count:
          type: integer
        issues:
          type: array
          items:
            $ref: '#/components/schemas/Issue'
    Rate:
      type: object
      required:
      - base_currency
      - quote_currency
      - rate_date
      - rate
      - source
      properties:
        base_currency:
          type: string
        quote_currency:
          type: string
        rate_date:
          type: string
          format: date
        rate:
          type: string
          format: decimal
        source:
          type: string
    SubmitBatchRequest:
      type: object
      required:
      - rates
      properties:
        rates:
          type: array
          items:
            $ref: '#/components/schemas/RateRow'
    Error:
      type: object
      properties:
        detail:
          description: Описание ошибки
```

DTO (`gen/dto.py`):

```python
# AUTO-GENERATED из model/pim.yaml (generator/generate.py). Не править вручную.
from __future__ import annotations

from datetime import date, datetime  # noqa: F401
from decimal import Decimal  # noqa: F401
from typing import Literal  # noqa: F401

from pydantic import BaseModel


class RateRow(BaseModel):
    base_currency: str
    quote_currency: str
    rate_date: date
    rate: Decimal


class Issue(BaseModel):
    row_number: int
    reason: str


class BatchResult(BaseModel):
    batch_key: str
    status: Literal['accepted', 'rejected']
    row_count: int
    issues: list[Issue]


class Rate(BaseModel):
    base_currency: str
    quote_currency: str
    rate_date: date
    rate: Decimal
    source: str


class SubmitBatchRequest(BaseModel):
    rates: list[RateRow]
```

### 6.3. Диаграмма развёртывания

```mermaid
flowchart TB
    SRC["Источник курсов<br/>загрузчик пакетов"]
    BI["Аналитики, BI"]
    LB["Балансировщик нагрузки"]

    subgraph ZA["Зона отказа A"]
        API1["Узел 1: API<br/>Python, FastAPI"]
        PG1[("PostgreSQL<br/>основной узел")]
    end
    subgraph ZB["Зона отказа B"]
        API2["Узел 2: API<br/>Python, FastAPI"]
        PG2[("PostgreSQL<br/>реплика, синхронная")]
    end

    SRC -->|"HTTPS, PUT пакета"| LB
    BI -->|"HTTPS, GET курса"| LB
    LB --> API1
    LB --> API2
    API1 --> PG1
    API2 --> PG1
    PG1 ==>|"репликация"| PG2
    API1 -.->|"при отказе основного узла"| PG2
    API2 -.->|"при отказе основного узла"| PG2
```

Границы отказов: потеря зоны A оставляет работающими узел API 2 и реплику БД; она становится основной после автоматического переключения (нужен менеджер переключения, например Patroni — выбор уточняется на итерации хранилища). Сервис API не хранит состояние, поэтому два экземпляра равноправны, а идемпотентность держится на уникальном индексе в БД, а не на памяти приложения.

---

## 7. Генерация артефактов

| Артефакт | Файл | Что сгенерировано |
| --- | --- | --- |
| Миграция БД | `gen/migrations/001_init.sql` | 4 таблицы, 6 именованных ограничений-инвариантов, 4 индекса |
| Контракт API | `gen/openapi.yaml` | 2 операции, 6 схем |
| Исполняемые инварианты | `gen/invariants.py` | Предикаты из OCL для INV-2, INV-3, INV-5 и описание ключей INV-1, INV-4 |
| DTO | `gen/dto.py` | Модели Pydantic |
| Каркас контроллеров | `gen/api.py` | Контракт `BatchService` и роутер FastAPI |

**Команда запуска** (из корня проекта):

```bash
python generator/generate.py
```

Вывод генератора:

```
generated gen/migrations/001_init.sql
generated gen/openapi.yaml
generated gen/dto.py
generated gen/api.py
generated gen/invariants.py
generated gen/__init__.py
```

Вручную написаны только бизнес-логика и работа с БД (`app/service.py`): проверка строк, отпечаток содержимого, транзакция и запросы. Контракт, схема и DTO правятся только через модель `model/pim.yaml`.

---

## 8. Проверка соответствия

**Команда:**

```bash
pytest -v
```

**Результат (реальный запуск, PostgreSQL 16):**

```
test_scalar_invariants_match_database PASSED
test_each_scalar_invariant_is_exercised PASSED
test_unique_invariants_match_database[INV-1] PASSED
test_unique_invariants_match_database[INV-4] PASSED
test_every_invariant_has_named_constraint PASSED
test_inv1_batch_key_unique_per_source PASSED
test_rate_constraints[USD-RUB--1-CheckViolation] PASSED
test_rate_constraints[USD-RUB-0-CheckViolation] PASSED
test_rate_constraints[USD-USD-1-CheckViolation] PASSED
test_rate_constraints[usd-RUB-1-CheckViolation] PASSED
test_rate_constraints[US-RUB-1-CheckViolation] PASSED
test_inv4_duplicate_pair_date_in_batch PASSED
test_scenario_submit_then_get_rate PASSED
test_inv7_repeat_is_idempotent PASSED
test_inv7_same_key_other_content_is_conflict PASSED
test_same_key_different_source_is_allowed PASSED
test_inv6_invalid_row_rejects_whole_batch PASSED
test_duplicate_row_in_batch_rejected PASSED
test_latest_accepted_batch_wins_and_rejected_is_ignored PASSED
test_malformed_requests_422[/v1/rates/usd/RUB-params0] PASSED
test_malformed_requests_422[/v1/rates/USD/RUB-params1] PASSED
test_malformed_requests_422[/v1/rates/USD/RUB-params2] PASSED
test_malformed_body_422 PASSED
test_openapi_is_valid_and_matches_application PASSED
test_generation_is_reproducible PASSED
test_concurrent_submissions_create_exactly_one_batch PASSED
test_inv8_out_of_range_or_precision_is_rejected_not_500[0.000000001] PASSED
test_inv8_out_of_range_or_precision_is_rejected_not_500[0.123456789] PASSED
test_inv8_out_of_range_or_precision_is_rejected_not_500[10000000000] PASSED
test_inv8_out_of_range_or_precision_is_rejected_not_500[1E+12] PASSED
test_inv8_boundary_values_are_accepted[0.12345678] PASSED
test_inv8_boundary_values_are_accepted[0.1234567800] PASSED
test_inv8_boundary_values_are_accepted[9999999999.99999999] PASSED
======================== 33 passed, 1 warning in 4.29s =========================
```

Что проверено:

| Группа | Что проверяет |
| --- | --- |
| Ограничения БД | Каждый инвариант INV-1…INV-5 существует в БД как именованное ограничение и срабатывает на неверных данных |
| Сценарии API | С1 и С2 целиком: приём, повтор, конфликт, отклонение пакета, выбор последнего принятого пакета |
| Точность курса | INV-8: слишком малые, слишком большие и слишком точные значения дают отклонённый пакет, а не ошибку 500 |
| Устойчивость | 8 одновременных одинаковых запросов дают ровно один созданный пакет и 7 повторов |
| Контракт | `gen/openapi.yaml` проходит валидацию и совпадает с маршрутами работающего приложения |
| Воспроизводимость | Повторная генерация даёт побайтово тот же результат |

Что не проверено: производительность (p95), отказоустойчивость развёртывания и репликация — они требуют стенда с несколькими узлами.

### 8.1. Дополнительное задание: OCL-инварианты и их проверка в тестах

OCL-выражения записаны в модели рядом с текстом инварианта. Генератор (правило R16) переводит подмножество OCL в исполняемые предикаты `gen/invariants.py`, а `tests/test_ocl.py` сверяет их с поведением реальной БД: **строка принимается базой тогда и только тогда, когда выполнены все инварианты модели**.

| Инвариант | Как проверяется |
| --- | --- |
| INV-2, INV-3, INV-5 | Предикаты, сгенерированные из OCL; 400 строк из перебора 10 значений кода валюты × 10 × 6 значений курса (порядок задан фиксированным seed), включая коды `usd`, `US`, `USD ` (с пробелом) и `USD` с переводом строки. Отдельный тест проверяет, что для каждого инварианта есть и нарушающие, и подходящие строки |
| INV-1, INV-4 | Ключи уникальности, сгенерированные из `isUnique`; по 300 случайных вставок с повторяющимися ключами, ожидание — «ключ ещё не встречался» |
| INV-6 | OCL записан, но содержит импликацию и коллекции — автоматически не переводится; проверяется тестами API |
| INV-7, INV-8 | В OCL не записаны; проверяются тестами API (`test_inv7_*`, `test_inv8_*`) |

**Что этот способ нашёл** (до исправления модель и реализация расходились):

1. PostgreSQL молча принимал код валюты `'USD '` (с пробелом на конце) в колонке `CHAR(3)`, хотя по INV-5 это не код. Правило R1 изменено: код хранится как `TEXT`, а длину и формат контролирует `CHECK`.
2. Курс `0.000000001` приводил к ошибке 500: база округляла его до нуля и срабатывала проверка INV-2, а сервис эту ситуацию не ловил; курс с 9 знаками после запятой округлялся молча. В модель добавлен INV-8, сервис отклоняет такие значения с понятной причиной.

**Ограничение.** Переводчик OCL понимает только небольшое подмножество (обращение к атрибутам, `matches`, сравнения, `and`, `or`, `not`); это не полноценный OCL-движок вроде Eclipse OCL.

---

## 9. Архитектурные решения (ADR)

### ADR-1. Идемпотентность через ключ и уникальный индекс

- **Контекст.** Источник может повторить передачу после обрыва связи; API работает двумя экземплярами; дубли курсов искажают отчёты.
- **Варианты.**
  1. Хранить обработанные ключи в памяти или кэше приложения.
  2. Отдельная таблица обработанных ключей с проверкой «есть ли ключ» перед вставкой.
  3. Ключ пакета в пути + уникальный индекс на `(источник, ключ)` + вставка `ON CONFLICT DO NOTHING` + отпечаток содержимого.
- **Решение.** Вариант 3.
- **Последствия.**
  - (+) Работает при нескольких экземплярах и после перезапуска; гонка запросов решается самой БД (тест на 8 параллельных запросов).
  - (+) Отпечаток содержимого отличает безопасный повтор от конфликта.
  - (−) Источник обязан формировать стабильный ключ пакета.
  - (−) Ключи нельзя удалять, пока живут пакеты; нужна политика хранения.
  - Вариант 1 отвергнут: теряется при перезапуске и не работает между экземплярами. Вариант 2 отвергнут: между проверкой и вставкой возможна гонка.

### ADR-2. Курсы хранятся неизменяемыми по пакетам

- **Контекст.** Нужны проверяемая история и возможность понять, из какого пакета взят курс (цель ПР №1 — единая проверяемая версия метрик).
- **Варианты.**
  1. Одна строка на пару и дату, обновляется на месте (UPSERT).
  2. Курсы хранятся в составе пакета и не меняются; актуальным считается курс из последнего принятого пакета.
- **Решение.** Вариант 2.
- **Последствия.**
  - (+) Полная история, аудит и воспроизводимость отчётов; отклонённые пакеты не влияют на данные.
  - (−) Запрос курса требует соединения таблиц и сортировки; нужен индекс `ix_exchange_rate_lookup`.
  - (−) Объём данных растёт; нужна политика архивации (сроки хранения из ПР №1).

---

## 10. Трассируемость

| Требование | Элемент PIM | Элемент PSM | Артефакт и тест |
| --- | --- | --- | --- |
| ФТ-1. Приём пакетных файлов курсов | Операция submitBatch; IngestionBatch, ExchangeRate | `PUT /v1/sources/{source}/batches/{batch_key}`; таблицы `ingestion_batch`, `exchange_rate` | `gen/openapi.yaml`, `gen/api.py`; `test_scenario_submit_then_get_rate` |
| ФТ-1. Валидация входящих данных | INV-2, INV-3, INV-5; ValidationIssue | Ограничения `ck_exchange_rate_inv2/3/5`; таблица `validation_issue` | `test_rate_constraints`, `test_inv6_invalid_row_rejects_whole_batch` |
| Приём без дублей при повторе (КА-1) | INV-1, INV-7 | `uq_ingestion_batch_inv1`; `content_digest`; `ON CONFLICT` | `test_inv1_batch_key_unique_per_source`, `test_inv7_repeat_is_idempotent`, `test_inv7_same_key_other_content_is_conflict`, `test_concurrent_submissions_create_exactly_one_batch` |
| Курс только допустимой точности и величины (INV-8) | INV-8 | Проверка в `validate()`; тип `NUMERIC(18,8)` | `test_inv8_out_of_range_or_precision_is_rejected_not_500`, `test_inv8_boundary_values_are_accepted` |
| Инварианты модели совпадают с БД | INV-1…INV-5 в OCL | Ограничения БД; `gen/invariants.py` | `test_scalar_invariants_match_database`, `test_unique_invariants_match_database` |
| Пакет целиком или никак | INV-6 | Одна транзакция на пакет; статус `rejected` | `test_inv6_invalid_row_rejects_whole_batch`, `test_duplicate_row_in_batch_rejected` |
| В пакете нет дублей пары валют и даты | INV-4 | `uq_exchange_rate_inv4` | `test_inv4_duplicate_pair_date_in_batch` |
| Единая проверяемая версия метрик (цель ПР №1) | Операция getRate; правило «последний принятый пакет» | `GET /v1/rates/{base}/{quote}`; индекс `ix_exchange_rate_lookup`; ADR-2 | `test_latest_accepted_batch_wins_and_rejected_is_ignored` |
| Контракт соответствует реализации | Операции PIM | `gen/openapi.yaml` и маршруты FastAPI | `test_openapi_is_valid_and_matches_application` |
| Воспроизводимость генерации | Вся модель | Детерминированный генератор | `test_generation_is_reproducible` |
| Высокая доступность (КА-1) | — | Диаграмма развёртывания, раздел 6.3 | Не проверено в песочнице |

---

## 11. Как воспроизвести

Подробно — в `README.md` внутри архива. Кратко:

```bash
pip install -r requirements.txt
createdb pw4                      # PostgreSQL 16, пользователь pw4 с паролем pw4
python generator/generate.py      # генерация в gen/
pytest -v                         # применяет миграцию к чистой схеме и запускает проверки
uvicorn app.main:app              # запуск API (нужна база с применённой миграцией)
```

Строка подключения задаётся переменной `PW4_DSN` (по умолчанию `postgresql://pw4:pw4@localhost/pw4`). Тесты пересоздают схему `public` в указанной базе — не указывайте рабочую базу.

---

## 12. Выводы

**Что дал подход MDA:**

1. **Единый источник правды.** Инварианты записаны один раз в `pim.yaml`, а оттуда попали в ограничения БД, схему OpenAPI, исполняемые предикаты и тесты; номер инварианта виден в имени ограничения в БД.
2. **Воспроизводимость.** Схема, контракт и DTO получаются командой, а не вручную; тест проверяет, что повторная генерация даёт тот же результат.
3. **Смена платформы стоит дешевле.** PIM не упоминает PostgreSQL и HTTP: для другого стека (например, Java + MS SQL) нужно заменить таблицы соответствий R1–R16, а не переписывать модель.
4. **Модель нашла реальные дефекты.** Сверка OCL-инвариантов с БД выявила два расхождения между моделью и реализацией (раздел 8.1); без модели они остались бы незамеченными.

**Ограничения и риски:**

1. **Модель и код расходятся.** Поведение (идемпотентность, транзакция, выбор последнего пакета) пишется вручную; если модель изменить, а `app/service.py` нет, тесты покажут расхождение лишь частично.
2. **Свой генератор вместо стандартных средств.** Он покрывает один срез и не заменяет ATL/QVT; для большой модели нужен стандартный инструмент.
3. **Правила инвариантов вида `behavior`** (INV-6, INV-7) в схеме БД выразить нельзя — они держатся на тестах.
4. **Не проверены** производительность, отказоустойчивость и репликация (нужен многоузловой стенд).
5. **Из дополнительных заданий** выполнено только одно — OCL-инварианты и их проверка; вторая PSM, ATL/QVT и XMI-экспорт не делались.
