"""
Pre-startup validation for Azure deployment.
Checks essential components before starting the main application.
"""

import sys
import os
import importlib

def validate_environment():
    """Validate Azure environment setup"""
    print("🔍 Validating Azure environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print(f"❌ Python {sys.version_info} too old, need 3.8+")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check essential environment variables
    required_vars = ['PORT', 'WEBSITES_PORT', 'HTTP_PLATFORM_PORT']
    port_found = any(os.environ.get(var) for var in required_vars)
    if not port_found:
        print("⚠️ No port environment variable found, using default")
    else:
        print("✅ Port environment variable available")
    
    # Check Flask availability
    try:
        import flask
        print("✅ Flask available")
    except ImportError:
        print("❌ Flask not available")
        return False
    
    # Check optional dependencies
    try:
        import flask_cors
        print("✅ flask-cors available")
    except ImportError:
        print("⚠️ flask-cors not available (optional)")
    
    print("✅ Environment validation complete")
    return True

if __name__ == '__main__':
    if validate_environment():
        print("🚀 Starting minimal_startup.py...")
        # Import and run the main startup
        try:
            import minimal_startup
        except Exception as e:
            print(f"❌ Failed to start main app: {e}")
            sys.exit(1)
    else:
        print("❌ Environment validation failed")
        sys.exit(1)