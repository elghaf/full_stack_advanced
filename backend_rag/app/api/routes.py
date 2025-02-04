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

# Initialize processors
file_processor = FileProcessor()
rag_processor = RAGProcessor()

router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)

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

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        logger.info(f"Received chat message: {request.message}")
        logger.info(f"Document context: {request.documentId if request.documentId else 'all documents'}")
        
        if request.chatHistory:
            logger.info(f"Chat history length: {len(request.chatHistory)}")
        
        # Initialize RAG processor
        rag = RAGProcessor()
        
        # Get response from RAG
        response = rag.get_response(
            query=request.message,
            document_id=request.documentId
        )
        
        logger.info("Generated response successfully")
        
        return {
            "answer": response["answer"],
            "sources": response["sources"]
        }
        
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
        # Look for the document in uploads directory
        upload_dir = Path("uploads")
        logger.info(f"Looking for document {document_id} in {upload_dir}")
        
        # List all files in uploads directory
        all_files = list(upload_dir.glob("*"))
        logger.info(f"Files in uploads directory: {[f.name for f in all_files]}")
        
        # Look for any file with the document_id as prefix
        document_files = list(upload_dir.glob(f"{document_id}.*"))
        
        if not document_files:
            logger.error(f"No files found for document_id: {document_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {document_id}"
            )
            
        document_path = document_files[0]
        logger.info(f"Found document at {document_path}")
        
        if not document_path.exists():
            logger.error(f"File exists in glob but not on filesystem: {document_path}")
            raise HTTPException(
                status_code=404,
                detail="Document file not found on filesystem"
            )
            
        # Get file size
        file_size = document_path.stat().st_size
        logger.info(f"File size: {file_size} bytes")
        
        # Determine content type based on file extension
        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain'
        }
        content_type = content_types.get(document_path.suffix.lower(), 'application/octet-stream')
        
        # Get original filename from the path
        original_filename = document_path.name
        
        logger.info(f"Sending file: {original_filename} ({content_type})")
        
        return FileResponse(
            path=document_path,
            media_type=content_type,
            filename=original_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{original_filename}"',
                "Content-Type": content_type
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading document: {str(e)}"
        )

@router.post("/files")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Generate a unique document ID
        document_id = str(uuid.uuid4())
        
        # Create file path
        file_path = Path(rag_processor.upload_dir) / file.filename
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process the document with the document_id
        doc_info = rag_processor.process_document(
            file_path=file_path,
            filename=file.filename,
            document_id=document_id
        )
        
        return {
            "success": True,
            "document": {
                "id": doc_info["id"],
                "name": doc_info["filename"],
                "type": doc_info["file_type"],
                "size": doc_info["file_size"],
                "pageCount": doc_info["page_count"],
                "previewUrls": doc_info["preview_urls"],
                "uploadedAt": str(datetime.now().isoformat()),
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 