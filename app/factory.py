"""
Flask Application Factory with proper configuration and data management
"""
import os
from typing import Optional
from flask import Flask, g
from flask_cors import CORS
from app.utils.data_manager import ApplicationDataManager
from app.utils.centralized_logging import setup_logging, get_logger

# Setup centralized logging early
environment = os.environ.get('ENVIRONMENT', 'development')
setup_logging(environment)
logger = get_logger('app.factory')

# Import rate limiting (with fallback if not available)
try:
    from app.utils.rate_limiting import setup_rate_limiting
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    logger.warning("Rate limiting not available - flask-limiter not installed")
    RATE_LIMITING_AVAILABLE = False
    setup_rate_limiting = None


def create_app(config_name: Optional[str] = None) -> Flask:
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DEBUG'] = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.config['PROJECT_ROOT'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Initialize CORS
    CORS(app, origins=["http://localhost:5000", "https://*.azurewebsites.net"])
    
    # Initialize data manager
    data_manager = ApplicationDataManager(app.config['PROJECT_ROOT'])
    app.config['DATA_MANAGER'] = data_manager
    
    # Setup rate limiting if available
    if RATE_LIMITING_AVAILABLE and setup_rate_limiting:
        try:
            limiter = setup_rate_limiting(app)
            app.config['LIMITER'] = limiter
            logger.info("Rate limiting enabled")
        except Exception as e:
            logger.error(f"Failed to setup rate limiting: {e}")
    else:
        logger.info("Rate limiting disabled - not available or not configured")
    
    @app.before_request
    def load_global_data():
        """Load data manager into Flask's g object for request context"""
        g.data_manager = app.config['DATA_MANAGER']
    
    @app.teardown_appcontext
    def close_db(error):
        """Clean up request context"""
        g.pop('data_manager', None)
    
    # Import and register routes after app creation
    with app.app_context():
        from app.routes import register_routes
        register_routes(app)
    
    logger.info("Flask application created successfully")
    return app


def get_data_manager() -> ApplicationDataManager:
    """Get the data manager from Flask context"""
    if 'data_manager' not in g:
        # Fallback if not in request context
        from flask import current_app
        return current_app.config['DATA_MANAGER']
    return g.data_manager