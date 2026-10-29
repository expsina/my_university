-- AUTO-GENERATED из model/pim.yaml (generator/generate.py). Не править вручную.
BEGIN;

CREATE TABLE source (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    CONSTRAINT uq_source_name UNIQUE (name)
);

CREATE TABLE ingestion_batch (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_key TEXT NOT NULL,
    content_digest TEXT NOT NULL,
    status TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_id BIGINT NOT NULL REFERENCES source(id),
    CONSTRAINT ck_ingestion_batch_status_enum CHECK (status IN ('accepted', 'rejected')),
    CONSTRAINT uq_ingestion_batch_inv1 UNIQUE (source_id, batch_key)
);

CREATE TABLE exchange_rate (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate_date DATE NOT NULL,
    rate NUMERIC(18,8) NOT NULL,
    batch_id BIGINT NOT NULL REFERENCES ingestion_batch(id),
    CONSTRAINT ck_exchange_rate_inv5_base_currency CHECK (base_currency ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_exchange_rate_inv5_quote_currency CHECK (quote_currency ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_exchange_rate_inv2 CHECK (rate > 0),
    CONSTRAINT ck_exchange_rate_inv3 CHECK (base_currency <> quote_currency),
    CONSTRAINT uq_exchange_rate_inv4 UNIQUE (batch_id, base_currency, quote_currency, rate_date)
);

CREATE TABLE validation_issue (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    row_number INTEGER NOT NULL,
    reason TEXT NOT NULL,
    batch_id BIGINT NOT NULL REFERENCES ingestion_batch(id)
);

CREATE INDEX ix_ingestion_batch_source_id ON ingestion_batch (source_id);
CREATE INDEX ix_exchange_rate_batch_id ON exchange_rate (batch_id);
CREATE INDEX ix_validation_issue_batch_id ON validation_issue (batch_id);
CREATE INDEX ix_exchange_rate_lookup ON exchange_rate (base_currency, quote_currency, rate_date);

COMMIT;
