"""
Route registration module - registers all routes with the Flask app
"""
from flask import Flask
from app_modules.routes.main_routes import register_main_routes
from app_modules.routes.api_routes import register_api_routes
from app_modules.utils.centralized_logging import get_logger
logger = get_logger(__name__)


def register_routes(app: Flask) -> None:
    """Register all application routes"""
    try:
        # Register main routes (/, /health, /debug)
        register_main_routes(app)
        
        # Register API routes (/api/*)
        register_api_routes(app)
        
        # Register Enhanced API v2 routes (/api/v2/*)
        try:
            from app_modules.api.enhanced_routes_v2 import api_v2
            app.register_blueprint(api_v2)
            logger.info("Enhanced API v2 routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register Enhanced API v2 routes: {e}")
        
        logger.info("All routes registered successfully")
        
    except Exception as e:
        logger.error(f"Error registering routes: {e}")
        raise