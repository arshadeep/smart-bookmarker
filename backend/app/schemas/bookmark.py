from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

# Shared properties
class BookmarkBase(BaseModel):
    url: HttpUrl
    user_note: Optional[str] = None
    # Adding optional fields for when the frontend provides suggested values
    title: Optional[str] = None
    description: Optional[str] = None
    folder_name: Optional[str] = None

# Properties to receive on bookmark creation
class BookmarkCreate(BookmarkBase):
    pass

# Properties to return to client
class Bookmark(BookmarkBase):
    id: int
    title: str
    description: Optional[str] = None
    folder_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# Schema for AI-generated suggestion
class BookmarkSuggestion(BaseModel):
    title: str
    description: str
    folder_name: str