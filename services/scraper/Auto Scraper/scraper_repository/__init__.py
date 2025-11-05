"""
Scraper Repository - Auto-generated web scrapers for reuse
"""
import os
import json
import importlib.util
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import re


SCRAPERS_DIR = os.path.join(os.path.dirname(__file__), "scrapers")
METADATA_DIR = os.path.join(os.path.dirname(__file__), "metadata")


def get_scraper(domain: str):
    """
    Get a scraper module by domain name.
    
    Args:
        domain: Domain name (e.g., "hms.harvard.edu")
        
    Returns:
        Scraper module with a scrape() function
        
    Raises:
        FileNotFoundError: If scraper doesn't exist
    """
    # Convert domain to filename (replace dots with underscores)
    filename = domain.replace(".", "_") + ".py"
    filepath = os.path.join(SCRAPERS_DIR, filename)
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No scraper found for domain: {domain}")
    
    # Load the module dynamically
    spec = importlib.util.spec_from_file_location(f"scraper_{domain}", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return module


def get_scraper_metadata(domain: str) -> Dict[str, Any]:
    """
    Get metadata for a scraper.
    
    Args:
        domain: Domain name (e.g., "hms.harvard.edu")
        
    Returns:
        Dictionary containing scraper metadata
    """
    filename = domain.replace(".", "_") + ".json"
    filepath = os.path.join(METADATA_DIR, filename)
    
    if not os.path.exists(filepath):
        return {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_scraper_for_url(url: str):
    """
    Auto-detect and return the appropriate scraper for a URL.
    
    Args:
        url: The URL to scrape
        
    Returns:
        Scraper module with a scrape() function
        
    Raises:
        FileNotFoundError: If no matching scraper is found
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Try exact domain match first
    try:
        return get_scraper(domain)
    except FileNotFoundError:
        pass
    
    # Try pattern matching against all scrapers
    if not os.path.exists(METADATA_DIR):
        raise FileNotFoundError(f"No scraper found for URL: {url}")
    
    for metadata_file in os.listdir(METADATA_DIR):
        if not metadata_file.endswith('.json'):
            continue
            
        with open(os.path.join(METADATA_DIR, metadata_file), 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        url_pattern = metadata.get('url_pattern', '')
        if url_pattern and re.match(url_pattern, url):
            domain = metadata['domain']
            return get_scraper(domain)
    
    raise FileNotFoundError(f"No scraper found for URL: {url}")


def list_scrapers() -> list:
    """
    List all available scrapers.
    
    Returns:
        List of dictionaries containing scraper info
    """
    scrapers = []
    
    if not os.path.exists(METADATA_DIR):
        return scrapers
    
    for metadata_file in os.listdir(METADATA_DIR):
        if not metadata_file.endswith('.json'):
            continue
            
        with open(os.path.join(METADATA_DIR, metadata_file), 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            scrapers.append(metadata)
    
    return scrapers


__all__ = ['get_scraper', 'get_scraper_for_url', 'get_scraper_metadata', 'list_scrapers']
