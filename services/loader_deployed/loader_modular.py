"""
===============
loader service
===============
Modular version with separated concerns
"""

import os
import pandas as pd
import psycopg
from psycopg import sql
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import logging
from dataclasses import dataclass

# Vertex AI
from google import genai
from google.genai import types

# Langchain
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from pgvector.psycopg import register_vector

logger = logging.getLogger(__name__)

# ============= CONFIGURATION =============
ARTICLES_TABLE_NAME = os.environ.get("ARTICLES_TABLE_NAME", "articles")
VECTOR_TABLE_NAME = os.environ.get("VECTOR_TABLE_NAME", "chunks_vector")
DB_URL = os.environ["DATABASE_URL"]
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768

# Character chunking settings
CHUNK_SIZE_CHAR = 350
CHUNK_OVERLAP_CHAR = 20

# Recursive chunking settings
CHUNK_SIZE_RECURSIVE = 600
CHUNK_OVERLAP_RECURSIVE = 50
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]


# ============= DATA CLASSES =============
@dataclass
class Article:
    """Represents an article from the database"""

    id: int
    author: Optional[str]
    title: Optional[str]
    summary: Optional[str]
    content: Optional[str]
    source_link: Optional[str]
    source_type: Optional[str]
    fetched_at: Any
    published_at: Any
    vflag: int
    article_id: str


@dataclass
class ProcessingResult:
    """Result of processing operation"""

    status: str
    message: str
    processed: int
    total_found: int = 0


# ============= EMBEDDINGS CLASS =============
class VertexEmbeddings:
    """Wrapper for Vertex AI embeddings"""

    def __init__(self):
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

        if not project:
            raise RuntimeError("Need to set GOOGLE_CLOUD_PROJECT")

        self.client = genai.Client(vertexai=True, project=project, location=location)
        self.model = EMBEDDING_MODEL
        self.dim = EMBEDDING_DIM

        logger.info(
            f"VertexEmbeddings initialized - Project: {project}, "
            f"Location: {location}, Model: {self.model}, Dim: {self.dim}"
        )

    def _embed_one(self, text: str) -> List[float]:
        """Embed a single text"""
        resp = self.client.models.embed_content(
            model=self.model,
            contents=[text],
            config=types.EmbedContentConfig(output_dimensionality=self.dim),
        )
        return resp.embeddings[0].values

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents"""
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        """Embed a query text"""
        return self._embed_one(text)


# ============= DATABASE OPERATIONS =============
class DatabaseManager:
    """Handles all database operations"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None
        self.cur = None

    def __enter__(self):
        """Context manager entry"""
        self.conn = psycopg.connect(self.db_url, autocommit=True)
        register_vector(self.conn)
        self.cur = self.conn.cursor()
        logger.info("Connected to database")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

    def fetch_unprocessed_articles(self) -> List[Article]:
        """Fetch articles with vflag = 0"""
        self.cur.execute(
            sql.SQL(
                """
                SELECT id, author, title, summary, content,
                    source_link, source_type, fetched_at, published_at,
                    vflag, article_id
                FROM {}
                WHERE vflag = 0;
            """
            ).format(sql.Identifier(ARTICLES_TABLE_NAME))
        )

        rows = self.cur.fetchall()
        logger.info(f"Fetched {len(rows)} articles with vflag=0")

        return [Article(*row) for row in rows]

    def insert_chunks(self, chunks_df: pd.DataFrame) -> int:
        """Insert chunks into vector table"""
        insert_sql = sql.SQL(
            """
            INSERT INTO {} (
                author, title, summary, content,
                source_link, source_type, fetched_at, published_at,
                chunk, chunk_index, embedding, article_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        ).format(sql.Identifier(VECTOR_TABLE_NAME))

        inserted = 0
        for _, row in chunks_df.iterrows():
            self.cur.execute(
                insert_sql,
                (
                    row["author"],
                    row["title"],
                    row["summary"],
                    row["content"],
                    row["source_link"],
                    row["source_type"],
                    row["fetched_at"],
                    row["published_at"],
                    row["chunk"],
                    int(row["chunk_index"]),
                    row["embedding"],
                    row["article_id"],
                ),
            )
            inserted += 1

        return inserted

    def mark_article_processed(self, article_id: str) -> None:
        """Update article vflag to 1"""
        update_sql = sql.SQL(
            """
            UPDATE {} 
            SET vflag = 1 
            WHERE article_id = %s
        """
        ).format(sql.Identifier(ARTICLES_TABLE_NAME))

        self.cur.execute(update_sql, (article_id,))
        logger.info(f"Updated vflag=1 for article_id={article_id}")


# ============= CHUNKING STRATEGIES =============
class ChunkingStrategy:
    """Base class for chunking strategies"""

    def chunk_text(self, text: str) -> List[str]:
        """Override in subclasses"""
        raise NotImplementedError


class CharacterChunking(ChunkingStrategy):
    """Character-based text splitting"""

    def __init__(
        self, chunk_size: int = CHUNK_SIZE_CHAR, chunk_overlap: int = CHUNK_OVERLAP_CHAR
    ):
        self.splitter = CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=None,
            strip_whitespace=False,
        )

    def chunk_text(self, text: str) -> List[str]:
        docs = self.splitter.create_documents([text or ""])
        return [d.page_content for d in docs]


class RecursiveChunking(ChunkingStrategy):
    """Recursive text splitting"""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE_RECURSIVE,
        chunk_overlap: int = CHUNK_OVERLAP_RECURSIVE,
        separators: List[str] = None,
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators or CHUNK_SEPARATORS,
        )

    def chunk_text(self, text: str) -> List[str]:
        docs = self.splitter.create_documents([text or ""])
        return [d.page_content for d in docs]


# ============= CHUNKING FACTORY =============
def get_chunking_strategy(
    method: str, embeddings: Optional[VertexEmbeddings] = None
) -> ChunkingStrategy:
    """Factory function to get the appropriate chunking strategy"""
    strategies = {
        "char-split": CharacterChunking,
        "recursive-split": RecursiveChunking,
    }

    if method in strategies:
        return strategies[method]()
    else:
        raise ValueError(f"Unknown chunking method: {method}")


# ============= ARTICLE PROCESSOR =============
class ArticleProcessor:
    """Processes individual articles"""

    def __init__(self, chunking_strategy: ChunkingStrategy, embedder: VertexEmbeddings):
        self.chunking_strategy = chunking_strategy
        self.embedder = embedder

    def process_article(
        self, article: Article, article_num: int, total: int
    ) -> pd.DataFrame:
        """Process a single article into chunks with embeddings"""
        import time

        article_start = time.time()

        logger.info(
            f"[{article_num}/{total}] Processing article_id={article.article_id}, "
            f"title='{(article.title or 'N/A')[:50]}...'"
        )

        # Chunk the article
        text_chunks = self.chunking_strategy.chunk_text(article.content)
        logger.info(
            f"[{article_num}/{total}] Created {len(text_chunks)} chunks "
            f"for article_id={article.article_id}"
        )

        # Create DataFrame
        df = self._create_chunks_dataframe(article, text_chunks)

        # Generate embeddings
        logger.info(f"[{article_num}/{total}] Starting embedding for {len(df)} chunks")
        df["embedding"] = self.embedder.embed_documents(df["chunk"].tolist())
        logger.info(f"[{article_num}/{total}] Embedding completed")

        # Log timing
        article_time = time.time() - article_start
        logger.info(
            f"[{article_num}/{total}] ✓ Article {article.article_id} "
            f"completed in {article_time:.2f}s"
        )

        return df

    def _create_chunks_dataframe(
        self, article: Article, chunks: List[str]
    ) -> pd.DataFrame:
        """Create DataFrame from article and chunks"""
        df = pd.DataFrame(chunks, columns=["chunk"])
        df["author"] = article.author
        df["title"] = article.title
        df["summary"] = article.summary
        df["content"] = article.content
        df["source_link"] = article.source_link
        df["source_type"] = article.source_type
        df["fetched_at"] = article.fetched_at
        df["published_at"] = article.published_at
        df["chunk_index"] = range(len(df))
        df["article_id"] = article.article_id
        return df


# ============= MAIN ORCHESTRATOR =============
def chunk_embed_load(method: str = "char-split") -> Dict[str, Any]:
    """
    Main orchestration function for chunking, embedding, and loading articles

    Args:
        method: Chunking method ('char-split', 'recursive-split')

    Returns:
        Dictionary with processing results
    """
    logger.info(f"=== Starting chunk_embed_load - Method: {method} ===")
    logger.info(
        f"Using tables - Articles: {ARTICLES_TABLE_NAME}, Vectors: {VECTOR_TABLE_NAME}"
    )

    # Initialize components
    embedder = VertexEmbeddings()
    chunking_strategy = get_chunking_strategy(method)
    processor = ArticleProcessor(chunking_strategy, embedder)

    # Process articles
    with DatabaseManager(DB_URL) as db:
        # Fetch unprocessed articles
        articles = db.fetch_unprocessed_articles()

        if not articles:
            logger.info("No new articles to process")
            return ProcessingResult(
                status="success", message="No new articles to process", processed=0
            ).__dict__

        # Process each article
        processed_count = 0
        for i, article in enumerate(articles, start=1):
            # Process article into chunks with embeddings
            chunks_df = processor.process_article(article, i, len(articles))

            # Insert chunks
            inserted = db.insert_chunks(chunks_df)
            logger.info(
                f"[{i}/{len(articles)}] Inserted {inserted} chunks into {VECTOR_TABLE_NAME}"
            )

            # Mark article as processed
            db.mark_article_processed(article.article_id)

            processed_count += 1

    logger.info(
        f"=== COMPLETED: Processed {processed_count} articles, Total found: {len(articles)} ==="
    )

    return ProcessingResult(
        status="success",
        message=f"Processed {processed_count} articles",
        processed=processed_count,
        total_found=len(articles),
    ).__dict__


def main():
    """Entry point for standalone execution"""
    logger.info("Starting loader main function")
    result = chunk_embed_load("recursive-split")
    print(f"Final result: {result}")
    logger.info(f"Loader main function completed: {result}")


if __name__ == "__main__":
    main()
    