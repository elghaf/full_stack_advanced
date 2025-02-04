// src/components/DocumentPreview.tsx
'use client'

import { useState, useEffect } from 'react';
import { useDocuments } from '@/context/DocumentContext';
import { formatFileSize, formatTimeAgo } from '@/utils/formatters';
import { 
  FiFile, 
  FiFilePlus, 
  FiFileText, 
  FiMoreVertical, 
  FiEye,
  FiChevronRight,
  FiTrash2,
  FiDownload
} from 'react-icons/fi';
import { 
  AiOutlineFilePdf, 
  AiOutlineFileWord, 
  AiOutlineFileText 
} from 'react-icons/ai';
import Image from 'next/image';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';

const DocumentPreview = () => {
  const { uploadedFiles, activeDocument, setActiveDocument, removeDocument } = useDocuments();
  const [currentPage, setCurrentPage] = useState(1);
  const [showAllPages, setShowAllPages] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeDocument) {
      setCurrentPage(1);
      setError(null);
    }
  }, [activeDocument]);

  const handleDeleteDocument = async (documentId: string) => {
    try {
      const response = await fetch(`/api/documents/${documentId}`, {
        method: 'DELETE',
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to delete document');
      }
      
      if (data.success) {
        removeDocument(documentId);
      } else {
        throw new Error(data.error || 'Failed to delete document');
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      alert(error instanceof Error ? error.message : 'Failed to delete document');
    }
  };

  const handleDownloadDocument = async (documentId: string, fileName: string) => {
      try {
        // Remove the extra /api from the URL
        const response = await fetch(`/api/documents/${documentId}/download`);  // Changed from /api/api/documents/...
        if (!response.ok) throw new Error('Download failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (error) {
        console.error('Error downloading document:', error);
        alert('Failed to download document');
      }
  };

  if (!uploadedFiles || uploadedFiles.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center">
          <FiFileText className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No documents</h3>
          <p className="mt-1 text-sm text-gray-500">Upload a document to get started</p>
        </div>
      </div>
    );
  }

  const getFileIcon = (fileType: string) => {
    switch(true) {
      case fileType.includes('pdf'):
        return <AiOutlineFilePdf className="text-red-500 text-xl" />;
      case fileType.includes('doc'):
        return <AiOutlineFileWord className="text-blue-500 text-xl" />;
      default:
        return <AiOutlineFileText className="text-gray-500 text-xl" />;
    }
  };

  const handlePreviewError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    setError('Failed to load preview');
    const target = e.target as HTMLImageElement;
    target.src = "https://ai-public.creatie.ai/gen_page/pdf_preview.png";
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Source Preview Section */}
      {activeDocument && (
        <div className="border-t border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-900">Source Preview</h3>
            <button 
              className="text-xs text-gray-500 hover:text-custom flex items-center gap-1"
              onClick={() => setShowAllPages(!showAllPages)}
            >
              {showAllPages ? 'Show less' : 'View all pages'} <FiChevronRight className="w-4 h-4" />
            </button>
          </div>

          {error && (
            <div className="mt-2 text-sm text-red-600">
              {error}
            </div>
          )}

          <div className={`mt-3 grid gap-4 ${showAllPages ? 'grid-cols-3' : 'flex overflow-x-auto'} pb-2`}>
            {Array.from({ length: activeDocument.pageCount || 1 }).map((_, index) => (
              <div key={index} className={`${showAllPages ? '' : 'flex-none'} w-32`}>
                <div 
                  className={`aspect-[3/4] bg-gray-100 rounded-lg overflow-hidden cursor-pointer ${
                    currentPage === index + 1 ? 'ring-2 ring-custom' : ''
                  }`}
                  onClick={() => setCurrentPage(index + 1)}
                >
                  {activeDocument.previewUrls?.[index] ? (
                    <img
                      src={`${process.env.NEXT_PUBLIC_BACKEND_URL}${activeDocument.previewUrls[index]}`}
                      alt={`Page ${index + 1}`}
                      className="w-full h-full object-cover"
                      onError={handlePreviewError}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <FiFileText className="w-8 h-8 text-gray-400" />
                    </div>
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500 truncate">
                  Page {index + 1}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Documents Section */}
      <h3 className="text-lg font-medium text-gray-900 mt-6">Recent Documents</h3>
      <div className="mt-6 space-y-4">
        {uploadedFiles.map((file) => (
          <div 
            key={file.id}
            className={`bg-gray-50 p-4 rounded-lg hover:bg-gray-100 transition-colors ${
              activeDocument?.id === file.id ? 'ring-2 ring-custom' : ''
            }`}
          >
            <div className="flex items-center">
              <div 
                className="flex-1 flex items-center cursor-pointer"
                onClick={() => setActiveDocument(file)}
              >
                <FiFileText className={`text-xl ${
                  file.type.includes('pdf') ? 'text-red-500' :
                  file.type.includes('doc') ? 'text-blue-500' :
                  'text-gray-500'
                }`} />
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(file.size)} · {formatTimeAgo(new Date(file.uploadedAt))}
                  </p>
                </div>
              </div>
              
              <Menu as="div" className="relative">
                <Menu.Button className="p-2 hover:bg-gray-200 rounded-full">
                  <FiMoreVertical className="w-5 h-5 text-gray-500" />
                </Menu.Button>
                <Transition
                  as={Fragment}
                  enter="transition ease-out duration-100"
                  enterFrom="transform opacity-0 scale-95"
                  enterTo="transform opacity-100 scale-100"
                  leave="transition ease-in duration-75"
                  leaveFrom="transform opacity-100 scale-100"
                  leaveTo="transform opacity-0 scale-95"
                >
                  <Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          className={`${
                            active ? 'bg-gray-100' : ''
                          } group flex w-full items-center px-4 py-2 text-sm text-gray-700`}
                          onClick={() => handleDownloadDocument(file.id, file.name)}
                        >
                          <FiDownload className="mr-3 h-5 w-5" />
                          Download
                        </button>
                      )}
                    </Menu.Item>
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          className={`${
                            active ? 'bg-gray-100' : ''
                          } group flex w-full items-center px-4 py-2 text-sm text-red-600`}
                          onClick={() => handleDeleteDocument(file.id)}
                        >
                          <FiTrash2 className="mr-3 h-5 w-5" />
                          Delete
                        </button>
                      )}
                    </Menu.Item>
                  </Menu.Items>
                </Transition>
              </Menu>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DocumentPreview;