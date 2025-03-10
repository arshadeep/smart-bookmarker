'use client';

import { useState, useEffect } from 'react';
import { getFolders } from '../lib/api';
import BookmarkForm from '../components/BookmarkForm';
import FolderList from '../components/FolderList';

export default function Home() {
  const [folders, setFolders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadFolders = async () => {
    try {
      setIsLoading(true);
      const data = await getFolders();
      setFolders(data);
      setError(null);
    } catch (err) {
      setError('Failed to load folders. Please try again later.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFolders();
  }, []);

  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Smart Bookmarker</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">Add New Bookmark</h2>
          <BookmarkForm onSuccess={loadFolders} />
        </div>
        
        <div>
          <h2 className="text-xl font-semibold mb-4">Your Bookmark Folders</h2>
          {isLoading ? (
            <p>Loading folders...</p>
          ) : error ? (
            <p className="text-red-500">{error}</p>
          ) : (
            <FolderList folders={folders} onFolderChange={loadFolders} />
          )}
        </div>
      </div>
    </main>
  );
}