import os
import pytest
import psycopg

# Adjust path if needed to import from sibling directory or ensure pythonpath is set
from db_manager import PostgresDBManager


@pytest.mark.integration
class TestDBManagerIntegration:

    @pytest.fixture(scope="class")
    def db_url(self):
        """Ensure we have a database URL for testing."""
        url = os.environ.get("DATABASE_URL")
        if not url:
            pytest.fail("DATABASE_URL environment variable not set for integration tests.")
        return url

    @pytest.fixture(autouse=True)
    def clean_db(self, db_url):
        """Clean up the articles table before and after each test."""
        # Clean before
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE articles RESTART IDENTITY CASCADE;")

        yield

        # Clean after (optional, but good practice)
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE articles RESTART IDENTITY CASCADE;")

    def test_insert_and_filter(self, db_url):
        """Test full flow: Insert records -> Check existence -> Filter duplicates."""
        # The schema uses 'source_link' for the URL, so we must use that here.
        manager = PostgresDBManager(url_column="source_link")

        # 1. Define test records
        # Must match the columns in 'articles' table in init_test_db.sql
        record1 = {
            "source_link": "http://example.com/1",
            "article_id": "test-id-1",
            "source_type": "Integration Test",
            "title": "Title 1",
            "published_at": "2023-01-01T12:00:00Z",
            "fetched_at": "2023-01-01T12:00:00Z",
        }
        record2 = {
            "source_link": "http://example.com/2",
            "article_id": "test-id-2",
            "source_type": "Integration Test",
            "title": "Title 2",
            "published_at": "2023-01-01T13:00:00Z",
            "fetched_at": "2023-01-01T13:00:00Z",
        }

        # 2. Insert first batch
        count = manager.insert_records([record1])
        assert count == 1, "Should insert 1 new record"

        # Verify insertion
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT source_link FROM articles WHERE source_link = %s", (record1["source_link"],))
                result = cur.fetchone()
                assert result is not None
                assert result[0] == record1["source_link"]

        # 3. Test filter logic directly
        # Should only return the URL for record2, because record1 is already in DB
        new_urls = manager.filter_new_urls([record1["source_link"], record2["source_link"]])
        assert len(new_urls) == 1
        assert new_urls[0] == record2["source_link"]

        # 4. Attempt to insert both again via insert_records
        # internal logic should filter out record1 and only insert record2
        count_2 = manager.insert_records([record1, record2])
        assert count_2 == 1, "Should filter out the duplicate and insert only the new one"

        # Final count check
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM articles")
                total = cur.fetchone()[0]
                assert total == 2
