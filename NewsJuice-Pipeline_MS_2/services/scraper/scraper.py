'''
Scraper service

* Captures news from Harvard Gazette RSS feed
* Stores them in a jsonl file (news.jsonl) in the artifacts folder
'''

#app/main.py
import httpx
import feedparser
import trafilatura
from datetime import datetime, timezone
from urllib.parse import urlparse
from dateutil import parser as dateparser


import json, pathlib
from pathlib import Path

out = Path("/data/news.jsonl") # for docker-compose
#out = Path("./news.jsonl") # for standalone

out.parent.mkdir(parents=True, exist_ok=True)



import os
FEED_URL = "https://news.harvard.edu/gazette/feed/"                     # 1 source
TIMEOUT = 10.0
USER_AGENT = "newsjuice-scraper/0.2 (+https://newsjuiceapp.com)"


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

def get_rss_text(url: str) -> str:
    r = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        follow_redirects=True,
    )
    r.raise_for_status()
    return r.text
# ---------- Main minimal flow ----------
def main():
    try:
        rss_text = get_rss_text(FEED_URL)
    except Exception as e:
        print(f"[rss-fetch-error] {FEED_URL} :: {e}")
        return

    fp = feedparser.parse(rss_text)
    print(f"[rss] status={getattr(fp, 'status', 'n/a')} bozo={getattr(fp, 'bozo', 0)} "
          f"exc={getattr(fp, 'bozo_exception', None)}")

    entries = list(getattr(fp, "entries", []))
    print(f"[rss] entries={len(entries)}")
    if not entries:
        print("[rss] first 400 chars (debug):")
        print(rss_text[:400])
        return

    print(FEED_URL)
    print("\nENTRY 0:", entries[0])
    print("\nENTRY 9:", entries[9])

    inserted = 0
    source_link = source_label(FEED_URL)
    fetched_at = datetime.now(timezone.utc)
    fetched_at = fetched_at.isoformat() if fetched_at else None
    print("\ndatetime = ", datetime)            #exit()


    items = []

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
        published_at = parse_date_safe(getattr(e, "published", None))
        published_at = published_at.isoformat() if published_at else None
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
        
        item = {"author": author, "title" : title, "content": content, "published_at": published_at, "fetched_at": fetched_at, "source_link": FEED_URL, "source_type": "RSS", "summary":""}
        items.append(item)

    with out.open("w", encoding="utf-8") as f:
        count = 0
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
        print("NUMBER OF NEWS SCRAPED: ", count)    

if __name__ == "__main__":
    main()