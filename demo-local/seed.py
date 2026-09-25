#!/usr/bin/env python3
"""
Seed the local demo database with real Harvard articles.

This is a compressed stand-in for the scraper + loader services: it fetches
recent articles from public RSS feeds, extracts the body text, chunks it with
the SAME parameters production uses (350 chars / 20 overlap), embeds each chunk
with Vertex AI text-embedding-004 (768-dim), and writes articles + chunks_vector.

It exists because the production corpus lives in a GCS bucket behind
credentials, and a demo only needs a few hundred good chunks.

    uv run --with feedparser --with trafilatura --with httpx \
           --with "psycopg[binary]" --with pgvector --with google-genai \
           demo-local/seed.py --limit 40

Requires:
    DATABASE_URL          postgresql://postgres:newsjuice@localhost:5433/newsdb
    GOOGLE_CLOUD_PROJECT  your new GCP project id
    GOOGLE_APPLICATION_CREDENTIALS  path to the service-account JSON
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone

import feedparser
import httpx
import psycopg
import trafilatura
try:
    # pgvector < 0.4: Vector lives in the psycopg adapter module
    from pgvector.psycopg import Vector, register_vector
except ImportError:
    # pgvector >= 0.4: Vector moved to the package root
    from pgvector import Vector
    from pgvector.psycopg import register_vector

from google import genai
from google.genai import types

# Must match loader_deployed/loader.py
CHUNK_SIZE = 350
CHUNK_OVERLAP = 20
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768

# source_type strings must match what the scrapers write, because the daily-brief
# query filters on `WHERE source_type = ANY(...)` from the user's saved preferences.
# Verified live 2026-09-24. The Crimson's RSS endpoints all 404 now, so it is
# omitted -- the production scraper reaches it by HTML scraping, not RSS.
FEEDS = {
    "Harvard Gazette": "https://news.harvard.edu/gazette/feed/",
    "Harvard Magazine": "https://www.harvardmagazine.com/rss.xml",
    "Harvard Law School": "https://hls.harvard.edu/feed/",
    "Harvard Kennedy School": "https://www.hks.harvard.edu/rss.xml",
}


def chunk_text(text: str) -> list[str]:
    """Fixed-width character chunking with overlap (production 'char-split' strategy)."""
    text = " ".join(text.split())
    if len(text) <= CHUNK_SIZE:
        return [text] if text else []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    return [text[i : i + CHUNK_SIZE] for i in range(0, len(text), step) if text[i : i + CHUNK_SIZE].strip()]


def fetch_articles(limit_per_feed: int) -> list[dict]:
    """Pull recent entries from each feed and extract readable body text."""
    articles = []
    client = httpx.Client(
        timeout=20.0,
        follow_redirects=True,
        headers={"User-Agent": "NewsJuice-demo-seed/1.0"},
    )

    for source_type, feed_url in FEEDS.items():
        print(f"\n[feed] {source_type} -> {feed_url}")
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"  [skip] feed parse failed: {e}")
            continue

        if not parsed.entries:
            print("  [skip] no entries returned")
            continue

        taken = 0
        for entry in parsed.entries:
            if taken >= limit_per_feed:
                break
            link = entry.get("link")
            if not link:
                continue
            try:
                resp = client.get(link)
                resp.raise_for_status()
                body = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
            except Exception as e:
                print(f"  [skip] {link[:70]} -> {type(e).__name__}")
                continue

            if not body or len(body) < 400:
                print(f"  [skip] too short: {link[:70]}")
                continue

            published = None
            if entry.get("published_parsed"):
                published = datetime(*entry.published_parsed[:6])

            articles.append(
                {
                    "article_id": hashlib.sha1(link.encode()).hexdigest(),
                    "author": (entry.get("author") or "")[:255] or None,
                    "title": entry.get("title") or "Untitled",
                    "summary": (entry.get("summary") or "")[:2000] or None,
                    "content": body,
                    "source_link": link,
                    "source_type": source_type,
                    "fetched_at": datetime.now(timezone.utc).replace(tzinfo=None),
                    "published_at": published,
                }
            )
            taken += 1
            print(f"  [ok]   {entry.get('title', '')[:65]}  ({len(body)} chars)")

    client.close()
    return articles


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25, help="articles per feed (default 25)")
    ap.add_argument("--dry-run", action="store_true", help="scrape + chunk but do not embed or write")
    args = ap.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    region = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

    if not db_url:
        print("ERROR: DATABASE_URL is not set")
        return 1

    articles = fetch_articles(args.limit)
    if not articles:
        print("\nERROR: no articles fetched -- check network / feed URLs")
        return 1

    total_chunks = sum(len(chunk_text(a["content"])) for a in articles)
    print(f"\n[plan] {len(articles)} articles -> ~{total_chunks} chunks to embed")

    if args.dry_run:
        print("[dry-run] stopping before embedding")
        return 0

    if not project:
        print("ERROR: GOOGLE_CLOUD_PROJECT is not set (needed for Vertex embeddings)")
        return 1

    embed_client = genai.Client(vertexai=True, project=project, location=region)
    embed_cfg = types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)

    def embed(text: str) -> list[float]:
        resp = embed_client.models.embed_content(model=EMBEDDING_MODEL, contents=[text], config=embed_cfg)
        return resp.embeddings[0].values

    conn = psycopg.connect(db_url, autocommit=False)
    register_vector(conn)
    cur = conn.cursor()

    inserted_articles = 0
    inserted_chunks = 0

    for a in articles:
        chunks = chunk_text(a["content"])
        if not chunks:
            continue

        cur.execute(
            """
            INSERT INTO articles (article_id, author, title, summary, content,
                                  source_link, source_type, fetched_at, published_at, vflag)
            VALUES (%(article_id)s, %(author)s, %(title)s, %(summary)s, %(content)s,
                    %(source_link)s, %(source_type)s, %(fetched_at)s, %(published_at)s, 0)
            ON CONFLICT (article_id) DO NOTHING
            RETURNING article_id
            """,
            a,
        )
        if cur.fetchone() is None:
            print(f"[dup]  already seeded: {a['title'][:60]}")
            continue
        inserted_articles += 1

        print(f"[embed] {a['title'][:55]}  ({len(chunks)} chunks)", end="", flush=True)
        for idx, chunk in enumerate(chunks):
            try:
                vec = embed(chunk)
            except Exception as e:
                print(f"\n  [embed-error] chunk {idx}: {e}")
                continue
            cur.execute(
                """
                INSERT INTO chunks_vector (article_id, author, title, summary, content,
                                           source_link, source_type, fetched_at, published_at,
                                           chunk, chunk_index, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    a["article_id"], a["author"], a["title"], a["summary"], a["content"],
                    a["source_link"], a["source_type"], a["fetched_at"], a["published_at"],
                    chunk, idx, Vector(vec),
                ),
            )
            inserted_chunks += 1
            print(".", end="", flush=True)

        cur.execute("UPDATE articles SET vflag = 1 WHERE article_id = %s", (a["article_id"],))
        conn.commit()
        print(" done")

    cur.execute("SELECT count(*) FROM chunks_vector")
    grand_total = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"\n[done] +{inserted_articles} articles, +{inserted_chunks} chunks")
    print(f"[done] chunks_vector now holds {grand_total} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
