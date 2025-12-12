"""Tests for CrimsonArticleScraper - extraction methods and scrape flow."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crimson_scraper import CrimsonArticleScraper  # noqa: E402

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_html(filename):
    path = os.path.join(_TEST_DIR, "Saved_pages", filename)
    with open(path, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture(scope="module")
def article_soup():
    return _load_html("Crimson_sample_article.html")


@pytest.fixture(scope="module")
def topic_soup():
    return _load_html("Crimson_sample_topic_page.html")


@pytest.fixture
def scraper():
    """Scraper with mocked DB manager."""
    with patch("crimson_scraper.PostgresDBManager"):
        s = CrimsonArticleScraper(headless=True, test_mode=True)
        s.db_manager = MagicMock()
        s.db_manager.filter_new_urls.return_value = []
        yield s


class TestCrimsonScraper:

    # --- Extraction tests (core functionality) ---
    def test_extract_article_links(self, scraper, topic_soup):
        links = scraper.extract_article_links(topic_soup)
        assert isinstance(links, list)
        assert len(links) > 0

    def test_extract_article_content(self, scraper, article_soup):
        content = scraper.extract_article_content(article_soup)
        assert content and len(content) > 100

    def test_extract_article_title(self, scraper, article_soup):
        title = scraper.extract_article_title(article_soup)
        assert title and len(title) > 5

    def test_extract_article_author(self, scraper, article_soup):
        author = scraper.extract_article_author(article_soup)
        assert author is not None

    def test_extract_article_publish_date(self, scraper, article_soup):
        date = scraper.extract_article_publish_date(article_soup)
        assert date and "T" in date

    def test_fetched_at_date_formatted(self, scraper):
        date = scraper.fetched_at_date_formatted()
        assert "T" in date and "+00:00" in date

    # --- Edge cases (None returns) ---
    def test_extract_content_missing(self, scraper):
        soup = BeautifulSoup("<div>empty</div>", "html.parser")
        assert scraper.extract_article_content(soup) is None

    def test_extract_date_missing(self, scraper):
        soup = BeautifulSoup("<div>no date</div>", "html.parser")
        assert scraper.extract_article_publish_date(soup) is None

    def test_extract_title_alt_class(self, scraper):
        soup = BeautifulSoup('<h1 class="css-1rfyg0l">Alt Title</h1>', "html.parser")
        assert scraper.extract_article_title(soup) == "Alt Title"

    def test_extract_author_alt_class(self, scraper):
        soup = BeautifulSoup('<span class="css-x0hxbi">Alt Author</span>', "html.parser")
        assert scraper.extract_article_author(soup) == "Alt Author"

    # --- Scrape flow test ---
    @patch("crimson_scraper.sync_playwright")
    def test_scrape_flow(self, mock_playwright, scraper, topic_soup, article_soup):
        # Setup mock browser
        mock_page = MagicMock()
        mock_page.content.side_effect = [topic_soup.prettify(), article_soup.prettify()]
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

        # Configure scraper
        scraper.topic_urls = ["http://fake-topic.com"]
        scraper.db_manager.filter_new_urls.return_value = ["https://www.thecrimson.com/article/test/"]

        results = scraper.scrape()

        assert len(results) == 1
        assert results[0]["article_url"] == "https://www.thecrimson.com/article/test/"
        assert results[0]["source_type"] == "Harvard Crimson"
        mock_browser.close.assert_called_once()
