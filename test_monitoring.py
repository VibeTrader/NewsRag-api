"""
Test script to verify Application Insights monitoring.
"""

import os
import requests
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API base URL - update this to your actual URL if running on a different port
BASE_URL = "http://localhost:8000"

def test_health_endpoint():
    """Test the health endpoint."""
    print("\n--- Testing Health Endpoint ---")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_search_endpoint():
    """Test the search endpoint."""
    print("\n--- Testing Search Endpoint ---")
    payload = {
        "query": "forex market",
        "limit": 5,
        "score_threshold": 0.3
    }
    try:
        response = requests.post(f"{BASE_URL}/search", json=payload)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {data['total_count']} results with threshold {data['used_threshold']}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_summarize_endpoint():
    """Test the summarize endpoint."""
    print("\n--- Testing Summarize Endpoint ---")
    payload = {
        "query": "forex market",
        "limit": 10,
        "format": "json"
    }
    try:
        response = requests.post(f"{BASE_URL}/summarize", json=payload)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Generated summary using {data['articleCount']} articles")
            print(f"Sentiment: {data['sentiment']['overall']}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def run_tests():
    """Run all tests."""
    print("=== NewsRagnarok API Monitoring Test ===")
    print(f"Using base URL: {BASE_URL}")
    
    # Check if we have a valid instrumentation key
    instrumentation_key = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")
    if not instrumentation_key or instrumentation_key == "00000000-0000-0000-0000-000000000000":
        print("\n⚠️ WARNING: Using dummy instrumentation key. Telemetry won't be sent to Application Insights.")
    else:
        print("\n✅ Using valid instrumentation key format.")
    
    # Run tests
    health_ok = test_health_endpoint()
    search_ok = test_search_endpoint()
    summary_ok = test_summarize_endpoint()
    
    # Print summary
    print("\n=== Test Results ===")
    print(f"Health endpoint: {'✅ Passed' if health_ok else '❌ Failed'}")
    print(f"Search endpoint: {'✅ Passed' if search_ok else '❌ Failed'}")
    print(f"Summarize endpoint: {'✅ Passed' if summary_ok else '❌ Failed'}")
    
    print("\nNext steps:")
    if instrumentation_key and instrumentation_key != "00000000-0000-0000-0000-000000000000":
        print("1. Check Application Insights portal for telemetry data")
        print("2. Wait a few minutes if data doesn't appear immediately")
        print("3. Check for any errors in the console output")
    else:
        print("1. Create an Application Insights resource in Azure Portal")
        print("2. Add the instrumentation key to your .env file")
        print("3. Restart the API and run this test again")

if __name__ == "__main__":
    run_tests()