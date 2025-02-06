from pathlib import Path
import logging
from typing import Dict, Any, Tuple

from docx import Document  # This is from python-docx
import PyPDF2
from pdf2image import convert_from_path
import os
import shutil

logger = logging.getLogger(__name__)

class FileProcessor:
    def __init__(self):
        self.supported_extensions = ['.pdf', '.docx', '.txt']
        # Create directories if they don't exist
        self.upload_dir = Path("uploads")
        self.preview_dir = Path("previews")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.preview_dir.mkdir(parents=True, exist_ok=True)

    def process_file(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process uploaded file and generate previews if applicable"""
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            file_extension = file_path.suffix.lower()
            if file_extension not in self.supported_extensions:
                raise ValueError(f"Unsupported file type: {file_extension}")

            if file_extension == '.pdf':
                return self._process_pdf(file_path, document_id)
            elif file_extension == '.docx':
                return self._process_docx(file_path, document_id)
            else:  # .txt
                return self._process_txt(file_path, document_id)

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise

    def _process_pdf(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process PDF file and generate previews"""
        try:
            # Get page count
            with open(file_path, 'rb') as file:
                pdf = PyPDF2.PdfReader(file)
                page_count = len(pdf.pages)

            # Create document-specific preview directory
            preview_dir = self.preview_dir / document_id
            preview_dir.mkdir(parents=True, exist_ok=True)

            # Generate previews
            images = convert_from_path(
                str(file_path),
                dpi=72,
                size=(None, 800)
            )
            
            preview_urls = []
            for i, image in enumerate(images):
                preview_path = preview_dir / f"page_{i + 1}.png"
                image.save(str(preview_path), "PNG", optimize=True)
                preview_urls.append(f"/previews/{document_id}/page_{i + 1}.png")

            return {
                "page_count": page_count,
                "preview_urls": preview_urls
            }

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise

    def _process_docx(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process DOCX file"""
        try:
            doc = Document(file_path)
            return {
                "page_count": len(doc.sections),
                "preview_urls": []
            }
        except Exception as e:
            logger.error(f"Error processing DOCX: {str(e)}")
            raise

    def _process_txt(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process TXT file"""
        return {
            "page_count": 1,
            "preview_urls": []
        }

    def cleanup(self, document_id: str) -> None:
        """Clean up files associated with a document"""
        try:
            preview_dir = self.preview_dir / document_id
            if preview_dir.exists():
                for file in preview_dir.glob("*"):
                    file.unlink()
                preview_dir.rmdir()
            
            upload_file = self.upload_dir / document_id
            if upload_file.exists():
                upload_file.unlink()
                
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
            raise

    async def get_preview(self, document_id: str, page: int) -> Tuple[str, bytes]:
        """Get preview file content and type."""
        try:
            preview_dir = self.preview_dir / document_id
            
            # Find the preview file
            preview_files = list(preview_dir.glob(f"page_{page}.*"))
            if not preview_files:
                raise FileNotFoundError(f"Preview not found for document {document_id}, page {page}")

            preview_path = preview_files[0]
            
            # Determine content type
            content_type = {
                '.jpg': 'image/jpeg',
                '.png': 'image/png',
                '.txt': 'text/plain'
            }.get(preview_path.suffix, 'application/octet-stream')

            # Read the file content
            with open(preview_path, 'rb') as f:
                content = f.read()

            return content_type, content

        except Exception as e:
            print(f"Error getting preview: {e}")
            raise 