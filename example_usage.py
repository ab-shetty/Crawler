# Example usage as specified in the assignment

# The example provided for this kind of usage did not 
# make any mention of crawl depth, therefore this script
# and the CrawlerClient class do not make use of a direct
# crawl depth variable. 

import os
import sys
from crawler import CrawlerClient

def main():
    # Get API key from environment variable
    # In this case, this is just an OpenAI API key
    key = os.getenv('CRAWLER_API_KEY')
    
    # Initialize the client
    client = CrawlerClient(api_key=key)
    
    # Define instructions
    instructions = "We're making a chatbot for the HR in San Francisco."
    
    # Default URL - try to use a more reliable website for testing
    url = "https://www.sf.gov"
    
    # If command line argument is provided, use that URL instead
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    # Scrape the website
    print(f"Starting to scrape {url} with instructions: {instructions}")
    try:
        documents = client.scrape(url, instructions, depth=1, max_pages=30)
        
        # Handle case where a specific URL fails
        if any('error' in page for page in documents.get('pages', [])):
            print("Warning: Some pages had errors during crawling.")
            
            # Try a fallback URL if the original one failed completely
            if all('error' in page for page in documents.get('pages', [])):
                print(f"All pages failed. Trying fallback URL...")
                fallback_url = "https://example.com"
                documents = client.scrape(fallback_url, instructions, depth=0, max_pages=1)
        
        # Print statistics
        print(f"Scraped {len(documents['pages'])} pages")
        
        # Process the documents for RAG
        rag_documents = client.create_rag_documents(documents)
        print(f"Created {len(rag_documents)} RAG documents")
        
        # Show first 3 documents
        for i, doc in enumerate(rag_documents[:3]):
            print(f"\nDocument {i+1}:")
            print(f"Type: {doc['chunk_type']}, Length: {len(doc['content'])}")
            print(f"URL: {doc['metadata']['source_url']}")
            print(f"Relevance: {doc['metadata']['relevance_score']}")
            print("---")
        
        # Export results to markdown
        client.export_to_markdown(documents, "crawler_results.md")
        print("Exported results to crawler_results.md")
    
    except Exception as e:
        print(f"Error during crawling: {e}")
        print("Trying fallback URL with minimal settings...")
        try:
            documents = client.scrape("https://example.com", instructions, depth=0, max_pages=1)
            print(f"Fallback crawl succeeded with {len(documents['pages'])} pages")
            
            # Process the documents for RAG
            rag_documents = client.create_rag_documents(documents)
            print(f"Created {len(rag_documents)} RAG documents")
        except Exception as e2:
            print(f"Fallback also failed: {e2}")


if __name__ == "__main__":
    main()