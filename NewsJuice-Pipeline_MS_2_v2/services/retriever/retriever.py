'''
Retriever service

Asks for a user brief, does an embedding of it,
and retrives 2 best articles from DB

Inputs:
Runtime input from user   ---- text input from prompt

Outputs:
./artifacts/2-best.txt     --- text file with the 2 best articles

'''

# pip install psycopg2-binary pgvector
import psycopg
from pgvector.psycopg import register_vector, Vector

import os
DB_URL = os.environ["DATABASE_URL"]       
#DB_URL=postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb # for use with container
#DB_URL = "postgresql://postgres:Newsjuice25%2B@127.0.0.1:5432/newsdb"  # for use standalone; run proxy as well
TIMEOUT = 10.0
USER_AGENT = "minimal-rag-ingest/0.1"

from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")


conn = psycopg.connect(DB_URL, autocommit=True)
    #host="YOUR_CLOUDSQL_HOST",  # e.g. 127.0.0.1 if using Cloud SQL Proxy
    #dbname="YOUR_DB",
    #user="YOUR_USER",
    #password="YOUR_PASSWORD",
    #port=5432,)

register_vector(conn)

search_text = input("Search text ? : ")

# Query embedding
q = Vector(model.encode(search_text).tolist())

with conn, conn.cursor() as cur:
    # Choose one distance operator:
    #   <->  Euclidean   |  <#>  Inner product  |  <=>  Cosine distance
    cur.execute("SELECT current_database(), version();")
    db_name, db_version = cur.fetchone()
    print(f"[db] Connected successfully to '{db_name}'")
    print(f"[db] Server version: {db_version}")    
    
    cur.execute(
        """
        SELECT id, content, embedding <=> %s AS score
        FROM chunks_vector
        ORDER BY embedding <=> %s
        LIMIT 2;
        """,
        (q, q),
    )
    print("\n\nTOP 2  SEARCH RESULTS = \n\n")
    with open("/data/top-2.txt", "w", encoding="utf-8") as f:
        for row in cur.fetchall():
            f.write(str(row) + "\n\n")

