export interface UploadedFile {
  id: string;
  name: string;
  type: "pdf" | "docx" | "txt";
  size: number;
  uploadedAt: number;
  pageCount: number;
  previewZones?: PreviewZone[];
  chunkCount?: number;
}

export interface PreviewZone {
  page: number;
  startLine: number;
  endLine: number;
  text: string;
  sectionTitle?: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  source?: string;
} 
