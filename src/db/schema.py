"""
Database schema creation and management.
Run this module directly to create/update the schema:
    python -m src.db.schema
"""
import os
import psycopg2
from psycopg2 import sql


def get_connection():
    """Get a database connection from DATABASE_URL env var."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(database_url)


SCHEMA_SQL = """
-- Apps table: registered apps we're tracking
CREATE TABLE IF NOT EXISTS apps (
    app_id          SERIAL PRIMARY KEY,
    package_id      TEXT UNIQUE NOT NULL,
    name            TEXT,
    role            TEXT NOT NULL CHECK (role IN ('employee', 'driver', 'competitor')),
    source          TEXT DEFAULT 'google_play',
    verified_by_human BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Raw reviews: immutable, stores the original JSON payload
CREATE TABLE IF NOT EXISTS raw_reviews (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL DEFAULT 'google_play_scraper',
    source_review_id TEXT NOT NULL,
    app_id          INTEGER NOT NULL REFERENCES apps(app_id),
    payload_json    JSONB NOT NULL,
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, source_review_id, app_id)
);

-- Normalized reviews: cleaned, deduplicated, ready for analysis
CREATE TABLE IF NOT EXISTS reviews (
    review_id       SERIAL PRIMARY KEY,
    app_id          INTEGER NOT NULL REFERENCES apps(app_id),
    source_review_id TEXT NOT NULL,
    rating          INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    text            TEXT,
    lang            TEXT,
    review_date     TIMESTAMPTZ,
    app_version     TEXT,
    device          TEXT,
    thumbs_up       INTEGER DEFAULT 0,
    dev_reply       TEXT,
    dev_reply_date  TIMESTAMPTZ,
    review_hash     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (app_id, source_review_id)
);

-- Labels: classification results from Gemini
CREATE TABLE IF NOT EXISTS labels (
    label_id        SERIAL PRIMARY KEY,
    review_id       INTEGER NOT NULL REFERENCES reviews(review_id),
    taxonomy_version TEXT NOT NULL,
    themes          TEXT[] NOT NULL DEFAULT '{}',
    primary_theme   TEXT NOT NULL,
    sentiment       TEXT,
    severity        INTEGER CHECK (severity BETWEEN 1 AND 3),
    attribution     TEXT CHECK (attribution IN ('app', 'ops_vendor', 'customer_policy', 'unclear')),
    evidence_span   TEXT,
    confidence      REAL CHECK (confidence BETWEEN 0 AND 1),
    model           TEXT,
    prompt_version  TEXT,
    labeled_at      TIMESTAMPTZ DEFAULT NOW(),
    status          TEXT DEFAULT 'auto' CHECK (status IN ('auto', 'human', 'needs_review', 'rejected')),
    UNIQUE (review_id, taxonomy_version, prompt_version)
);

-- Pipeline run log
CREATE TABLE IF NOT EXISTS runs (
    run_id          SERIAL PRIMARY KEY,
    phase           TEXT NOT NULL,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    counts          JSONB DEFAULT '{}',
    errors          JSONB DEFAULT '[]',
    metadata        JSONB DEFAULT '{}'
);

-- Claims ledger for verified report generation
CREATE TABLE IF NOT EXISTS claims (
    claim_id        SERIAL PRIMARY KEY,
    text            TEXT NOT NULL,
    claim_type      TEXT NOT NULL CHECK (claim_type IN ('number', 'quote', 'finding', 'recommendation')),
    sql_or_script   TEXT,
    result          JSONB,
    review_ids      INTEGER[] DEFAULT '{}',
    generated_at    TIMESTAMPTZ DEFAULT NOW(),
    verified        BOOLEAN DEFAULT FALSE,
    verified_at     TIMESTAMPTZ
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_reviews_app_id ON reviews(app_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_date ON reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_reviews_hash ON reviews(review_hash);
CREATE INDEX IF NOT EXISTS idx_labels_review_id ON labels(review_id);
CREATE INDEX IF NOT EXISTS idx_labels_primary_theme ON labels(primary_theme);
CREATE INDEX IF NOT EXISTS idx_labels_attribution ON labels(attribution);
CREATE INDEX IF NOT EXISTS idx_raw_reviews_app_id ON raw_reviews(app_id);
"""


def create_schema(conn):
    """Create all tables and indexes."""
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()
    print("Schema created/updated successfully.")


def seed_apps(conn):
    """Insert the known apps if they don't already exist."""
    apps = [
        ("com.moveinsync.ets", "MoveInSync (Employee)", "employee"),
        ("com.moveinsync.driver.lite", "MoveInSync Partner Lite (Driver)", "driver"),
        ("com.moveinsync.driver.dco", "MoveInSync Driver Onboarding", "driver"),
        ("com.routematic.employee", "Routematic (Employee)", "competitor"),
        ("com.mtap.safetrax", "Safetrax Commuter", "competitor"),
    ]
    with conn.cursor() as cur:
        for package_id, name, role in apps:
            cur.execute(
                """INSERT INTO apps (package_id, name, role, verified_by_human)
                   VALUES (%s, %s, %s, TRUE)
                   ON CONFLICT (package_id) DO NOTHING""",
                (package_id, name, role),
            )
    conn.commit()
    print(f"Seeded {len(apps)} apps.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    conn = get_connection()
    try:
        create_schema(conn)
        seed_apps(conn)
    finally:
        conn.close()
