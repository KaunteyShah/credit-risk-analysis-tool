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

def configure_database_containers():
    """Configure database connection to use containerized database APIs"""
    try:
        logger.info("� Configuring database container connections...")
        
        # Set environment variables to point to database container APIs
        main_db_container = os.getenv('MAIN_DB_CONTAINER_URL', 'http://20.162.36.147:8080')
        vector_db_container = os.getenv('VECTOR_DB_CONTAINER_URL', 'http://20.162.22.99:8080')
        
        os.environ['MAIN_DB_CONTAINER_URL'] = main_db_container
        os.environ['VECTOR_DB_CONTAINER_URL'] = vector_db_container
        os.environ['USE_CONTAINER_DB'] = 'true'
        
        logger.info(f"✅ Main DB Container: {main_db_container}")
        logger.info(f"✅ Vector DB Container: {vector_db_container}")
        
        # Test connectivity
        import requests
        try:
            response = requests.get(f"{main_db_container}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Main database container is healthy")
            else:
                logger.warning(f"⚠️ Main database container returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to main database container: {e}")
        
        try:
            response = requests.get(f"{vector_db_container}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Vector database container is healthy")
            else:
                logger.warning(f"⚠️ Vector database container returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to vector database container: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to configure database containers: {e}")
        return False

def create_app():
    """
    Create and configure Flask app for Azure deployment
    """
    try:
        logger.info("🚀 Starting Credit Risk Analysis Tool on Azure...")
        
        import shutil
        
        # Configure database containers
        configure_database_containers()
        
        # ============================================================================
        # Configure Database Paths - Use Container APIs
        # ============================================================================
        # When using database containers, the app will connect via HTTP API
        # No local database files needed
        logger.info("✅ Using containerized databases via HTTP API")
        
        # Set environment for Flask
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