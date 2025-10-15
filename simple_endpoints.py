# Add this simple health endpoint to your api.py right after the imports
# This will work even if your main services aren't fully initialized

@app.get("/health/simple")
async def simple_health_check():
    """Simple health check that doesn't depend on external services."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "region": os.getenv("DEPLOYMENT_REGION", "unknown"),
        "version": "1.0.0"
    }

# Also add a basic root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "NewsRag API is running",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "region": os.getenv("DEPLOYMENT_REGION", "unknown"),
        "health_endpoint": "/health/simple"
    }