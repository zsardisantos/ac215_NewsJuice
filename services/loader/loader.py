''''
loader service

take the jsonl file from ./artifacts, which contains the scraped news articles,
chunks them, does embedding and loads the chunks into the vector database
'''

import uuid

import pandas as pd
#app/main.py
#---import httpx
#---import feedparser
import psycopg

from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser as dateparser



# Vertex AI
from google import genai
from google.genai import types
from google.genai.types import Content, Part, GenerationConfig, ToolConfig
from google.genai import errors
from google.genai import types

from google.cloud import storage

BUCKET_NAME = "newsjuice-data-exchange"

from typing import List

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768 #256
# Langchain
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
#from vertex_embeddings import VertexEmbeddings

from langchain_openai import OpenAIEmbeddings  # or another embedding provider
from langchain_huggingface import HuggingFaceEmbeddings


from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# Load the jsonl file from /data/news.jsonl
import json, sys, pathlib
PATH_TO_NEWS= pathlib.Path("/data/news.jsonl")  # for M2 docker-compose version
PATH_TO_CHUNKS = pathlib.Path("/data/chunked_articles")
#path = pathlib.Path("./news.jsonl")  # for standalone version


# Parameter for character chunking 
CHUNK_SIZE_CHAR = 350
CHUNK_OVERLAPP_CHAR = 20

# Parameter for recursive chunking 
CHUNK_SIZE_RECURSIVE = 350


import os
DB_URL = os.environ["DATABASE_URL"]       
#DB_URL= "postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb" # for use with container
#DB_URL = "postgresql://postgres:Newsjuice25%2B@127.0.0.1:5432/newsdb"  # for use standalone; run proxy as well
TIMEOUT = 10.0
USER_AGENT = "minimal-rag-ingest/0.1"

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 768 #256
GENERATIVE_MODEL = "gemini-2.0-flash-001"

class VertexEmbeddings:
    def __init__(self):
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
        if not project:
            raise RuntimeError("Set GOOGLE_CLOUD_PROJECT")
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


def upload_to_gcs(bucket_name, source_file_path, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    print(f"✅ File {source_file_path} uploaded to gs://{bucket_name}/{destination_blob_name}")


# Chunking function

def chunk(method='char-split'): 
    print("chunk()")
    

    os.makedirs("/data/chunked_articles", exist_ok=True)

    # Read the /data/news.jsonl" file with articles scraped
    with PATH_TO_NEWS.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[skip] bad JSON on line {i}: {e}", file=sys.stderr)
                continue

            article_id = uuid.uuid4().hex
            
            content = obj.get("content", "")    
            title = obj.get("title", "")

            author = obj.get("author", "")
            summary = obj.get("summary", "")
            source_link = obj.get("source_link", "")
            fetched_at = obj.get("fetched_at", "")
            published_at = obj.get("published_at", "")
            source_type = obj.get("source_type", "")
            

            text_chunks = None
            if method == "char-split":
                PATH_TO_CHUNKS.mkdir(parents=True, exist_ok=True)
                # Init the splitter
                text_splitter = CharacterTextSplitter(
                    chunk_size=CHUNK_SIZE_CHAR, chunk_overlap=CHUNK_OVERLAPP_CHAR, separator='', strip_whitespace=False)

                # Perform the splitting
                text_chunks = text_splitter.create_documents([content])
                text_chunks = [art.page_content for art in text_chunks]
                print("Number of chunks:", len(text_chunks))

            elif method == "recursive-split":
                PATH_TO_CHUNKS.mkdir(parents=True, exist_ok=True)
                # Init the splitter
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=CHUNK_SIZE_RECURSIVE)

                # Perform the splitting
                text_chunks = text_splitter.create_documents([content])
                text_chunks = [art.page_content for art in text_chunks]
                print("Number of chunks:", len(text_chunks))

            elif method == "semantic-split":

                PATH_TO_CHUNKS.mkdir(parents=True, exist_ok=True)
                emb = VertexEmbeddings()  # reads GOOGLE_API_KEY or pass api_key="..."
                text_splitter = SemanticChunker(embeddings=emb)
                docs = text_splitter.create_documents([content])
                text_chunks = [d.page_content for d in docs]
                print("Number of chunks:", len(text_chunks))
              

            if text_chunks is not None:
                emb = VertexEmbeddings()
                data_df = pd.DataFrame(text_chunks, columns=["chunk"])
                data_df["article_id"] = article_id
                data_df["chunk_index"] = range(len(data_df))
                data_df["title"] = title
                data_df["author"] = author
                data_df["summary"] = summary
                data_df["source_link"] = source_link
                data_df["source_type"] = source_type
                data_df["fetched_at"] = fetched_at
                data_df["published_at"] = published_at
                data_df["embedding"] = [emb.embed_query(t) for t in data_df["chunk"]]

                jsonl_filename = os.path.join(
                    PATH_TO_CHUNKS, f"chunks-{method}-{title}.jsonl")
                with open(jsonl_filename, "w") as json_file:
                    json_file.write(data_df.to_json(orient='records', lines=True))

# Embedding function
#def embed():

# Loading function
def load():
        
    with psycopg.connect(DB_URL, autocommit=True) as conn:
         with conn.cursor() as cur:
    
    
            #  Connecting and confirmaing vector DB
            cur.execute("SELECT current_database(), version();")
            db_name, db_version = cur.fetchone()
            print(f"[db] Connected successfully to '{db_name}'")
            print(f"[db] Server version: {db_version}")

            files = sorted(PATH_TO_CHUNKS.glob("*.jsonl"))

            if not files:
                print(f"[warn] No .jsonl files found in {PATH_TO_CHUNKS}", file=sys.stderr)
                return

            inserted = 0

            for fp in files:
                    print(f"[info] Processing {fp}")
                    with fp.open("r", encoding="utf-8") as f:
                        for i, line in enumerate(f, start=1):
                            if not line.strip():
                                continue
                            try:
                                obj = json.loads(line)
                            except json.JSONDecodeError as e:
                                print(f"[skip] {fp.name}:{i} bad JSON: {e}", file=sys.stderr)
                                continue

                            article_id = obj.get("article_id", "") 
                            chunk_index = obj.get("chunk_index", "")
                            chunk = obj.get("chunk", "")
                            #content = obj.get("content", "")    
                            title = obj.get("title", "")
                            author = obj.get("author", "")
                            summary = obj.get("summary", "")
                            source_link = obj.get("source_link", "")
                            fetched_at = obj.get("fetched_at", "")
                            published_at = obj.get("published_at", "")
                            source_type = obj.get("source_type", "")
                            embedding = obj.get("embedding", "")
                            # Embedding 
                            #embed_np = model.encode(chunk)
                            #embedding = embed_np.tolist()

                            # Use Vertex    
                            #emb = VertexEmbeddings()
                            #embedding = emb.embed_query(chunk)

                            # Loading into vector DB
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO chunks_vector (article_id, author, title, \
                                        summary, source_link, fetched_at, published_at, \
                                            source_type, chunk, chunk_index, embedding)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                                    """,
                                    (article_id, author, title, \
                                        summary, source_link, fetched_at, published_at, \
                                            source_type, chunk, chunk_index, embedding),
                                )

                                inserted += 1
                                print(f"Inserting row number into vector DB: {inserted-1}")
                
                            except Exception as ex:
                                print(f"[db-insert-error] {source_link} :: {ex}")

            print({"Number of rows inserted into vector DB": inserted})
        


def main():

    chunk("semantic-split")
    load()

    # Upload test
    upload_to_gcs(
        BUCKET_NAME, 
        "/data/news.jsonl", 
        "news2.jsonl")
 

if __name__ == "__main__":
    main()