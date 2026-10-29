# AUTO-GENERATED из model/pim.yaml (generator/generate.py). Не править вручную.
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
