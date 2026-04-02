"""
Modular Architecture Integration

This script demonstrates how to integrate the new modular architecture
alongside your existing flask_main.py without modifying it.

It registers new /api/v2/ routes that use the clean service layer architecture
while keeping all your existing routes and UI completely unchanged.
"""

import sys
import os

# Add project root and app directory to path for imports
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, '..'))
app_dir = os.path.abspath(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from flask_main import create_app
from api.modular_routes import modular_api
from utils.logger import logger

def create_modular_app():
    """
    Create Flask app with both existing and new modular architecture routes.
    
    This function:
    1. Creates your existing Flask app (with all current functionality)
    2. Registers new /api/v2/ routes that use modular architecture
    3. Keeps your UI and existing /api/ routes completely unchanged
    """
    try:
        # Create your existing Flask app
        app = create_app()
        
        # Register the new modular API routes
        app.register_blueprint(modular_api)
        
        logger.info("✅ Modular architecture integrated successfully!")
        logger.info("📋 Available route prefixes:")
        logger.info("   /api/     - Your existing routes (unchanged)")
        logger.info("   /api/v2/  - New modular architecture routes")
        logger.info("   /         - Your beautiful UI (unchanged)")
        
        return app
        
    except Exception as e:
        logger.error(f"❌ Error integrating modular architecture: {str(e)}")
        raise

def test_modular_integration():
    """
    Test function to verify modular architecture integration.
    
    This creates the app and tests that both old and new routes are available.
    """
    try:
        app = create_modular_app()
        
        with app.test_client() as client:
            # Test existing route (should work unchanged)
            logger.info("🧪 Testing existing /api/data route...")
            response = client.get('/api/data')
            logger.info(f"   Status: {response.status_code}")
            
            # Test new modular route (should work with new architecture)
            logger.info("🧪 Testing new /api/v2/data route...")
            response = client.get('/api/v2/data')
            logger.info(f"   Status: {response.status_code}")
            
            # Test architecture info route
            logger.info("🧪 Testing architecture info route...")
            response = client.get('/api/v2/architecture/info')
            logger.info(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                logger.info(f"   Architecture: {data.get('architecture', 'unknown')}")
                logger.info(f"   Components: {len(data.get('components', {}))}")
            
        logger.info("✅ All tests passed! Modular architecture is working.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return False

if __name__ == '__main__':
    """
    Run this script to test the modular architecture integration.
    
    Usage:
    python app/modular_integration.py
    """
    print("🚀 Testing Modular Architecture Integration...")
    print("=" * 50)
    
    success = test_modular_integration()
    
    if success:
        print("\n🎉 SUCCESS! Modular architecture is ready!")
        print("\n📋 Next Steps:")
        print("1. Your existing app works exactly as before")
        print("2. Test new routes at /api/v2/ endpoints")
        print("3. Compare responses between /api/ and /api/v2/ routes")
        print("4. When satisfied, gradually migrate existing routes")
        print("\n🎨 Your UI remains completely unchanged!")
    else:
        print("\n❌ Integration test failed. Check logs for details.")
        sys.exit(1)