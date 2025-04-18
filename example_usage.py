# Example usage as specified in the assignment
import os
from crawler import CrawlerClient

def main():
    # Get API key from environment variable
    key = os.getenv('CRAWLER_API_KEY')
    
    # Initialize the client
    client = CrawlerClient(api_key=key)
    
    # Define instructions
    instructions = "We're making a chatbot for the HR in San Francisco."
    
    # Scrape the website
    print(f"Starting to scrape with instructions: {instructions}")
    documents = client.scrape("https://www.sfgov.com", instructions)
    
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

if __name__ == "__main__":
    main()