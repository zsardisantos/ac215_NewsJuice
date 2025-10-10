import httpx
import feedparser
import trafilatura
from time import sleep
from tqdm import tqdm
from datetime import datetime, timezone
from dateutil import parser as dateparser

class GazetteArticleScraper:
    def __init__(self, test_mode=False):

        self.test_mode = test_mode
        self.FEED_URL = "https://news.harvard.edu/gazette/feed/"            
        self.TIMEOUT = 10.0
        self.USER_AGENT = "newsjuice-scraper/0.2 (+https://newsjuiceapp.com)"

    def fetch_feed(self, url):
        r = httpx.get(
            url,
            headers={"User-Agent": self.USER_AGENT},
            timeout=self.TIMEOUT,
            follow_redirects=True,
        )
        r.raise_for_status()

        parsed_feed = feedparser.parse(r.text)
        entries = list(getattr(parsed_feed, "entries", []))
        if not entries:
            print("[rss] first 400 chars (debug):")
            print(rss_text[:400])
        return entries

    def fetch_html(self, url):
        try:
            html = httpx.get(url, 
                            headers={"User-Agent": self.USER_AGENT}, 
                            timeout=self.TIMEOUT, 
                            follow_redirects=True)
            html.raise_for_status()
            sleep(0.2)
            return html.text

        except Exception as ex:
            print(f"[fetch-error] {url} :: {ex}")
            return None

    def extract_article_link(self, entry):
        url = getattr(entry, "link", None)
        return url

    def extract_article_content(self, html):
        content = trafilatura.extract(html, include_comments=False, include_tables=False, favor_recall=True) or ""
        return content.strip()

    def extract_article_title(self, entry):
        title = getattr(entry, "title", None)
        return title

    def extract_article_author(self, entry):
        author = (getattr(entry, "author", "") or "").strip()
        return author

    def extract_publication_date(self, entry):
        date_str = getattr(entry, "published", None)
        if not date_str:
            return None
        try:
            d = dateparser.parse(date_str)
            if not d:
                return None
            if not d.tzinfo:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc).isoformat()
        except Exception:
            return None
    
    

    def fetched_at_date_formatted(self):
        fetched_at = datetime.now(timezone.utc)
        fetched_at = fetched_at.isoformat() if fetched_at else None
        return fetched_at


    def scrape(self):
        try:
            feed_entries = self.fetch_feed(self.FEED_URL)
        except Exception as e:
            print(f"[rss-fetch-error] {self.FEED_URL} :: {e}")

        print(f"scraping {len(feed_entries)} articles")

        if self.test_mode:
            feed_entries = [feed_entries[0]]

        all_articles_details = []
        for entry in tqdm(feed_entries):
            article_details={}

            # Get all the article URLs from the feed
            url = self.extract_article_link(entry)
            if not url:
                continue

            #the content is hard to extract from the data feed, pull the html to extract it
            # If HTML is not fetchable, then the link might be broaken. Skip Article. 
            html = self.fetch_html(url)
            if not html:
                continue
            
            content = self.extract_article_content(html)
            if not content or len(content) < 200:
                # skip very short or empty pages
                continue

            article_details = {
                "article_url": url,
                "article_title" : self.extract_article_title(entry),
                "article_author": self.extract_article_author(entry), 
                "article_publish_date": self.extract_publication_date(entry),
                "article_content": content,
                "fetched_at": self.fetched_at_date_formatted(), 
                "source_type": "Harvard Gazette",
                "summary":""}

            if self.test_mode:
                print(f"Article URL: {article_details['article_url']}")
                print(f"Article Title: {article_details['article_title']}")
                print(f"Article Author: {article_details['article_author']}")
                print(f"Article Publish Date: {article_details['article_publish_date']}")
                print(f"Article Content (first 200 chars): {article_details['article_content'][:200]}")
                print("\n\n")
            


            all_articles_details.append(article_details)

        
        print("Gazette Scraper Summary:")
        print(f"\n\nTotal number of articles: {len(all_articles_details)}")
        blank_content = len([d for d in all_articles_details if not d["article_content"] or d["article_content"].strip() == ""])
        blank_author = len([d for d in all_articles_details if not d["article_author"] or d["article_author"].strip() == ""])
        blank_title = len([d for d in all_articles_details if not d["article_title"] or d["article_title"].strip() == ""])
        blank_publish_date = len([d for d in all_articles_details if not d["article_publish_date"]])
        print(f"Blank article content: {blank_content}")
        print(f"Blank article author: {blank_author}")
        print(f"Blank article title: {blank_title}")
        print(f"Blank article publish date: {blank_publish_date}")

        return all_articles_details

if __name__=="__main__":
    scraper = GazetteArticleScraper(test_mode=False)
    details = scraper.scrape()

