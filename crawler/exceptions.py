# crawler/exceptions.py

class CrawlerError(Exception):
    """Base exception class for the Crawler project."""
    pass

class CrawlingError(CrawlerError):
    """Raised when there's an error during the crawling process (e.g., network issue, page load failure)."""
    def __init__(self, url: str, message: str):
        self.url = url
        self.message = f"Failed to crawl {url}: {message}"
        super().__init__(self.message)

class ContentProcessingError(CrawlerError):
    """Raised when there's an error during content extraction or synthesis."""
    def __init__(self, message: str):
        self.message = f"Content processing failed: {message}"
        super().__init__(self.message)

class ConfigurationError(CrawlerError):
    """Raised for invalid configuration settings."""
    pass

class RateLimitError(CrawlerError):
    """Raised when the crawler is rate limited by the server."""
    pass