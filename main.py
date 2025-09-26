#!/usr/bin/env python3
"""
Production Azure Entry Point - Credit Risk Analysis
Clean implementation with proper error handling and logging
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging for Azure App Service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def create_application():
    """Create Flask application with proper error handling"""
    logger.info("🚀 Starting Credit Risk Analysis Application")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    try:
        # Ensure proper Python path setup
        project_root = Path(__file__).parent
        app_dir = project_root / 'app'
        
        if str(app_dir) not in sys.path:
            sys.path.insert(0, str(app_dir))
            logger.info(f"Added to Python path: {app_dir}")
        
        # Import and create Flask app
        logger.info("Loading Flask application from flask_main...")
        from flask_main import create_app
        
        app = create_app()
        logger.info("✅ Flask application created successfully!")
        
        return app
        
    except ImportError as e:
        logger.error(f"❌ Import Error: {e}")
        logger.error("Check that all required dependencies are installed")
        raise
    except Exception as e:
        logger.error(f"❌ Application Error: {e}")
        logger.error("Check application configuration and data files")
        raise

# Create WSGI application for Azure
logger.info("Initializing WSGI application...")
app = create_application()
application = app  # Azure App Service expects 'application'

def main():
    """Development server entry point"""
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🌐 Starting development server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()