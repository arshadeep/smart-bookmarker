// API client functions for interacting with the backend

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Bookmark API functions
export async function addBookmark(bookmark) {
  try {
    // We now pass the full bookmark object which may include title, description, and folder_name
    const response = await fetch(`${API_BASE_URL}/bookmarks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(bookmark),
    });
    
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error adding bookmark:', error);
    throw error;
  }
}

export async function getBookmarkSuggestion(bookmark) {
  try {
    const response = await fetch(`${API_BASE_URL}/bookmarks/suggest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(bookmark),
    });
    
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error getting bookmark suggestion:', error);
    throw error;
  }
}

export async function getBookmarks() {
  try {
    const response = await fetch(`${API_BASE_URL}/bookmarks`);
    
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching bookmarks:', error);
    throw error;
  }
}

export async function deleteBookmark(id) {
  try {
    const response = await fetch(`${API_BASE_URL}/bookmarks/${id}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error deleting bookmark:', error);
    throw error;
  }
}

// Folder API functions
export async function getFolders() {
  try {
    const response = await fetch(`${API_BASE_URL}/folders`);
    
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching folders:', error);
    throw error;
  }
}

export async function getFolderWithBookmarks(id) {
  try {
    const response = await fetch(`${API_BASE_URL}/folders/${id}`);
    
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching folder:', error);
    throw error;
  }
}

export async function deleteFolder(id) {
  try {
    const response = await fetch(`${API_BASE_URL}/folders/${id}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      // Try to parse error message from response
      const errorData = await response.json();
      throw new Error(errorData.detail || `Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error deleting folder:', error);
    throw error;
  }
}

export async function createFolder(folderName) {
  try {
    const response = await fetch(`${API_BASE_URL}/folders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name: folderName }),
    });
    
    if (!response.ok) {
      // Try to get detailed error message if available
      try {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error: ${response.status}`);
      } catch {
        throw new Error(`Error: ${response.status}`);
      }
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error creating folder:', error);
    throw error;
  }
}