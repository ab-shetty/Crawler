# api/schemas.py

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Any, Optional

class CrawlRequest(BaseModel):
    """Defines the expected structure for a crawl request."""
    url: HttpUrl = Field(..., description="The starting URL to crawl.")
    instructions: str = Field(
        default="Extract main content.",
        description="Instructions for the crawler on what data to focus on."
    )
    depth: Optional[int] = Field(
        default=0,
        ge=0, # Must be greater than or equal to 0
        description="Maximum link depth to follow (0 means only the starting URL)."
    )

class CrawlResponseData(BaseModel):
    """Represents the data structure for a single crawled page's result."""
    url: str
    title: Optional[str] = None
    paragraphs: Optional[List[str]] = None
    error: Optional[str] = None
    # Add other fields extracted by your crawler as needed
    # e.g., relevant_sections: Optional[List[str]] = None

class CrawlResponse(BaseModel):
    """Defines the overall structure of the API response."""
    status: str = Field(..., description="Indicates success or failure ('success' or 'error').")
    message: Optional[str] = None # Optional message, e.g., for errors
    data: Optional[List[Dict[str, Any]]] = Field(
         None, description="List of results from crawled pages (flexible dict for now)."
    )
    # Using List[Dict[str, Any]] for flexibility as your base SimpleCrawlerClient returns dicts.
    # You could refine this to use List[CrawlResponseData] if your client always returns that structure.

