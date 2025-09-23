#!/usr/bin/env python3
"""
Main entry point for the Credit Risk Analysis Flask application on Azure App Service.
This file serves as the entry point that Azure App Service can automatically detect.
"""
import os
import sys
import subprocess
import logging

# Configure logging for Azure App Service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Flask application."""
    logger.info("🚀 Starting Credit Risk Analysis Flask Application...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    
    # Set environment variables
    os.environ['PYTHONPATH'] = '/home/site/wwwroot'
    port = os.environ.get('WEBSITES_PORT', '8000')
    logger.info(f"Port: {port}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    
    # Test critical imports first
    try:
        logger.info("🔍 Testing critical imports...")
        import flask
        try:
            # Try to get Flask version (method varies by version)
            flask_version = getattr(flask, '__version__', 'unknown')
            logger.info(f"✅ Flask version: {flask_version}")
        except:
            logger.info("✅ Flask imported successfully (version detection failed)")
        
        import flask_cors
        logger.info(f"✅ Flask-CORS available")
        
        from app.utils.config_manager import ConfigManager
        logger.info("✅ ConfigManager import successful")
        
    except ImportError as e:
        logger.error(f"❌ Critical import failed: {e}")
        logger.info("📦 Installing dependencies...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            logger.info("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as install_error:
            logger.error(f"❌ Failed to install dependencies: {install_error}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error during imports: {e}")
        sys.exit(1)
    
    # Start Flask app
    logger.info(f"🌐 Starting Flask application on port {port}...")
    
    try:
        # Import and run the Flask app
        from app.flask_main import create_app
        
        app = create_app()
        logger.info("✅ Flask app created successfully")
        logger.info("🚀 Starting Flask server...")
        
        app.run(host='0.0.0.0', port=int(port), debug=False)
        
    except Exception as e:
        logger.error(f"❌ Failed to start Flask application: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
