-- tests/setup/init_test_db.sql

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Articles table
CREATE TABLE IF NOT EXISTS articles_test (
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

-- Chunks vector table
CREATE TABLE IF NOT EXISTS chunks_vector_test (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    title TEXT,
    summary TEXT,
    content TEXT,
    source_link TEXT,
    source_type VARCHAR(50),
    fetched_at TIMESTAMP,
    published_at TIMESTAMP,
    chunk TEXT,
    chunk_index INTEGER,
    embedding vector(768),  -- pgvector type
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles_test(article_id) ON DELETE CASCADE
);

-- Create index on embedding for similarity search
CREATE INDEX IF NOT EXISTS chunks_vector_test_embedding_idx
    ON chunks_vector_test
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Create index on vflag for faster queries
CREATE INDEX IF NOT EXISTS articles_test_vflag_idx
    ON articles_test(vflag);
