'use client';

export default function BookmarkCard({ bookmark, onDelete, isDeleting }) {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  return (
    <div className="bg-gray-50 p-3 rounded-md border border-gray-200">
      <div className="flex justify-between">
        <h3 className="font-medium text-blue-600 truncate">
          <a 
            href={bookmark.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="hover:underline"
          >
            {bookmark.title}
          </a>
        </h3>
        
        <button
          onClick={onDelete}
          disabled={isDeleting}
          className="text-red-500 hover:text-red-700 text-sm"
          title="Delete bookmark"
        >
          {isDeleting ? 'Deleting...' : '✕'}
        </button>
      </div>
      
      {/* Display user notes first if they exist */}
      {bookmark.user_note && (
        <div className="mt-2 text-sm bg-blue-50 p-2 rounded border-l-2 border-blue-300">
          <p className="font-medium text-gray-700">Your note:</p>
          <p className="text-gray-800">{bookmark.user_note}</p>
        </div>
      )}
      
      {bookmark.description && (
        <p className="text-sm text-gray-600 mt-2 line-clamp-2 overflow-hidden">
          {bookmark.description}
        </p>
      )}
      
      <div className="mt-2 flex justify-between text-xs text-gray-500">
        <span>{new URL(bookmark.url).hostname}</span>
        <span>Saved on {formatDate(bookmark.created_at)}</span>
      </div>
    </div>
  );
}