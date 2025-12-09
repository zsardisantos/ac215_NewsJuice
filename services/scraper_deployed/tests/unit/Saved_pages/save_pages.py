"""Utility script to download HTML snapshots for a list of URLs using Playwright.

Edit the URLS_TO_SAVE list with the pages you want to capture. Each entry must
provide the target URL and the filename (with or without the .html extension)
that should be written into the output directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from playwright.sync_api import sync_playwright

BASE_OUTPUT_DIR = Path(__file__).parent

# Populate this list with (url, output_name) pairs.
URLS_TO_SAVE: list[Tuple[str, str]] = [
    ["https://www.thecrimson.com/section/news/", "Crimson_sample_topic_page.html"],
    [
        "https://www.thecrimson.com/article/2025/11/16/trump-summers-epstein-doj/",
        "Crimson_sample_article.html",
    ],
    ["https://gsas.harvard.edu/news/topic/commencement", "GSAS_sample_topic_page.html"],
    [
        "https://news.harvard.edu/gazette/story/2025/05/searching-for-answers-to-lifes-" "big-questions/",
        "GSAS_sample_article.html",
    ],
    [
        "https://www.harvardmagazine.com/topic/arts-culture",
        "Harvard_Magazine_sample_topic_page.html",
    ],
    [
        "https://www.harvardmagazine.com/university-news/marla-frederick-harvard-" "divinity-school",
        "Harvard_Magazine_sample_article.html",
    ],
    [
        "https://www.hbs.edu/news/Pages/browse.aspx?format=Article&source=Harvard%20" "Business%20School",
        "HBS_sample_topic_page.html",
    ],
    [
        "https://www.hbs.edu/news/articles/Pages/sabrina-howell-profile-2025.aspx",
        "HBS_sample_article.html",
    ],
    ["https://www.hks.harvard.edu/news-announcements", "HKS_sample_topic_page.html"],
    [
        "https://www.hks.harvard.edu/announcements/harvard-impact-labs-announces-"
        "inaugural-group-faculty-members-working-tackle-todays",
        "HKS_sample_article.html",
    ],
    ["https://hls.harvard.edu/today/archive/", "HLS_sample_topic_page.html"],
    [
        "https://hls.harvard.edu/today/global-hopes-still-pinned-to-international-" "law/",
        "HLS_sample_article.html",
    ],
    ["https://hms.harvard.edu/news", "HMS_sample_topic_page.html"],
    [
        "https://hms.harvard.edu/news/using-click-chemistry-drug-undruggable-" "tumor-suppressors",
        "HMS_sample_article.html",
    ],
    ["https://seas.harvard.edu/news", "SEAS_sample_topic_page.html"],
    [
        "https://seas.harvard.edu/news/2025/11/alumni-profile-nick-waldo-ab-13",
        "SEAS_sample_article.html",
    ],
    [
        "https://news.harvard.edu/gazette/story/2025/11/solving-mystery-at-tip-of-" "south-america/",
        "Gazette_sample_article.html",
    ],
]

# Optional extra delay (in milliseconds) after each navigation to allow the
# page to finish rendering before the HTML snapshot is taken.
POST_NAVIGATION_WAIT_MS = 500


def save_pages(
    url_filename_pairs: Iterable[Tuple[str, str]],
    wait_ms: int = POST_NAVIGATION_WAIT_MS,
    headless: bool = False,
) -> None:
    """Visit each URL with Playwright and persist the rendered HTML."""
    pairs = list(url_filename_pairs)
    if not pairs:
        raise ValueError("URL list is empty. Populate URLS_TO_SAVE before running the script.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        try:
            for url, output_name in pairs:
                print(f"Fetching {url} -> {output_name}")
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                if wait_ms:
                    page.wait_for_timeout(wait_ms)
                html = page.content()
                output_path = Path(output_name)
                if not output_path.is_absolute():
                    output_path = BASE_OUTPUT_DIR / output_path
                if output_path.suffix.lower() != ".html":
                    output_path = output_path.with_suffix(".html")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(html, encoding="utf-8")
                print(f"Saved {output_path}")
        finally:
            browser.close()


if __name__ == "__main__":
    save_pages(URLS_TO_SAVE)
