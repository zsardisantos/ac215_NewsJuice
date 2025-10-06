'''
loader service

take the jsonl file from ./artifacts, which contains the scraped news,
chunks them, does embedding and loads into vector database
'''

#app/main.py
import httpx
import feedparser
import psycopg
import trafilatura
from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser as dateparser


from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# Load the jsonl file from /data/news.jsonl
import json, sys, pathlib
path = pathlib.Path("/data/news.jsonl")  # for M2 docker-compose version
#path = pathlib.Path("./news.jsonl")  # for standalone version

jsonl_line_list = []
with path.open("r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"[skip] bad JSON on line {i}: {e}", file=sys.stderr)
            continue
        jsonl_line_list.append(obj)
        # or pretty:
        # print(json.dumps(obj, ensure_ascii=False, indent=2))
print("JASONL LIST = ")
print(jsonl_line_list)
#exit()

import os
DB_URL = os.environ["DATABASE_URL"]       
#DB_URL= "postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb" # for use with container
#DB_URL = "postgresql://postgres:Newsjuice25%2B@127.0.0.1:5432/newsdb"  # for use standalone; run proxy as well
TIMEOUT = 10.0
USER_AGENT = "minimal-rag-ingest/0.1"


# ---------- Main minimal flow ----------
def main():
    
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            #  Confirmation of connection to DB
            cur.execute("SELECT current_database(), version();")
            db_name, db_version = cur.fetchone()
            print(f"[db] Connected successfully to '{db_name}'")
            print(f"[db] Server version: {db_version}")

            inserted = 0
            for lin in  jsonl_line_list:

                author = lin['author']
                title = lin['title']
                summary = lin['summary']
                content = lin['content']
                source_link = lin['source_link']
                fetched_at = lin['fetched_at']
                published_at = lin['published_at']
                source_type = lin['source_type']

                 # Chunking  DUMMY - takes all content per news as 1 chunk
                chunk_index = 0  
                chunk = content

                # Embedding 
                embed_np = model.encode(chunk)
                embedding = embed_np.tolist()
    
                try:
                    cur.execute(
                        """
                        INSERT INTO chunks_vector (author, title, summary, content, source_link, fetched_at, published_at, source_type, chunk, chunk_index, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (author, title, summary, content, source_link, fetched_at, published_at, source_type, chunk, chunk_index, embedding),
                    )

                    inserted += 1
                    print(f"Inserting row number: {inserted-1}")
                
                except Exception as ex:
                    print(f"[db-insert-error] {source_link} :: {ex}")

    print({"Number of rows_inserted": inserted})
    

if __name__ == "__main__":
    main()