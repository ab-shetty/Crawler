# crawler/crawler_client.py

import time
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urlparse
import concurrent.futures
from collections import deque
import os

from .client import SimpleCrawlerClient
from .exceptions import CrawlerError, CrawlingError
from .utils import setup_logger, normalize_url

class CrawlerClient:
    """
    An intelligent web crawler that can extract data from multiple pages
    based on user instructions.
    """
    
    def __init__(self, user_agent: str = "Crawler/1.0"):
        """
        Initialize the crawler client.
        
        Args:
            user_agent: User agent string to use for HTTP requests
        """
        self.logger = setup_logger("CrawlerClient")
        self.simple_client = SimpleCrawlerClient(user_agent=user_agent)
    
    def scrape(self, 
               url: str, 
               instructions: str, 
               depth: int = 2,
               follow_external_links: bool = False,
               max_pages: int = 20,
               max_workers: int = 5) -> Dict[str, Any]:
        """
        Scrape a website and follow links up to the specified depth.
        
        Args:
            url: The URL to start scraping from
            instructions: Natural language instructions for what to extract
            depth: How many levels of links to follow (default: 2)
            follow_external_links: Whether to follow links to external domains
            max_pages: Maximum number of pages to scrape
            max_workers: Maximum number of concurrent workers for scraping
            
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
        url_queue = deque([(url, 0)])
        
        # Process the queue
        while url_queue and len(visited_urls) < max_pages:
            # Get the next URL and its depth
            current_url, current_depth = url_queue.popleft()
            
            # Skip if already visited
            if current_url in visited_urls:
                continue
            
            # Mark as visited
            visited_urls.add(current_url)
            
            try:
                # Scrape the current page
                self.logger.info(f"Scraping {current_url} (depth {current_depth})")
                page_data = self.simple_client.scrape_page(
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
                        if link in visited_urls:
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
                "time_taken": end_time - start_time,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "pages": results
        }
        
        self.logger.info(f"Crawl completed. Scraped {len(results)} pages.")
        return result
    
    def scrape_parallel(self, 
                       url: str, 
                       instructions: str, 
                       depth: int = 2,
                       follow_external_links: bool = False,
                       max_pages: int = 20,
                       max_workers: int = 5) -> Dict[str, Any]:
        """
        Scrape a website in parallel using multiple threads.
        
        Args:
            url: The URL to start scraping from
            instructions: Natural language instructions for what to extract
            depth: How many levels of links to follow
            follow_external_links: Whether to follow links to external domains
            max_pages: Maximum number of pages to scrape
            max_workers: Maximum number of concurrent workers
            
        Returns:
            A dictionary containing the scraped data and metadata
        """
        start_time = time.time()
        self.logger.info(f"Starting parallel crawl of {url} with depth {depth}")
        
        # Initialize tracking structures
        visited_urls: Set[str] = set()
        visited_urls.add(url)  # Mark start URL as visited
        results = []
        
        # Parse the starting domain
        start_domain = urlparse(url).netloc
        
        # First, scrape the starting page
        try:
            start_page_data = self.simple_client.scrape_page(
                url=url,
                instructions=instructions
            )
            results.append(start_page_data)
            
            # Extract links for first level
            links_to_crawl = []
            for link in start_page_data.get('links', []):
                if link not in visited_urls:
                    link_domain = urlparse(link).netloc
                    if link_domain == start_domain or (follow_external_links):
                        links_to_crawl.append((link, 1))  # depth 1
                        visited_urls.add(link)  # Mark as visited
            
            # Function for parallel execution
            def process_url(url_depth_tuple):
                url, depth = url_depth_tuple
                try:
                    page_data = self.simple_client.scrape_page(
                        url=url,
                        instructions=instructions
                    )
                    
                    next_links = []
                    if depth < depth:
                        for link in page_data.get('links', []):
                            if link not in visited_urls:
                                link_domain = urlparse(link).netloc
                                if link_domain == start_domain or (follow_external_links):
                                    next_links.append((link, depth + 1))
                    
                    return {
                        "page_data": page_data,
                        "next_links": next_links
                    }
                except Exception as e:
                    self.logger.error(f"Error processing {url}: {str(e)}")
                    return {
                        "page_data": {
                            "url": url,
                            "error": str(e)
                        },
                        "next_links": []
                    }
            
            # Process URLs in parallel at each depth level
            current_depth = 1
            while current_depth <= depth and links_to_crawl and len(results) < max_pages:
                self.logger.info(f"Processing {len(links_to_crawl)} URLs at depth {current_depth}")
                
                # Limit the number of URLs to process based on max_pages
                remaining_capacity = max_pages - len(results)
                urls_to_process = links_to_crawl[:remaining_capacity]
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_url = {executor.submit(process_url, url_depth): url_depth 
                                    for url_depth in urls_to_process}
                    
                    next_level_links = []
                    for future in concurrent.futures.as_completed(future_to_url):
                        url_depth = future_to_url[future]
                        try:
                            data = future.result()
                            results.append(data["page_data"])
                            next_level_links.extend(data["next_links"])
                        except Exception as e:
                            self.logger.error(f"Thread error for {url_depth[0]}: {str(e)}")
                
                # Update links for next depth level
                links_to_crawl = next_level_links
                current_depth += 1
                
                # Update visited set
                for link, _ in links_to_crawl:
                    visited_urls.add(link)
        
        except Exception as e:
            self.logger.error(f"Error processing start URL {url}: {str(e)}")
            results.append({
                "url": url,
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
                "time_taken": end_time - start_time,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "pages": results
        }
        
        self.logger.info(f"Parallel crawl completed. Scraped {len(results)} pages.")
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
            f.write(f"- **Time Taken:** {data['meta']['time_taken']:.2f} seconds\n")
            f.write(f"- **Timestamp:** {data['meta']['timestamp']}\n\n")
            
            # Write page data
            for i, page in enumerate(data['pages']):
                f.write(f"## Page {i+1}: {page.get('title', 'No Title')}\n\n")
                f.write(f"**URL:** {page['url']}\n\n")
                
                if 'error' in page:
                    f.write(f"**Error:** {page['error']}\n\n")
                else:
                    f.write("### Content\n\n")
                    for paragraph in page.get('paragraphs', []):
                        f.write(f"{paragraph}\n\n")
                    
                    f.write("### Links\n\n")
                    for link in page.get('links', [])[:10]:  # Limit to 10 links
                        f.write(f"- [{link}]({link})\n")
                
                f.write("\n---\n\n")
        
        self.logger.info(f"Data exported to {filepath}")


# Example usage
if __name__ == "__main__":
    # For testing the client independently
    client = CrawlerClient()
    result = client.scrape(
        url="https://example.com",
        instructions="Extract information about products and services",
        depth=1,
        max_pages=5
    )
    
    print(f"Crawled {result['meta']['pages_crawled']} pages:")
    for i, page in enumerate(result['pages']):
        print(f"{i+1}. {page.get('title', 'No title')} - {page['url']}")
    
    # Example export
    client.export_to_json(result, "crawler_results.json")
    client.export_to_markdown(result, "crawler_results.md")