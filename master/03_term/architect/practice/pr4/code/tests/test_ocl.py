"""Дополнительное задание: OCL-инварианты из PIM и их проверка в тестах.

Из OCL в model/pim.yaml генератор строит исполняемые предикаты (gen/invariants.py).
Тесты на псевдослучайных данных проверяют: БД принимает строку тогда и только тогда,
когда выполнены все инварианты, выраженные в модели.
"""
import itertools
import random
from decimal import Decimal
from types import SimpleNamespace

import psycopg
import pytest

from gen.invariants import SCALAR, UNIQUE

SEED = 20261029
CURRENCIES = ["USD", "EUR", "RUB", "usd", "US", "EURO", "U1D", "", "USD ", "USD\n"]
RATES = [Decimal(x) for x in ["-5", "0", "0.00000001", "0.5", "95.5", "9999999999.99999999"]]


def snake(n):
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", n).lower()


def new_batch(db, key="k"):
    db.execute("INSERT INTO source (name) VALUES ('s') ON CONFLICT DO NOTHING")
    sid = db.execute("SELECT id FROM source WHERE name='s'").fetchone()[0]
    return db.execute(
        "INSERT INTO ingestion_batch (source_id, batch_key, content_digest, status, row_count) "
        "VALUES (%s, %s, 'd', 'accepted', 1) RETURNING id", (sid, key)).fetchone()[0]


def db_accepts_rate(db, batch_id, row):
    try:
        db.execute(
            "INSERT INTO exchange_rate (batch_id, base_currency, quote_currency, rate_date, rate) "
            "VALUES (%s, %s, %s, '2026-10-29', %s)",
            (batch_id, row.baseCurrency, row.quoteCurrency, row.rate))
        db.execute("DELETE FROM exchange_rate")
        return True
    except (psycopg.errors.CheckViolation, psycopg.errors.StringDataRightTruncation):
        return False


def test_scalar_invariants_match_database(db):
    """INV-2, INV-3, INV-5: решение БД совпадает с предикатами, сгенерированными из OCL."""
    batch = new_batch(db)
    rows = [SimpleNamespace(baseCurrency=b, quoteCurrency=q, rate=r)
            for b, q, r in itertools.product(CURRENCIES, CURRENCIES, RATES)]
    random.Random(SEED).shuffle(rows)
    rows = rows[:400]
    mismatches = []
    for row in rows:
        expected = all(pred(row) for ent, pred in SCALAR.values() if ent == "ExchangeRate")
        actual = db_accepts_rate(db, batch, row)
        if expected != actual:
            mismatches.append((row, expected, actual))
    assert not mismatches, mismatches[:5]


def test_each_scalar_invariant_is_exercised():
    """Данные теста не вырождены: для каждого инварианта есть и нарушающие, и подходящие строки."""
    rows = [SimpleNamespace(baseCurrency=b, quoteCurrency=q, rate=r)
            for b, q, r in itertools.product(CURRENCIES, CURRENCIES, RATES)]
    for name, (_, pred) in SCALAR.items():
        verdicts = {pred(r) for r in rows}
        assert verdicts == {True, False}, name


@pytest.mark.parametrize("inv", sorted(UNIQUE))
def test_unique_invariants_match_database(db, inv):
    """INV-1, INV-4: БД отвергает строку тогда и только тогда, когда ключ уже встречался."""
    entity, fields = UNIQUE[inv]
    rng = random.Random(SEED)
    db.execute("INSERT INTO source (name) VALUES ('s1'), ('s2')")
    sources = [r[0] for r in db.execute("SELECT id FROM source ORDER BY id").fetchall()]
    batches = [new_batch(db, f"base{i}") for i in range(2)]
    seen, mismatches = set(), []
    for _ in range(300):
        if entity == "IngestionBatch":
            row = {"source": rng.choice(sources), "batchKey": rng.choice("abc")}
            sql = ("INSERT INTO ingestion_batch (source_id, batch_key, content_digest, status, row_count) "
                   "VALUES (%s, %s, 'd', 'accepted', 1)")
            params = (row["source"], row["batchKey"])
        else:
            row = {"batch": rng.choice(batches), "baseCurrency": rng.choice(["USD", "EUR"]),
                   "quoteCurrency": rng.choice(["RUB", "CNY"]), "rateDate": rng.choice(["2026-10-28", "2026-10-29"])}
            sql = ("INSERT INTO exchange_rate (batch_id, base_currency, quote_currency, rate_date, rate) "
                   "VALUES (%s, %s, %s, %s, 1)")
            params = (row["batch"], row["baseCurrency"], row["quoteCurrency"], row["rateDate"])
        key = tuple(row[f] for f in fields)
        expected = key not in seen
        try:
            db.execute(sql, params)
            actual = True
        except psycopg.errors.UniqueViolation:
            actual = False
        if actual:
            seen.add(key)
        if expected != actual:
            mismatches.append((row, expected, actual))
    assert not mismatches, mismatches[:5]
    assert 0 < len(seen) < 300  # были и принятые, и отклонённые строки
