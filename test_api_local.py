#!/usr/bin/env python3
"""
Local test of the API client with current Qdrant data
"""

import asyncio
import os
from dotenv import load_dotenv
import sys

# Add the NewsRag-api directory to the path
sys.path.append('NewsRag-api')

from clients.qdrant_client import QdrantClientWrapper

# Load environment variables
load_dotenv()

async def test_api_client():
    """Test the API client locally"""
    print("🧪 Testing API Client Locally...")
    
    try:
        # Initialize client
        client = QdrantClientWrapper()
        
        # Test health check
        print("\n1. Testing health check...")
        health_ok = await client.check_health()
        print(f"   Health: {'✅ OK' if health_ok else '❌ Failed'}")
        
        # Test collection stats
        print("\n2. Testing collection stats...")
        stats = await client.get_collection_stats()
        if stats:
            print(f"   Collection: {stats['collection_name']}")
            print(f"   Points: {stats['points_count']}")
            print(f"   Status: {stats['status']}")
            print(f"   Model: {stats['embedding_model']}")
        else:
            print("   ❌ Could not get stats")
        
        # Test search
        print("\n3. Testing search...")
        search_results = await client.search_documents(
            query="forex trading",
            limit=2,
            score_threshold=0.5
        )
        
        if search_results:
            print(f"   Found {len(search_results)} results")
            for i, result in enumerate(search_results):
                payload = result['payload']
                print(f"   Result {i+1}:")
                print(f"     Score: {result['score']:.3f}")
                print(f"     Title: {payload['title'][:50]}...")
                print(f"     Source: {payload['source']}")
                print(f"     Author: {payload['author']}")
                print(f"     Content Length: {len(payload['content'])} chars")
        else:
            print("   ❌ No search results")
        
        # Close client
        await client.close()
        
    except Exception as e:
        print(f"❌ Error testing API client: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_client())
