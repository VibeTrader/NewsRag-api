from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import asyncio
import json
import hashlib
from loguru import logger
from dotenv import load_dotenv
import redis.asyncio as redis

# Import our Qdrant client
from clients.qdrant_client import QdrantClientWrapper

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="NewsRagnarok API",
    description="FastAPI service for news article search using Qdrant vector database with Redis caching",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6380"))  # Default to 6380 for Azure Redis
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_SSL = os.getenv("REDIS_SSL", "true").lower() == "true"  # Default to true for Azure Redis
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default

# Initialize Redis client
redis_client = None

async def get_redis_client():
    """Get Redis client instance."""
    global redis_client
    if redis_client is None:
        try:
            if REDIS_URL:
                # Use REDIS_URL if provided
                redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            elif REDIS_HOST and REDIS_PASSWORD:
                # Use separate configuration for Azure Redis
                redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    password=REDIS_PASSWORD,
                    ssl=REDIS_SSL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            else:
                logger.warning("Redis configuration not found")
                return None
                
            # Test connection
            await redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            redis_client = None
    return redis_client

async def cache_search_results(cache_key: str, results: List[Dict], ttl: int = CACHE_TTL):
    """Cache search results in Redis."""
    try:
        redis_client = await get_redis_client()
        if redis_client:
            await redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(results, default=str)
            )
            logger.info(f"Cached search results for key: {cache_key}")
    except Exception as e:
        logger.error(f"Failed to cache results: {e}")

async def get_cached_results(cache_key: str) -> Optional[List[Dict]]:
    """Get cached search results from Redis."""
    try:
        redis_client = await get_redis_client()
        if redis_client:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                results = json.loads(cached_data)
                logger.info(f"Retrieved cached results for key: {cache_key}")
                return results
    except Exception as e:
        logger.error(f"Failed to get cached results: {e}")
    return None

def generate_cache_key(query: str, limit: int, score_threshold: float, use_ai_summary: bool) -> str:
    """Generate a unique cache key for search parameters."""
    cache_string = f"{query}:{limit}:{score_threshold}:{use_ai_summary}"
    return f"search:{hashlib.md5(cache_string.encode()).hexdigest()}"

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    score_threshold: Optional[float] = 0.7
    use_ai_summary: Optional[bool] = False

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_count: int
    query: str

class HealthResponse(BaseModel):
    status: str
    qdrant_connected: bool
    redis_connected: bool
    collection_stats: Optional[Dict[str, Any]] = None

class DeleteRequest(BaseModel):
    hours: int

# Dependency to get Qdrant client
async def get_qdrant_client():
    """Dependency to get Qdrant client instance."""
    client = QdrantClientWrapper()
    try:
        yield client
    finally:
        await client.close()

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check(client: QdrantClientWrapper = Depends(get_qdrant_client)):
    """Health check endpoint."""
    try:
        # Check Qdrant connection
        qdrant_ok = await client.check_health()
        
        # Check Redis connection
        redis_ok = False
        try:
            redis_client = await get_redis_client()
            if redis_client:
                await redis_client.ping()
                redis_ok = True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            redis_ok = False

        # Get collection stats if connected
        stats = None
        if qdrant_ok:
            stats = await client.get_collection_stats()
        
        return HealthResponse(
            status="healthy" if qdrant_ok and redis_ok else "unhealthy",
            qdrant_connected=qdrant_ok,
            redis_connected=redis_ok,
            collection_stats=stats
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            qdrant_connected=False,
            redis_connected=False,
            collection_stats=None
        )



# Search documents endpoint
@app.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    client: QdrantClientWrapper = Depends(get_qdrant_client)
):
    """Search for documents similar to the query."""
    try:
        # Generate cache key
        cache_key = generate_cache_key(
            request.query,
            request.limit,
            request.score_threshold,
            request.use_ai_summary
        )

        # Check for cached results
        cached_results = await get_cached_results(cache_key)
        if cached_results:
            return SearchResponse(
                results=cached_results,
                total_count=len(cached_results),
                query=request.query
            )

        results = await client.search_documents(
            query=request.query,
            limit=request.limit,
            score_threshold=request.score_threshold,
            use_ai_summary=request.use_ai_summary
        )
        
        if results is not None:
            # Cache the results
            await cache_search_results(cache_key, results)
            return SearchResponse(
                results=results,
                total_count=len(results),
                query=request.query
            )
        else:
            raise HTTPException(status_code=500, detail="Search failed")
            
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Delete documents older than endpoint
@app.delete("/documents/older-than/{hours}")
async def delete_documents_older_than(
    hours: int,
    client: QdrantClientWrapper = Depends(get_qdrant_client)
):
    """Delete documents older than specified hours."""
    try:
        if hours <= 0:
            raise HTTPException(status_code=400, detail="Hours must be greater than 0")
        
        result = await client.delete_documents_older_than(hours)
        
        if result:
            return result
        else:
            raise HTTPException(status_code=500, detail="Failed to delete documents")
            
    except Exception as e:
        logger.error(f"Error deleting old documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Clear all documents endpoint
@app.delete("/documents")
async def clear_all_documents(client: QdrantClientWrapper = Depends(get_qdrant_client)):
    """Clear all documents from the collection."""
    try:
        result = await client.clear_all_documents()
        
        if result:
            return result
        else:
            raise HTTPException(status_code=500, detail="Failed to clear documents")
            
    except Exception as e:
        logger.error(f"Error clearing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get collection stats endpoint
@app.get("/documents/stats")
async def get_collection_stats(client: QdrantClientWrapper = Depends(get_qdrant_client)):
    """Get collection statistics."""
    try:
        stats = await client.get_collection_stats()
        
        if stats:
            return stats
        else:
            raise HTTPException(status_code=500, detail="Failed to get collection stats")
            
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Clear cache endpoint
@app.delete("/cache")
async def clear_cache():
    """Clear all cached search results."""
    try:
        redis_client = await get_redis_client()
        if redis_client:
            # Clear all search cache keys
            keys = await redis_client.keys("search:*")
            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cached search results")
                return {"status": "success", "message": f"Cleared {len(keys)} cached results"}
            else:
                return {"status": "success", "message": "No cached results to clear"}
        else:
            raise HTTPException(status_code=503, detail="Redis not available")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get cache stats endpoint
@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    try:
        redis_client = await get_redis_client()
        if redis_client:
            keys = await redis_client.keys("search:*")
            return {
                "status": "success",
                "cached_searches": len(keys),
                "cache_keys": keys[:10]  # Show first 10 keys
            }
        else:
            raise HTTPException(status_code=503, detail="Redis not available")
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "NewsRagnarok API",
        "version": "1.0.0",
        "description": "FastAPI service for news article search using Qdrant vector database with Redis caching",
        "endpoints": {
            "health": "/health",
            "search": "/search",
            "delete_old": "/documents/older-than/{hours}",
            "clear_all": "/documents",
            "stats": "/documents/stats",
            "cache_clear": "/cache",
            "cache_stats": "/cache/stats"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8000))
    
    # Run the application
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
