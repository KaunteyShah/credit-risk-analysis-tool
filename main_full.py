#!/usr/bin/env python3
"""
Azure App Service entry point for Credit Risk Analysis Tool.
This file serves as the main entry point that Azure App Service expects.
"""

import os
import sys
import logging

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging for Azure App Service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import and create the Flask application
try:
    from app.flask_main import create_app
    logger.info("✅ Successfully imported create_app from app.flask_main")
except ImportError as e:
    logger.error(f"❌ Failed to import create_app: {e}")
    sys.exit(1)

# Create the Flask application instance
app = create_app()
logger.info("✅ Flask application created successfully")

# For Azure App Service with Gunicorn
application = app

# Add a health check endpoint for Azure App Service
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'message': 'Flask app is running'}, 200

@app.route('/')
def home():
    return {'status': 'running', 'message': 'Credit Risk Analysis Tool - Flask API is operational'}, 200

if __name__ == '__main__':
    # Azure App Service uses the PORT environment variable
    # Default to 8000 for Azure, 8001 for local development
    port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8001)))
    
    logger.info(f"🌐 Environment variables:")
    logger.info(f"   PORT: {os.environ.get('PORT', 'not set')}")
    logger.info(f"   WEBSITES_PORT: {os.environ.get('WEBSITES_PORT', 'not set')}")
    logger.info(f"   Using port: {port}")
    
    logger.info(f"🚀 Starting Flask application on 0.0.0.0:{port}")
    logger.info(f"✅ Health check available at /health")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Failed to start Flask app: {e}")
        raise