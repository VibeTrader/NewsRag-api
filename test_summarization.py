"""
Simple test script for the summarization service.
"""
import asyncio
import json
import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")

async def test_summarization():
    """Test the summarization endpoint."""
    print("\n=== Testing Summarization Service ===\n")
    
    # Test data
    test_query = "latest forex news"
    
    # Build the request
    url = f"{API_BASE_URL}/summarize"
    data = {
        "query": test_query,
        "limit": 10,
        "use_cache": False  # Disable cache for testing
    }
    
    print(f"Sending request to {url}")
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    try:
        # Make the request
        response = requests.post(url, json=data)
        
        # Check status code
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            # Parse the response
            result = response.json()
            
            # Print summary info
            print("\n=== Summary Results ===\n")
            print(f"Summary: {result.get('summary', 'No summary available')}")
            print(f"Impact Level: {result.get('impactLevel', 'N/A')}")
            print(f"Sentiment: {result.get('sentiment', {}).get('overall', 'N/A')} ({result.get('sentiment', {}).get('score', 0)})")
            
            print("\nKey Points:")
            for point in result.get("keyPoints", []):
                print(f"- {point}")
            
            # Print currency pair rankings
            if "currencyPairRankings" in result and result["currencyPairRankings"]:
                print("\nCurrency Pair Rankings:")
                for pair in result["currencyPairRankings"]:
                    print(f"- {pair.get('pair', 'N/A')} (Rank: {pair.get('rank', 0)}/{pair.get('maxRank', 10)})")
                    print(f"  Fundamental Outlook: {pair.get('fundamentalOutlook', 0)}%")
                    print(f"  Sentiment Outlook: {pair.get('sentimentOutlook', 0)}%")
                    print(f"  Rationale: {pair.get('rationale', 'N/A')}")
                    print()
            
            # Print market conditions
            if "marketConditions" in result:
                print(f"\nMarket Conditions: {result['marketConditions']}")
                
            # Print risk assessment
            if "riskAssessment" in result:
                print("\nRisk Assessment:")
                risk = result["riskAssessment"]
                print(f"- Primary Risk: {risk.get('primaryRisk', 'N/A')}")
                print(f"- Correlation Risk: {risk.get('correlationRisk', 'N/A')}")
                print(f"- Volatility Potential: {risk.get('volatilityPotential', 'N/A')}")
                
            # Print trade management guidelines
            if "tradeManagementGuidelines" in result and result["tradeManagementGuidelines"]:
                print("\nTrade Management Guidelines:")
                for guideline in result["tradeManagementGuidelines"]:
                    print(f"- {guideline}")
            
            # Print article count
            print(f"\nArticles analyzed: {result.get('articleCount', 0)}")
            
            # Test successful
            print("\nTest successful!")
            return True
        else:
            # Handle error response
            print(f"Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"Exception: {e}")
        return False

async def test_cache_stats():
    """Test the cache stats endpoint."""
    print("\n=== Testing Cache Stats ===\n")
    
    url = f"{API_BASE_URL}/summarize/stats"
    
    try:
        # Make the request
        response = requests.get(url)
        
        # Check status code
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            # Parse the response
            result = response.json()
            
            # Print cache stats
            print("\nCache Statistics:")
            print(f"Size: {result.get('size', 0)} / {result.get('max_size', 0)}")
            print(f"Hit Rate: {result.get('hit_rate', '0%')}")
            print(f"Hits: {result.get('hits', 0)}")
            print(f"Misses: {result.get('misses', 0)}")
            
            # Test successful
            print("\nTest successful!")
            return True
        else:
            # Handle error response
            print(f"Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"Exception: {e}")
        return False

async def main():
    """Run all tests."""
    # Test summarization
    summarize_result = await test_summarization()
    
    # Test cache stats
    cache_stats_result = await test_cache_stats()
    
    # Print overall result
    print("\n=== Test Results ===\n")
    print(f"Summarization: {'PASS' if summarize_result else 'FAIL'}")
    print(f"Cache Stats: {'PASS' if cache_stats_result else 'FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())