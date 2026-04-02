"""
Rate Limiter - API rate limiting and abuse prevention
"""

import time
from datetime import datetime, timedelta
from flask import request, jsonify, current_app
from app_modules.database.connection import DatabaseConnection

class RateLimiter:
    """
    API Rate limiting middleware with configurable limits per endpoint
    """
    
    def __init__(self, app=None):
        self.default_limits = {
            'requests_per_minute': 60,
            'requests_per_hour': 1000,
            'burst_limit': 10  # Max requests in 10 seconds
        }
        
        self.endpoint_limits = {
            '/api/sqlite/companies': {'requests_per_minute': 30},
            '/api/sqlite/advanced-search': {'requests_per_minute': 20},
            '/api/modular/workflows': {'requests_per_minute': 10}
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize rate limiter with Flask app"""
        app.config.setdefault('RATE_LIMITING_ENABLED', True)
        app.config.setdefault('RATE_LIMIT_STORAGE', 'database')  # or 'memory'
        
        # Update limits from config
        self.default_limits.update(app.config.get('DEFAULT_RATE_LIMITS', {}))
        self.endpoint_limits.update(app.config.get('ENDPOINT_RATE_LIMITS', {}))
        
        # Register before_request handler
        app.before_request(self.check_rate_limit)
        
        print("🛡️ Rate Limiter initialized")
    
    def get_client_identifier(self):
        """Get unique identifier for client (IP + User-Agent hash)"""
        ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if not ip:
            ip = request.headers.get('X-Real-IP', '')
        if not ip:
            ip = request.remote_addr or 'unknown'
            
        # Could add API key or user ID here for authenticated requests
        return ip[:45]  # Limit length
    
    def get_endpoint_pattern(self, path):
        """Get normalized endpoint pattern for rate limiting"""
        # Normalize dynamic routes to patterns
        if path.startswith('/api/sqlite/companies/'):
            return '/api/sqlite/companies'
        elif path.startswith('/api/modular/workflows/') and '/agents/' in path:
            return '/api/modular/workflows/*/agents/*'
        else:
            return path
    
    def get_rate_limits(self, endpoint):
        """Get rate limits for specific endpoint"""
        limits = self.default_limits.copy()
        
        # Check if endpoint has specific limits
        for pattern, endpoint_limits in self.endpoint_limits.items():
            if endpoint.startswith(pattern):
                limits.update(endpoint_limits)
                break
                
        return limits
    
    def check_rate_limit(self):
        """Check if current request exceeds rate limits"""
        if not current_app.config.get('RATE_LIMITING_ENABLED', True):
            return
            
        # Skip static files and health checks
        if (request.path.startswith('/static/') or 
            request.path == '/favicon.ico' or 
            request.path == '/health'):
            return
        
        client_id = self.get_client_identifier()
        endpoint_pattern = self.get_endpoint_pattern(request.path)
        limits = self.get_rate_limits(endpoint_pattern)
        
        # Check various time windows
        violations = []
        
        # Check minute limit
        if self._check_time_window(client_id, endpoint_pattern, 60, limits['requests_per_minute']):
            violations.append(f"Minute limit exceeded ({limits['requests_per_minute']}/min)")
        
        # Check hour limit  
        if self._check_time_window(client_id, endpoint_pattern, 3600, limits['requests_per_hour']):
            violations.append(f"Hour limit exceeded ({limits['requests_per_hour']}/hour)")
        
        # Check burst limit (10 seconds)
        if self._check_time_window(client_id, endpoint_pattern, 10, limits['burst_limit']):
            violations.append(f"Burst limit exceeded ({limits['burst_limit']}/10sec)")
        
        if violations:
            self._log_rate_limit_violation(client_id, endpoint_pattern, violations)
            
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please slow down.',
                'violations': violations,
                'retry_after': 60  # seconds
            }), 429
        
        # Record this request
        self._record_request(client_id, endpoint_pattern)
    
    def _check_time_window(self, client_id, endpoint_pattern, window_seconds, limit):
        """Check if requests in time window exceed limit"""
        try:
            with DatabaseConnection().get_connection() as conn:
                window_start = datetime.utcnow() - timedelta(seconds=window_seconds)
                
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM api_rate_limits 
                    WHERE ip_address = ? AND endpoint_pattern = ? 
                    AND window_start >= ? AND is_blocked = FALSE
                """, (client_id, endpoint_pattern, window_start.isoformat()))
                
                current_count = cursor.fetchone()[0]
                return current_count >= limit
                
        except Exception as e:
            current_app.logger.error(f"Rate limit check error: {e}")
            return False  # Allow request on error
    
    def _record_request(self, client_id, endpoint_pattern):
        """Record current request for rate limiting"""
        try:
            with DatabaseConnection().get_connection() as conn:
                # Use current minute as window for aggregation
                window_start = datetime.utcnow().replace(second=0, microsecond=0)
                
                conn.execute("""
                    INSERT INTO api_rate_limits (
                        ip_address, endpoint_pattern, window_start, request_count, last_request
                    ) VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(ip_address, endpoint_pattern, window_start) DO UPDATE SET
                        request_count = request_count + 1,
                        last_request = CURRENT_TIMESTAMP
                """, (client_id, endpoint_pattern, window_start.isoformat()))
                
        except Exception as e:
            current_app.logger.error(f"Rate limit recording error: {e}")
    
    def _log_rate_limit_violation(self, client_id, endpoint_pattern, violations):
        """Log rate limit violation"""
        try:
            with DatabaseConnection().get_connection() as conn:
                # Mark client as temporarily blocked
                window_start = datetime.utcnow().replace(second=0, microsecond=0)
                
                conn.execute("""
                    UPDATE api_rate_limits 
                    SET is_blocked = TRUE 
                    WHERE ip_address = ? AND endpoint_pattern = ? AND window_start = ?
                """, (client_id, endpoint_pattern, window_start.isoformat()))
                
                # Log to error tracking
                conn.execute("""
                    INSERT INTO error_tracking (
                        endpoint, method, error_type, error_message,
                        ip_address, user_agent, request_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    endpoint_pattern,
                    request.method,
                    'RateLimitViolation',
                    f"Rate limit violations: {'; '.join(violations)}",
                    client_id,
                    request.headers.get('User-Agent', '')[:500],
                    f"Endpoint: {endpoint_pattern}"
                ))
                
            current_app.logger.warning(f"Rate limit violation: {client_id} on {endpoint_pattern}")
            
        except Exception as e:
            current_app.logger.error(f"Rate limit violation logging error: {e}")
    
    def get_rate_limit_status(self, client_id=None):
        """Get current rate limit status for client"""
        if not client_id:
            client_id = self.get_client_identifier()
            
        try:
            with DatabaseConnection().get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        endpoint_pattern,
                        SUM(request_count) as total_requests,
                        MAX(last_request) as last_request,
                        MIN(window_start) as first_request,
                        SUM(CASE WHEN is_blocked THEN 1 ELSE 0 END) as blocked_windows
                    FROM api_rate_limits 
                    WHERE ip_address = ? AND window_start >= datetime('now', '-1 hour')
                    GROUP BY endpoint_pattern
                    ORDER BY total_requests DESC
                """, (client_id,))
                
                status = []
                for row in cursor.fetchall():
                    endpoint_limits = self.get_rate_limits(row[0])
                    
                    # Calculate remaining requests for current minute
                    minute_start = datetime.utcnow().replace(second=0, microsecond=0)
                    cursor_minute = conn.execute("""
                        SELECT request_count FROM api_rate_limits 
                        WHERE ip_address = ? AND endpoint_pattern = ? AND window_start = ?
                    """, (client_id, row[0], minute_start.isoformat()))
                    
                    minute_count = cursor_minute.fetchone()
                    current_minute_requests = minute_count[0] if minute_count else 0
                    
                    status.append({
                        'endpoint': row[0],
                        'total_requests_last_hour': row[1],
                        'requests_this_minute': current_minute_requests,
                        'minute_limit': endpoint_limits['requests_per_minute'],
                        'minute_remaining': max(0, endpoint_limits['requests_per_minute'] - current_minute_requests),
                        'hour_limit': endpoint_limits['requests_per_hour'],
                        'hour_remaining': max(0, endpoint_limits['requests_per_hour'] - row[1]),
                        'is_blocked': row[4] > 0,
                        'last_request': row[2]
                    })
                
                return {
                    'client_id': client_id,
                    'endpoints': status,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def reset_rate_limits(self, client_id=None, endpoint_pattern=None):
        """Reset rate limits for client/endpoint (admin function)"""
        try:
            with DatabaseConnection().get_connection() as conn:
                if client_id and endpoint_pattern:
                    conn.execute("""
                        DELETE FROM api_rate_limits 
                        WHERE ip_address = ? AND endpoint_pattern = ?
                    """, (client_id, endpoint_pattern))
                elif client_id:
                    conn.execute("""
                        DELETE FROM api_rate_limits 
                        WHERE ip_address = ?
                    """, (client_id,))
                else:
                    # Reset all old rate limit records (older than 1 hour)
                    conn.execute("""
                        DELETE FROM api_rate_limits 
                        WHERE window_start < datetime('now', '-1 hour')
                    """)
                
                return True
                
        except Exception as e:
            current_app.logger.error(f"Rate limit reset error: {e}")
            return False
    
    def get_top_rate_limited_clients(self, hours=24, limit=10):
        """Get clients with most rate limit violations"""
        try:
            with DatabaseConnection().get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        ip_address,
                        COUNT(*) as total_violations,
                        COUNT(DISTINCT endpoint_pattern) as endpoints_affected,
                        MAX(last_request) as last_violation
                    FROM api_rate_limits 
                    WHERE is_blocked = TRUE AND window_start >= datetime('now', '-{} hours')
                    GROUP BY ip_address
                    ORDER BY total_violations DESC
                    LIMIT ?
                """.format(hours), (limit,))
                
                return [
                    {
                        'ip_address': row[0],
                        'total_violations': row[1],
                        'endpoints_affected': row[2],
                        'last_violation': row[3]
                    } for row in cursor.fetchall()
                ]
                
        except Exception as e:
            current_app.logger.error(f"Failed to get rate limited clients: {e}")
            return []