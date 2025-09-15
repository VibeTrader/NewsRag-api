"""
Patch script to update the test_langfuse_connection function in the API.
"""

import sys
import os
import re

def patch_api_file():
    """Patch the API file with the new test_langfuse_connection implementation."""
    api_file_path = "api.py"
    
    # Read the API file
    with open(api_file_path, "r") as f:
        content = f.read()
    
    # Define the pattern to match the old test_langfuse_connection function
    pattern = r'@app\.get\("/test-langfuse"\)\nasync def test_langfuse_connection\(\):\n.*?return \{"status": "error", "message": "Langfuse connection test failed"\}'
    
    # Define the new implementation
    new_implementation = '''@app.get("/test-langfuse")
async def test_langfuse_connection():
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
        return {"status": "error", "message": f"Langfuse connection test failed: {str(e)}"}'''
    
    # Replace the old implementation with the new one
    new_content = re.sub(pattern, new_implementation, content, flags=re.DOTALL)
    
    # Write the updated content back to the file
    with open(api_file_path, "w") as f:
        f.write(new_content)
    
    print("API file updated successfully!")

if __name__ == "__main__":
    # Change to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    patch_api_file()