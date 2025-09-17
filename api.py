# Import patch BEFORE any other imports
import opentelemetry_patch

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import asyncio
import time
import traceback
from loguru import logger
from dotenv import load_dotenv

# Import our Qdrant client
from clients.qdrant_client import QdrantClientWrapper

# Import summarization module
from utils.summarization import NewsSummarizer

# Import monitoring modules
from utils.monitoring import AppInsightsMonitor
from utils.monitoring.dependency_tracker import DependencyTracker
from utils.monitoring import LangfuseMonitor
from utils.monitoring.langfuse import StatefulTraceClient
from utils.monitoring import LangChainMonitoring
from utils.summarization.news_summarizer import NewsSummarizer

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

# Replace the general summarizer with the enhanced financial summarizer
logger.info("enhanced financial summarizer")
summarizer = NewsSummarizer()
logger.info("Enhanced financial summarizer integration complete")

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

# Initialize monitoring
try:
    # Initialize Langfuse monitoring
    from utils.monitoring.langfuse import SimpleLangfuseMonitor
    langfuse_monitor = SimpleLangfuseMonitor(app)
    
    # Initialize LangChain monitoring if available
    from utils.monitoring import LangChainMonitoring
    langchain_monitor = LangChainMonitoring()
except ImportError as e:
    logger.warning(f"Monitoring initialization error: {e}")
    langfuse_monitor = None
    langchain_monitor = None



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
            
            # Create a Langfuse trace if not already created
            trace = langfuse_monitor.create_trace(
                name=f"summarize:{request.query}",
                metadata={
                    "query": request.query,
                    "article_count": len(search_results),
                    "threshold_used": used_threshold,
                    "format": request.format,
                    "duration_ms": summary_duration,
                    "use_cache": request.use_cache
                },
                tags=["summarize", "forex"],
                input=request.query,  # Explicitly set input at trace level
                output=summary_result.get("formatted_text", summary_result.get("summary", ""))  # Explicitly set output at trace level
            )
            
            # Track comprehensive Langfuse metrics
            if langfuse_monitor.enabled:
                try:
                    # Estimate token usage
                    prompt_tokens = 0
                    completion_tokens = 0
                    
                    # Estimate tokens for articles
                    for article in search_results:
                        content = article.get("payload", {}).get("content", "")
                        prompt_tokens += langfuse_monitor.count_tokens(content)
                    
                    # Estimate tokens for summary
                    if "formatted_text" in summary_result:
                        completion_tokens = langfuse_monitor.count_tokens(summary_result["formatted_text"])
                    
                    # Extract proper summary content for output
                    summary_output = ""
                    if "formatted_text" in summary_result:
                        summary_output = summary_result["formatted_text"]
                    elif "summary" in summary_result:
                        summary_output = summary_result["summary"]
                    
                    # Track comprehensive Langfuse metrics
                    currency_pairs = [pair.get("pair", "") for pair in summary_result.get("currencyPairRankings", [])]
                    langfuse_monitor.track_span(
                        trace=trace,
                        name="summarization_metrics",
                        metadata={
                            "processing_time_ms": int(summary_duration),
                            "token_usage": {
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens,
                                "total_tokens": prompt_tokens + completion_tokens
                            },
                            "cache_hit": request.use_cache,
                            "article_count": len(search_results),
                            "currency_pairs": currency_pairs,
                            "sentiment_score": summary_result.get("sentiment", {}).get("score", 0),
                            "impact_level": summary_result.get("impactLevel", "UNKNOWN")
                        },
                        input=request.query,  # Pass input as separate parameter
                        output=summary_output  # Pass output as separate parameter
                    )
                    
                    # Explicitly flush data to ensure it's sent
                    logger.info("Explicitly flushing Langfuse data")
                    langfuse_monitor.flush()
                except Exception as e:
                    logger.warning(f"Error tracking Langfuse metrics: {e}")
                    import traceback
                    logger.warning(f"Langfuse metrics error traceback: {traceback.format_exc()}")
            
            # Track standard metrics
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
            
            # Add explicit flush for Langfuse
            try:
                if langfuse_monitor and langfuse_monitor.enabled:
                    logger.info("Explicitly flushing Langfuse data")
                    langfuse_monitor.flush()
            except Exception as e:
                logger.warning(f"Error flushing Langfuse data: {e}")
            
            return summary_result
        except Exception as e:
            logger.error(f"Error during summary generation: {e}")
            
            # Track error in Langfuse
            trace = langfuse_monitor.create_trace(
                name=f"summarize_error:{request.query}",
                metadata={
                    "query": request.query,
                    "error": str(e),
                    "error_type": str(type(e)),
                    "phase": "summary_generation"
                },
                tags=["summarize", "error"]
            )
            
            if trace:
                langfuse_monitor.track_span(
                    trace=trace,
                    name="error",
                    metadata={
                        "error": str(e),
                        "error_type": str(type(e)),
                        "traceback": str(traceback.format_exc())
                    },
                    status="error",
                    input=request.query,
                    output=f"Error: {str(e)}"
                )
            
            # Track exception in AppInsights
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
            "stats": "/documents/stats",
            "summarize": "/summarize",
            "monitoring": "/monitoring",
            "langfuse_test": "/langfuse-debug"
        }
    }

# Add monitoring dashboard endpoint
@app.get("/monitoring")
async def monitoring_dashboard():
    """Monitoring dashboard with links to observability tools."""
    # Get App Insights stats
    app_insights_enabled = monitor.enabled
    app_insights_url = None
    if app_insights_enabled:
        app_insights_url = f"https://portal.azure.com/#blade/AppInsightsExtension/UsageUsageBlade/ComponentId/{monitor.instrumentation_key}"
    
    # Get Langfuse stats
    langfuse_enabled = langfuse_monitor.enabled
    langfuse_url = None
    if langfuse_enabled:
        langfuse_url = f"{langfuse_monitor.langfuse_host}/project/{langfuse_monitor.project_name}"
    
    return {
        "app_insights": {
            "enabled": app_insights_enabled,
            "dashboard_url": app_insights_url
        },
        "langfuse": {
            "enabled": langfuse_enabled,
            "dashboard_url": langfuse_url,
            "project": langfuse_monitor.project_name if langfuse_enabled else None
        },
        "monitoring_status": "healthy" if (app_insights_enabled or langfuse_enabled) else "limited"
    }

# Add performance metrics endpoint
@app.get("/performance")
async def performance_metrics():
    """Get performance metrics for the API."""
    try:
        # Get cache stats
        cache_stats = summarizer.get_cache_stats()
        
        # Get Langfuse status
        langfuse_status = {
            "enabled": langfuse_monitor.enabled,
            "host": langfuse_monitor.langfuse_host if hasattr(langfuse_monitor, "langfuse_host") else None,
            "has_client": hasattr(langfuse_monitor, "langfuse") and langfuse_monitor.langfuse is not None,
            "project": langfuse_monitor.project_name if hasattr(langfuse_monitor, "project_name") else None
        }
        
        # Get current configuration
        api_config = {
            "max_summary_articles": int(os.getenv("MAX_SUMMARY_ARTICLES", "15")),
            "max_article_content_chars": int(os.getenv("MAX_ARTICLE_CONTENT_CHARS", "1500")),
            "llm_timeout": int(os.getenv("LLM_TIMEOUT", "120")),
            "temperature": float(os.getenv("TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("MAX_TOKENS", "4000")),
            "model": os.getenv("AZURE_OPENAI_DEPLOYMENT", "Unknown")
        }
        
        # Return combined metrics
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "cache": cache_stats,
            "langfuse": langfuse_status,
            "config": api_config,
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Import the Langfuse debugging endpoint
from langfuse_test_endpoint import router as langfuse_test_router

# Add the Langfuse testing router
app.include_router(langfuse_test_router, prefix="/langfuse-debug", tags=["diagnostics"])

# Add a direct endpoint for even more detailed Langfuse debugging
@app.get("/langfuse-direct-test")
async def langfuse_direct_test():
    """Directly test Langfuse connectivity by creating a test trace and event."""
    try:
        import langfuse_debug
        
        # Test connectivity
        connectivity_result = langfuse_debug.test_langfuse_connectivity()
        
        # Test direct API call
        direct_api_result = langfuse_debug.test_direct_trace_creation()
        
        # Compile results
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "connectivity": connectivity_result,
            "direct_api": direct_api_result,
            "environment_variables": {
                "LANGFUSE_HOST": os.getenv("LANGFUSE_HOST"),
                "LANGFUSE_PUBLIC_KEY_EXISTS": bool(os.getenv("LANGFUSE_PUBLIC_KEY")),
                "LANGFUSE_SECRET_KEY_EXISTS": bool(os.getenv("LANGFUSE_SECRET_KEY")),
                "PROJECT_NAME": os.getenv("PROJECT_NAME", "newsragnarok")
            }
        }
    except Exception as e:
        logger.error(f"Error in direct Langfuse test: {e}")
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
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

@app.get("/test-langfuse")
async def test_langfuse_connection():
    """Test the Langfuse connection."""
    try:
        # Get Langfuse config details
        langfuse_config = {
            "host": langfuse_monitor.langfuse_host if hasattr(langfuse_monitor, "langfuse_host") else os.getenv("LANGFUSE_HOST"),
            "public_key": os.getenv("LANGFUSE_PUBLIC_KEY", "")[:5] + "..." if os.getenv("LANGFUSE_PUBLIC_KEY") else None,
            "secret_key": os.getenv("LANGFUSE_SECRET_KEY", "")[:5] + "..." if os.getenv("LANGFUSE_SECRET_KEY") else None,
            "enabled": langfuse_monitor.enabled,
            "client_initialized": hasattr(langfuse_monitor, "langfuse") and langfuse_monitor.langfuse is not None,
            "project": langfuse_monitor.project_name if hasattr(langfuse_monitor, "project_name") else os.getenv("PROJECT_NAME", "newsragnarok")
        }
        
        # Log a test event
        event_id = langfuse_monitor.log_event(
            name="api_test_connection",
            metadata={"source": "api_test_endpoint", "timestamp": time.time()}
        )
        
        # Create a test trace with explicit input/output fields
        trace_id = langfuse_monitor.create_trace(
            name="api_test_trace",
            metadata={"source": "api_test_endpoint", "timestamp": time.time()},
            tags=["test", "api"],
            input="Test input data",  # Add explicit input
            output="Test output data"  # Add explicit output
        )
        
        # Add a span to the trace with explicit input/output
        span_id = langfuse_monitor.track_span(
            trace=trace_id,
            name="connection_test",
            metadata={"status": "success"},
            input="Test span input",  # Add explicit input
            output="Test span output"  # Add explicit output
        )
        
        # Log a test LLM generation
        generation_id = langfuse_monitor.log_llm_generation(
            model="test-model",
            prompt="Test prompt",
            completion="Test completion",
            token_count={
                "prompt_tokens": 2,
                "completion_tokens": 2,
                "total_tokens": 4
            }
        )
        
        # Force flush data to Langfuse
        try:
            logger.info("Explicitly flushing Langfuse data")
            langfuse_monitor.flush()
        except Exception as flush_error:
            logger.error(f"Error flushing Langfuse data: {flush_error}")
        
        # Return detailed status
        return {
            "status": "success", 
            "message": "Langfuse connection test completed",
            "config": langfuse_config,
            "details": {
                "event_id": event_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "generation_id": generation_id,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error testing Langfuse connection: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "error", 
            "message": f"Langfuse connection test failed: {str(e)}",
            "error_type": str(type(e)),
            "traceback": traceback.format_exc()
        }
