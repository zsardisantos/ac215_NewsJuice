from tqdm import tqdm
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from dateutil import parser as dateparser
from datetime import timezone, datetime
from urllib.parse import urljoin
from db_manager import PostgresDBManager
from time import sleep

class SeasArticleScraper:
    def __init__(self, headless=True, test_mode=False, wait_ms=1000):

        self.headless = headless
        self.test_mode = test_mode   #"single_topic", "all_topics", False
        self.wait_ms = wait_ms
        if not self.test_mode:
            self.db_manager = PostgresDBManager(url_column="source_link")
        self.topic_urls =[
            "https://seas.harvard.edu/news",    
        ]
        self.all_articles_details = []

# get the html for each of the urls in topic_url and extract all the <a> tags from it

    def extract_article_links(self, soup):
        article_urls =[]
        for a in soup.find_all('a'):
            href = a.get('href')
            if (href
            and "/news/" in href
            and "//seas.harvard.edu/news/home" not in href):
                article_urls.append(href)
        if self.test_mode:
            print(article_urls)
        return article_urls

    def extract_article_content(self, soup):
        content = None
        body_sections = []
        body_root = soup.select_one('div.body.field-wrapper.field--name-body')
        if body_root:
            body_sections.append(body_root)
        body_sections.extend(soup.select('div.formatted-text__body.field-name-field-body'))
        if not body_sections:
            body_sections.extend(soup.select('div.field--name-body.field--label-hidden.field__items'))

        for section in body_sections:
            if not section:
                continue
            containers = section.select('div.field__item') or [section]
            content_parts = []
            for container in containers:
                for node in container.find_all(['p', 'li']):
                    classes = node.get('class', [])
                    if classes and 'cta-button' in classes:
                        continue
                    text = node.get_text(separator=' ', strip=True)
                    if text:
                        content_parts.append(text)
            if content_parts:
                content = '\n'.join(content_parts)
                break

        if content is None:
            print("Content div not found")
        return content

    def extract_article_title(self, soup):
        
        title_div = soup.find('h1')
        if title_div:
            title = title_div.get_text()
            return title

    def extract_article_author(self, soup):

        author_div = soup.find('div', {'class': 'news__author-press'})
        if not author_div:
            return None

        author_text = author_div.get_text(separator=' ', strip=True)
        if author_text:
            if author_text.lower().startswith('by '):
                author_text = author_text[3:].strip()
            return author_text or None

        return None


    def extract_article_publish_date(self, soup):
        date_tag = soup.find('time')
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
            

            if self.test_mode=="single_topic":
                self.topic_urls = [self.topic_urls[0]]

            ## Navigate to article library and extract all the <a> tags from it
            article_urls = []
            for topic_url in self.topic_urls:
                page.goto(topic_url, wait_until="domcontentloaded")
                sleep(1)  # sleep needed to avoid bot detection
                soup = BeautifulSoup(page.content(), 'html.parser')
                topic_article_urls = self.extract_article_links(soup)
                print(f"Found {len(topic_article_urls)} in the topic {topic_url}")
                
                article_urls.extend(topic_article_urls)

                page.wait_for_timeout(200)

            normalized_urls = []
            base_url = "https://seas.harvard.edu"
            for url in article_urls:
                if not url:
                    continue
                normalized_urls.append(urljoin(base_url, url))
            article_urls = normalized_urls
            
            # Filter to only new URLs not in database
            article_urls = list(dict.fromkeys(article_urls))
            if not self.test_mode:
                article_urls = set(self.db_manager.filter_new_urls(article_urls))
                print(f"Found {len(article_urls)} new articles (out of {len(article_urls)} total)")
            
            if self.test_mode:
                print(len(article_urls))
                print(f"Articles to test: {list(article_urls)[:10]}")
                article_urls=article_urls[:3]

            ##Using the article URLs extracted, Navigate to the indevidual articles and extract the main content from it
            for article_url in tqdm(list(article_urls)):
                # URL already normalized above
                # print("navigating to: ", article_url)
                page.goto(article_url, wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                html = page.content()

                if self.test_mode:
                    print(article_url)

                soup = BeautifulSoup(html, 'html.parser')
                article_details = {
                "article_url": article_url,  
                "article_title": self.extract_article_title(soup),
                "article_author": self.extract_article_author(soup),   
                "article_publish_date": self.extract_article_publish_date(soup),
                "article_content": self.extract_article_content(soup),
                "fetched_at": self.fetched_at_date_formatted(), 
                "source_type": "Harvard School of Engineering and Applied Sciences",
                "summary":""
                }

                if self.test_mode:
                    print(article_details)
                self.all_articles_details.append(article_details)
                    
                page.wait_for_timeout(200)

            browser.close()

        return self.all_articles_details

if __name__=="__main__":
    scraper = SeasArticleScraper(headless=False, test_mode="all_topics", wait_ms=1000)
    details = scraper.scrape()

    print("sEAS News Scraper Summary")
    print(f"\n\nTotal number of articles: {len(details)}")
    blank_content = len([d for d in details if not d["article_content"] or d["article_content"].strip() == ""])
    blank_author = len([d for d in details if not d["article_author"] or d["article_author"].strip() == ""])
    blank_title = len([d for d in details if not d["article_title"] or d["article_title"].strip() == ""])
    blank_publish_date = len([d for d in details if not d["article_publish_date"] or d["article_publish_date"].strip() == ""])
    print(f"Blank article content: {blank_content}")
    print(f"Blank article author: {blank_author}")
    print(f"Blank article title: {blank_title}")
    print(f"Blank article publish date: {blank_publish_date}")










