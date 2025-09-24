#!/usr/bin/env python3#!/usr/bin/env python3#!/usr/bin/env python3

"""

Azure App Service entry point for Credit Risk Analysis Tool.""""""

This file serves as the main entry point that Azure App Service expects.

"""Entry point for Azure App Service deployment.Main entry point for the Credit Risk Analysis Flask application on Azure App Service.



import sysThis file serves as the main entry point that Azure App Service expects.This file serves as the entry point that Azure App Service can automatically detect.

import os

""""""

# Add the project root to Python path

project_root = os.path.dirname(os.path.abspath(__file__))import os

if project_root not in sys.path:

    sys.path.insert(0, project_root)import sysimport sys



# Import and create the Flask applicationimport osimport subprocess

from app.flask_main import create_app

import logging

# Create the Flask application instance

app = create_app()# Add the project root to Python path



if __name__ == '__main__':project_root = os.path.dirname(os.path.abspath(__file__))# Configure logging for Azure App Service

    # For local development

    port = int(os.environ.get('PORT', 8001))if project_root not in sys.path:logging.basicConfig(

    app.run(host='0.0.0.0', port=port, debug=False)
    sys.path.insert(0, project_root)    level=logging.INFO,

    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

# Import and start the Flask application    handlers=[

from app.flask_main import create_app        logging.StreamHandler(sys.stdout)

    ]

# Create the Flask application)

app = create_app()logger = logging.getLogger(__name__)



if __name__ == '__main__':def main():

    # For local development    """Main entry point for the Flask application."""

    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8001)), debug=True)    logger.info("🚀 Starting Credit Risk Analysis Flask Application...")

else:    logger.info(f"Python version: {sys.version}")

    # For Azure App Service with Gunicorn    logger.info(f"Python executable: {sys.executable}")

    # Azure will use this 'app' object    

    application = app    # Set environment variables
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
