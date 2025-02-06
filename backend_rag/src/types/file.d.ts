export interface UploadedFile {
    id: string;
    name: string;
    type: "pdf" | "docx" | "txt";
    size: string;
    uploadedAt: Date;
  }