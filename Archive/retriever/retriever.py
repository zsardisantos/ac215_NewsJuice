'''
Retriever service

Can be used in two ways:
1. Standalone: Asks for user input and retrieves 2 best articles
2. Importable: Provides search_articles() function for other services

Inputs:
- Runtime input from user (standalone mode)
- Query string parameter (function mode)

Outputs:
- ./artifacts/top-2.txt (standalone mode)
- List of article chunks (function mode)

NOTE: for testing use: #VECTOR_TABLE_NAME = "chunks_vector_test"
'''

VECTOR_TABLE_NAME = "chunks_vector"
#VECTOR_TABLE_NAME = "chunks_vector_test"

import psycopg
from pgvector.psycopg import register_vector, Vector
from psycopg import sql
import os
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Optional

# Configuration
DB_URL = os.environ["DATABASE_URL"]       
TIMEOUT = 10.0
USER_AGENT = "minimal-rag-ingest/0.1"

# Initialize model (this will be loaded once when module is imported)
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def get_db_connection():
    """Get a database connection with vector support."""
    conn = psycopg.connect(DB_URL, autocommit=True)
    register_vector(conn)
    return conn

def search_articles(query: str, limit: int = 2) -> List[Tuple[int, str, float]]:
    """
    Search for articles using semantic similarity.
    
    Args:
        query: The search query string
        limit: Maximum number of results to return (default: 2)
    
    Returns:
        List of tuples: (id, chunk, score) for each matching article
    """
    try:
        # Query embedding
        q = Vector(model.encode(query).tolist())
        
        with get_db_connection() as conn, conn.cursor() as cur:
            # Test database connection
            cur.execute("SELECT current_database(), version();")
            db_name, db_version = cur.fetchone()
            print(f"[retriever] Connected to '{db_name}'")
            
            # Search for similar chunks
            select_sql = sql.SQL("""
                SELECT id, chunk, embedding <=> %s AS score
                FROM {}
                ORDER BY embedding <=> %s
                LIMIT %s;
                """).format(sql.Identifier(VECTOR_TABLE_NAME))
            cur.execute(select_sql, (q, q, limit))
            
            results = cur.fetchall()
            print(f"[retriever] Found {len(results)} results for query: '{query[:50]}...'")
            return results
            
    except Exception as e:
        print(f"[retriever] Error searching articles: {e}")
        return []

# Retriever service is designed to be called by other services
# Use search_articles(query, limit) function directly
# No standalone mode - only function-based API

