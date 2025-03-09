'use client';

import { useState } from 'react';
import { addBookmark, getBookmarkSuggestion } from '../lib/api';

export default function BookmarkForm({ onSuccess }) {
  const [url, setUrl] = useState('');
  const [note, setNote] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suggestion, setSuggestion] = useState(null);
  const [showSuggestion, setShowSuggestion] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!url) {
      setError('URL is required');
      return;
    }
    
    try {
      setIsLoading(true);
      setError(null);
      
      // Get a suggestion first (optional step)
      if (!showSuggestion) {
        const suggestionData = await getBookmarkSuggestion({ url, user_note: note });
        setSuggestion(suggestionData);
        setShowSuggestion(true);
        return;
      }
      
      // Actually save the bookmark
      await addBookmark({ url, user_note: note });
      
      // Reset the form
      setUrl('');
      setNote('');
      setSuggestion(null);
      setShowSuggestion(false);
      
      // Trigger success callback
      if (onSuccess) {
        onSuccess();
      }
      
    } catch (err) {
      setError('Failed to add bookmark. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Save the bookmark
      await addBookmark({ url, user_note: note });
      
      // Reset the form
      setUrl('');
      setNote('');
      setSuggestion(null);
      setShowSuggestion(false);
      
      // Trigger success callback
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError('Failed to add bookmark. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setShowSuggestion(false);
    setSuggestion(null);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      {!showSuggestion ? (
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
              URL *
            </label>
            <input
              type="url"
              id="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            />
          </div>
          
          <div className="mb-6">
            <label htmlFor="note" className="block text-sm font-medium text-gray-700 mb-1">
              Note (optional)
            </label>
            <textarea
              id="note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Why are you saving this bookmark?"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows="3"
            />
          </div>
          
          {error && <p className="text-red-500 mb-4">{error}</p>}
          
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md disabled:opacity-50"
          >
            {isLoading ? 'Processing...' : 'Add Bookmark'}
          </button>
        </form>
      ) : (
        <div>
          <h3 className="font-semibold text-lg mb-2">AI Suggestion</h3>
          
          {suggestion && (
            <div className="mb-4">
              <p className="font-medium">Title:</p>
              <p className="mb-2">{suggestion.title}</p>
              
              <p className="font-medium">Description:</p>
              <p className="mb-2">{suggestion.description}</p>
              
              <p className="font-medium">Folder:</p>
              <p className="mb-4">{suggestion.folder_name}</p>
            </div>
          )}
          
          <div className="flex space-x-4">
            <button
              onClick={handleConfirm}
              disabled={isLoading}
              className="flex-1 bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded-md disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : 'Save Bookmark'}
            </button>
            
            <button
              onClick={handleCancel}
              disabled={isLoading}
              className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-800 font-medium py-2 px-4 rounded-md disabled:opacity-50"
            >
              Try Again
            </button>
          </div>
        </div>
      )}
    </div>
  );
}