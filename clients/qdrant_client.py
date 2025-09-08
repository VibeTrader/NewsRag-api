import os
import asyncio
from typing import Optional, Dict, Any, List
from loguru import logger
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
import numpy as np

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
        
        # Embedding model configuration (for search queries only) - Match crawler exactly
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-stocks")
        self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "3072"))  # text-embedding-3-large: 3072
        
        logger.info(f"QdrantClient initialized for URL: {self.url}")
        logger.info(f"Using collection: {self.collection_name}")
        logger.info(f"Using embedding deployment: {self.embedding_deployment} (dimensions: {self.embedding_dimension})")
        
        # Ensure collection exists synchronously
        self._ensure_collection_exists_sync()



    def _get_embedding_for_search(self, text: str):
        """Generate embedding for search queries using Azure OpenAI.
        This is needed because search queries need to be converted to vectors
        to find similar articles in the database."""
        try:
            # Import here to avoid dependency if not needed
            from openai import AzureOpenAI
            import httpx

            # Create HTTP client without proxies
            http_client = httpx.Client(
                headers={"Accept-Encoding": "gzip, deflate"}
            )
            
            # Initialize OpenAI client for search queries only
            openai_client = AzureOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                azure_endpoint=os.getenv("OPENAI_BASE_URL"),
                http_client=http_client
            )
            
            response = openai_client.embeddings.create(
                input=text,
                model=self.embedding_deployment
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error generating search embedding: {e}")
            raise

    def _generate_ai_summary(self, text_content: str) -> str:
        """Generate AI summary of the content using Azure OpenAI."""
        try:
            from openai import AzureOpenAI
            import httpx
            
            # Create HTTP client without proxies
            http_client = httpx.Client(
                headers={"Accept-Encoding": "gzip, deflate"}
            )
            
            openai_client = AzureOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                azure_endpoint=os.getenv("OPENAI_BASE_URL"),
                http_client=http_client
            )
            
            # Use the embedding-stocks deployment directly
            model_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-stocks")
            
            # Generate summary using GPT
            response = openai_client.chat.completions.create(
                model=model_deployment,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise summaries of news articles. Focus on the key points and main insights."},
                    {"role": "user", "content": f"Please provide a concise summary of this article:\n\n{text_content[:3000]}"}  # Limit to 3000 chars
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            # Fallback to first 500 characters
            return text_content[:500] + "..." if len(text_content) > 500 else text_content

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
                    field_schema=models.PayloadFieldSchema.INTEGER  # Use INTEGER for timestamp
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
        """Checks the health of Qdrant service."""
        try:
            # Test Qdrant connection
            collections = self.client.get_collections()
            logger.info(f"Qdrant health check successful. Found {len(collections.collections)} collections.")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False



    

    async def search_documents(self, query: str, limit: int = 10, score_threshold: float = 0.7, use_ai_summary: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Searches for documents similar to the query using Azure OpenAI embeddings.
        
        Args:
            query: The search query text.
            limit: Maximum number of results to return.
            score_threshold: Minimum similarity score threshold.
            use_ai_summary: Whether to generate AI summaries (slower but better).
            
        Returns:
            List of matching documents with scores, or None on failure.
        """
        try:
            # Generate query embedding using Azure OpenAI for search
            query_embedding = self._get_embedding_for_search(query)
            
            # Search in collection
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results to match crawler's data structure
            results = []
            for result in search_results:
                payload = result.payload
                
                # Get the text content (this is what the crawler stores)
                text_content = payload.get("text", "")
                
                # Generate summary based on preference
                if use_ai_summary and len(text_content) > 100:
                    summary = self._generate_ai_summary(text_content)
                else:
                    summary = text_content  # Full content as summary
                
                # Format the response to match expected API format
                formatted_payload = {
                    "id": result.id,
                    "title": text_content[:100] + "..." if len(text_content) > 100 else text_content,
                    "content": text_content,
                    "summary": summary,
                    "url": payload.get("url", ""),  # URL if available
                    "source": payload.get("source", ""),
                    "author": payload.get("author", ""),
                    "category": payload.get("category", ""),
                    "publishDatePst": payload.get("publishDatePst", ""),
                    "text_length": payload.get("text_length", 0),
                    "article_id": payload.get("article_id", "")
                }
                
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": formatted_payload
                })
            
            logger.info(f"Search returned {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents in Qdrant: {e}")
            return None

    

    async def get_collection_stats(self) -> Optional[Dict[str, Any]]:
        """Gets statistics about the collection."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            # Get point count by scrolling
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=1
            )
            
            # Count total points (this is a simple approach)
            total_points = 0
            try:
                # Get a sample to check if collection has data
                sample = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=1000
                )
                total_points = len(sample[0]) if sample[0] else 0
            except:
                pass
            
            return {
                "collection_name": self.collection_name,
                "points_count": total_points,
                "segments_count": getattr(collection_info, 'segments_count', 'unknown'),
                "status": collection_info.status,
                "embedding_model": self.embedding_deployment
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return None