from datetime import datetime, timezone

from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright
from tqdm import tqdm

from db_manager import PostgresDBManager


class GsasArticleScraper:
    def __init__(self, headless=True, test_mode=False, wait_ms=1000):

        self.headless = headless
        self.test_mode = test_mode  # "single_topic", "all_topics", False
        self.wait_ms = wait_ms
        self.db_manager = PostgresDBManager(url_column="source_link")
        self.topic_urls = [
            # Need to run 3 pages because each page is showing only 7 articles
            "https://gsas.harvard.edu/news/topic/commencement",
            "https://gsas.harvard.edu/news/topic/commencement?page=1",
            "https://gsas.harvard.edu/news/topic/commencement?page=2",
            "https://gsas.harvard.edu/news/topic/alumni",
            "https://gsas.harvard.edu/news/topic/alumni?page=1",
            "https://gsas.harvard.edu/news/topic/alumni?page=2",
            "https://gsas.harvard.edu/news/topic/research",
            "https://gsas.harvard.edu/news/topic/research?page=1",
            "https://gsas.harvard.edu/news/topic/research?page=2",
            "https://gsas.harvard.edu/news/topic/climate",
            "https://gsas.harvard.edu/news/topic/climate?page=1",
            "https://gsas.harvard.edu/news/topic/climate?page=2",
            "https://gsas.harvard.edu/news/topic/voices",
            "https://gsas.harvard.edu/news/topic/voices?page=1",
            "https://gsas.harvard.edu/news/topic/voices?page=2",
            "https://gsas.harvard.edu/news/topic/leadership",
            "https://gsas.harvard.edu/news/topic/leadership?page=1",
            "https://gsas.harvard.edu/news/topic/leadership?page=2",
        ]
        self.all_articles_details = []

    # get the html for each of the urls in topic_url and extract all the <a> tags from it

    def extract_article_links(self, soup):
        article_urls = []
        for a in soup.find_all("a"):
            href = a.get("href")
            if (
                href
                and "/news/" in href
                and "/news/topic/" not in href
                and "https://" not in href
                and "/news/search" not in href
            ):
                article_urls.append(href)

        # print(article_urls)
        return article_urls

    def extract_article_content(self, soup):
        content_div = soup.find(
            "div",
            {
                "class": (
                    "field field--node-field-content field--name-field-content "
                    "field--type-entity-reference-revisions field--label-hidden field__items"
                )
            },
        )
        if content_div:
            # Only get <p> tags that don't have a class attribute
            paragraphs = content_div.find_all("p", class_=False)
            content = "\n".join([p.get_text(strip=True) for p in paragraphs])
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

        spans = soup.find_all(
            "span",
            {
                "class": (
                    "field field--node-field-author field--name-field-author "
                    "field--type-entity-reference field--label-hidden field__item"
                )
            },
        )
        if spans:
            text_list = [span.get_text() for span in spans]
            return ", ".join(text_list)

    def extract_article_publish_date(self, soup):
        date_tag = soup.find(
            "div",
            {
                "class": (
                    "field field--node-field-publication-date field--name-field-publication-date "
                    "field--type-datetime field--label-hidden field__item"
                )
            },
        )
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
                soup = BeautifulSoup(page.content(), "html.parser")
                topic_article_urls = self.extract_article_links(soup)
                print(f"Found {len(topic_article_urls)} in the topic {topic_url}")

                article_urls.extend(topic_article_urls)

                page.wait_for_timeout(200)

            # Normalize URLs to full format
            normalized_urls = []
            for url in article_urls:
                if "https://gsas.harvard.edu" not in url:
                    normalized_urls.append("https://gsas.harvard.edu" + url)
                else:
                    normalized_urls.append(url)

            # Filter to only new URLs not in database
            normalized_urls = list(dict.fromkeys(normalized_urls))
            new_urls = set(self.db_manager.filter_new_urls(normalized_urls))
            print(f"Found {len(new_urls)} new articles (out of {len(normalized_urls)} total)")

            if self.test_mode:
                print(len(new_urls))
                print(f"Articles to test: {list(new_urls)[:10]}")

            # Using the article URLs extracted, Navigate to the indevidual articles and
            #  extract the main content from it
            for article_url in tqdm(list(new_urls)):
                # URL already normalized above
                page.goto(article_url, wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                html = page.content()

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

                if self.test_mode:
                    print(article_url)
                    print(article_details)

                self.all_articles_details.append(article_details)

                page.wait_for_timeout(200)

            browser.close()

        return self.all_articles_details


if __name__ == "__main__":
    scraper = GsasArticleScraper(headless=False, test_mode="all_topics", wait_ms=1000)
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
