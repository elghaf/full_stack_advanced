from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DocumentPreview(BaseModel):
    id: str
    name: str
    type: str
    size: int
    uploadedAt: datetime
    pageCount: Optional[int] = 1
    previewUrls: List[str] = []

class UploadResponse(BaseModel):
    document: DocumentPreview
    success: bool

class Source(BaseModel):
    document_id: str
    file_name: str
    page: int
    text: str
    relevance_score: float
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    section_title: Optional[str] = None
    document_info: Optional[DocumentPreview] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]

class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None