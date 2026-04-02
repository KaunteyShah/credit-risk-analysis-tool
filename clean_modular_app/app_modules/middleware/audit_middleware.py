"""
Audit Middleware for comprehensive API request/response logging
Tracks all API calls with performance metrics and error handling
"""

import time
import json
import psutil
import os
from datetime import datetime
from flask import request, g, current_app
from app_modules.database.connection import DatabaseConnection

class AuditMiddleware:
    """
    Flask middleware for comprehensive API audit logging
    Automatically tracks all requests, responses, and performance metrics
    """
    
    def __init__(self, app=None):
        self.enabled = True
        self.exclude_paths = ['/static/', '/favicon.ico', '/health']
        self.max_payload_size = 10240  # 10KB max payload logging
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown)
        
        # Store reference for configuration
        app.config.setdefault('AUDIT_ENABLED', True)
        app.config.setdefault('AUDIT_EXCLUDE_PATHS', self.exclude_paths)
        
        print("🔧 Audit Middleware initialized")
    
    def should_audit_request(self):
        """Determine if current request should be audited"""
        if not self.enabled:
            return False
            
        # Skip static files and health checks
        path = request.path
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
                
        return True
    
    def before_request(self):
        """Capture request start time and data"""
        if not self.should_audit_request():
            return
            
        g.start_time = time.time()
        g.request_data = {
            'endpoint': request.endpoint or request.path,
            'method': request.method,
            'ip_address': self._get_client_ip(),
            'user_agent': request.headers.get('User-Agent', '')[:500],  # Limit length
            'payload': self._get_request_payload(),
            'content_type': request.headers.get('Content-Type', ''),
            'query_params': dict(request.args)
        }
    
    def after_request(self, response):
        """Log completed request with response data"""
        if not self.should_audit_request() or not hasattr(g, 'start_time'):
            return response
            
        try:
            response_time_ms = int((time.time() - g.start_time) * 1000)
            
            # Safely get response size without accessing data in passthrough mode
            try:
                response_size = len(response.get_data(as_text=False)) if hasattr(response, 'get_data') else 0
            except (RuntimeError, AttributeError):
                # Handle direct passthrough mode or other response types
                response_size = int(response.headers.get('Content-Length', 0))
            
            # Log to database asynchronously
            self._log_api_call(
                endpoint=g.request_data['endpoint'],
                method=g.request_data['method'],
                response_status=response.status_code,
                response_time_ms=response_time_ms,
                response_size_bytes=response_size,
                ip_address=g.request_data['ip_address'],
                user_agent=g.request_data['user_agent'],
                request_payload=g.request_data['payload'],
                query_params=g.request_data['query_params'],
                content_type=g.request_data['content_type']
            )
            
            # Add performance headers
            response.headers['X-Response-Time'] = f"{response_time_ms}ms"
            response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
            
        except Exception as e:
            # Don't let audit errors break the response
            current_app.logger.error(f"Audit middleware error: {e}")
            
        return response
    
    def teardown(self, exception):
        """Handle any cleanup on request teardown"""
        if exception and hasattr(g, 'request_data'):
            # Log errors that occurred during request processing
            self._log_error(
                endpoint=g.request_data.get('endpoint', 'unknown'),
                method=g.request_data.get('method', 'unknown'),
                error_message=str(exception),
                ip_address=g.request_data.get('ip_address', ''),
                user_agent=g.request_data.get('user_agent', ''),
                request_data=g.request_data.get('payload', '')
            )
    
    def _get_client_ip(self):
        """Get the real client IP address"""
        # Check for forwarded headers first (for reverse proxies)
        ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if not ip:
            ip = request.headers.get('X-Real-IP', '')
        if not ip:
            ip = request.remote_addr or 'unknown'
        return ip[:45]  # Limit length for IPv6
    
    def _get_request_payload(self):
        """Safely extract request payload for logging"""
        try:
            content_length = request.content_length or 0
            if request.is_json and content_length < self.max_payload_size:
                payload = request.get_json()
                # Sanitize sensitive data
                return self._sanitize_payload(payload)
            elif request.form and content_length < self.max_payload_size:
                return self._sanitize_payload(dict(request.form))
            else:
                return None
        except Exception:
            return None
    
    def _sanitize_payload(self, payload):
        """Remove sensitive information from payload before logging"""
        if not isinstance(payload, dict):
            return str(payload)[:500]  # Limit string length
            
        sensitive_keys = ['password', 'token', 'key', 'secret', 'auth', 'credential']
        sanitized = {}
        
        for key, value in payload.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = str(value)[:200]  # Limit value length
                
        return json.dumps(sanitized)[:1000]  # Limit total payload size
    
    def _log_api_call(self, **kwargs):
        """Log API call to database"""
        try:
            with DatabaseConnection().get_connection() as conn:
                conn.execute("""
                    INSERT INTO api_audit_log (
                        endpoint, method, response_status, response_time_ms,
                        response_size_bytes, ip_address, user_agent, request_payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    kwargs['endpoint'],
                    kwargs['method'],
                    kwargs['response_status'],
                    kwargs['response_time_ms'],
                    kwargs['response_size_bytes'],
                    kwargs['ip_address'],
                    kwargs['user_agent'],
                    kwargs['request_payload']
                ))
                
                # Update daily performance metrics
                self._update_performance_metrics(conn, **kwargs)
                
        except Exception as e:
            current_app.logger.error(f"Failed to log API call: {e}")
    
    def _update_performance_metrics(self, conn, **kwargs):
        """Update aggregated performance metrics"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Upsert performance metrics
            conn.execute("""
                INSERT INTO api_performance_metrics (
                    date, endpoint, method, total_calls, avg_response_time_ms,
                    min_response_time_ms, max_response_time_ms, success_count, 
                    error_count, total_bytes_served
                ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, endpoint, method) DO UPDATE SET
                    total_calls = total_calls + 1,
                    avg_response_time_ms = (avg_response_time_ms * total_calls + ?) / (total_calls + 1),
                    min_response_time_ms = MIN(min_response_time_ms, ?),
                    max_response_time_ms = MAX(max_response_time_ms, ?),
                    success_count = success_count + CASE WHEN ? >= 200 AND ? < 300 THEN 1 ELSE 0 END,
                    error_count = error_count + CASE WHEN ? >= 400 THEN 1 ELSE 0 END,
                    total_bytes_served = total_bytes_served + ?,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                today, kwargs['endpoint'], kwargs['method'],
                kwargs['response_time_ms'], kwargs['response_time_ms'], kwargs['response_time_ms'],
                1 if 200 <= kwargs['response_status'] < 300 else 0,
                1 if kwargs['response_status'] >= 400 else 0,
                kwargs['response_size_bytes'],
                kwargs['response_time_ms'], kwargs['response_time_ms'], kwargs['response_time_ms'],
                kwargs['response_status'], kwargs['response_status'],
                kwargs['response_status'],
                kwargs['response_size_bytes']
            ))
            
        except Exception as e:
            current_app.logger.error(f"Failed to update performance metrics: {e}")
    
    def _log_error(self, **kwargs):
        """Log error to error tracking table"""
        try:
            with DatabaseConnection().get_connection() as conn:
                conn.execute("""
                    INSERT INTO error_tracking (
                        endpoint, method, error_type, error_message,
                        ip_address, user_agent, request_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    kwargs['endpoint'],
                    kwargs['method'],
                    'RequestError',
                    kwargs['error_message'][:1000],
                    kwargs['ip_address'],
                    kwargs['user_agent'],
                    kwargs['request_data']
                ))
        except Exception as e:
            current_app.logger.error(f"Failed to log error: {e}")
    
    @staticmethod
    def get_system_metrics():
        """Get current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage_percent': cpu_percent,
                'memory_usage_mb': memory.used / (1024 * 1024),
                'memory_total_mb': memory.total / (1024 * 1024),
                'disk_usage_mb': disk.used / (1024 * 1024),
                'disk_total_mb': disk.total / (1024 * 1024),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def log_system_health(self):
        """Log current system health metrics"""
        try:
            metrics = self.get_system_metrics()
            
            if 'error' not in metrics:
                with DatabaseConnection().get_connection() as conn:
                    # Get recent API statistics
                    cursor = conn.execute("""
                        SELECT COUNT(*) as requests, 
                               COALESCE(AVG(response_time_ms), 0) as avg_time,
                               COALESCE(SUM(CASE WHEN response_status >= 400 THEN 1 ELSE 0 END), 0) as errors
                        FROM api_audit_log 
                        WHERE timestamp >= datetime('now', '-1 hour')
                    """)
                    api_stats = cursor.fetchone()
                    
                    # Safely calculate error rate with null checks
                    requests_count = api_stats[0] or 0
                    errors_count = api_stats[2] or 0
                    error_rate = (errors_count / max(requests_count, 1)) * 100 if requests_count > 0 else 0
                    
                    conn.execute("""
                        INSERT INTO system_health_metrics (
                            cpu_usage_percent, memory_usage_mb, disk_usage_mb,
                            total_requests_last_hour, avg_response_time_last_hour,
                            error_rate_last_hour, database_size_mb
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metrics['cpu_usage_percent'],
                        metrics['memory_usage_mb'],
                        metrics['disk_usage_mb'],
                        requests_count,
                        api_stats[1] or 0,
                        error_rate,
                        self._get_database_size()
                    ))
                    
        except Exception as e:
            current_app.logger.error(f"Failed to log system health: {e}")
    
    def _get_database_size(self):
        """Get current database size in MB"""
        try:
            db_path = os.path.join('data', 'credit_risk.db')
            if os.path.exists(db_path):
                return os.path.getsize(db_path) / (1024 * 1024)
        except Exception:
            pass
        return 0.0