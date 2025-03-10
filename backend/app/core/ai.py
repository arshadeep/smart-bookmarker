import json
from typing import Dict, List, Optional, Tuple, Any
import httpx
import re
import os
from bs4 import BeautifulSoup

# LangChain imports
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_community.llms import Ollama
from langchain_core.runnables import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Configuration for Ollama
# By default, Ollama runs on localhost:11434
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# You can choose any model you've pulled with Ollama
# Common options: llama3, llama2, mistral, gemma, etc.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # Default to llama3

# Initialize the Ollama model
llm = Ollama(
    model="mistral-nemo",
    temperature=0.7,
    num_ctx=4096,  # Context window size
    num_predict=512  # Maximum tokens to generate
)

# Define output schemas for structured responses
class BookmarkMetadata(BaseModel):
    title: str = Field(description="A concise, descriptive title for the bookmark")
    description: str = Field(description="A brief summary of the bookmark content")
    
class CategorySuggestion(BaseModel):
    primary_category: str = Field(description="The main category for the bookmark (e.g., Tech, Finance, Health)")
    subcategory: str = Field(description="A more specific subcategory (e.g., Programming, Investing, Fitness)")
    confidence_score: float = Field(description="A score from 0.0 to 1.0 indicating confidence in the categorization")
    rationale: str = Field(description="Brief explanation of why this category was chosen")

async def fetch_url_content(url: str) -> str:
    """Fetch the content of a URL and extract relevant text."""
    try:
        # Set up custom headers to mimic a real browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=30.0)
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract the title
            title = soup.title.string if soup.title else ""
            
            # Extract meta description
            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and "content" in meta_tag.attrs:
                meta_desc = meta_tag["content"]
            
            # Look for any structured data that might have useful information
            enhanced_title = ""
            enhanced_description = ""
            
            structured_data = soup.find("script", type="application/ld+json")
            if structured_data:
                try:
                    data = json.loads(structured_data.string)
                    # Handle different schema structures
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    
                    # Try to extract name and description from any schema type
                    if isinstance(data, dict):
                        if "name" in data:
                            enhanced_title = data.get("name", "")
                        if "description" in data:
                            enhanced_description = data.get("description", "")
                except:
                    pass
            
            # Use enhanced data if available
            if enhanced_title:
                title = enhanced_title
            if enhanced_description:
                meta_desc = enhanced_description
            
            # Extract main content (improved approach)
            # Remove non-content elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                element.extract()
            
            # Try to identify the main content area
            main_content = ""
            main_elements = soup.select("main, article, .content, #content, .main, #main")
            if main_elements:
                main_content = main_elements[0].get_text(separator=' ', strip=True)
            else:
                # Fall back to body text if no main content area identified
                main_content = soup.body.get_text(separator=' ', strip=True) if soup.body else ""
            
            # Limit to a reasonable length for the LLM
            main_content = main_content[:1000]
            
            # Look for any lists that might contain important information
            list_items = []
            important_lists = soup.select("ul.important, ol.important, ul.list, ol.list, ul.items, ol.items")
            if not important_lists:
                # If no specifically marked lists, look for any lists in the main content area
                important_lists = soup.select("main ul, main ol, article ul, article ol, .content ul, .content ol")
            
            for list_el in important_lists[:2]:  # Only take the first couple of lists to avoid overloading
                for item in list_el.find_all("li"):
                    list_items.append(item.get_text(strip=True))
            
            # Look for keywords and tags
            keywords = []
            keyword_meta = soup.find("meta", attrs={"name": "keywords"})
            if keyword_meta and "content" in keyword_meta.attrs:
                keywords = [k.strip() for k in keyword_meta["content"].split(",")]
            
            # Build the result
            result = {
                "title": title,
                "description": meta_desc,
                "content": main_content[:1500],  # Limit content size
                "list_items": list_items[:10],   # Limit number of list items
                "keywords": keywords[:10],       # Limit number of keywords
                "url": url,
                "domain": url.split("//")[-1].split("/")[0]
            }
            
            return json.dumps(result)
    except Exception as e:
        print(f"Error fetching URL content: {e}")
        # Return a general message with the URL
        domain = url.split("//")[-1].split("/")[0]
        return json.dumps({
            "error": f"Could not fetch content from {url}",
            "domain": domain,
            "url": url
        })

async def generate_title_description(url: str, user_note: str = "") -> Tuple[str, str]:
    """Generate a title and description for a bookmark using content and optional user notes."""
    try:
        # Fetch content from the URL
        content_json = await fetch_url_content(url)
        content = json.loads(content_json)
        
        # Create a prompt template with optional user note
        if user_note:
            prompt_text = """Generate a concise, informative title and brief description for this bookmark based on the webpage content and the user's notes.

User's note about why they saved this bookmark: {user_note}

Web page information:
Title: {content_title}
Description: {content_description}
Content: {content_main}
URL: {url}

Your task:
1. Generate a clear, descriptive title (maximum 10 words)
2. Write a concise summary description (1-2 sentences)

Format your response exactly like this:
Title: [your generated title]
Description: [your generated description]"""
        else:
            prompt_text = """Generate a concise, informative title and brief description for this bookmark based on the webpage content.

Web page information:
Title: {content_title}
Description: {content_description}
Content: {content_main}
URL: {url}

Your task:
1. Generate a clear, descriptive title (maximum 10 words)
2. Write a concise summary description (1-2 sentences)

Format your response exactly like this:
Title: [your generated title]
Description: [your generated description]"""
        
        title_desc_template = PromptTemplate(
            input_variables=["content_title", "content_description", "content_main", "url"] + (["user_note"] if user_note else []),
            template=prompt_text
        )
        
        # Use the modern pipe syntax
        title_desc_chain = title_desc_template | llm | StrOutputParser()
        
        # Prepare input data
        input_data = {
            "content_title": content.get("title", ""),
            "content_description": content.get("description", ""),
            "content_main": content.get("content", "")[:500],  # Limit size for prompt
            "url": url
        }
        if user_note:
            input_data["user_note"] = user_note
        
        # Call the chain
        result = await title_desc_chain.ainvoke(input_data)
        
        # Parse the results
        title = ""
        description = ""
        
        for line in result.split('\n'):
            line = line.strip()
            if line.startswith("Title:"):
                title = line[6:].strip()
            elif line.startswith("Description:"):
                description = line[12:].strip()
        
        # If parsing failed, use fallbacks
        if not title or len(title) < 5:
            title = content.get("title", url.split("//")[-1].split("/")[0])
        
        if not description or len(description) < 10:
            description = content.get("description", "No description available.")
        
        return title, description
    except Exception as e:
        print(f"Error generating title/description: {e}")
        # Fallback to a simple title and description based on the URL
        domain = url.split("//")[-1].split("/")[0]
        return domain, "No description available"

async def analyze_content_for_category(url: str, user_note: str, title: str, description: str) -> dict:
    """
    Analyze content to suggest categories with confidence scores.
    Prioritizes user note but combines with scraped content for better categorization.
    """
    try:
        # Create a prompt for category analysis that incorporates user notes and webpage content
        category_prompt = PromptTemplate(
            input_variables=["url", "user_note", "title", "description"],
            template="""Analyze the following information and suggest the best category and subcategory for organizing this bookmark:

URL: {url}
User's note: {user_note}
Title: {title}
Description: {description}

1. Determine the primary category (e.g., Technology, Finance, Health, Education, Entertainment)
2. Determine a more specific subcategory
3. Provide a confidence score (0.0 to 1.0) indicating how confident you are
4. Provide a brief rationale for your suggestion

Your response should be valid JSON in the following format:
{{
  "primary_category": "string",
  "subcategory": "string",
  "confidence_score": float,
  "rationale": "string"
}}"""
        )
        
        # Create a parser for the response
        class CategoryResponse(BaseModel):
            primary_category: str
            subcategory: str
            confidence_score: float
            rationale: str
        
        parser = PydanticOutputParser(pydantic_object=CategoryResponse)
        
        # Use the chain
        category_chain = category_prompt | llm | parser
        
        result = await category_chain.ainvoke({
            "url": url,
            "user_note": user_note,
            "title": title,
            "description": description
        })
        
        # Convert Pydantic model to dict
        return {
            "primary_category": result.primary_category,
            "subcategory": result.subcategory,
            "confidence_score": result.confidence_score,
            "rationale": result.rationale
        }
    except Exception as e:
        print(f"Error analyzing content for category: {e}")
        # Provide a fallback response
        return {
            "primary_category": "Uncategorized",
            "subcategory": "General",
            "confidence_score": 0.3,
            "rationale": "Could not analyze content properly due to an error."
        }

async def find_matching_folder(category_suggestion: dict, existing_folders: list) -> Optional[str]:
    """
    Find if there's a matching existing folder for the suggested category.
    Uses a scoring system to find best matches rather than exact matches.
    """
    try:
        primary_category = category_suggestion["primary_category"]
        subcategory = category_suggestion["subcategory"]
        
        # No folders to match against
        if not existing_folders:
            return None
            
        # Format the input for the LLM
        folder_match_prompt = PromptTemplate(
            input_variables=["primary_category", "subcategory", "existing_folders"],
            template="""Your task is to match a bookmark category to the closest existing folder.

Bookmark categorization:
Primary category: {primary_category}
Subcategory: {subcategory}

Existing folders: {existing_folders}

Instructions:
1. Analyze if the bookmark category conceptually belongs in any existing folder
2. If there's a good match, return the exact name of the matching folder
3. If there's no good match, return "create_new" to suggest creating a new folder
4. Provide a confidence score between 0.0 and 1.0
5. Briefly explain your reasoning

Your response should be valid JSON in the following format:
{{
  "matching_folder": "string or create_new",
  "confidence_score": float,
  "reasoning": "string"
}}"""
        )
        
        # Create a simple output parser
        class FolderMatchResponse(BaseModel):
            matching_folder: str
            confidence_score: float
            reasoning: str
        
        parser = PydanticOutputParser(pydantic_object=FolderMatchResponse)
        
        # Use the chain
        folder_match_chain = folder_match_prompt | llm | parser
        
        result = await folder_match_chain.ainvoke({
            "primary_category": primary_category,
            "subcategory": subcategory,
            "existing_folders": ", ".join([f'"{f}"' for f in existing_folders])
        })
        
        # If we should create a new folder, return None
        if result.matching_folder == "create_new" or result.confidence_score < 0.65:
            return None
            
        # Find the exact folder name in our list (case sensitive match)
        for folder in existing_folders:
            if folder == result.matching_folder:
                return folder
                
        # No exact match found, check for case-insensitive match as fallback
        for folder in existing_folders:
            if folder.lower() == result.matching_folder.lower():
                return folder
                
        # Still no match found
        return None
        
    except Exception as e:
        print(f"Error finding matching folder: {e}")
        return None

async def suggest_folder_name(category_suggestion: dict) -> str:
    """
    Generate a folder name suggestion based on category analysis.
    """
    try:
        primary_category = category_suggestion["primary_category"]
        subcategory = category_suggestion["subcategory"]
        
        folder_name_prompt = PromptTemplate(
            input_variables=["primary_category", "subcategory"],
            template="""Create a clear, concise folder name for bookmarks based on these categories:

Primary category: {primary_category}
Subcategory: {subcategory}

Rules for the folder name:
1. Keep it short (2-3 words maximum)
2. Make it intuitive and user-friendly
3. Focus on broad enough categorization that similar bookmarks could fit
4. Use title case (capitalize main words)

Response format:
Folder: [your suggested folder name]"""
        )
        
        folder_name_chain = folder_name_prompt | llm | StrOutputParser()
        
        result = await folder_name_chain.ainvoke({
            "primary_category": primary_category,
            "subcategory": subcategory
        })
        
        # Extract folder name from the response
        folder_name = ""
        for line in result.split('\n'):
            if line.startswith("Folder:"):
                folder_name = line[7:].strip()
                break
                
        # Clean and validate the folder name
        if folder_name and len(folder_name) > 2:
            # Limit to 30 characters
            return folder_name[:30]
        else:
            # Fallback to primary category
            return primary_category
            
    except Exception as e:
        print(f"Error suggesting folder name: {e}")
        return "Uncategorized"

async def suggest_folder(url: str, title: str, description: str, user_note: str, existing_folders: list) -> str:
    """
    Main function that suggests a folder for a bookmark using the enhanced algorithm.
    1. Analyzes user note (if provided) and combined content
    2. Checks for matching existing folders
    3. Creates new folder suggestion if needed
    """
    try:
        # Step 1: Analyze content to get category suggestion
        category_data = await analyze_content_for_category(url, user_note, title, description)
        
        # Step 2: Check if any existing folder matches the category
        matching_folder = await find_matching_folder(category_data, existing_folders)
        
        # If we found a matching folder, use it
        if matching_folder:
            return matching_folder
            
        # Step 3: No matching folder, suggest a new one
        new_folder = await suggest_folder_name(category_data)
        
        return new_folder
    except Exception as e:
        print(f"Error in suggest_folder: {e}")
        return "Uncategorized"

# Main function used by the API endpoints
async def process_bookmark(url: str, user_note: str = "", existing_folders: list = None) -> Tuple[str, str, str]:
    """
    Process a bookmark to generate title, description, and folder suggestion.
    Implements the enhanced algorithm that prioritizes user notes and combines with web content.
    """
    if existing_folders is None:
        existing_folders = []
        
    # Generate title and description
    title, description = await generate_title_description(url, user_note)
    
    # Suggest folder based on combined analysis
    folder_name = await suggest_folder(url, title, description, user_note, existing_folders)
    
    return title, description, folder_name