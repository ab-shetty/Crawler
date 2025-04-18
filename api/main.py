# api/main.py

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Path Setup ---
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.append(str(project_root))

# Import EnhancedCrawlerClient directly
from crawler.enhanced_crawler import EnhancedCrawlerClient

# --- FastAPI App Setup ---
app = FastAPI(
    title="Crawler API",
    description="API for the AI Web Crawler",
    version="0.1.0"
)

# Mount static files if available
static_dir = project_root / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"Warning: Static directory not found at {static_dir}.")

# --- Startup: Pre-initialize Crawler ---
@app.on_event("startup")
async def on_startup():
    crawler = EnhancedCrawlerClient()
    await crawler.initialize_crawler()
    app.state.crawler = crawler

@app.on_event("shutdown")
async def on_shutdown():
    crawler: EnhancedCrawlerClient = app.state.crawler
    await crawler.close()

# --- API Endpoints ---
@app.post("/api/scrape")
async def scrape_website(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    url = body.get("url")
    instructions = body.get("instructions", "Extract main content")
    depth = body.get("depth", 0)
    follow_external_links = body.get("follow_external_links", False)
    max_pages = body.get("max_pages", 20)

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    crawler: EnhancedCrawlerClient = app.state.crawler

    try:
        if depth == 0:
            result_data = await crawler.scrape_page(str(url), instructions)
            return {"status": "success", "data": [result_data]}
        else:
            result_data = await crawler.scrape(
                str(url), instructions, depth, follow_external_links, max_pages
            )
            return {"status": "success", "data": result_data['pages']}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        import gc
        gc.collect()

@app.post("/api/download")
async def download_results(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if "data" not in body:
        raise HTTPException(status_code=400, detail="Data is required")

    format = body.get("format", "json")
    temp_dir = project_root / "temp"
    temp_dir.mkdir(exist_ok=True)

    import time
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"crawler_results_{timestamp}.{format}"
    filepath = temp_dir / filename

    from crawler.enhanced_crawler import CrawlerClient  # Only for export
    client = CrawlerClient()

    if format == "json":
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(body["data"], f, indent=2)
    elif format in {"markdown", "md"}:
        result = {
            "meta": {
                "url": body.get("url", "Unknown URL"),
                "instructions": body.get("instructions", "No instructions"),
                "depth": body.get("depth", 0),
                "pages_crawled": len(body["data"]),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "pages": body["data"]
        }
        client.export_to_markdown(result, str(filepath))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    return FileResponse(path=filepath, filename=filename, media_type="application/octet-stream")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/api/environment")
async def environment_check():
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
    try:
        import playwright
        playwright_installed = True
    except ImportError:
        playwright_installed = False

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
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    uvicorn.run(app, host=host, port=port, reload=debug)
