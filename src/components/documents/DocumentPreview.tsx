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
  const [previewZones, setPreviewZones] = useState<PreviewZone[]>([]);

  const fetchPreviewZones = async (documentId: string) => {
    try {
      const response = await fetch(`/api/documents/${documentId}/preview`);
      if (!response.ok) throw new Error('Failed to fetch preview');
      const data = await response.json();
      setPreviewZones(data.zones || []);
    } catch (error) {
      console.error('Error fetching preview:', error);
      setPreviewZones([]);
    }
  };

  const handlePreviewClick = async (documentId: string) => {
    if (selectedDoc === documentId) {
      setSelectedDoc(null);
      setPreviewZones([]);
    } else {
      setSelectedDoc(documentId);
      await fetchPreviewZones(documentId);
    }
  };

  const formatPreviewText = (text: string): string => {
    // Remove excessive spaces and normalize line breaks
    return text
      .replace(/\s+/g, ' ')  // Replace multiple spaces with single space
      .replace(/\s+\n\s+/g, '\n')  // Clean up spaces around line breaks
      .trim();  // Remove leading/trailing whitespace
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
    <div className="max-w-5xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-8 text-gray-800">Documents</h2>
      <div className="space-y-6">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden transition-all duration-200 hover:shadow-md"
          >
            <div className="p-6">
              <div className="flex justify-between items-start">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <FiFile className="w-6 h-6 text-blue-500" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg text-gray-800" title={doc.name}>
                      {truncateFileName(doc.name)}
                    </h3>
                    <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
                      <FiClock className="w-4 h-4" />
                      <span>
                        {format(new Date(doc.uploadedAt * 1000), 'MMM d, yyyy')}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handlePreviewClick(doc.id)}
                    className="p-2 text-gray-500 hover:text-blue-500 rounded-lg hover:bg-blue-50 transition-colors"
                    title={selectedDoc === doc.id ? "Hide Preview" : "Show Preview"}
                  >
                    {selectedDoc === doc.id ? <FiChevronUp className="w-5 h-5" /> : <FiChevronDown className="w-5 h-5" />}
                  </button>
                  <button
                    onClick={() => downloadDocument(doc.id)}
                    className="p-2 text-gray-500 hover:text-blue-500 rounded-lg hover:bg-blue-50 transition-colors"
                    title="Download"
                  >
                    <FiDownload className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => deleteDocument(doc.id)}
                    className="p-2 text-gray-500 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                    title="Delete"
                  >
                    <FiX className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {selectedDoc === doc.id && (
                <div className="mt-6 border-t pt-6">
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="text-sm font-medium text-gray-500">Pages</div>
                      <div className="mt-1 text-2xl font-semibold text-gray-800">
                        {doc.pageCount || 1}
                      </div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="text-sm font-medium text-gray-500">Size</div>
                      <div className="mt-1 text-2xl font-semibold text-gray-800">
                        {formatFileSize(doc.size)}
                      </div>
                    </div>
                  </div>

                  {previewZones.length > 0 ? (
                    <div className="space-y-4">
                      {previewZones.map((zone, index) => (
                        <div
                          key={index}
                          className="bg-gray-50 rounded-lg p-4"
                        >
                          <div className="flex justify-between items-start mb-3">
                            <div className="text-sm font-medium text-gray-900">
                              {zone.sectionTitle || `Section ${index + 1}`}
                            </div>
                            <div className="text-xs px-2 py-1 bg-gray-200 rounded text-gray-600">
                              Page {zone.page} • Lines {zone.startLine}-{zone.endLine}
                            </div>
                          </div>
                          <div className="prose prose-sm max-w-none">
                            <p className="text-gray-600 leading-relaxed">
                              {formatPreviewText(zone.text)}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      No preview available for this document
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