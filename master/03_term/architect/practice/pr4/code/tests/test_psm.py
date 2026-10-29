"""Проверка соответствия PSM модели PIM: ограничения БД, поведение API, контракт, воспроизводимость."""
import hashlib
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest
import yaml
from openapi_spec_validator import validate

from app.main import create_app

ROOT = Path(__file__).resolve().parent.parent
GOOD = [
    {"base_currency": "USD", "quote_currency": "RUB", "rate_date": "2026-10-29", "rate": "95.5"},
    {"base_currency": "EUR", "quote_currency": "RUB", "rate_date": "2026-10-29", "rate": "104.25"},
]


def put(client, key, rates, source="cbr"):
    return client.put(f"/v1/sources/{source}/batches/{key}", json={"rates": rates})


# --- Ограничения базы (INV-1 ... INV-5) -----------------------------------------------

def test_every_invariant_has_named_constraint(db):
    """Трассируемость: каждый формальный инвариант PIM виден как ограничение в БД."""
    names = {r[0] for r in db.execute("SELECT conname FROM pg_constraint").fetchall()}
    for expected in [
        "uq_ingestion_batch_inv1", "ck_exchange_rate_inv2", "ck_exchange_rate_inv3",
        "uq_exchange_rate_inv4", "ck_exchange_rate_inv5_base_currency", "ck_exchange_rate_inv5_quote_currency",
    ]:
        assert expected in names, expected


def _batch(db, key="k1"):
    db.execute("INSERT INTO source (name) VALUES ('s') ON CONFLICT DO NOTHING")
    sid = db.execute("SELECT id FROM source WHERE name='s'").fetchone()[0]
    return db.execute(
        "INSERT INTO ingestion_batch (source_id, batch_key, content_digest, status, row_count) "
        "VALUES (%s, %s, 'd', 'accepted', 1) RETURNING id", (sid, key)).fetchone()[0], sid


def test_inv1_batch_key_unique_per_source(db):
    _, sid = _batch(db)
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute("INSERT INTO ingestion_batch (source_id, batch_key, content_digest, status, row_count) "
                   "VALUES (%s, 'k1', 'd', 'accepted', 1)", (sid,))


@pytest.mark.parametrize("base,quote,rate,error", [
    ("USD", "RUB", -1, psycopg.errors.CheckViolation),      # INV-2
    ("USD", "RUB", 0, psycopg.errors.CheckViolation),       # INV-2
    ("USD", "USD", 1, psycopg.errors.CheckViolation),       # INV-3
    ("usd", "RUB", 1, psycopg.errors.CheckViolation),       # INV-5
    ("US", "RUB", 1, psycopg.errors.CheckViolation),        # INV-5: короткий код
])
def test_rate_constraints(db, base, quote, rate, error):
    bid, _ = _batch(db)
    with pytest.raises(error):
        db.execute("INSERT INTO exchange_rate (batch_id, base_currency, quote_currency, rate_date, rate) "
                   "VALUES (%s, %s, %s, '2026-10-29', %s)", (bid, base, quote, rate))


def test_inv4_duplicate_pair_date_in_batch(db):
    bid, _ = _batch(db)
    sql = ("INSERT INTO exchange_rate (batch_id, base_currency, quote_currency, rate_date, rate) "
           "VALUES (%s, 'USD', 'RUB', '2026-10-29', 90)")
    db.execute(sql, (bid,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute(sql, (bid,))


# --- Поведение API (INV-6, INV-7, сценарии CIM) -----------------------------------------

def test_scenario_submit_then_get_rate(client):
    r = put(client, "2026-10-29", GOOD)
    assert r.status_code == 201
    assert r.json() == {"batch_key": "2026-10-29", "status": "accepted", "row_count": 2, "issues": []}
    got = client.get("/v1/rates/USD/RUB", params={"rate_date": "2026-10-29"})
    assert got.status_code == 200
    assert got.json()["source"] == "cbr" and float(got.json()["rate"]) == 95.5


def test_inv7_repeat_is_idempotent(client, db):
    assert put(client, "k", GOOD).status_code == 201
    again = put(client, "k", GOOD)
    assert again.status_code == 200
    assert again.json()["status"] == "accepted"
    assert db.execute("SELECT count(*) FROM exchange_rate").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM ingestion_batch").fetchone()[0] == 1


def test_inv7_same_key_other_content_is_conflict(client, db):
    put(client, "k", GOOD)
    other = [dict(GOOD[0], rate="99")]
    assert put(client, "k", other).status_code == 409
    assert db.execute("SELECT count(*) FROM exchange_rate").fetchone()[0] == 2


def test_same_key_different_source_is_allowed(client):
    assert put(client, "k", GOOD, source="a").status_code == 201
    assert put(client, "k", GOOD, source="b").status_code == 201


def test_inv6_invalid_row_rejects_whole_batch(client, db):
    bad = GOOD + [{"base_currency": "USD", "quote_currency": "USD", "rate_date": "2026-10-29", "rate": "-5"}]
    r = put(client, "bad", bad)
    assert r.status_code == 201 and r.json()["status"] == "rejected"
    assert {i["row_number"] for i in r.json()["issues"]} == {3}
    assert db.execute("SELECT count(*) FROM exchange_rate").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM validation_issue").fetchone()[0] == 2
    # повтор отклонённого пакета возвращает те же причины и ничего не добавляет
    again = put(client, "bad", bad)
    assert again.status_code == 200 and again.json()["issues"] == r.json()["issues"]
    assert db.execute("SELECT count(*) FROM validation_issue").fetchone()[0] == 2
    assert client.get("/v1/rates/USD/RUB", params={"rate_date": "2026-10-29"}).status_code == 404


def test_duplicate_row_in_batch_rejected(client):
    r = put(client, "dup", GOOD + [GOOD[0]])
    assert r.json()["status"] == "rejected"


def test_latest_accepted_batch_wins_and_rejected_is_ignored(client):
    put(client, "b1", [dict(GOOD[0], rate="90")])
    put(client, "b2", [dict(GOOD[0], rate="91")])
    put(client, "b3", [dict(GOOD[0], rate="-1")])  # отклонён
    got = client.get("/v1/rates/USD/RUB", params={"rate_date": "2026-10-29"}).json()
    assert float(got["rate"]) == 91


@pytest.mark.parametrize("url,params", [
    ("/v1/rates/usd/RUB", {"rate_date": "2026-10-29"}),
    ("/v1/rates/USD/RUB", {}),
    ("/v1/rates/USD/RUB", {"rate_date": "not-a-date"}),
])
def test_malformed_requests_422(client, url, params):
    assert client.get(url, params=params).status_code == 422


def test_malformed_body_422(client):
    assert client.put("/v1/sources/a/batches/k", json={"rates": [{"base_currency": "USD"}]}).status_code == 422


# --- Контракт и воспроизводимость ----------------------------------------------------------

def test_openapi_is_valid_and_matches_application():
    spec = yaml.safe_load((ROOT / "gen" / "openapi.yaml").read_text(encoding="utf-8"))
    validate(spec)
    live = create_app().openapi()
    spec_ops = {(p, m) for p, item in spec["paths"].items() for m in item}
    live_ops = {(p, m) for p, item in live["paths"].items() for m in item}
    assert spec_ops == live_ops


def test_generation_is_reproducible():
    def snapshot():
        files = sorted((ROOT / "gen").rglob("*"))
        return {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in files if f.is_file() and "__pycache__" not in f.parts}
    before = snapshot()
    subprocess.run([sys.executable, str(ROOT / "generator" / "generate.py")], check=True, capture_output=True)
    assert snapshot() == before


def test_concurrent_submissions_create_exactly_one_batch(db):
    """ADR-1: при гонке одинаковых запросов уникальный индекс оставляет один пакет."""
    from concurrent.futures import ThreadPoolExecutor
    from app.service import PgBatchService
    from gen.dto import RateRow
    from tests.conftest import DSN
    rows = [RateRow(base_currency="USD", quote_currency="RUB", rate_date="2026-10-29", rate="95.5")]
    svc = PgBatchService(DSN)
    with ThreadPoolExecutor(8) as pool:
        kinds = [f.result().kind for f in [pool.submit(svc.submit_batch, "cbr", "race", rows) for _ in range(8)]]
    assert kinds.count("created") == 1 and kinds.count("repeated") == 7
    assert db.execute("SELECT count(*) FROM exchange_rate").fetchone()[0] == 1


@pytest.mark.parametrize("rate", ["0.000000001", "0.123456789", "10000000000", "1E+12"])
def test_inv8_out_of_range_or_precision_is_rejected_not_500(client, db, rate):
    """INV-8: недопустимая точность и величина дают отклонённый пакет, а не ошибку сервера."""
    r = put(client, "p" + rate, [dict(GOOD[0], rate=rate)])
    assert r.status_code == 201 and r.json()["status"] == "rejected"
    assert db.execute("SELECT count(*) FROM exchange_rate").fetchone()[0] == 0


@pytest.mark.parametrize("rate", ["0.12345678", "0.1234567800", "9999999999.99999999"])
def test_inv8_boundary_values_are_accepted(client, rate):
    assert put(client, "b" + rate, [dict(GOOD[0], rate=rate)]).json()["status"] == "accepted"
