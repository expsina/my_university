# ПР №4. MDA: курсы валют, PIM → PSM (Python + FastAPI + PostgreSQL)

Вертикальный срез: загрузка пакета курсов валют (идемпотентно) и запрос курса на дату.

## Состав

| Путь | Что это |
| --- | --- |
| `model/pim.yaml` | PIM: сущности, инварианты, операции (без технологических деталей) |
| `generator/generate.py` | Правила R1–R16 PIM → PSM и генерация артефактов |
| `gen/` | Сгенерированное: миграция БД, OpenAPI, DTO, каркас роутера, исполняемые OCL-инварианты (`invariants.py`) |
| `app/` | Написано вручную: бизнес-логика и доступ к БД (`service.py`), приложение (`main.py`) |
| `tests/` | Проверки: ограничения БД, сценарии API, контракт, воспроизводимость; `test_ocl.py` — доп. задание: сверка OCL-инвариантов модели с БД |

## Требования

Python 3.12, PostgreSQL 16 (подойдут и соседние версии).

## Запуск

```bash
pip install -r requirements.txt

# База для проверок. Тесты пересоздают схему public — используйте отдельную пустую базу.
createdb pw4        # или: CREATE DATABASE pw4; пользователь pw4 с паролем pw4
export PW4_DSN=postgresql://pw4:pw4@localhost/pw4   # значение по умолчанию

python generator/generate.py   # генерация в gen/
pytest -v                      # применяет gen/migrations/001_init.sql и запускает проверки
```

Запуск API (миграцию нужно применить: `psql "$PW4_DSN" -f gen/migrations/001_init.sql`):

```bash
uvicorn app.main:app --reload
curl -X PUT localhost:8000/v1/sources/cbr/batches/2026-10-29 \
  -H 'Content-Type: application/json' \
  -d '{"rates":[{"base_currency":"USD","quote_currency":"RUB","rate_date":"2026-10-29","rate":"95.5"}]}'
curl 'localhost:8000/v1/rates/USD/RUB?rate_date=2026-10-29'
```

## Как менять

Меняйте только `model/pim.yaml` и правила в `generator/generate.py`, затем `python generator/generate.py`. Файлы в `gen/` вручную не правятся.
