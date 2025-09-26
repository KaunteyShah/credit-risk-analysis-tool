#!/usr/bin/env python3
"""
Azure App Service Startup Script
Optimized for Azure Linux App Service with proper Gunicorn configuration
"""

import os
import sys
import logging

# Configure logging for Azure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

def main():
    """Entry point for Azure App Service"""
    logger.info("🚀 Azure App Service startup initiated")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Python path: {sys.path}")
    
    # Import and create the Flask application
    try:
        from main import create_application
        app = create_application()
        logger.info("✅ Flask application created successfully")
        return app
    except Exception as e:
        logger.error(f"❌ Failed to create Flask application: {e}")
        raise

# For Gunicorn WSGI
application = main()

if __name__ == '__main__':
    # For direct execution (development)
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🌐 Running directly on port {port}")
    application.run(host='0.0.0.0', port=port, debug=False)