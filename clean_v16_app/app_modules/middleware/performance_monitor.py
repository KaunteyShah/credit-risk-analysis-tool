"""
Performance Monitor - Advanced system performance tracking and alerting
"""

import time
import threading
from datetime import datetime, timedelta
from flask import current_app
from app_modules.database.connection import DatabaseConnection

class PerformanceMonitor:
    """
    Advanced performance monitoring with real-time alerts
    """
    
    def __init__(self, app=None):
        self.monitoring_active = False
        self.alert_thresholds = {
            'avg_response_time': 1000,  # ms
            'error_rate': 5.0,  # percentage
            'cpu_usage': 80.0,  # percentage
            'memory_usage': 85.0,  # percentage
            'requests_per_minute': 1000
        }
        self.monitor_thread = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize performance monitor with Flask app"""
        app.config.setdefault('PERFORMANCE_MONITORING', True)
        app.config.setdefault('ALERT_THRESHOLDS', self.alert_thresholds)
        
        # Update thresholds from config
        self.alert_thresholds.update(app.config.get('ALERT_THRESHOLDS', {}))
        
        print("📊 Performance Monitor initialized")
    
    def start_monitoring(self):
        """Start background performance monitoring"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("🚀 Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        print("🛑 Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Check performance metrics every 60 seconds
                self._check_performance_metrics()
                time.sleep(60)
            except Exception as e:
                if current_app:
                    current_app.logger.error(f"Performance monitoring error: {e}")
                time.sleep(30)  # Shorter sleep on error
    
    def _check_performance_metrics(self):
        """Check current performance against thresholds"""
        try:
            with DatabaseConnection().get_connection() as conn:
                # Get recent API performance
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_requests,
                        COALESCE(AVG(response_time_ms), 0) as avg_response_time,
                        COALESCE(SUM(CASE WHEN response_status >= 400 THEN 1 ELSE 0 END), 0) as error_count
                    FROM api_audit_log 
                    WHERE timestamp >= datetime('now', '-5 minutes')
                """)
                
                api_metrics = cursor.fetchone()
                
                if api_metrics and api_metrics[0] > 0:  # Has requests
                    # Safely calculate metrics with null checks
                    errors = api_metrics[2] or 0
                    requests = api_metrics[0] or 0
                    error_rate = (errors / max(requests, 1)) * 100
                    requests_per_minute = requests / 5  # 5-minute window
                    
                    # Check thresholds
                    alerts = []
                    
                    if api_metrics[1] > self.alert_thresholds['avg_response_time']:
                        alerts.append(f"High response time: {api_metrics[1]:.0f}ms")
                    
                    if error_rate > self.alert_thresholds['error_rate']:
                        alerts.append(f"High error rate: {error_rate:.1f}%")
                    
                    if requests_per_minute > self.alert_thresholds['requests_per_minute']:
                        alerts.append(f"High request rate: {requests_per_minute:.0f}/min")
                    
                    # Log alerts if any
                    if alerts:
                        self._log_performance_alert(alerts, {
                            'avg_response_time': api_metrics[1],
                            'error_rate': error_rate,
                            'requests_per_minute': requests_per_minute
                        })
                
                # Get system health metrics
                cursor = conn.execute("""
                    SELECT cpu_usage_percent, memory_usage_mb, disk_usage_mb
                    FROM system_health_metrics 
                    ORDER BY timestamp DESC LIMIT 1
                """)
                
                system_metrics = cursor.fetchone()
                if system_metrics:
                    system_alerts = []
                    
                    if system_metrics[0] > self.alert_thresholds['cpu_usage']:
                        system_alerts.append(f"High CPU usage: {system_metrics[0]:.1f}%")
                    
                    # Calculate memory usage percentage (assuming 8GB total for example)
                    memory_total = 8 * 1024  # 8GB in MB
                    memory_usage = system_metrics[1] or 0
                    memory_percent = (memory_usage / memory_total) * 100
                    
                    if memory_percent > self.alert_thresholds['memory_usage']:
                        system_alerts.append(f"High memory usage: {memory_percent:.1f}%")
                    
                    if system_alerts:
                        self._log_performance_alert(system_alerts, {
                            'cpu_usage': system_metrics[0],
                            'memory_usage_mb': system_metrics[1],
                            'memory_usage_percent': memory_percent
                        })
                        
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Performance check error: {e}")
    
    def _log_performance_alert(self, alerts, metrics):
        """Log performance alerts"""
        alert_message = "; ".join(alerts)
        
        try:
            with DatabaseConnection().get_connection() as conn:
                conn.execute("""
                    INSERT INTO error_tracking (
                        endpoint, method, error_type, error_message,
                        ip_address, user_agent, request_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    'SYSTEM',
                    'MONITOR',
                    'PerformanceAlert',
                    alert_message,
                    'localhost',
                    'PerformanceMonitor',
                    str(metrics)
                ))
                
            if current_app:
                current_app.logger.warning(f"Performance Alert: {alert_message}")
                
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Failed to log performance alert: {e}")
    
    def get_performance_summary(self, hours=24):
        """Get performance summary for the last N hours"""
        try:
            with DatabaseConnection().get_connection() as conn:
                # API Performance Summary
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_requests,
                        AVG(response_time_ms) as avg_response_time,
                        MIN(response_time_ms) as min_response_time,
                        MAX(response_time_ms) as max_response_time,
                        SUM(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 ELSE 0 END) as success_count,
                        SUM(CASE WHEN response_status >= 400 THEN 1 ELSE 0 END) as error_count,
                        COUNT(DISTINCT ip_address) as unique_users,
                        SUM(response_size_bytes) as total_bytes_served
                    FROM api_audit_log 
                    WHERE timestamp >= datetime('now', '-{} hours')
                """.format(hours))
                
                api_summary = cursor.fetchone()
                
                # Top Slow Endpoints
                cursor = conn.execute("""
                    SELECT endpoint, method, AVG(response_time_ms) as avg_time, COUNT(*) as count
                    FROM api_audit_log 
                    WHERE timestamp >= datetime('now', '-{} hours')
                    GROUP BY endpoint, method
                    ORDER BY avg_time DESC
                    LIMIT 5
                """.format(hours))
                
                slow_endpoints = cursor.fetchall()
                
                # Error Summary
                cursor = conn.execute("""
                    SELECT response_status, COUNT(*) as count
                    FROM api_audit_log 
                    WHERE timestamp >= datetime('now', '-{} hours') AND response_status >= 400
                    GROUP BY response_status
                    ORDER BY count DESC
                """.format(hours))
                
                error_summary = cursor.fetchall()
                
                # System Health Trend
                cursor = conn.execute("""
                    SELECT 
                        AVG(cpu_usage_percent) as avg_cpu,
                        AVG(memory_usage_mb) as avg_memory,
                        AVG(avg_response_time_last_hour) as avg_hourly_response_time,
                        AVG(error_rate_last_hour) as avg_hourly_error_rate
                    FROM system_health_metrics 
                    WHERE timestamp >= datetime('now', '-{} hours')
                """.format(hours))
                
                system_trend = cursor.fetchone()
                
                return {
                    'period_hours': hours,
                    'api_performance': {
                        'total_requests': api_summary[0] or 0,
                        'avg_response_time_ms': round(api_summary[1] or 0, 2),
                        'min_response_time_ms': api_summary[2] or 0,
                        'max_response_time_ms': api_summary[3] or 0,
                        'success_count': api_summary[4] or 0,
                        'error_count': api_summary[5] or 0,
                        'error_rate_percent': round((api_summary[5] / max(api_summary[0], 1)) * 100, 2),
                        'unique_users': api_summary[6] or 0,
                        'total_bytes_served': api_summary[7] or 0
                    },
                    'slow_endpoints': [
                        {
                            'endpoint': row[0],
                            'method': row[1], 
                            'avg_response_time_ms': round(row[2], 2),
                            'request_count': row[3]
                        } for row in slow_endpoints
                    ],
                    'error_summary': [
                        {'status_code': row[0], 'count': row[1]} 
                        for row in error_summary
                    ],
                    'system_health': {
                        'avg_cpu_percent': round(system_trend[0] or 0, 2),
                        'avg_memory_mb': round(system_trend[1] or 0, 2),
                        'avg_response_time_ms': round(system_trend[2] or 0, 2),
                        'avg_error_rate_percent': round(system_trend[3] or 0, 2)
                    } if system_trend else None
                }
                
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Failed to get performance summary: {e}")
            return {'error': str(e)}
    
    def get_real_time_stats(self):
        """Get real-time performance statistics"""
        try:
            with DatabaseConnection().get_connection() as conn:
                # Last 5 minutes stats
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as requests_last_5min,
                        AVG(response_time_ms) as avg_response_time,
                        SUM(CASE WHEN response_status >= 400 THEN 1 ELSE 0 END) as errors_last_5min
                    FROM api_audit_log 
                    WHERE timestamp >= datetime('now', '-5 minutes')
                """)
                
                stats = cursor.fetchone()
                
                # Active endpoints (last hour)
                cursor = conn.execute("""
                    SELECT COUNT(DISTINCT endpoint) as active_endpoints
                    FROM api_audit_log 
                    WHERE timestamp >= datetime('now', '-1 hour')
                """)
                
                active_endpoints = cursor.fetchone()[0]
                
                return {
                    'timestamp': datetime.utcnow().isoformat(),
                    'requests_last_5min': stats[0] or 0,
                    'avg_response_time_ms': round(stats[1] or 0, 2),
                    'errors_last_5min': stats[2] or 0,
                    'error_rate_percent': round((stats[2] / max(stats[0], 1)) * 100, 2),
                    'active_endpoints_last_hour': active_endpoints or 0
                }
                
        except Exception as e:
            return {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}