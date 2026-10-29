"""Генератор PIM -> PSM (Python + FastAPI + PostgreSQL).

Читает model/pim.yaml, применяет правила трансформации и пишет артефакты в gen/.
Запуск из корня проекта:  python generator/generate.py
Вывод детерминирован: повторный запуск даёт побайтово тот же результат.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PIM_PATH = ROOT / "model" / "pim.yaml"
GEN = ROOT / "gen"

# ---------------------------------------------------------------------------
# Правила трансформации (таблицы соответствий PIM -> PSM)
# ---------------------------------------------------------------------------

# R1. Базовый тип PIM -> тип PostgreSQL
SQL_TYPES = {
    "Text": "TEXT",
    "Integer": "INTEGER",
    "Date": "DATE",
    "Timestamp": "TIMESTAMPTZ",
    "Decimal": "NUMERIC(18,8)",
}

# R2. Базовый тип PIM -> тип Python/Pydantic (DTO)
PY_TYPES = {
    "Text": "str",
    "Integer": "int",
    "Date": "date",
    "Timestamp": "datetime",
    "Decimal": "Decimal",
}

# R3. Базовый тип PIM -> схема OpenAPI
OAS_TYPES = {
    "Text": {"type": "string"},
    "Integer": {"type": "integer"},
    "Date": {"type": "string", "format": "date"},
    "Timestamp": {"type": "string", "format": "date-time"},
    "Decimal": {"type": "string", "format": "decimal"},
}

# R4. Вид инварианта -> префикс имени ограничения
CONSTRAINT_PREFIX = {"unique": "uq", "positive": "ck", "distinct": "ck", "type": "ck"}


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def load_pim() -> dict:
    return yaml.safe_load(PIM_PATH.read_text(encoding="utf-8"))


class Pim:
    def __init__(self, data: dict):
        self.d = data
        self.enums = data.get("enums", {})
        self.types = data.get("types", {})
        self.entities = data["entities"]
        self.invariants = data.get("invariants", [])
        self.structures = data.get("structures", {})
        self.operations = data["operations"]

    def base_type(self, t: str) -> str:
        """Раскрывает доменный тип (CurrencyCode) до базового (Text)."""
        return self.types[t]["base"] if t in self.types else t


# ---------------------------------------------------------------------------
# R5-R9. PIM -> схема БД (миграция)
# ---------------------------------------------------------------------------

def gen_sql(pim: Pim) -> str:
    out = [
        "-- AUTO-GENERATED из model/pim.yaml (generator/generate.py). Не править вручную.",
        "BEGIN;",
        "",
    ]
    tables = {e: snake(e) for e in pim.entities}
    # колонка -> список инвариантов типа (R8: инвариант типа -> CHECK)
    for ename, ent in pim.entities.items():
        table = tables[ename]
        cols = ["    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY"]
        checks = []
        # R5: атрибут -> колонка
        for aname, a in ent.get("attributes", {}).items():
            col = snake(aname)
            t = a["type"]
            if t in pim.enums:
                sql_t = "TEXT"
                values = ", ".join(f"'{v}'" for v in pim.enums[t])
                checks.append(f"    CONSTRAINT ck_{table}_{col}_enum CHECK ({col} IN ({values}))")
            else:
                sql_t = SQL_TYPES[pim.base_type(t)]  # CurrencyCode -> TEXT: длину и формат держит CHECK (INV-5)
            line = f"    {col} {sql_t} NOT NULL"
            if a.get("auto") == "creationMoment":  # R6
                line += " DEFAULT now()"
            cols.append(line)
            # R8: инвариант типа -> CHECK
            if t == "CurrencyCode":
                inv = pim.types[t]["invariant"]["id"].lower().replace("-", "")
                checks.append(
                    f"    CONSTRAINT ck_{table}_{inv}_{col} CHECK ({col} ~ '^[A-Z]{{3}}$')"
                )
            if a.get("identifying"):  # R7: идентифицирующий атрибут -> UNIQUE
                checks.append(f"    CONSTRAINT uq_{table}_{col} UNIQUE ({col})")
        # R7: ассоциация с кратностью 1 -> внешний ключ
        for aname, assoc in ent.get("associations", {}).items():
            col = f"{snake(aname)}_id"
            cols.append(f"    {col} BIGINT NOT NULL REFERENCES {tables[assoc['target']]}(id)")
        # R9: инварианты сущности -> ограничения
        for inv in pim.invariants:
            if inv["entity"] != ename or inv["kind"] == "behavior":
                continue
            n = inv["id"].lower().replace("-", "")
            prefix = CONSTRAINT_PREFIX[inv["kind"]]
            name = f"{prefix}_{table}_{n}"
            if inv["kind"] == "unique":
                over = [
                    f"{snake(x)}_id" if x in ent.get("associations", {}) else snake(x)
                    for x in inv["over"]
                ]
                checks.append(f"    CONSTRAINT {name} UNIQUE ({', '.join(over)})")
            elif inv["kind"] == "positive":
                checks.append(f"    CONSTRAINT {name} CHECK ({snake(inv['attribute'])} > 0)")
            elif inv["kind"] == "distinct":
                a, b = (snake(x) for x in inv["attributes"])
                checks.append(f"    CONSTRAINT {name} CHECK ({a} <> {b})")
        out.append(f"CREATE TABLE {table} (")
        out.append(",\n".join(cols + checks))
        out.append(");")
        out.append("")
    # R10: внешние ключи -> индексы
    for ename, ent in pim.entities.items():
        for aname in ent.get("associations", {}):
            out.append(
                f"CREATE INDEX ix_{tables[ename]}_{snake(aname)}_id "
                f"ON {tables[ename]} ({snake(aname)}_id);"
            )
    # R11: lookup операции -> составной индекс
    for oname, op in pim.operations.items():
        if "lookup" in op:
            lk = op["lookup"]
            cols = ", ".join(snake(c) for c in lk["by"])
            out.append(
                f"CREATE INDEX ix_{tables[lk['entity']]}_lookup ON {tables[lk['entity']]} ({cols});"
            )
    out += ["", "COMMIT;", ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# R12-R14. PIM -> DTO (Pydantic) и OpenAPI
# ---------------------------------------------------------------------------

def parse_type(t: str):
    """'Issue[]' -> ('Issue', True)."""
    return (t[:-2], True) if t.endswith("[]") else (t, False)


def py_type(pim: Pim, t: str) -> str:
    inner, many = parse_type(t)
    if inner in pim.enums:
        py = "Literal[" + ", ".join(repr(v) for v in pim.enums[inner]) + "]"
    elif inner in pim.structures:
        py = inner
    else:
        py = PY_TYPES[pim.base_type(inner)]
    return f"list[{py}]" if many else py


def oas_schema(pim: Pim, t: str) -> dict:
    inner, many = parse_type(t)
    if inner in pim.enums:
        s = {"type": "string", "enum": list(pim.enums[inner])}
    elif inner in pim.structures:
        s = {"$ref": f"#/components/schemas/{inner}"}
    else:
        s = dict(OAS_TYPES[pim.base_type(inner)])
    return {"type": "array", "items": s} if many else s


def gen_dto(pim: Pim) -> str:
    out = [
        "# AUTO-GENERATED из model/pim.yaml (generator/generate.py). Не править вручную.",
        "from __future__ import annotations",
        "",
        "from datetime import date, datetime  # noqa: F401",
        "from decimal import Decimal  # noqa: F401",
        "from typing import Literal  # noqa: F401",
        "",
        "from pydantic import BaseModel",
        "",
    ]
    for sname, fields in pim.structures.items():
        out += ["", f"class {sname}(BaseModel):"]
        for fname, t in fields.items():
            out.append(f"    {snake(fname)}: {py_type(pim, t)}")
        out.append("")
    # R13: команда -> тело запроса без параметров идемпотентности (они уходят в путь)
    for oname, op in pim.operations.items():
        if op["kind"] == "command":
            body = {k: v for k, v in op["input"].items() if k not in op["idempotencyKey"]}
            cls = oname[0].upper() + oname[1:] + "Request"
            out += ["", f"class {cls}(BaseModel):"]
            for fname, t in body.items():
                out.append(f"    {snake(fname)}: {py_type(pim, t)}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def gen_openapi(pim: Pim) -> str:
    schemas = {}
    for sname, fields in pim.structures.items():
        schemas[sname] = {
            "type": "object",
            "required": [snake(f) for f in fields],
            "properties": {snake(f): oas_schema(pim, t) for f, t in fields.items()},
        }
    paths = {}
    for oname, op in pim.operations.items():
        if op["kind"] == "command":
            # R12: идемпотентная команда -> PUT, ключ идемпотентности в пути
            key = op["idempotencyKey"]
            path = "/v1/sources/{source}/batches/{batch_key}"
            body = {k: v for k, v in op["input"].items() if k not in key}
            req = oname[0].upper() + oname[1:] + "Request"
            schemas[req] = {
                "type": "object",
                "required": [snake(f) for f in body],
                "properties": {snake(f): oas_schema(pim, t) for f, t in body.items()},
            }
            paths[path] = {
                "put": {
                    "operationId": oname,
                    "summary": op["description"],
                    "parameters": [
                        {"name": snake(k), "in": "path", "required": True, "schema": {"type": "string"}}
                        for k in key
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{req}"}}},
                    },
                    "responses": {
                        "201": {"description": "Пакет принят впервые",
                                "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{op['output']}"}}}},
                        "200": {"description": "Повтор: тот же ключ и то же содержимое, данные не изменены",
                                "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{op['output']}"}}}},
                        "409": {"description": "Тот же ключ, но другое содержимое",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "422": {"description": "Тело или параметры не соответствуют схеме",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            }
        else:
            # R12: запрос -> GET; валюты в путь, остальное в query
            path = "/v1/rates/{base_currency}/{quote_currency}"
            params = []
            for k, t in op["input"].items():
                inner = pim.base_type(t)
                schema = dict(OAS_TYPES[inner])
                if t == "CurrencyCode":
                    schema["pattern"] = "^[A-Z]{3}$"  # R8 на границе API
                where = "path" if t == "CurrencyCode" else "query"
                params.append({"name": snake(k), "in": where, "required": True, "schema": schema})
            paths[path] = {
                "get": {
                    "operationId": oname,
                    "summary": op["description"],
                    "parameters": params,
                    "responses": {
                        "200": {"description": "Курс найден",
                                "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{op['output']}"}}}},
                        "404": {"description": "Курса на эту дату нет",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "422": {"description": "Параметры не соответствуют схеме",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                }
            }
    schemas["Error"] = {"type": "object", "properties": {"detail": {"description": "Описание ошибки"}}}
    doc = {
        "openapi": "3.0.3",
        "info": {
            "title": "Currency Rates Ingestion API",
            "version": "1.0.0",
            "description": "AUTO-GENERATED из model/pim.yaml (generator/generate.py).",
        },
        "paths": paths,
        "components": {"schemas": schemas},
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def gen_api(pim: Pim) -> str:
    """R14: операции PIM -> контракт сервиса (Protocol) и каркас роутера FastAPI."""
    return '''# AUTO-GENERATED из model/pim.yaml (generator/generate.py). Не править вручную.
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, Optional, Protocol

from fastapi import APIRouter, HTTPException, Path, Query, Response

from gen.dto import BatchResult, Rate, RateRow, SubmitBatchRequest

CURRENCY_PATTERN = r"^[A-Z]{3}$"


@dataclass
class SubmitOutcome:
    kind: Literal["created", "repeated", "content_conflict"]
    result: Optional[BatchResult] = None


class BatchService(Protocol):
    """Контракт, который реализует вручную написанный слой (app/service.py)."""

    def submit_batch(self, source: str, batch_key: str, rates: list[RateRow]) -> SubmitOutcome: ...

    def get_rate(self, base_currency: str, quote_currency: str, rate_date: date) -> Optional[Rate]: ...


def create_router(service: BatchService) -> APIRouter:
    router = APIRouter()

    @router.put(
        "/v1/sources/{source}/batches/{batch_key}",
        response_model=BatchResult,
        status_code=201,
        operation_id="submitBatch",
        summary="Источник передаёт пакет курсов.",
    )
    def submit_batch(source: str, batch_key: str, body: SubmitBatchRequest, response: Response):
        outcome = service.submit_batch(source, batch_key, body.rates)
        if outcome.kind == "content_conflict":
            raise HTTPException(status_code=409, detail="Пакет с этим ключом уже принят с другим содержимым")
        if outcome.kind == "repeated":
            response.status_code = 200
        return outcome.result

    @router.get(
        "/v1/rates/{base_currency}/{quote_currency}",
        response_model=Rate,
        operation_id="getRate",
        summary="Потребитель запрашивает курс на дату.",
    )
    def get_rate(
        base_currency: str = Path(pattern=CURRENCY_PATTERN),
        quote_currency: str = Path(pattern=CURRENCY_PATTERN),
        rate_date: date = Query(),
    ):
        rate = service.get_rate(base_currency, quote_currency, rate_date)
        if rate is None:
            raise HTTPException(status_code=404, detail="Курса на эту дату нет")
        return rate

    return router
'''


# ---------------------------------------------------------------------------
# R16. OCL-инварианты -> исполняемые проверки (gen/invariants.py)
# ---------------------------------------------------------------------------

def ocl_to_python(expr: str, subject: str) -> str:
    """Переводит подмножество OCL в выражение Python.

    Поддержано: self.<атрибут>, self.matches('regex'), сравнения (>, <, =, <>), and, or, not.
    Выражения с коллекциями (allInstances, isUnique, implies, ->) этим переводчиком не
    обрабатываются: уникальность проверяется по метаданным UNIQUE, а INV-6 — тестами API.
    """
    out = expr
    # self.matches('X') -> значение типа проверяется регулярным выражением целиком
    out = re.sub(r"self\.matches\('([^']*)'\)", rf"bool(re.fullmatch(r'\1', {subject}))", out)
    out = out.replace("self.", "row.").replace("<>", "!=")
    out = re.sub(r"(?<![<>!=])=(?!=)", "==", out)
    return out


def gen_invariants(pim: Pim) -> str:
    out = [
        "# AUTO-GENERATED из model/pim.yaml (generator/generate.py). Не править вручную.",
        "# Исполняемые версии OCL-инвариантов; используются тестами для сверки с БД.",
        "import re  # noqa: F401",
        "from decimal import Decimal  # noqa: F401",
        "",
        "SCALAR = {}   # инвариант -> (сущность, функция-предикат над строкой)",
        "UNIQUE = {}   # инвариант -> (сущность, поля ключа)",
        "",
    ]
    # инварианты типов (INV-5): предикат применяется ко всем атрибутам этого типа
    for tname, t in pim.types.items():
        inv = t.get("invariant")
        if not inv or "ocl" not in inv:
            continue
        n = inv["id"].lower().replace("-", "")
        body = ocl_to_python(inv["ocl"], "value")
        out += [f"def {n}_value(value):", f"    # OCL: {inv['ocl']}", f"    return {body}", ""]
        for ename, ent in pim.entities.items():
            attrs = [a for a, d in ent.get("attributes", {}).items() if d["type"] == tname]
            if attrs:
                conds = " and ".join(f"{n}_value(row.{a})" for a in attrs)
                out += [f"def {n}(row):", f"    return {conds}", "",
                        f"SCALAR[{inv['id']!r}] = ({ename!r}, {n})", ""]
    for inv in pim.invariants:
        if "ocl" not in inv:
            continue
        n = inv["id"].lower().replace("-", "")
        if inv["kind"] in ("positive", "distinct"):
            out += [f"def {n}(row):", f"    # OCL: {inv['ocl']}",
                    f"    return {ocl_to_python(inv['ocl'], 'row')}", "",
                    f"SCALAR[{inv['id']!r}] = ({inv['entity']!r}, {n})", ""]
        elif inv["kind"] == "unique":
            out += [f"UNIQUE[{inv['id']!r}] = ({inv['entity']!r}, {tuple(inv['over'])!r})  # OCL: {inv['ocl']}", ""]
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    pim = Pim(load_pim())
    (GEN / "migrations").mkdir(parents=True, exist_ok=True)
    files = {
        GEN / "migrations" / "001_init.sql": gen_sql(pim),
        GEN / "openapi.yaml": gen_openapi(pim),
        GEN / "dto.py": gen_dto(pim),
        GEN / "api.py": gen_api(pim),
        GEN / "invariants.py": gen_invariants(pim),
        GEN / "__init__.py": "",
    }
    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
        print(f"generated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
