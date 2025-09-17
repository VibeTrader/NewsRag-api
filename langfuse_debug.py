"""
Langfuse connectivity testing module for NewsRagnarok API.
"""

import os
import traceback
import requests
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_langfuse_connectivity():
    """Test basic connectivity to Langfuse servers."""
    langfuse_host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    langfuse_api_host = "https://api.us.langfuse.com"
    
    # If we're using EU endpoint, adjust API host
    if "eu.cloud.langfuse.com" in langfuse_host:
        langfuse_api_host = "https://api.eu.langfuse.com"
    
    results = {
        "connectivity_tests": [],
        "environment": {},
        "timestamp": datetime.now().isoformat()
    }
    
    # Check environment variables
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    project_name = os.getenv("PROJECT_NAME", "newsragnarok")
    
    # Add environment info to results
    results["environment"] = {
        "host": langfuse_host,
        "has_public_key": bool(public_key),
        "public_key_prefix": public_key[:8] + "..." if public_key else None,
        "has_secret_key": bool(secret_key),
        "secret_key_prefix": secret_key[:8] + "..." if secret_key else None,
        "project_name": project_name
    }
    
    # Test connectivity to dashboard
    try:
        response = requests.get(
            f"{langfuse_host}/api/health", 
            timeout=5,
            headers={"Accept": "application/json"}
        )
        results["connectivity_tests"].append({
            "endpoint": f"{langfuse_host}/api/health",
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response": str(response.text)[:100] if response.text else None
        })
    except Exception as e:
        results["connectivity_tests"].append({
            "endpoint": f"{langfuse_host}/api/health",
            "error": str(e),
            "error_type": str(type(e)),
            "success": False
        })
    
    # Test connectivity to API endpoint
    try:
        response = requests.get(
            f"{langfuse_api_host}/health", 
            timeout=5,
            headers={"Accept": "application/json"}
        )
        results["connectivity_tests"].append({
            "endpoint": f"{langfuse_api_host}/health",
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response": str(response.text)[:100] if response.text else None
        })
    except Exception as e:
        results["connectivity_tests"].append({
            "endpoint": f"{langfuse_api_host}/health",
            "error": str(e),
            "error_type": str(type(e)),
            "success": False
        })
    
    # Try a simple auth test if we have credentials
    if public_key and secret_key:
        try:
            response = requests.get(
                f"{langfuse_api_host}/auth-test",
                timeout=5,
                headers={
                    "Accept": "application/json",
                    "X-Langfuse-Public-Key": public_key,
                    "X-Langfuse-Secret-Key": secret_key
                }
            )
            results["connectivity_tests"].append({
                "endpoint": f"{langfuse_api_host}/auth-test",
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
                "response": str(response.text)[:100] if response.text else None
            })
        except Exception as e:
            results["connectivity_tests"].append({
                "endpoint": f"{langfuse_api_host}/auth-test",
                "error": str(e),
                "error_type": str(type(e)),
                "success": False
            })
    
    return results


def check_langfuse_sdk():
    """Check installed Langfuse SDK version."""
    try:
        import importlib.metadata
        langfuse_version = importlib.metadata.version("langfuse")
        
        # Try to import key components to verify functionality
        from langfuse import Langfuse
        from langfuse.client import LangfuseClient
        
        # Try creating a minimal client to check for import issues
        try:
            client = Langfuse(
                public_key="test_pub",
                secret_key="test_sec",
                host="https://us.cloud.langfuse.com"
            )
            client_works = True
        except Exception as e:
            client_works = False
            client_error = str(e)
        
        return {
            "version": langfuse_version,
            "client_import_works": True,
            "client_creation_works": client_works,
            "client_error": client_error if not client_works else None
        }
    except ImportError:
        return {
            "version": "not_installed",
            "client_import_works": False
        }
    except Exception as e:
        return {
            "error": str(e),
            "error_type": str(type(e))
        }


def test_direct_trace_creation():
    """Try to create a trace directly using requests."""
    try:
        langfuse_host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
        api_host = "https://api.us.langfuse.com"
        
        if "eu.cloud.langfuse.com" in langfuse_host:
            api_host = "https://api.eu.langfuse.com"
        
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        project_name = os.getenv("PROJECT_NAME", "newsragnarok")
        
        if not public_key or not secret_key:
            return {
                "success": False,
                "error": "Missing API keys"
            }
        
        # Create a simple trace
        trace_data = {
            "name": "direct_api_test",
            "projectName": project_name,
            "metadata": {
                "test_time": datetime.now().isoformat(),
                "source": "direct_api_call"
            },
            "tags": ["debug", "test"],
            "input": "Test input",
            "output": "Test output"
        }
        
        response = requests.post(
            f"{api_host}/api/public/traces",
            json=trace_data,
            headers={
                "Content-Type": "application/json",
                "X-Langfuse-Public-Key": public_key,
                "X-Langfuse-Secret-Key": secret_key
            },
            timeout=10
        )
        
        return {
            "success": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "response": response.text if response.text else None,
            "trace_data": trace_data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": str(type(e)),
            "trace": traceback.format_exc()
        }
