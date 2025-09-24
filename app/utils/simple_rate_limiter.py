"""
Simple rate limiting implementation without external dependencies
"""
import time
from functools import wraps
from typing import Dict, Optional, Callable
from collections import defaultdict, deque
from flask import request, jsonify, g
from app.utils.centralized_logging import get_logger
logger = get_logger(__name__)


class SimpleRateLimiter:
    """Simple in-memory rate limiter using sliding window"""
    
    def __init__(self, default_rate: str = "100 per minute"):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.default_rate = self._parse_rate(default_rate)
        
    def _parse_rate(self, rate_str: str) -> tuple:
        """Parse rate string like '100 per minute' into (count, seconds)"""
        try:
            parts = rate_str.lower().split()
            if len(parts) >= 3:
                count = int(parts[0])
                unit = parts[2]
                
                time_mapping = {
                    'second': 1,
                    'seconds': 1, 
                    'minute': 60,
                    'minutes': 60,
                    'hour': 3600,
                    'hours': 3600,
                    'day': 86400,
                    'days': 86400
                }
                
                seconds = time_mapping.get(unit, 60)  # Default to minute
                return (count, seconds)
                
        except Exception as e:
            logger.warning(f"Could not parse rate '{rate_str}': {e}")
            
        return (100, 60)  # Default: 100 per minute
    
    def _get_client_key(self) -> str:
        """Get unique identifier for the client"""
        ip = request.remote_addr or 'unknown'
        user_agent = request.headers.get('User-Agent', '')[:50]
        
        # Simple hash of IP + User-Agent
        import hashlib
        combined = f"{ip}:{user_agent}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]
    
    def _cleanup_old_requests(self, client_key: str, window_seconds: int) -> None:
        """Remove requests older than the time window"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        # Remove old requests
        while (self.requests[client_key] and 
               self.requests[client_key][0] < cutoff_time):
            self.requests[client_key].popleft()
    
    def is_allowed(self, rate: Optional[str] = None) -> tuple:
        """Check if request is allowed, return (allowed, info)"""
        client_key = self._get_client_key()
        rate_limit, window_seconds = self._parse_rate(rate or "100 per minute")
        
        current_time = time.time()
        
        # Clean up old requests
        self._cleanup_old_requests(client_key, window_seconds)
        
        # Check if under limit
        current_count = len(self.requests[client_key])
        
        if current_count >= rate_limit:
            # Calculate when limit resets
            if self.requests[client_key]:
                oldest_request = self.requests[client_key][0]
                reset_time = oldest_request + window_seconds
            else:
                reset_time = current_time + window_seconds
                
            return False, {
                'limit': rate_limit,
                'current': current_count,
                'reset_time': reset_time,
                'retry_after': int(reset_time - current_time)
            }
        
        # Allow request and record it
        self.requests[client_key].append(current_time)
        
        return True, {
            'limit': rate_limit,
            'current': current_count + 1,
            'remaining': rate_limit - (current_count + 1),
            'reset_time': current_time + window_seconds
        }


# Global rate limiter instance
_rate_limiter = SimpleRateLimiter()


def rate_limit(rate: str = "100 per minute"):
    """Decorator to apply rate limiting to Flask routes"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            allowed, info = _rate_limiter.is_allowed(rate)
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {_rate_limiter._get_client_key()}")
                
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {info["limit"]} requests per window.',
                    'retry_after': info.get('retry_after', 60),
                    'reset_time': info.get('reset_time')
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(info.get('retry_after', 60))
                response.headers['X-RateLimit-Limit'] = str(info['limit'])
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(int(info.get('reset_time', time.time())))
                
                return response
            
            # Store rate limit info for response headers
            g.rate_limit_info = info
            
            # Execute the original function
            response = f(*args, **kwargs)
            
            # Add rate limit headers to successful responses
            if hasattr(response, 'headers') and hasattr(g, 'rate_limit_info'):
                info = g.rate_limit_info
                response.headers['X-RateLimit-Limit'] = str(info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(info.get('remaining', 0))
                response.headers['X-RateLimit-Reset'] = str(int(info.get('reset_time', time.time())))
            
            return response
        
        return wrapper
    return decorator


def get_rate_limit_status() -> dict:
    """Get current rate limit status for debugging"""
    try:
        client_key = _rate_limiter._get_client_key()
        current_requests = len(_rate_limiter.requests.get(client_key, []))
        
        return {
            'client_id': client_key,
            'current_requests': current_requests,
            'default_limit': _rate_limiter.default_rate[0],
            'window_seconds': _rate_limiter.default_rate[1]
        }
        
    except Exception as e:
        return {'error': str(e)}


def clear_rate_limits():
    """Clear all rate limit data (useful for testing)"""
    _rate_limiter.requests.clear()
    logger.info("Rate limit data cleared")


# Pre-configured rate limit decorators for common use cases
data_rate_limit = rate_limit("200 per minute")  # Data endpoints
ai_rate_limit = rate_limit("10 per minute")     # AI/computation endpoints  
update_rate_limit = rate_limit("50 per minute") # Update endpoints
strict_rate_limit = rate_limit("20 per minute") # General strict limit