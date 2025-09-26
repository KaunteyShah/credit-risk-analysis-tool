#!/usr/bin/env python3
"""
Azure App Service WSGI Entry Point
Optimized for Gunicorn deployment in Azure Linux App Service
"""

import os
import sys
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging for Azure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    logger.info("🚀 Azure App Service startup initiated")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Python path: {sys.path[:3]}...")  # Show first 3 entries
    
    try:
        # Import and create Flask application
        logger.info("Importing main application...")
        from main import create_application
        
        logger.info("Creating Flask application instance...")
        app = create_application()
        
        logger.info("✅ Flask application created successfully")
        return app
        
    except ImportError as e:
        logger.error(f"❌ Import error during app creation: {e}")
        logger.error("Available files in current directory:")
        for file in os.listdir('.'):
            logger.error(f"  - {file}")
        raise
        
    except Exception as e:
        logger.error(f"❌ Failed to create Flask application: {e}")
        logger.exception("Full traceback:")
        raise

# Create the WSGI application instance for Gunicorn
logger.info("Creating WSGI application for Gunicorn...")
application = create_app()
logger.info("✅ WSGI application ready")

if __name__ == '__main__':
    # For direct execution (development only)
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🌐 Running directly on port {port} (development mode)")
    application.run(host='0.0.0.0', port=port, debug=False)