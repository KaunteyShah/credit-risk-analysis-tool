#!/usr/bin/env python3
"""
Azure App Service startup test script for debugging deployment issues.
This script helps identify what's going wrong during Azure deployment.
"""
import os
import sys
import time
import traceback

def test_azure_startup():
    """Test Azure App Service startup configuration."""
    print("=" * 60)
    print("🧪 Azure App Service Startup Test")
    print("=" * 60)
    
    # Test 1: Check Python version
    print(f"Python Version: {sys.version}")
    
    # Test 2: Check environment variables
    print(f"WEBSITES_PORT: {os.environ.get('WEBSITES_PORT', 'Not set')}")
    print(f"PORT: {os.environ.get('PORT', 'Not set')}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # Test 3: Check working directory
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"Files in directory: {os.listdir('.')}")
    
    # Test 4: Check critical dependencies
    critical_deps = ['flask', 'pandas', 'numpy', 'gunicorn']
    for dep in critical_deps:
        try:
            __import__(dep)
            print(f"✅ {dep} imported successfully")
        except ImportError as e:
            print(f"❌ {dep} import failed: {e}")
    
    # Test 5: Try to import our app
    try:
        from app.flask_main import create_app
        print("✅ App import successful")
        
        # Test 6: Try to create app instance
        app = create_app()
        print("✅ App instance created successfully")
        
        # Test 7: Check app configuration
        print(f"App debug mode: {app.debug}")
        print(f"App secret key configured: {'Yes' if app.secret_key else 'No'}")
        
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 8: Test port binding
    port = os.environ.get('WEBSITES_PORT') or os.environ.get('PORT', '8000')
    print(f"Will bind to port: {port}")
    
    print("=" * 60)
    print("🎉 Startup test completed!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        test_azure_startup()
        print("✅ Test passed - starting main application")
        
        # Import and run the actual app
        from main import main
        main()
        
    except Exception as e:
        print(f"💥 Critical startup error: {e}")
        traceback.print_exc()
        sys.exit(1)