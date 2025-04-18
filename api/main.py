# api/main.py

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import json
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Adjust Python Path to Find Sibling 'crawler' Directory ---
# Get the directory of the current file (api/main.py)
current_dir = Path(__file__).parent
# Get the parent directory (the project root)
project_root = current_dir.parent
# Add the project root to the Python path
sys.path.append(str(project_root))
# --- End Path Adjustment ---

# Import the crawler
try:
    from crawler import SimpleCrawlerClient, CrawlerClient, CrawlerError
except ImportError:
    print("Error: Could not import SimpleCrawlerClient from the 'crawler' package.")
    print("Ensure the 'crawler' directory exists and is in the Python path.")
    # Define dummy classes if import fails, so FastAPI can still start
    class SimpleCrawlerClient:
        def scrape_page(self, url: str, instructions: str | None = None) -> dict:
            return {"url": str(url), "error": "Crawler not found"}
    class CrawlerClient:
        def scrape(self, url: str, instructions: str, depth: int = 0, 
                  follow_external_links: bool = False, max_pages: int = 20) -> dict:
            return {"pages": [{"url": str(url), "error": "Crawler not found"}]}
    class CrawlerError(Exception): pass

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
@app.post("/api/scrape")
async def scrape_website(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint to initiate a web crawl.
    Accepts JSON body with URL and instructions.
    """
    # Parse the request body
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    
    # Get required fields
    if 'url' not in body:
        raise HTTPException(status_code=400, detail="URL is required")
    
    url = body['url']
    instructions = body.get('instructions', "Extract main content")
    depth = body.get('depth', 0)
    
    # For tracking, print the request details
    print(f"Processing request: URL={url}, Instructions={instructions}, Depth={depth}")
    
    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    try:
        # For depth=0, just scrape a single page
        if depth == 0:
            # Initialize the client with OpenAI API key if available
            client = SimpleCrawlerClient(api_key=api_key)
            
            # Scrape the page
            result_data = client.scrape_page(url=str(url), instructions=instructions)
            
            # Return a successful response with the scraped data
            return {
                "status": "success",
                "data": [result_data]  # Wrap in list for compatibility
            }
        else:
            # For depth > 0, use the multi-page crawler
            advanced_client = CrawlerClient(api_key=api_key)
            
            # Use advanced crawling for depth > 0
            result_data = advanced_client.scrape(
                url=str(url),
                instructions=instructions,
                depth=depth,
                follow_external_links=body.get('follow_external_links', False),
                max_pages=body.get('max_pages', 20)
            )
            
            return {
                "status": "success",
                "data": result_data['pages']
            }

    except CrawlerError as e:
        raise HTTPException(status_code=500, detail=f"Crawler error: {e}")
    except Exception as e:
        # Log the full error details
        import traceback
        traceback.print_exc()
        # Return a concise error message to the client
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# --- Download endpoint to save results ---
@app.post("/api/download")
async def download_results(request: Request):
    """
    Endpoint to download crawling results in various formats.
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    
    if 'data' not in body:
        raise HTTPException(status_code=400, detail="Data is required")
    
    format = body.get('format', 'json')
    
    # Create temp directory if it doesn't exist
    temp_dir = project_root / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    # Generate a filename
    import time
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"crawler_results_{timestamp}.{format}"
    filepath = temp_dir / filename
    
    # Write the data to the file
    if format == 'json':
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(body['data'], f, indent=2)
    elif format == 'markdown' or format == 'md':
        # Use CrawlerClient for export
        client = CrawlerClient()
        
        # Construct a properly formatted result for markdown export
        result = {
            "meta": {
                "url": body.get('url', 'Unknown URL'),
                "instructions": body.get('instructions', 'No instructions'),
                "depth": body.get('depth', 0),
                "pages_crawled": len(body['data']),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "pages": body['data']
        }
        
        client.export_to_markdown(result, str(filepath))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    
    # Return the file
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/octet-stream'
    )

# --- Root Endpoint to Serve Frontend ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main index.html file."""
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)

# --- Health check endpoint ---
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}

# --- Environment check endpoint (for testing) ---
@app.get("/api/environment")
async def environment_check():
    """
    Returns information about the environment for debugging purposes.
    In production, this would be restricted to admins or removed.
    """
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
    
    # Check if Playwright is installed
    playwright_installed = False
    try:
        import playwright
        playwright_installed = True
    except ImportError:
        pass
    
    return {
        "has_openai_key": has_openai_key,
        "playwright_installed": playwright_installed,
        "python_version": sys.version,
        "paths": {
            "current_dir": str(current_dir),
            "project_root": str(project_root),
            "static_dir": str(static_dir),
        }
    }


if __name__ == "__main__":
    import uvicorn
    # Run directly for testing
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    
    uvicorn.run(app, host=host, port=port, reload=debug)