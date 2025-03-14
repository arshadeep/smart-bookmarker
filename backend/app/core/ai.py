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

async def generate_title_description(url: str, user_note: str = "") -> Tuple[str, str]:
    """Generate a title and description for a bookmark using content and optional user notes."""
    try:
        # Fetch content from the URL
        content = await fetch_url_content(url)
        
        # Create a prompt with consideration for user note if provided
        prompt_template = """Based on the following web page content{user_note_context}, generate:
1. A concise, descriptive title (maximum 10 words)
2. A brief summary (1-2 sentences)

Format your response exactly like this:
Title: [your generated title]
Description: [your generated description]

Web content:
{content}"""

        # Add user note context if available
        if user_note and len(user_note.strip()) > 0:
            user_note_context = f" and the user's note: '{user_note}'"
            prompt_with_note = prompt_template.replace("{user_note_context}", user_note_context)
        else:
            prompt_with_note = prompt_template.replace("{user_note_context}", "")
        
        combined_template = PromptTemplate(
            input_variables=["content"],
            template=prompt_with_note
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

# Original function signature for backwards compatibility
async def suggest_folder(title: str, description: str, existing_folders: list) -> str:
    """Original function signature that forwards to the enhanced version."""
    return await enhanced_suggest_folder(title, description, "", existing_folders)

# Enhanced function with improved categorization
async def enhanced_suggest_folder(title: str, description: str, user_note: str, existing_folders: list) -> str:
    """Enhanced version that prioritizes user notes and treats folders as broad categories."""
    try:
        # Prioritize user note if available by putting it first in the combined content
        if user_note and user_note.strip():
            # Give the user note higher weight by repeating it and placing it first
            combined_content = f"USER NOTE (Important): {user_note}\n\nTitle: {title}\nDescription: {description}"
        else:
            combined_content = f"{title} - {description}"
        
        # If there are existing folders, check if content matches any of them
        if existing_folders:
            # Create a prompt that asks the model to pick the best matching folder or suggest a new one
            # This revised prompt emphasizes that folders are categories and content can vaguely match
            matching_template = PromptTemplate(
                input_variables=["content", "folders"],
                template="""Consider this content: "{content}"

Here are the existing category folders: {folders}

IMPORTANT GUIDELINES:
1. Treat folders as broad topic categories rather than precise matches.
2. Bookmarked Content can belong to a category even if it's only vaguely related.
3. If the user provided notes, those should be given priority in category matching.
4. It's better to place content in an existing category than create a new one.
5. Only suggest a new category if the content truly doesn't fit any existing categories.

Step 1: Evaluate if the content could reasonably belong in one of the existing folder categories.
Step 2: If it could belong in an existing folder, respond with just that folder name.
Step 3: If it doesn't match any existing folder, respond with a new suggested folder name (maximum 3 words).

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
                    return folder  # Return the exact folder name from the list with original casing
                # Also match if the suggested folder is a substring of an existing folder (or vice versa)
                elif (folder.lower() in folder_suggestion.lower() or 
                      folder_suggestion.lower() in folder.lower()):
                    # If there's significant overlap, use the existing folder
                    if len(folder) >= 3 and len(folder_suggestion) >= 3:
                        return folder
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
        
        # Standardize the folder name (proper capitalization, etc.)
        folder_suggestion = folder_suggestion.strip()
        
        # Capitalize first letter of each word for consistency
        folder_suggestion = " ".join(word.capitalize() for word in folder_suggestion.split())
            
        return folder_suggestion if folder_suggestion and len(folder_suggestion) > 2 else "Uncategorized"
    except Exception as e:
        print(f"Error suggesting folder: {e}")
        return "Uncategorized"

# New function that combines all processing in one call
async def process_bookmark(url: str, user_note: str = "", existing_folders: list = None) -> Tuple[str, str, str]:
    """
    Process a bookmark to generate title, description, and folder suggestion.
    Implements the enhanced algorithm that prioritizes user notes and combines with web content.
    """
    if existing_folders is None:
        existing_folders = []
        
    # Generate title and description, making sure user_note is used
    title, description = await generate_title_description(url, user_note)
    
    # Suggest folder based on combined analysis with high priority for user notes
    # If user provided a note, we should use it as a strong signal for categorization
    folder_name = await enhanced_suggest_folder(title, description, user_note, existing_folders)
    
    # If user's note directly suggests a category and we don't have a good match
    # in existing folders, we should consider using keywords from the note as a category
    if user_note and folder_name == "Uncategorized" and len(user_note.strip()) > 0:
        # Create a special prompt for note-based categorization if all else fails
        matching_template = PromptTemplate(
            input_variables=["note"],
            template="""Based solely on this user note, suggest a category name (2-3 words):
"{note}"

Respond with ONLY the category name."""
        )
        
        # Try to extract a category from just the user's note as a last resort
        try:
            note_chain = matching_template | llm | StrOutputParser()
            note_category = await note_chain.ainvoke({"note": user_note})
            if note_category and len(note_category.strip()) > 3:
                folder_name = note_category.strip()
        except Exception as e:
            print(f"Error extracting category from note: {e}")
    
    return title, description, folder_name