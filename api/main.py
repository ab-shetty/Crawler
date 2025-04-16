# api/main.py

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import os
import sys
from pathlib import Path

# --- Adjust Python Path to Find Sibling 'crawler' Directory ---
# Get the directory of the current file (api/main.py)
current_dir = Path(__file__).parent
# Get the parent directory (the project root)
project_root = current_dir.parent
# Add the project root to the Python path
sys.path.append(str(project_root))
# --- End Path Adjustment ---

from .schemas import CrawlRequest, CrawlResponse # Use relative import for schemas
# Import your crawler client (adjust if your class name is different)
try:
    from crawler import SimpleCrawlerClient, SimpleCrawlerError
except ImportError:
    print("Error: Could not import SimpleCrawlerClient from the 'crawler' package.")
    print("Ensure the 'crawler' directory exists and is in the Python path.")
    # Define dummy classes if import fails, so FastAPI can still start
    class SimpleCrawlerClient:
        def scrape_page(self, url: str, instructions: str | None = None) -> dict:
            return {"url": str(url), "error": "Crawler not found"}
    class SimpleCrawlerError(Exception): pass

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Crawler API",
    description="API for the AI Web Crawler",
    version="0.1.0"
)

# --- Mount Static Files Directory ---
# Serve files from the 'web/static' directory at the '/static' URL path
static_dir = project_root / "web" / "static"
if not static_dir.exists():
    print(f"Warning: Static directory not found at {static_dir}. Frontend won't be served correctly.")
else:
     # Path relative to the project root for mounting
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# --- API Endpoints ---
@app.post("/api/scrape", response_model=CrawlResponse, tags=["Crawling"])
async def scrape_website(request: CrawlRequest):
    """
    Endpoint to initiate a web crawl for a single page.
    (Note: Currently uses the simple client for one page).
    """
    client = SimpleCrawlerClient() # Instantiate your simple client
    try:
        # In the simple version, 'depth' isn't used, but instructions are passed
        # If you evolve the client, you'd pass request.depth here.
        result_data = client.scrape_page(url=str(request.url), instructions=request.instructions)
        # Wrap the single result in a list to match CrawlResponse structure
        return CrawlResponse(status="success", data=[result_data])

    except SimpleCrawlerError as e:
        raise HTTPException(status_code=500, detail=f"Crawler error: {e}")
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# --- Root Endpoint to Serve Frontend ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root():
    """Serves the main index.html file."""
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)

# --- Optional: Add Background Task Example (if needed later) ---
# async def run_scrape_task(client: SimpleCrawlerClient, url: str, instructions: str):
#     print(f"Background task started for {url}")
#     # Replace with actual long-running crawl logic
#     await asyncio.sleep(5) # Simulate work
#     result = client.scrape_page(url=url, instructions=instructions)
#     print(f"Background task finished for {url}. Result: {result.get('title', 'N/A')}")
#     # Here you would typically store the result somewhere (DB, cache, file)

# @app.post("/api/scrape_background", status_code=202, tags=["Crawling"])
# async def scrape_background(request: CrawlRequest, background_tasks: BackgroundTasks):
#     """Endpoint to initiate scraping as a background task."""
#     client = SimpleCrawlerClient()
#     background_tasks.add_task(run_scrape_task, client, str(request.url), request.instructions)
#     return {"message": "Scraping task accepted and running in the background."}


if __name__ == "__main__":
    import uvicorn
    # Run directly for testing (uvicorn api.main:app --reload)
    uvicorn.run(app, host="0.0.0.0", port=8000)

