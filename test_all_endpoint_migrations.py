"""
Comprehensive test suite for all API endpoint migrations
Tests modular architecture implementations against original fallback implementations
"""
import requests
import json
import time
import sys
import os

# Add project root to path for imports
sys.path.insert(0, '.')

def test_endpoint_migration(endpoint_url, test_name, request_data=None, method='GET'):
    """Test an endpoint and measure performance"""
    print(f"\n🧪 Testing {test_name}: {endpoint_url}")
    
    try:
        start_time = time.time()
        
        if method == 'GET':
            response = requests.get(endpoint_url, timeout=30)
        elif method == 'POST':
            response = requests.post(endpoint_url, json=request_data, timeout=30)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {test_name}: SUCCESS ({response_time:.1f}ms)")
            return {
                'success': True,
                'response_time': response_time,
                'status_code': response.status_code,
                'data_keys': list(data.keys()) if isinstance(data, dict) else 'list',
                'data_size': len(str(data))
            }
        else:
            print(f"❌ {test_name}: FAILED - Status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return {
                'success': False,
                'response_time': response_time,
                'status_code': response.status_code,
                'error': response.text[:200]
            }
            
    except Exception as e:
        print(f"❌ {test_name}: ERROR - {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'response_time': None
        }

def test_all_endpoints():
    """Test all API endpoints that have been migrated"""
    base_url = "http://localhost:5000"
    
    results = {
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'total_response_time': 0,
        'test_results': []
    }
    
    # Test cases for migrated endpoints
    test_cases = [
        # Core data endpoints
        {
            'url': f"{base_url}/api/companies?page=1&limit=10",
            'name': "Companies Pagination",
            'method': 'GET'
        },
        {
            'url': f"{base_url}/api/companies?search=tech&limit=5",
            'name': "Companies Search",
            'method': 'GET'
        },
        {
            'url': f"{base_url}/api/companies?country=United%20Kingdom&page=1&limit=5",
            'name': "Companies Country Filter",
            'method': 'GET'
        },
        
        # SIC prediction endpoints
        {
            'url': f"{base_url}/api/predict_sic",
            'name': "SIC Prediction (Simulation)",
            'method': 'POST',
            'data': {'company_index': 0}
        },
        {
            'url': f"{base_url}/api/predict_sic",
            'name': "SIC Prediction (Real Agents)",
            'method': 'POST',
            'data': {'company_index': 0, 'use_real_agents': True}
        },
        
        # Company details
        {
            'url': f"{base_url}/api/company_details/0",
            'name': "Company Details",
            'method': 'GET'
        },
        {
            'url': f"{base_url}/api/company_details/5",
            'name': "Company Details (Index 5)",
            'method': 'GET'
        },
        
        # Additional endpoints (may use original implementation for now)
        {
            'url': f"{base_url}/api/data",
            'name': "Data Endpoint",
            'method': 'GET'
        },
        {
            'url': f"{base_url}/api/filter_options",
            'name': "Filter Options",
            'method': 'GET'
        },
        {
            'url': f"{base_url}/api/stats",
            'name': "Statistics",
            'method': 'GET'
        },
        {
            'url': f"{base_url}/api/summary",
            'name': "Summary",
            'method': 'GET'
        }
    ]
    
    print("🚀 COMPREHENSIVE API ENDPOINT MIGRATION TESTING")
    print("=" * 60)
    
    for test_case in test_cases:
        result = test_endpoint_migration(
            test_case['url'], 
            test_case['name'],
            test_case.get('data'),
            test_case['method']
        )
        
        results['test_results'].append({
            'test_name': test_case['name'],
            'url': test_case['url'],
            'result': result
        })
        
        results['total_tests'] += 1
        if result['success']:
            results['passed_tests'] += 1
            if result['response_time']:
                results['total_response_time'] += result['response_time']
        else:
            results['failed_tests'] += 1
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    print(f"Total Tests: {results['total_tests']}")
    print(f"✅ Passed: {results['passed_tests']}")
    print(f"❌ Failed: {results['failed_tests']}")
    print(f"Success Rate: {(results['passed_tests']/results['total_tests']*100):.1f}%")
    
    if results['passed_tests'] > 0:
        avg_response_time = results['total_response_time'] / results['passed_tests']
        print(f"⚡ Average Response Time: {avg_response_time:.1f}ms")
    
    print("\n📋 DETAILED RESULTS:")
    for test_result in results['test_results']:
        status = "✅" if test_result['result']['success'] else "❌"
        rt = f"{test_result['result']['response_time']:.1f}ms" if test_result['result'].get('response_time') else "N/A"
        print(f"{status} {test_result['test_name']}: {rt}")
    
    # Performance analysis
    print("\n⚡ PERFORMANCE ANALYSIS:")
    fast_endpoints = []
    slow_endpoints = []
    
    for test_result in results['test_results']:
        if test_result['result']['success'] and test_result['result'].get('response_time'):
            rt = test_result['result']['response_time']
            if rt < 200:
                fast_endpoints.append((test_result['test_name'], rt))
            elif rt > 1000:
                slow_endpoints.append((test_result['test_name'], rt))
    
    if fast_endpoints:
        print(f"🚀 Fast endpoints (<200ms): {len(fast_endpoints)}")
        for name, rt in fast_endpoints:
            print(f"   • {name}: {rt:.1f}ms")
    
    if slow_endpoints:
        print(f"🐌 Slow endpoints (>1000ms): {len(slow_endpoints)}")
        for name, rt in slow_endpoints:
            print(f"   • {name}: {rt:.1f}ms")
    
    # Migration status
    print("\n🏗️ MODULAR ARCHITECTURE STATUS:")
    modular_endpoints = [
        "Companies Pagination", "Companies Search", "Companies Country Filter",
        "SIC Prediction (Simulation)", "SIC Prediction (Real Agents)", 
        "Company Details", "Company Details (Index 5)"
    ]
    
    migrated_count = 0
    for test_result in results['test_results']:
        if test_result['test_name'] in modular_endpoints and test_result['result']['success']:
            migrated_count += 1
    
    print(f"✅ Migrated endpoints working: {migrated_count}/{len(modular_endpoints)}")
    print(f"📈 Migration progress: {(migrated_count/len(modular_endpoints)*100):.1f}%")
    
    return results

def main():
    """Main test execution"""
    print("Starting Flask app validation...")
    print("Please ensure your Flask app is running on http://localhost:5000")
    print("Press Enter to continue or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        return
    
    results = test_all_endpoints()
    
    # Generate test report
    print(f"\n📄 MIGRATION TEST REPORT GENERATED")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if results['failed_tests'] == 0:
        print("\n🎉 ALL TESTS PASSED! Migration successful!")
    else:
        print(f"\n⚠️ {results['failed_tests']} tests failed. Check logs above.")
    
    return results

if __name__ == "__main__":
    main()