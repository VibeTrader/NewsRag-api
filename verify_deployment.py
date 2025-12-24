import requests
import json
import time

BASE_URL = "https://newsrag-api-prod-global-ftheascbdfh9efe8.z03.azurefd.net"

def test_endpoint(name, method, url, **kwargs):
    print(f"\n--- Testing {name} ---")
    print(f"URL: {url}")
    try:
        start = time.time()
        if method == "GET":
            response = requests.get(url, **kwargs)
        elif method == "POST":
            response = requests.post(url, **kwargs)
        duration = time.time() - start
        
        print(f"Status: {response.status_code}")
        print(f"Time: {duration:.2f}s")
        
        if response.status_code == 200:
            print("✅ Success")
            try:
                print("Response:", json.dumps(response.json(), indent=2)[:500] + "...")
            except:
                print("Response:", response.text[:200])
        else:
            print("❌ Failed")
            print("Response:", response.text[:500])
            
    except Exception as e:
        print(f"❌ Error: {e}")

# 1. Test Simple Health (No dependencies)
test_endpoint("Simple Health", "GET", f"{BASE_URL}/health/simple")

# 2. Test Full Health (Checks env vars)
test_endpoint("Full Health", "GET", f"{BASE_URL}/health")

# 3. Test Summarize (Triggers Lazy LLM Init)
payload = {
  "query": "forex market analysis",
  "limit": 5, 
  "score_threshold": 0.3,
  "use_cache": False, # Force it to run
  "format": "json"
}
test_endpoint("Summarize (Triggers LLM)", "POST", f"{BASE_URL}/summarize", json=payload)
