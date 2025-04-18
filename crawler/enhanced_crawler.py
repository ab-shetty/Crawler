# enhanced_crawler.py (Refactored for RAG-friendly Markdown)

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

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from .exceptions import CrawlingError
from .utils import setup_logger, normalize_url, clean_text
from .ai_processor import AiProcessor

class EnhancedCrawlerClient:
    def __init__(self, api_key: Optional[str] = None, user_agent: str = "Crawler/1.0"):
        self.logger = setup_logger("EnhancedCrawlerClient")
        load_dotenv()

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.ai_processor = AiProcessor(api_key=self.api_key)

        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
            user_agent=user_agent
        )

        self.crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)

        self._crawler = None
        self._crawler_initialized = False

    async def initialize_crawler(self):
        if not self._crawler_initialized:
            self._crawler = AsyncWebCrawler(config=self.browser_config)
            await self._crawler.start()
            self._crawler_initialized = True
            self.logger.info("Crawler initialized")

    async def _ensure_crawler_initialized(self):
        if not self._crawler_initialized:
            await self.initialize_crawler()

    async def close(self):
        if self._crawler_initialized and self._crawler:
            await self._crawler.close()
            self._crawler_initialized = False
            self.logger.info("Crawler closed")

    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_tag = soup.find('title')
        if title_tag and title_tag.text:
            return clean_text(title_tag.text)
        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.text:
            return clean_text(h1_tag.text)
        return "No title found"

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        links = []
        seen_urls = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            normalized_url = normalize_url(base_url, href)
            if normalized_url and normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                links.append(normalized_url)
        return links

    def _extract_structured_markdown(self, soup: BeautifulSoup) -> str:
        lines = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li', 'pre', 'code']):
            name = tag.name.lower()
            text = clean_text(tag.get_text(" ", strip=True))
            if not text:
                continue
            if name == 'h1':
                lines.append(f"# {text}")
            elif name == 'h2':
                lines.append(f"## {text}")
            elif name == 'h3':
                lines.append(f"### {text}")
            elif name == 'p':
                lines.append(text)
            elif name == 'li':
                lines.append(f"- {text}")
            elif name == 'pre' or name == 'code':
                lines.append(f"```\n{text}\n```")
        return "\n\n".join(lines)

    async def scrape_page(self, url: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        self.logger.info(f"Scraping URL: {url}")
        try:
            await self._ensure_crawler_initialized()
            session_id = f"session_{int(time.time())}"
            result = await self._crawler.arun(url=url, config=self.crawl_config, session_id=session_id)

            if not result.success:
                raise CrawlingError(url, result.error_message or "Unknown error")

            html_content = result.html
            soup = BeautifulSoup(html_content, 'html.parser')
            title = self._extract_title(soup)
            links = self._extract_links(soup, base_url=url)
            structured_markdown = self._extract_structured_markdown(soup)

            content_sample = structured_markdown[:5000] if instructions else ""
            relevance_score, relevance_reason = (1.0, "No instructions") if not instructions else self.ai_processor.analyze_relevance(
                content=content_sample,
                title=title,
                instructions=instructions
            )

            if relevance_score >= 0.3:
                ai_extracted_content = self.ai_processor.extract_structured_content(
                    html_content=html_content,
                    title=title,
                    url=url,
                    instructions=instructions or "Extract main content"
                )
                result_data = {
                    "url": url,
                    "title": title,
                    "markdown": structured_markdown,
                    "links": links[:20],
                    "relevance": {
                        "score": relevance_score,
                        "reason": relevance_reason
                    },
                    "ai_extracted_content": ai_extracted_content,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
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
            return {"url": url, "error": f"Failed to crawl page: {str(e)}"}
        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            return {"url": url, "error": f"Error processing page: {str(e)}"}

    async def scrape(self, url: str, instructions: str, depth: int = 1, follow_external_links: bool = False, max_pages: int = 20) -> Dict[str, Any]:
        start_time = time.time()
        self.logger.info(f"Starting crawl of {url} with depth {depth}")

        visited_urls: Set[str] = set()
        results = []
        start_domain = urlparse(url).netloc
        url_queue = [(url, 0)]

        while url_queue and len(visited_urls) < max_pages:
            current_url, current_depth = url_queue.pop(0)
            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            try:
                self.logger.info(f"Scraping {current_url} (depth {current_depth})")
                page_data = await self.scrape_page(url=current_url, instructions=instructions)
                results.append(page_data)

                if current_depth < depth:
                    links = page_data.get('links', [])
                    current_domain = urlparse(current_url).netloc
                    for link in links:
                        if link in visited_urls or any(link == u for u, _ in url_queue):
                            continue
                        link_domain = urlparse(link).netloc
                        if link_domain == current_domain or (follow_external_links and link_domain == start_domain):
                            url_queue.append((link, current_depth + 1))

            except Exception as e:
                self.logger.error(f"Error processing {current_url}: {str(e)}")
                results.append({"url": current_url, "error": str(e)})

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

    def export_to_markdown(self, data: Dict[str, Any], filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Crawler Results: {data['meta']['url']}\n\n")
            f.write(f"- **Instructions:** {data['meta']['instructions']}\n")
            f.write(f"- **Depth:** {data['meta']['depth']}\n")
            f.write(f"- **Pages Crawled:** {data['meta']['pages_crawled']}\n")
            f.write(f"- **Timestamp:** {data['meta']['timestamp']}\n\n")

            for i, page in enumerate(data['pages']):
                f.write(f"## Page {i+1}: {page.get('title', 'No Title')}\n\n")
                f.write(f"**URL:** {page['url']}\n\n")

                if 'error' in page:
                    f.write(f"**Error:** {page['error']}\n\n")
                else:
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

                    if 'markdown' in page and page['markdown']:
                        f.write("### Content\n\n")
                        f.write(page['markdown'] + "\n\n")

                    if 'links' in page and page['links']:
                        f.write("### Links\n\n")
                        for link in page['links'][:10]:
                            f.write(f"- [{link}]({link})\n")
                        f.write("\n")

                f.write("\n---\n\n")

        self.logger.info(f"Data exported to {filepath}")

