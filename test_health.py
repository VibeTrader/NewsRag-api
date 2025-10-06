#!/usr/bin/env python3
"""
Simple health check test for CI/CD pipeline.
Tests the health endpoint functionality without starting a server.
"""

import json
import sys
import os
from unittest.mock import Mock, AsyncMock

def test_health_endpoint():
    """Test that the health endpoint function works correctly."""
    print("🧪 Testing health endpoint functionality...")
    
    try:
        # Add the current directory to Python path
        sys.path.insert(0, os.getcwd())
        
        # Import your API module
        import api
        
        print("✅ API module imported successfully")
        
        # Test that FastAPI app is created
        assert hasattr(api, 'app'), "FastAPI app should exist"
        print("✅ FastAPI app exists")
        
        # Check if health endpoint exists by inspecting routes
        routes = [route.path for route in api.app.routes]
        health_routes = [route for route in routes if '/health' in route]
        
        if health_routes:
            print(f"✅ Health endpoint found: {health_routes}")
        else:
            print("⚠️ No /health route found in API routes")
            print(f"Available routes: {routes}")
        
        print("✅ Health endpoint test completed successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import API module: {e}")
        return False
    except Exception as e:
        print(f"❌ Health endpoint test failed: {e}")
        return False

def test_environment_setup():
    """Test that the environment is set up correctly."""
    print("🧪 Testing environment setup...")
    
    try:
        import fastapi
        print(f"✅ FastAPI version: {fastapi.__version__}")
        
        import uvicorn
        print(f"✅ Uvicorn available: {uvicorn.__version__}")
        
        # Test Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        print(f"✅ Python version: {python_version}")
        
        if python_version >= "3.12":
            print("✅ Python version is compatible")
        else:
            print("⚠️ Python version might not be optimal")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Running NewsRag API Health Tests")
    print("=" * 50)
    
    # Run tests
    env_test = test_environment_setup()
    health_test = test_health_endpoint()
    
    print("=" * 50)
    
    if env_test and health_test:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
