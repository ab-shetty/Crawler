# crawler/utils.py

import logging
from urllib.parse import urljoin, urlparse
from typing import List, Optional

# Default logging settings
LOGGING_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logger(name: str) -> logging.Logger:
    """Sets up a standard logger."""
    logging.basicConfig(level=LOGGING_LEVEL, format=LOG_FORMAT)
    logger = logging.getLogger(name)
    return logger

def normalize_url(base_url: str, link: str) -> Optional[str]:
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

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    """
    Split text into chunks, respecting code blocks and paragraphs.
    
    Args:
        text: The text to split into chunks
        chunk_size: Maximum size of each chunk in characters
        
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = min(start + chunk_size, text_length)
        
        # If we're not at the end of the text, try to find a good break point
        if end < text_length:
            # Try to break at paragraph
            paragraph_break = text.rfind('\n\n', start, end)
            if paragraph_break != -1:
                end = paragraph_break + 2  # Include the newlines
            else:
                # Try to break at sentence
                sentence_break = text.rfind('. ', start, end)
                if sentence_break != -1:
                    end = sentence_break + 2  # Include the period and space
                else:
                    # Try to break at word
                    space_break = text.rfind(' ', start, end)
                    if space_break != -1:
                        end = space_break + 1  # Include the space
        
        # Add the chunk
        chunks.append(text[start:end])
        start = end
    
    return chunks

def get_domain(url: str) -> str:
    """Extract domain from URL."""
    return urlparse(url).netloc

def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs have the same domain."""
    return get_domain(url1) == get_domain(url2)