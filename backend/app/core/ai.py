import json
from typing import Dict, List, Optional, Tuple
import httpx
import re
import os
from bs4 import BeautifulSoup

# LangChain imports
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
from langchain_core.runnables import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

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
            
            # Build the result
            result = [f"Title: {title}", f"Description: {meta_desc}", f"Content: {main_content}"]
            
            if list_items:
                result.append("List Items: " + ", ".join(list_items[:10]))
            
            return "\n".join(result)
    except Exception as e:
        print(f"Error fetching URL content: {e}")
        # Return a general message with the URL
        domain = url.split("//")[-1].split("/")[0]
        return f"Could not fetch content from {url}. This appears to be from {domain}."

async def generate_title_description(url: str) -> Tuple[str, str]:
    """Generate a title and description for a bookmark using Ollama."""
    try:
        # Fetch content from the URL
        content = await fetch_url_content(url)
        
        # Create a prompt for title and description generation
        combined_template = PromptTemplate(
            input_variables=["content"],
            template="""Based on the following web page content, generate:
1. A concise, descriptive title (maximum 10 words)
2. A brief summary (1-2 sentences)

Format your response exactly like this:
Title: [your generated title]
Description: [your generated description]

Web content:
{content}"""
        )
        
        # Use the modern pipe syntax
        combined_chain = combined_template | llm | StrOutputParser()
        
        # Call the chain with await and invoke
        combined_result = await combined_chain.ainvoke({"content": content[:1500]})
        
        # Parse the results
        title = ""
        description = ""
        
        for line in combined_result.split('\n'):
            line = line.strip()
            if line.startswith("Title:"):
                title = line[6:].strip()
            elif line.startswith("Description:"):
                description = line[12:].strip()
        
        # If parsing failed, use fallbacks
        if not title or len(title) < 5:
            # Extract title from the original content
            original_title = ""
            title_match = content.split("\n")[0] if "\n" in content else ""
            if title_match.startswith("Title:"):
                original_title = title_match[6:].strip()
            title = original_title if original_title else url.split("//")[-1].split("/")[0]
        
        if not description or len(description) < 10:
            # Extract description from the original content
            original_desc = ""
            for line in content.split("\n"):
                if line.startswith("Description:"):
                    original_desc = line[12:].strip()
                    break
            description = original_desc if original_desc else "No description available."
        
        return title, description
    except Exception as e:
        print(f"Error generating title/description: {e}")
        # Fallback to a simple title and description based on the URL
        return url.split("//")[-1].split("/")[0], "No description available"

async def suggest_folder(title: str, description: str, existing_folders: list) -> str:
    """Suggest a folder name based on the bookmark content using Ollama."""
    try:
        combined_content = f"{title} - {description}"
        
        # If there are existing folders, check if content matches any of them
        if existing_folders:
            # Create a prompt that asks the model to pick the best matching folder or suggest a new one
            matching_template = PromptTemplate(
                input_variables=["content", "folders"],
                template="""Consider this content: "{content}"

Here are the existing folders: {folders}

Step 1: Evaluate if the content clearly belongs in one of the existing folders.
Step 2: If it does belong in an existing folder, respond with just that folder name.
Step 3: If it doesn't clearly match any existing folder, respond with a new suggested folder name (maximum 3 words).

Your response should be ONLY the folder name, nothing else."""
            )
            
            # Join the folders as a comma-separated list for the prompt
            folders_str = ", ".join([f'"{f}"' for f in existing_folders])
            
            # Use the modern pipe syntax
            matching_chain = matching_template | llm | StrOutputParser()
            
            # Call the chain with await and invoke
            folder_suggestion = await matching_chain.ainvoke({
                "content": combined_content, 
                "folders": folders_str
            })
            
            # Clean up the response
            folder_suggestion = folder_suggestion.strip().replace('"', '').replace("'", "")
            
            # Check if the suggestion matches an existing folder
            for folder in existing_folders:
                # Use case-insensitive comparison to improve matching
                if folder.lower() == folder_suggestion.lower():
                    return folder  # Return the exact folder name from the list
        else:
            # If no existing folders, just get a suggestion for a new one
            suggestion_template = PromptTemplate(
                input_variables=["content"],
                template="""Suggest a broad, generic category folder name (2-3 words maximum) for content about:
"{content}"

Examples of good folder names:
- "AI & Machine Learning"
- "Cooking Recipes"
- "Web Development"
- "Personal Finance"
- "Travel Destinations"
- "Health & Fitness"
- "Book Recommendations"
- "Tech News"

Respond with ONLY the category name, nothing else."""
            )
            
            # Use the modern pipe syntax
            suggestion_chain = suggestion_template | llm | StrOutputParser()
            
            # Call the chain with await and invoke
            folder_suggestion = await suggestion_chain.ainvoke({"content": combined_content})
            
            # Clean up the suggestion
            folder_suggestion = folder_suggestion.strip().replace('"', '').replace("'", "")
        
        # Final cleanup and formatting
        # Get only the first few words if too long
        words = folder_suggestion.split()
        if len(words) > 3:
            folder_suggestion = " ".join(words[:3])
            
        return folder_suggestion if folder_suggestion and len(folder_suggestion) > 2 else "Uncategorized"
    except Exception as e:
        print(f"Error suggesting folder: {e}")
        return "Uncategorized"

# Additional fallback function that can be used when API calls fail
async def fallback_title_description(url: str, content: str) -> Tuple[str, str]:
    """Generate a fallback title and description when the LLM fails."""
    # Extract domain for the title
    domain = url.split("//")[-1].split("/")[0]
    
    # Try to extract title from content
    title = domain
    description = "No description available."
    
    # Parse the content for better fallbacks
    lines = content.split("\n")
    for line in lines:
        if line.startswith("Title:"):
            extracted_title = line[6:].strip()
            if extracted_title:
                title = extracted_title
        elif line.startswith("Description:"):
            extracted_desc = line[12:].strip()
            if extracted_desc:
                description = extracted_desc
    
    # If content has meaningful text, use first sentence as description
    if "Content:" in content:
        content_parts = content.split("Content:")
        if len(content_parts) > 1:
            content_text = content_parts[1].strip()
            # Get first sentence or first 100 chars
            first_sentence = content_text.split(".")[0]
            if len(first_sentence) > 10:
                description = first_sentence[:100] + "..."
    
    return title, description