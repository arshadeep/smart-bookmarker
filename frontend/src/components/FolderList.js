'use client';

import { useState } from 'react';
import { getFolderWithBookmarks, deleteFolder } from '../lib/api';
import BookmarkList from './BookmarkList';

export default function FolderList({ folders, onFolderChange }) {
  const [activeFolder, setActiveFolder] = useState(null);
  const [bookmarks, setBookmarks] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deletingFolderId, setDeletingFolderId] = useState(null);
  const [localFolders, setLocalFolders] = useState(folders);

  // Update local folders when prop changes
  if (JSON.stringify(folders) !== JSON.stringify(localFolders)) {
    setLocalFolders(folders);
  }

  const handleFolderClick = async (folderId) => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Toggle folder if it's already active
      if (activeFolder === folderId) {
        setActiveFolder(null);
        setBookmarks([]);
        return;
      }
      
      // Load folder details with bookmarks
      const folderData = await getFolderWithBookmarks(folderId);
      setActiveFolder(folderId);
      setBookmarks(folderData.bookmarks);
    } catch (err) {
      setError('Failed to load bookmarks. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle bookmark deletion
  const handleBookmarkDelete = async (bookmarkId) => {
    // Update the bookmarks state by removing the deleted bookmark
    setBookmarks(bookmarks.filter(bookmark => bookmark.id !== bookmarkId));
  };

  // Handle folder deletion
  const handleFolderDelete = async (folderId) => {
    if (!confirm('Are you sure you want to delete this folder? This action cannot be undone.')) {
      return;
    }

    try {
      setDeletingFolderId(folderId);
      setError(null);
      
      // Check if folder contains bookmarks
      const folderData = await getFolderWithBookmarks(folderId);
      if (folderData.bookmarks && folderData.bookmarks.length > 0) {
        setError('Cannot delete folder with bookmarks. Please delete or move all bookmarks first.');
        return;
      }
      
      await deleteFolder(folderId);
      
      // Update local state
      const updatedFolders = localFolders.filter(folder => folder.id !== folderId);
      setLocalFolders(updatedFolders);
      
      // If we're deleting the active folder, close it
      if (activeFolder === folderId) {
        setActiveFolder(null);
        setBookmarks([]);
      }
      
      // Notify parent component
      if (onFolderChange) {
        onFolderChange();
      }
    } catch (err) {
      // Check if error message contains information about bookmarks
      if (err.message && err.message.includes('bookmarks')) {
        setError('Cannot delete folder that contains bookmarks. Remove all bookmarks first.');
      } else {
        setError('Failed to delete folder. Please try again.');
      }
      console.error(err);
    } finally {
      setDeletingFolderId(null);
    }
  };

  if (localFolders.length === 0) {
    return <p className="text-gray-500 py-4">No folders yet. Add your first bookmark to create a folder!</p>;
  }

  return (
    <div className="bg-white rounded-lg shadow-md">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4">
          <span className="block sm:inline">{error}</span>
          <span 
            className="absolute top-0 bottom-0 right-0 px-4 py-3 cursor-pointer"
            onClick={() => setError(null)}
          >
            <span className="text-red-500">×</span>
          </span>
        </div>
      )}
      
      <ul className="divide-y divide-gray-200">
        {localFolders.map((folder) => (
          <li key={folder.id}>
            <div className="p-4">
              <div className="flex items-center justify-between mb-2">
                <button
                  onClick={() => handleFolderClick(folder.id)}
                  className="text-left flex-grow flex items-center"
                >
                  <span className="font-medium">{folder.name}</span>
                  <span className="ml-2">{activeFolder === folder.id ? '▼' : '▶'}</span>
                </button>
                
                <button
                  onClick={() => handleFolderDelete(folder.id)}
                  disabled={deletingFolderId === folder.id}
                  className="ml-2 text-red-500 hover:text-red-700 text-sm px-2 py-1 rounded-md transition-colors"
                  title="Delete folder"
                >
                  {deletingFolderId === folder.id ? 'Deleting...' : 'Delete'}
                </button>
              </div>
              
              {activeFolder === folder.id && (
                <div className="mt-2 pl-4 border-l-2 border-gray-200">
                  {isLoading ? (
                    <p className="text-sm text-gray-500">Loading bookmarks...</p>
                  ) : (
                    <BookmarkList 
                      bookmarks={bookmarks} 
                      onDelete={handleBookmarkDelete}
                    />
                  )}
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}