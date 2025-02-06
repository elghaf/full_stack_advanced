// src/components/DocumentPreview.tsx
'use client'

import { useState, useEffect, useCallback } from 'react';
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
  const [isDownloading, setIsDownloading] = useState(false);

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

  const handleDownloadDocument = useCallback(async () => {
    if (!activeDocument?.id) return;

    try {
      const response = await fetch(`/api/documents/${activeDocument.id}/download`);
      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = activeDocument.name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading document:', error);
    }
  }, [activeDocument?.id]);

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
    target.src = "/images/pdf_preview_fallback.png";
  };

  if (!activeDocument) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center">
          <p>No document selected</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Document header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">{activeDocument.name}</h2>
          <div className="flex space-x-2">
            <button
              onClick={handleDownloadDocument}
              disabled={isDownloading}
              className="p-2 text-gray-600 hover:text-custom rounded-full hover:bg-gray-100"
            >
              <FiDownload className="w-5 h-5" />
            </button>
            <button
              onClick={() => removeDocument(activeDocument.id)}
              className="p-2 text-gray-600 hover:text-red-500 rounded-full hover:bg-gray-100"
            >
              <FiTrash2 className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="mt-1 text-sm text-gray-500">
          {formatFileSize(activeDocument?.size || 0)} • Uploaded {formatTimeAgo(new Date(activeDocument?.uploadedAt || ''))}
        </div>
      </div>

      {/* Document preview */}
      <div className="flex-1 overflow-auto p-4">
        {activeDocument.previewUrls && activeDocument.previewUrls.length > 0 ? (
          activeDocument.previewUrls.map((url, index) => (
            <img
              key={url}
              src={url}
              alt={`Page ${index + 1}`}
              className="w-full mb-4 shadow-lg rounded-lg"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.onerror = null;
                target.src = "/images/pdf_preview_fallback.png";
              }}
            />
          ))
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <FiFile className="text-4xl mb-4" />
            <p>No preview available</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentPreview;