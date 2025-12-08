import pytest
import psycopg
from psycopg import sql


class TestDatabaseConnection:

    def test_can_connect(self, db_url):
        conn = psycopg.connect(db_url)
        assert conn is not None
        conn.close()

    def test_pgvector_extension_exists(self, db_url):
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        result = cur.fetchone()
        
        assert result is not None
        cur.close()
        conn.close()


class TestArticlesTable:

    @pytest.fixture(autouse=True)
    def setup(self, db_url, articles_table):
        self.conn = psycopg.connect(db_url, autocommit=True)
        self.cur = self.conn.cursor()
        self.table = articles_table
        yield
        self.cur.execute(
            sql.SQL("DELETE FROM {} WHERE article_id LIKE 'test-%'").format(
                sql.Identifier(self.table)
            )
        )
        self.cur.close()
        self.conn.close()

    def test_insert_article(self, sample_article):
        self.cur.execute(
            sql.SQL("""
                INSERT INTO {} (article_id, title, author, content, source_link, source_type, vflag)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """).format(sql.Identifier(self.table)),
            (
                sample_article["article_id"],
                sample_article["title"],
                sample_article["author"],
                sample_article["content"],
                sample_article["source_link"],
                sample_article["source_type"],
                sample_article["vflag"],
            )
        )

        self.cur.execute(
            sql.SQL("SELECT * FROM {} WHERE article_id = %s").format(
                sql.Identifier(self.table)
            ),
            (sample_article["article_id"],)
        )
        result = self.cur.fetchone()

        assert result is not None
        