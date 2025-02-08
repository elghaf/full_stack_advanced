'use client'

import { useState, useEffect, useCallback } from 'react';
import { UploadedFile } from '@/types/file';

export function useDocuments() {
  const [documents, setDocuments] = useState<UploadedFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    console.log('Fetching documents...');
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('Making fetch request to /api/documents');
      const response = await fetch('/api/documents');
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error('Error response:', errorData);
        throw new Error(errorData.detail || 'Failed to fetch documents');
      }
      
      const data = await response.json();
      console.log('Received documents:', data);
      
      setDocuments(data.documents || []);
      console.log('Documents state updated');
      
    } catch (error) {
      console.error('Error in fetchDocuments:', error);
      setError(error instanceof Error ? error.message : 'Failed to fetch documents');
    } finally {
      setIsLoading(false);
      console.log('Loading state set to false');
    }
  }, []);

  const deleteDocument = useCallback(async (documentId: string) => {
    try {
      const response = await fetch(`/api/documents/${documentId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete document');
      }
      
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));
    } catch (error) {
      console.error('Error deleting document:', error);
      throw error;
    }
  }, []);

  const downloadDocument = useCallback(async (documentId: string) => {
    try {
      const response = await fetch(`/api/documents/${documentId}/download`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to download document');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = documents.find(doc => doc.id === documentId)?.name || 'document';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading document:', error);
      throw error;
    }
  }, [documents]);

  useEffect(() => {
    console.log('useEffect triggered, calling fetchDocuments');
    fetchDocuments();
  }, [fetchDocuments]);

  return {
    documents,
    isLoading,
    error,
    deleteDocument,
    downloadDocument,
    refreshDocuments: fetchDocuments,
  };
} 