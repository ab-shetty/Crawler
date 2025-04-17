# crawler/__init__.py

# Import and expose the main client classes and exceptions
from .client import SimpleCrawlerClient
from .crawler_client import CrawlerClient
from .exceptions import CrawlerError, CrawlingError, ContentProcessingError, ConfigurationError

# Version information
__version__ = "0.1.0"

# Export these classes/functions for easier imports
__all__ = [
    'SimpleCrawlerClient',
    'CrawlerClient',
    'CrawlerError',
    'CrawlingError',
    'ContentProcessingError',
    'ConfigurationError'
]