export interface DocumentInfo {
  id: string;
  name: string;
  type: string;
  size: number;
  uploadedAt: string;
  pageCount: number;
  previewUrls: string[];
}

export interface Source {
  document_id: string;
  file_name: string;
  page: number;
  text: string;
  relevance_score: number;
  start_line?: number;
  end_line?: number;
  section_title?: string;
  document_info?: DocumentInfo;
}

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp?: string;
  sources?: {
    documentId: string;
    fileName: string;
    page: number;
    relevanceScore: number;
    text: string;
  }[];
} 