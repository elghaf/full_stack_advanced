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
from tqdm import tqdm
import unittest
from unittest.mock import patch, MagicMock
from weaviate.classes.query import Filter
import openai


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Ensure you have your OpenAI API key set in your environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

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
            
            # Handle text files
            if file_path.suffix.lower() == '.txt':
                try:
                    logger.info("Processing text file...")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    
                    # Split the text into chunks based on double newlines
                    chunks = text.split('\n\n')
                    logger.info(f"Split text into {len(chunks)} chunks")
                    
                    # Add progress bar for text chunks
                    for i, chunk in enumerate(tqdm(chunks, desc="Processing text chunks", unit="chunk")):
                        # Print the chunk to the console
                        print("****************************\n")
                        print(f"Chunk {i+1}:\n{chunk}\n{'-'*40}")
                        

                        # Calculate start and end lines based on chunk index
                        start_line = i * 1000 + 1
                        end_line = (i + 1) * 1000
                        
                        self._store_chunk(
                            text=chunk,
                            document_id=document_id,
                            page=1,
                            start_line=start_line,
                            end_line=end_line,
                            section_title=f"Section {i+1}",
                            file_name=file_name
                        )
                        
                        preview_zones.append({
                            "page": 1,
                            "startLine": start_line,
                            "endLine": end_line,
                            "text": chunk,
                            "sectionTitle": f"Section {i+1}"
                        })
                        
                except UnicodeDecodeError:
                    logger.info("Retrying with latin-1 encoding...")
                    with open(file_path, 'r', encoding='latin-1') as f:
                        text = f.read()
                    # Same processing with chunks...
            
            # Process PDF files
            elif file_path.suffix.lower() == '.pdf':
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    total_pages = len(pdf_reader.pages)
                    logger.info(f"Processing PDF with {total_pages} pages...")
                    
                    # Add progress bar for PDF pages
                    for page_num in tqdm(range(1, total_pages + 1), desc="Processing PDF pages", unit="page"):
                        page = pdf_reader.pages[page_num - 1]
                        text = page.extract_text()
                        if text:
                            lines = text.split('\n')
                            current_section = "Main Content"
                            section_text = []
                            start_line = 1
                            
                            # Add progress bar for sections within each page
                            for line_num, line in enumerate(tqdm(lines, desc=f"Processing page {page_num}", leave=False), 1):
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

            logger.info("Document processing completed successfully")
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
            # Check if the query is a single word
            is_single_word = len(query.split()) == 1

            # Create the query result based on whether it's a single word or not
            if  (is_single_word == False):
                query_result = self.collection.query.near_text(
                    query=query,
                    limit=10
                )
            else:
                query_filter = Filter.by_property("text").like(f"*{query}*")
                query_result = self.collection.query.near_text(
                    query=query,
                    limit=10,
                    filters=query_filter
                )

            data_response = query_result.objects

            if not data_response:
                return "I couldn't find any relevant information in the documents. Please try rephrasing your query or upload more documents.", []

            # Prepare the data for OpenAI
            data_to_send = "\n".join([doc.properties['text'] for doc in data_response])

            # Call OpenAI to select the most relevant response
            openai_response = openai.ChatCompletion.create(
                model="gpt-4",  # or the model you want to use
                messages=[
                    {"role": "user", "content": f"Based on the query_for_client= '{query}', select the most relevant response from the following data_response:\n{data_to_send}"}
                ]
            )

            # Extract the selected response from OpenAI
            selected_response = openai_response['choices'][0]['message']['content']
            print("****************************\n")
            print(f"Selected response: {selected_response}")
            print("****************************\n")
            # Process the selected response as needed
            # You can further parse this selected response if necessary

            # Continue with your existing logic to format responses and sources
            sources = []
            seen_ids = set()
            formatted_responses = []

            for doc in data_response:
                # Get metadata
                metadata = doc.properties
                start_line = metadata.get("start_line", 0)
                end_line = metadata.get("end_line", 0)
                file_name = metadata.get("file_name", "Unknown")
                page = metadata.get("page", 1)

                # Extract service ID from content
                content_lines = doc.properties['text'].split('\n')
                service_id = None
                service_info = {}

                for line in content_lines:
                    if line.startswith('ID:'):
                        service_id = line.replace('ID:', '').strip()
                    elif line.startswith('Lien EN:'):
                        service_info['url'] = line.replace('Lien EN:', '').strip()
                    elif line.startswith('Nom du service EN:'):
                        service_info['name'] = line.replace('Nom du service EN:', '').strip()
                    elif line.startswith('DESCRIPTION EN EN:'):
                        service_info['description'] = line.replace('DESCRIPTION EN EN:', '').strip()

                # Skip if we've already seen this service ID or if it's empty
                if not service_id or service_id in seen_ids or not service_info.get('description'):
                    logger.warning(f"Skipping service ID: {service_id} - already seen or missing description.")
                    continue

                seen_ids.add(service_id)

                # Format the response with service information and URL
                if service_info.get('name') and service_info.get('description'):
                    response = f"**{service_info['name']}**: {service_info['description']}"
                    if service_info.get('url'):
                        response += f"\n→ More information: {service_info['url']}"
                    formatted_responses.append(response)

                # Create source info with all fields at the root level
                source_info = {
                    "document_id": service_id,
                    "service_name": service_info.get('name', ''),
                    "description": service_info.get('description', ''),
                    "url": service_info.get('url', ''),
                    "relevance_score": 1.0,  # Adjust as needed
                    "file_name": file_name,
                    "page": page,
                    "start_line": start_line,
                    "end_line": end_line
                }
                sources.append(source_info)

                logger.info(f"Processed service ID: {service_id} (lines {start_line}-{end_line})")

            if not sources:
                return "Could not find relevant information in the documents.", []

            # Combine all formatted responses into a single string with proper spacing
            final_response = selected_response  # Use the selected response from OpenAI

            # Add source information to the response
            final_response += "\n\nSources:"
            for idx, source in enumerate(sources, 1):
                final_response += f"\n{idx}. Found in {source['file_name']} (Page {source['page']}, Lines {source['start_line']}-{source['end_line']})"

            return final_response, sources

        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}", exc_info=True)
            raise

    def cleanup(self) -> None:
        """Cleanup resources."""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Weaviate client closed successfully.")
