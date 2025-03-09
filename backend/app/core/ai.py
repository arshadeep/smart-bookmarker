import requests
import json
from typing import Dict, Optional, Tuple
import httpx
from app.config import HUGGINGFACE_API_KEY
from bs4 import BeautifulSoup

# Headers for HuggingFace API requests
headers = {
    "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
    "Content-Type": "application/json"
}

# Using Llama models from Hugging Face
# You can replace these with other Llama variants based on your needs
LLAMA_TEXT_GENERATION_API = "https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-chat-hf"
LLAMA_CLASSIFICATION_API = "https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-hf"

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
            
            # Limit to a reasonable length for the API
            main_content = main_content[:1500]
            
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
    """Generate a title and description for a bookmark using Llama."""
    try:
        # Fetch content from the URL
        content = await fetch_url_content(url)
        
        # Format prompt for Llama (these models often need specific prompt formatting)
        title_prompt = f"""<s>[INST] Generate a concise, descriptive title (maximum 10 words) for this web page content:

{content}

Title: [/INST]"""
        
        title_payload = {
            "inputs": title_prompt,
            "parameters": {
                "max_new_tokens": 30,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True
            }
        }
        
        title_response = requests.post(LLAMA_TEXT_GENERATION_API, headers=headers, json=title_payload)
        title_response.raise_for_status()
        
        # Parse Llama response (format may vary depending on model)
        title_text = title_response.json()[0].get("generated_text", "")
        # Extract the part after the prompt
        if '[/INST]' in title_text:
            title = title_text.split('[/INST]')[1].strip()
        else:
            title = title_text.replace(title_prompt, "").strip()
        
        # Format description prompt for Llama
        desc_prompt = f"""<s>[INST] Summarize the following web page content in one or two sentences:

{content}

Summary: [/INST]"""
        
        desc_payload = {
            "inputs": desc_prompt,
            "parameters": {
                "max_new_tokens": 100,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True
            }
        }
        
        desc_response = requests.post(LLAMA_TEXT_GENERATION_API, headers=headers, json=desc_payload)
        desc_response.raise_for_status()
        
        # Parse Llama response
        desc_text = desc_response.json()[0].get("generated_text", "")
        if '[/INST]' in desc_text:
            description = desc_text.split('[/INST]')[1].strip()
        else:
            description = desc_text.replace(desc_prompt, "").strip()
        
        # Clean up potential artifacts
        title = title.replace("<s>", "").replace("</s>", "").strip()
        description = description.replace("<s>", "").replace("</s>", "").strip()
        
        return title, description
    except Exception as e:
        print(f"Error generating title/description: {e}")
        # Fallback to a simple title and description based on the URL
        return url.split("//")[-1].split("/")[0], "No description available"

async def suggest_folder(title: str, description: str, existing_folders: list) -> str:
    """Suggest a human-like folder name based on the bookmark content using Llama."""
    try:
        # First, check if any existing folders semantically match the content
        if existing_folders:
            # Format prompt for Llama
            match_prompt = f"""<s>[INST] I have a bookmark with title '{title}' and description '{description}'.

Which of these folders would be the best match for it: {', '.join(existing_folders)}?
If none of these folders is a good semantic match, respond with "NONE".

Answer with just the folder name or "NONE". [/INST]"""
            
            match_payload = {
                "inputs": match_prompt,
                "parameters": {
                    "max_new_tokens": 30,
                    "temperature": 0.2,  # Lower temperature for more predictable answers
                    "top_p": 0.9,
                    "do_sample": True
                }
            }
            
            match_response = requests.post(LLAMA_TEXT_GENERATION_API, headers=headers, json=match_payload)
            match_response.raise_for_status()
            
            match_text = match_response.json()[0].get("generated_text", "")
            if '[/INST]' in match_text:
                suggested_folder = match_text.split('[/INST]')[1].strip()
            else:
                suggested_folder = match_text.replace(match_prompt, "").strip()
            
            # Clean up the response to just get the folder name
            suggested_folder = suggested_folder.split()[0] if suggested_folder else ""
            
            # Only use existing folder if it's explicitly matched and not NONE
            if suggested_folder in existing_folders and suggested_folder.upper() != "NONE":
                # Double-check the relevance - ask for confidence score (0-10)
                # Format confidence prompt for Llama
                confidence_prompt = f"""<s>[INST] On a scale of 0-10, how confident are you that the bookmark with:
Title: '{title}'
Description: '{description}'
belongs in the folder '{suggested_folder}'?

Answer with just a number. [/INST]"""
                
                confidence_payload = {
                    "inputs": confidence_prompt,
                    "parameters": {
                        "max_new_tokens": 10,
                        "temperature": 0.2,
                        "top_p": 0.9,
                        "do_sample": True
                    }
                }
                
                confidence_response = requests.post(LLAMA_TEXT_GENERATION_API, headers=headers, json=confidence_payload)
                confidence_response.raise_for_status()
                
                confidence_text = confidence_response.json()[0].get("generated_text", "")
                if '[/INST]' in confidence_text:
                    confidence = confidence_text.split('[/INST]')[1].strip()
                else:
                    confidence = confidence_text.replace(confidence_prompt, "").strip()
                
                try:
                    # Extract the first number in the response
                    import re
                    confidence_match = re.search(r'\d+', confidence)
                    if confidence_match:
                        confidence_score = int(confidence_match.group())
                        # Only use the existing folder if confidence is high
                        if confidence_score >= 7:
                            return suggested_folder
                except Exception as e:
                    print(f"Error parsing confidence score: {e}")
                    # If we can't parse the confidence, be cautious and create a new folder
                    pass
        
        # If no good match or low confidence, suggest a new broad category folder name
        # Format new folder prompt for Llama
        new_folder_prompt = f"""<s>[INST] Based on this bookmark with title '{title}' and description '{description}', suggest a broad, generic category folder name that a human would create to organize this content.

Folder names should be general categories, not specific to the bookmark content.

Examples of good folder names:
- "AI & Machine Learning"
- "Cooking Recipes"
- "Web Development"
- "Personal Finance"
- "Travel Destinations"
- "Health & Fitness"
- "Book Recommendations"
- "Tech News"
- "Educational Resources"
- "Business Strategy"

Suggest just ONE simple, clear category name (2-3 words maximum). [/INST]"""
        
        new_folder_payload = {
            "inputs": new_folder_prompt,
            "parameters": {
                "max_new_tokens": 30,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True
            }
        }
        
        new_folder_response = requests.post(LLAMA_TEXT_GENERATION_API, headers=headers, json=new_folder_payload)
        new_folder_response.raise_for_status()
        
        new_folder_text = new_folder_response.json()[0].get("generated_text", "")
        if '[/INST]' in new_folder_text:
            suggested_category = new_folder_text.split('[/INST]')[1].strip()
        else:
            suggested_category = new_folder_text.replace(new_folder_prompt, "").strip()
        
        # Clean up potential artifacts and get first line only
        suggested_category = suggested_category.replace("<s>", "").replace("</s>", "").strip()
        suggested_category = suggested_category.split("\n")[0] if "\n" in suggested_category else suggested_category
        
        # Ensure we're getting a category, not specific content
        if len(suggested_category.split()) > 3 or len(suggested_category) > 30:
            # Too long or specific, try a second attempt with stricter instructions
            # Format retry prompt for Llama
            retry_prompt = f"""<s>[INST] Please provide a SHORT, GENERIC category name (maximum 3 words) for content about:
'{title} - {description}'

Examples: "Tech News", "Cooking", "Travel", "Finance", "Education"

Just the category name: [/INST]"""
            
            retry_payload = {
                "inputs": retry_prompt,
                "parameters": {
                    "max_new_tokens": 20,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "do_sample": True
                }
            }
            
            retry_response = requests.post(LLAMA_TEXT_GENERATION_API, headers=headers, json=retry_payload)
            retry_response.raise_for_status()
            
            retry_text = retry_response.json()[0].get("generated_text", "")
            if '[/INST]' in retry_text:
                suggested_category = retry_text.split('[/INST]')[1].strip()
            else:
                suggested_category = retry_text.replace(retry_prompt, "").strip()
            
            # Get only the first line and clean up
            suggested_category = suggested_category.split("\n")[0] if "\n" in suggested_category else suggested_category
            suggested_category = suggested_category.replace("<s>", "").replace("</s>", "").strip()
        
        return suggested_category
    except Exception as e:
        print(f"Error suggesting folder: {e}")
        return "Uncategorized"