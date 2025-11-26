from datetime import datetime, timezone
from time import sleep

from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright
from tqdm import tqdm

from db_manager import PostgresDBManager


class HbsArticleScraper:
    def __init__(self, headless=True, test_mode=False, wait_ms=1000):

        self.headless = headless
        self.test_mode = test_mode  # "single_topic", "all_topics", False
        self.wait_ms = wait_ms
        if not self.test_mode:
            self.db_manager = PostgresDBManager(url_column="source_link")
        self.topic_urls = [
            ("https://www.hbs.edu/news/Pages/browse.aspx?" "format=Article&source=Harvard%20Business%20School"),
        ]
        self.all_articles_details = []

    # get the html for each of the urls in topic_url and extract all the <a> tags from it

    def extract_article_links(self, soup):
        article_urls = []
        for a in soup.find_all("a"):
            href = a.get("href")
            if href and "https://www.hbs.edu/news/" in href and "https://www.hbs.edu/news/Pages/" not in href:
                article_urls.append(href)

        return article_urls

    def extract_article_content(self, soup):
        content_div = soup.find("table", {"class": "body-html-fix"})
        if content_div:
            # Only get <p> tags that don't have a class attribute
            paragraphs = content_div.find_all("p", class_=False)
            if paragraphs:
                first_text = paragraphs[0].get_text(strip=True)
                if first_text.lower().startswith("by "):
                    paragraphs = paragraphs[1:]
            if paragraphs:
                content = "\n".join([p.get_text(strip=True) for p in paragraphs])
            else:
                content = None
        else:
            content = None
            print("Content div not found")
        return content

    def extract_article_title(self, soup):

        title_div = soup.find("h1")
        if title_div:
            title = title_div.get_text()
            return title

    def extract_article_author(self, soup):

        author_div = soup.find("table", {"class": "body-html-fix"})
        if not author_div:
            return None

        author_tag = author_div.find("p")
        if not author_tag:
            return None

        author_text = author_tag.get_text(strip=True)
        if author_text.lower().startswith("by "):
            return author_text[3:].strip()

        return None

    def extract_article_publish_date(self, soup):
        date_tag = soup.find("span", {"style": "text-transform:uppercase;"})
        try:
            if not date_tag:
                return None
            date_text = date_tag.get_text(strip=True)
            dt = dateparser.parse(date_text)
            if not dt:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return None

    def fetched_at_date_formatted(self):
        fetched_at = datetime.now(timezone.utc)
        fetched_at = fetched_at.isoformat() if fetched_at else None
        return fetched_at

    # browser control

    def scrape(self):

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.headless)
            page = browser.new_page()

            if self.test_mode == "single_topic":
                self.topic_urls = [self.topic_urls[0]]

            # Navigate to article library and extract all the <a> tags from it
            article_urls = []
            for topic_url in self.topic_urls:
                page.goto(topic_url, wait_until="domcontentloaded")
                sleep(2)  # sleep needed to avoid bot detection
                soup = BeautifulSoup(page.content(), "html.parser")
                topic_article_urls = self.extract_article_links(soup)
                print(f"Found {len(topic_article_urls)} in the topic {topic_url}")

                article_urls.extend(topic_article_urls)

                page.wait_for_timeout(200)

            # Filter to only new URLs not in database
            article_urls = list(dict.fromkeys(article_urls))
            if not self.test_mode:
                article_urls = set(self.db_manager.filter_new_urls(article_urls))
                print(f"Found {len(article_urls)} new articles (out of {len(article_urls)} total)")

            if self.test_mode:
                print(len(article_urls))
                print(f"Articles to test: {list(article_urls)[:10]}")
                article_urls = article_urls[:10]

            # Using the article URLs extracted, Navigate to the indevidual articles and extract the
            # main content from it
            for article_url in tqdm(list(article_urls)):
                # URL already normalized above
                page.goto(article_url, wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                html = page.content()

                if self.test_mode:
                    print(article_url)

                soup = BeautifulSoup(html, "html.parser")
                article_details = {
                    "article_url": article_url,
                    "article_title": self.extract_article_title(soup),
                    "article_author": self.extract_article_author(soup),
                    "article_publish_date": self.extract_article_publish_date(soup),
                    "article_content": self.extract_article_content(soup),
                    "fetched_at": self.fetched_at_date_formatted(),
                    "source_type": "Harvard Business School",
                    "summary": "",
                }

                if self.test_mode:
                    print(article_details)
                self.all_articles_details.append(article_details)

                page.wait_for_timeout(200)

            browser.close()

        return self.all_articles_details


if __name__ == "__main__":
    scraper = HbsArticleScraper(headless=False, test_mode="all_topics", wait_ms=1000)
    details = scraper.scrape()

    print("GSAS News Scraper Summary")
    print(f"\n\nTotal number of articles: {len(details)}")
    blank_content = len([d for d in details if not d["article_content"] or d["article_content"].strip() == ""])
    blank_author = len([d for d in details if not d["article_author"] or d["article_author"].strip() == ""])
    blank_title = len([d for d in details if not d["article_title"] or d["article_title"].strip() == ""])
    blank_publish_date = len(
        [d for d in details if not d["article_publish_date"] or d["article_publish_date"].strip() == ""]
    )
    print(f"Blank article content: {blank_content}")
    print(f"Blank article author: {blank_author}")
    print(f"Blank article title: {blank_title}")
    print(f"Blank article publish date: {blank_publish_date}")
