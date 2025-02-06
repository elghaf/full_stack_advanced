export interface ChatMessage {
    id: string;
    sender: "user" | "ai";
    content: string;
    timestamp: Date;
    source?: string;
  }