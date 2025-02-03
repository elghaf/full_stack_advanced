from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from pathlib import Path
from pydantic import BaseModel

from utils.file_processing import FileProcessor
from utils.rag_processor import RAGProcessor

# Initialize processors
file_processor = FileProcessor()
rag_processor = RAGProcessor()

router = APIRouter()

class DocumentResponse(BaseModel):
    id: str
    name: str
    type: str
    size: int
    uploadedAt: str
    pageCount: int
    previewUrls: List[str]

class ChatMessage(BaseModel):
    message: str
    document_id: Optional[str] = None
    chat_history: Optional[List[Dict[str, Any]]] = None

@router.post("/files/", response_model=DocumentResponse)
async def upload_file(file: UploadFile = File(...)):
    try:
        # Validate file type
        valid_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        ]
        
        if file.content_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF, DOCX, and TXT files are allowed."
            )

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        unique_filename = f"{file_id}{file_extension}"
        file_path = file_processor.upload_dir / unique_filename

        # Save the file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            file_size = len(content)

        # Process the file based on its type
        if file.content_type == "application/pdf":
            page_count, preview_urls = await file_processor.process_pdf(file_path)
        elif file.content_type.endswith("document"):
            page_count, preview_urls = await file_processor.process_docx(file_path)
        else:  # text/plain
            page_count, preview_urls = await file_processor.process_text(file_path)

        # Process file for RAG
        await rag_processor.process_document(file_path, file_id)

        return DocumentResponse(
            id=file_id,
            name=file.filename,
            type=file.content_type,
            size=file_size,
            uploadedAt=datetime.now().isoformat(),
            pageCount=page_count,
            previewUrls=preview_urls
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/previews/{document_id}/{page}")
async def get_preview(document_id: str, page: int):
    try:
        content_type, content = await file_processor.get_preview(document_id, page)
        return Response(content=content, media_type=content_type)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Preview not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/")
async def chat(message: ChatMessage):
    try:
        response = await rag_processor.get_response(
            query=message.message,
            document_id=message.document_id,
            chat_history=message.chat_history
        )

        return {
            "id": str(uuid.uuid4()),
            "content": response["answer"],
            "timestamp": datetime.now().isoformat(),
            "sources": response["sources"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 