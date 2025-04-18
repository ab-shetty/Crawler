# crawler/__init__.py

# Import and expose the main client classes and exceptions
from .enhanced_crawler import EnhancedCrawlerClient as CrawlerClient
from .exceptions import CrawlerError, CrawlingError, ContentProcessingError, ConfigurationError, RateLimitError

# Version information
__version__ = "0.1.0"

# Export these classes/functions for easier imports
__all__ = [
    'CrawlerClient',
    'CrawlerError',
    'CrawlingError',
    'ContentProcessingError',
    'ConfigurationError',
    'RateLimitError'
]