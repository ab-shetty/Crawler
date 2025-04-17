import os
from typing import Dict, Any, List, Optional, Tuple
import json
import logging
from openai import OpenAI
from .utils import setup_logger
from dotenv import load_dotenv

class AiProcessor:
    """
    AI-powered content processor using OpenAI's models to analyze and extract
    information from web content based on user instructions.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the AI processor.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
        """
        self.logger = setup_logger("AiProcessor")

        load_dotenv()
        
        # Use provided API key or get from environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            self.logger.warning("No OpenAI API key provided. AI features will be limited.")
        
        # Initialize OpenAI client if API key is available
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def analyze_relevance(self, 
                         content: str, 
                         title: str, 
                         instructions: str) -> Tuple[float, str]:
        """
        Use AI to analyze how relevant a page is to the given instructions.
        
        Args:
            content: The page content
            title: The page title
            instructions: User instructions
            
        Returns:
            Tuple of (relevance_score, reason)
        """
        if not self.client:
            # Fallback to simple keyword matching if no API key
            return self._keyword_relevance(content, title, instructions)
        
        try:
            # Prepare prompt for relevance analysis
            prompt = f"""
            You are analyzing the relevance of a web page to a user's instructions.
            
            Page Title: {title}
            
            User Instructions: {instructions}
            
            Page Content (excerpt): {content[:2000]}...
            
            On a scale of 0.0 to 1.0, how relevant is this content to the user's instructions?
            Provide your answer in the following JSON format:
            {{
                "relevance_score": 0.0 to 1.0,
                "reasoning": "Brief explanation of why this content is or isn't relevant"
            }}
            """
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a content relevance analyzer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            # Extract and parse the response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            return (
                float(result.get("relevance_score", 0.5)), 
                result.get("reasoning", "No reasoning provided")
            )
            
        except Exception as e:
            self.logger.error(f"Error using OpenAI for relevance analysis: {str(e)}")
            # Fallback to simple keyword matching
            return self._keyword_relevance(content, title, instructions)
    
    def _keyword_relevance(self, content: str, title: str, instructions: str) -> Tuple[float, str]:
        """
        Simple keyword-based relevance analysis as a fallback.
        
        Args:
            content: The page content
            title: The page title
            instructions: User instructions
            
        Returns:
            Tuple of (relevance_score, reason)
        """
        # Convert to lowercase for comparison
        content_lower = content.lower()
        title_lower = title.lower()
        instructions_lower = instructions.lower()
        
        # Extract keywords (simple approach)
        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'when', 'where', 'how', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'to', 'from', 'in', 'out',
            'get', 'find', 'extract', 'information', 'about'
        }
        
        keywords = [word for word in instructions_lower.split() 
                   if len(word) > 3 and word not in stopwords]
        
        if not keywords:
            return (0.5, "No specific keywords found in instructions")
        
        # Count matches
        title_matches = sum(1 for keyword in keywords if keyword in title_lower)
        content_matches = sum(1 for keyword in keywords if keyword in content_lower)
        
        # Calculate score
        if len(keywords) == 0:
            score = 0.5
        else:
            score = (title_matches * 3 + content_matches) / (len(keywords) * 4)
            score = min(max(score, 0.0), 1.0)
        
        if score > 0.7:
            reason = "High keyword match in title and content"
        elif score > 0.4:
            reason = "Moderate keyword match"
        else:
            reason = "Low keyword match"
            
        return (score, reason)
    
    def extract_structured_content(self, 
                                  html_content: str, 
                                  title: str, 
                                  url: str, 
                                  instructions: str) -> Dict[str, Any]:
        """
        Use AI to extract structured content based on user instructions.
        
        Args:
            html_content: Raw HTML content
            title: Page title
            url: Page URL
            instructions: User instructions
            
        Returns:
            Structured data based on instructions
        """
        if not self.client:
            # Return basic extraction if no API key
            return self._basic_extraction(html_content, title, url)
        
        try:
            # Clean HTML to plain text (simplified for example)
            import re
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator='\n', strip=True)
            
            # Truncate if too long
            if len(text_content) > 8000:
                text_content = text_content[:8000] + "..."
                
            # Prepare prompt for content extraction
            prompt = f"""
            You are extracting specific information from a web page based on user instructions.
            
            URL: {url}
            Page Title: {title}
            User Instructions: "{instructions}"
            
            Page Content:
            {text_content}
            
            Based on the user's instructions, extract the most relevant information from this page.
            Format your response as JSON with these fields:
            1. "summary": A short summary of the page relevant to the instructions (2-3 sentences)
            2. "key_points": List of key points relevant to the instructions (up to 5 points)
            3. "relevance_score": Number from 0-1 indicating relevance to instructions
            4. "extracted_data": Any specific data mentioned in the instructions (object format)
            
            Only include information explicitly found on the page.
            """
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18", 
                messages=[
                    {"role": "system", "content": "You are a precise web content extraction assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Extract the response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Add metadata to result
            result["source_url"] = url
            result["source_title"] = title
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error using OpenAI for content extraction: {str(e)}")
            # Fallback to basic extraction
            return self._basic_extraction(html_content, title, url)
    
    def _basic_extraction(self, html_content: str, title: str, url: str) -> Dict[str, Any]:
        """
        Basic content extraction as a fallback.
        
        Args:
            html_content: Raw HTML content
            title: Page title
            url: Page URL
            
        Returns:
            Basic extracted content
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract paragraphs
        paragraphs = []
        for p in soup.find_all('p'):
            if p.text and len(p.text.strip()) > 50:  # Only substantial paragraphs
                paragraphs.append(p.text.strip())
        
        # Extract headings
        headings = []
        for h in soup.find_all(['h1', 'h2', 'h3']):
            if h.text and len(h.text.strip()) > 0:
                headings.append(h.text.strip())
        
        # Create a simple summary
        summary = f"Page titled '{title}' with {len(paragraphs)} paragraphs and {len(headings)} headings."
        
        # Extract any lists
        list_items = []
        for li in soup.find_all('li'):
            if li.text and len(li.text.strip()) > 10:
                list_items.append(li.text.strip())
        
        return {
            "source_url": url,
            "source_title": title,
            "summary": summary,
            "key_points": headings[:5],  # Use headings as key points
            "relevance_score": 0.5,  # Default mid-relevance
            "paragraphs": paragraphs[:10],  # First 10 paragraphs
            "list_items": list_items[:20]  # First 20 list items
        }
    
    def generate_search_queries(self, instructions: str, base_url: str, depth: int) -> List[str]:
        """
        Generate effective search queries for finding relevant pages based on instructions.
        
        Args:
            instructions: User instructions
            base_url: The base URL for the website
            depth: Crawl depth
            
        Returns:
            List of suggested search queries
        """
        if not self.client:
            # Return basic query if no API key
            return [f"site:{base_url} {instructions}"]
        
        try:
            # Prepare prompt for query generation
            prompt = f"""
            You are helping generate effective site-specific search queries based on user instructions.
            
            User Instructions: "{instructions}"
            Base Website URL: {base_url}
            Crawl Depth: {depth}
            
            Generate 3-5 specific search queries that would be effective for finding pages on this website
            that match the user's instructions. Format them as Google search queries including site: operator.
            
            Format your response as a JSON array of strings.
            """
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a search query optimization assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # Higher temperature for more variety
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            # Extract and parse the response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "queries" in result:
                return result["queries"]
            else:
                # Fallback if response format is unexpected
                return [f"site:{base_url} {instructions}"]
            
        except Exception as e:
            self.logger.error(f"Error using OpenAI for query generation: {str(e)}")
            # Fallback to basic query
            return [f"site:{base_url} {instructions}"]