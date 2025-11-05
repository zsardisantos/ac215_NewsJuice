'''
Scraper service

* Captures news from Harvard Gazette RSS feed
* Stores them in a jsonl file (news.jsonl) in the artifacts folder

News Sources: 
✅ The Harvard Gazette
    https://news.harvard.edu/gazette/feed/
✅ The Harvard Crimson
    https://www.thecrimson.com/
✅ Harvard Magazine
    https://www.harvardmagazine.com/harvard-headlines
✅ Colloquy: The alumni newsletter for the Graduate School of Arts and Sciences.
    https://gsas.harvard.edu/news/all
✅ Harvard Business School Communications Office: Publishes news and research from the business school.
    https://www.hbs.edu/news/Pages/browse.aspx?format=Article&source=Harvard%20Business%20School
✅ Harvard Law Today: The news hub for Harvard Law School.
    https://hls.harvard.edu/today/
✅ Harvard Medical School Office of Communications and External Relations - News: Disseminates news from the medical school.
    https://hms.harvard.edu/news
✅ Harvard Kennedy School
    https://www.hks.harvard.edu/news-announcements
- Harvard School of Engineering
    https://seas.harvard.edu/news


'''

import json
import uuid
import argparse
from pathlib import Path
from tqdm import tqdm
from gazette_scraper import GazetteArticleScraper
from crimson_scraper import CrimsonArticleScraper
from harvard_magazine_scraper import HarvardMagazineArticleScraper
from gsas_scraper import GsasArticleScraper
from hbs_scraper import HbsArticleScraper
from hls_scraper import HlsArticleScraper
from hms_scraper import HmsArticleScraper
from hks_scraper import HksArticleScraper
from seas_scraper import SeasArticleScraper
from db_manager import PostgresDBManager
from article_tags_builder import call_gemini_api

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape news articles')
    parser.add_argument('--out', default='artifacts/news.jsonl', help='Output file path')
    args = parser.parse_args()
    
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize database manager
    db_manager = PostgresDBManager(url_column="source_link")

    sources = [
        ("Gazette", GazetteArticleScraper(test_mode=False)),
        ("Crimson", CrimsonArticleScraper(headless=True, test_mode=False, wait_ms=1000)),
        ("Harvard Magazine", HarvardMagazineArticleScraper(headless=True, test_mode=False, wait_ms=1000)),
        ("GSAS", GsasArticleScraper(headless=True, test_mode=False, wait_ms=1000)),
        ("HBS", HbsArticleScraper(headless=True, test_mode=False, wait_ms=1000)),
        ("HLS", HlsArticleScraper(headless=True, test_mode=False, wait_ms=1000)),
        ("HMS", HmsArticleScraper(headless=True, test_mode=False, wait_ms=1000)),
        ("HKS", HksArticleScraper(headless=True, test_mode=False, wait_ms=1000)),
        ("SEAS", SeasArticleScraper(headless=True, test_mode=False, wait_ms=1000)),
    ]

    total_scraped = 0
    total_inserted = 0

    for label, scraper in sources:
        print(f"\nStarting {label} Scraper")
        try:
            articles = scraper.scrape()
        except Exception as exc:
            print(f"[scraper-error] {label} scrape failed: {exc}")
            continue

        if not articles:
            print(f"[scraper] {label}: no articles scraped")
            continue

        total_scraped += len(articles)
        db_records = []
        for article in tqdm(articles, desc=f"[tags] {label}", unit="article"):
            summary_value = article.get("summary", "")
            content = article.get("article_content", "") or ""

            prompt_source = content.strip()
            if prompt_source:
                tags_payload, error = call_gemini_api(prompt_source)
                if error:
                    print(f"[tags-error] {label} article tagging failed: {error}")
                else:
                    summary_value = json.dumps(tags_payload, ensure_ascii=False)

            db_record = {
                "author": article.get("article_author", ""),
                "title": article.get("article_title", ""),
                "summary": summary_value,
                "content": article.get("article_content", ""),
                "source_link": article.get("article_url", ""),
                "source_type": article.get("source_type", ""),
                "fetched_at": article.get("fetched_at"),
                "published_at": article.get("article_publish_date"),
                "vflag": 0,
                "article_id": str(uuid.uuid4()),
            }
            db_records.append(db_record)

        inserted_count = db_manager.insert_records(db_records)
        total_inserted += inserted_count
        print(f"[scraper] {label}: inserted {inserted_count}/{len(db_records)} new articles")

    print(f"\n✅ Inserted {total_inserted} new articles across all sources.")
    print(f"Total articles scraped: {total_scraped}")
    
    # # Optional: still write to JSONL for backup
    # with out.open("w", encoding="utf-8") as f:
    #     for article in all_articles:
    #         f.write(json.dumps(article, ensure_ascii=False) + "\n")    


if __name__ == "__main__":
    main()