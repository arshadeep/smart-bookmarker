import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API configurations
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
if not HUGGINGFACE_API_KEY:
    raise ValueError("HUGGINGFACE_API_KEY environment variable is not set")

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bookmarks.db")