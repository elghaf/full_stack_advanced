'use client'

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUpload } from 'react-icons/fi';

interface FileUploadProps {
  onUploadSuccess?: () => void;
  onUploadError?: (error: string) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ 
  onUploadSuccess, 
  onUploadError 
}) => {
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', acceptedFiles[0]);

    try {
      const response = await fetch('/api/files', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.details || 'Upload failed');
      }

      const data = await response.json();
      console.log('Upload successful:', data);
      onUploadSuccess?.();
    } catch (error) {
      console.error('Upload error:', error);
      onUploadError?.(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [onUploadSuccess, onUploadError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    multiple: false
  });

  return (
    <div
      {...getRootProps()}
      className={`p-10 border-2 border-dashed rounded-lg text-center cursor-pointer
        ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
        ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <input {...getInputProps()} disabled={uploading} />
      <FiUpload className="mx-auto h-12 w-12 text-gray-400" />
      <p className="mt-2 text-sm text-gray-600">
        {uploading ? 'Uploading...' : 
          isDragActive ? 'Drop the file here...' : 
          'Drag & drop a file here, or click to select'}
      </p>
      <p className="mt-1 text-xs text-gray-500">
        Supported files: PDF, TXT, DOCX
      </p>
    </div>
  );
};