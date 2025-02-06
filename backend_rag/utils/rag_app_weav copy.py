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
                doc_info = self._process_pdf(file_path, document_id)
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

    def _process_pdf(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        """Process PDF document and generate previews."""
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
                dpi=72,  # Lower DPI for previews
                size=(None, 800)  # Max height of 800px
            )
            preview_urls = []
            for i, image in enumerate(images):
                preview_path = preview_dir / f"page_{i + 1}.png"
                image.save(str(preview_path), "PNG", optimize=True)
                preview_urls.append(f"/api/previews/{document_id}/{i + 1}")

            # Process for RAG if available
            if hasattr(self, 'vectorstore'):
                loader = PyPDFLoader(str(file_path))
                pages = loader.load_and_split()
                chunks = self.text_splitter.split_documents(pages)
                self.vectorstore.add_documents(chunks)
                vector_count = len(chunks)
            else:
                vector_count = 0

            return {
                "page_count": page_count,
                "preview_urls": preview_urls,
                "vector_count": vector_count
            }
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {
                "page_count": 0,
                "preview_urls": [],
                "vector_count": 0
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
            # Load the SentenceTransformer model
            model = SentenceTransformer("nomic-ai/modernbert-embed-base")

            # Generate query embedding
            query_embedding = model.encode(query)

            # Prepare the query
            logger.info(f"Query: {query}, Document ID: {document_id}")

            # Get the collection
            collection = self.client.collections.get(self.collection_name)

            # Perform a similarity search using the query embedding
            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=5
            )

            # Log the response
            logger.info(f"Response: {response}")

            # Extract the relevant documents
            source_documents = []
            for obj in response.objects:
                source_documents.append({
                    "document_id": obj.properties.get("document_id"),
                    "page": obj.properties.get("page"),
                    "text": obj.properties.get("text", "")[:200] + "..."
                })

            # Log the source documents
            logger.info(f"Source documents: {source_documents}")

            # Create prompt template
            system_prompt = (
                "You are an assistant for question-answering tasks. "
                "Use the following pieces of retrieved context to answer "
                "the question. If you don't know the answer, say that you "
                "don't know. Use three sentences maximum and keep the "
                "answer concise.\n\n{context}"
            )
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
            ])

            # Create chain
            llm = ChatOpenAI(
                temperature=0,
                model_name="gpt-4",
                openai_api_key=self.openai_api_key
            )

            # Create and run the chain
            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            
            # Format the context from source documents
            context = "\n\n".join([doc["text"] for doc in source_documents])
            
            # Get the answer
            result = question_answer_chain.invoke({
                "input": query,
                "context": context
            })

            logger.info(f"Result type: {type(result)}, Result content: {result}")

            if isinstance(result, dict) and "answer" in result:
                return result["answer"], source_documents
            else:
                logger.error("Unexpected result format")
                raise ValueError("Unexpected result format")

        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}")
            raise

    def cleanup(self) -> None:
        """Cleanup resources."""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Weaviate client closed successfully.")