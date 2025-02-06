'use client'

import { useDocuments } from '@/context/DocumentContext';
import DocumentPreview from './DocumentPreview';

const DocumentList = () => {
  const { documents } = useDocuments();

  if (!documents || documents.length === 0) {
    return (
      <div className="text-center py-10 text-gray-500">
        No documents uploaded yet
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
      {documents.map((doc) => (
        <DocumentPreview
          key={doc.id}
          filename={doc.filename}
          fileSize={doc.file_size}
          previewUrls={doc.preview_urls}
          onViewAll={() => {/* implement view all */}}
          onDelete={() => {/* implement delete */}}
          onDownload={() => {/* implement download */}}
        />
      ))}
    </div>
  );
};

export default DocumentList; 