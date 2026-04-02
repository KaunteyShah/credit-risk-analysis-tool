"""
Enhanced API Routes v2 - Advanced endpoints with comprehensive functionality
Includes analytics, batch operations, and performance monitoring endpoints
"""
# [DEAD FILE] api_v2 blueprint (prefix /api/v2) is registered ONLY via routes/__init__.py → factory.py.
# main.py uses flask_main.create_app() which never calls register_routes(). Blueprint is unreachable.
# Safe to delete this entire file — analytics/batch/performance routes are unused.

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import json

from app_modules.database.repositories.company_repository import CompanyRepository
from app_modules.database.connection import DatabaseConnection
from app_modules.middleware.audit_middleware import AuditMiddleware
from app_modules.middleware.performance_monitor import PerformanceMonitor
from app_modules.middleware.rate_limiter import RateLimiter

# Create API v2 blueprint
api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# Initialize repositories
company_repo = CompanyRepository()
audit_middleware = AuditMiddleware()
performance_monitor = PerformanceMonitor()
rate_limiter = RateLimiter()

@api_v2.route('/health', methods=['GET'])
def health_check():
    """Comprehensive API health check with system metrics"""
    try:
        # Test database connectivity
        with DatabaseConnection().get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM companies")
            company_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM api_audit_log WHERE timestamp >= datetime('now', '-1 hour')")
            recent_requests = cursor.fetchone()[0]
        
        # Get system metrics
        system_metrics = AuditMiddleware.get_system_metrics()
        
        # Get performance stats
        perf_stats = performance_monitor.get_real_time_stats()
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0',
            'database': {
                'connected': True,
                'company_count': company_count,
                'recent_requests_1h': recent_requests
            },
            'system': system_metrics,
            'performance': perf_stats,
            'features': {
                'audit_logging': True,
                'performance_monitoring': True,
                'rate_limiting': True,
                'analytics': True,
                'batch_operations': True
            }
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@api_v2.route('/companies/search', methods=['GET'])
def advanced_company_search():
    """
    Advanced company search with multiple filters and pagination
    
    Query Parameters:
    - q: Text search query
    - country: Filter by country
    - min_employees, max_employees: Employee count range
    - sic_code: Filter by SIC code
    - min_revenue, max_revenue: Revenue range (if available)
    - sort_by: Sort field (name, employees, country)
    - sort_order: asc or desc
    - limit: Results per page (max 100)
    - offset: Pagination offset
    """
    try:
        # Parse query parameters
        query = request.args.get('q', '').strip()
        country = request.args.get('country', '').strip()
        min_employees = request.args.get('min_employees', type=int)
        max_employees = request.args.get('max_employees', type=int)
        sic_code = request.args.get('sic_code', '').strip()
        min_revenue = request.args.get('min_revenue', type=float)
        max_revenue = request.args.get('max_revenue', type=float)
        
        # Pagination and sorting
        limit = min(request.args.get('limit', 20, type=int), 100)
        offset = request.args.get('offset', 0, type=int)
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Validate sort parameters
        valid_sort_fields = ['name', 'employees', 'country', 'created_at']
        if sort_by not in valid_sort_fields:
            sort_by = 'name'
        
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'
        
        # Build search criteria dictionary
        search_criteria = {
            'search': query,  # Changed from 'query' to 'search' to match repository
            'country': country,
            'min_employees': min_employees,
            'max_employees': max_employees,
            'sic_code': sic_code,
            'min_revenue': min_revenue,
            'max_revenue': max_revenue,
            'sort_by': sort_by,
            'sort_order': sort_order
        }
        
        # Execute search with correct method signature
        results = company_repo.advanced_search(criteria=search_criteria, limit=limit, offset=offset)
        
        # Get total count for pagination
        count_criteria = {
            k: v for k, v in search_criteria.items() 
            if k not in ['sort_by', 'sort_order']
        }
        total_count = company_repo.count_advanced_search(criteria=count_criteria)
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = offset + limit < total_count
        has_prev = offset > 0
        
        return jsonify({
            'companies': results,
            'pagination': {
                'total_count': total_count,
                'total_pages': total_pages,
                'current_page': (offset // limit) + 1,
                'per_page': limit,
                'has_next': has_next,
                'has_prev': has_prev,
                'next_offset': offset + limit if has_next else None,
                'prev_offset': max(0, offset - limit) if has_prev else None
            },
            'search_criteria': search_criteria,
            'response_time': None  # Will be added by audit middleware
        })
        
    except Exception as e:
        current_app.logger.error(f"Advanced search error: {e}")
        return jsonify({
            'error': 'Search failed',
            'message': str(e)
        }), 500

@api_v2.route('/companies/batch', methods=['POST'])
def batch_company_operations():
    """
    Batch operations for companies (create, update, delete multiple)
    
    Request Body:
    {
        "operations": [
            {"action": "create", "data": {...}},
            {"action": "update", "id": 123, "data": {...}},
            {"action": "delete", "id": 456}
        ]
    }
    """
    try:
        data = request.get_json()
        if not data or 'operations' not in data:
            return jsonify({'error': 'Invalid request format'}), 400
        
        operations = data['operations']
        if not isinstance(operations, list) or len(operations) > 100:
            return jsonify({'error': 'Max 100 operations per batch'}), 400
        
        results = []
        success_count = 0
        error_count = 0
        
        with DatabaseConnection().get_connection() as conn:
            for i, operation in enumerate(operations):
                try:
                    action = operation.get('action')
                    
                    if action == 'create':
                        # Create new company
                        company_data = operation.get('data', {})
                        # Validate required fields
                        if not company_data.get('name'):
                            raise ValueError("Company name is required")
                        
                        cursor = conn.execute("""
                            INSERT INTO companies (name, country, employees, description)
                            VALUES (?, ?, ?, ?)
                        """, (
                            company_data['name'],
                            company_data.get('country', ''),
                            company_data.get('employees', 0),
                            company_data.get('description', '')
                        ))
                        
                        results.append({
                            'operation_index': i,
                            'action': action,
                            'status': 'success',
                            'company_id': cursor.lastrowid
                        })
                        success_count += 1
                        
                    elif action == 'update':
                        # Update existing company
                        company_id = operation.get('id')
                        company_data = operation.get('data', {})
                        
                        if not company_id:
                            raise ValueError("Company ID is required for update")
                        
                        # Build dynamic update query
                        update_fields = []
                        update_values = []
                        
                        for field in ['name', 'country', 'employees', 'description']:
                            if field in company_data:
                                update_fields.append(f"{field} = ?")
                                update_values.append(company_data[field])
                        
                        if update_fields:
                            update_values.append(company_id)
                            cursor = conn.execute(f"""
                                UPDATE companies SET {', '.join(update_fields)}
                                WHERE id = ?
                            """, update_values)
                            
                            if cursor.rowcount == 0:
                                raise ValueError(f"Company {company_id} not found")
                        
                        results.append({
                            'operation_index': i,
                            'action': action,
                            'status': 'success',
                            'company_id': company_id,
                            'updated_fields': list(company_data.keys())
                        })
                        success_count += 1
                        
                    elif action == 'delete':
                        # Delete company
                        company_id = operation.get('id')
                        
                        if not company_id:
                            raise ValueError("Company ID is required for delete")
                        
                        cursor = conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
                        
                        if cursor.rowcount == 0:
                            raise ValueError(f"Company {company_id} not found")
                        
                        results.append({
                            'operation_index': i,
                            'action': action,
                            'status': 'success',
                            'company_id': company_id
                        })
                        success_count += 1
                        
                    else:
                        raise ValueError(f"Unknown action: {action}")
                        
                except Exception as e:
                    results.append({
                        'operation_index': i,
                        'action': operation.get('action', 'unknown'),
                        'status': 'error',
                        'error': str(e)
                    })
                    error_count += 1
            
            # Commit all successful operations
            if success_count > 0:
                conn.commit()
        
        return jsonify({
            'batch_results': results,
            'summary': {
                'total_operations': len(operations),
                'successful': success_count,
                'failed': error_count,
                'success_rate': round((success_count / len(operations)) * 100, 2)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Batch operations error: {e}")
        return jsonify({
            'error': 'Batch operation failed',
            'message': str(e)
        }), 500

@api_v2.route('/analytics/api-usage', methods=['GET'])
def api_usage_analytics():
    """
    Get comprehensive API usage analytics
    
    Query Parameters:
    - days: Number of days to analyze (default 7, max 30)
    - endpoint: Filter by specific endpoint
    - group_by: Group results by 'hour', 'day', or 'endpoint'
    """
    try:
        days = min(request.args.get('days', 7, type=int), 30)
        endpoint_filter = request.args.get('endpoint', '').strip()
        group_by = request.args.get('group_by', 'day')
        
        if group_by not in ['hour', 'day', 'endpoint']:
            group_by = 'day'
        
        with DatabaseConnection().get_connection() as conn:
            # Base query with date filter
            base_where = f"WHERE timestamp >= datetime('now', '-{days} days')"
            if endpoint_filter:
                base_where += f" AND endpoint LIKE '%{endpoint_filter}%'"
            
            if group_by == 'hour':
                cursor = conn.execute(f"""
                    SELECT 
                        strftime('%Y-%m-%d %H:00:00', timestamp) as time_period,
                        COUNT(*) as total_requests,
                        AVG(response_time_ms) as avg_response_time,
                        SUM(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 ELSE 0 END) as success_count,
                        SUM(CASE WHEN response_status >= 400 THEN 1 ELSE 0 END) as error_count,
                        COUNT(DISTINCT ip_address) as unique_users,
                        SUM(response_size_bytes) as total_bytes
                    FROM api_audit_log 
                    {base_where}
                    GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
                    ORDER BY time_period DESC
                """)
            elif group_by == 'day':
                cursor = conn.execute(f"""
                    SELECT 
                        date(timestamp) as time_period,
                        COUNT(*) as total_requests,
                        AVG(response_time_ms) as avg_response_time,
                        SUM(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 ELSE 0 END) as success_count,
                        SUM(CASE WHEN response_status >= 400 THEN 1 ELSE 0 END) as error_count,
                        COUNT(DISTINCT ip_address) as unique_users,
                        SUM(response_size_bytes) as total_bytes
                    FROM api_audit_log 
                    {base_where}
                    GROUP BY date(timestamp)
                    ORDER BY time_period DESC
                """)
            else:  # group_by == 'endpoint'
                cursor = conn.execute(f"""
                    SELECT 
                        endpoint as time_period,
                        COUNT(*) as total_requests,
                        AVG(response_time_ms) as avg_response_time,
                        SUM(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 ELSE 0 END) as success_count,
                        SUM(CASE WHEN response_status >= 400 THEN 1 ELSE 0 END) as error_count,
                        COUNT(DISTINCT ip_address) as unique_users,
                        SUM(response_size_bytes) as total_bytes
                    FROM api_audit_log 
                    {base_where}
                    GROUP BY endpoint
                    ORDER BY total_requests DESC
                """)
            
            analytics_data = []
            for row in cursor.fetchall():
                analytics_data.append({
                    'period': row[0],
                    'total_requests': row[1],
                    'avg_response_time_ms': round(row[2] or 0, 2),
                    'success_count': row[3],
                    'error_count': row[4],
                    'error_rate_percent': round((row[4] / max(row[1], 1)) * 100, 2),
                    'unique_users': row[5],
                    'total_bytes_served': row[6],
                    'avg_bytes_per_request': round((row[6] / max(row[1], 1)), 2)
                })
            
            # Get summary statistics
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_requests,
                    AVG(response_time_ms) as avg_response_time,
                    MIN(response_time_ms) as min_response_time,
                    MAX(response_time_ms) as max_response_time,
                    COUNT(DISTINCT endpoint) as unique_endpoints,
                    COUNT(DISTINCT ip_address) as unique_users,
                    SUM(response_size_bytes) as total_bytes
                FROM api_audit_log 
                {base_where}
            """)
            
            summary = cursor.fetchone()
            
            return jsonify({
                'analytics': analytics_data,
                'summary': {
                    'period_days': days,
                    'group_by': group_by,
                    'total_requests': summary[0] or 0,
                    'avg_response_time_ms': round(summary[1] or 0, 2),
                    'min_response_time_ms': summary[2] or 0,
                    'max_response_time_ms': summary[3] or 0,
                    'unique_endpoints': summary[4] or 0,
                    'unique_users': summary[5] or 0,
                    'total_bytes_served': summary[6] or 0
                },
                'filters': {
                    'days': days,
                    'endpoint': endpoint_filter,
                    'group_by': group_by
                },
                'timestamp': datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        current_app.logger.error(f"Analytics error: {e}")
        return jsonify({
            'error': 'Analytics retrieval failed',
            'message': str(e)
        }), 500

@api_v2.route('/analytics/performance', methods=['GET'])
def performance_analytics():
    """Get detailed performance analytics and metrics"""
    try:
        hours = min(request.args.get('hours', 24, type=int), 168)  # Max 1 week
        
        # Get comprehensive performance summary
        summary = performance_monitor.get_performance_summary(hours)
        
        # Get real-time stats
        real_time = performance_monitor.get_real_time_stats()
        
        return jsonify({
            'performance_summary': summary,
            'real_time_stats': real_time,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Performance analytics error: {e}")
        return jsonify({
            'error': 'Performance analytics failed',
            'message': str(e)
        }), 500

@api_v2.route('/analytics/errors', methods=['GET'])
def error_analytics():
    """Get detailed error analysis and patterns"""
    try:
        days = min(request.args.get('days', 7, type=int), 30)
        
        with DatabaseConnection().get_connection() as conn:
            # Error summary by status code
            cursor = conn.execute("""
                SELECT 
                    response_status,
                    COUNT(*) as error_count,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(DISTINCT ip_address) as unique_ips,
                    COUNT(DISTINCT endpoint) as unique_endpoints
                FROM api_audit_log 
                WHERE response_status >= 400 AND timestamp >= datetime('now', '-{} days')
                GROUP BY response_status
                ORDER BY error_count DESC
            """.format(days))
            
            error_by_status = [
                {
                    'status_code': row[0],
                    'error_count': row[1],
                    'avg_response_time_ms': round(row[2] or 0, 2),
                    'unique_ips': row[3],
                    'unique_endpoints': row[4]
                } for row in cursor.fetchall()
            ]
            
            # Error trends by day
            cursor = conn.execute("""
                SELECT 
                    date(timestamp) as error_date,
                    response_status,
                    COUNT(*) as error_count
                FROM api_audit_log 
                WHERE response_status >= 400 AND timestamp >= datetime('now', '-{} days')
                GROUP BY date(timestamp), response_status
                ORDER BY error_date DESC, error_count DESC
            """.format(days))
            
            error_trends = [
                {
                    'date': row[0],
                    'status_code': row[1],
                    'error_count': row[2]
                } for row in cursor.fetchall()
            ]
            
            # Top error endpoints
            cursor = conn.execute("""
                SELECT 
                    endpoint,
                    method,
                    COUNT(*) as error_count,
                    AVG(response_time_ms) as avg_response_time,
                    GROUP_CONCAT(DISTINCT CAST(response_status AS TEXT)) as status_codes
                FROM api_audit_log 
                WHERE response_status >= 400 AND timestamp >= datetime('now', '-{} days')
                GROUP BY endpoint, method
                ORDER BY error_count DESC
                LIMIT 10
            """.format(days))
            
            top_error_endpoints = [
                {
                    'endpoint': row[0],
                    'method': row[1],
                    'error_count': row[2],
                    'avg_response_time_ms': round(row[3] or 0, 2),
                    'status_codes': row[4].split(',') if row[4] else []
                } for row in cursor.fetchall()
            ]
            
            # Error tracking records (from error_tracking table)
            cursor = conn.execute("""
                SELECT 
                    error_type,
                    COUNT(*) as occurrence_count,
                    COUNT(DISTINCT ip_address) as unique_ips,
                    MAX(timestamp) as last_occurrence,
                    SUM(CASE WHEN resolved THEN 1 ELSE 0 END) as resolved_count
                FROM error_tracking 
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY error_type
                ORDER BY occurrence_count DESC
            """.format(days))
            
            error_types = [
                {
                    'error_type': row[0],
                    'occurrence_count': row[1],
                    'unique_ips': row[2],
                    'last_occurrence': row[3],
                    'resolved_count': row[4],
                    'resolution_rate': round((row[4] / max(row[1], 1)) * 100, 2)
                } for row in cursor.fetchall()
            ]
            
            return jsonify({
                'error_analysis': {
                    'by_status_code': error_by_status,
                    'trends': error_trends,
                    'top_error_endpoints': top_error_endpoints,
                    'error_types': error_types
                },
                'period_days': days,
                'timestamp': datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        current_app.logger.error(f"Error analytics error: {e}")
        return jsonify({
            'error': 'Error analytics failed',
            'message': str(e)
        }), 500

@api_v2.route('/system/status', methods=['GET'])
def system_status():
    """Get comprehensive system status and health metrics"""
    try:
        # Get system metrics
        system_metrics = AuditMiddleware.get_system_metrics()
        
        # Get rate limiting status for current client
        rate_limit_status = rate_limiter.get_rate_limit_status()
        
        # Get recent alerts/issues
        with DatabaseConnection().get_connection() as conn:
            cursor = conn.execute("""
                SELECT error_type, error_message, timestamp
                FROM error_tracking 
                WHERE error_type IN ('PerformanceAlert', 'RateLimitViolation', 'SystemError')
                AND timestamp >= datetime('now', '-24 hours')
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            
            recent_alerts = [
                {
                    'type': row[0],
                    'message': row[1],
                    'timestamp': row[2]
                } for row in cursor.fetchall()
            ]
        
        return jsonify({
            'system_health': system_metrics,
            'rate_limits': rate_limit_status,
            'recent_alerts': recent_alerts,
            'api_version': '2.0',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'System status check failed',
            'message': str(e)
        }), 500

# Register error handlers
@api_v2.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested API endpoint does not exist',
        'available_endpoints': [
            '/api/v2/health',
            '/api/v2/companies/search',
            '/api/v2/companies/batch',
            '/api/v2/analytics/api-usage',
            '/api/v2/analytics/performance',
            '/api/v2/analytics/errors',
            '/api/v2/system/status'
        ]
    }), 404

@api_v2.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500