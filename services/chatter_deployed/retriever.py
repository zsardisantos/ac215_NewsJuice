"""
==================
Retriever service (to be imported by main.py)
==================

In this version the embedding model is switched to
* text-embedding-004 from VertexAI
Changes are marked with "FE" and comments

Steps:
* get_db_connection
* embed the query
* search_articles in the vector database by similarity
* return chunks


NOTE: for testing use: #VECTOR_TABLE_NAME = "chunks_vector_test"
"""

import os
import psycopg
from pgvector.psycopg import register_vector, Vector
from psycopg import sql
from typing import List, Tuple

from google import genai
from google.genai import types
import logging

if os.path.exists(".env"):
    from dotenv import load_dotenv

    load_dotenv()


print(f"[retriever-debug] DATABASE_URL = {os.getenv('DATABASE_URL')}")

VECTOR_TABLE_NAME = "chunks_vector"
# VECTOR_TABLE_NAME = "chunks_vector_test"

# Configuration
# DB_URL = os.environ["DATABASE_URL"]
# DB_URL = os.environ.get("DATABASE_URL",
#    "postgresql://postgres:Newsjuice25+@/newsdb?host=/cloudsql/newsjuice-123456:
#                                                                   us-central1:newsdb-instance")
DB_URL = os.environ.get(
    "DATABASE_URL"
)  # [Z] for any script trying to access our GCP DB, assuming we have to specify the path
if not DB_URL:
    # Fallback for Cloud Run
    DB_URL = "postgresql://postgres:Newsjuice25+@/newsdb?host=/cloudsql/newsjuice-123456:" "us-central1:newsdb-instance"

TIMEOUT = 10.0
USER_AGENT = "minimal-rag-ingest/0.1"

# Initialize model (this will be loaded once when module is imported)
# model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
# model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")  # 768-D

# ======== FE 15-11-25 - Commented out: for embedding model switch========
# from sentence_transformers import SentenceTransformer
# MODEL_PATH = os.getenv("SENTENCE_MODEL_PATH", "sentence-transformers/all-mpnet-base-v2")
# model = SentenceTransformer(MODEL_PATH)  # loads local path baked into the image
# ======================================END

# ======== FE 15-11-25  - Added: Parameter for final embedding using Vertex AI
EMBEDDING_MODEL = "text-embedding-004"
# GENERATIVE_MODEL = "gemini-2.0-flash-001"
EMBEDDING_DIM = 768  # 256
# ======================================END

# ====FE 15-11-25 ADDED: embedding model switch
logger = logging.getLogger(__name__)


class VertexEmbeddings:
    def __init__(self):
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
        if not project:
            raise RuntimeError("Need to set GOOGLE_CLOUD_PROJECT")
        # Uses ADC via GOOGLE_APPLICATION_CREDENTIALS or gcloud
        self.client = genai.Client(vertexai=True, project=project, location=location)
        self.model = EMBEDDING_MODEL  # [Z] initialize  model, text-embedding-004 from VertexAI
        self.dim = EMBEDDING_DIM  # [Z] embedding dim is 768
        # ============== CHANGE 2: LOG INITIALIZATION ==============
        logger.info(
            f"""VertexEmbeddings initialized - Project: {project}, Location: {location},
            Model: {self.model}, Dim: {self.dim}"""
        )
        # ==========================================================

    def _embed_one(self, text: str) -> List[float]:
        resp = self.client.models.embed_content(
            model=self.model,
            contents=[text],  # one at a time to avoid 20k token limit
            config=types.EmbedContentConfig(output_dimensionality=self.dim),
        )
        return resp.embeddings[0].values

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_one(text)


# ==========END


# model = SentenceTransformer("all-MiniLM-L6-v2") # 384 D


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

        # ======= FE 15-11-25 Added: for new emnbedding model
        vertex_embedder = VertexEmbeddings()
        # ============END

        # ======= FE 15-11-25 Commented out: for new emnbedding model
        # q = Vector(model.encode(query).tolist())
        # ==============END

        # ======= FE 15-11-25 Added: for new emnbedding model
        # q = vertex_embedder.embed_documents(query.tolist())
        q = Vector(vertex_embedder.embed_query(query))
        # ========END

        with get_db_connection() as conn, conn.cursor() as cur:
            # Test database connection
            cur.execute("SELECT current_database(), version();")
            db_name, db_version = cur.fetchone()
            print(f"[retriever] Connected to '{db_name}'")

            # Search for similar chunks
            select_sql = sql.SQL(
                """
                SELECT id, chunk, embedding <=> %s AS score
                FROM {}
                ORDER BY embedding <=> %s
                LIMIT %s;
                """
            ).format(sql.Identifier(VECTOR_TABLE_NAME))
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
