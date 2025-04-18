# crawler/enhanced_crawler.py

import os
import sys
import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urlparse
from datetime import datetime, timezone

from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Import Crawl4AI components
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# Import local components
from .exceptions import CrawlerError, CrawlingError, ContentProcessingError
from .utils import setup_logger, normalize_url, clean_text
from .ai_processor import AiProcessor

class EnhancedCrawlerClient:
    """
    An intelligent web crawler that uses Crawl4AI to extract data from web pages
    based on user instructions and uses AI to process the content.
    """
    
    def __init__(self, api_key: Optional[str] = None, user_agent: str = "Crawler/1.0"):
        """
        Initialize the enhanced crawler client with Crawl4AI.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            user_agent: User agent string to use for HTTP requests
        """
        self.logger = setup_logger("EnhancedCrawlerClient")
        load_dotenv()
        
        # Initialize AI processor
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.ai_processor = AiProcessor(api_key=self.api_key)
        
        # Configure Crawl4AI
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=[
                "--disable-gpu", 
                "--disable-dev-shm-usage", 
                "--no-sandbox"
            ],
            # Use provided user agent if specified
            user_agent=user_agent
        )
        
        # Default crawler run configuration
        self.crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Don't use cache by default
            stream=False  # Don't stream results by default
        )
        
        # Initialize crawler asynchronously during first use
        self._crawler = None
        self._crawler_initialized = False
        
    async def initialize_crawler(self):
        """
        Explicitly initialize the crawler.
        This method should be called before using the crawler in FastAPI.
        """
        if not self._crawler_initialized:
            self._crawler = AsyncWebCrawler(config=self.browser_config)
            await self._crawler.start()
            self._crawler_initialized = True
            self.logger.info("Crawler initialized")

    async def _ensure_crawler_initialized(self):
        """Ensure the crawler is initialized."""
        if not self._crawler_initialized:
            await self.initialize_crawler()
                
    async def close(self):
        """Close the AsyncWebCrawler and release resources."""
        if self._crawler_initialized and self._crawler:
            await self._crawler.close()
            self._crawler_initialized = False
            self.logger.info("Crawler closed")
            
    async def scrape_page(self, url: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape a single webpage using Crawl4AI and extract content based on instructions.
        
        Args:
            url: The URL to scrape
            instructions: Natural language instructions for what to extract
            
        Returns:
            A dictionary containing the scraped data
        """
        self.logger.info(f"Scraping URL: {url}")
        
        try:
            # Ensure crawler is initialized
            await self._ensure_crawler_initialized()
            
            # Use Crawl4AI to crawl the page
            session_id = f"session_{int(time.time())}"
            result = await self._crawler.arun(
                url=url,
                config=self.crawl_config,
                session_id=session_id
            )
            
            if not result.success:
                raise CrawlingError(url, result.error_message or "Unknown error")
            
            # Extract content from the crawl result
            html_content = result.html
            markdown_content = result.markdown.raw_markdown if result.markdown else ""
            print (markdown_content)
            
            # Parse HTML for basic data extraction
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract basic page information
            title = self._extract_title(soup)
            
            # Extract links for potential further crawling
            links = self._extract_links(soup, base_url=url)
            
            # Use AI to assess relevance if instructions provided
            if instructions:
                # Use first part of markdown content for relevance check
                content_sample = markdown_content[:5000] if markdown_content else ""
                if not content_sample:
                    paragraphs = self._extract_paragraphs(soup)
                    content_sample = "\n".join(paragraphs[:10])
                
                relevance_score, relevance_reason = self.ai_processor.analyze_relevance(
                    content=content_sample,
                    title=title,
                    instructions=instructions
                )
            else:
                relevance_score = 1.0  # Assume relevant if no instructions
                relevance_reason = "No filtering instructions provided"
            
            # If content is relevant, use AI to extract structured content
            if relevance_score >= 0.3:  # Threshold for extraction
                ai_extracted_content = self.ai_processor.extract_structured_content(
                    html_content=html_content,
                    title=title,
                    url=url,
                    instructions=instructions or "Extract main content"
                )
                
                # Prepare the result with AI-extracted content
                result_data = {
                    "url": url,
                    "title": title,
                    "markdown": markdown_content,
                    "links": links[:20],  # Limit number of links
                    "relevance": {
                        "score": relevance_score,
                        "reason": relevance_reason
                    },
                    "ai_extracted_content": ai_extracted_content,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                # If not relevant, return minimal information
                result_data = {
                    "url": url,
                    "title": title,
                    "links": links[:20],
                    "relevance": {
                        "score": relevance_score,
                        "reason": relevance_reason
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return result_data
            
        except CrawlingError as e:
            self.logger.error(f"Crawling error for {url}: {str(e)}")
            return {
                "url": url,
                "error": f"Failed to crawl page: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            return {
                "url": url,
                "error": f"Error processing page: {str(e)}"
            }
    
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
            
    async def scrape(self, 
               url: str, 
               instructions: str, 
               depth: int = 1,
               follow_external_links: bool = False,
               max_pages: int = 20) -> Dict[str, Any]:
        """
        Scrape a website and follow links up to the specified depth using Crawl4AI.
        
        Args:
            url: The URL to start scraping from
            instructions: Natural language instructions for what to extract
            depth: How many levels of links to follow (default: 1)
            follow_external_links: Whether to follow links to external domains
            max_pages: Maximum number of pages to scrape
            
        Returns:
            A dictionary containing the scraped data and metadata
        """
        start_time = time.time()
        self.logger.info(f"Starting crawl of {url} with depth {depth}")
        
        # Initialize tracking structures
        visited_urls: Set[str] = set()
        results = []
        
        # Parse the starting domain
        start_domain = urlparse(url).netloc
        
        # Create a queue of (url, current_depth) tuples
        url_queue = [(url, 0)]
        
        # Process the queue
        while url_queue and len(visited_urls) < max_pages:
            # Get the next URL and its depth
            current_url, current_depth = url_queue.pop(0)
            
            # Skip if already visited
            if current_url in visited_urls:
                continue
            
            # Mark as visited
            visited_urls.add(current_url)
            
            try:
                # Scrape the current page
                self.logger.info(f"Scraping {current_url} (depth {current_depth})")
                page_data = await self.scrape_page(
                    url=current_url,
                    instructions=instructions
                )
                
                # Add to results
                results.append(page_data)
                
                # If we haven't reached max depth, add links to queue
                if current_depth < depth:
                    links = page_data.get('links', [])
                    current_domain = urlparse(current_url).netloc
                    
                    for link in links:
                        # Skip if already visited or queued
                        if link in visited_urls or any(link == url for url, _ in url_queue):
                            continue
                        
                        # Check if link is on the same domain
                        link_domain = urlparse(link).netloc
                        if link_domain == current_domain or (follow_external_links and link_domain == start_domain):
                            url_queue.append((link, current_depth + 1))
            
            except Exception as e:
                self.logger.error(f"Error processing {current_url}: {str(e)}")
                # Add error info to results
                results.append({
                    "url": current_url,
                    "error": str(e)
                })
        
        end_time = time.time()
        
        # Prepare the final result
        result = {
            "meta": {
                "url": url,
                "instructions": instructions,
                "depth": depth,
                "follow_external_links": follow_external_links,
                "pages_crawled": len(results),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "pages": results
        }
        
        self.logger.info(f"Crawl completed. Scraped {len(results)} pages.")
        return result
    
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
    
    def export_to_markdown(self, data: Dict[str, Any], filepath: str) -> None:
        """
        Export scraped data to a Markdown file for better readability.
        
        Args:
            data: The data to export
            filepath: Path where the Markdown file will be saved
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"# Crawler Results: {data['meta']['url']}\n\n")
            f.write(f"- **Instructions:** {data['meta']['instructions']}\n")
            f.write(f"- **Depth:** {data['meta']['depth']}\n")
            f.write(f"- **Pages Crawled:** {data['meta']['pages_crawled']}\n")
            f.write(f"- **Timestamp:** {data['meta']['timestamp']}\n\n")
            
            # Write page data
            for i, page in enumerate(data['pages']):
                f.write(f"## Page {i+1}: {page.get('title', 'No Title')}\n\n")
                f.write(f"**URL:** {page['url']}\n\n")
                
                if 'error' in page:
                    f.write(f"**Error:** {page['error']}\n\n")
                else:
                    # Write AI-extracted content if available
                    if 'ai_extracted_content' in page:
                        ai_content = page['ai_extracted_content']
                        
                        if 'summary' in ai_content:
                            f.write(f"### Summary\n\n{ai_content['summary']}\n\n")
                        
                        if 'key_points' in ai_content and ai_content['key_points']:
                            f.write("### Key Points\n\n")
                            for point in ai_content['key_points']:
                                f.write(f"- {point}\n")
                            f.write("\n")
                        
                        if 'extracted_data' in ai_content and ai_content['extracted_data']:
                            f.write("### Extracted Data\n\n")
                            for key, value in ai_content['extracted_data'].items():
                                f.write(f"- **{key}:** {value}\n")
                            f.write("\n")
                    
                    # Include markdown content if available
                    if 'markdown' in page and page['markdown']:
                        f.write("### Content\n\n")
                        f.write(page['markdown'] + "...\n\n")
                    
                    # Write links
                    if 'links' in page and page['links']:
                        f.write("### Links\n\n")
                        for link in page['links'][:10]:  # Limit to 10 links
                            f.write(f"- [{link}]({link})\n")
                        f.write("\n")
                
                f.write("\n---\n\n")
        
        self.logger.info(f"Data exported to {filepath}")


# # Sync wrapper for compatibility with existing code
# class SimpleCrawlerClient:
#     """
#     A synchronous wrapper around the EnhancedCrawlerClient for backward compatibility.
#     """
    
#     def __init__(self, api_key: Optional[str] = None, user_agent: str = "Crawler/1.0"):
#         """Initialize the simple crawler client."""
#         self.enhanced_client = EnhancedCrawlerClient(api_key=api_key, user_agent=user_agent)
#         self.logger = setup_logger("SimpleCrawlerClient")
    
#     def scrape_page(self, url: str, instructions: Optional[str] = None) -> Dict[str, Any]:
#         """
#         Synchronous wrapper for scrape_page that works within FastAPI.
#         """
#         try:
#             # Instead of creating a new event loop, use asyncio.run_coroutine_threadsafe
#             # if we're in an existing event loop
#             import asyncio
            
#             try:
#                 # Check if we're already in an event loop
#                 current_loop = asyncio.get_event_loop()
#                 if current_loop.is_running():
#                     # If we're in a running event loop (FastAPI), use a different approach
#                     import concurrent.futures
#                     import functools
                    
#                     # Create a new thread with its own event loop
#                     with concurrent.futures.ThreadPoolExecutor() as executor:
#                         future = executor.submit(
#                             lambda: asyncio.run(self.enhanced_client.scrape_page(url, instructions))
#                         )
#                         return future.result()
#                 else:
#                     # If we're not in a running event loop, we can use run_until_complete
#                     return current_loop.run_until_complete(
#                         self.enhanced_client.scrape_page(url, instructions)
#                     )
#             except RuntimeError:
#                 # If no event loop is set, create a new one
#                 return asyncio.run(self.enhanced_client.scrape_page(url, instructions))
                
#         except Exception as e:
#             self.logger.error(f"Error in sync wrapper: {str(e)}")
#             return {
#                 "url": url,
#                 "error": f"Error processing page: {str(e)}"
#             }
    
#     def export_to_json(self, data: Dict[str, Any], filepath: str) -> None:
#         """Wrapper for export_to_json."""
#         self.enhanced_client.export_to_json(data, filepath)
    
#     def export_to_text(self, data: Dict[str, Any], filepath: str) -> None:
#         """Legacy method for backward compatibility."""
#         self.export_to_markdown(data, filepath)
    
#     def export_to_markdown(self, data: Dict[str, Any], filepath: str) -> None:
#         """Wrapper for export_to_markdown."""
#         self.enhanced_client.export_to_markdown(data, filepath)


# Similarly, fix the CrawlerClient class
class CrawlerClient:
    """
    A synchronous wrapper around the EnhancedCrawlerClient for backward compatibility.
    """
    
    def __init__(self, api_key: Optional[str] = None, user_agent: str = "Crawler/1.0"):
        """Initialize the crawler client."""
        self.enhanced_client = EnhancedCrawlerClient(api_key=api_key, user_agent=user_agent)
        self.logger = setup_logger("CrawlerClient")
    
    def scrape_page(self, url: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for scrape_page that works within FastAPI.
        """
        try:
            # Instead of creating a new event loop, use asyncio.run_coroutine_threadsafe
            # if we're in an existing event loop
            import asyncio
            
            try:
                # Check if we're already in an event loop
                current_loop = asyncio.get_event_loop()
                if current_loop.is_running():
                    # If we're in a running event loop (FastAPI), use a different approach
                    import concurrent.futures
                    import functools
                    
                    # Create a new thread with its own event loop
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(self.enhanced_client.scrape_page(url, instructions))
                        )
                        return future.result()
                else:
                    # If we're not in a running event loop, we can use run_until_complete
                    return current_loop.run_until_complete(
                        self.enhanced_client.scrape_page(url, instructions)
                    )
            except RuntimeError:
                # If no event loop is set, create a new one
                return asyncio.run(self.enhanced_client.scrape_page(url, instructions))
                
        except Exception as e:
            self.logger.error(f"Error in sync wrapper: {str(e)}")
            return {
                "url": url,
                "error": f"Error processing page: {str(e)}"
            }
    
    def scrape(self, 
               url: str, 
               instructions: str, 
               depth: int = 1,
               follow_external_links: bool = False,
               max_pages: int = 20) -> Dict[str, Any]:
        """
        Synchronous wrapper for the multi-page crawler that works within FastAPI.
        """
        try:
            # Similar approach as scrape_page
            import asyncio
            
            try:
                current_loop = asyncio.get_event_loop()
                if current_loop.is_running():
                    import concurrent.futures
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(
                                self.enhanced_client.scrape(
                                    url, 
                                    instructions, 
                                    depth, 
                                    follow_external_links, 
                                    max_pages
                                )
                            )
                        )
                        return future.result()
                else:
                    return current_loop.run_until_complete(
                        self.enhanced_client.scrape(
                            url, 
                            instructions, 
                            depth, 
                            follow_external_links, 
                            max_pages
                        )
                    )
            except RuntimeError:
                return asyncio.run(
                    self.enhanced_client.scrape(
                        url, 
                        instructions, 
                        depth, 
                        follow_external_links, 
                        max_pages
                    )
                )
                
        except Exception as e:
            self.logger.error(f"Error in sync wrapper: {str(e)}")
            return {
                "meta": {
                    "url": url,
                    "instructions": instructions,
                    "depth": depth,
                    "error": str(e)
                },
                "pages": [{
                    "url": url,
                    "error": f"Error processing crawl: {str(e)}"
                }]
            }
    
    def scrape_parallel(self, 
                       url: str, 
                       instructions: str, 
                       depth: int = 1,
                       follow_external_links: bool = False,
                       max_pages: int = 20,
                       max_workers: int = 5) -> Dict[str, Any]:
        """
        Legacy method that now calls the standard scrape method.
        """
        return self.scrape(url, instructions, depth, follow_external_links, max_pages)
    
    def export_to_json(self, data: Dict[str, Any], filepath: str) -> None:
        """Wrapper for export_to_json."""
        self.enhanced_client.export_to_json(data, filepath)
    
    def export_to_markdown(self, data: Dict[str, Any], filepath: str) -> None:
        """Wrapper for export_to_markdown."""
        self.enhanced_client.export_to_markdown(data, filepath)