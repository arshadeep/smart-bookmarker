from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationship with bookmarks
    bookmarks = relationship("Bookmark", back_populates="folder")


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    title = Column(String)
    description = Column(Text, nullable=True)
    user_note = Column(Text, nullable=True)
    folder_id = Column(Integer, ForeignKey("folders.id"))
    created_at = Column(DateTime, default=func.now())
    
    # Relationship with folder
    folder = relationship("Folder", back_populates="bookmarks")