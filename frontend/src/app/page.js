'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { getFolders } from '../lib/api';
import BookmarkForm from '../components/BookmarkForm';
import FolderList from '../components/FolderList';

export default function Home() {
  const [folders, setFolders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
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

    loadFolders();
  }, []);

  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Smart Bookmarker</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">Add New Bookmark</h2>
          <BookmarkForm onSuccess={() => {
            // Reload folders after adding a bookmark
            getFolders().then(data => setFolders(data));
          }} />
        </div>
        
        <div>
          <h2 className="text-xl font-semibold mb-4">Your Bookmark Folders</h2>
          {isLoading ? (
            <p>Loading folders...</p>
          ) : error ? (
            <p className="text-red-500">{error}</p>
          ) : folders.length === 0 ? (
            <p>No folders yet. Add your first bookmark to create a folder!</p>
          ) : (
            <FolderList folders={folders} />
          )}
        </div>
      </div>
    </main>
  );
}