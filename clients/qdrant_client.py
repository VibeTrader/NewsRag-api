import os
import asyncio
from typing import Optional, Dict, Any, List
from loguru import logger
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
import numpy as np
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

class QdrantClientWrapper:
    """Client for interacting with Qdrant Cloud vector database with Azure OpenAI embeddings."""

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """Initializes the Qdrant client with Azure OpenAI embeddings.

        Args:
            url: The Qdrant Cloud URL. If None, loads from QDRANT_URL environment variable.
            api_key: The Qdrant API key. If None, loads from QDRANT_API_KEY environment variable.
        """
        self.url = url or os.getenv("QDRANT_URL")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "news_articles")
        
        if not self.url:
            raise ValueError("QDRANT_URL environment variable is not configured.")
        if not self.api_key:
            raise ValueError("QDRANT_API_KEY environment variable is not configured.")
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=30.0
        )
        
        # Initialize Azure OpenAI client for embeddings
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Embedding model configuration
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
        self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "1536"))  # ada-002: 1536, text-embedding-3-small: 1536, text-embedding-3-large: 3072
        
        logger.info(f"QdrantClient initialized for URL: {self.url}")
        logger.info(f"Using collection: {self.collection_name}")
        logger.info(f"Using Azure OpenAI deployment: {self.embedding_deployment}")
        
        # Ensure collection exists synchronously
        self._ensure_collection_exists_sync()

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding using Azure OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_deployment
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using Azure OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                input=texts,
                model=self.embedding_deployment
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    def _ensure_collection_exists_sync(self):
        """Ensures the collection exists with proper configuration (synchronous version)."""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                
                # Create collection with Azure OpenAI embedding dimensions
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.embedding_dimension,  # Azure OpenAI embedding size
                        distance=models.Distance.COSINE
                    )
                )
                
                # Create payload indexes for efficient filtering
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="publishDatePst",
                    field_schema=models.PayloadFieldSchema.DATETIME
                )
                
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="source",
                    field_schema=models.PayloadFieldSchema.KEYWORD
                )
                
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise

    async def close(self):
        """Closes the Qdrant client."""
        if self.client:
            self.client.close()
            logger.info("QdrantClient closed.")

    async def check_health(self) -> bool:
        """Checks the health of both Qdrant and Azure OpenAI services."""
        try:
            # Test Qdrant connection
            collections = self.client.get_collections()
            logger.info(f"Qdrant health check successful. Found {len(collections.collections)} collections.")
            
            # Test Azure OpenAI connection
            test_embedding = self._get_embedding("health check")
            logger.info(f"Azure OpenAI health check successful. Embedding dimension: {len(test_embedding)}")
            
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def add_document(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Adds a document to the Qdrant collection using Azure OpenAI embeddings.
        
        Args:
            text_content: The text content to embed and store.
            metadata: Optional metadata to store with the document.
            
        Returns:
            Dictionary with status and document ID, or None on failure.
        """
        try:
            # Generate embedding using Azure OpenAI
            embedding = self._get_embedding(text_content)
            
            # Prepare payload
            payload = {
                "text": text_content,
                "text_length": len(text_content)
            }
            
            # Add metadata to payload
            if metadata:
                payload.update(metadata)
            
            # Generate unique ID
            import hashlib
            content_hash = hashlib.md5(f"{text_content}{str(metadata)}".encode()).hexdigest()
            
            # Upsert point (insert or update)
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=content_hash,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            logger.info(f"Successfully added document with ID: {content_hash}")
            return {
                "status": "success",
                "document_id": content_hash,
                "message": "Document added successfully"
            }
            
        except Exception as e:
            logger.error(f"Error adding document to Qdrant: {e}")
            return None

    async def add_documents_batch(self, documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Add multiple documents in batch for better performance.
        
        Args:
            documents: List of documents, each with 'text' and optional 'metadata'.
            
        Returns:
            Dictionary with status and count of added documents.
        """
        try:
            texts = [doc['text'] for doc in documents]
            
            # Generate embeddings in batch (more efficient)
            embeddings = self._get_embeddings_batch(texts)
            
            # Prepare points for batch insert
            points = []
            for i, doc in enumerate(documents):
                import hashlib
                content_hash = hashlib.md5(f"{doc['text']}{str(doc.get('metadata', {}))}".encode()).hexdigest()
                
                payload = {
                    "text": doc['text'],
                    "text_length": len(doc['text'])
                }
                
                if doc.get('metadata'):
                    payload.update(doc['metadata'])
                
                points.append(
                    models.PointStruct(
                        id=content_hash,
                        vector=embeddings[i],
                        payload=payload
                    )
                )
            
            # Batch upsert
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Successfully added {len(points)} documents in batch")
            return {
                "status": "success",
                "added_count": len(points),
                "message": f"Added {len(points)} documents successfully"
            }
            
        except Exception as e:
            logger.error(f"Error adding documents batch to Qdrant: {e}")
            return None

    async def search_documents(self, query: str, limit: int = 10, score_threshold: float = 0.7) -> Optional[List[Dict[str, Any]]]:
        """Searches for documents similar to the query using Azure OpenAI embeddings.
        
        Args:
            query: The search query text.
            limit: Maximum number of results to return.
            score_threshold: Minimum similarity score threshold.
            
        Returns:
            List of matching documents with scores, or None on failure.
        """
        try:
            # Generate query embedding using Azure OpenAI
            query_embedding = self._get_embedding(query)
            
            # Search in collection
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })
            
            logger.info(f"Search returned {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents in Qdrant: {e}")
            return None

    # ... rest of your methods remain the same (delete_document, delete_documents_older_than, etc.)
    
    async def delete_document(self, document_id: str) -> bool:
        """Deletes a document from the collection."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[document_id])
            )
            logger.info(f"Successfully deleted document with ID: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    async def delete_documents_older_than(self, hours: int) -> Optional[Dict[str, Any]]:
        """Deletes documents older than specified hours."""
        try:
            from datetime import datetime, timedelta
            import pytz
            
            pst = pytz.timezone('US/Pacific')
            cutoff_time = datetime.now(pst) - timedelta(hours=hours)
            
            old_docs = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="publishDatePst",
                            range=models.DatetimeRange(lt=cutoff_time.isoformat())
                        )
                    ]
                ),
                limit=1000
            )
            
            if not old_docs[0]:
                return {
                    "status": "no_action",
                    "deleted_count": 0,
                    "message": "No documents older than specified hours found"
                }
            
            doc_ids = [doc.id for doc in old_docs[0]]
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=doc_ids)
            )
            
            logger.info(f"Deleted {len(doc_ids)} documents older than {hours} hours")
            return {
                "status": "success",
                "deleted_count": len(doc_ids),
                "message": f"Deleted {len(doc_ids)} documents older than {hours} hours"
            }
            
        except Exception as e:
            logger.error(f"Error deleting old documents: {e}")
            return None

    async def clear_all_documents(self) -> Optional[Dict[str, Any]]:
        """Clears all documents from the collection."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            doc_count = collection_info.points_count
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=models.Filter())
            )
            
            logger.info(f"Cleared all {doc_count} documents from collection")
            return {
                "status": "success",
                "message": f"Cleared all {doc_count} documents from collection"
            }
            
        except Exception as e:
            logger.error(f"Error clearing all documents: {e}")
            return None

    async def get_collection_stats(self) -> Optional[Dict[str, Any]]:
        """Gets statistics about the collection."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "status": collection_info.status,
                "embedding_model": self.embedding_deployment
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return None