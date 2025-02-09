// src/components/DocumentPreview.tsx
'use client'

import React, { useState } from 'react';
import { FiFile, FiX, FiDownload, FiEye, FiChevronDown, FiChevronUp, FiClock, FiFileText } from 'react-icons/fi';
import { useDocuments } from '@/hooks/useDocuments';
import { format } from 'date-fns';
import { formatFileSize } from '@/utils/formatters';

interface PreviewZone {
  page: number;
  startLine: number;
  endLine: number;
  text: string;
  sectionTitle?: string;
}

const DocumentPreview = () => {
  const { documents, isLoading, error, deleteDocument, downloadDocument } = useDocuments();
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [chunkLimit, setChunkLimit] = useState<{ [key: string]: number }>({});

  const CHUNKS_PER_PAGE = 5;

  const handlePreviewClick = async (documentId: string) => {
    if (selectedDoc === documentId) {
      setSelectedDoc(null);
      // Reset chunk limit when closing
      setChunkLimit(prev => ({ ...prev, [documentId]: CHUNKS_PER_PAGE }));
    } else {
      setSelectedDoc(documentId);
      // Initialize chunk limit for this document
      setChunkLimit(prev => ({ ...prev, [documentId]: CHUNKS_PER_PAGE }));
    }
  };

  const handleShowMore = (documentId: string, totalChunks: number) => {
    setChunkLimit(prev => ({
      ...prev,
      [documentId]: Math.min((prev[documentId] || CHUNKS_PER_PAGE) + CHUNKS_PER_PAGE, totalChunks)
    }));
  };

  const handleShowLess = (documentId: string) => {
    setChunkLimit(prev => ({
      ...prev,
      [documentId]: CHUNKS_PER_PAGE
    }));
  };

  const formatPreviewText = (text: string): string => {
    return text
      .replace(/\s+/g, ' ')
      .trim();
  };

  const truncateFileName = (name: string): string => {
    const maxLength = 20;
    if (name.length <= maxLength) return name;
    
    const extension = name.split('.').pop();
    const baseName = name.slice(0, name.lastIndexOf('.'));
    const truncated = baseName.slice(0, maxLength - 3) + '...';
    return `${truncated}.${extension}`;
  };

  if (isLoading) {
    return (
      <div className="min-h-[400px] flex justify-center items-center">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 border-t-blue-500" />
          <p className="text-gray-500">Loading documents...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[400px] flex justify-center items-center">
        <div className="text-center max-w-md mx-auto p-6 bg-red-50 rounded-lg">
          <div className="text-red-500 font-medium mb-2">Error loading documents</div>
          <div className="text-sm text-red-400">{error}</div>
        </div>
      </div>
    );
  }

  if (!documents.length) {
    return (
      <div className="min-h-[400px] flex justify-center items-center">
        <div className="text-center">
          <FiFileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No documents uploaded yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full p-4">
      <h2 className="text-lg font-semibold mb-4 text-gray-800">Documents</h2>
      <div className="space-y-4">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden transition-all duration-200 hover:shadow-md"
          >
            <div className="p-4">
              <div className="flex justify-between items-start">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <FiFile className="w-5 h-5 text-blue-500" />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm text-gray-800" title={doc.name}>
                      {truncateFileName(doc.name)}
                    </h3>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                      <FiClock className="w-3 h-3" />
                      <span>
                        {format(new Date(doc.uploadedAt), 'MMM d, yyyy')}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => handlePreviewClick(doc.id)}
                  className="p-1.5 text-gray-500 hover:text-blue-500 rounded-lg hover:bg-blue-50 transition-colors"
                >
                  {selectedDoc === doc.id ? (
                    <FiChevronUp className="w-4 h-4" />
                  ) : (
                    <FiChevronDown className="w-4 h-4" />
                  )}
                </button>
              </div>

              {selectedDoc === doc.id && (
                <div className="mt-4 border-t pt-4">
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs font-medium text-gray-500">Pages</div>
                      <div className="mt-1 text-lg font-semibold text-gray-800">
                        {doc.pageCount || 1}
                      </div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs font-medium text-gray-500">Chunks</div>
                      <div className="mt-1 text-lg font-semibold text-gray-800">
                        {doc.previewZones?.length || 0}
                      </div>
                    </div>
                  </div>

                  {doc.previewZones && doc.previewZones.length > 0 ? (
                    <div className="space-y-3">
                      {doc.previewZones
                        .slice(0, chunkLimit[doc.id] || CHUNKS_PER_PAGE)
                        .map((zone, index) => (
                          <div
                            key={index}
                            className="bg-gray-50 rounded-lg p-3 text-sm"
                          >
                            <div className="flex justify-between items-start mb-2">
                              <div className="text-xs font-medium text-gray-900">
                                {zone.sectionTitle || `Chunk ${index + 1}`}
                              </div>
                              <div className="text-xs px-2 py-0.5 bg-gray-200 rounded text-gray-600">
                                Page {zone.page} • Lines {zone.startLine}-{zone.endLine}
                              </div>
                            </div>
                            <div className="prose prose-sm max-w-none">
                              <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap">
                                {formatPreviewText(zone.text)}
                              </p>
                            </div>
                          </div>
                        ))}
                      
                      {/* Show More/Less buttons */}
                      {doc.previewZones.length > CHUNKS_PER_PAGE && (
                        <div className="flex justify-center pt-2">
                          {(chunkLimit[doc.id] || CHUNKS_PER_PAGE) < doc.previewZones.length ? (
                            <button
                              onClick={() => handleShowMore(doc.id, doc.previewZones.length)}
                              className="text-sm text-blue-500 hover:text-blue-600 flex items-center gap-1"
                            >
                              Show More <FiChevronDown className="w-4 h-4" />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleShowLess(doc.id)}
                              className="text-sm text-blue-500 hover:text-blue-600 flex items-center gap-1"
                            >
                              Show Less <FiChevronUp className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-sm text-gray-500">
                      No preview chunks available for this document
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DocumentPreview;