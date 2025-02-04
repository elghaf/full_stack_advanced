import { Metadata } from 'next';
import { Inter } from "next/font/google";
import "@/styles/globals.css";
import { DocumentProvider } from '@/context/DocumentContext';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'Document Chat',
  description: 'Chat with your documents using AI',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
          rel="stylesheet"
        />
      </head>
      <body className={`${inter.className} bg-gray-50 font-sans min-h-screen flex flex-col`}>
        <DocumentProvider>
          <Navbar />
          {children}
        </DocumentProvider>
      </body>
    </html>
  );
}

const Navbar = () => (
  <nav className="bg-white border-b border-gray-200">
    <div className="max-w-8xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between h-16">
        <div className="flex">
          <div className="flex-shrink-0 flex items-center">
            <img
              className="h-8 w-auto"
              src="https://ai-public.creatie.ai/gen_page/logo_placeholder.png"
              alt="Logo"
            />
          </div>
          <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
            <a
              href="#"
              className="border-custom text-custom inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
            >
              Documents
            </a>
            <a
              href="#"
              className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
            >
              History
            </a>
            <a
              href="#"
              className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
            >
              Settings
            </a>
          </div>
        </div>
        <div className="flex items-center">
          <button
            type="button"
            className="bg-gray-100 p-1 rounded-full text-gray-400 hover:text-gray-500 focus:outline-none"
          >
            <i className="fas fa-moon"></i>
          </button>
          <div className="ml-3 relative">
            <div>
              <button
                type="button"
                className="bg-white rounded-full flex text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-custom"
                id="user-menu-button"
              >
                <img
                  className="h-8 w-8 rounded-full"
                  src="https://creatie.ai/ai/api/search-image?query=A professional headshot photo of a young business person with a friendly smile, wearing smart casual attire, against a neutral background&width=32&height=32&orientation=squarish&flag=87367a5d-4bfa-44b3-90ba-791edc759e6a&flag=c7369f39-6882-4c3d-b7d2-e5ac618c1591"
                  alt=""
                />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </nav>
);