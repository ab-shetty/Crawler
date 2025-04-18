import asyncio
from crawl4ai import *
import time
from bs4 import BeautifulSoup

async def main(url):

    """
    Scrape a single webpage using Crawl4AI and extract content based on instructions.
    
    Args:
        url: The URL to scrape
        instructions: Natural language instructions for what to extract
        
    Returns:
        A dictionary containing the scraped data
    """
    
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, # Or CacheMode.NORMAL for development
    stream=False,)
    # Use Crawl4AI to crawl the page
    session_id = f"session_{int(time.time())}"
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            config=crawl_config,
            session_id=session_id
        )
        
        if not result.success:
            raise CrawlingError(url, result.error_message or "Unknown error")
        
        # Extract content from the crawl result
        html_content = result.html
        markdown_content = result.markdown.raw_markdown if result.markdown else ""
        
        # Parse HTML for basic data extraction
        soup = BeautifulSoup(html_content, 'html.parser')
        

        print (markdown_content)

if __name__ == "__main__":
    asyncio.run(main(url="https://ai.pydantic.dev/changelog/"))