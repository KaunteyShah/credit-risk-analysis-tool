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

if __name__ == '__main__':
    # For local development and Azure App Service
    port = int(os.environ.get('PORT', 8001))
    logger.info(f"🚀 Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)