'''
This version reads 10 articles from 1 web source (Harvard Gazette:
"https://news.harvard.edu/gazette/feed/"), 
takes the article content as 1 chunk, 
embeds each chunk into a 786 dim embedding vector (using 
sentence_transformer) and stores each article entry
in vector database on GCS.


PROJECT/DATABASE/TABLE on GCS

Account: harvardnewsjuice@gmail.com 
Password: (separate)
Project: NewsJuice
Instance: newsdb-instance
Database: newsdb  (NOTE: postgresSQL)
Table: articles_vec


1) NEED TO INSTALL Cloud SQL server to run this from container 
(NOTE: Using a database in GCS is slightly more complex than using a bucket, so you
need for development this running server. In production this is not necessary)

brew install cloud-sql-proxy
OR (which includes the above)
brew install google-cloud-sdk

2) THEN NEED TO STRAT A CLOUD SQL PROXY IN A TERMINAL 
FROM THE PROJECT FOLDER WITH JSON KEY FOR GCS DATABASE (sa-key.json)

cloud-sql-proxy \
  --credentials-file=./sa-key.json \
  --port 5432 \
  newsjuice-123456:us-central1:newsdb-instance

3) THEN FROM A SECOND TERMINAL BUILD CONTAINER OF CODE CHANGED:

docker build -t news-feed-proto-v2 -f Dockerfile .

4) THEN  RUN THE CONTAINER

docker run --rm -it \
  -e DATABASE_URL="postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb" \
  -v "$(pwd)":/app \
  news-feed-proto-v2

THE RESULT SHOULD BE 10 ADDED LINES IN THE articles_vec table



'''

#app/main.py
import httpx
import feedparser
import psycopg
import trafilatura
from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser as dateparser


# ---------- Config (hardcoded for a minimal demo) ----------
#DB_URL = "postgresql://postgres:Newsjuice25%2B@34.42.4.152:5432/newsdb"  # TODO: move to env later
#DB_URL=postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb # for use with container


import os
DB_URL = os.environ["DATABASE_URL"]

FEED_URL = "https://news.harvard.edu/gazette/feed/"                     # 1 source
TIMEOUT = 10.0
USER_AGENT = "minimal-rag-ingest/0.1"

from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")


# ---------- Tiny helpers ----------
def fetch_html_sync(url: str) -> str:
    r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, follow_redirects=True)
    r.raise_for_status()
    return r.text

def extract_content_and_title(html: str):
    """Returns (title, content) using trafilatura; empty strings on failure."""
    content = trafilatura.extract(html, include_comments=False, include_tables=False, favor_recall=True) or ""
    title = ""
    try:
        md = trafilatura.extract_metadata(html)
        if md and md.title:
            title = (md.title or "").strip()
    except Exception:
        pass
    return title.strip(), content.strip()

def parse_date_safe(dt_str):
    """Parse many date formats -> UTC aware datetime, or None."""
    if not dt_str:
        return None
    try:
        d = dateparser.parse(dt_str)
        if not d:
            return None
        if not d.tzinfo:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:
        return None

def source_label(feed_url: str) -> str:
    """Human-ish label from feed host (e.g., 'news.harvard.edu')."""
    return urlparse(feed_url).netloc or "unknown"


# ---------- Main minimal flow ----------
def main():
    # 1) Read RSS
    fp = feedparser.parse(FEED_URL)
    entries = fp.entries[:10]  # limit to 10 items

    print(FEED_URL)
    print("\nENTRY 0:", entries[0])
    print("\nENTRY 9:", entries[0])

    inserted = 0
    src = source_label(FEED_URL)
    fetch_now = datetime.now(timezone.utc)
    print("\ndatetime = ", datetime)

    # 2) Open DB connection (autocommit for simplicity)
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        with conn.cursor() as cur:

            #  Confirmation of connection
            cur.execute("SELECT current_database(), version();")
            db_name, db_version = cur.fetchone()
            print(f"[db] Connected successfully to '{db_name}'")
            print(f"[db] Server version: {db_version}")

            #exit()

            for e in entries:
                url = getattr(e, "link", None)
                if not url:
                    continue

                # 3) Fetch page + extract
                try:
                    html = fetch_html_sync(url)
                except Exception as ex:
                    print(f"[fetch-error] {url} :: {ex}")
                    continue

                title_guess, content = extract_content_and_title(html)
                if not content or len(content) < 200:
                    # skip very short or empty pages
                    continue

                # Prefer feed title if present; else extracted title
                title = (getattr(e, "title", None) or title_guess or "").strip()

                # publish date from feed if available
                publish_date = parse_date_safe(getattr(e, "published", None))

                # try to pull author from feed; if missing, try trafilatura metadata
                author = ""
                author = (getattr(e, "author", "") or "").strip()
                if not author:
                    try:
                        md = trafilatura.extract_metadata(html)
                        if md and md.author:
                            author = (md.author or "").strip()
                    except Exception:
                        pass

                # Get embedding
                chunk = content
                embed_np = model.encode(chunk)
                embed = embed_np.tolist()
    
                # 4) Insert row into your existing table
                # Expected columns: content, title, source, fetch_date, publish_date, author, type_source
                try:
                    cur.execute(
                        """
                        INSERT INTO articles_vec (content, title, source, fetched_at, published_at, type, chunk, chunk_index, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (content, title, src, fetch_now, publish_date, "rss", content, 0, embed),
                    )
                    inserted += 1
                    print(f"Inserting row: {inserted-1}")
                except Exception as ex:
                    print(f"[db-insert-error] {url} :: {ex}")

    print({"rows_inserted": inserted})


if __name__ == "__main__":
    main()