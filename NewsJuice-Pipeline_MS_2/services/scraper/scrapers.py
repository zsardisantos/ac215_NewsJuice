'''
Scraper service

* Captures news from Harvard Gazette RSS feed
* Stores them in a jsonl file (news.jsonl) in the artifacts folder

News Sources: 
✅ The Harvard Gazette
    https://news.harvard.edu/gazette/feed/
✅ The Harvard Crimson
    https://www.thecrimson.com/
- Harvard Magazine
    https://www.harvardmagazine.com/harvard-headlines
- Colloquy: The alumni newsletter for the Graduate School of Arts and Sciences.
    https://gsas.harvard.edu/news/all
- Harvard Business School Communications Office: Publishes news and research from the business school.
    https://www.hbs.edu/news/Pages/browse.aspx
- Harvard Law Today: The news hub for Harvard Law School.
    https://hls.harvard.edu/today/
- Harvard Medical School Office of Communications and External Relations - News: Disseminates news from the medical school.
    https://hms.harvard.edu/news

    # And more



'''

import json
from pathlib import Path
from gazette_scraper import GazetteArticleScraper
from crimson_scraper import CrimsonArticleScraper

out = Path("artifacts/news.jsonl") # for docker-compose
out.parent.mkdir(parents=True, exist_ok=True)

def main():

    print("\nStarting Gazette Scraper")
    gazzet_scraper = GazetteArticleScraper(test_mode=False)
    gazzet_details = gazzet_scraper.scrape()

    print("\nStarting Crimson Scraper")
    crimson_scraper = CrimsonArticleScraper(headless=True, test_mode="all_topics", wait_ms=1000)
    crimson_details = crimson_scraper.scrape()

    all_articles = gazzet_details +crimson_details

    with out.open("w", encoding="utf-8") as f:
        count = 0
        for article in all_articles:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")
            count += 1
        print("NUMBER OF NEWS SCRAPED: ", count)    

if __name__ == "__main__":
    main()