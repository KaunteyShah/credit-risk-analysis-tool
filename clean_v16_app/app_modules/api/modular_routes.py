"""
Modular API Routes

These routes demonstrate the new modular architecture working alongside
the existing flask_main.py routes. They provide identical functionality
but use clean service layer separation.

These routes use the /api/v2/ prefix to avoid conflicts with existing routes.
"""
# [DEAD FILE] modular_api blueprint (prefix /api/v2) is registered ONLY via modular_integration.py
# which is never called from flask_main.create_app(). All /api/v2/* routes are unreachable in prod.
# Safe to delete once migration to flask_main equivalents is confirmed.

from flask import Blueprint, request, jsonify
from app_modules.infrastructure import get_company_service
from app_modules.utils.logger import logger
from app_modules.utils.input_validation import validate_api_input, validate_predict_sic_input, validate_update_revenue_input

# Create blueprint for modular API routes
modular_api = Blueprint('modular_api', __name__, url_prefix='/api/v2')

@modular_api.route('/data')
def get_data_modular():
    """
    Modular version of /api/data endpoint.
    
    This route demonstrates the new architecture:
    API Route → Service Layer → Repository Interface → File Implementation
    
    It should produce identical results to the original /api/data route.
    """
    try:
        # Get service instance from DI container
        company_service = get_company_service()
        
        # Extract request parameters (same as original)
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)
        country = request.args.get('country')
        
        # Build filters object
        filters = {}
        if country and country != 'all':
            filters['country'] = country
        
        # Use service layer for business logic
        result = company_service.get_companies_data(filters, limit, page)
        
        if result['success']:
            # Return same response structure as original route
            return jsonify({
                'data': result['data'],
                'total': result['total'],
                'page': result['page'],
                'limit': result['limit'],
                'total_pages': result['total_pages']
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        logger.error(f"Error in modular /api/v2/data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@modular_api.route('/filter_options')
def get_filter_options_modular():
    """
    Modular version of /api/filter_options endpoint.
    
    Demonstrates clean service layer usage for filter options.
    """
    try:
        company_service = get_company_service()
        result = company_service.get_filter_options()
        
        if result['success']:
            return jsonify({
                'countries': result['countries'],
                'sic_codes': result['sic_codes'],
                'employee_ranges': result['employee_ranges']
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        logger.error(f"Error in modular /api/v2/filter_options: {str(e)}")
        return jsonify({'error': str(e)}), 500

@modular_api.route('/predict_sic', methods=['POST'])
def predict_sic_modular():
    """
    Modular version of /api/predict_sic endpoint.
    
    Demonstrates clean service layer usage for SIC prediction.
    This route uses the same validation as the original.
    """
    try:
        # Use same validation as original route
        data = request.get_json()
        if not data or 'company_index' not in data:
            return jsonify({'error': 'company_index is required'}), 400
        
        company_index = data['company_index']
        use_real_agents = data.get('use_real_agents', False)
        
        # Use service layer for business logic
        company_service = get_company_service()
        result = company_service.predict_company_sic(company_index, use_real_agents)
        
        if result['success']:
            # Return same response structure as original route
            return jsonify({
                'success': True,
                'predicted_sic': result['predicted_sic'],
                'confidence': result['confidence'],
                'accuracy': result['accuracy'],
                'algorithm': result['algorithm'],
                'company_name': result['company_name'],
                'business_description': result['business_description']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Error in modular /api/v2/predict_sic: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@modular_api.route('/update_revenue', methods=['POST'])
def update_revenue_modular():
    """
    Modular version of /api/update_revenue endpoint.
    
    Demonstrates clean service layer usage for revenue updates.
    """
    try:
        data = request.get_json()
        if not data or 'company_registration' not in data or 'revenue' not in data:
            return jsonify({'error': 'company_registration and revenue are required'}), 400
        
        company_registration = data['company_registration']
        revenue = float(data['revenue'])
        
        # Use service layer for business logic
        company_service = get_company_service()
        result = company_service.update_company_revenue(company_registration, revenue)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'company_registration': result['company_registration'],
                'new_revenue': result['new_revenue']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Error in modular /api/v2/update_revenue: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@modular_api.route('/data/reload', methods=['POST'])
def reload_data_modular():
    """
    Modular version of /api/data/reload endpoint.
    
    Demonstrates clean service layer usage for data reloading.
    """
    try:
        company_service = get_company_service()
        result = company_service.reload_company_data()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'total_companies': result['total_companies']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        logger.error(f"Error in modular /api/v2/data/reload: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@modular_api.route('/company/<registration>')
def get_company_details_modular(registration: str):
    """
    New endpoint for getting detailed company information.
    
    Demonstrates additional functionality enabled by clean architecture.
    """
    try:
        company_service = get_company_service()
        result = company_service.get_company_details(registration)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting company details for {registration}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@modular_api.route('/architecture/info')
def get_architecture_info():
    """
    New endpoint that provides information about the modular architecture.
    
    This demonstrates the new architecture capabilities.
    """
    try:
        from app_modules.infrastructure.di.container import get_container
        
        container = get_container()
        
        # Get repository and service information
        company_repo = container.get('company_repository')
        company_service = container.get('company_service')
        
        architecture_info = {
            'success': True,
            'architecture': 'modular',
            'components': {
                'repository': {
                    'type': type(company_repo).__name__,
                    'interface': 'CompanyRepositoryInterface',
                    'data_source': 'file_based'
                },
                'service': {
                    'type': type(company_service).__name__,
                    'business_logic': 'separated'
                },
                'dependency_injection': {
                    'enabled': True,
                    'container': 'DIContainer'
                }
            },
            'benefits': [
                'Clean separation of concerns',
                'Easy testing with mock dependencies', 
                'Modular architecture ready for SQLite migration',
                'Same UI and API responses as original'
            ],
            'endpoints': [
                '/api/v2/data - Company data with filtering',
                '/api/v2/filter_options - Filter options',
                '/api/v2/predict_sic - SIC prediction',
                '/api/v2/update_revenue - Revenue updates',
                '/api/v2/data/reload - Data reload',
                '/api/v2/company/<registration> - Company details',
                '/api/v2/architecture/info - Architecture information'
            ]
        }
        
        # Get some statistics
        try:
            total_companies = company_repo.count()
            architecture_info['statistics'] = {
                'total_companies': total_companies,
                'data_loaded': total_companies > 0
            }
        except Exception as e:
            architecture_info['statistics'] = {
                'error': str(e)
            }
        
        return jsonify(architecture_info)
        
    except Exception as e:
        logger.error(f"Error getting architecture info: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500