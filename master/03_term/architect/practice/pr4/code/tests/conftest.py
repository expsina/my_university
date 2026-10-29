import os
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app

DSN = os.environ.get("PW4_DSN", "postgresql://pw4:pw4@localhost/pw4")
MIGRATION = Path(__file__).resolve().parent.parent / "gen" / "migrations" / "001_init.sql"


@pytest.fixture(scope="session", autouse=True)
def schema():
    """Применяет сгенерированную миграцию к чистой схеме."""
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute(MIGRATION.read_text(encoding="utf-8"))
    yield


@pytest.fixture(autouse=True)
def clean(schema):
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("TRUNCATE validation_issue, exchange_rate, ingestion_batch, source RESTART IDENTITY CASCADE")
    yield


@pytest.fixture
def db():
    with psycopg.connect(DSN, autocommit=True) as conn:
        yield conn


@pytest.fixture
def client():
    return TestClient(create_app(DSN))
