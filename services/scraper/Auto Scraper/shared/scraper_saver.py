"""
Utility to save validated scrapers to the repository
"""
import os
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, Any, Optional


REPO_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scraper_repository")
SCRAPERS_DIR = os.path.join(REPO_ROOT, "scrapers")
METADATA_DIR = os.path.join(REPO_ROOT, "metadata")


def ensure_directories():
    """Ensure repository directories exist"""
    os.makedirs(SCRAPERS_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)


def domain_to_filename(domain: str) -> str:
    """Convert domain to valid filename"""
    return domain.replace(".", "_")


def save_scraper(
    code: str,
    url: str,
    selectors: Dict[str, Any],
    site_name: Optional[str] = None
) -> Dict[str, str]:
    """
    Save a validated scraper to the repository.
    
    Args:
        code: The Python scraper code
        url: The URL this scraper was designed for
        selectors: The selector map used
        site_name: Optional site name
        
    Returns:
        Dictionary with 'scraper_path' and 'metadata_path'
    """
    ensure_directories()
    
    # Extract domain from URL
    parsed = urlparse(url)
    domain = parsed.netloc
    filename_base = domain_to_filename(domain)
    
    # Save the scraper code
    scraper_path = os.path.join(SCRAPERS_DIR, f"{filename_base}.py")
    with open(scraper_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # Extract field names from selectors
    fields = list(selectors.keys()) if isinstance(selectors, dict) else []
    
    # Create metadata
    metadata = {
        "domain": domain,
        "site_name": site_name or domain,
        "url_pattern": f"https?://{re.escape(domain)}/.*",
        "example_url": url,
        "fields": fields,
        "selectors": selectors,
        "created_at": datetime.now().isoformat(),
        "last_validated": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    # Save metadata
    metadata_path = os.path.join(METADATA_DIR, f"{filename_base}.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return {
        "scraper_path": scraper_path,
        "metadata_path": metadata_path,
        "domain": domain
    }


def update_scraper_validation(domain: str):
    """
    Update the last_validated timestamp for a scraper.
    
    Args:
        domain: Domain name
    """
    filename_base = domain_to_filename(domain)
    metadata_path = os.path.join(METADATA_DIR, f"{filename_base}.json")
    
    if not os.path.exists(metadata_path):
        return
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    metadata['last_validated'] = datetime.now().isoformat()
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
