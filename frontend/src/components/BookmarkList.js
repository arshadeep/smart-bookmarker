'use client';

import { useState } from 'react';
import BookmarkCard from './BookmarkCard';
import { deleteBookmark } from '../lib/api';

export default function BookmarkList({ bookmarks, onDelete }) {
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);

  const handleDelete = async (id) => {
    try {
      setDeletingId(id);
      setError(null);
      
      await deleteBookmark(id);
      
      // Call parent's onDelete if provided
      if (onDelete) {
        onDelete(id);
      }
    } catch (err) {
      setError('Failed to delete bookmark. Please try again.');
      console.error(err);
    } finally {
      setDeletingId(null);
    }
  };

  if (bookmarks.length === 0) {
    return <p className="text-gray-500 py-2">No bookmarks to display.</p>;
  }

  return (
    <div className="space-y-3 mt-2">
      {error && <p className="text-red-500 text-sm">{error}</p>}
      
      {bookmarks.map((bookmark) => (
        <BookmarkCard
          key={bookmark.id}
          bookmark={bookmark}
          onDelete={() => handleDelete(bookmark.id)}
          isDeleting={deletingId === bookmark.id}
        />
      ))}
    </div>
  );
}