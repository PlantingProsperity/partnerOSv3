-- PartnerOS v3.2 — schema.sql
-- Enforce auto_vacuum = INCREMENTAL (ADR-M02)
PRAGMA auto_vacuum = INCREMENTAL;

-- ── Infrastructure ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS schema_migrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_id  TEXT NOT NULL UNIQUE,
    applied_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS maintenance_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT    NOT NULL,
    job_name  TEXT    NOT NULL,
    success   INTEGER NOT NULL DEFAULT 1,
    message   TEXT
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT    NOT NULL,
    deal_id      TEXT,
    agent        TEXT    NOT NULL,
    model        TEXT    NOT NULL,
    prompt_len   INTEGER,
    response_len INTEGER,
    tokens_in    INTEGER,
    tokens_out   INTEGER,
    latency_ms   INTEGER,
    success      INTEGER NOT NULL DEFAULT 1,
    error        TEXT
);

CREATE TABLE IF NOT EXISTS gemini_token_usage (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT    NOT NULL,
    date         TEXT    NOT NULL,    -- ISO date: YYYY-MM-DD
    agent        TEXT    NOT NULL,
    model        TEXT    NOT NULL,
    call_type    TEXT    NOT NULL,    -- 'text' | 'audio' | 'embedding'
    tokens_in    INTEGER NOT NULL DEFAULT 0,
    tokens_out   INTEGER NOT NULL DEFAULT 0,
    deal_id      TEXT
);

CREATE INDEX IF NOT EXISTS idx_token_usage_date  ON gemini_token_usage(date);
CREATE INDEX IF NOT EXISTS idx_token_usage_agent ON gemini_token_usage(agent);

CREATE VIEW IF NOT EXISTS v_daily_token_usage AS
    SELECT date,
           SUM(tokens_in + tokens_out) AS total_tokens,
           SUM(CASE WHEN call_type='audio' THEN tokens_in+tokens_out ELSE 0 END) AS audio_tokens,
           SUM(CASE WHEN call_type='text'  THEN tokens_in+tokens_out ELSE 0 END) AS text_tokens,
           ROUND(100.0 * SUM(tokens_in+tokens_out) / 1000000, 1) AS pct_of_daily_budget
    FROM gemini_token_usage
    GROUP BY date
    ORDER BY date DESC;

-- ── Brain (RAG) ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS brain_chunks (
    chunk_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path  TEXT    NOT NULL,
    source_cat   TEXT    NOT NULL CHECK(source_cat IN ('wisdom','reference','learned')),
    chunk_text   TEXT    NOT NULL,
    chunk_index  INTEGER NOT NULL,
    content_hash TEXT    NOT NULL,
    embedded_at  TEXT    NOT NULL,
    embedding    F32_BLOB(768)
);

CREATE VIRTUAL TABLE IF NOT EXISTS brain_chunks_fts
    USING fts5(chunk_text, content='brain_chunks',
               content_rowid='chunk_id', tokenize='porter ascii');

-- FTS5 triggers
CREATE TRIGGER IF NOT EXISTS brain_chunks_ai AFTER INSERT ON brain_chunks BEGIN
  INSERT INTO brain_chunks_fts(rowid, chunk_text) VALUES (new.chunk_id, new.chunk_text);
END;

CREATE TRIGGER IF NOT EXISTS brain_chunks_ad AFTER DELETE ON brain_chunks BEGIN
  INSERT INTO brain_chunks_fts(brain_chunks_fts, rowid, chunk_text) VALUES('delete', old.chunk_id, old.chunk_text);
END;

CREATE TRIGGER IF NOT EXISTS brain_chunks_au AFTER UPDATE ON brain_chunks BEGIN
  INSERT INTO brain_chunks_fts(brain_chunks_fts, rowid, chunk_text) VALUES('delete', old.chunk_id, old.chunk_text);
  INSERT INTO brain_chunks_fts(rowid, chunk_text) VALUES (new.chunk_id, new.chunk_text);
END;

-- ── Prospect Pipeline ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prospects (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_name     TEXT    NOT NULL,
    address        TEXT    NOT NULL,
    parcel_number  TEXT    UNIQUE,
    hold_years     INTEGER,
    equity_score   TEXT    NOT NULL DEFAULT 'UNKNOWN'
                           CHECK(equity_score IN ('HIGH','LOW','UNKNOWN')),
    pipeline_stage TEXT    NOT NULL DEFAULT 'IDENTIFIED',
    source         TEXT    NOT NULL
                           CHECK(source IN ('bird_call','bird_letter','referral',
                                            'csv_import','other')),
    archetype      TEXT,
    last_contact   TEXT,
    notes          TEXT,
    created_at     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS letters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id     INTEGER NOT NULL REFERENCES prospects(id),
    letter_type     TEXT    NOT NULL,
    draft_text      TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'DRAFT'
                            CHECK(status IN ('DRAFT','APPROVED','SENT','REJECTED')),
    approved_by     TEXT,
    approved_at     TEXT,
    sent_at         TEXT,
    rejection_reason TEXT
);

CREATE TABLE IF NOT EXISTS csv_import_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT    NOT NULL,
    imported_at   TEXT    NOT NULL,
    rows_total    INTEGER NOT NULL,
    rows_new      INTEGER NOT NULL,
    rows_updated  INTEGER NOT NULL,
    rows_skipped  INTEGER NOT NULL
);

-- ── Deal Pipeline ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS deals (
    deal_id      TEXT    PRIMARY KEY,
    address      TEXT    NOT NULL,
    address_slug TEXT    NOT NULL,
    jacket_path  TEXT    NOT NULL,
    prospect_id  INTEGER REFERENCES prospects(id),
    thread_id    TEXT    NOT NULL UNIQUE,
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id        TEXT    REFERENCES deals(deal_id),
    file_path      TEXT    NOT NULL UNIQUE,
    original_name  TEXT    NOT NULL,
    file_type      TEXT    NOT NULL,      -- 'audio'|'pdf'|'spreadsheet'|'transcript'|'other'
    content_class  TEXT    NOT NULL,
    content_hash   TEXT    NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'PENDING',
    extracted_text TEXT,
    page_count     INTEGER,
    size_bytes     INTEGER,
    discovered_at  TEXT    NOT NULL,
    processed_at   TEXT
);

CREATE TABLE IF NOT EXISTS draft_financials (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id     TEXT    NOT NULL REFERENCES deals(deal_id),
    citations   TEXT    NOT NULL, -- JSON
    status      TEXT    NOT NULL DEFAULT 'UNVERIFIED',
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS verified_financials (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id     TEXT    NOT NULL REFERENCES deals(deal_id),
    data        TEXT    NOT NULL, -- JSON
    verified_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_analyses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id     TEXT    NOT NULL REFERENCES deals(deal_id),
    cap_rate    REAL,
    dscr        REAL,
    ltv         REAL,
    cash_on_cash REAL,
    irr         REAL,
    below_dscr_floor INTEGER,
    below_cap_floor  INTEGER,
    calculated_at TEXT  NOT NULL
);

CREATE TABLE IF NOT EXISTS property_records (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id           TEXT    NOT NULL REFERENCES deals(deal_id),
    parcel_number     TEXT,
    zoning            TEXT,
    lot_size          REAL,
    building_sqft     REAL,
    year_built        INTEGER,
    assessed_value    REAL,
    mailing_address   TEXT,
    tax_status        TEXT,
    scrape_status     TEXT    NOT NULL, -- 'COMPLETE'|'PARTIAL'
    created_at        TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS seller_profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id         TEXT    NOT NULL REFERENCES deals(deal_id),
    archetype       TEXT    NOT NULL, -- High-D/I/S/C
    archetype_conf  INTEGER,
    motivation_notes TEXT,
    pinneo_cites    TEXT,   -- JSON
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS verdicts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id           TEXT    NOT NULL REFERENCES deals(deal_id),
    verdict           TEXT    NOT NULL CHECK(verdict IN ('APPROVE','KILL')),
    confidence        INTEGER NOT NULL,
    reasoning_text    TEXT    NOT NULL,
    conditions_to_flip TEXT,   -- JSON
    loi_path          TEXT,
    issued_at         TEXT    NOT NULL
);
