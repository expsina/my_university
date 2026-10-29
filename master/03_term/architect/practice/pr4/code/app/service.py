"""Вручную написанный слой: бизнес-логика и работа с PostgreSQL.

Реализует контракт BatchService из gen/api.py. Политики PSM:
- транзакции: один пакет = одна транзакция (всё или ничего);
- идемпотентность: ключ (источник, batch_key) + уникальный индекс (INV-1) + отпечаток содержимого;
- ошибки: некорректные строки не вызывают 5xx, пакет получает статус rejected и список причин.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from decimal import Decimal
from typing import Optional

import psycopg

from gen.api import SubmitOutcome
from gen.dto import BatchResult, Issue, Rate, RateRow

DEFAULT_DSN = "postgresql://pw4:pw4@localhost/pw4"
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
MAX_RATE = Decimal("10000000000")  # INV-8: строго меньше 10^10
MAX_SCALE = 8                      # INV-8: не больше 8 знаков после запятой


def digest_of(rates: list[RateRow]) -> str:
    rows = sorted(
        (r.base_currency, r.quote_currency, r.rate_date.isoformat(), format(r.rate.normalize(), "f"))
        for r in rates
    )
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def validate(rates: list[RateRow]) -> list[Issue]:
    """Доменная проверка строк (INV-2, INV-3, INV-4, INV-5) до обращения к БД."""
    issues: list[Issue] = []
    seen: set[tuple] = set()
    for n, r in enumerate(rates, start=1):
        if not CURRENCY_RE.match(r.base_currency) or not CURRENCY_RE.match(r.quote_currency):
            issues.append(Issue(row_number=n, reason="код валюты должен состоять из трёх заглавных латинских букв"))
        elif r.base_currency == r.quote_currency:
            issues.append(Issue(row_number=n, reason="базовая и котируемая валюты совпадают"))
        if not r.rate.is_finite() or r.rate <= 0:
            issues.append(Issue(row_number=n, reason="курс должен быть строго положительным"))
        elif r.rate >= MAX_RATE:
            issues.append(Issue(row_number=n, reason="курс вне допустимого диапазона"))
        elif r.rate.as_tuple().exponent < -MAX_SCALE and r.rate != r.rate.quantize(Decimal(1).scaleb(-MAX_SCALE)):
            issues.append(Issue(row_number=n, reason="у курса больше 8 знаков после запятой"))  # INV-8
        key = (r.base_currency, r.quote_currency, r.rate_date)
        if key in seen:
            issues.append(Issue(row_number=n, reason="дубликат пары валют и даты внутри пакета"))
        seen.add(key)
    return issues


class PgBatchService:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.environ.get("PW4_DSN", DEFAULT_DSN)

    def submit_batch(self, source: str, batch_key: str, rates: list[RateRow]) -> SubmitOutcome:
        digest = digest_of(rates)
        issues = validate(rates)
        status = "rejected" if issues else "accepted"
        with psycopg.connect(self.dsn) as conn:  # транзакция фиксируется при выходе из блока
            source_id = conn.execute(
                "INSERT INTO source (name) VALUES (%s) "
                "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                (source,),
            ).fetchone()[0]
            row = conn.execute(
                "INSERT INTO ingestion_batch (source_id, batch_key, content_digest, status, row_count) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (source_id, batch_key) DO NOTHING RETURNING id",
                (source_id, batch_key, digest, status, len(rates)),
            ).fetchone()
            if row is None:  # ключ уже занят: повтор или конфликт
                old = conn.execute(
                    "SELECT id, content_digest, status, row_count FROM ingestion_batch "
                    "WHERE source_id = %s AND batch_key = %s",
                    (source_id, batch_key),
                ).fetchone()
                if old[1] != digest:
                    return SubmitOutcome(kind="content_conflict")
                old_issues = conn.execute(
                    "SELECT row_number, reason FROM validation_issue WHERE batch_id = %s ORDER BY id",
                    (old[0],),
                ).fetchall()
                result = BatchResult(
                    batch_key=batch_key, status=old[2], row_count=old[3],
                    issues=[Issue(row_number=i[0], reason=i[1]) for i in old_issues],
                )
                return SubmitOutcome(kind="repeated", result=result)
            batch_id = row[0]
            if status == "accepted":
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO exchange_rate (batch_id, base_currency, quote_currency, rate_date, rate) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        [(batch_id, r.base_currency, r.quote_currency, r.rate_date, r.rate) for r in rates],
                    )
            else:
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO validation_issue (batch_id, row_number, reason) VALUES (%s, %s, %s)",
                        [(batch_id, i.row_number, i.reason) for i in issues],
                    )
        return SubmitOutcome(
            kind="created",
            result=BatchResult(batch_key=batch_key, status=status, row_count=len(rates), issues=issues),
        )

    def get_rate(self, base_currency: str, quote_currency: str, rate_date: date) -> Optional[Rate]:
        with psycopg.connect(self.dsn) as conn:
            row = conn.execute(
                "SELECT r.base_currency, r.quote_currency, r.rate_date, r.rate, s.name "
                "FROM exchange_rate r "
                "JOIN ingestion_batch b ON b.id = r.batch_id "
                "JOIN source s ON s.id = b.source_id "
                "WHERE r.base_currency = %s AND r.quote_currency = %s AND r.rate_date = %s "
                "AND b.status = 'accepted' "
                "ORDER BY b.received_at DESC, b.id DESC LIMIT 1",
                (base_currency, quote_currency, rate_date),
            ).fetchone()
        if row is None:
            return None
        return Rate(base_currency=row[0], quote_currency=row[1], rate_date=row[2], rate=row[3], source=row[4])
