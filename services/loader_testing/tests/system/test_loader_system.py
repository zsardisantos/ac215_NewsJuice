# tests/system/test_loader_system.py
import pytest
import requests
import psycopg
from psycopg import sql
import os
from unittest.mock import patch, MagicMock


class TestLoaderSystem:
    """System-level tests - supports both real and mocked AI"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.base_url = os.environ.get("API_BASE_URL", "http://localhost:8080")
        self.db_url = os.environ["DATABASE_URL"]
        self.articles_table = os.environ.get("ARTICLES_TABLE_NAME", "articles_test")
        self.chunks_table = os.environ.get("VECTOR_TABLE_NAME", "chunks_vector_test")
        self.use_mocked_ai = os.environ.get("USE_MOCKED_AI", "false").lower() == "true"

        self.conn = psycopg.connect(self.db_url)
        self.cur = self.conn.cursor()

        yield

        self.cur.close()
        self.conn.close()

    def test_health_check(self):
        """Test 1: API health check"""
        response = requests.get(f"{self.base_url}/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        print("✓ Health check passed")

    def test_complete_workflow(self):
        """
        Test 2: Complete workflow
        Uses real or mocked AI depending on environment
        """
        test_article_id = "test_article_123"
        
        # Mock AI if needed
        if self.use_mocked_ai:
            with patch('api.loader.VertexEmbeddings') as mock_embeddings:
                mock_instance = MagicMock()
                mock_instance.embed_documents.return_value = [[0.1] * 768] * 4
                mock_embeddings.return_value = mock_instance
                self._run_workflow(test_article_id, mocked=True)
        else:
            self._run_workflow(test_article_id, mocked=False)

    def _run_workflow(self, test_article_id: str, mocked: bool):
        """Execute the workflow test"""
        # Insert test article
        self._insert_test_article(test_article_id)
        print(f"✓ Inserted test article: {test_article_id}")

        # Verify initial state
        initial_vflag = self._get_article_vflag(test_article_id)
        assert initial_vflag == 0
        print("✓ Verified article has vflag=0")

        # Process
        ai_type = "mocked" if mocked else "REAL Vertex AI"
        print(f"⏳ Processing with {ai_type}...")
        response = requests.post(f"{self.base_url}/process-sync")
        assert response.status_code == 200
        result = response.json()

        print(f"✓ API Response: {result}")
        assert result["status"] == "success"
        assert result["processed"] >= 1
        print(f"✓ Processing completed with {ai_type}")

        # Verify chunks
        chunk_count = self._count_chunks(test_article_id)
        assert chunk_count > 0
        print(f"✓ Created {chunk_count} chunks")

        # Verify vflag
        final_vflag = self._get_article_vflag(test_article_id)
        assert final_vflag == 1
        print("✓ Article marked as processed")

        # Cleanup
        self._cleanup_test_data(test_article_id)
        print("✓ Test data cleaned up")

    # ... (keep all your helper methods)
    def _insert_test_article(self, article_id: str):
        """Insert test article"""
        delete_sql = sql.SQL("DELETE FROM {} WHERE article_id = %s").format(
            sql.Identifier(self.articles_table)
        )
        self.cur.execute(delete_sql, (article_id,))

        insert_sql = sql.SQL("""
            INSERT INTO {} (
                article_id, author, title, summary, content,
                source_link, source_type, vflag
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """).format(sql.Identifier(self.articles_table))

        self.cur.execute(insert_sql, (
            article_id, "Test Author", "Test Article Title",
            "This is a test summary", "This is test content. " * 50,
            "https://test.com/article", "test", 0
        ))
        self.conn.commit()

    def _get_article_vflag(self, article_id: str) -> int:
        select_sql = sql.SQL("SELECT vflag FROM {} WHERE article_id = %s").format(
            sql.Identifier(self.articles_table)
        )
        self.cur.execute(select_sql, (article_id,))
        result = self.cur.fetchone()
        return result[0] if result else None

    def _count_chunks(self, article_id: str) -> int:
        count_sql = sql.SQL("SELECT COUNT(*) FROM {} WHERE article_id = %s").format(
            sql.Identifier(self.chunks_table)
        )
        self.cur.execute(count_sql, (article_id,))
        return self.cur.fetchone()[0]

    def _cleanup_test_data(self, article_id: str):
        delete_chunks = sql.SQL("DELETE FROM {} WHERE article_id = %s").format(
            sql.Identifier(self.chunks_table)
        )
        self.cur.execute(delete_chunks, (article_id,))

        delete_article = sql.SQL("DELETE FROM {} WHERE article_id = %s").format(
            sql.Identifier(self.articles_table)
        )
        self.cur.execute(delete_article, (article_id,))
        self.conn.commit()