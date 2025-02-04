import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import os
from utils.rag_processor import RAGProcessor
from dotenv import load_dotenv
from datetime import datetime
import uuid
from app.api.routes import router
import logging

# Load environment variables
load_dotenv()

# Ensure temp directory exists
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(title="RAG API", version="1.0.0")

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Your Next.js frontend URL
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/files/")
    async def upload_file(file: UploadFile = File(...)):
        try:
            logger.info(f"Received file upload request: {file.filename}")
            logger.info(f"Content type: {file.content_type}")
            
            # Generate a unique document ID
            document_id = str(uuid.uuid4())
            
            # Create uploads directory if it doesn't exist
            upload_dir = Path("uploads")
            upload_dir.mkdir(exist_ok=True)
            
            # Save file with original extension
            original_extension = Path(file.filename).suffix
            upload_path = upload_dir / f"{document_id}{original_extension}"
            
            logger.info(f"Saving file to: {upload_path}")
            
            # Save uploaded file
            with upload_path.open("wb") as buffer:
                contents = await file.read()  # Read the file first
                buffer.write(contents)  # Then write it
            
            logger.info(f"File saved successfully at {upload_path}")
            
            # Process with RAG
            rag = RAGProcessor()
            doc_info = rag.process_document(
                file_path=upload_path,
                filename=file.filename,
                document_id=document_id
            )
            
            # Verify file exists after processing
            if not upload_path.exists():
                logger.error(f"File not found after processing: {upload_path}")
                raise HTTPException(
                    status_code=500,
                    detail="File was not saved correctly"
                )
            
            logger.info(f"File processed successfully. Size: {upload_path.stat().st_size} bytes")
            
            return {
                "success": True,
                "detail": "File processed successfully",
                "document": {
                    "id": document_id,
                    "name": file.filename,
                    "type": file.content_type,
                    "size": file.size,
                    "uploadedAt": str(datetime.now().isoformat()),
                    "pageCount": doc_info.get("page_count", 1),
                    "previewUrls": doc_info.get("preview_urls", []),
                    "vectorCount": doc_info.get("vector_count", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in file upload: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy"}

    # Include the router without additional prefix
    app.include_router(router)  # Removed prefix here since it's in the router

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 