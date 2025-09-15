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
            "monitoring": "/monitoring"
        }
    }