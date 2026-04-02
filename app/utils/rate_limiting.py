"""
Rate limiting configuration and implementation for Flask API endpoints
"""
from flask import Flask, request, jsonify, g
from typing import Optional
import os
from app.utils.centralized_logging import get_logger
logger = get_logger(__name__)

# Import Flask-Limiter with fallback
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    # Create dummy classes for type hints when flask-limiter is not available
    class Limiter:
        pass
    
    def get_remote_address():
        return request.remote_addr if request else 'unknown'
    
    LIMITER_AVAILABLE = False


def get_user_identity():
    """Get user identity for rate limiting (IP-based with user-agent consideration)"""
    # Combine IP address with user agent for better rate limiting
    ip = get_remote_address()
    user_agent = request.headers.get('User-Agent', 'unknown')
    
    # Create a simple hash for rate limiting purposes
    import hashlib
    combined = f"{ip}:{user_agent[:50]}"  # Limit user agent length
    user_hash = hashlib.md5(combined.encode()).hexdigest()[:8]
    
    return f"{ip}:{user_hash}"


def create_limiter(app: Flask) -> Limiter:
    """Create and configure rate limiter for the Flask app"""
    
    # Configuration from environment or defaults
    rate_limit_storage = os.environ.get('RATE_LIMIT_STORAGE_URL', 'memory://')
    default_limits = os.environ.get('RATE_LIMIT_DEFAULT', '1000 per hour, 100 per minute')
    
    # Create limiter instance
    limiter = Limiter(
        app=app,
        key_func=get_user_identity,
        storage_uri=rate_limit_storage,
        default_limits=[default_limits],
        headers_enabled=True,  # Include rate limit info in response headers
        retry_after='http-date'  # Standard retry-after header format
    )
    
    # Error handler for rate limit exceeded
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handle rate limit exceeded errors"""
        logger.warning(f"Rate limit exceeded for {get_user_identity()}: {str(e)}")
        
        response_data = {
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'retry_after': getattr(e, 'retry_after', None),
            'limit': str(e.limit) if hasattr(e, 'limit') else None
        }
        
        response = jsonify(response_data)
        response.status_code = 429
        
        # Add rate limit headers if available
        if hasattr(e, 'retry_after'):
            response.headers['Retry-After'] = str(e.retry_after)
        
        return response
    
    logger.info(f"Rate limiting initialized with storage: {rate_limit_storage}")
    return limiter


def configure_endpoint_limits(limiter: Limiter, app: Flask):
    """Configure specific rate limits for different API endpoints"""
    
    # High-traffic data endpoints - more restrictive
    data_endpoints = [
        '/api/data',
        '/api/filter_options', 
        '/api/stats',
        '/api/summary'
    ]
    
    # AI/computation endpoints - very restrictive  
    ai_endpoints = [
        '/api/predict_sic',
        '/api/predict_sic_real',
        '/api/run_agent_workflow',
        '/api/test_agents'
    ]
    
    # Update endpoints - moderate restrictions
    update_endpoints = [
        '/api/update_revenue',
        '/api/update_sic', 
        '/api/update_main_table'
    ]
    
    # Apply endpoint-specific limits
    with app.app_context():
        # Data endpoints: 200 per minute, 2000 per hour
        for endpoint in data_endpoints:
            limiter.limit("200 per minute, 2000 per hour")(
                app.view_functions.get(endpoint.replace('/api/', 'api_'))
            )
        
        # AI endpoints: 10 per minute, 100 per hour (very restrictive)
        for endpoint in ai_endpoints:
            view_func_name = endpoint.replace('/api/', 'api_').replace('/', '_')
            view_func = app.view_functions.get(view_func_name)
            if view_func:
                limiter.limit("10 per minute, 100 per hour")(view_func)
        
        # Update endpoints: 50 per minute, 500 per hour
        for endpoint in update_endpoints:
            view_func_name = endpoint.replace('/api/', 'api_').replace('/', '_')
            view_func = app.view_functions.get(view_func_name)
            if view_func:
                limiter.limit("50 per minute, 500 per hour")(view_func)
    
    logger.info("Configured endpoint-specific rate limits")


def setup_rate_limiting(app: Flask) -> Limiter:
    """Set up complete rate limiting for the Flask application"""
    try:
        # Create limiter
        limiter = create_limiter(app)
        
        # Configure endpoint-specific limits
        configure_endpoint_limits(limiter, app)
        
        # Add rate limit info to responses
        @app.after_request
        def add_rate_limit_headers(response):
            """Add rate limiting information to response headers"""
            try:
                # Get current limit status
                current_limit = getattr(g, '_view_rate_limit', None)
                if current_limit:
                    response.headers['X-RateLimit-Limit'] = str(current_limit.limit)
                    response.headers['X-RateLimit-Remaining'] = str(current_limit.remaining)
                    response.headers['X-RateLimit-Reset'] = str(current_limit.reset_time)
            except Exception as e:
                logger.debug(f"Could not add rate limit headers: {e}")
            
            return response
        
        logger.info("Rate limiting setup completed successfully")
        return limiter
        
    except Exception as e:
        logger.error(f"Failed to setup rate limiting: {e}")
        # Return a dummy limiter that does nothing to avoid breaking the app
        return None


def get_rate_limit_status(limiter: 'Limiter', endpoint: Optional[str] = None) -> dict:
    """Get current rate limit status for monitoring/debugging"""
    try:
        if not limiter:
            return {'error': 'Rate limiting not available'}
        
        user_id = get_user_identity()
        
        # Get limit info
        limits = limiter.get_current_limits()
        status = {
            'user_id': user_id,
            'limits': [],
            'endpoint': endpoint or 'general'
        }
        
        for limit in limits:
            status['limits'].append({
                'limit': str(limit.limit),
                'remaining': limit.remaining,
                'reset_time': limit.reset_time
            })
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        return {'error': str(e)}