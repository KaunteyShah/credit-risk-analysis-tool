#!/usr/bin/env python3
"""
Test the debug endpoint with error handling
"""
import requests
import json

APP_URL = "https://credit-risk-analysis-prod-app-25h2ya.azurewebsites.net"

try:
    print("🔍 Testing debug endpoint...")
    response = requests.get(f"{APP_URL}/api/data/debug", timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Debug info retrieved successfully!")
        
        # Key information
        print(f"\nEnvironment: {result.get('environment')}")
        print(f"Project root: {result.get('project_root')}")
        print(f"Working directory: {result.get('working_directory')}")
        
        # Data file status
        print(f"\nCompany file exists: {result.get('company_file_exists')}")
        print(f"Company file path: {result.get('company_file_path')}")
        if result.get('company_file_size'):
            print(f"Company file size: {result.get('company_file_size')} bytes")
            
        print(f"\nSIC file exists: {result.get('sic_file_exists')}")
        print(f"SIC file path: {result.get('sic_file_path')}")
        if result.get('sic_file_size'):
            print(f"SIC file size: {result.get('sic_file_size')} bytes")
            
        # Data directory contents
        print(f"\nData directory exists: {result.get('data_directory_exists')}")
        if result.get('data_directory_contents'):
            print(f"Data directory contents: {result.get('data_directory_contents')}")
            
        # App data status
        print(f"\nApp company data loaded: {result.get('app_company_data_loaded')}")
        print(f"App company data is None: {result.get('app_company_data_is_none')}")
        
    else:
        print(f"❌ Error: {response.status_code}")
        error_text = response.text[:500]
        print(f"Response: {error_text}")
        
        # Try to parse as JSON to get error details
        try:
            error_json = response.json()
            print(f"Error: {error_json.get('error')}")
        except:
            pass
            
except Exception as e:
    print(f"❌ Connection error: {e}")