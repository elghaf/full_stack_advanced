'use client'

import FileUpload from './FileUpload';
import DocumentList from './DocumentList';
import { DocumentProvider } from '@/context/DocumentContext';

const ClientWrapper = () => {
  return (
    <DocumentProvider>
      <div className="container mx-auto">
        <FileUpload />
        <DocumentList />
      </div>
    </DocumentProvider>
  );
};

export default ClientWrapper; 