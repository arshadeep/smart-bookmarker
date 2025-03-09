'use client';

import { useState } from 'react';
import Link from 'next/link';
import { getFolderWithBookmarks } from '../lib/api';
import BookmarkList from './BookmarkList';

export default function FolderList({ folders }) {
  const [activeFolder, setActiveFolder] = useState(null);
  const [bookmarks, setBookmarks] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

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

  return (
    <div className="bg-white rounded-lg shadow-md">
      <ul className="divide-y divide-gray-200">
        {folders.map((folder) => (
          <li key={folder.id}>
            <div className="p-4">
              <button
                onClick={() => handleFolderClick(folder.id)}
                className="w-full text-left flex items-center justify-between"
              >
                <span className="font-medium">{folder.name}</span>
                <span>{activeFolder === folder.id ? '▼' : '▶'}</span>
              </button>
              
              {activeFolder === folder.id && (
                <div className="mt-2">
                  {isLoading ? (
                    <p className="text-sm text-gray-500">Loading bookmarks...</p>
                  ) : error ? (
                    <p className="text-sm text-red-500">{error}</p>
                  ) : bookmarks.length === 0 ? (
                    <p className="text-sm text-gray-500">No bookmarks in this folder.</p>
                  ) : (
                    <BookmarkList bookmarks={bookmarks} />
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