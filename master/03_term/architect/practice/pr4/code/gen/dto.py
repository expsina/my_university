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
