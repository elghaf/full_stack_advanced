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
import json
import PyPDF2

from utils.file_processing import FileProcessor
from utils.rag_app_weav import RAGProcessor
from app.models import Source

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
    sources: List[Source]

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
    """Chat with the RAG system"""
    try:
        logger.info(f"Received chat request: {request.message}")
        
        # Initialize RAG processor
        rag_processor = RAGProcessor()
        
        # Get response
        answer, sources = rag_processor.get_response(
            query=request.message,
            document_id=request.documentId
        )
        
        logger.info("Generated response successfully")
        
        # Convert sources to match the Source model
        formatted_sources = [
            Source(
                document_id=source["document_id"],
                service_name=source["service_name"],
                description=source["description"],
                url=source["url"],
                relevance_score=source["relevance_score"],
                file_name=source["file_name"],
                page=source["page"],
                start_line=source.get("start_line"),
                end_line=source.get("end_line"),
                text=source.get("description", "")  # Use description as text or empty string
            ) for source in sources
        ]
        
        return ChatResponse(answer=answer, sources=formatted_sources)
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
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
    """Upload and process a document"""
    try:
        # Generate unique ID for the document
        document_id = str(uuid.uuid4())
        
        # Create uploads directory if it doesn't exist
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)
        
        # Save file with original extension
        file_extension = Path(file.filename).suffix
        file_path = uploads_dir / f"{document_id}{file_extension}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Initialize RAG processor and process document
        process_result = rag_processor.process_document(file_path, document_id)
        
        # Get file stats
        stats = file_path.stat()
        
        return {
            "success": True,
            "document": {
                "id": document_id,
                "name": file.filename,
                "type": file.content_type,
                "size": stats.st_size,
                "uploadedAt": stats.st_mtime,
                "pageCount": process_result.get("page_count", 1),
                "previewZones": process_result.get("preview_zones", []),
                "chunkCount": process_result.get("chunk_count", 0)
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
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

@router.get("/documents/{document_id}/preview")
async def get_document_preview(document_id: str):
    """Get preview zones for a document"""
    try:
        # Try to load saved preview
        preview_file = Path(f"uploads/{document_id}_preview.json")
        if preview_file.exists():
            with open(preview_file, 'r', encoding='utf-8') as f:
                preview_data = json.load(f)
                return preview_data
        
        # If no preview exists, return empty zones
        return {
            "zones": [],
            "error": "No preview available for this document"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document preview: {str(e)}"
        )

@router.get("/documents")
async def list_documents():
    """List all documents"""
    try:
        print("GET /api/documents - Starting request")
        uploads_dir = Path("uploads")
        
        if not uploads_dir.exists():
            print(f"Uploads directory does not exist: {uploads_dir}")
            return {"documents": []}

        documents = []
        print(f"Scanning directory: {uploads_dir}")
        
        for file_path in uploads_dir.glob("*"):
            print(f"Found file: {file_path}")
            
            # Skip preview JSON files and non-files
            if not file_path.is_file() or file_path.suffix == '.json':
                print(f"Skipping file: {file_path}")
                continue
                
            try:
                # Get file stats
                stats = file_path.stat()
                print(f"File stats for {file_path.name}: size={stats.st_size}, mtime={stats.st_mtime}")
                
                # Get preview data if exists
                preview_file = Path(f"uploads/{file_path.stem}_preview.json")
                preview_data = None
                if preview_file.exists():
                    print(f"Found preview file: {preview_file}")
                    with open(preview_file, 'r', encoding='utf-8') as f:
                        preview_data = json.load(f)
                else:
                    print(f"No preview file found for: {file_path.name}")

                # Create document info
                doc_info = {
                    "id": file_path.stem,
                    "name": file_path.name,
                    "type": file_path.suffix.lower()[1:],
                    "size": stats.st_size,
                    "uploadedAt": stats.st_mtime,
                    "pageCount": 1,
                    "previewZones": preview_data.get("zones", []) if preview_data else []
                }
                
                print(f"Created doc_info for {file_path.name}: {doc_info}")
                
                # Get page count for PDFs
                if file_path.suffix.lower() == '.pdf':
                    try:
                        with open(file_path, 'rb') as pdf_file:
                            pdf_reader = PyPDF2.PdfReader(pdf_file)
                            doc_info["pageCount"] = len(pdf_reader.pages)
                            print(f"PDF page count for {file_path.name}: {doc_info['pageCount']}")
                    except Exception as e:
                        print(f"Error reading PDF page count for {file_path.name}: {str(e)}")

                documents.append(doc_info)
                
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")
                continue

        # Sort by upload time, newest first
        documents.sort(key=lambda x: x["uploadedAt"], reverse=True)
        
        print(f"Returning {len(documents)} documents")
        return {"documents": documents}

    except Exception as e:
        print(f"Error in list_documents: {str(e)}")
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        ) 