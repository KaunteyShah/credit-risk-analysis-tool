#!/usr/bin/env python3
"""
Test Modular Functionality - Comprehensive API and Frontend Testing
"""
import requests
import json
import time
from threading import Thread
from new_modular_ui_app import create_new_modular_ui_app

def run_server():
    """Run Flask server in background"""
    app = create_new_modular_ui_app()
    app.run(host='127.0.0.1', port=5003, debug=False, use_reloader=False)

def wait_for_server(url='http://localhost:5003', timeout=60):
    """Wait for server to be ready"""
    print(f"🔄 Waiting for server at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/api/modular/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Server ready after {time.time() - start_time:.1f} seconds")
                return True
        except:
            pass
        time.sleep(1)
    print(f"❌ Server not ready after {timeout} seconds")
    return False

def test_api_endpoints():
    """Test all critical API endpoints"""
    base_url = "http://localhost:5003/api/modular"
    
    tests = [
        ("Health Check", f"{base_url}/health"),
        ("Filter Options", f"{base_url}/filter-options"),
        ("Companies List", f"{base_url}/companies"),
        ("Company Details", f"{base_url}/companies/0"),
    ]
    
    results = {}
    
    for test_name, url in tests:
        try:
            print(f"🧪 Testing {test_name}...")
            response = requests.get(url, timeout=30)  # Increased timeout
            
            results[test_name] = {
                'status': response.status_code,
                'success': response.status_code == 200,
                'content_type': response.headers.get('Content-Type', ''),
                'data_preview': response.text[:200] if response.text else 'No content'
            }
            
            if response.status_code == 200:
                print(f"✅ {test_name} - OK")
                if 'application/json' in response.headers.get('Content-Type', ''):
                    data = response.json()
                    if test_name == "Companies List":
                        companies = data.get('companies', [])
                        print(f"   📊 Companies loaded: {len(companies)}")
                    elif test_name == "Company Details":
                        print(f"   🏢 Company: {data.get('company_name', 'Unknown')}")
                else:
                    print(f"   ⚠️  Non-JSON response: {response.headers.get('Content-Type')}")
            else:
                print(f"❌ {test_name} - Status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"⏰ {test_name} - Timeout (server still initializing)")
            results[test_name] = {'success': False, 'error': 'Timeout'}
        except Exception as e:
            print(f"❌ {test_name} - Error: {e}")
            results[test_name] = {'success': False, 'error': str(e)}
    
    return results

def main():
    print("🚀 Starting Modular Architecture Test")
    print("="*50)
    
    # Start server
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to be ready
    if wait_for_server():
        print("\n📋 Testing API Endpoints...")
        results = test_api_endpoints()
        
        print("\n📊 Test Results Summary:")
        print("="*50)
        for test_name, result in results.items():
            status = "✅ PASS" if result.get('success') else "❌ FAIL"
            print(f"{test_name}: {status}")
            if not result.get('success'):
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Overall assessment
        passed_tests = sum(1 for result in results.values() if result.get('success'))
        total_tests = len(results)
        print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All systems operational!")
        else:
            print("⚠️  Some issues detected - see details above")
    else:
        print("❌ Server failed to start within timeout period")

if __name__ == "__main__":
    main()