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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RAGProcessor:
    def __init__(self):
        # Get credentials from environment variables
        self.cluster_url = os.getenv("WCD_URL")
        self.api_key = os.getenv("WCD_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.collection_name = "DocumentChunks"

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)

        # Validate credentials
        if not all([self.cluster_url, self.api_key, self.openai_api_key]):
            raise ValueError("Missing required environment variables")

        logger.info(f"Connecting to Weaviate at URL: {self.cluster_url}")

        try:
            # Initialize Weaviate client
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.cluster_url,
                auth_credentials=Auth.api_key(self.api_key),
                headers={'X-OpenAI-Api-Key': self.openai_api_key}
            )
            logger.info("Successfully connected to Weaviate")

            # Initialize or get collection
            self._initialize_collection()
            
            # Initialize vector store
            self.vectorstore = WeaviateVectorStore(
                client=self.client,
                index_name=self.collection_name,
                text_key="text",
                embedding=self.embeddings,
            )
            
            # Register cleanup on program exit
            atexit.register(self.cleanup)

        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {str(e)}")
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

    def process_document(self, file_path: Path, document_id: str) -> None:
        """Process a document for RAG."""
        try:
            # Load document based on file type
            if file_path.suffix.lower() == '.pdf':
                loader = PyPDFLoader(str(file_path))
                logger.info("Using PDF loader")
            elif file_path.suffix.lower() == '.docx':
                loader = Docx2txtLoader(str(file_path))
                logger.info("Using DOCX loader")
            else:  # .txt
                loader = TextLoader(str(file_path))
                logger.info("Using Text loader")

            documents = loader.load()
            logger.info(f"Loaded {len(documents)} document segments")
            
            # Split text into chunks
            texts = self.text_splitter.split_documents(documents)
            logger.info(f"Split into {len(texts)} chunks")
            
            # Add document ID to metadata
            for text in texts:
                text.metadata["document_id"] = document_id

            # Store in vector database
            self.vectorstore.add_documents(texts)
            logger.info("Successfully stored documents in vector database")

        except Exception as e:
            logger.error(f"Error processing document for RAG: {e}")
            raise

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