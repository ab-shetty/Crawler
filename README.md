# Crawler - AI Web Scraping Tool for RAG Systems

Crawler is an intelligent web scraping tool that uses AI to extract relevant content from websites based on natural language instructions. It's designed specifically for creating high-quality documents for Retrieval Augmented Generation (RAG) systems.

## Features

- **Natural Language Instructions**: Tell the crawler what information you want in plain English
- **Intelligent Content Extraction**: Uses AI to identify and extract only the most relevant content
- **Smart Link Following**: Crawls through websites, following links to find related content
- **Dynamic Content Handling**: Waits for JavaScript-rendered content to load
- **RAG-Ready Document Creation**: Outputs structured, chunked documents optimized for RAG systems
- **Error Handling**: Robust handling of rate limiting, network errors, and other issues

## Installation

```bash
pip install crawler
```

## Basic Usage

```python
import os
from crawler import CrawlerClient

# Get API key from environment variable
key = os.getenv('CRAWLER_API_KEY')

# Initialize the client
client = CrawlerClient(api_key=key)

# Define your instructions
instructions = "We're building a chatbot for HR. Extract information about employee benefits and company policies."

# Scrape a website
documents = client.scrape("https://example.com", instructions)

# Process for RAG
rag_documents = client.create_rag_documents(documents)

# Print the first document
print(f"Document Type: {rag_documents[0]['chunk_type']}")
print(f"Content: {rag_documents[0]['content'][:100]}...")
print(f"Metadata: {rag_documents[0]['metadata']}")
```

## Advanced Usage

### Controlling Crawl Depth

You can control how deep the crawler follows links:

```python
# Only crawl the specified URL (depth=0)
documents = client.scrape("https://example.com", instructions, depth=0)

# Follow links 2 levels deep
documents = client.scrape("https://example.com", instructions, depth=2)
```

### Following External Links

By default, the crawler only follows links within the same domain:

```python
# Enable following links to external domains
documents = client.scrape("https://example.com", instructions, follow_external_links=True)
```

### Limiting Pages

Control the maximum number of pages to crawl:

```python
# Limit to 10 pages maximum
documents = client.scrape("https://example.com", instructions, max_pages=10)
```

### Exporting Results

Export results to markdown for easy viewing:

```python
# Export to Markdown
client.export_to_markdown(documents, "results.md")
```

## RAG Integration

The `create_rag_documents()` method returns documents structured for RAG systems:

```python
rag_documents = client.create_rag_documents(documents)
```

Each document includes:
- `chunk_type`: "summary", "key_point", or "content"
- `content`: The actual text content
- `metadata`: Source URL, title, relevance score, and more

You can easily load these into vector databases or RAG pipelines:

```python
# Example integration with a vector database (pseudocode)
for doc in rag_documents:
    vector_db.add_document(
        text=doc['content'],
        metadata=doc['metadata']
    )
```

## Requirements

- Python 3.9+
- OpenAI API key (for AI content processing)

## License

MIT