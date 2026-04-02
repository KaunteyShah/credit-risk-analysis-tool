"""
API routes module - placeholder for future refactoring
"""
from flask import Flask
from app.utils.centralized_logging import get_logger
logger = get_logger(__name__)


def register_api_routes(app: Flask) -> None:
    """Register API routes - placeholder for future refactoring"""
    # This will be populated when we refactor the existing flask_main.py routes
    # For now, we'll keep using the monolithic flask_main.py structure
    logger.info("API routes registration placeholder - using flask_main.py routes")
    pass