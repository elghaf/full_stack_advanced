from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
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
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
import weaviate.classes.query as weaviate_query




# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RAGProcessor:
    def __init__(self):
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

        # Initialize text splitter with smaller chunks for better retrieval
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20)
        
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
            
            # Initialize vector store with more attributes
            self.vectorstore = WeaviateVectorStore(
                client=self.client,
                index_name=self.collection_name,
                text_key="text",
                embedding=self.embeddings,
                attributes=[
                    "document_id",
                    "page",
                    "start_line",
                    "end_line",
                    "content_preview",
                    "section_title"
                ]
            )
            
            # Initialize conversation memory
            self.memory = ConversationBufferMemory(
                memory_key='chat_history',
                return_messages=True
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
                        wvc.Property(name="content_preview", data_type=wvc.DataType.TEXT),
                    ],
                )
                logger.info(f"Created new collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise

    def process_document(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process document and add to vector store"""
        try:
            logger.info(f"Processing document: {file_path} (ID: {document_id})")
            
            # Load and split document based on type
            if file_path.suffix.lower() == '.pdf':
                loader = PyPDFLoader(str(file_path))
            elif file_path.suffix.lower() == '.docx':
                loader = Docx2txtLoader(str(file_path))
            elif file_path.suffix.lower() == '.txt':
                loader = TextLoader(str(file_path))
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")

            # Load document
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} pages from document")

            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Split into {len(chunks)} chunks")

            # Process chunks with metadata
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "document_id": document_id,
                    "page": i + 1,
                    "content_preview": chunk.page_content[:200].replace('\n', ' ').strip(),
                    "title": file_path.name
                })
                processed_chunks.append(chunk)

            # Add to vector store
            text_meta_pairs = [(doc.page_content, doc.metadata) for doc in processed_chunks]
            texts, meta = list(zip(*text_meta_pairs))
            
            logger.info(f"Adding {len(texts)} chunks to vector store")
            self.vectorstore.add_texts(texts=texts, metadatas=list(meta))
            logger.info("Successfully added to vector store")

            return {
                "status": "success",
                "document_id": document_id,
                "page_count": len(documents),
                "chunk_count": len(chunks)
            }

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            raise

    def process_uploaded_file(self, file_content: bytes, filename: str, document_id: str) -> Dict[str, Any]:
        """Process an uploaded file"""
        try:
            logger.info(f"Processing uploaded file: {filename} (ID: {document_id})")
            
            # Create document directories
            doc_upload_dir = self.upload_dir / document_id
            doc_preview_dir = self.preview_dir / document_id
            doc_upload_dir.mkdir(parents=True, exist_ok=True)
            doc_preview_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file
            file_path = doc_upload_dir / filename
            with open(file_path, 'wb') as f:
                f.write(file_content)
            logger.info(f"File saved to: {file_path}")
            
            # Process for RAG
            processing_result = self.process_document(file_path, document_id)
            logger.info(f"Document processing result: {processing_result}")
            
            # Generate previews for PDF
            preview_urls = []
            if file_path.suffix.lower() == '.pdf':
                preview_urls = self._generate_pdf_previews(file_path, doc_preview_dir, document_id)
            
            return {
                "id": document_id,
                "name": filename,
                "type": file_path.suffix.lower(),
                "size": os.path.getsize(file_path),
                "uploadedAt": datetime.now().isoformat(),
                "pageCount": processing_result.get("page_count", 1),
                "previewUrls": preview_urls,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error processing uploaded file: {str(e)}", exc_info=True)
            self.cleanup_document(document_id)  # Cleanup on failure
            raise

    def _generate_pdf_previews(self, pdf_path: Path, preview_dir: Path, document_id: str) -> List[str]:
        """Generate preview images for PDF files"""
        try:
            preview_urls = []
            images = convert_from_path(str(pdf_path), dpi=72, size=(800, None))
            
            for i, image in enumerate(images, 1):
                preview_path = preview_dir / f"page_{i}.png"
                image.save(str(preview_path), "PNG", optimize=True)
                preview_urls.append(f"/api/previews/{document_id}/{i}")
            
            return preview_urls

        except Exception as e:
            logger.error(f"Error generating PDF previews: {str(e)}")
            raise

    def get_response(self, query: str, document_id: Optional[str] = None, chat_history: Optional[List[Dict]] = None) -> Tuple[str, List[Dict]]:
        try:
            # Initialize LLM
            llm = ChatOpenAI(
                temperature=0.7,
                model_name="gpt-3.5-turbo",
                openai_api_key=self.openai_api_key
            )

            # Initialize memory
            memory = ConversationBufferMemory(
                memory_key='chat_history',
                return_messages=True
            )

            # Create conversation chain
            conversation_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                memory=memory
            )

            # Get response
            result = conversation_chain({"question": query})
            
            # Get relevant documents
            docs = self.vectorstore.similarity_search_with_score(
                query=query,
                k=5
            )

            # Process sources with clean text
            sources = []
            for doc, score in docs:
                source_info = {
                    "document_id": str(doc.metadata.get("document_id", "")),
                    "page": int(doc.metadata.get("page", 1)),
                    "text": doc.metadata.get("content_preview", "").replace('\n', ' ').strip(),
                    "relevance_score": float(score)
                }
                sources.append(source_info)

            return result["answer"], sources

        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}", exc_info=True)
            raise

    def cleanup(self) -> None:
        """Cleanup resources."""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Weaviate client closed successfully.")