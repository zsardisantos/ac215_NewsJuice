"""Integration tests for loader database operations"""

import pytest
import psycopg
from psycopg import sql
import pandas as pd


@pytest.fixture(autouse=True)
def mock_env(monkeypatch, db_url):
    """Set DATABASE_URL for loader_modular import"""
    monkeypatch.setenv("DATABASE_URL", db_url)


@pytest.fixture
def clean_test_data(db_url, articles_table, vector_table):
    """Clean up test data before and after each test"""
    yield
    # Cleanup after test
    conn = psycopg.connect(db_url, autocommit=True)
    cur = conn.cursor()
    cur.execute(
        sql.SQL("DELETE FROM {} WHERE article_id LIKE 'test-%'").format(
            sql.Identifier(vector_table)
        )
    )
    cur.execute(
        sql.SQL("DELETE FROM {} WHERE article_id LIKE 'test-%'").format(
            sql.Identifier(articles_table)
        )
    )
    cur.close()
    conn.close()


@pytest.fixture
def insert_test_article(db_url, articles_table):
    """Insert a test article and return its article_id"""
    conn = psycopg.connect(db_url, autocommit=True)
    cur = conn.cursor()
    
    article_id = "test-integration-001"
    cur.execute(
        sql.SQL("""
            INSERT INTO {} (article_id, title, author, content, source_link, source_type, vflag)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (article_id) DO NOTHING
        """).format(sql.Identifier(articles_table)),
        (article_id, "Test Title", "Test Author", "Test content for chunking.", "http://test.com", "test", 0)
    )
    
    cur.close()
    conn.close()
    
    return article_id


class TestDatabaseManagerIntegration:
    
    def test_fetch_unprocessed_articles(self, db_url, insert_test_article, clean_test_data):
        """Test DatabaseManager fetches articles with vflag=0"""
        from loader_modular import DatabaseManager
        
        with DatabaseManager(db_url) as db:
            articles = db.fetch_unprocessed_articles()
        
        # Should find at least our test article
        article_ids = [a.article_id for a in articles]
        assert insert_test_article in article_ids
    
    def test_insert_chunks(self, db_url, vector_table, insert_test_article, clean_test_data):
        """Test DatabaseManager inserts chunks correctly"""
        from loader_modular import DatabaseManager
        
        # Create test chunks DataFrame
        df = pd.DataFrame([
            {
                "author": "Test Author",
                "title": "Test Title",
                "summary": "Test summary",
                "content": "Test content",
                "source_link": "http://test.com",
                "source_type": "test",
                "fetched_at": "2025-01-01",
                "published_at": "2025-01-01",
                "chunk": "This is chunk 1",
                "chunk_index": 0,
                "embedding": [0.1] * 768,
                "article_id": insert_test_article,
            },
            {
                "author": "Test Author",
                "title": "Test Title",
                "summary": "Test summary",
                "content": "Test content",
                "source_link": "http://test.com",
                "source_type": "test",
                "fetched_at": "2025-01-01",
                "published_at": "2025-01-01",
                "chunk": "This is chunk 2",
                "chunk_index": 1,
                "embedding": [0.2] * 768,
                "article_id": insert_test_article,
            },
        ])
        
        with DatabaseManager(db_url) as db:
            inserted = db.insert_chunks(df)
        
        assert inserted == 2
        
        # Verify in database
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT COUNT(*) FROM {} WHERE article_id = %s").format(
                sql.Identifier(vector_table)
            ),
            (insert_test_article,)
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        assert count == 2
    
    def test_mark_article_processed(self, db_url, articles_table, insert_test_article, clean_test_data):
        """Test DatabaseManager updates vflag to 1"""
        from loader_modular import DatabaseManager
        
        # Verify vflag starts at 0
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT vflag FROM {} WHERE article_id = %s").format(
                sql.Identifier(articles_table)
            ),
            (insert_test_article,)
        )
        assert cur.fetchone()[0] == 0
        cur.close()
        conn.close()
        
        # Mark as processed
        with DatabaseManager(db_url) as db:
            db.mark_article_processed(insert_test_article)
        
        # Verify vflag is now 1
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT vflag FROM {} WHERE article_id = %s").format(
                sql.Identifier(articles_table)
            ),
            (insert_test_article,)
        )
        assert cur.fetchone()[0] == 1
        cur.close()
        conn.close()


class TestChunkingIntegration:
    
    def test_chunking_creates_valid_chunks(self, db_url):
        """Test chunking strategies work with real text"""
        from loader_modular import RecursiveChunking
        
        chunker = RecursiveChunking(chunk_size=100, chunk_overlap=20)
        text = "This is a test paragraph. " * 20
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)
        assert all(len(c) <= 150 for c in chunks)  # Allow some overflow
        