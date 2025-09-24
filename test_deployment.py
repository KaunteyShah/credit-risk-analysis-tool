#!/usr/bin/env python3
"""
Test script to check the deployed Azure application endpoints
"""
import requests
import json

# Your Azure app URL - replace with the actual URL
APP_URL = "https://credit-risk-analysis-prod-app-25h2ya.azurewebsites.net"

def test_endpoint(endpoint, method="GET", data=None):
    """Test an endpoint and return results"""
    try:
        url = f"{APP_URL}{endpoint}"
        print(f"\n🔍 Testing {method} {endpoint}")
        print(f"URL: {url}")
        
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            if endpoint == "/api/test":
                print(f"   Data loaded: {result.get('data_loaded')}")
                print(f"   Total companies: {result.get('total_companies')}")
            elif endpoint == "/api/data":
                print(f"   Total records: {result.get('total', 'N/A')}")
                print(f"   Data length: {len(result.get('data', []))}")
            else:
                print(f"   Response: {json.dumps(result, indent=2)[:500]}...")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Test all relevant endpoints"""
    print("🚀 Testing Azure deployment endpoints...")
    
    # Test basic connectivity
    test_endpoint("/health")
    test_endpoint("/api/test")
    
    # Test data endpoints
    test_endpoint("/api/data")
    test_endpoint("/api/data?limit=5")
    
    # Try data reload
    print("\n🔄 Attempting data reload...")
    test_endpoint("/api/data/reload", method="POST")
    
    # Test again after reload
    print("\n🔍 Testing after reload attempt...")
    test_endpoint("/api/test")
    test_endpoint("/api/data?limit=3")

if __name__ == "__main__":
    main()