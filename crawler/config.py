# crawler/config.py

import logging
from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig

# --- Default Crawler Settings ---
DEFAULT_MAX_DEPTH = 1
DEFAULT_MAX_LINKS_PER_PAGE = 5 # Limit how many links to follow from one page
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 2 # Base delay for exponential backoff

# --- Browser Configuration ---
# Configure headless mode, JS execution, etc.
DEFAULT_BROWSER_CONFIG = BrowserConfig(
    headless=True,
    java_script_enabled=True,
    # You might add options like user_agent, proxy settings here
    # browser_args=["--no-sandbox", "--disable-dev-shm-usage"] # Common args for containers
)

# --- Run Configuration ---
# Cache mode, streaming, JS code injection, etc.
DEFAULT_RUN_CONFIG = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS, # Or CacheMode.NORMAL for development
    stream=False, # Set to True if you want streaming results
    # js_code=None # Example placeholder for dynamic JS injection
)

# --- Logging Configuration ---
LOGGING_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# --- AI Processor Settings ---
DEFAULT_RELEVANCE_THRESHOLD = 0.5 # Example threshold for content filtering

# --- Output Settings ---
DEFAULT_OUTPUT_FORMAT = 'json' # Could be 'markdown', 'json', etc.
