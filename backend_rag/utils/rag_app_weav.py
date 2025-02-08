from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_weaviate import WeaviateVectorStore
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
import weaviate
from weaviate.classes import config as wvc
from weaviate.classes.init import Auth
import os
from dotenv import load_dotenv
import logging
import atexit
from pdf2image import convert_from_path
import PyPDF2
from sentence_transformers import SentenceTransformer
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from weaviate.auth import AuthApiKey
from langchain.schema import Document
import json
from langchain_core.messages import SystemMessage, HumanMessage
from datetime import datetime
import mimetypes

from weaviate.classes.query import Filter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RAGProcessor:
    def __init__(self):
        """Initialize RAG application"""
        self.supported_extensions = ['.pdf', '.docx', '.txt']
        # Create directories if they don't exist
        self.upload_dir = Path("uploads")
        self.preview_dir = Path("previews")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.preview_dir.mkdir(parents=True, exist_ok=True)

        # Get credentials from environment variables
        self.cluster_url = os.getenv("WCD_URL")
        self.api_key = os.getenv("WCD_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.collection_name = "DocumentChunks"

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize RAG components if credentials are available
        if all([self.cluster_url, self.api_key, self.openai_api_key]):
            self._initialize_rag_components()
            
        logger.info(f"RAGProcessor initialized with upload_dir: {self.upload_dir}, preview_dir: {self.preview_dir}")

    def _initialize_rag_components(self):
        """Initialize RAG-specific components"""
        try:
            self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)
            
            # Initialize Weaviate client
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.cluster_url,
                auth_credentials=Auth.api_key(self.api_key),
                headers={'X-OpenAI-Api-Key': self.openai_api_key}
            )
            
            # Initialize or get collection
            self._initialize_collection()
            
            # Initialize vector store
            self.vectorstore = WeaviateVectorStore(
                client=self.client,
                index_name=self.collection_name,
                text_key="text",
                embedding=self.embeddings,
            )
            
            # Register cleanup
            atexit.register(self.cleanup)
            
            logger.info("Successfully initialized RAG components")
        except Exception as e:
            logger.error(f"Failed to initialize RAG components: {str(e)}")
            raise

    def _initialize_collection(self) -> None:
        """Initialize or get the Weaviate collection."""
        try:
            if self.client.collections.exists(self.collection_name):
                self.collection = self.client.collections.get(self.collection_name)
                logger.info(f"Using existing collection: {self.collection_name}")
            else:
                # Create new collection with properties
                self.collection = self.client.collections.create(
                    name=self.collection_name,
                    vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(),
                    generative_config=wvc.Configure.Generative.openai(),
                    properties=[
                        wvc.Property(name="text", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="document_id", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="page", data_type=wvc.DataType.INT),
                        wvc.Property(name="start_line", data_type=wvc.DataType.INT),
                        wvc.Property(name="end_line", data_type=wvc.DataType.INT),
                        wvc.Property(name="section_title", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="file_name", data_type=wvc.DataType.TEXT),
                    ]
                )
                logger.info(f"Created new collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise

    def _store_chunk(self, text: str, document_id: str, page: int, start_line: int, end_line: int, section_title: str, file_name: str):
        """Store a chunk in the vector store with metadata"""
        try:
            # Create object in Weaviate using the new API
            self.collection.data.insert({
                "text": text,
                "document_id": document_id,
                "page": page,
                "start_line": start_line,
                "end_line": end_line,
                "section_title": section_title,
                "file_name": file_name
            })
            
            logger.info(f"Stored chunk for {file_name} (page {page}, lines {start_line}-{end_line})")
        except Exception as e:
            logger.error(f"Error storing chunk: {str(e)}")
            raise

    def process_document(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process document and add to vector store"""
        try:
            logger.info(f"Processing document: {file_path}")
            preview_zones = []
            total_pages = 1
            file_name = file_path.name
            
            # Process PDF files
            if file_path.suffix.lower() == '.pdf':
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    total_pages = len(pdf_reader.pages)
                    
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        text = page.extract_text()
                        if text:
                            lines = text.split('\n')
                            current_section = "Main Content"
                            section_text = []
                            start_line = 1
                            
                            for line_num, line in enumerate(lines, 1):
                                if line.strip() and (line.isupper() or line.strip().endswith(':')):
                                    # Save previous section
                                    if section_text:
                                        section_content = '\n'.join(section_text)
                                        preview_zones.append({
                                            "page": page_num,
                                            "startLine": start_line,
                                            "endLine": line_num - 1,
                                            "text": section_content,
                                            "sectionTitle": current_section
                                        })
                                        
                                        # Store in vector store
                                        self._store_chunk(
                                            text=section_content,
                                            document_id=document_id,
                                            page=page_num,
                                            start_line=start_line,
                                            end_line=line_num - 1,
                                            section_title=current_section,
                                            file_name=file_name
                                        )
                                    
                                    current_section = line.strip()
                                    section_text = []
                                    start_line = line_num
                                else:
                                    section_text.append(line)
                            
                            # Add final section
                            if section_text:
                                section_content = '\n'.join(section_text)
                                preview_zones.append({
                                    "page": page_num,
                                    "startLine": start_line,
                                    "endLine": len(lines),
                                    "text": section_content,
                                    "sectionTitle": current_section
                                })
                                
                                # Store in vector store
                                self._store_chunk(
                                    text=section_content,
                                    document_id=document_id,
                                    page=page_num,
                                    start_line=start_line,
                                    end_line=len(lines),
                                    section_title=current_section,
                                    file_name=file_name
                                )
            
            else:
                # Handle other file types (txt, docx)
                if file_path.suffix.lower() == '.docx':
                    loader = Docx2txtLoader(str(file_path))
                else:
                    loader = TextLoader(str(file_path))
                    
                documents = loader.load()
                text = documents[0].page_content
                
                # Create single preview zone for non-PDF files
                preview_zones.append({
                    "page": 1,
                    "startLine": 1,
                    "endLine": text.count('\n') + 1,
                    "text": text[:1000],
                    "sectionTitle": "Main Content"
                })
                
                # Add to vector store
                chunk = Document(
                    page_content=text,
                    metadata={
                        "document_id": document_id,
                        "page": 1,
                        "total_pages": 1,
                        "content_preview": text[:300],
                        "sections": ["Main Content"]
                    }
                )
                self.vectorstore.add_texts(
                    texts=[chunk.page_content],
                    metadatas=[chunk.metadata]
                )

            # Save preview zones to file for later retrieval
            preview_file = Path(f"uploads/{document_id}_preview.json")
            with open(preview_file, 'w', encoding='utf-8') as f:
                json.dump({"zones": preview_zones}, f, ensure_ascii=False, indent=2)

            return {
                "status": "success",
                "document_id": document_id,
                "file_name": file_name,
                "page_count": total_pages,
                "preview_zones": preview_zones,
                "chunk_count": len(preview_zones)
            }

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    def get_response(self, query: str, document_id: Optional[str] = None, chat_history: Optional[List[Dict]] = None) -> Tuple[str, List[Dict]]:
        """Get response for a query using the RAG system"""
        try:
            # Initialize LLM
            llm = ChatOpenAI(
                temperature=0.7,
                model_name="gpt-3.5-turbo",
                openai_api_key=self.openai_api_key
            )

            # Get relevant documents first
            docs = self.vectorstore.similarity_search_with_score(query=query, k=5)
            
            if not docs:
                return "I don't see any documents in the system. Please upload some documents first.", []

            # Process sources with proper document info
            sources = []
            context_texts = []
            
            for doc, score in docs:
                # Get metadata
                metadata = doc.metadata
                doc_id = str(metadata.get("document_id", ""))
                
                try:
                    # Get file info from uploads directory
                    file_path = next(Path("uploads").glob(f"{doc_id}.*"))
                    file_stats = file_path.stat()
                    
                    # Create document info
                    document_info = {
                        "id": doc_id,
                        "name": file_path.name,
                        "type": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
                        "size": file_stats.st_size,
                        "uploadedAt": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                        "pageCount": metadata.get("page_count", 1),
                        "previewUrls": []
                    }

                    # Create source info
                    source_info = {
                        "document_id": doc_id,
                        "file_name": file_path.name,
                        "page": metadata.get("page", 1),
                        "text": doc.page_content,
                        "relevance_score": round(float(1 - (score or 0)), 3),
                        "start_line": metadata.get("start_line"),
                        "end_line": metadata.get("end_line"),
                        "section_title": metadata.get("section_title", "Main Content"),
                        "document_info": document_info
                    }
                    
                    # Add to context
                    context_texts.append(f"From {file_path.name} (Page {metadata.get('page', 1)}):\n{doc.page_content}\n")
                    sources.append(source_info)
                    
                    logger.info(f"Processed source from {file_path.name}")
                    
                except StopIteration:
                    logger.warning(f"Could not find file for document ID: {doc_id}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing document {doc_id}: {str(e)}")
                    continue

            if not sources:
                return "Could not find relevant information in the documents.", []

            # Create full context
            full_context = "\n\n".join(context_texts)
            
            # Create messages
            messages = [
                SystemMessage(content="""You are a helpful AI assistant that provides accurate information based on the documents provided. 
                When answering:
                1. Use only the information from the provided documents
                2. If you don't have enough information, say so clearly
                3. Cite specific documents and sections when providing information
                4. Maintain the original meaning and context"""),
                HumanMessage(content=f"Context:\n{full_context}\n\nQuestion: {query}")
            ]

            # Get response
            chat_response = llm(messages)
            
            # Log for debugging
            logger.info(f"Query: {query}")
            logger.info(f"Number of sources found: {len(sources)}")
            logger.info(f"Sources: {[s['file_name'] for s in sources]}")
            
            return chat_response.content, sources

        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}", exc_info=True)
            raise

    def cleanup(self) -> None:
        """Cleanup resources."""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Weaviate client closed successfully.")