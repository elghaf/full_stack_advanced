'use client'

import React, { useCallback, useState } from 'react';
import { useDocuments } from '@/context/DocumentContext';
import { FiUploadCloud } from 'react-icons/fi';

export const FileUpload = () => {
  const { addDocument } = useDocuments();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async (files: FileList) => {
    if (isUploading) return;

    try {
      setIsUploading(true);
      
      for (const file of Array.from(files)) {
        // Validate file size
        if (file.size > 10 * 1024 * 1024) {
          throw new Error('File size must be less than 10MB');
        }

        // Validate file type
        const allowedTypes = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        if (!allowedTypes.includes(file.type)) {
          throw new Error('File type not supported. Please upload PDF, TXT, or DOCX files.');
        }

        const formData = new FormData();
        formData.append('file', file);

        console.log('Uploading file:', {
          name: file.name,
          type: file.type,
          size: file.size
        });

        const response = await fetch('/api/files', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();
        console.log('Response data:', data);

        if (!response.ok || !data.success) {
          throw new Error(data.error || data.detail || 'Upload failed');
        }

        if (!data.document) {
          throw new Error('Invalid response from server');
        }

        // Add the document to context
        addDocument({
          id: data.document.id,
          name: data.document.name,
          type: data.document.type,
          size: data.document.size,
          uploadedAt: data.document.uploadedAt,
          pageCount: data.document.pageCount || 1,
          previewUrls: data.document.previewUrls || [],
          previewZones: data.document.previewZones || [],
          sourceInfo: data.document.sourceInfo || []
        });
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert(error instanceof Error ? error.message : 'Failed to upload file');
    } finally {
      setIsUploading(false);
      setIsDragging(false);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    handleUpload(files);
  }, [handleUpload]);

  return (
    <div className="p-6">
      <div
        className={`w-full border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
          isDragging ? 'border-custom bg-custom/5' : 'border-gray-300 hover:border-custom'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="fileInput"
          className="hidden"
          onChange={(e) => e.target.files && handleUpload(e.target.files)}
          accept=".pdf,.docx,.txt"
          multiple
        />
        <div className="mx-auto flex justify-center">
          <FiUploadCloud className={`w-12 h-12 ${isUploading ? 'text-custom animate-pulse' : 'text-gray-400'}`} />
        </div>
        <p className="mt-4 text-sm text-gray-600">
          {isUploading ? 'Uploading...' : 'Drag and drop your files here, or'}
        </p>
        <label
          htmlFor="fileInput"
          className="mt-2 cursor-pointer inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-custom hover:bg-custom/90 disabled:opacity-50"
        >
          Browse Files
        </label>
        <p className="mt-2 text-xs text-gray-500">PDF, DOCX, TXT up to 10MB</p>
      </div>
    </div>
  );
};