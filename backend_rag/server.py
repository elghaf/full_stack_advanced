import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import os
from utils.rag_processor import RAGProcessor
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Ensure temp directory exists
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

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

    @app.post("/api/files/")
    async def upload_file(file: UploadFile = File(...)):
        try:
            # Create temp file path
            temp_file_path = TEMP_DIR / file.filename
            
            # Save uploaded file
            with temp_file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Process with RAG
            rag = RAGProcessor()
            doc_info = rag.process_document(temp_file_path, file.filename)
            
            # Clean up temp file
            os.remove(temp_file_path)
            
            # Return document information
            return {
                "success": True,
                "detail": "File processed successfully",
                "document": {
                    "id": str(doc_info.get("id", "")),
                    "filename": file.filename,
                    "type": file.content_type,
                    "size": file.size,
                    "uploadedAt": str(datetime.now().isoformat()),
                    "pageCount": doc_info.get("page_count", 1),
                    "previewUrls": doc_info.get("preview_urls", []),
                    "vectorCount": doc_info.get("vector_count", 0)
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy"}

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        workers=4,
        log_level="info"
    ) 