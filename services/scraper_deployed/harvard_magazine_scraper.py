from datetime import datetime, timezone
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright
from tqdm import tqdm

from db_manager import PostgresDBManager

"""
Need to use Playwright instead of requests because some of the content such as "date" is rendered
in the browser
List of headline pages. used to extract the articles URLs
All articcles follow the path /article/YYY/MM/DD/title-of-article

"""


class HarvardMagazineArticleScraper:
    def __init__(self, headless=True, test_mode=False, wait_ms=1000):

        self.headless = headless
        self.test_mode = test_mode  # "single_topic", "all_topics", False
        self.wait_ms = wait_ms
        self.db_manager = PostgresDBManager(url_column="source_link")
        self.topic_urls = [
            "https://www.harvardmagazine.com/topic/arts-culture",
            "https://www.harvardmagazine.com/topic/commentary",  # falls under Opinion
            "https://www.harvardmagazine.com/topic/faculty-community",  # Falls under Opinion
            "https://www.harvardmagazine.com/topic/health-medicine",  # Falls under Opinion
            "https://www.harvardmagazine.com/topic/humanities-arts",  # Falls under Arts
            "https://www.harvardmagazine.com/topic/international-affairs",  # Falls under Arts
            "https://www.harvardmagazine.com/topic/science",  # Falls under Arts
            "https://www.harvardmagazine.com/topic/social-sciences",  # Falls under Arts
            "https://www.harvardmagazine.com/topic/athletics",  # Falls under Arts
            "https://www.harvardmagazine.com/topic/students",  # Falls under Arts
            "https://www.harvardmagazine.com/topic/the-professions",  # Falls under Arts
            "https://www.harvardmagazine.com/topic/university-news",  # Falls under Arts
        ]
        self.all_articles_details = []

    # get the html for each of the urls in topic_url and extract all the <a> tags from it

    def extract_article_links(self, soup):
        article_urls = []
        for a in soup.find_all("a"):
            href = a.get("href")

            # All article topics have the domain in them. This removes internal references and
            # youtube and social media links
            if href and "https://www.harvardmagazine.com/" in href:
                path_segments = [segment for segment in urlparse(href).path.split("/") if segment]
                if (
                    len(path_segments) == 2  # Article paths need to hae 2 path segments
                    and not path_segments[0].isdigit()
                    and "/topic/" not in href  # Removing references to topic pages, focusing only on articles:
                    and "/browse/issue/" not in href
                ):
                    article_urls.append(href)
        return article_urls

    def extract_article_content(self, soup):
        container = soup.find("div", class_="block block-layout-builder block-field-blocknodearticlebody")
        if not container:
            print("Content div not found")
            return None

        parts = []
        for tag in container.find_all(["p"]):
            text = tag.get_text(" ", strip=True)
            if text:
                parts.append(text)

        if not parts:
            return None

        return "\n\n".join(parts)

    def extract_article_title(self, soup):

        title_div = soup.find("h1")
        if title_div:
            title = title_div.get_text()
            return title

    def extract_article_author(self, soup):

        byline = soup.find("div", {"class": "article_header_section__byline"})
        if byline:
            anchor_names = [a.get_text(strip=True) for a in byline.find_all("a") if a.get_text(strip=True)]
            if anchor_names:
                return ", ".join(anchor_names)

            stripped = [text for text in byline.stripped_strings if text.lower() != "by"]
            if stripped:
                return " ".join(stripped)

    def extract_article_publish_date(self, soup):
        time_tag = soup.find("time")
        if not time_tag:
            return None

        candidates = []
        datetime_attr = time_tag.get("datetime")
        if datetime_attr:
            candidates.append(datetime_attr)

        text_value = time_tag.get_text(strip=True)
        if text_value:
            candidates.append(text_value)

        for raw in candidates:
            cleaned = raw.replace("Updated ", "").replace(" at ", " ")

            try:
                dt = dateparser.parse(cleaned)
            except Exception:
                continue

            if not dt:
                continue

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc).isoformat()

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

                if self.test_mode:
                    print(f"Extracting {len(topic_article_urls)} Unique URLs")
                    topic_article_urls = topic_article_urls[:2]

                article_urls.extend(topic_article_urls)

                if len(article_urls) < 5 and not self.test_mode:
                    print(
                        """WARNING: Less than 10 article URLs extracted. This may indicate
                        a problem with the scraper."""
                    )
                page.wait_for_timeout(200)

            # # Filter to only new URLs not in database
            print(f"found a total of {len(article_urls)} URLs")
            article_urls = list(dict.fromkeys(article_urls))
            new_urls = set(self.db_manager.filter_new_urls(article_urls))
            print(
                f"""Found {len(new_urls)} new articles (out of {len(article_urls)}
                total unique articles)"""
            )

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
                    "source_type": "Harvard Magazine",
                    "summary": "",
                }

                if self.test_mode:
                    print(article_details)

                content = article_details.get("article_content")
                if content and len(content) > 100:
                    self.all_articles_details.append(article_details)

                page.wait_for_timeout(200)

            browser.close()

        return self.all_articles_details


if __name__ == "__main__":
    scraper = HarvardMagazineArticleScraper(headless=False, test_mode=False, wait_ms=1000)
    details = scraper.scrape()

    print("Harvard news Scraper Summary")
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
