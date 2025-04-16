# crawler/__init__.py

# Expose the main client class for easier imports
from .client import CrawlerClient
from .exceptions import CrawlerError

__all__ = ['CrawlerClient', 'CrawlerError']
__version__ = "0.1.0" # Example version