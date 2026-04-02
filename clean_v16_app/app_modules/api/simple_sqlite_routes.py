"""
Simple SQLite-based API routes for testing Phase 3 integration.
Basic endpoints to test SQLite database connectivity.
"""

from flask import Blueprint, jsonify
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
simple_sqlite_api = Blueprint('simple_sqlite_api', __name__)


@simple_sqlite_api.route('/api/sqlite/simple-health', methods=['GET'])
def simple_sqlite_health():
    """Simple health check for SQLite API endpoints."""
    try:
        return jsonify({
            'status': 'healthy',
            'message': 'Simple SQLite API is working',
            'database': 'sqlite',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Simple SQLite health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })


@simple_sqlite_api.route('/api/sqlite/companies/test-count', methods=['GET'])
def test_companies_count():
    """Test endpoint to count companies in SQLite."""
    try:
        # Lazy import to avoid startup delays
        from ..database.repositories.company_repository import CompanyRepository
        
        repo = CompanyRepository()
        count = repo.count()
        
        return jsonify({
            'status': 'success',
            'companies_count': count,
            'message': f'Found {count} companies in SQLite database',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Companies count test failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })


@simple_sqlite_api.route('/api/sqlite/sic-codes/test-count', methods=['GET'])
def test_sic_codes_count():
    """Test endpoint to count SIC codes in SQLite."""
    try:
        # Lazy import to avoid startup delays
        from ..database.repositories.company_repository import SICCodeRepository
        
        repo = SICCodeRepository()
        count = repo.count()
        
        return jsonify({
            'status': 'success',
            'sic_codes_count': count,
            'message': f'Found {count} SIC codes in SQLite database',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"SIC codes count test failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })