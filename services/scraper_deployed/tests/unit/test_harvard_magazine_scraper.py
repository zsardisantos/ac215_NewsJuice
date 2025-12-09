"""Tests for HarvardMagazineArticleScraper."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harvard_magazine_scraper import HarvardMagazineArticleScraper  # noqa: E402

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_html(filename):
    path = os.path.join(_TEST_DIR, "Saved_pages", filename)
    with open(path, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture(scope="module")
def article_soup():
    return _load_html("Harvard_Magazine_sample_article.html")


@pytest.fixture(scope="module")
def topic_soup():
    return _load_html("Harvard_Magazine_sample_topic_page.html")


@pytest.fixture
def scraper():
    with patch("harvard_magazine_scraper.PostgresDBManager"):
        s = HarvardMagazineArticleScraper(headless=True, test_mode=True)
        s.db_manager = MagicMock()
        s.db_manager.filter_new_urls.return_value = []
        yield s


class TestHarvardMagazineScraper:

    def test_extract_article_links(self, scraper, topic_soup):
        links = scraper.extract_article_links(topic_soup)
        assert isinstance(links, list)

    def test_extract_article_content(self, scraper, article_soup):
        content = scraper.extract_article_content(article_soup)
        assert content and len(content) > 50

    def test_extract_article_title(self, scraper, article_soup):
        title = scraper.extract_article_title(article_soup)
        assert title and len(title) > 5

    def test_extract_article_author(self, scraper, article_soup):
        author = scraper.extract_article_author(article_soup)
        assert author is None or isinstance(author, str)

    def test_extract_article_publish_date(self, scraper, article_soup):
        date = scraper.extract_article_publish_date(article_soup)
        assert date and "T" in date

    def test_fetched_at_date_formatted(self, scraper):
        date = scraper.fetched_at_date_formatted()
        assert "T" in date and "+00:00" in date

    # Scrape flow
    @patch("harvard_magazine_scraper.sync_playwright")
    def test_scrape_flow(self, mock_playwright, scraper, topic_soup, article_soup):
        mock_page = MagicMock()
        mock_page.content.side_effect = [topic_soup.prettify(), article_soup.prettify()]
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

        scraper.topic_urls = ["http://fake-topic.com"]
        scraper.db_manager.filter_new_urls.return_value = ["https://harvardmagazine.com/test"]

        results = scraper.scrape()
        assert len(results) == 1
        mock_browser.close.assert_called_once()
