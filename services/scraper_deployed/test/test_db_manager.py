import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_manager import PostgresDBManager  # noqa: E402


@pytest.fixture
def mock_env():
    """Mock environment variable for DATABASE_URL."""
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost:5432/testdb"}):
        yield


@pytest.fixture
def db_manager(mock_env):
    """Provides a PostgresDBManager instance with mocked environment."""
    return PostgresDBManager(url_column="source_link")


class TestPostgresDBManager:

    def test_init_with_env_var(self, mock_env):
        """Test initialization with DATABASE_URL environment variable."""
        manager = PostgresDBManager(url_column="article_url")
        assert manager._dsn == "postgresql://test:test@localhost:5432/testdb"
        assert manager._table_name == "articles"
        assert manager._url_column == "article_url"

    def test_init_without_env_var(self):
        """Test initialization fails without DATABASE_URL."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="Postgres DSN not provided"):
                PostgresDBManager(url_column="source_link")

    @patch("db_manager.psycopg.connect")
    def test_filter_new_urls_empty_list(self, mock_connect, db_manager):
        """Test filter_new_urls with empty list."""
        result = db_manager.filter_new_urls([])
        assert result == []
        mock_connect.assert_not_called()

    @patch("db_manager.psycopg.connect")
    def test_filter_new_urls_all_new(self, mock_connect, db_manager):
        """Test filter_new_urls when all URLs are new."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        urls = ["https://example.com/1", "https://example.com/2"]
        result = db_manager.filter_new_urls(urls)

        assert result == urls
        mock_cursor.execute.assert_called_once()

    @patch("db_manager.psycopg.connect")
    def test_filter_new_urls_some_existing(self, mock_connect, db_manager):
        """Test filter_new_urls when some URLs already exist."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("https://example.com/1",)]
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        result = db_manager.filter_new_urls(urls)

        assert result == ["https://example.com/2", "https://example.com/3"]

    @patch("db_manager.psycopg.connect")
    def test_filter_new_urls_removes_duplicates(self, mock_connect, db_manager):
        """Test filter_new_urls removes duplicate URLs while preserving order."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/1"]
        result = db_manager.filter_new_urls(urls)

        # Should preserve first occurrence and remove duplicates
        assert result == ["https://example.com/1", "https://example.com/2"]

    @patch("db_manager.psycopg.connect")
    def test_insert_records_empty_list(self, mock_connect, db_manager):
        """Test insert_records with empty list."""
        result = db_manager.insert_records([])
        assert result == 0
        mock_connect.assert_not_called()

    @patch("db_manager.psycopg.connect")
    def test_insert_records_success(self, mock_connect, db_manager):
        """Test successful insertion of new records."""
        # Mock filter_new_urls to return all URLs as new
        with patch.object(
            db_manager,
            "filter_new_urls",
            return_value=["https://example.com/1", "https://example.com/2"],
        ):
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn = MagicMock()
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            records = [
                {
                    "source_link": "https://example.com/1",
                    "title": "Article 1",
                    "content": "Content 1",
                },
                {
                    "source_link": "https://example.com/2",
                    "title": "Article 2",
                    "content": "Content 2",
                },
            ]
            result = db_manager.insert_records(records)

            assert result == 2
            assert mock_cursor.execute.call_count == 2

    @patch("db_manager.psycopg.connect")
    def test_insert_records_missing_url_field(self, mock_connect, db_manager):
        """Test insert_records raises KeyError when URL field is missing."""
        records = [{"title": "Article 1", "content": "Content 1"}]
        with pytest.raises(KeyError, match="Record missing required URL field"):
            db_manager.insert_records(records)

    @patch("db_manager.psycopg.connect")
    def test_insert_records_inconsistent_columns(self, mock_connect, db_manager):
        """Test insert_records raises ValueError when records have different columns."""
        with patch.object(
            db_manager,
            "filter_new_urls",
            return_value=["https://example.com/1", "https://example.com/2"],
        ):
            records = [
                {"source_link": "https://example.com/1", "title": "Article 1"},
                {
                    "source_link": "https://example.com/2",
                    "title": "Article 2",
                    "content": "Content 2",
                },
            ]
            with pytest.raises(ValueError, match="All records must contain the same columns"):
                db_manager.insert_records(records)

    @patch("db_manager.psycopg.connect")
    def test_insert_records_filters_existing(self, mock_connect, db_manager):
        """Test insert_records filters out existing URLs."""
        # Mock filter_new_urls to return only one URL as new
        with patch.object(db_manager, "filter_new_urls", return_value=["https://example.com/2"]):
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn = MagicMock()
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            records = [
                {"source_link": "https://example.com/1", "title": "Article 1"},
                {"source_link": "https://example.com/2", "title": "Article 2"},
            ]
            result = db_manager.insert_records(records)

            assert result == 1
            assert mock_cursor.execute.call_count == 1

    @patch("db_manager.psycopg.connect")
    def test_fetch_articles_without_summary_no_limit(self, mock_connect, db_manager):
        """Test fetching articles without summary with no limit."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, "art1", "Title 1", "Content 1"),
            (2, "art2", "Title 2", "Content 2"),
        ]
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = db_manager.fetch_articles_without_summary()

        assert len(result) == 2
        assert result[0] == {
            "id": 1,
            "article_id": "art1",
            "title": "Title 1",
            "content": "Content 1",
        }
        assert result[1] == {
            "id": 2,
            "article_id": "art2",
            "title": "Title 2",
            "content": "Content 2",
        }

    @patch("db_manager.psycopg.connect")
    def test_fetch_articles_without_summary_with_limit(self, mock_connect, db_manager):
        """Test fetching articles without summary with a limit."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, "art1", "Title 1", "Content 1")]
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = db_manager.fetch_articles_without_summary(limit=1)

        assert len(result) == 1
        # Verify that execute was called with limit parameter
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == (1,)

    @patch("db_manager.psycopg.connect")
    def test_fetch_articles_without_summary_empty(self, mock_connect, db_manager):
        """Test fetching articles when none are missing summaries."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = db_manager.fetch_articles_without_summary()

        assert result == []

    @patch("db_manager.psycopg.connect")
    def test_update_article_summary_success(self, mock_connect, db_manager):
        """Test successful update of article summary."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = db_manager.update_article_summary("art123", "This is a summary")

        assert result == 1
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("db_manager.psycopg.connect")
    def test_update_article_summary_no_match(self, mock_connect, db_manager):
        """Test update when article_id doesn't exist."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = db_manager.update_article_summary("nonexistent", "Summary")

        assert result == 0
        mock_conn.commit.assert_called_once()
