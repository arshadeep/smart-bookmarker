'use client';

import { useState } from 'react';
import { createFolder } from '../lib/api';

export default function FolderForm({ onSuccess }) {
  const [folderName, setFolderName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!folderName.trim()) {
      setError('Folder name is required');
      return;
    }
    
    try {
      setIsLoading(true);
      setError(null);
      
      await createFolder(folderName);
      
      // Reset the form
      setFolderName('');
      
      // Trigger success callback
      if (onSuccess) {
        onSuccess();
      }
      
    } catch (err) {
      if (err.message && err.message.includes('already exists')) {
        setError('A folder with this name already exists.');
      } else {
        setError('Failed to create folder. Please try again.');
      }
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-md mb-4">
      <h3 className="text-lg font-medium mb-3">Create New Folder</h3>
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label htmlFor="folderName" className="block text-sm font-medium text-gray-700 mb-1">
            Folder Name
          </label>
          <input
            type="text"
            id="folderName"
            value={folderName}
            onChange={(e) => setFolderName(e.target.value)}
            placeholder="Enter folder name"
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            required
          />
        </div>
        
        {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
        
        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded-md text-sm disabled:opacity-50"
        >
          {isLoading ? 'Creating...' : 'Create Folder'}
        </button>
      </form>
    </div>
  );
}