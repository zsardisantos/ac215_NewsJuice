# services/loader_faster/tests/unit/test_database_manager.py

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def mock_db_url(monkeypatch):
    # Ensure DATABASE_URL exists whenever loader is imported
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")


def test_database_manager_fetch_insert_and_mark(monkeypatch):
    from api import loader as loader_mod

    # --- Fake psycopg connection & cursor ---------------------------------
    fake_rows = [
        (
            1,                    # id
            "Author",             # author
            "Title",              # title
            "Summary",            # summary
            "Content",            # content
            "http://example.com", # source_link
            "rss",                # source_type
            "fetched",            # fetched_at
            "published",          # published_at
            0,                    # vflag
            "article-1",          # article_id
        )
    ]

    class FakeCursor:
        def __init__(self, rows):
            self.rows = rows
            self.executed = []

        def execute(self, sql, params=None):
            # Just remember what was executed
            self.executed.append((sql, params))

        def fetchall(self):
            return self.rows

        def close(self):
            pass

    class FakeConn:
        def __init__(self, *args, **kwargs):
            self.cursor_obj = FakeCursor(fake_rows)
            self.closed = False

        def cursor(self):
            return self.cursor_obj

        def close(self):
            self.closed = True

    def fake_connect(dsn, autocommit=True):
        # Mimic psycopg.connect
        return FakeConn()

    # Patch psycopg.connect and register_vector inside loader module
    monkeypatch.setattr(loader_mod.psycopg, "connect", fake_connect)
    monkeypatch.setattr(loader_mod, "register_vector", lambda conn: None)

    # --- Use DatabaseManager with our fake connection ----------------------
    with loader_mod.DatabaseManager("postgresql://fake") as db:
        # fetch_unprocessed_articles
        articles = db.fetch_unprocessed_articles()
        assert len(articles) == 1
        assert isinstance(articles[0], loader_mod.Article)
        assert articles[0].article_id == "article-1"

        # Prepare a simple chunks DataFrame for insert_chunks
        df = pd.DataFrame(
            [
                {
                    "author": "Author",
                    "title": "Title",
                    "summary": "Summary",
                    "content": "Content",
                    "source_link": "http://example.com",
                    "source_type": "rss",
                    "fetched_at": "fetched",
                    "published_at": "published",
                    "chunk": "chunk-1",
                    "chunk_index": 0,
                    "embedding": [0.1, 0.2, 0.3],
                    "article_id": "article-1",
                }
            ]
        )

        inserted = db.insert_chunks(df)
        assert inserted == 1  # one row inserted

        # mark_article_processed
        db.mark_article_processed("article-1")

        fake_cursor = db.cur
        # We expect at least one INSERT and one UPDATE
        executed_sqls = fake_cursor.executed
        assert any("UPDATE" in str(sql) for sql, _ in executed_sqls)
        assert any("INSERT" in str(sql) for sql, _ in executed_sqls)
