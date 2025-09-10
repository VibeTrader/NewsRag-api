from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import asyncio
import time
from loguru import logger
from dotenv import load_dotenv

# Import our Qdrant client
from clients.qdrant_client import QdrantClientWrapper

# Import summarization module
from utils.summarization import NewsSummarizer

# Import monitoring module
from utils.monitoring import AppInsightsMonitor
from utils.monitoring.dependency_tracker import DependencyTracker

# Load environment variables from .env file
load_dotenv()

# Initialize summarizer
summarizer = NewsSummarizer()

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

# Initialize Application Insights monitoring
monitor = AppInsightsMonitor(app)

# Initialize dependency tracker
dependency_tracker = DependencyTracker(monitor)



# Pydantic models
class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    score_threshold: Optional[float] = 0.3  # Changed from 0.7 to 0.3
    use_ai_summary: Optional[bool] = False

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_count: int
    query: str
    used_threshold: Optional[float] = None # Added for dynamic threshold

class SummaryRequest(BaseModel):
    query: str
    limit: Optional[int] = 20
    score_threshold: Optional[float] = 0.3
    use_cache: Optional[bool] = True
    format: Optional[str] = "json"  # Can be "json" or "text"

class SummaryResponse(BaseModel):
    summary: str
    keyPoints: List[str]
    sentiment: Dict[str, Any]
    impactLevel: str
    currencyPairRankings: List[Dict[str, Any]]
    riskAssessment: Dict[str, str]
    tradeManagementGuidelines: List[str]
    marketConditions: Optional[str] = None
    timestamp: str
    query: str
    articleCount: int
    formatted_text: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    qdrant_connected: bool
    collection_stats: Optional[Dict[str, Any]] = None

# Dependency to get Qdrant client
async def get_qdrant_client():
    """Dependency to get Qdrant client instance."""
    client = QdrantClientWrapper(dependency_tracker=dependency_tracker)
    try:
        yield client
    finally:
        await client.close()

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check(client: QdrantClientWrapper = Depends(get_qdrant_client)):
    """Health check endpoint."""
    try:
        # Start timing the request
        start_time = time.time()
        
        # Check Qdrant connection with dependency tracking
        qdrant_ok = await dependency_tracker.track_async(
            client.check_health(),
            name="check_qdrant_health",
            type_name="Qdrant",
            target="health_check"
        )
        
        # Get collection stats if connected
        stats = None
        if qdrant_ok:
            stats = await dependency_tracker.track_async(
                client.get_collection_stats(),
                name="get_collection_stats",
                type_name="Qdrant",
                target="collection_stats"
            )
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000
        
        # Track metric for health check time
        monitor.track_metric("health_check_time", duration)
        
        # Track event for health status
        monitor.track_event("health_check", {
            "qdrant_connected": str(qdrant_ok),
            "status": "healthy" if qdrant_ok else "unhealthy",
            "duration_ms": str(int(duration))
        })
        
        return HealthResponse(
            status="healthy" if qdrant_ok else "unhealthy",
            qdrant_connected=qdrant_ok,
            collection_stats=stats
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        # Track the exception
        monitor.track_exception({
            "error": str(e),
            "phase": "health_check"
        })
        
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
    """Search for documents similar to the query with dynamic threshold."""
    try:
        # Start timing the request
        start_time = time.time()
        
        # Log the search request
        logger.info(f"Search request received: query='{request.query}', limit={request.limit}")
        
        # Dynamic threshold: try higher thresholds first, fallback to lower ones
        thresholds_to_try = [0.7, 0.6, 0.5, 0.4, 0.3]
        
        # If user specified a custom threshold, use it
        if request.score_threshold is not None:
            thresholds_to_try = [request.score_threshold]
        
        results = None
        used_threshold = None
        
        for threshold in thresholds_to_try:
            # Track the search operation with the current threshold
            search_properties = {
                "query": request.query,
                "limit": str(request.limit),
                "threshold": str(threshold),
                "use_ai_summary": str(request.use_ai_summary)
            }
            
            # Execute search with dependency tracking
            results = await dependency_tracker.track_async(
                client.search_documents(
                    query=request.query,
                    limit=request.limit,
                    score_threshold=threshold,
                    use_ai_summary=request.use_ai_summary
                ),
                name="search_documents",
                type_name="Qdrant",
                target="vector_search",
                properties=search_properties
            )
            
            if results and len(results) > 0:
                used_threshold = threshold
                break
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000
        
        # Track metrics
        monitor.track_metric("search_latency", duration, {
            "query": request.query,
            "threshold_used": str(used_threshold)
        })
        
        if results:
            monitor.track_metric("search_results_count", len(results), {
                "query": request.query
            })
        
        # Track the search event
        monitor.track_event("search_completed", {
            "query": request.query,
            "limit": str(request.limit),
            "results_count": str(len(results) if results else 0),
            "threshold_used": str(used_threshold),
            "duration_ms": str(int(duration))
        })
        
        if results is not None and len(results) > 0:
            logger.info(f"Search completed: query='{request.query}', found {len(results)} results with threshold {used_threshold}")
            return SearchResponse(
                results=results,
                total_count=len(results),
                query=request.query,
                used_threshold=used_threshold  # Add this to show which threshold was used
            )
        else:
            logger.warning(f"No results found: query='{request.query}' with any threshold")
            
            # Track the no results event
            monitor.track_event("search_no_results", {
                "query": request.query,
                "thresholds_tried": str(thresholds_to_try)
            })
            
            raise HTTPException(status_code=404, detail="No results found with any threshold")
            
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        
        # Track the exception
        monitor.track_exception({
            "query": request.query,
            "error": str(e)
        })
        
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

# Add the new summarize endpoint
@app.post("/summarize")
async def summarize_news(
    request: SummaryRequest,
    client: QdrantClientWrapper = Depends(get_qdrant_client)
):
    """Generate a comprehensive summary of news articles related to a query."""
    try:
        # Start timing the request
        start_time = time.time()
        
        logger.info(f"Summarizing news: query='{request.query}', limit={request.limit}, use_cache={request.use_cache}")
        
        # Track event for summary request
        monitor.track_event("summary_request", {
            "query": request.query,
            "limit": str(request.limit),
            "format": request.format,
            "use_cache": str(request.use_cache)
        })
        
        # First, search for articles using the existing search functionality
        thresholds_to_try = [0.7, 0.6, 0.5, 0.4, 0.3]
        
        # If user specified a custom threshold, use it
        if request.score_threshold is not None:
            thresholds_to_try = [request.score_threshold]
        
        # Try thresholds until we get results
        search_results = None
        used_threshold = None
        
        try:
            for threshold in thresholds_to_try:
                logger.info(f"Trying search with threshold: {threshold}")
                
                # Track the search operation with the current threshold
                search_properties = {
                    "query": request.query,
                    "limit": str(request.limit),
                    "threshold": str(threshold),
                    "for_summary": "true"
                }
                
                # Execute search directly
                search_results = await client.search_documents(
                    query=request.query,
                    limit=request.limit,
                    score_threshold=threshold
                )
                
                if search_results and len(search_results) > 0:
                    used_threshold = threshold
                    break
            
            logger.info(f"Search results: {search_results is not None}, count: {len(search_results) if search_results else 0}")
            
            if not search_results or len(search_results) == 0:
                logger.warning(f"No search results found for query: {request.query}")
                
                # Track the no results event
                monitor.track_event("summary_no_results", {
                    "query": request.query,
                    "thresholds_tried": str(thresholds_to_try)
                })
                
                raise HTTPException(status_code=404, detail="No news articles found for the query")
            
            logger.info(f"Found {len(search_results)} articles with threshold {used_threshold}")
            
            # Track metric for article count
            monitor.track_metric("summary_article_count", len(search_results), {
                "query": request.query
            })
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            
            # Track the exception
            monitor.track_exception({
                "query": request.query,
                "error": str(e),
                "phase": "search_for_summary"
            })
            
            raise HTTPException(status_code=500, detail=f"Error during search: {str(e)}")
            
        # Generate summary
        try:
            logger.info(f"Generating summary for {len(search_results)} articles")
            
            # Start timing summary generation
            summary_start_time = time.time()
            
            # Generate summary directly without dependency tracking
            summary_result = await summarizer.generate_summary(
                articles=search_results,
                query=request.query,
                use_cache=request.use_cache
            )
            
            # Add query and article count
            summary_result["query"] = request.query
            summary_result["articleCount"] = len(search_results)
            
            # Calculate summary generation duration
            summary_duration = (time.time() - summary_start_time) * 1000
            
            # Track metric for summary generation time
            monitor.track_metric("summary_generation_time", summary_duration, {
                "query": request.query,
                "article_count": str(len(search_results))
            })
            
            # Track sentiment and impact metrics
            if "sentiment" in summary_result:
                sentiment = summary_result["sentiment"].get("overall", "neutral")
                sentiment_score = summary_result["sentiment"].get("score", 50)
                
                monitor.track_metric("summary_sentiment_score", sentiment_score, {
                    "query": request.query,
                    "sentiment": sentiment
                })
            
            if "impactLevel" in summary_result:
                monitor.track_event("summary_impact", {
                    "query": request.query,
                    "impact_level": summary_result["impactLevel"]
                })
            
            # Track currency pairs mentioned
            if "currencyPairRankings" in summary_result:
                currency_pairs = [pair.get("pair", "") for pair in summary_result["currencyPairRankings"]]
                
                monitor.track_event("currency_pairs_analyzed", {
                    "query": request.query,
                    "pairs": str(currency_pairs)
                })
            
            # Calculate total duration
            total_duration = (time.time() - start_time) * 1000
            
            # Track metric for total processing time
            monitor.track_metric("summary_total_time", total_duration, {
                "query": request.query
            })
            
            # Track summary completion event
            monitor.track_event("summary_completed", {
                "query": request.query,
                "article_count": str(len(search_results)),
                "format": request.format,
                "duration_ms": str(int(total_duration))
            })
            
            # Check if text format was requested
            if request.format and request.format.lower() == "text":
                # Return formatted text if available
                if "formatted_text" in summary_result:
                    from fastapi.responses import PlainTextResponse
                    formatted_text = summary_result["formatted_text"]
                    
                    # No additional formatting needed as the system prompt has been updated
                    # to match the exact desired format
                    
                    return PlainTextResponse(content=formatted_text)
            
            return summary_result
        except Exception as e:
            logger.error(f"Error during summary generation: {e}")
            
            # Track the exception
            monitor.track_exception({
                "query": request.query,
                "error": str(e),
                "phase": "summary_generation"
            })
            
            raise HTTPException(status_code=500, detail=f"Error during summary generation: {str(e)}")
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        
        # Track the exception
        monitor.track_exception({
            "query": request.query,
            "error": str(e),
            "phase": "summary_overall"
        })
        
        raise HTTPException(status_code=500, detail=str(e))

# Add endpoint for summary cache stats
@app.get("/summarize/stats")
async def get_summary_stats():
    """Get statistics about the summary cache."""
    try:
        return summarizer.get_cache_stats()
    except Exception as e:
        logger.error(f"Error getting summary stats: {e}")
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
            "stats": "/documents/stats"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8000))
    
    # Log application startup
    logger.info(f"Starting NewsRagnarok API on port {port}")
    logger.info(f"Monitoring enabled: {monitor.enabled}")
    
    # Set application metadata for monitoring
    monitor.set_custom_properties({
        "app_version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "host": os.getenv("COMPUTERNAME", "unknown"),
    })
    
    # Run the application
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
