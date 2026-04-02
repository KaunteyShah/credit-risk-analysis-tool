#!/usr/bin/env python3
"""
Pure Modular Architecture Test Script
Tests all modular endpoints to verify they work without fallbacks
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:5001"

def test_endpoint(method, endpoint, data=None, description=""):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    print(f"\n🧪 Testing: {method} {endpoint}")
    if description:
        print(f"   Description: {description}")
    
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
            
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success ({response.status_code}) - {response_time:.1f}ms")
            
            # Check if modular info is present
            if isinstance(result, dict) and 'modular_info' in result:
                modular_info = result['modular_info']
                print(f"   🏗️  Architecture: {modular_info.get('architecture', 'unknown')}")
                print(f"   🔄 Fallback Used: {modular_info.get('fallback_used', 'unknown')}")
                if 'service_type' in modular_info:
                    print(f"   🔧 Service: {modular_info['service_type']}")
            
            # Show relevant data counts
            if 'data' in result and isinstance(result['data'], list):
                print(f"   📊 Returned: {len(result['data'])} items")
            elif 'companies_loaded' in result.get('data', {}):
                print(f"   📊 Companies: {result['data']['companies_loaded']}")
                
            return True
        else:
            print(f"❌ Failed ({response.status_code}) - {response_time:.1f}ms")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Raw error: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed - Is the server running on {BASE_URL}?")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    print("🚀 Pure Modular Architecture Test Suite")
    print("=" * 50)
    print(f"Testing server: {BASE_URL}")
    print("Expected: 100% modular responses, no fallbacks")
    print("")
    
    tests = [
        ("GET", "/", "Home page with architecture info"),
        ("GET", "/api/modular/health", "Health check for modular components"),
        ("GET", "/api/modular/stats", "Architecture statistics"),
        ("GET", "/api/modular/companies?page=1&limit=5", "Get first 5 companies (paginated)"),
        ("GET", "/api/modular/companies/0", "Get company details with AI reasoning"),
        ("POST", "/api/modular/predict-sic", "SIC prediction for company", {"company_index": 0, "use_real_agents": False})
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        method, endpoint = test[0], test[1]
        description = test[2] if len(test) > 2 else ""
        data = test[3] if len(test) > 3 else None
        
        if test_endpoint(method, endpoint, data, description):
            passed += 1
    
    print(f"\n📊 TEST RESULTS")
    print(f"=" * 20)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Pure Modular Architecture Working!")
    else:
        print("⚠️  Some tests failed - Check server logs for details")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)