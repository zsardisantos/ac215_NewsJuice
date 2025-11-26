"""
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
✅ Harvard Business School Communications Office: Publishes news from the business school.
    https://www.hbs.edu/news/Pages/browse.aspx?format=Article&source=Harvard%20Business%20School
✅ Harvard Law Today: The news hub for Harvard Law School.
    https://hls.harvard.edu/today/
✅ Harvard Medical School Office of Communications and External Relations
    https://hms.harvard.edu/news
✅ Harvard Kennedy School
    https://www.hks.harvard.edu/news-announcements
- Harvard School of Engineering
    https://seas.harvard.edu/news


"""

# ============== SETUP LOGGING ==============
import logging
import os
import sys
import uuid
from datetime import datetime
from tqdm import tqdm
from crimson_scraper import CrimsonArticleScraper
from db_manager import PostgresDBManager
from gazette_scraper import GazetteArticleScraper
from gsas_scraper import GsasArticleScraper
from harvard_magazine_scraper import HarvardMagazineArticleScraper
from hbs_scraper import HbsArticleScraper
from hks_scraper import HksArticleScraper
from hls_scraper import HlsArticleScraper
from hms_scraper import HmsArticleScraper
from seas_scraper import SeasArticleScraper

# from article_tags_builder import call_gemini_api


log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"scraper_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file}")
# ============================================================


def scrape_tag_load():

    logger.info("=== Starting scrape_tag_load  ===")

    # Initialize database manager
    db_manager = PostgresDBManager(url_column="source_link")

    sources = [
        ("Gazette", GazetteArticleScraper(test_mode=False)),
        ("Crimson", CrimsonArticleScraper(headless=True, test_mode=False, wait_ms=1000)),
        (
            "Harvard Magazine",
            HarvardMagazineArticleScraper(headless=True, test_mode=False, wait_ms=1000),
        ),
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

            db_record = {
                "author": article.get("article_author", ""),
                "title": article.get("article_title", ""),
                "summary": summary_value,
                "content": content,
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

    # ============== LOG COMPLETION ===============================================
    logger.info("\n✅ === SCRAPER COMPLETED ===")
    logger.info(f"\n✅ Inserted {total_inserted} new articles across all sources.")
    logger.info(f"\n✅ Total articles scraped: {total_scraped}")
    # =============================================================================

    # CM Need to check what parameter to return
    return {
        "status": "success",
        "message": f"Inserted {total_inserted} new articles across all sources",
        "processed": total_inserted,
        "total_found": total_scraped,
    }


def main():
    # ============== CHANGE 16: LOG MAIN START ==============
    logger.info("Starting scraper main function")
    # =======================================================

    result = scrape_tag_load()
    print(f"Final result: {result}")

    # ============== CHANGE 17: LOG MAIN COMPLETE ==============
    logger.info(f"Scraper main function completed: {result}")
    # ==========================================================


if __name__ == "__main__":
    main()
