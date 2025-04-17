# crawler/client.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import os
from typing import Dict, Any, List, Optional, Set
import logging
import json

from .exceptions import CrawlerError as SimpleCrawlerError
from .utils import setup_logger, normalize_url, clean_text
from .ai_processor import AiProcessor

class SimpleCrawlerClient:
    """
    A web crawler client that uses AI to extract content from webpages
    based on user-defined instructions.
    """
    
    def __init__(self, api_key: Optional[str] = None, user_agent: str = "Crawler/1.0"):
        """
        Initialize the crawler client.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            user_agent: User agent string to use for HTTP requests
        """
        self.logger = setup_logger("SimpleCrawlerClient")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent
        })
        
        # Initialize AI processor
        self.ai_processor = AiProcessor(api_key=api_key)
    
    def scrape_page(self, url: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape a single webpage and extract content based on instructions.
        
        Args:
            url: The URL to scrape
            instructions: Natural language instructions for what to extract
            
        Returns:
            A dictionary containing the scraped data
        """
        self.logger.info(f"Scraping URL: {url}")
        
        try:
            # Fetch the page
            response = self._fetch_page(url)
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic page information
            title = self._extract_title(soup)
            
            # Extract links for potential further crawling
            links = self._extract_links(soup, base_url=url)
            
            # Use AI to assess relevance
            if instructions:
                paragraphs = self._extract_paragraphs(soup)
                content_text = "\n".join(paragraphs[:10])  # Use first 10 paragraphs for relevance check
                relevance_score, relevance_reason = self.ai_processor.analyze_relevance(
                    content=content_text,
                    title=title,
                    instructions=instructions
                )
            else:
                relevance_score = 1.0  # Assume relevant if no instructions
                relevance_reason = "No filtering instructions provided"
            
            # If content is relevant, use AI to extract structured content
            if relevance_score >= 0.3:  # Threshold for extraction
                ai_extracted_content = self.ai_processor.extract_structured_content(
                    html_content=response.text,
                    title=title,
                    url=url,
                    instructions=instructions or "Extract main content"
                )
                
                # Prepare the result with AI-extracted content
                result = {
                    "url": url,
                    "title": title,
                    "links": links[:10],  # Limit to 10 links
                    "relevance": {
                        "score": relevance_score,
                        "reason": relevance_reason
                    },
                    "ai_extracted_content": ai_extracted_content,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            else:
                # If not relevant, return minimal information
                result = {
                    "url": url,
                    "title": title,
                    "links": links[:10],
                    "relevance": {
                        "score": relevance_score,
                        "reason": relevance_reason
                    },
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            
            return result
            
        except requests.RequestException as e:
            self.logger.error(f"Request error for {url}: {str(e)}")
            return {
                "url": url,
                "error": f"Failed to fetch page: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            return {
                "url": url,
                "error": f"Error processing page: {str(e)}"
            }
    
    def _fetch_page(self, url: str) -> requests.Response:
        """
        Fetch a webpage with error handling and retries.
        
        Args:
            url: The URL to fetch
            
        Returns:
            The HTTP response
            
        Raises:
            requests.RequestException: If the request fails after retries
        """
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()  # Raise exception for HTTP errors
                return response
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Attempt {attempt+1} failed for {url}: {str(e)}. Retrying...")
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    self.logger.error(f"All {max_retries} attempts failed for {url}")
                    raise
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        title_tag = soup.find('title')
        if title_tag and title_tag.text:
            return clean_text(title_tag.text)
        
        # Fallback to h1 if title tag is missing
        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.text:
            return clean_text(h1_tag.text)
        
        return "No title found"
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """Extract all paragraph text from the page."""
        paragraphs = []
        
        # Extract text from paragraph tags
        for p_tag in soup.find_all('p'):
            if p_tag.text and len(p_tag.text.strip()) > 0:
                paragraphs.append(clean_text(p_tag.text))
        
        # If no paragraphs found, try to extract text from div tags
        if not paragraphs:
            for div_tag in soup.find_all('div'):
                if div_tag.text and len(div_tag.text.strip()) > 0:
                    # Skip divs that contain mostly other HTML elements
                    if len(div_tag.find_all()) < 3:
                        paragraphs.append(clean_text(div_tag.text))
        
        return paragraphs
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from the page."""
        links = []
        seen_urls = set()
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            normalized_url = normalize_url(base_url, href)
            
            if normalized_url and normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                links.append(normalized_url)
        
        return links
    
    def export_to_json(self, data: Dict[str, Any], filepath: str) -> None:
        """
        Export scraped data to a JSON file.
        
        Args:
            data: The data to export
            filepath: Path where the JSON file will be saved
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Data exported to {filepath}")
    
    def export_to_text(self, data: Dict[str, Any], filepath: str) -> None:
        """
        Export scraped data to a plain text file.
        
        Args:
            data: The data to export
            filepath: Path where the text file will be saved
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Crawler Results for {data['url']}\n")
            f.write(f"Title: {data['title']}\n\n")
            
            if 'ai_extracted_content' in data:
                ai_content = data['ai_extracted_content']
                
                f.write("--- AI-Extracted Content ---\n")
                f.write(f"Summary: {ai_content.get('summary', 'N/A')}\n\n")
                
                f.write("Key Points:\n")
                for i, point in enumerate(ai_content.get('key_points', [])):
                    f.write(f"{i+1}. {point}\n")
                f.write("\n")
                
                if 'extracted_data' in ai_content:
                    f.write("Extracted Data:\n")
                    for key, value in ai_content['extracted_data'].items():
                        f.write(f"- {key}: {value}\n")
                    f.write("\n")
            
            if 'error' in data:
                f.write(f"Error: {data['error']}\n")
            
            f.write("\n--- Links ---\n")
            for link in data.get('links', []):
                f.write(f"* {link}\n")
        
        self.logger.info(f"Data exported to {filepath}")