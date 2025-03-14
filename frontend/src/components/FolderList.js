'use client';

import { useState } from 'react';
import { getFolderWithBookmarks, deleteFolder, createFolder } from '../lib/api';
import BookmarkList from './BookmarkList';

export default function FolderList({ folders, onFolderChange }) {
  const [activeFolder, setActiveFolder] = useState(null);
  const [bookmarks, setBookmarks] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deletingFolderId, setDeletingFolderId] = useState(null);
  const [localFolders, setLocalFolders] = useState(folders);
  const [newFolderName, setNewFolderName] = useState('');
  const [isAddingFolder, setIsAddingFolder] = useState(false);

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
    if (!confirm('Are you sure you want to delete this category? This action cannot be undone.')) {
      return;
    }

    try {
      setDeletingFolderId(folderId);
      setError(null);
      
      // Check if folder contains bookmarks
      const folderData = await getFolderWithBookmarks(folderId);
      if (folderData.bookmarks && folderData.bookmarks.length > 0) {
        setError('Cannot delete a category that contains bookmarks. Please delete or move all bookmarks first.');
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
        setError('Cannot delete a category that contains bookmarks. Remove all bookmarks first.');
      } else {
        setError('Failed to delete category. Please try again.');
      }
      console.error(err);
    } finally {
      setDeletingFolderId(null);
    }
  };

  // Handle adding a new folder
  const handleAddFolder = async (e) => {
    e.preventDefault();
    
    if (!newFolderName || newFolderName.trim() === '') {
      setError('Please enter a category name');
      return;
    }

    try {
      setIsAddingFolder(true);
      setError(null);
      
      await createFolder(newFolderName);
      
      // Reset form
      setNewFolderName('');
      
      // Update folders
      if (onFolderChange) {
        onFolderChange();
      }
    } catch (err) {
      if (err.message && err.message.includes('already exists')) {
        setError('A category with this name already exists');
      } else {
        setError('Failed to create category. Please try again.');
      }
      console.error(err);
    } finally {
      setIsAddingFolder(false);
    }
  };

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
      
      {/* Add new folder form */}
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-sm font-medium mb-2">Add New Category</h3>
        <form onSubmit={handleAddFolder} className="flex gap-2">
          <input
            type="text"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            placeholder="Enter category name"
            className="flex-grow px-3 py-2 border border-gray-300 rounded-md text-sm"
          />
          <button
            type="submit"
            disabled={isAddingFolder}
            className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-2 rounded-md text-sm disabled:opacity-50"
          >
            {isAddingFolder ? 'Adding...' : 'Add'}
          </button>
        </form>
      </div>
      
      {/* Folder list */}
      {localFolders.length === 0 ? (
        <p className="text-gray-500 py-4 px-4">No categories yet. Add your first bookmark or create a category above!</p>
      ) : (
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
                    title="Delete category"
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
      )}
    </div>
  );
}