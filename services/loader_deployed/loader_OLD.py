"""
===============
loader service
===============

Comment on the VertexEmbeddings wrapper class:

Without you would need to do
from google import genai
client = genai.Client(vertexai=True, project="my-project", location="us-central1")
resp = client.models.embed_content(model="text-embedding-004", contents=["text"])

with wrapper you just do:
emb = VertexEmbeddings()
vectors = emb.embed_documents(["text1", "text2"])
"""

import os

# Table configuration from environment variables
ARTICLES_TABLE_NAME = os.environ.get("ARTICLES_TABLE_NAME", "articles_test")
VECTOR_TABLE_NAME = os.environ.get("VECTOR_TABLE_NAME", "chunks_vector_test")


import pandas as pd
import psycopg
from psycopg import sql
from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser as dateparser
from typing import List
import json, sys, pathlib

# Vertex AI
from google import genai
from google.genai import types
from google.genai.types import Content, Part, GenerationConfig, ToolConfig
from google.genai import errors
from google.genai import types

# Langchain
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker

# source: https://api.python.langchain.com/en/latest/text_splitter/langchain_experimental.text_splitter.SemanticChunker.html


# FE - Comment out if final embedding is Vertex AI
# from sentence_transformers import SentenceTransformer
# model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")


# FE - Parameter for final embedding using Vertex AI
EMBEDDING_MODEL = "text-embedding-004"
# GENERATIVE_MODEL = "gemini-2.0-flash-001"
EMBEDDING_DIM = 768  # 256

# Parameter for chunking
CHUNK_SIZE_CHAR = 350
CHUNK_OVERLAP_CHAR = 20
CHUNK_SIZE_RECURSIVE = 350


import os

DB_URL = os.environ["DATABASE_URL"]
# DB_URL= "postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb" # for use with container
# DB_URL = "postgresql://postgres:Newsjuice25%2B@127.0.0.1:5432/newsdb"  # for use standalone; run proxy as well
# USER_AGENT = "minimal-rag-ingest/0.1"

from pgvector.psycopg import register_vector


class VertexEmbeddings:
    def __init__(self):
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
        if not project:
            raise RuntimeError("Need to set GOOGLE_CLOUD_PROJECT")
        # Uses ADC via GOOGLE_APPLICATION_CREDENTIALS or gcloud
        self.client = genai.Client(vertexai=True, project=project, location=location)
        self.model = EMBEDDING_MODEL
        self.dim = EMBEDDING_DIM

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


# Chunking function
def chunk_embed_load(method="char-split"):

    conn = psycopg.connect(DB_URL, autocommit=True)

    register_vector(conn)

    cur = conn.cursor()

    # Fetch new articles from articles table (vflag = 0)
    cur.execute(
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

    rows = cur.fetchall()

    if not rows:
        print("[Message from loader - chunk_embed_load:] No new articles to process")
        return {
            "status": "success",
            "message": "No new articles to process",
            "processed": 0,
        }

    # Prepare semantic splitter once (if requested)
    sem_splitter = None
    processed_count = 0
    if method == "semantic-split":
        emb = VertexEmbeddings()
        # sem_splitter = SemanticChunker(embeddings=emb)
        # NEW VERSION WITH ALL PARAMETERS SET EXPLICITLY
        sem_splitter = SemanticChunker(
            embeddings=emb,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=90,
            min_chunk_size=None,
            # max_chunk_size=None,
            # embedding_batch_size=100
        )

        # FE - Use this when using VERTEX AI for final embedding
        vertex_embedder = VertexEmbeddings()

    """
    Process now article by article
    """

    for i, row in enumerate(rows, start=1):
        (
            id,
            author,
            title,
            summary,
            content,
            source_link,
            source_type,
            fetched_at,
            published_at,
            vflag,
            article_id,
        ) = row

        """
        Do chunking of the article
        """

        if method == "char-split":
            text_splitter = CharacterTextSplitter(
                chunk_size=CHUNK_SIZE_CHAR,
                chunk_overlap=CHUNK_OVERLAP_CHAR,
                separator=None,
                strip_whitespace=False,
            )
            docs = text_splitter.create_documents([content or ""])

        elif method == "recursive-split":
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE_RECURSIVE
            )
            docs = text_splitter.create_documents([content or ""])

        elif method == "semantic-split":
            if sem_splitter is None:
                raise RuntimeError("Semantic splitter not initialized")
            docs = sem_splitter.create_documents([content or ""])

        else:
            raise ValueError(f"Unknown method: {method}")

        text_chunks = [d.page_content for d in docs]
        print(f"[{i}/{len(rows)}] article_id={article_id} → {len(text_chunks)} chunks")

        """
        Build rows to insert into vector table
        """

        df = pd.DataFrame(text_chunks, columns=["chunk"])
        df["author"] = author
        df["title"] = title
        df["summary"] = summary
        df["content"] = content
        df["source_link"] = source_link
        df["source_type"] = source_type
        df["fetched_at"] = fetched_at
        df["published_at"] = published_at
        df["chunk_index"] = range(len(df))
        df["article_id"] = article_id

        """
        Final embedding of the chunk (align with retrieval model)
        here: sentence-transformers/all-mpnet-base-v2
        """

        # FE - VERSION WITH HUGGING sentence-encoder
        # df["embedding"] = [model.encode(t).tolist() for t in df["chunk"]]
        # VERSION WITH VERTEX AI
        df["embedding"] = vertex_embedder.embed_documents(df["chunk"].tolist())

        """
        Print article currently processed for inspection
        """
        print(f"\n \n Inserting now chunks for article_ID = {article_id}")
        print("Article text =\n")
        print(content)

        """
        Insert chunks
        """
        inserted = 0
        for _, r in df.iterrows():
            # --- INSERT chunk row into vector table ---
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

            cur.execute(
                insert_sql,
                (
                    r["author"],
                    r["title"],
                    r["summary"],
                    r["content"],
                    r["source_link"],
                    r["source_type"],
                    r["fetched_at"],
                    r["published_at"],
                    r["chunk"],
                    int(r["chunk_index"]),
                    r["embedding"],
                    r["article_id"],
                ),
            )

            # print chunk for inspection
            print(f"\nChunk Number {int(r['chunk_index'])}: ")
            print(r["chunk"])
            print("\n")

        # UPDATE article as
        update_sql = sql.SQL(
            """
            UPDATE {} 
            SET vflag = 1 
            WHERE article_id = %s
        """
        ).format(sql.Identifier(ARTICLES_TABLE_NAME))

        cur.execute(update_sql, (article_id,))
        processed_count += 1

    cur.close()
    conn.close()

    return {
        "status": "success",
        "message": f"Processed {processed_count} articles",
        "processed": processed_count,
        "total_found": len(rows),
    }


def main():

    result = chunk_embed_load("semantic-split")
    print(f"Final result: {result}")


if __name__ == "__main__":
    main()
