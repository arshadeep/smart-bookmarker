from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal
from app.db.models import Folder
from app.schemas.folder import FolderCreate, Folder as FolderSchema, FolderWithBookmarks

router = APIRouter()

@router.post("/", response_model=FolderSchema)
def create_folder(folder: FolderCreate, db: Session = Depends(get_db)):
    """Create a new folder."""
    # Check if folder with same name already exists
    db_folder = db.query(Folder).filter(Folder.name == folder.name).first()
    if db_folder:
        raise HTTPException(status_code=400, detail="Folder with this name already exists")
    
    # Create new folder
    db_folder = Folder(name=folder.name)
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    
    return db_folder

@router.get("/", response_model=List[FolderSchema])
def read_folders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve all folders."""
    folders = db.query(Folder).offset(skip).limit(limit).all()
    return folders

@router.get("/{folder_id}", response_model=FolderWithBookmarks)
def read_folder(folder_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific folder by ID, including its bookmarks."""
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder

@router.delete("/{folder_id}")
def delete_folder(folder_id: int, db: Session = Depends(get_db)):
    """Delete a folder by ID."""
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Check if folder has bookmarks
    if folder.bookmarks:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete folder with bookmarks. Move or delete bookmarks first."
        )
    
    db.delete(folder)
    db.commit()
    
    return {"message": "Folder deleted successfully"}