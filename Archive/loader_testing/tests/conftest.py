import os
import pytest
from unittest.mock import MagicMock

# Set environment variables BEFORE any imports
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_REGION", "us-central1")


# Mock DB Connection globally to prevent hangs on localhost:5432
@pytest.fixture(autouse=True)
def mock_db_connection(monkeypatch):
    """
    Globally mock psycopg.connect to prevent tests from trying
    to connect to a non-existent database, which causes hangs.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Configure context managers
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.__enter__.return_value = mock_cursor

    # Mock psycopg.connect
    import psycopg

    monkeypatch.setattr(psycopg, "connect", MagicMock(return_value=mock_conn))

    return mock_conn
