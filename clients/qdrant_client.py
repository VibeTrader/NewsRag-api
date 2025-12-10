import os
import asyncio
import time
from typing import Optional, Dict, Any, List
from loguru import logger
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
import numpy as np

# Import custom exceptions
try:
    from utils.exceptions import EmbeddingError, QdrantError, ErrorCategory
    HAS_CUSTOM_EXCEPTIONS = True
except ImportError:
    HAS_CUSTOM_EXCEPTIONS = False
    # Fallback classes
    class EmbeddingError(Exception):
        def __init__(self, message, **kwargs):
            super().__init__(message)
            self.category = kwargs.get('category', 'internal')
            self.service = "azure_openai"
            self.details = kwargs.get('details', {})
    
    class QdrantError(Exception):
        def __init__(self, message, **kwargs):
            super().__init__(message)
            self.category = kwargs.get('category', 'internal')
            self.service = "qdrant"
            self.details = kwargs.get('details', {})
    
    class ErrorCategory:
        AUTHENTICATION = "authentication"
        CONFIGURATION = "configuration"
        SERVICE_UNAVAILABLE = "service_unavailable"
        RATE_LIMIT = "rate_limit"
        INTERNAL = "internal"

# Import monitoring for error tracking
try:
    from utils.monitoring import AppInsightsMonitor
    try:
        monitor = AppInsightsMonitor.get_instance()
        if not monitor.enabled:
            monitor = None
    except Exception:
        monitor = None
except ImportError:
    monitor = None

# Load environment variables
load_dotenv()

class QdrantClientWrapper:
    """Client for interacting with Qdrant Cloud vector database with Azure OpenAI embeddings."""

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None, dependency_tracker=None):
        """Initializes the Qdrant client with Azure OpenAI embeddings.

        Args:
            url: The Qdrant Cloud URL. If None, loads from QDRANT_URL environment variable.
            api_key: The Qdrant API key. If None, loads from QDRANT_API_KEY environment variable.
            dependency_tracker: Optional dependency tracker for monitoring.
        """
        self.url = url or os.getenv("QDRANT_URL")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "news_articles")
        self.dependency_tracker = dependency_tracker
        
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
        """Generate embedding for search queries using Azure OpenAI with proper error handling."""
        try:
            from openai import AzureOpenAI
            import httpx

            # Check for required environment variables first
            api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            endpoint = os.getenv("OPENAI_BASE_URL")
            
            if not api_key:
                error = EmbeddingError(
                    "Azure OpenAI API key not configured. Set AZURE_OPENAI_API_KEY or OPENAI_API_KEY.",
                    details={"missing_var": "AZURE_OPENAI_API_KEY or OPENAI_API_KEY"}
                )
                logger.error(f"Configuration error: {error}")
                if monitor and monitor.enabled:
                    monitor.track_event("critical_config_error", {
                        "service": "azure_openai",
                        "error": "missing_api_key"
                    })
                raise error
            
            if not endpoint:
                error = EmbeddingError(
                    "Azure OpenAI endpoint not configured. Set OPENAI_BASE_URL.",
                    details={"missing_var": "OPENAI_BASE_URL"}
                )
                logger.error(f"Configuration error: {error}")
                raise error

            http_client = httpx.Client(
                headers={"Accept-Encoding": "gzip, deflate"},
                timeout=30.0
            )
            
            openai_client = AzureOpenAI(
                api_key=api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                azure_endpoint=endpoint,
                http_client=http_client
            )
            
            response = openai_client.embeddings.create(
                input=text,
                model=self.embedding_deployment
            )
            return response.data[0].embedding
            
        except EmbeddingError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            error_str = str(e)
            
            # Create detailed error with proper categorization
            error = EmbeddingError(
                f"Failed to generate embedding: {error_str}",
                original_error=e,
                details={
                    "deployment": self.embedding_deployment,
                    "text_length": len(text),
                    "endpoint": os.getenv("OPENAI_BASE_URL", "not_set")[:30] + "..."
                }
            )
            
            # Track to App Insights with proper categorization
            if monitor and monitor.enabled:
                category = "internal"
                if HAS_CUSTOM_EXCEPTIONS and hasattr(error, 'category'):
                    category = error.category.value if hasattr(error.category, 'value') else str(error.category)
                
                monitor.track_exception({
                    "error": str(error),
                    "category": category,
                    "service": "azure_openai",
                    "operation": "embedding",
                    "deployment": self.embedding_deployment
                })
                
                # Track as a critical event for alerting on auth/config issues
                if "401" in error_str.lower() or "unauthorized" in error_str.lower() or "invalid" in error_str.lower():
                    monitor.track_event("critical_api_error", {
                        "service": "azure_openai",
                        "category": "authentication",
                        "error": error_str[:200]
                    })
                elif "404" in error_str.lower() or "not found" in error_str.lower():
                    monitor.track_event("critical_api_error", {
                        "service": "azure_openai",
                        "category": "configuration",
                        "error": error_str[:200]
                    })
            
            logger.error(f"Embedding generation failed: {error}")
            raise error

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

    def _perform_search(self, query_vector: List[float], limit: int, score_threshold: float):
        """Perform vector search with compatibility for different qdrant-client versions.
        
        qdrant-client v1.15+ replaced 'search' with 'query_points'.
        This method handles both versions.
        """
        try:
            # Try new API first (qdrant-client >= 1.15)
            if hasattr(self.client, 'query_points'):
                results = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    with_payload=True
                )
                # query_points returns QueryResponse with .points attribute
                return results.points if hasattr(results, 'points') else results
            else:
                # Fallback to old API (qdrant-client < 1.15)
                return self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold
                )
        except Exception as e:
            logger.error(f"Error in _perform_search: {e}")
            raise QdrantError(
                f"Search failed: {str(e)}",
                original_error=e,
                details={"collection": self.collection_name}
            )

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
            List of matching documents with scores.
            
        Raises:
            EmbeddingError: If embedding generation fails (API key issues, etc.)
            QdrantError: If Qdrant search fails
        """
        try:
            start_time = time.time()
            
            # Generate query embedding - this will raise EmbeddingError if it fails
            try:
                if self.dependency_tracker:
                    query_embedding = await self.dependency_tracker.track_async(
                        asyncio.to_thread(self._get_embedding_for_search, query),
                        name="generate_embedding",
                        type_name="Azure OpenAI",
                        target=self.embedding_deployment,
                        properties={"query_length": str(len(query)), "operation": "embedding"}
                    )
                else:
                    query_embedding = self._get_embedding_for_search(query)
            except EmbeddingError:
                # Re-raise embedding errors with full context for proper handling upstream
                raise
            
            # Search in collection
            search_start_time = time.time()
            
            # Track Qdrant search operation
            # Note: qdrant-client v1.15+ uses query_points instead of search
            if self.dependency_tracker:
                search_results = await self.dependency_tracker.track_async(
                    asyncio.to_thread(
                        self._perform_search,
                        query_embedding,
                        limit,
                        score_threshold
                    ),
                    name="vector_search",
                    type_name="Qdrant",
                    target=self.url,
                    properties={
                        "collection": self.collection_name,
                        "limit": str(limit),
                        "threshold": str(score_threshold)
                    }
                )
            else:
                search_results = self._perform_search(query_embedding, limit, score_threshold)
            
            # Format results to match crawler's data structure
            results = []
            for result in search_results:
                payload = result.payload
                
                # Get the text content (this is what the crawler stores)
                text_content = payload.get("text", "")
                
                # Generate summary based on preference
                if use_ai_summary and len(text_content) > 100:
                    if self.dependency_tracker:
                        # Wrap the synchronous summary function in asyncio.to_thread
                        summary = await self.dependency_tracker.track_async(
                            asyncio.to_thread(self._generate_ai_summary, text_content),
                            name="generate_summary",
                            type_name="Azure OpenAI",
                            target=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
                            properties={"content_length": str(len(text_content)), "operation": "summarization"}
                        )
                    else:
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
            
            # Track metrics for the overall operation
            total_duration = (time.time() - start_time) * 1000
            search_duration = (search_start_time - start_time) * 1000
            results_processing_duration = (time.time() - search_start_time) * 1000
            
            logger.info(f"Search returned {len(results)} results for query: {query[:50]}... (duration: {total_duration:.2f}ms)")
            
            return results
            
        except EmbeddingError:
            # Re-raise embedding errors so they can be handled properly upstream
            raise
        except Exception as e:
            # Wrap other errors in QdrantError for proper categorization
            error = QdrantError(
                f"Error searching documents: {str(e)}",
                original_error=e,
                details={"query": query[:100], "collection": self.collection_name}
            )
            logger.error(f"Search error: {error}")
            
            if monitor and monitor.enabled:
                monitor.track_exception({
                    "error": str(error),
                    "service": "qdrant",
                    "operation": "search",
                    "collection": self.collection_name
                })
            
            raise error

    

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