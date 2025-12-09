"""
Unit tests for retriever.py - Vector search and article retrieval.
Target: 50%+ code coverage
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import List

# Set environment variables BEFORE any imports
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/testdb"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
os.environ["GOOGLE_CLOUD_REGION"] = "us-central1"

# Mock external dependencies before importing
sys.modules['psycopg'] = MagicMock()
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.psycopg'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


@pytest.fixture
def mock_vertex_embedder():
    """Mock VertexEmbeddings class."""
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 768
    mock_embedder.embed_documents.return_value = [[0.1] * 768]
    return mock_embedder


@pytest.fixture
def sample_search_results():
    """Sample search results from database."""
    return [
        (1, "Harvard announced new research funding for climate science.", "Harvard Gazette", 0.15),
        (2, "The university president spoke about campus sustainability.", "Harvard Crimson", 0.22),
        (3, "Budget allocations for next fiscal year revealed.", "Harvard Magazine", 0.28),
    ]


# ============================================================
# TESTS: VertexEmbeddings Class
# ============================================================

class TestVertexEmbeddings:
    """Tests for VertexEmbeddings class."""

    def test_vertex_embeddings_init_success(self):
        """Test successful VertexEmbeddings initialization."""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "GOOGLE_CLOUD_REGION": "us-central1"
        }):
            with patch('retriever.genai') as mock_genai:
                mock_client = MagicMock()
                mock_genai.Client.return_value = mock_client
                
                from retriever import VertexEmbeddings
                
                embedder = VertexEmbeddings()
                
                assert embedder.model == "text-embedding-004"
                assert embedder.dim == 768
                mock_genai.Client.assert_called_once()

    def test_vertex_embeddings_init_no_project(self):
        """Test VertexEmbeddings initialization without project."""
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": ""}, clear=False):
            # Remove GOOGLE_CLOUD_PROJECT
            env_backup = os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
            
            try:
                # Need to reload module to test initialization
                with pytest.raises(RuntimeError, match="Need to set GOOGLE_CLOUD_PROJECT"):
                    # Force reimport
                    if 'retriever' in sys.modules:
                        del sys.modules['retriever']
                    
                    with patch('retriever.genai'):
                        from retriever import VertexEmbeddings
                        VertexEmbeddings()
            finally:
                if env_backup:
                    os.environ["GOOGLE_CLOUD_PROJECT"] = env_backup

    def test_embed_query(self, mock_vertex_embedder):
        """Test embedding a single query."""
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch('retriever.genai') as mock_genai:
                mock_response = MagicMock()
                mock_embedding = MagicMock()
                mock_embedding.values = [0.1] * 768
                mock_response.embeddings = [mock_embedding]
                
                mock_client = MagicMock()
                mock_client.models.embed_content.return_value = mock_response
                mock_genai.Client.return_value = mock_client
                
                from retriever import VertexEmbeddings
                
                embedder = VertexEmbeddings()
                result = embedder.embed_query("test query")
                
                assert len(result) == 768
                mock_client.models.embed_content.assert_called_once()

    def test_embed_documents(self, mock_vertex_embedder):
        """Test embedding multiple documents."""
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch('retriever.genai') as mock_genai:
                mock_response = MagicMock()
                mock_embedding = MagicMock()
                mock_embedding.values = [0.1] * 768
                mock_response.embeddings = [mock_embedding]
                
                mock_client = MagicMock()
                mock_client.models.embed_content.return_value = mock_response
                mock_genai.Client.return_value = mock_client
                
                from retriever import VertexEmbeddings
                
                embedder = VertexEmbeddings()
                result = embedder.embed_documents(["doc1", "doc2", "doc3"])
                
                assert len(result) == 3
                assert all(len(emb) == 768 for emb in result)


# ============================================================
# TESTS: get_db_connection
# ============================================================

class TestGetDbConnection:
    """Tests for get_db_connection function."""

    def test_get_db_connection_success(self):
        """Test successful database connection."""
        with patch('retriever.psycopg') as mock_psycopg:
            with patch('retriever.register_vector') as mock_register:
                mock_conn = MagicMock()
                mock_psycopg.connect.return_value = mock_conn
                
                from retriever import get_db_connection
                
                conn = get_db_connection()
                
                mock_psycopg.connect.assert_called_once()
                mock_register.assert_called_once_with(mock_conn)
                assert conn == mock_conn

    def test_get_db_connection_failure(self):
        """Test database connection failure."""
        with patch('retriever.psycopg') as mock_psycopg:
            mock_psycopg.connect.side_effect = Exception("Connection failed")
            
            from retriever import get_db_connection
            
            with pytest.raises(Exception, match="Connection failed"):
                get_db_connection()


# ============================================================
# TESTS: search_articles
# ============================================================

class TestSearchArticles:
    """Tests for search_articles function."""

    def test_search_articles_success(self, sample_search_results):
        """Test successful article search."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.get_db_connection') as mock_get_conn:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = ("testdb", "PostgreSQL 15")
                mock_cursor.fetchall.return_value = sample_search_results
                
                mock_conn = MagicMock()
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_conn.__enter__ = MagicMock(return_value=mock_conn)
                mock_conn.__exit__ = MagicMock(return_value=False)
                
                mock_get_conn.return_value = mock_conn
                
                with patch('retriever.Vector') as mock_vector:
                    mock_vector.return_value = MagicMock()
                    
                    from retriever import search_articles
                    
                    results = search_articles("Harvard research funding", limit=10)
                    
                    assert len(results) == 3
                    assert results[0][0] == 1  # id
                    assert "research funding" in results[0][1]  # chunk
                    assert results[0][2] == "Harvard Gazette"  # source_type

    def test_search_articles_empty_results(self):
        """Test search with no results."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.get_db_connection') as mock_get_conn:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = ("testdb", "PostgreSQL 15")
                mock_cursor.fetchall.return_value = []
                
                mock_conn = MagicMock()
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_conn.__enter__ = MagicMock(return_value=mock_conn)
                mock_conn.__exit__ = MagicMock(return_value=False)
                
                mock_get_conn.return_value = mock_conn
                
                with patch('retriever.Vector'):
                    from retriever import search_articles
                    
                    results = search_articles("nonexistent topic xyz")
                    
                    assert results == []

    def test_search_articles_database_error(self):
        """Test search with database error."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.get_db_connection') as mock_get_conn:
                mock_get_conn.side_effect = Exception("Database connection failed")
                
                with patch('retriever.Vector'):
                    from retriever import search_articles
                    
                    results = search_articles("test query")
                    
                    # Should return empty list on error
                    assert results == []

    def test_search_articles_embedding_error(self):
        """Test search with embedding error."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder_class.side_effect = Exception("Embedding service unavailable")
            
            from retriever import search_articles
            
            results = search_articles("test query")
            
            # Should return empty list on error
            assert results == []

    def test_search_articles_custom_limit(self, sample_search_results):
        """Test search with custom limit."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.get_db_connection') as mock_get_conn:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = ("testdb", "PostgreSQL 15")
                mock_cursor.fetchall.return_value = sample_search_results[:2]  # Only 2 results
                
                mock_conn = MagicMock()
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_conn.__enter__ = MagicMock(return_value=mock_conn)
                mock_conn.__exit__ = MagicMock(return_value=False)
                
                mock_get_conn.return_value = mock_conn
                
                with patch('retriever.Vector'):
                    from retriever import search_articles
                    
                    results = search_articles("test query", limit=2)
                    
                    assert len(results) == 2


# ============================================================
# TESTS: search_articles_by_preferences
# ============================================================

class TestSearchArticlesByPreferences:
    """Tests for search_articles_by_preferences function."""

    def test_search_by_preferences_success(self, sample_search_results):
        """Test successful search by preferences."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.psycopg') as mock_psycopg:
                with patch('retriever.register_vector'):
                    mock_cursor = MagicMock()
                    mock_cursor.fetchall.return_value = sample_search_results
                    
                    mock_conn = MagicMock()
                    mock_conn.cursor.return_value = mock_cursor
                    mock_psycopg.connect.return_value = mock_conn
                    
                    with patch('retriever.Vector'):
                        from retriever import search_articles_by_preferences
                        
                        results = search_articles_by_preferences(
                            topics=["Politics", "Technology"],
                            sources=["Harvard Gazette", "Harvard Crimson"],
                            limit=30,
                            days_back=2
                        )
                        
                        assert len(results) == 3
                        mock_cursor.execute.assert_called_once()

    def test_search_by_preferences_empty_topics(self):
        """Test search with empty topics."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.psycopg') as mock_psycopg:
                with patch('retriever.register_vector'):
                    mock_cursor = MagicMock()
                    mock_cursor.fetchall.return_value = []
                    
                    mock_conn = MagicMock()
                    mock_conn.cursor.return_value = mock_cursor
                    mock_psycopg.connect.return_value = mock_conn
                    
                    with patch('retriever.Vector'):
                        from retriever import search_articles_by_preferences
                        
                        results = search_articles_by_preferences(
                            topics=[],
                            sources=["Harvard Gazette"],
                            limit=30,
                            days_back=2
                        )
                        
                        # Should still execute but may return empty
                        assert isinstance(results, list)

    def test_search_by_preferences_database_error(self):
        """Test search by preferences with database error."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.psycopg') as mock_psycopg:
                mock_psycopg.connect.side_effect = Exception("Database error")
                
                with patch('retriever.Vector'):
                    from retriever import search_articles_by_preferences
                    
                    results = search_articles_by_preferences(
                        topics=["Politics"],
                        sources=["Harvard Gazette"],
                        limit=30,
                        days_back=2
                    )
                    
                    # Should return empty list on error
                    assert results == []

    def test_search_by_preferences_single_topic(self, sample_search_results):
        """Test search with single topic."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.psycopg') as mock_psycopg:
                with patch('retriever.register_vector'):
                    mock_cursor = MagicMock()
                    mock_cursor.fetchall.return_value = sample_search_results[:1]
                    
                    mock_conn = MagicMock()
                    mock_conn.cursor.return_value = mock_cursor
                    mock_psycopg.connect.return_value = mock_conn
                    
                    with patch('retriever.Vector'):
                        from retriever import search_articles_by_preferences
                        
                        results = search_articles_by_preferences(
                            topics=["Politics"],
                            sources=["Harvard Gazette"],
                            limit=10,
                            days_back=1
                        )
                        
                        assert len(results) == 1

    def test_search_by_preferences_multiple_sources(self, sample_search_results):
        """Test search with multiple sources."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.psycopg') as mock_psycopg:
                with patch('retriever.register_vector'):
                    mock_cursor = MagicMock()
                    mock_cursor.fetchall.return_value = sample_search_results
                    
                    mock_conn = MagicMock()
                    mock_conn.cursor.return_value = mock_cursor
                    mock_psycopg.connect.return_value = mock_conn
                    
                    with patch('retriever.Vector'):
                        from retriever import search_articles_by_preferences
                        
                        results = search_articles_by_preferences(
                            topics=["Technology"],
                            sources=["Harvard Gazette", "Harvard Crimson", "Harvard Magazine"],
                            limit=30,
                            days_back=2
                        )
                        
                        assert len(results) == 3


# ============================================================
# TESTS: Module-level Configuration
# ============================================================

class TestModuleConfiguration:
    """Tests for module-level configuration."""

    def test_vector_table_name(self):
        """Test that VECTOR_TABLE_NAME is set correctly."""
        from retriever import VECTOR_TABLE_NAME
        
        assert VECTOR_TABLE_NAME == "chunks_vector"

    def test_embedding_model_config(self):
        """Test embedding model configuration."""
        from retriever import EMBEDDING_MODEL, EMBEDDING_DIM
        
        assert EMBEDDING_MODEL == "text-embedding-004"
        assert EMBEDDING_DIM == 768

    def test_db_url_fallback(self):
        """Test DATABASE_URL fallback."""
        # The module should have a fallback DB_URL
        from retriever import DB_URL
        
        assert DB_URL is not None
        assert "postgresql" in DB_URL


# ============================================================
# TESTS: Edge Cases
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_search_articles_empty_query(self):
        """Test search with empty query string."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.get_db_connection') as mock_get_conn:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = ("testdb", "PostgreSQL 15")
                mock_cursor.fetchall.return_value = []
                
                mock_conn = MagicMock()
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_conn.__enter__ = MagicMock(return_value=mock_conn)
                mock_conn.__exit__ = MagicMock(return_value=False)
                
                mock_get_conn.return_value = mock_conn
                
                with patch('retriever.Vector'):
                    from retriever import search_articles
                    
                    results = search_articles("")
                    
                    # Should handle empty query gracefully
                    assert isinstance(results, list)

    def test_search_articles_special_characters(self):
        """Test search with special characters in query."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.get_db_connection') as mock_get_conn:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = ("testdb", "PostgreSQL 15")
                mock_cursor.fetchall.return_value = []
                
                mock_conn = MagicMock()
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_conn.__enter__ = MagicMock(return_value=mock_conn)
                mock_conn.__exit__ = MagicMock(return_value=False)
                
                mock_get_conn.return_value = mock_conn
                
                with patch('retriever.Vector'):
                    from retriever import search_articles
                    
                    # Query with special characters
                    results = search_articles("What's Harvard's plan for $100M?")
                    
                    assert isinstance(results, list)

    def test_search_articles_unicode_query(self):
        """Test search with unicode characters."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.get_db_connection') as mock_get_conn:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = ("testdb", "PostgreSQL 15")
                mock_cursor.fetchall.return_value = []
                
                mock_conn = MagicMock()
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_conn.__enter__ = MagicMock(return_value=mock_conn)
                mock_conn.__exit__ = MagicMock(return_value=False)
                
                mock_get_conn.return_value = mock_conn
                
                with patch('retriever.Vector'):
                    from retriever import search_articles
                    
                    # Query with unicode
                    results = search_articles("研究资金 Harvard")
                    
                    assert isinstance(results, list)

    def test_search_by_preferences_large_limit(self, sample_search_results):
        """Test search with large limit value."""
        with patch('retriever.VertexEmbeddings') as mock_embedder_class:
            mock_embedder = MagicMock()
            mock_embedder.embed_query.return_value = [0.1] * 768
            mock_embedder_class.return_value = mock_embedder
            
            with patch('retriever.psycopg') as mock_psycopg:
                with patch('retriever.register_vector'):
                    mock_cursor = MagicMock()
                    mock_cursor.fetchall.return_value = sample_search_results
                    
                    mock_conn = MagicMock()
                    mock_conn.cursor.return_value = mock_cursor
                    mock_psycopg.connect.return_value = mock_conn
                    
                    with patch('retriever.Vector'):
                        from retriever import search_articles_by_preferences
                        
                        results = search_articles_by_preferences(
                            topics=["Politics"],
                            sources=["Harvard Gazette"],
                            limit=1000,  # Large limit
                            days_back=30
                        )
                        
                        assert isinstance(results, list)
