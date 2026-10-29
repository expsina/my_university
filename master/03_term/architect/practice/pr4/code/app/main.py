from fastapi import FastAPI

from app.service import PgBatchService
from gen.api import create_router


def create_app(dsn: str | None = None) -> FastAPI:
    app = FastAPI(title="Currency Rates Ingestion API", version="1.0.0")
    app.include_router(create_router(PgBatchService(dsn)))
    return app


app = create_app()
