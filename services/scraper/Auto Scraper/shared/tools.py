"""
Shared tools used by all agents.
"""

import requests
import subprocess
import sys
import tempfile
import os
from typing import Optional
from .scraper_saver import save_scraper as _save_scraper


def fetch_webpage(url: str) -> str:
    """
    Fetches the raw HTML content of a webpage.
    
    Args:
        url: The URL of the webpage to fetch
        
    Returns:
        The raw HTML content as a string
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error fetching webpage: {str(e)}"


def test_selector(url: str, selector: str, attribute: str = "") -> str:
    """
    Tests a CSS selector on a URL and shows what it finds.
    Helps the analyst verify selectors before generating the full Selector Map.
    
    Args:
        url: The URL to test against
        selector: The CSS selector to test (e.g., "h1.title", "article.content")
        attribute: Optional attribute to extract (e.g., "href", "datetime"). Leave empty for text content.
        
    Returns:
        A report showing what the selector matched and the extracted data
    """
    try:
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        report = f"Testing selector: '{selector}' on {url}\n"
        report += "=" * 80 + "\n\n"
        
        # Try select_one (single element)
        element = soup.select_one(selector)
        if element:
            report += f"✓ Found 1 element with select_one()\n"
            report += f"  Tag: <{element.name}>\n"
            report += f"  Classes: {element.get('class', [])}\n"
            report += f"  ID: {element.get('id', 'N/A')}\n"
            
            if attribute and attribute.strip():
                value = element.get(attribute)
                report += f"  Attribute '{attribute}': {value}\n"
            else:
                text = element.get_text(strip=True)
                report += f"  Text (first 200 chars): {text[:200]}\n"
                report += f"  Text length: {len(text)} characters\n"
        else:
            report += f"✗ No element found with select_one()\n"
        
        # Try select (multiple elements)
        elements = soup.select(selector)
        report += f"\n{len(elements)} total elements found with select()\n"
        
        if elements and len(elements) > 1:
            report += "\nFirst 3 matches:\n"
            for i, elem in enumerate(elements[:3]):
                text = elem.get_text(strip=True)
                report += f"  [{i+1}] {text[:100]}...\n"
        
        return report
        
    except Exception as e:
        return f"Error testing selector: {str(e)}"


def analyze_html_structure(url: str, focus_area: str = "main content") -> str:
    """
    Fetches a webpage and provides a structured analysis of its HTML.
    Helps identify the best selectors for scraping.
    
    Args:
        url: The URL to analyze
        focus_area: What to focus on (e.g., "main content", "article body", "author info")
        
    Returns:
        A structured report of HTML elements and suggested selectors
    """
    try:
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        report = f"HTML Structure Analysis for: {url}\n"
        report += "=" * 80 + "\n\n"
        
        # Analyze main content containers
        report += "MAIN CONTENT CONTAINERS:\n"
        for tag in ['main', 'article', 'div[role="main"]']:
            elements = soup.select(tag)
            if elements:
                for i, elem in enumerate(elements[:3]):  # Limit to first 3
                    classes = ' '.join(elem.get('class', []))
                    id_attr = elem.get('id', '')
                    report += f"  - <{elem.name}> "
                    if id_attr:
                        report += f"id='{id_attr}' "
                    if classes:
                        report += f"class='{classes}' "
                    # Show first 100 chars of text
                    text_preview = elem.get_text(strip=True)[:100]
                    report += f"\n    Text preview: {text_preview}...\n"
        
        report += "\nHEADINGS (H1-H2):\n"
        for heading in soup.find_all(['h1', 'h2'])[:5]:
            classes = ' '.join(heading.get('class', []))
            report += f"  - <{heading.name}> class='{classes}': {heading.get_text(strip=True)}\n"
        
        report += "\nTIME/DATE ELEMENTS:\n"
        for time_elem in soup.find_all('time')[:3]:
            datetime_attr = time_elem.get('datetime', '')
            classes = ' '.join(time_elem.get('class', []))
            report += f"  - <time> class='{classes}' datetime='{datetime_attr}': {time_elem.get_text(strip=True)}\n"
        
        report += "\nAUTHOR-RELATED ELEMENTS:\n"
        # Check meta tags
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta:
            report += f"  - <meta name='author' content='{author_meta.get('content', '')}'/>\n"
        
        # Check for author-related classes
        for selector in ['.author', '.byline', '[rel="author"]', '.writer', '.post-author']:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:2]:
                    report += f"  - {selector}: {elem.get_text(strip=True)}\n"
        
        report += "\nLARGE TEXT BLOCKS (potential content):\n"
        for tag in ['article', 'main', '.content', '.article-body', '.post-content', '.entry-content']:
            elements = soup.select(tag)
            for elem in elements[:2]:
                text = elem.get_text(strip=True)
                if len(text) > 200:  # Only show substantial content
                    classes = ' '.join(elem.get('class', []))
                    report += f"  - <{elem.name}> class='{classes}'\n"
                    report += f"    Length: {len(text)} chars\n"
                    report += f"    Preview: {text[:150]}...\n\n"
        
        return report
        
    except Exception as e:
        return f"Error analyzing HTML structure: {str(e)}"


def execute_code(code: str, test_url: str) -> dict:
    """
    Executes Python scraper code and returns the result.
    
    Args:
        code: The Python code to execute (must define a 'scrape' function)
        test_url: The URL to test the scraper against
        
    Returns:
        A dictionary with 'success' (bool), 'output' (str), and 'error' (str) keys
    """
    try:
        # Create a temporary file to execute the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            # Remove any existing if __name__ == '__main__' block from the code
            # to avoid conflicts with our wrapper
            code_lines = code.split('\n')
            cleaned_code = []
            skip_main_block = False

 # test if the prompt engineering is enough            
            for line in code_lines:
                if "if __name__ ==" in line:
                    skip_main_block = True
                    continue
                if skip_main_block:
                    # Check if we're still in the main block
                    if line.strip() == "":
                        # Empty line - skip it
                        continue
                    elif line and line[0] not in (' ', '\t'):
                        # Non-indented line - we've exited the main block
                        skip_main_block = False
                        # Don't continue - process this line normally
                    else:
                        # Indented line - still in the main block, skip it
                        continue
                
                if not skip_main_block:
                    cleaned_code.append(line)
            
            code_cleaned = '\n'.join(cleaned_code)
            
            # Wrap the code to capture output and invoke the scrape function
            wrapped_code = f"""{code_cleaned}

# Execute the scraper
if __name__ == '__main__':
    import json
    try:
        result = scrape('{test_url}')
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"EXECUTION_ERROR: {{str(e)}}")
"""
            f.write(wrapped_code)
            temp_file = f.name
        
        # Execute the code
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'  # Replace invalid UTF-8 bytes with �
        )
        
        # Clean up
        os.unlink(temp_file)
        
        output = result.stdout if result.stdout else ""
        error = result.stderr if result.stderr else ""
        
        if result.returncode != 0 or "EXECUTION_ERROR" in output:
            return {
                "success": False,
                "output": output,
                "error": error or "Code execution failed",
                "debug_info": f"STDOUT:\n{output}\n\nSTDERR:\n{error}"
            }
        
        return {
            "success": True,
            "output": output,
            "error": "",
            "debug_info": f"STDOUT:\n{output}"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Code execution timed out (30s limit)"
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }


def save_scraper_to_repository(code: str, url: str, selectors: dict, site_name: Optional[str] = None) -> dict:
    """
    Save the validated scraper to the repository for reuse.
    """
    try:
        result = _save_scraper(code, url, selectors, site_name)
        return {
            "success": True,
            "message": f"Scraper saved successfully for domain: {result['domain']}",
            "scraper_path": result['scraper_path'],
            "metadata_path": result['metadata_path'],
            "domain": result['domain']
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to save scraper: {str(e)}"
        }
