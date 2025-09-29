"""
Pure Modular Flask Application - No Fallbacks
Demonstrates modular architecture using only repositories and services
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_modular_app():
    """Create Flask app using ONLY modular architecture components"""
    app = Flask(__name__)
    CORS(app)
    
    # Set environment for modular architecture
    os.environ['DATABASE_TYPE'] = 'files'
    
    logger.info("🚀 Creating PURE MODULAR Flask App (No Fallbacks)")
    
    # Import modular components
    try:
        from app.core.dependency_injection import get_company_service, get_sic_prediction_service
        logger.info("✅ Modular components imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import modular components: {e}")
        raise
    
    @app.route('/', methods=['GET'])
    def home():
        """Home page showing available modular endpoints"""
        return jsonify({
            'message': '🏗️ Pure Modular Architecture Demo',
            'description': 'This Flask app uses ONLY modular architecture - no fallbacks!',
            'architecture': {
                'repositories': [
                    'FileCompanyRepository - Handles company data access',
                    'FileSICPredictionRepository - Handles SIC prediction data'
                ],
                'services': [
                    'CompanyService - Business logic for company operations',
                    'SICPredictionService - Business logic for SIC predictions'
                ],
                'dependency_injection': 'DIContainer - Auto-wires components based on configuration'
            },
            'available_endpoints': {
                'GET /': 'This information page',
                'GET /api/modular/health': 'Health check for modular components',
                'GET /api/modular/companies': 'Paginated companies (page, limit, country, search)',
                'GET /api/modular/companies/{index}': 'Company details with AI reasoning',
                'POST /api/modular/predict-sic': 'SIC prediction using modular architecture',
                'GET /api/modular/stats': 'Repository and service statistics'
            },
            'configuration': {
                'database_type': os.environ.get('DATABASE_TYPE', 'files'),
                'modular_only': True,
                'fallback_enabled': False
            }
        })
    
    @app.route('/api/modular/health', methods=['GET'])
    def modular_health():
        """Health check for modular components"""
        try:
            # Test service initialization
            company_service = get_company_service(app)
            sic_service = get_sic_prediction_service(app)
            
            # Test basic operations
            companies_count = company_service.repository.get_companies_count()
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'company_service': {
                        'status': 'operational',
                        'type': type(company_service).__name__,
                        'repository': type(company_service.repository).__name__
                    },
                    'sic_prediction_service': {
                        'status': 'operational', 
                        'type': type(sic_service).__name__,
                        'repository': type(sic_service.repository).__name__
                    }
                },
                'data': {
                    'companies_loaded': companies_count,
                    'data_source': 'CSV files',
                    'architecture': '100% modular'
                }
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/api/modular/companies', methods=['GET'])
    def get_companies_modular():
        """Get paginated companies using ONLY modular architecture"""
        try:
            # Get service (no fallback - pure modular)
            company_service = get_company_service(app)
            
            # Parse request parameters
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 50))
            country = request.args.get('country')
            search = request.args.get('search')
            
            logger.info(f"🔍 Modular companies request: page={page}, limit={limit}, country={country}, search={search}")
            
            # Use modular service (no fallback)
            result = company_service.get_companies_paginated(page, limit, country, search)
            
            # Add modular metadata
            result['modular_info'] = {
                'architecture': 'pure_modular',
                'fallback_used': False,
                'service_type': type(company_service).__name__,
                'repository_type': type(company_service.repository).__name__
            }
            
            logger.info(f"✅ Modular companies returned: {len(result.get('data', []))} companies")
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ Modular companies error: {e}")
            return jsonify({
                'error': f'Modular architecture error: {str(e)}',
                'modular_info': {
                    'architecture': 'pure_modular',
                    'fallback_used': False,
                    'fallback_available': False
                }
            }), 500
    
    @app.route('/api/modular/companies/<int:company_index>', methods=['GET'])
    def get_company_details_modular(company_index):
        """Get company details using ONLY modular architecture"""
        try:
            # Get service (no fallback - pure modular)
            company_service = get_company_service(app)
            
            logger.info(f"🏢 Modular company details request for index: {company_index}")
            
            # Use modular service (no fallback)
            result = company_service.get_company_details_with_reasoning(company_index)
            
            if result and 'error' in result:
                error_response = dict(result) if result else {}
                error_response['modular_info'] = {
                    'architecture': 'pure_modular',
                    'fallback_used': False,
                    'service_type': type(company_service).__name__
                }
                return jsonify(error_response), 400
            
            # Add modular metadata
            if result:
                result['modular_info'] = {
                'architecture': 'pure_modular',
                'fallback_used': False,
                'service_type': type(company_service).__name__,
                'repository_type': type(company_service.repository).__name__
            }
            
            logger.info(f"✅ Modular company details returned for index {company_index}")
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ Modular company details error: {e}")
            return jsonify({
                'error': f'Modular architecture error: {str(e)}',
                'company_index': company_index,
                'modular_info': {
                    'architecture': 'pure_modular',
                    'fallback_used': False,
                    'fallback_available': False
                }
            }), 500
    
    @app.route('/api/modular/predict-sic', methods=['POST'])
    def predict_sic_modular():
        """SIC prediction using ONLY modular architecture"""
        try:
            # Get service (no fallback - pure modular)
            sic_service = get_sic_prediction_service(app)
            
            # Parse request data
            data = request.get_json() or {}
            company_index = data.get('company_index')
            use_real_agents = data.get('use_real_agents', False)
            
            if company_index is None:
                return jsonify({
                    'error': 'company_index is required',
                    'modular_info': {
                        'architecture': 'pure_modular',
                        'fallback_used': False
                    }
                }), 400
            
            logger.info(f"🔮 Modular SIC prediction request: index={company_index}, real_agents={use_real_agents}")
            
            # Use modular service (no fallback)
            result = sic_service.predict_sic_for_company(company_index, use_real_agents, app)
            
            if result and 'error' in result:
                error_response = dict(result) if result else {}
                error_response['modular_info'] = {
                    'architecture': 'pure_modular',
                    'fallback_used': False,
                    'service_type': type(sic_service).__name__
                }
                return jsonify(error_response), 400
            
            # Add modular metadata
            if result:
                result['modular_info'] = {
                'architecture': 'pure_modular',
                'fallback_used': False,
                'service_type': type(sic_service).__name__,
                'repository_type': type(sic_service.repository).__name__
            }
            
            logger.info(f"✅ Modular SIC prediction completed for index {company_index}")
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ Modular SIC prediction error: {e}")
            return jsonify({
                'error': f'Modular architecture error: {str(e)}',
                'modular_info': {
                    'architecture': 'pure_modular',
                    'fallback_used': False,
                    'fallback_available': False
                }
            }), 500
    
    @app.route('/api/modular/stats', methods=['GET'])
    def get_modular_stats():
        """Get statistics about modular architecture components"""
        try:
            # Get services
            company_service = get_company_service(app)
            sic_service = get_sic_prediction_service(app)
            
            # Get repository stats
            companies_count = company_service.repository.get_companies_count()
            
            return jsonify({
                'modular_architecture': {
                    'status': 'fully_operational',
                    'fallback_mode': False,
                    'pure_modular': True
                },
                'services': {
                    'company_service': {
                        'class': type(company_service).__name__,
                        'repository_class': type(company_service.repository).__name__,
                        'status': 'active'
                    },
                    'sic_prediction_service': {
                        'class': type(sic_service).__name__,
                        'repository_class': type(sic_service.repository).__name__,
                        'status': 'active'
                    }
                },
                'data': {
                    'companies_loaded': companies_count,
                    'data_source': 'CSV files',
                    'database_type': os.environ.get('DATABASE_TYPE', 'files')
                },
                'endpoints': {
                    'total_modular_endpoints': 5,
                    'fallback_endpoints': 0,
                    'pure_modular_coverage': '100%'
                }
            })
            
        except Exception as e:
            return jsonify({
                'error': f'Stats generation error: {str(e)}',
                'modular_architecture': {
                    'status': 'error',
                    'fallback_mode': False,
                    'pure_modular': True
                }
            }), 500
    
    logger.info("🎯 Pure Modular Flask App created successfully!")
    logger.info("   No fallbacks - 100% modular architecture")
    logger.info(f"   Total routes: {len(list(app.url_map.iter_rules()))}")
    
    return app

if __name__ == '__main__':
    app = create_modular_app()
    print("🚀 Starting Pure Modular Flask App")
    print("   URL: http://localhost:5001")
    print("   Architecture: 100% Modular (No Fallbacks)")
    print("   Endpoints: /api/modular/*")
    app.run(host='0.0.0.0', port=5001, debug=True)