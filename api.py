from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import asyncio
from loguru import logger
from dotenv import load_dotenv

# Import our Qdrant client
from clients.qdrant_client import QdrantClientWrapper

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="NewsRagnarok API",
    description="FastAPI service for news article search using Qdrant vector database",
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

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    score_threshold: Optional[float] = 0.7

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_count: int
    query: str

class HealthResponse(BaseModel):
    status: str
    qdrant_connected: bool
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
        
        # Get collection stats if connected
        stats = None
        if qdrant_ok:
            stats = await client.get_collection_stats()
        
        return HealthResponse(
            status="healthy" if qdrant_ok else "unhealthy",
            qdrant_connected=qdrant_ok,
            collection_stats=stats
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            qdrant_connected=False,
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
        results = await client.search_documents(
            query=request.query,
            limit=request.limit,
            score_threshold=request.score_threshold
        )
        
        if results is not None:
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

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "NewsRagnarok API",
        "version": "1.0.0",
        "description": "FastAPI service for news article search using Qdrant vector database",
        "endpoints": {
            "health": "/health",
            "search": "/search",
            "delete_old": "/documents/older-than/{hours}",
            "clear_all": "/documents",
            "stats": "/documents/stats"
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
