# crawler/__init__.py

# Import and expose the main client classes and exceptions
from .enhanced_crawler import EnhancedCrawlerClient
from .exceptions import CrawlerError, CrawlingError, ContentProcessingError, ConfigurationError

# Version information
__version__ = "0.2.0"

# Export these classes/functions for easier imports
__all__ = [
    'EnhancedCrawlerClient',
    'CrawlerClient',
    'CrawlerError',
    'CrawlingError',
    'ContentProcessingError',
    'ConfigurationError'
]