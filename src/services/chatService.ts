// src/services/chatService.ts
import apiClient from "./apiClient";

export const sendMessage = async (message: string): Promise<string> => {
  const response = await apiClient.post("/chat", { message });
  return response.data.response;
};