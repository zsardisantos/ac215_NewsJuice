from datetime import datetime, timezone

from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright
from tqdm import tqdm

from db_manager import PostgresDBManager

"""
Need to use Playwright instead of requests because some of the content such as "date" is rendered in
the browser.
List of headline pages. used to extract the articles URLs
All articcles follow the path /article/YYY/MM/DD/title-of-article

"""


class CrimsonArticleScraper:
    def __init__(self, headless=True, test_mode=False, wait_ms=1000):

        self.headless = headless
        self.test_mode = test_mode  # "single_topic", "all_topics", False
        self.wait_ms = wait_ms
        self.db_manager = PostgresDBManager(url_column="source_link")
        self.topic_urls = [
            "https://www.thecrimson.com/section/news/",
            "https://www.thecrimson.com/tag/editorials/",  # falls under Opinion
            "https://www.thecrimson.com/tag/op-eds/",  # Falls under Opinion
            "https://www.thecrimson.com/tag/columns/",  # Falls under Opinion
            "https://www.thecrimson.com/tag/arts-columns/",  # Falls under Arts
            "https://www.thecrimson.com/tag/campus-arts/",  # Falls under Arts
            "https://www.thecrimson.com/tag/books/",  # Falls under Arts
            "https://www.thecrimson.com/tag/music/",  # Falls under Arts
            "https://www.thecrimson.com/tag/film/",  # Falls under Arts
            "https://www.thecrimson.com/tag/tv/",  # Falls under Arts
            "https://www.thecrimson.com/tag/theater/",  # Falls under Arts
            "https://www.thecrimson.com/tag/culture/",  # Falls under Arts
            "https://www.thecrimson.com/tag/metro-arts/",  # Falls under Arts
            "https://www.thecrimson.com/section/metro/",
            "https://www.thecrimson.com/section/sports/",
        ]
        self.all_articles_details = []

    # get the html for each of the urls in topic_url and extract all the <a> tags from it

    def extract_article_links(self, soup):
        article_urls = []
        for a in soup.find_all("a"):
            href = a.get("href")
            if href and "/article/" in href:
                article_urls.append(href)
        return article_urls

    def extract_article_content(self, soup):
        content_div = soup.find("div", {"class": "css-ujgn17"})
        if content_div:
            content = "\n".join([p.get_text() for p in content_div.find_all("p")])
        else:
            content = None
            print("Content div not found")
        return content

    def extract_article_title(self, soup):

        title_div = soup.find("h1", {"class": "css-894m66"})
        if title_div:
            title = title_div.get_text()
            return title

        title_div = soup.find("h1", {"class": "css-1rfyg0l"})
        if title_div:
            title = title_div.get_text()
            return title

    def extract_article_author(self, soup):

        spans = soup.find_all("span", {"class": "css-1ys3e0l"})
        if spans:
            text_list = [span.get_text() for span in spans]
            return ", ".join(text_list)

        spans = soup.find_all("span", {"class": "css-x0hxbi"})
        if spans:
            text_list = [span.get_text() for span in spans]
            return ", ".join(text_list)

    def extract_article_publish_date(self, soup):
        time_tag = soup.find("time", attrs={"title": True})
        raw = time_tag.get("title") if time_tag else None
        if not raw:
            return None

        cleaned = raw.replace("Updated ", "").replace(" at ", " ")

        try:
            dt = dateparser.parse(cleaned)
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
                soup = BeautifulSoup(page.content(), "html.parser")
                topic_article_urls = self.extract_article_links(soup)
                print(f"Found {len(topic_article_urls)} in the topic {topic_url}")

                article_urls.extend(topic_article_urls)

                if len(article_urls) < 10 and not self.test_mode:
                    print(
                        """WARNING: Less than 10 article URLs extracted. This may indicate a problem
                        with the scraper."""
                    )
                page.wait_for_timeout(200)

            # Normalize URLs to full format
            normalized_urls = []
            for url in article_urls:
                if "https://www.thecrimson.com" not in url:
                    normalized_urls.append("https://www.thecrimson.com" + url)
                else:
                    normalized_urls.append(url)

            # Filter to only new URLs not in database
            new_urls = set(self.db_manager.filter_new_urls(normalized_urls))
            print(f"Found {len(new_urls)} new articles (out of {len(normalized_urls)} total)")

            if self.test_mode:
                print(len(new_urls))
                print(f"Articles to test: {list(new_urls)[:10]}")

            # Using the article URLs extracted, Navigate to the indevidual articles and extract the
            # main content from it
            for article_url in tqdm(list(new_urls)):
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
                    "source_type": "Harvard Crimson",
                    "summary": "",
                }

                print()
                self.all_articles_details.append(article_details)

                page.wait_for_timeout(200)

            browser.close()

        print("Crimson Scraper Summary")
        print(f"\n\nTotal number of articles: {len(self.all_articles_details)}")
        blank_content = len(
            [d for d in self.all_articles_details if not d["article_content"] or d["article_content"].strip() == ""]
        )
        blank_author = len(
            [d for d in self.all_articles_details if not d["article_author"] or d["article_author"].strip() == ""]
        )
        blank_title = len(
            [d for d in self.all_articles_details if not d["article_title"] or d["article_title"].strip() == ""]
        )
        blank_publish_date = len(
            [
                d
                for d in self.all_articles_details
                if not d["article_publish_date"] or d["article_publish_date"].strip() == ""
            ]
        )
        print(f"Blank article content: {blank_content}")
        print(f"Blank article author: {blank_author}")
        print(f"Blank article title: {blank_title}")
        print(f"Blank article publish date: {blank_publish_date}")

        return self.all_articles_details


if __name__ == "__main__":
    scraper = CrimsonArticleScraper(headless=True, test_mode="all_topics", wait_ms=1000)
    details = scraper.scrape()
