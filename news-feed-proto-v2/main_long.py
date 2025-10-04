'''
Uses async - FOR LATER
'''

# app/main.py
import os
import re
import asyncio
from datetime import datetime, timezone
from typing import Optional, Tuple

import feedparser
import httpx
import psycopg # for connection to postgres DB
import trafilatura
from dateutil import parser as dateparser
from langdetect import detect, LangDetectException

# ----------------------
# Config via environment
# ----------------------
#DB_URL = os.environ["DATABASE_URL"]  # for later
DB_URL = "postgresql://postgres:Newsjuice25+@34.42.4.152:5432/newsdb" # not safe as passoword, change later
#TIMEOUT = float(os.environ.get("FETCH_TIMEOUT", "10.0"))
TIMEOUT = 10.0
#USER_AGENT = os.environ.get("USER_AGENT", "minimal-rag-ingest/0.1")
USER_AGENT = "minimal-rag-ingest/0.1"


FEEDS = [
    "https://news.harvard.edu/gazette/feed/"
]

# ----------------------
# Helpers
# ----------------------

# Cleans up the URL 
def canonicalize_url(u: str) -> str:
    return re.sub(r"#.+$", "", (u or "").strip())


# Safely parses a date string into a Python datetime.
# Normalizes all datetimes to UTC.
# Returns None if parsing fails.

def parse_date(dt: Optional[str]):
    if not dt:
        return None
    try:
        d = dateparser.parse(dt) # dateutil.parser.parse
        if not d:
            return None
        if not d.tzinfo:  #If the parsed datetime doesn’t include timezone info, assume it’s UTC.
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:
        return None

async def fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(
        timeout=TIMEOUT, headers=headers, follow_redirects=True
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text

def extract_text_and_title(html: str) -> Tuple[str, str]:
    """
    Use trafilatura to extract main article text and (if possible) title.
    """
    txt = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )
    text = (txt or "").strip()

    title = ""
    try:
        md = trafilatura.extract_metadata(html)
        if md and md.title:
            title = md.title.strip()
    except Exception:
        pass

    return title, text

def detect_lang(text: str) -> Optional[str]:
    try:
        return detect(text) if text else None
    except LangDetectException:
        return None

def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception:
            pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
              id BIGSERIAL PRIMARY KEY,
              url TEXT UNIQUE,
              title TEXT,
              source TEXT,
              published_at TIMESTAMPTZ NULL,
              language TEXT,
              text TEXT NOT NULL,
              fetched_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

def upsert_article(conn: psycopg.Connection, row: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO articles (url, title, source, published_at, language, text, fetched_at)
            VALUES (%(url)s, %(title)s, %(source)s, %(published_at)s, %(language)s, %(text)s, %(fetched_at)s)
            ON CONFLICT (url) DO UPDATE SET
              title = EXCLUDED.title,
              source = EXCLUDED.source,
              published_at = EXCLUDED.published_at,
              language = EXCLUDED.language,
              text = EXCLUDED.text,
              fetched_at = EXCLUDED.fetched_at;
            """,
            row,
        )

async def process_entry(entry, source: str, conn: psycopg.Connection) -> bool:
    link = canonicalize_url(entry.get("link"))
    if not link:
        return False
    try:
        html = await fetch_html(link)
    except Exception as e:
        print(f"[fetch-error] {link} :: {e}")
        return False

    title, text = extract_text_and_title(html)
    if not text or len(text) < 200:
        return False

    row = {
        "url": link,
        "title": entry.get("title") or title or "",
        "source": source,
        "published_at": parse_date(entry.get("published")),
        "language": detect_lang(text),
        "text": text,
        "fetched_at": datetime.now(timezone.utc),
    }

    try:
        upsert_article(conn, row)
        return True
    except Exception as e:
        print(f"[db-error] {link} :: {e}")
        return False

# ----------------------
# Main entrypoint
# ----------------------
async def run():
    inserted = 0
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        ensure_schema(conn)

        for feed_url in FEEDS:
            try:
                fp = feedparser.parse(feed_url)
                # entries = fp.entries  # original: all entries
                entries = fp.entries[:10]  # limit to 10 per source for testing
            except Exception as e:
                print(f"[feed-error] {feed_url} :: {e}")
                continue

            tasks = [process_entry(e, feed_url, conn) for e in entries]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if r is True:
                    inserted += 1

    print({"rows_upserted": inserted})

if __name__ == "__main__":
    asyncio.run(run())