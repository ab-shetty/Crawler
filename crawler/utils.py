# crawler/utils.py

import logging
from urllib.parse import urljoin, urlparse

from .config import LOGGING_LEVEL, LOG_FORMAT

def setup_logger(name: str) -> logging.Logger:
    """Sets up a standard logger."""
    logging.basicConfig(level=LOGGING_LEVEL, format=LOG_FORMAT)
    logger = logging.getLogger(name)
    return logger

def normalize_url(base_url: str, link: str) -> str | None:
    """
    Normalizes a potentially relative URL against a base URL.
    Returns the absolute URL or None if the link is invalid or not HTTP/HTTPS.
    """
    try:
        # Join the base URL and the link
        absolute_url = urljoin(base_url, link)

        # Parse the result
        parsed_url = urlparse(absolute_url)

        # Check if it's a valid HTTP/HTTPS URL
        if parsed_url.scheme in ['http', 'https'] and parsed_url.netloc:
            # Reconstruct to remove fragments (#)
            return parsed_url._replace(fragment="").geturl()
        else:
            return None
    except ValueError:
        # Handle potential errors during urljoin or urlparse
        return None

def clean_text(text: str) -> str:
    """Basic text cleaning (can be expanded)."""
    import re
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Add more cleaning rules as needed
    return text

# Add more utility functions as needed (e.g., data formatters, file handlers)
