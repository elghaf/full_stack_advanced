// src/services/chatService.ts
import apiClient from "./apiClient";

export interface ChatResponse {
  answer: string;
  sources: {
    document_id: string;
    page: number;
    text: string;
  }[];
}

export const sendMessage = async (
  message: string, 
  documentId?: string
): Promise<ChatResponse> => {
  const response = await apiClient.post("/chat", { 
    message,
    documentId 
  });
  return response.data;
};