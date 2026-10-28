# University

Личный архив учёбы: бакалавриат, магистратура, поступление, диплом и научные работы.

## Структура

```
university/
├── bachelor/          # бакалавриат: NN_term / предмет / тип материала
├── master/            # магистратура: та же схема
├── thesis/            # дипломные работы (bachelor, master)
├── research/          # научные статьи и конференции
├── admission/         # поступление (master, phd)
├── library/           # книги и учебники по предметам (не в git)
└── _shared/           # общие шаблоны и справочники
```

### Учебные семестры

Схема: `уровень / NN_term / предмет / тип_материала`.

```
bachelor/05_term/data_analysis/
├── lectures/
├── practice/
├── homework/
└── exam/
```

Внутри семестра рядом с предметами могут лежать:
- `term_paper/` — курсовая работа;
- `analytic_paper/` — аналитическая работа.

Подпапки создаются по мере надобности, пустые не держим.

### Диплом (`thesis/`)

Для `bachelor` и `master` одинаковый набор:
`text`, `code`, `data`, `figures`, `presentation`, `docs`, `literature`, `pre_degree`.

### Научные работы (`research/`)

Каждая статья в своей папке: `research/papers/ГГГГ_короткое_название/`
со стандартными подпапками (`text`, `code`, `data`, `figures`, `review`).

### Поступление (`admission/`)

Для `master` и `phd`: `exams`, `docs`, `portfolio`.

### Библиотека (`library/`)

Книги и учебники, подпапки названы так же, как предметы.
Папка в `.gitignore`: файлы остаются только на диске, бэкап делается отдельно.

## Соглашения об именах

- Только латиница, нижний регистр, подчёркивания вместо пробелов.
- Без кириллицы, скобок и пробелов в именах файлов и папок.
- Номера с нулём в начале: `01_term`, `lab_03`.
- Предметы называются короткими английскими слагами (список ниже).
- Файлы: `тип_номер_тема`, например `lab_03_regression.pdf`, `hw_05.pdf`.
- Служебные папки начинаются с `_` (`_shared`, `_archive`).

## Слаги предметов

### Бакалавриат
| Семестр | Предметы |
|---|---|
| 01_term | linear_algebra |
| 05_term | data_analysis, math_modeling, stat_multidimensional, stat_non_numeric, stat_population, stat_sectors |
| 06_term | forecasting, stat_business, stat_multidimensional, stat_sampling, stat_social |
| 07_term | applied_analytics, artificial_intelligence, data_visualization, econometrics, finance_report, national_accounting, psychology, stat_finance, stat_risk |

### Магистратура
| Семестр | Предметы |
|---|---|
| 01_term | hardware_software_dev, intellectual_technologies, professional_orientation, science_research_work |
| 02_term | data_analysis, data_warehouse, english, nonlinear_dynamic |
| 03_term | architect, data_mining, math_modeling, neural_networks, parallelism, projects_planning |

`stat_multidimensional` шёл в 5 и 6 семестрах, книги лежат в `library/stat_multidimensional`.

## Git

В репозитории хранятся код, ноутбуки, тексты и небольшие документы.
Не отслеживаются: `library/`, виртуальное окружение `.venv/`, `.env`,
офисные файлы (`*.docx`, `*.xlsx`, `*.pptx`), кроме `_shared/custom-reference.docx`.

## Окружение

Виртуальное окружение Python создаётся локально (`.venv/`, не в git).
Установка зависимостей: см. `requirements.txt` (если появится).

## Бэкап

Сам репозиторий хранится в git. Папка `library/` и офисные файлы не в git,
их бэкап делается через ______ (Time Machine / облако).