"""
Quick test script for the API.
"""

import requests
import json

def test_api():
    """Test the API endpoints."""
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    print("Testing health endpoint...")
    response = requests.get(f"{base_url}/health")
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    
    # Test summarize endpoint
    print("Testing summarize endpoint...")
    payload = {
        "query": "forex news",
        "limit": 5,
        "format": "json"
    }
    
    try:
        response = requests.post(f"{base_url}/summarize", json=payload)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("Summary generated successfully!")
            result = response.json()
            print(f"Summary: {result.get('summary', '')[:200]}...")
            print(f"Currency pairs: {[pair['pair'] for pair in result.get('currencyPairRankings', [])]}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
