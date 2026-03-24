-- Migration 004: Cognitive Memory Foundation (H-MEM)
-- Date: 2026-03-24

-- 1. Episodic Traces: Raw, time-stamped interaction summaries
CREATE TABLE IF NOT EXISTS episodic_traces (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id           TEXT NOT NULL REFERENCES deals(deal_id),
    seller_id         TEXT NOT NULL,
    trace_date        TEXT NOT NULL,
    trace_type        TEXT CHECK(trace_type IN ('MEETING','CALL','EMAIL','TEXT')),
    raw_summary       TEXT NOT NULL,
    salience_score    REAL DEFAULT 0.5,
    created_at        TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_episodic_seller ON episodic_traces(seller_id);
CREATE INDEX IF NOT EXISTS idx_episodic_deal ON episodic_traces(deal_id);

-- 2. Semantic Facts: Distilled, stateful truths about a seller/deal
CREATE TABLE IF NOT EXISTS semantic_facts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id         TEXT NOT NULL,
    trait_key         TEXT NOT NULL, -- e.g., 'motivation_level'
    trait_value       TEXT NOT NULL, -- e.g., 'High'
    alpha             REAL DEFAULT 1.0, -- Positive evidence (Bayesian)
    beta              REAL DEFAULT 1.0, -- Negative evidence (Bayesian)
    confidence        REAL GENERATED ALWAYS AS (alpha / (alpha + beta)) VIRTUAL,
    last_updated      TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(seller_id, trait_key)
);

-- 3. Procedural Tactics: Maps tactics to archetypes (Procedural Memory)
CREATE TABLE IF NOT EXISTS procedural_tactics (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    archetype         TEXT NOT NULL,
    tactic_name       TEXT NOT NULL,
    description       TEXT NOT NULL,
    success_rate      REAL DEFAULT 0.0,
    created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Register migration
INSERT OR IGNORE INTO schema_migrations (migration_id, applied_at) VALUES ('004_cognitive_memory', CURRENT_TIMESTAMP);
