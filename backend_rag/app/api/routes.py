from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response, JSONResponse, FileResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from pathlib import Path
from pydantic import BaseModel
import os
import logging
import shutil

from utils.file_processing import FileProcessor
from utils.rag_processor import RAGProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Initialize processors
file_processor = FileProcessor()
rag_processor = RAGProcessor()

# Store uploaded files in a consistent location
UPLOAD_DIR = Path("uploads")
TEMP_DIR = Path("temp")
UPLOAD_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

class DocumentResponse(BaseModel):
    id: str
    name: str
    type: str
    size: int
    uploadedAt: str
    pageCount: int
    previewUrls: List[str]

class ChatMessage(BaseModel):
    sender: str
    content: str

class ChatRequest(BaseModel):
    message: str
    documentId: Optional[str] = None
    chatHistory: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@router.get("/previews/{document_id}/{page}")
async def get_preview(document_id: str, page: int):
    try:
        logger.info(f"Fetching preview for document {document_id}, page {page}")
        
        # Construct the preview path
        preview_path = Path("previews") / document_id / f"page_{page}.png"
        logger.info(f"Looking for preview at: {preview_path}")
        
        if not preview_path.exists():
            logger.error(f"Preview not found at: {preview_path}")
            raise HTTPException(
                status_code=404,
                detail=f"Preview not found for document {document_id}, page {page}"
            )
        
        return FileResponse(
            str(preview_path),
            media_type="image/png",
            filename=f"{document_id}_page_{page}.png"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving preview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error serving preview: {str(e)}"
        )

@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    try:
        # Get document info from the uploads directory
        upload_path = Path("uploads") / document_id
        preview_dir = Path("previews") / document_id
        
        if not preview_dir.exists():
            raise HTTPException(status_code=404, detail="Document not found")
            
        # Count preview pages
        preview_files = list(preview_dir.glob("page_*.png"))
        page_count = len(preview_files)
        
        return {
            "success": True,
            "document": {
                "id": document_id,
                "pageCount": page_count,
                "previewUrls": [f"/api/previews/{document_id}/{i+1}" for i in range(page_count)]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document: {str(e)}"
        )

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"Received chat message: {request.message}")
        logger.info(f"Document context: {request.documentId if request.documentId else 'all documents'}")
        
        if request.chatHistory:
            logger.info(f"Chat history length: {len(request.chatHistory)}")
        
        # Initialize RAG processor
        rag = RAGProcessor()
        
        # Get response from RAG using query parameter - properly await the async call
        answer, sources = await rag.get_response(
            query=request.message,
            document_id=request.documentId,
            chat_history=request.chatHistory
        )
        
        logger.info("Generated response successfully")
        
        return ChatResponse(answer=answer, sources=sources)
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    try:
        logger.info(f"Deleting document: {document_id}")
        
        # Check preview directory
        preview_dir = Path("previews") / document_id
        upload_file = Path("uploads") / document_id
        logger.info(f"Looking for preview directory: {preview_dir}")
        
        # Delete preview files if they exist
        if preview_dir.exists():
            try:
                for preview_file in preview_dir.glob("*"):
                    preview_file.unlink()
                preview_dir.rmdir()
                logger.info(f"Deleted preview directory: {preview_dir}")
            except Exception as e:
                logger.error(f"Error deleting preview files: {str(e)}", exc_info=True)

        # Delete uploaded file if it exists
        if upload_file.exists():
            try:
                upload_file.unlink()
                logger.info(f"Deleted uploaded file: {upload_file}")
            except Exception as e:
                logger.error(f"Error deleting uploaded file: {str(e)}", exc_info=True)
            
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Document {document_id} deleted successfully"
            }
        )
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error deleting document: {str(e)}"
            }
        )

@router.get("/documents/{document_id}/download")
async def download_document(document_id: str):
    try:
        logger.info(f"Download requested for document: {document_id}")
        
        # Search for the file with any extension
        files = list(UPLOAD_DIR.glob(f"{document_id}.*"))
        logger.info(f"Found files: {[f.name for f in files]}")
        
        if not files:
            logger.error(f"No files found for ID: {document_id}")
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        file_path = files[0]
        logger.info(f"Found file at: {file_path}")
        
        # Get original filename if available
        original_filename = file_path.name
        if (UPLOAD_DIR / "filenames.txt").exists():
            with open(UPLOAD_DIR / "filenames.txt", "r") as f:
                for line in f:
                    stored_name, orig_name = line.strip().split("|")
                    if stored_name == file_path.name:
                        original_filename = orig_name
                        break
        
        # Determine content type
        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain'
        }
        content_type = content_types.get(file_path.suffix.lower(), 'application/octet-stream')
        
        logger.info(f"Serving {file_path} as {content_type}")
        
        return FileResponse(
            path=file_path,
            media_type=content_type,
            filename=original_filename,
            headers={"Content-Disposition": f'attachment; filename="{original_filename}"'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/files")
async def upload_file(file: UploadFile = File(...)):
    try:
        document_id = str(uuid.uuid4())
        logger.info(f"Processing file upload with ID: {document_id}")
        
        # Validate file type
        allowed_types = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="File type not supported. Allowed types: PDF, TXT, DOCX"
            )
        
        # Save file with document ID as name
        file_extension = Path(file.filename).suffix.lower()
        save_path = UPLOAD_DIR / f"{document_id}{file_extension}"
        
        logger.info(f"Saving file to: {save_path}")
        
        # Save the file
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
            
        file_size = os.path.getsize(save_path)
        logger.info(f"File saved successfully. Size: {file_size} bytes")
        
        # Store the original filename mapping
        with open(UPLOAD_DIR / "filenames.txt", "a") as f:
            f.write(f"{document_id}{file_extension}|{file.filename}\n")
        
        # Process document with RAG
        try:
            doc_info = rag_processor.process_document(save_path, file.filename, document_id)
            logger.info(f"Document processed successfully: {doc_info}")
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            doc_info = {}
        
        return {
            "success": True,
            "document": {
                "id": document_id,
                "name": file.filename,
                "type": file.content_type,
                "size": file_size,
                "uploadedAt": datetime.now().isoformat(),
                "pageCount": doc_info.get("page_count", 1),
                "previewUrls": doc_info.get("preview_urls", [])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/debug/files")
async def list_files():
    """Debug endpoint to list all files"""
    try:
        files = list(UPLOAD_DIR.glob("*"))
        return {
            "upload_dir": str(UPLOAD_DIR),
            "files": [
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                }
                for f in files if f.is_file()
            ]
        }
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        ) 