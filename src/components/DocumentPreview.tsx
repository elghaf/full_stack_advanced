// src/components/DocumentPreview.tsx
'use client'

import { useState } from 'react';
import { useDocuments } from '@/context/DocumentContext';
import { formatFileSize, formatTimeAgo } from '@/utils/formatters';
import { 
  FiFile, 
  FiFilePlus, 
  FiFileText, 
  FiMoreVertical, 
  FiEye,
  FiChevronRight
} from 'react-icons/fi';
import { 
  AiOutlineFilePdf, 
  AiOutlineFileWord, 
  AiOutlineFileText 
} from 'react-icons/ai';

const DocumentPreview = () => {
  const { uploadedFiles, activeDocument, setActiveDocument } = useDocuments();
  const [previewPage, setPreviewPage] = useState(1);

  if (!uploadedFiles || uploadedFiles.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center">
          <FiFilePlus className="mx-auto h-12 w-12 text-gray-400" />
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

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Source Preview Section */}
      {activeDocument && (
        <div className="border-t border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-900">Source Preview</h3>
            <button 
              className="text-xs text-gray-500 hover:text-custom flex items-center gap-1"
              onClick={() => setPreviewPage(1)}
            >
              View all <FiChevronRight className="w-4 h-4" />
            </button>
          </div>
          <div className="mt-3 flex space-x-2 overflow-x-auto pb-2">
            {[...Array(activeDocument.pageCount || 1)].map((_, index) => (
              <div key={index} className="flex-none w-32">
                <div 
                  className={`aspect-[3/4] bg-gray-100 rounded-lg overflow-hidden cursor-pointer ${
                    previewPage === index + 1 ? 'ring-2 ring-custom' : ''
                  }`}
                  onClick={() => setPreviewPage(index + 1)}
                >
                  {activeDocument.previewUrls?.[index] ? (
                    <img 
                      src={activeDocument.previewUrls[index]} 
                      alt={`Page ${index + 1}`}
                      className="w-full h-full object-cover"
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
            className={`bg-gray-50 p-4 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer ${
              activeDocument?.id === file.id ? 'ring-2 ring-custom' : ''
            }`}
            onClick={() => setActiveDocument(file)}
          >
            <div className="flex items-center">
              {getFileIcon(file.type)}
              <div className="ml-3 flex-1">
                <p className="text-sm font-medium text-gray-900">{file.name}</p>
                <p className="text-xs text-gray-500">
                  {formatFileSize(file.size)} · Uploaded {formatTimeAgo(new Date(file.uploadedAt))}
                </p>
              </div>
              <button 
                className="text-gray-400 hover:text-gray-500"
                onClick={(e) => {
                  e.stopPropagation();
                  // Add document options menu here
                }}
              >
                <FiMoreVertical className="w-5 h-5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DocumentPreview;