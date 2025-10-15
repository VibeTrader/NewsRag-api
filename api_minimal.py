# Minimal API for testing deployment
from fastapi import FastAPI
import os

# Create a simple FastAPI app for testing
app = FastAPI(title="NewsRag API - Debug Version")

@app.get("/")
async def root():
    return {
        "message": "NewsRag API is running",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "region": os.getenv("DEPLOYMENT_REGION", "unknown")
    }

@app.get("/health")
async def health_check():
    """Health endpoint for Traffic Manager"""
    return {
        "status": "healthy",
        "region": os.getenv("DEPLOYMENT_REGION", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "production")
    }

# For local testing
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)