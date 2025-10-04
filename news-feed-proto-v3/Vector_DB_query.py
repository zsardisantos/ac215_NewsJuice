# pip install psycopg2-binary pgvector
import psycopg
from pgvector.psycopg import register_vector, Vector

import os
DB_URL = os.environ["DATABASE_URL"]

from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

conn = psycopg.connect(DB_URL, autocommit=True)
    #host="YOUR_CLOUDSQL_HOST",  # e.g. 127.0.0.1 if using Cloud SQL Proxy
    #dbname="YOUR_DB",
    #user="YOUR_USER",
    #password="YOUR_PASSWORD",
    #port=5432,)

register_vector(conn)

search_text = input("Search text?")

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
        FROM articles_vec
        ORDER BY embedding <=> %s
        LIMIT 2;
        """,
        (q, q),
    )
    print("TOP 2  SEARCH RESULTS = \n\n")
    for row in cur.fetchall():
        print(row)
        print("\n")
