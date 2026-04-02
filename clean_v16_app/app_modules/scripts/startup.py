#!/usr/bin/env python3
"""
Azure Web App Startup Script
Entry point for Azure deployment of the Credit Risk Analysis Tool
"""
import os
import sys
import logging

# Configure logging for Azure App Service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

def create_app():
    """
    Create and configure Flask app for Azure deployment
    """
    try:
        logger.info("🚀 Starting Credit Risk Analysis Tool on Azure...")
        
        # Set production environment
        os.environ['FLASK_ENV'] = 'production'
        os.environ['FLASK_DEBUG'] = 'False'
        
        # Add the project root to Python path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import and create Flask app
        logger.info("Creating Flask application...")
        from app_modules.flask_main import create_app as create_flask_app
        app = create_flask_app()
        
        logger.info("✅ Flask application created successfully")
        logger.info(f"App name: {app.name}")
        logger.info(f"Debug mode: {app.debug}")
        
        return app
        
    except Exception as e:
        logger.error(f"❌ Failed to create Flask app: {e}")
        raise

# Create app instance for Azure
app = create_app()

if __name__ == '__main__':
    # This will be called by Azure App Service
    port = int(os.environ.get('PORT', 5002))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)