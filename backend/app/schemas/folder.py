from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.bookmark import Bookmark

# Shared properties
class FolderBase(BaseModel):
    name: str

# Properties to receive on folder creation
class FolderCreate(FolderBase):
    pass

# Properties to return to client
class Folder(FolderBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# Extended folder model with bookmarks included
class FolderWithBookmarks(Folder):
    bookmarks: List[Bookmark] = []