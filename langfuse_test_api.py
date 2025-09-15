"""
Simple FastAPI app for testing Langfuse integration.
"""

from fastapi import FastAPI
import uvicorn
import time
import os
import sys
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from utils.monitoring.langfuse.simple_langfuse import SimpleLangfuseMonitor

# Load environment variables from .env file
load_dotenv()

# Print environment variables for debugging
for key, value in os.environ.items():
    if key.startswith("LANGFUSE_"):
        print(f"Environment variable: {key}={value[:3]}...{value[-3:]}")

# Initialize FastAPI app
app = FastAPI(
    title="Langfuse Test API",
    description="Simple API for testing Langfuse integration",
    version="1.0.0"
)

# Initialize Langfuse monitoring
langfuse_monitor = SimpleLangfuseMonitor(app)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Langfuse Test API",
        "version": "1.0.0",
        "endpoints": {
            "test": "/test-langfuse"
        }
    }

@app.get("/test-langfuse")
async def test_langfuse():
    """Test the Langfuse connection."""
    try:
        # Log a test event
        event_id = langfuse_monitor.log_event(
            name="api_test_connection",
            metadata={"source": "api_test_endpoint", "timestamp": time.time()}
        )
        
        # Create a test trace
        trace_id = langfuse_monitor.create_trace(
            name="api_test_trace",
            metadata={"source": "api_test_endpoint", "timestamp": time.time()},
            tags=["test", "api"]
        )
        
        # Add a span to the trace
        langfuse_monitor.track_span(
            trace=trace_id,
            name="connection_test",
            metadata={"status": "success"}
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
        
        # Flush data to Langfuse
        langfuse_monitor.flush()
        
        # Return success
        return {
            "status": "success", 
            "message": "Langfuse connection test successful",
            "details": {
                "event_id": event_id,
                "trace_id": trace_id,
                "generation_id": generation_id,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error testing Langfuse connection: {e}")
        return {"status": "error", "message": f"Langfuse connection test failed: {str(e)}"}

# Run the application
if __name__ == "__main__":
    # Use port 9624 (make sure it's different from your main API)
    port = 9624
    
    # Log application startup
    logger.info(f"Starting Langfuse Test API on port {port}")
    logger.info(f"Monitoring enabled: {langfuse_monitor.enabled}")
    
    # Run the application with explicit port
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
