"""Tests for HbsArticleScraper."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hbs_scraper import HbsArticleScraper  # noqa: E402

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_html(filename):
    path = os.path.join(_TEST_DIR, "Saved_pages", filename)
    with open(path, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture(scope="module")
def article_soup():
    return _load_html("HBS_sample_article.html")


@pytest.fixture(scope="module")
def topic_soup():
    return _load_html("HBS_sample_topic_page.html")


@pytest.fixture
def scraper():
    with patch("hbs_scraper.PostgresDBManager"):
        s = HbsArticleScraper(headless=True, test_mode=True)
        s.db_manager = MagicMock()
        s.db_manager.filter_new_urls.return_value = []
        yield s


class TestHbsScraper:

    def test_extract_article_links(self, scraper, topic_soup):
        links = scraper.extract_article_links(topic_soup)
        assert isinstance(links, list)

    def test_extract_article_content(self, scraper, article_soup):
        content = scraper.extract_article_content(article_soup)
        if content:
            assert len(content) > 50

    def test_extract_article_title(self, scraper, article_soup):
        title = scraper.extract_article_title(article_soup)
        if title:
            assert len(title) > 5

    def test_extract_article_author(self, scraper, article_soup):
        author = scraper.extract_article_author(article_soup)
        assert author is None or isinstance(author, str)

    def test_extract_article_publish_date(self, scraper, article_soup):
        date = scraper.extract_article_publish_date(article_soup)
        if date:
            assert "T" in date

    def test_fetched_at_date_formatted(self, scraper):
        date = scraper.fetched_at_date_formatted()
        assert "T" in date and "+00:00" in date

    # Edge cases
    def test_extract_content_missing(self, scraper):
        soup = BeautifulSoup("<div>empty</div>", "html.parser")
        assert scraper.extract_article_content(soup) is None

    def test_extract_content_with_author_prefix(self, scraper):
        html = '<table class="body-html-fix"><p>By Author</p><p>Content here.</p></table>'
        soup = BeautifulSoup(html, "html.parser")
        content = scraper.extract_article_content(soup)
        assert content and "Content here" in content

    def test_extract_title_missing(self, scraper):
        soup = BeautifulSoup("<div>no title</div>", "html.parser")
        assert scraper.extract_article_title(soup) is None

    def test_extract_date_missing(self, scraper):
        soup = BeautifulSoup("<div>no date</div>", "html.parser")
        assert scraper.extract_article_publish_date(soup) is None

    def test_extract_author_with_by_prefix(self, scraper):
        soup = BeautifulSoup('<table class="body-html-fix"><p>By John Doe</p></table>', "html.parser")
        assert scraper.extract_article_author(soup) == "John Doe"

    def test_extract_author_missing(self, scraper):
        soup = BeautifulSoup("<div>no author</div>", "html.parser")
        assert scraper.extract_article_author(soup) is None

    @patch("hbs_scraper.dateparser.parse", return_value=None)
    def test_extract_date_parse_fails(self, mock_parse, scraper, article_soup):
        assert scraper.extract_article_publish_date(article_soup) is None

    # Scrape flow
    @patch("hbs_scraper.sync_playwright")
    def test_scrape_flow(self, mock_playwright, scraper, topic_soup, article_soup):
        mock_page = MagicMock()
        mock_page.content.return_value = article_soup.prettify()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

        scraper.topic_urls = ["http://fake-topic.com"]
        scraper.db_manager.filter_new_urls.return_value = ["https://www.hbs.edu/news/test"]

        results = scraper.scrape()
        assert isinstance(results, list)
        mock_browser.close.assert_called_once()
