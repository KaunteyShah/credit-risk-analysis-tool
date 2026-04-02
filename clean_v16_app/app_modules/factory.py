"""
Flask Application Factory with proper configuration and data management
"""
import os
from typing import Optional
from flask import Flask, g
from flask_cors import CORS
from app_modules.utils.data_manager import ApplicationDataManager
from app_modules.utils.centralized_logging import setup_logging, get_logger

# Setup centralized logging early
environment = os.environ.get('ENVIRONMENT', 'development')
setup_logging(environment)
logger = get_logger('app.factory')

# Import rate limiting (with fallback if not available)
try:
    from app_modules.utils.rate_limiting import setup_rate_limiting
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    logger.warning("Rate limiting not available - flask-limiter not installed")
    RATE_LIMITING_AVAILABLE = False
    setup_rate_limiting = None


def create_app(config_name: Optional[str] = None) -> Flask:
    """Create and configure Flask application with container-friendly configuration"""
    app = Flask(__name__)
    
    # Initialize Credit Risk Configuration
    from app_modules.config import CreditRiskConfig
    credit_risk_config = CreditRiskConfig()
    app.config['CREDIT_RISK_CONFIG'] = credit_risk_config
    
    # Use configuration-based settings
    app.config['SECRET_KEY'] = credit_risk_config.flask_secret_key
    app.config['DEBUG'] = credit_risk_config.debug_mode
    app.config['PROJECT_ROOT'] = str(credit_risk_config.project_root)
    
    # Initialize CORS
    CORS(app, origins=["http://localhost:5000", "https://*.azurewebsites.net"])
    
    # Initialize data manager with configuration
    data_manager = ApplicationDataManager(str(credit_risk_config.project_root))
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
        from app_modules.routes import register_routes
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


def get_credit_risk_config():
    """Get the Credit Risk configuration from Flask context"""
    try:
        from flask import current_app
        return current_app.config['CREDIT_RISK_CONFIG']
    except (RuntimeError, KeyError):
        # Fallback when outside Flask context
        from app_modules.config import CreditRiskConfig
        return CreditRiskConfig()