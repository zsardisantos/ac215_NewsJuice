
-- Enable pgvector extension (just in case, though scraper might not use it directly, standardizing is good)
CREATE EXTENSION IF NOT EXISTS vector;

-- Articles table (Matching the schema expected by PostgresDBManager and scrapers.py)
-- Note: Table name HARDCODED to 'articles' in db_manager.py
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) UNIQUE NOT NULL,
    author VARCHAR(255),
    title TEXT,
    summary TEXT,
    content TEXT,
    source_link TEXT,
    source_type VARCHAR(50),
    fetched_at TIMESTAMP,
    published_at TIMESTAMP,
    vflag INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index on source_link for faster filtering in filter_new_urls
CREATE INDEX IF NOT EXISTS articles_source_link_idx ON articles(source_link);
