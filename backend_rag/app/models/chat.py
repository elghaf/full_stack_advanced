from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ChatMessageRequest(BaseModel):
    content: Optional[str] = None
    sender: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    documentId: Optional[str] = None
    chatHistory: Optional[List[ChatMessageRequest]] = None

class Source(BaseModel):
    document_id: str
    page: int
    text: str

class ChatResponse(BaseModel):
    answer: str
    sources: Optional[List[Source]] = None 