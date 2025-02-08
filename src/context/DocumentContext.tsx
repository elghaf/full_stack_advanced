'use client'

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface Document {
  id: string;
  name: string;
  type: string;
  size: number;
  uploadedAt: number;
  pageCount: number;
  previewZones: any[];
  previewUrls: string[];
  sourceInfo?: {
    documentId: string;
    fileName: string;
    page: number;
    relevanceScore: number;
    text: string;
  }[];
}

export interface DocumentContextType {
  documents: Document[];
  activeDocument: Document | null;
  setDocuments: (documents: Document[]) => void;
  setActiveDocument: (document: Document | null) => void;
  addDocument: (document: Document) => void;
}

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export function DocumentProvider({ children }: { children: ReactNode }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeDocument, setActiveDocument] = useState<Document | null>(null);

  return (
    <DocumentContext.Provider value={{ documents, activeDocument, setDocuments, setActiveDocument }}>
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