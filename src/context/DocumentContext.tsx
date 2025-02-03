'use client'

import React, { createContext, useContext, useState } from 'react';
import { UploadedFile } from '@/types/file';
import { ChatMessage } from '@/types/chat';

interface DocumentContextType {
  uploadedFiles: UploadedFile[];
  activeDocument: UploadedFile | null;
  chatHistory: ChatMessage[];
  addFile: (file: UploadedFile) => void;
  setActiveDocument: (file: UploadedFile | null) => void;
  addMessage: (message: ChatMessage) => void;
}

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export function DocumentProvider({ children }: { children: React.ReactNode }) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [activeDocument, setActiveDocument] = useState<UploadedFile | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);

  const addFile = (file: UploadedFile) => {
    setUploadedFiles(prev => [...prev, file]);
  };

  const addMessage = (message: ChatMessage) => {
    setChatHistory(prev => [...prev, message]);
  };

  return (
    <DocumentContext.Provider
      value={{
        uploadedFiles,
        activeDocument,
        chatHistory,
        addFile,
        setActiveDocument,
        addMessage,
      }}
    >
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