export interface DocumentAnalysis {
  summary: string;
  keyPoints: string[];
  pageCount: number;
  metadata: {
    title?: string;
    author?: string;
    creationDate?: string;
  };
}

export async function analyzeDocument(documentId: string): Promise<DocumentAnalysis> {
  const response = await fetch(`/api/documents/${documentId}/analyze`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Failed to analyze document');
  }

  return response.json();
}

export async function getDocumentContent(documentId: string): Promise<string> {
  const response = await fetch(`/api/documents/${documentId}/content`, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new Error('Failed to get document content');
  }

  return response.json();
}
