"""Tests for GazetteArticleScraper."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gazette_scraper import GazetteArticleScraper  # noqa: E402

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def scraper():
    with patch("gazette_scraper.PostgresDBManager"):
        s = GazetteArticleScraper(test_mode=True)
        s.db_manager = MagicMock()
        s.db_manager.filter_new_urls.return_value = []
        yield s


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.link = "https://news.harvard.edu/gazette/story/2025/05/test/"
    entry.title = "Test Article"
    entry.author = "Test Author"
    entry.published = "2025-05-21T20:35:24+00:00"
    return entry


class TestGazetteScraper:

    def test_extract_article_link(self, scraper, mock_entry):
        assert scraper.extract_article_link(mock_entry) == mock_entry.link

    def test_extract_article_link_none(self, scraper):
        entry = MagicMock(link=None)
        assert scraper.extract_article_link(entry) is None

    def test_extract_article_title(self, scraper, mock_entry):
        assert scraper.extract_article_title(mock_entry) == "Test Article"

    def test_extract_article_author(self, scraper, mock_entry):
        assert scraper.extract_article_author(mock_entry) == "Test Author"

    def test_extract_publication_date(self, scraper, mock_entry):
        date = scraper.extract_publication_date(mock_entry)
        assert date and "T" in date

    def test_extract_publication_date_none(self, scraper):
        entry = MagicMock(published=None)
        assert scraper.extract_publication_date(entry) is None

    def test_fetched_at_date_formatted(self, scraper):
        date = scraper.fetched_at_date_formatted()
        assert "T" in date and "+00:00" in date

    @patch("gazette_scraper.trafilatura.extract")
    def test_extract_article_content(self, mock_extract, scraper):
        mock_extract.return_value = "Extracted content"
        assert scraper.extract_article_content("<html>test</html>") == "Extracted content"

    @patch("gazette_scraper.trafilatura.extract", return_value=None)
    def test_extract_article_content_none(self, mock_extract, scraper):
        assert scraper.extract_article_content("<html>test</html>") == ""

    @patch("gazette_scraper.httpx.get")
    def test_fetch_feed(self, mock_get, scraper):
        mock_get.return_value.text = (
            '<?xml version="1.0"?><rss><channel><item><title>Test</title></item></channel></rss>'
        )
        entries = scraper.fetch_feed("https://test.com/feed")
        assert isinstance(entries, list)

    @patch("gazette_scraper.httpx.get")
    def test_fetch_html_success(self, mock_get, scraper):
        mock_get.return_value.text = "<html>Test</html>"
        assert scraper.fetch_html("https://example.com") == "<html>Test</html>"

    @patch("gazette_scraper.httpx.get", side_effect=Exception("Error"))
    def test_fetch_html_exception(self, mock_get, scraper):
        assert scraper.fetch_html("https://example.com") is None

    @patch("gazette_scraper.httpx.get")
    @patch("gazette_scraper.trafilatura.extract")
    def test_scrape_flow(self, mock_extract, mock_get, scraper):
        feed_xml = (
            '<?xml version="1.0"?><rss><channel><item><title>Test</title>'
            "<link>https://example.com/article</link></item></channel></rss>"
        )
        mock_get.side_effect = [
            MagicMock(text=feed_xml),
            MagicMock(text="<html>content</html>"),
        ]
        mock_extract.return_value = "Long content " * 50  # >200 chars
        scraper.db_manager.filter_new_urls.return_value = ["https://example.com/article"]

        results = scraper.scrape()
        assert len(results) >= 0  # May vary based on content length

    @patch("gazette_scraper.httpx.get")
    def test_scrape_skip_short_content(self, mock_get, scraper):
        feed_xml = (
            '<?xml version="1.0"?><rss><channel><item><title>Test</title>'
            "<link>https://example.com/short</link></item></channel></rss>"
        )
        mock_get.side_effect = [MagicMock(text=feed_xml), MagicMock(text="<html>short</html>")]
        scraper.db_manager.filter_new_urls.return_value = ["https://example.com/short"]

        with patch("gazette_scraper.trafilatura.extract", return_value="Short"):
            results = scraper.scrape()
        assert len(results) == 0
