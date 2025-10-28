# Scraper Repository

This directory contains auto-generated web scrapers that can be reused across different applications.

## Structure

```
scraper_repository/
├── scrapers/           # Individual scraper modules
│   ├── hms_harvard_edu.py
│   ├── example_com.py
│   └── ...
├── metadata/           # Metadata for each scraper
│   ├── hms_harvard_edu.json
│   ├── example_com.json
│   └── ...
└── __init__.py        # Makes this a Python package
```

## Metadata Format

Each scraper has a corresponding JSON metadata file containing:
- `domain`: The domain this scraper is designed for
- `url_pattern`: Regex pattern for matching URLs
- `fields`: List of fields extracted by the scraper
- `created_at`: Timestamp of creation
- `last_validated`: Last successful validation timestamp
- `selectors`: The CSS selectors used

## Usage

```python
from scraper_repository import get_scraper

# Get scraper by domain
scraper = get_scraper("hms.harvard.edu")
data = scraper.scrape("https://hms.harvard.edu/news/...")

# Or auto-detect from URL
scraper = get_scraper_for_url("https://hms.harvard.edu/news/...")
data = scraper.scrape(url)
```
