"""
Route registration module - registers all routes with the Flask app
"""
from flask import Flask
from app.routes.main_routes import register_main_routes
from app.routes.api_routes import register_api_routes
from app.utils.centralized_logging import get_logger
logger = get_logger(__name__)


def register_routes(app: Flask) -> None:
    """Register all application routes"""
    try:
        # Register main routes (/, /health, /debug)
        register_main_routes(app)
        
        # Register API routes (/api/*)
        register_api_routes(app)
        
        logger.info("All routes registered successfully")
        
    except Exception as e:
        logger.error(f"Error registering routes: {e}")
        raise