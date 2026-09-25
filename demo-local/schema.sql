-- NewsJuice local demo schema.
-- Table and column names match the production names the services expect
-- (articles / chunks_vector), NOT the *_test names used by the pytest fixtures.

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------
-- Articles: one row per scraped article (written by the scraper)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS articles (
    id           SERIAL PRIMARY KEY,
    article_id   VARCHAR(255) UNIQUE NOT NULL,
    author       VARCHAR(255),
    title        TEXT,
    summary      TEXT,
    content      TEXT,
    source_link  TEXT,
    source_type  VARCHAR(100),
    fetched_at   TIMESTAMP,
    published_at TIMESTAMP,
    vflag        INTEGER DEFAULT 0,          -- 0 = not yet chunked/embedded
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS articles_vflag_idx ON articles (vflag);

-- ---------------------------------------------------------------
-- Chunks + embeddings: what retrieval actually searches
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chunks_vector (
    id           SERIAL PRIMARY KEY,
    article_id   VARCHAR(255) NOT NULL,
    author       VARCHAR(255),
    title        TEXT,
    summary      TEXT,
    content      TEXT,
    source_link  TEXT,
    source_type  VARCHAR(100),
    fetched_at   TIMESTAMP,
    published_at TIMESTAMP,
    chunk        TEXT,
    chunk_index  INTEGER,
    embedding    vector(768),                -- text-embedding-004
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles (article_id) ON DELETE CASCADE
);

-- NO vector index here, on purpose. ivfflat learns its clusters from the rows
-- that exist when the index is built; built on an empty table, its clusters are
-- meaningless and searches return near-random chunks. At a few thousand rows an
-- exact scan is fast anyway. At real scale: load data first, then create
-- HNSW (or ivfflat with lists ~ rows/1000).

CREATE INDEX IF NOT EXISTS chunks_vector_source_type_idx ON chunks_vector (source_type);

-- ---------------------------------------------------------------
-- User tables (only needed if you run WITH Firebase auth)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id    VARCHAR(255) PRIMARY KEY,     -- Firebase uid
    email      VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Key/value layout, matching user_db.py: one row per (user, preference name).
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id          VARCHAR(255) NOT NULL,
    preference_key   VARCHAR(100) NOT NULL,
    preference_value TEXT,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, preference_key),
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audio_history (
    id            SERIAL PRIMARY KEY,
    user_id       VARCHAR(255),
    question_text TEXT,
    podcast_text  TEXT,
    audio_url     TEXT,
    source_chunks JSONB DEFAULT NULL,        -- migration 001: daily-brief context
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS audio_history_user_idx ON audio_history (user_id, created_at DESC);
