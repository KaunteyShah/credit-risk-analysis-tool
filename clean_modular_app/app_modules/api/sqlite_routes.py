"""
SQLite-based API routes for Phase 3 integration.
Modern API endpoints using SQLite database with advanced filtering and search.
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..database.repositories.company_repository import CompanyRepository, SICCodeRepository, CompanySICCodeRepository
from ..database.connection import db_connection

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
sqlite_api = Blueprint('sqlite_api', __name__)

# Initialize repositories lazily to avoid startup delays
company_repo = None
sic_repo = None 
company_sic_repo = None

def get_repositories():
    """Lazy load repositories to avoid startup delays."""
    global company_repo, sic_repo, company_sic_repo
    if company_repo is None:
        company_repo = CompanyRepository()
        sic_repo = SICCodeRepository()
        company_sic_repo = CompanySICCodeRepository()
    return company_repo, sic_repo, company_sic_repo


@sqlite_api.route('/api/sqlite/health', methods=['GET'])
def sqlite_health():
    """Health check for SQLite API endpoints."""
    try:
        # Test database connection with lazy-loaded repositories
        comp_repo, sic_repo_inst, comp_sic_repo = get_repositories()
        companies_count = comp_repo.count()
        sic_codes_count = sic_repo_inst.count()
        relationships_count = comp_sic_repo.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'sqlite',
            'timestamp': datetime.now().isoformat(),
            'stats': {
                'companies': companies_count,
                'sic_codes': sic_codes_count,
                'relationships': relationships_count
            }
        })
    except Exception as e:
        logger.error(f"SQLite health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@sqlite_api.route('/api/sqlite/companies', methods=['GET'])
def get_companies():
    """Get companies with advanced filtering and pagination."""
    try:
        # Extract query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
        # Build filters from query parameters
        filters = {}
        
        if request.args.get('name'):
            filters['name'] = request.args.get('name')
        
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
            
        if request.args.get('company_type'):
            filters['company_type'] = request.args.get('company_type')
            
        if request.args.get('jurisdiction'):
            filters['jurisdiction'] = request.args.get('jurisdiction')
        
        # Get companies with filters
        companies = company_repo.search_companies(filters, limit=limit, offset=offset)
        total_count = company_repo.count()
        
        # Convert to dictionaries
        companies_data = [company.to_dict() for company in companies]
        
        return jsonify({
            'success': True,
            'data': companies_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            },
            'filters_applied': filters
        })
        
    except Exception as e:
        logger.error(f"Failed to get companies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sqlite_api.route('/api/sqlite/companies/<int:company_id>', methods=['GET'])
def get_company_detail(company_id):
    """Get detailed company information with SIC codes."""
    try:
        # Get company
        company = company_repo.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'error': 'Company not found'
            }), 404
        
        # Get associated SIC codes
        sic_relationships = company_sic_repo.get_by_company_id(company_id)
        sic_codes_data = []
        
        for relationship in sic_relationships:
            sic_code = sic_repo.get_by_id(relationship.sic_code_id)
            if sic_code:
                sic_codes_data.append({
                    'sic_code': sic_code.sic_code,
                    'description': sic_code.sic_description,
                    'section': sic_code.section,
                    'is_primary': relationship.is_primary
                })
        
        company_data = company.to_dict()
        company_data['sic_codes'] = sic_codes_data
        
        return jsonify({
            'success': True,
            'data': company_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get company details for ID {company_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sqlite_api.route('/api/sqlite/companies/search', methods=['GET'])
def search_companies():
    """Advanced company search with multiple criteria."""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        # Search in company names and business descriptions
        filters = {'name': query}
        companies = company_repo.search_companies(filters, limit=50)
        
        # Convert to search results format
        results = []
        for company in companies:
            results.append({
                'id': company.id,
                'company_number': company.company_number,
                'company_name': company.company_name,
                'status': company.status,
                'business_description': company.business_description[:200] + '...' if company.business_description and len(company.business_description) > 200 else company.business_description
            })
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Failed to search companies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sqlite_api.route('/api/sqlite/sic-codes', methods=['GET'])
def get_sic_codes():
    """Get SIC codes with filtering and pagination."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        section = request.args.get('section')
        search = request.args.get('search')
        
        if search:
            sic_codes = sic_repo.search_by_description(search, limit=limit)
        elif section:
            sic_codes = sic_repo.get_by_section(section, limit=limit)
        else:
            sic_codes = sic_repo.list_all(limit=limit, offset=offset)
        
        total_count = sic_repo.count()
        
        sic_codes_data = [sic_code.to_dict() for sic_code in sic_codes]
        
        return jsonify({
            'success': True,
            'data': sic_codes_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get SIC codes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sqlite_api.route('/api/sqlite/sic-codes/<int:sic_id>/companies', methods=['GET'])
def get_companies_by_sic_code(sic_id):
    """Get companies associated with a specific SIC code."""
    try:
        # Get SIC code
        sic_code = sic_repo.get_by_id(sic_id)
        if not sic_code:
            return jsonify({
                'success': False,
                'error': 'SIC code not found'
            }), 404
        
        # Get associated companies
        relationships = company_sic_repo.get_by_sic_code_id(sic_id)
        companies_data = []
        
        for relationship in relationships:
            company = company_repo.get_by_id(relationship.company_id)
            if company:
                companies_data.append({
                    'id': company.id,
                    'company_number': company.company_number,
                    'company_name': company.company_name,
                    'status': company.status,
                    'is_primary': relationship.is_primary
                })
        
        return jsonify({
            'success': True,
            'sic_code': sic_code.to_dict(),
            'companies': companies_data,
            'count': len(companies_data)
        })
        
    except Exception as e:
        logger.error(f"Failed to get companies for SIC code ID {sic_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sqlite_api.route('/api/sqlite/stats', methods=['GET'])
def get_database_stats():
    """Get comprehensive database statistics."""
    try:
        # Get basic counts
        companies_count = company_repo.count()
        sic_codes_count = sic_repo.count()
        relationships_count = company_sic_repo.count()
        
        # Get companies by status
        with db_connection.get_connection() as conn:
            cursor = conn.cursor()
            
            # Company status distribution
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM companies 
                GROUP BY status 
                ORDER BY count DESC
            """)
            status_distribution = [{'status': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            # Top SIC codes by company count
            cursor.execute("""
                SELECT sc.sic_code, sc.sic_description, COUNT(csc.company_id) as company_count
                FROM sic_codes sc
                JOIN company_sic_codes csc ON sc.id = csc.sic_code_id
                GROUP BY sc.id, sc.sic_code, sc.sic_description
                ORDER BY company_count DESC
                LIMIT 10
            """)
            top_sic_codes = [
                {
                    'sic_code': row[0], 
                    'description': row[1], 
                    'company_count': row[2]
                } 
                for row in cursor.fetchall()
            ]
            
            # Companies with financial data
            cursor.execute("SELECT COUNT(*) FROM company_financials")
            financial_records_count = cursor.fetchone()[0]
        
        return jsonify({
            'success': True,
            'stats': {
                'companies': companies_count,
                'sic_codes': sic_codes_count,
                'relationships': relationships_count,
                'financial_records': financial_records_count,
                'status_distribution': status_distribution,
                'top_sic_codes': top_sic_codes
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sqlite_api.route('/api/sqlite/advanced-search', methods=['POST'])
def advanced_search():
    """Advanced search across companies with multiple criteria."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data required'
            }), 400
        
        # Extract search criteria
        criteria = data.get('criteria', {})
        limit = min(data.get('limit', 50), 100)  # Cap at 100 results
        
        # Build complex query based on criteria
        with db_connection.get_connection() as conn:
            cursor = conn.cursor()
            
            query_parts = ["SELECT DISTINCT c.* FROM companies c"]
            where_conditions = []
            params = []
            
            # Join with SIC codes if needed
            if criteria.get('sic_code') or criteria.get('sic_description'):
                query_parts.append("JOIN company_sic_codes csc ON c.id = csc.company_id")
                query_parts.append("JOIN sic_codes sc ON csc.sic_code_id = sc.id")
            
            # Add WHERE conditions
            if criteria.get('company_name'):
                where_conditions.append("c.company_name LIKE ?")
                params.append(f"%{criteria['company_name']}%")
            
            if criteria.get('status'):
                where_conditions.append("c.status = ?")
                params.append(criteria['status'])
                
            if criteria.get('sic_code'):
                where_conditions.append("sc.sic_code = ?")
                params.append(criteria['sic_code'])
                
            if criteria.get('sic_description'):
                where_conditions.append("sc.sic_description LIKE ?")
                params.append(f"%{criteria['sic_description']}%")
            
            if criteria.get('has_financial_data'):
                query_parts.append("JOIN company_financials cf ON c.id = cf.company_id")
            
            # Combine query
            if where_conditions:
                query_parts.append("WHERE " + " AND ".join(where_conditions))
            
            query_parts.append(f"ORDER BY c.company_name LIMIT {limit}")
            
            final_query = " ".join(query_parts)
            cursor.execute(final_query, params)
            
            results = []
            for row in cursor.fetchall():
                # Convert row to dict
                columns = [description[0] for description in cursor.description]
                row_dict = dict(zip(columns, row))
                results.append(row_dict)
        
        return jsonify({
            'success': True,
            'criteria': criteria,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Failed to perform advanced search: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sqlite_api.route('/api/sqlite/sic-codes/hierarchy', methods=['GET'])
def get_sic_hierarchy():
    """Get SIC codes organized in hierarchical structure."""
    try:
        hierarchy = sic_repo.get_hierarchical_structure()
        return jsonify({
            'success': True,
            'data': hierarchy,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to get SIC hierarchy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sqlite_api.route('/api/sqlite/countries', methods=['GET'])
def get_countries():
    """Get list of available countries."""
    try:
        # Get distinct countries from companies
        query = "SELECT DISTINCT jurisdiction FROM companies WHERE jurisdiction IS NOT NULL ORDER BY jurisdiction"
        result = db_connection.execute_query(query)
        
        countries = [row[0] for row in result if row[0]]
        
        return jsonify({
            'success': True,
            'countries': countries,
            'count': len(countries),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to get countries: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500