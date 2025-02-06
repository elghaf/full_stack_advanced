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

from weaviate.classes.query import Filter

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

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        
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
                self.collection = self.client.collections.create(
                    name=self.collection_name,
                    vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(),
                    generative_config=wvc.Configure.Generative.openai(),
                    properties=[
                        wvc.Property(name="text", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="document_id", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="page", data_type=wvc.DataType.INT),
                    ],
                )
                logger.info(f"Created new collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise

    def process_document(self, file_path: Path, filename: str, document_id: str) -> Dict[str, Any]:
        """Process a document and prepare it for RAG operations."""
        try:
            logger.info(f"Processing document: {filename} with ID: {document_id}")

            # Validate file exists
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Validate file extension
            file_extension = Path(filename).suffix.lower()
            if file_extension not in self.supported_extensions:
                raise ValueError(f"Unsupported file type: {file_extension}")

            # Process based on file type
            if file_extension == '.pdf':
                doc_info = self.process_pdf(file_path, document_id)
            elif file_extension == '.docx':
                doc_info = self._process_docx(file_path, document_id)
            else:  # .txt
                doc_info = self._process_txt(file_path, document_id)

            # Add basic document info
            doc_info.update({
                "id": document_id,
                "filename": filename,
                "file_type": file_extension,
                "file_size": os.path.getsize(file_path)
            })

            logger.info(f"Document processed successfully: {doc_info}")
            return doc_info
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "id": document_id,
                "filename": filename,
                "page_count": 0,
                "preview_urls": [],
                "vector_count": 0
            }

    def process_pdf(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process PDF document and prepare it for RAG operations"""
        try:
            logger.info(f"Processing PDF: {file_path}")

            # Extract text from PDF
            loader = PyPDFLoader(str(file_path))
            pages = loader.load()
            
            # Split text into chunks
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20)
            chunks = text_splitter.split_documents(pages)

            # Initialize OpenAI embeddings
            embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)

            # Connect to Weaviate
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.cluster_url,
                auth_credentials=AuthApiKey(api_key=self.api_key),
                headers={'X-OpenAI-Api-Key': self.openai_api_key}
            )

            # Initialize vector store
            vectorstore = WeaviateVectorStore(
                client=client,
                index_name=self.collection_name,
                text_key="text",
                embedding=embeddings,
            )

            # Add text chunks to vector store
            text_meta_pair = [(chunk.page_content, {"document_id": document_id}) for chunk in chunks]
            texts, meta = list(zip(*text_meta_pair))
            vectorstore.add_texts(texts, meta)

            logger.info(f"Successfully processed and stored PDF: {file_path}")

            return {
                "status": "success",
                "document_id": document_id,
                "chunk_count": len(chunks)
            }

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "document_id": document_id
            }

    def _process_docx(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process DOCX document."""
        try:
            loader = Docx2txtLoader(str(file_path))
            pages = loader.load_and_split()
            chunks = self.text_splitter.split_documents(pages)

            if hasattr(self, 'vectorstore'):
                self.vectorstore.add_documents(chunks)
                vector_count = len(chunks)
            else:
                vector_count = 0

            return {
                "page_count": len(pages),
                "preview_urls": [],  # DOCX doesn't support previews in this implementation
                "vector_count": vector_count
            }
        except Exception as e:
            logger.error(f"Error processing DOCX: {str(e)}")
            return {
                "page_count": 0,
                "preview_urls": [],
                "vector_count": 0
            }

    def _process_txt(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process TXT document."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Split text into chunks
            chunks = self.text_splitter.split_text(content)

            if hasattr(self, 'vectorstore'):
                self.vectorstore.add_texts(texts=chunks, metadatas=[{"document_id": document_id}] * len(chunks))
                vector_count = len(chunks)
            else:
                vector_count = 0

            return {
                "page_count": 1,  # TXT files are treated as single-page documents
                "preview_urls": [],  # TXT files don't have previews
                "vector_count": vector_count
            }
        except Exception as e:
            logger.error(f"Error processing TXT: {str(e)}")
            return {
                "page_count": 0,
                "preview_urls": [],
                "vector_count": 0
            }

    def get_response(self, query: str, document_id: Optional[str] = None, chat_history: Optional[List[Dict]] = None) -> Tuple[str, List[str]]:
        try:
            # Initialize OpenAI embeddings
            embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)

            # Connect to Weaviate
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.cluster_url,
                auth_credentials=AuthApiKey(api_key=self.api_key),
                headers={'X-OpenAI-Api-Key': self.openai_api_key}
            )

            # Initialize vector store
            vectorstore = WeaviateVectorStore(
                client=client,
                index_name=self.collection_name,
                text_key="text",
                embedding=embeddings,
            )

            # Initialize the conversational chain
            llm = ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo", openai_api_key=self.openai_api_key)
            memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
            conversation_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever(),
                memory=memory
            )

            # Query the conversation chain
            result = conversation_chain.invoke({"question": query})
            answer = result["answer"]

            # Log the answer
            logger.info(f"Answer: {answer}")

            return answer, []

        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}")
            raise

    def cleanup(self) -> None:
        """Cleanup resources."""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Weaviate client closed successfully.")