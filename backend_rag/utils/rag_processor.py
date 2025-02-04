from pathlib import Path
from typing import Any, Dict, List, Optional
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
        """Process a document and prepare it for RAG operations"""
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

    def _process_pdf(self, file_path: Path, doc_id: str) -> Dict[str, Any]:
        """Process PDF document and generate previews"""
        try:
            # Get page count
            with open(file_path, 'rb') as file:
                pdf = PyPDF2.PdfReader(file)
                page_count = len(pdf.pages)

            # Create document-specific preview directory
            preview_dir = self.preview_dir / doc_id
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
                preview_urls.append(f"/api/previews/{doc_id}/{i + 1}")

            logger.info(f"Generated {len(preview_urls)} previews for {file_path.name}")
            
            return {
                "page_count": page_count,
                "preview_urls": preview_urls,
                "vector_count": page_count
            }

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {
                "page_count": 0,
                "preview_urls": [],
                "vector_count": 0
            }

    def get_response(self, query: str, chat_history: Optional[List[Dict]] = None, document_id: Optional[str] = None) -> Dict:
        """Get RAG response for a query."""
        try:
            # Create retriever with optional document filter
            search_kwargs = {}
            if document_id:
                where_filter = wvc.query.Filter.by_property("document_id").equal(document_id)
                search_kwargs["filters"] = where_filter
            
            retriever = self.vectorstore.as_retriever(search_kwargs=search_kwargs)

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
            
            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            rag_chain = create_retrieval_chain(retriever, question_answer_chain)

            # Get response
            result = rag_chain.invoke({"input": query})
            logger.info("Received response from LLM")

            return {
                "answer": result["answer"],
                "sources": self._format_sources(result.get("source_documents", []))
            }

        except Exception as e:
            logger.error(f"Error getting RAG response: {e}")
            raise

    def _format_sources(self, source_documents: List[Any]) -> List[Dict[str, Any]]:
        """Format source documents for the response."""
        sources = []
        for doc in source_documents:
            sources.append({
                "document_id": doc.metadata.get("document_id"),
                "page": doc.metadata.get("page"),
                "text": doc.page_content[:200] + "..."
            })
        logger.info(f"Found {len(sources)} relevant sources")
        return sources

    def cleanup(self) -> None:
        """Cleanup resources."""
        if hasattr(self, 'client'):
            self.client.close()

    def _process_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Process PDF document and generate previews"""
        try:
            # Get page count
            with open(file_path, 'rb') as file:
                pdf = PyPDF2.PdfReader(file)
                page_count = len(pdf.pages)

            # Create document-specific preview directory
            doc_id = file_path.stem
            preview_dir = self.preview_dir / doc_id
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
                preview_urls.append(f"/api/previews/{doc_id}/{i + 1}")

            # Process for RAG if available
            if hasattr(self, 'vectorstore'):
                loader = PyPDFLoader(str(file_path))
                pages = loader.load()
                chunks = self.text_splitter.split_documents(pages)
                
                # Add to vector store
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