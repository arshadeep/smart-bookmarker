import './globals.css';

export const metadata = {
  title: 'Smart Bookmarker',
  description: 'AI-powered bookmark organization',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-100 min-h-screen">
        <nav className="bg-blue-600 text-white p-4">
          <div className="container mx-auto flex justify-between items-center">
            <a href="/" className="text-xl font-bold">Smart Bookmarker</a>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}