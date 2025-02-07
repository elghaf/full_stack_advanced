'use client'

import {FileUpload} from './documents/FileUpload';
import DocumentList from './documents/DocumentList';
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