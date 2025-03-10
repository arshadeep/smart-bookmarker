from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Bookmark, Folder
from app.schemas.bookmark import BookmarkCreate, Bookmark as BookmarkSchema, BookmarkSuggestion
from app.core.ai import generate_title_description, suggest_folder

router = APIRouter()

@router.post("/", response_model=BookmarkSchema)
async def create_bookmark(bookmark: BookmarkCreate, db: Session = Depends(get_db)):
    """Create a new bookmark with AI-generated title, description, and folder."""
    # Generate title and description using AI
    title, description = await generate_title_description(str(bookmark.url), bookmark.user_note)
    
    # Get all existing folder names
    existing_folders = [folder.name for folder in db.query(Folder).all()]
    
    # Suggest a folder using AI
    folder_name = await suggest_folder(title, description, existing_folders)
    
    # Check if the folder exists, create it if it doesn't
    folder = db.query(Folder).filter(Folder.name == folder_name).first()
    if not folder:
        folder = Folder(name=folder_name)
        db.add(folder)
        db.commit()
        db.refresh(folder)
    
    # Create bookmark
    db_bookmark = Bookmark(
        url=str(bookmark.url),
        title=title,
        description=description,
        user_note=bookmark.user_note,
        folder_id=folder.id
    )
    
    db.add(db_bookmark)
    db.commit()
    db.refresh(db_bookmark)
    
    return db_bookmark

@router.post("/suggest", response_model=BookmarkSuggestion)
async def suggest_bookmark_metadata(bookmark: BookmarkCreate, db: Session = Depends(get_db)):
    """Generate title, description, and folder suggestion without saving."""
    # Generate title and description using AI
    title, description = await generate_title_description(str(bookmark.url), bookmark.user_note)
    
    # Get all existing folder names
    existing_folders = [folder.name for folder in db.query(Folder).all()]
    
    # Suggest a folder using AI
    folder_name = await suggest_folder(title, description, existing_folders)
    
    return BookmarkSuggestion(
        title=title,
        description=description,
        folder_name=folder_name
    )

@router.get("/", response_model=List[BookmarkSchema])
def read_bookmarks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve all bookmarks."""
    bookmarks = db.query(Bookmark).offset(skip).limit(limit).all()
    return bookmarks

@router.get("/{bookmark_id}", response_model=BookmarkSchema)
def read_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific bookmark by ID."""
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if bookmark is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return bookmark

@router.put("/{bookmark_id}", response_model=BookmarkSchema)
def update_bookmark(
    bookmark_id: int, 
    title: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    user_note: Optional[str] = Body(None),
    folder_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Update a bookmark's metadata."""
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if bookmark is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    # Update only the fields that were provided
    if title is not None:
        bookmark.title = title
    if description is not None:
        bookmark.description = description
    if user_note is not None:
        bookmark.user_note = user_note
    if folder_id is not None:
        # Verify the folder exists
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        bookmark.folder_id = folder_id
    
    db.commit()
    db.refresh(bookmark)
    return bookmark

@router.delete("/{bookmark_id}")
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    """Delete a bookmark by ID."""
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if bookmark is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    db.delete(bookmark)
    db.commit()
    
    return {"message": "Bookmark deleted successfully"}