'use client'

import { createContext, useContext, useState, ReactNode } from 'react';

interface Document {
  id: string;
  name: string;
  type: string;
  size: number;
  uploadedAt: string;
  pageCount: number;
  previewUrls: string[];
}

interface DocumentContextType {
  uploadedFiles: Document[];
  activeDocument: Document | null;
  addDocument: (document: Document) => void;
  setActiveDocument: (document: Document | null) => void;
  removeDocument: (documentId: string) => void;
}

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export function DocumentProvider({ children }: { children: ReactNode }) {
  const [uploadedFiles, setUploadedFiles] = useState<Document[]>([]);
  const [activeDocument, setActiveDocument] = useState<Document | null>(null);

  const addDocument = (document: Document) => {
    console.log('Adding document:', document); // Debug log
    setUploadedFiles(prev => {
      // Check if document already exists
      const exists = prev.some(file => file.id === document.id);
      if (exists) {
        return prev.map(file => 
          file.id === document.id ? document : file
        );
      }
      // Add new document at the beginning of the array
      return [document, ...prev];
    });
    setActiveDocument(document);
  };

  const removeDocument = (documentId: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== documentId));
    if (activeDocument?.id === documentId) {
      setActiveDocument(null);
    }
  };

  return (
    <DocumentContext.Provider value={{
      uploadedFiles,
      activeDocument,
      addDocument,
      setActiveDocument,
      removeDocument,
    }}>
      {children}
    </DocumentContext.Provider>
  );
}

export function useDocuments() {
  const context = useContext(DocumentContext);
  if (context === undefined) {
    throw new Error('useDocuments must be used within a DocumentProvider');
  }
  return context;
} 