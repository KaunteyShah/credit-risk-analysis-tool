"""
Agentic API Routes

This module provides API routes for the intelligent agentic SIC prediction system.
It integrates seamlessly with the existing API structure while providing enhanced
agentic capabilities through new endpoints.

New Endpoints:
- POST /api/predict_sic_agentic: Enhanced agentic SIC prediction
- GET /api/agentic/status: Service health and configuration status
- GET /api/agentic/config: Get workflow configuration schema
- POST /api/agentic/config: Update workflow configuration

Integration Strategy:
- Zero-impact deployment alongside existing endpoints
- Backward compatible with existing API patterns
- Enhanced response format with agentic insights
- Comprehensive error handling and fallback mechanisms
"""

import logging
from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

from .sic_prediction.sic_service import AgenticSICPredictionService
from .update_revenue.revenue_agentic_service import AgenticRevenueService

logger = logging.getLogger(__name__)

# Create blueprint for agentic routes
agentic_bp = Blueprint('agentic', __name__, url_prefix='/api/agentic')

# Global service instances (initialized on first use)
_agentic_service: Optional[AgenticSICPredictionService] = None
_revenue_service: Optional[AgenticRevenueService] = None


def get_agentic_service() -> AgenticSICPredictionService:
    """
    Get or initialize the agentic SIC service.

    PRIMARY path: re-use the already-fully-initialised service stored on the Flask
    app by flask_main.create_app() as app.agentic_sic_service (it has the correct
    sqlite_sic_repository + companies_house_client services_container).

    FALLBACK: build from individual app attributes using the correct attribute
    names (sqlite_sic_repository, not sic_prediction_repository).
    """
    global _agentic_service

    if _agentic_service is None:
        try:
            # ── Primary: use the service already built by create_app() ──────────
            if current_app and getattr(current_app, 'agentic_sic_service', None):
                _agentic_service = current_app.agentic_sic_service
                logger.info("✅ Agentic service: reusing app-level instance")
                return _agentic_service

            # ── Fallback: build from app attributes (correct names) ───────────
            services_container = {}
            if current_app:
                # Correct attribute names as set by flask_main.create_app()
                services_container['sqlite_sic_repository'] = getattr(current_app, 'sqlite_sic_repository', None)
                services_container['companies_house_client'] = getattr(current_app, 'companies_house_client', None)
                services_container['enhanced_sic_matcher'] = getattr(current_app, 'sic_matcher', None)
                services_container['realtime_reasoning_service'] = getattr(current_app, 'realtime_reasoning_service', None)
                services_container['sector_classification_agent'] = getattr(current_app, 'sector_agent', None)

                try:
                    from app_modules.core.dependency_injection import get_company_service
                    services_container['company_service'] = get_company_service(current_app)
                except (ImportError, Exception) as e:
                    logger.warning(f"Could not get company service: {e}")

            services_container = {k: v for k, v in services_container.items() if v is not None}

            default_config = {
                'enable_reflection': True,
                'enable_reasoning_generation': True,
                'confidence_threshold': 0.7,
                'enable_ch_fallback': True,
                'max_execution_time': 60,
                'skip_reflection_high_confidence': False
            }

            _agentic_service = AgenticSICPredictionService(services_container, default_config)
            logger.info("✅ Agentic service initialised from app attributes")

        except Exception as e:
            logger.error(f"❌ Failed to initialise agentic service: {e}")
            _agentic_service = AgenticSICPredictionService({}, {})

    return _agentic_service


def get_revenue_service() -> AgenticRevenueService:
    """
    Get or initialize the agentic revenue service with dependency injection.
    
    This function ensures the revenue service is properly initialized with all 
    required dependencies for revenue extraction workflow.
    """
    global _revenue_service
    
    if _revenue_service is None:
        try:
            # Gather required services for revenue extraction
            services_container = {}
            
            # Check if we have access to current Flask app
            if current_app:
                # Get companies house client (required)
                services_container['companies_house_client'] = getattr(current_app, 'companies_house_client', None)
                
                # Try to get existing agents from app or DI container
                try:
                    # Import agents and repositories dynamically to avoid circular imports
                    from ..agents.document_download_agent import DocumentDownloadAgent
                    from ..agents.rag_document_agent import RAGDocumentAgent
                    from ..agents.smart_financial_extraction_agent import SmartFinancialExtractionAgent
                    from ..agents.turnover_estimation_agent import TurnoverEstimationAgent
                    from ..repositories.implementations.file_based.sqlite_filing_history_repository import SQLiteFilingHistoryRepository
                    from ..database.connection import DatabaseConnection
                    
                    # Initialize agents if not available on app
                    services_container['document_download_agent'] = getattr(current_app, 'document_agent', None) or DocumentDownloadAgent()
                    services_container['rag_document_agent'] = getattr(current_app, 'rag_agent', None) or RAGDocumentAgent()
                    services_container['smart_financial_extraction_agent'] = getattr(current_app, 'smart_extraction_agent', None) or SmartFinancialExtractionAgent()
                    services_container['turnover_estimation_agent'] = getattr(current_app, 'turnover_agent', None) or TurnoverEstimationAgent()
                    
                    # Initialize filing history repository
                    db_connection = getattr(current_app, 'db_connection', None) or DatabaseConnection()
                    services_container['filing_history_repository'] = SQLiteFilingHistoryRepository(db_connection)
                    
                except ImportError as e:
                    logger.warning(f"Could not import required agents or repositories: {e}")
            
            # Filter out None services
            services_container = {k: v for k, v in services_container.items() if v is not None}
            
            # Initialize revenue service with default config
            default_config = {
                'enable_vector_search': True,
                'extraction_timeout': 300,  # 5 minutes for large documents with 500+ chunks
                'confidence_threshold': 0.5,
                'enable_fallback_methods': True,
                'max_document_size_mb': 50
            }
            
            _revenue_service = AgenticRevenueService(services_container, default_config)
            logger.info("✅ Revenue agentic service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize revenue agentic service: {e}")
            # Create a minimal fallback service
            _revenue_service = AgenticRevenueService({}, {})
    
    return _revenue_service


@agentic_bp.route('/predict_sic', methods=['POST'])
def predict_sic_agentic():
    """
    Enhanced agentic SIC prediction endpoint.
    
    This endpoint provides intelligent agentic SIC prediction with comprehensive
    analysis, validation, and reasoning capabilities.
    
    Request Body:
    {
        "company_name": "string (required)",
        "business_description": "string (optional)",
        "company_number": "string (optional)", 
        "address": "string (optional)",
        "workflow_config": {  // optional configuration overrides
            "enable_reflection": boolean,
            "enable_reasoning_generation": boolean,
            "confidence_threshold": float,
            "enable_ch_fallback": boolean
        }
    }
    
    Response:
    {
        "success": boolean,
        "predicted_sic_code": "string",
        "confidence_score": float,
        "prediction_method": "string",
        "alternatives": [...],
        "reasoning": "string",
        "agentic_insights": {...},
        "companies_house_validation": {...},
        "workflow_summary": {...},
        "quality_assessment": {...},
        "workflow_steps": [...],
        "execution_time": float,
        "timestamp": "string"
    }
    """
    start_time = datetime.now()
    
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        company_name = data.get('company_name', '').strip()
        if not company_name:
            return jsonify({
                'success': False,
                'error': 'company_name is required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Extract optional fields
        business_description = data.get('business_description', '').strip()
        company_number = data.get('company_number', '').strip()
        address = data.get('address', '').strip()
        workflow_config = data.get('workflow_config', {})
        
        logger.info(f"🤖 Agentic SIC prediction request for: {company_name}")
        
        # Get agentic service
        service = get_agentic_service()
        
        # Execute agentic prediction
        result = service.predict_sic_agentic(
            company_name=company_name,
            business_description=business_description,
            company_number=company_number,
            address=address,
            workflow_config=workflow_config
        )
        
        # Add success flag and API metadata
        # Extract ch_sic_codes to top-level so JS approveSICPrediction can access it directly
        ch_sic_codes_top = result.get('companies_house_validation', {}).get('sic_codes', [])
        response = {
            'success': True,
            **result,
            'workflow_type': 'AGENTIC_MULTI_AGENT',  # JS uses this for approve payload
            'ch_sic_codes': ch_sic_codes_top,         # JS passes this to approve endpoint
            'api_version': '1.0.0',
            'endpoint': 'agentic'
        }
        
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Agentic prediction completed in {execution_time:.2f}s: {result['predicted_sic_code']}")
        
        return jsonify(response), 200
        
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        error_message = str(e)
        
        logger.error(f"❌ Agentic prediction failed: {error_message}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': error_message,
            'predicted_sic_code': '99999',  # Fallback SIC code
            'confidence_score': 0.0,
            'prediction_method': 'error_fallback',
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat(),
            'api_version': '1.0.0',
            'endpoint': 'agentic'
        }), 500


@agentic_bp.route('/status', methods=['GET'])
def get_agentic_status():
    """
    Get agentic service status and health information.
    
    Response:
    {
        "success": boolean,
        "service_status": {...},
        "health_check": {...},
        "capabilities": {...},
        "timestamp": "string"
    }
    """
    try:
        service = get_agentic_service()
        status = service.get_service_status()
        
        # Perform basic health checks
        health_check = {
            'service_initialized': status['service_initialized'],
            'langgraph_available': status['langgraph_available'],
            'required_services_available': status['services_configured']['required_services_present'],
            'workflow_ready': status['workflow_compiled'] or status['langgraph_available'],
            'overall_health': 'healthy'
        }
        
        # Determine overall health
        if not health_check['service_initialized']:
            health_check['overall_health'] = 'unhealthy'
        elif not health_check['langgraph_available']:
            health_check['overall_health'] = 'limited'
        elif not health_check['required_services_available']:
            health_check['overall_health'] = 'degraded'
        
        # Determine available capabilities
        capabilities = {
            'agentic_prediction': health_check['workflow_ready'],
            'companies_house_validation': status['services_configured']['required_services_present'],
            'reasoning_generation': status['services_configured']['optional_services_present']['realtime_reasoning_service'],
            'sector_classification': status['services_configured']['optional_services_present']['sector_classification_agent'],
            'reflection_evaluation': status['langgraph_available'],
            'workflow_visualization': True,
            'fallback_prediction': True
        }
        
        response = {
            'success': True,
            'service_status': status,
            'health_check': health_check,
            'capabilities': capabilities,
            'timestamp': datetime.now().isoformat()
        }
        
        # Return appropriate status code based on health
        status_code = 200
        if health_check['overall_health'] == 'unhealthy':
            status_code = 503
        elif health_check['overall_health'] in ['limited', 'degraded']:
            status_code = 206  # Partial Content
        
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'health_check': {'overall_health': 'unhealthy'},
            'timestamp': datetime.now().isoformat()
        }), 500


@agentic_bp.route('/config', methods=['GET'])
def get_workflow_config():
    """
    Get workflow configuration schema and current configuration.
    
    Response:
    {
        "success": boolean,
        "schema": {...},
        "current_config": {...},
        "timestamp": "string"
    }
    """
    try:
        service = get_agentic_service()
        schema = service.get_workflow_config_schema()
        status = service.get_service_status()
        current_config = status['configuration']
        
        return jsonify({
            'success': True,
            'schema': schema,
            'current_config': current_config,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Config retrieval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@agentic_bp.route('/config', methods=['POST'])
def update_workflow_config():
    """
    Update workflow configuration.
    
    Request Body:
    {
        "enable_reflection": boolean,
        "enable_reasoning_generation": boolean,
        "confidence_threshold": float,
        "enable_ch_fallback": boolean,
        "max_execution_time": float,
        "skip_reflection_high_confidence": boolean
    }
    
    Response:
    {
        "success": boolean,
        "updated_config": {...},
        "message": "string",
        "timestamp": "string"
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        new_config = request.get_json()
        service = get_agentic_service()
        
        # Update configuration
        success = service.update_configuration(new_config)
        
        if success:
            updated_status = service.get_service_status()
            return jsonify({
                'success': True,
                'updated_config': updated_status['configuration'],
                'message': 'Configuration updated successfully',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Configuration update failed',
                'timestamp': datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Config update failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@agentic_bp.route('/statistics', methods=['GET'])
def get_execution_statistics():
    """
    Get execution statistics and performance metrics.
    
    Response:
    {
        "success": boolean,
        "statistics": {...},
        "performance_metrics": {...},
        "timestamp": "string"
    }
    """
    try:
        service = get_agentic_service()
        status = service.get_service_status()
        
        statistics = status['execution_statistics']
        
        # Calculate additional performance metrics
        performance_metrics = {
            'success_rate': (
                statistics['successful_predictions'] / statistics['total_predictions'] 
                if statistics['total_predictions'] > 0 else 0.0
            ),
            'failure_rate': (
                statistics['failed_predictions'] / statistics['total_predictions']
                if statistics['total_predictions'] > 0 else 0.0
            ),
            'average_execution_time_ms': statistics['average_execution_time'] * 1000,
            'last_execution_time_ms': (
                statistics['last_execution_time'] * 1000 
                if statistics['last_execution_time'] else None
            ),
            'throughput_per_minute': (
                60 / statistics['average_execution_time'] 
                if statistics['average_execution_time'] > 0 else 0.0
            )
        }
        
        return jsonify({
            'success': True,
            'statistics': statistics,
            'performance_metrics': performance_metrics,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Statistics retrieval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# Legacy compatibility route for existing API structure
@agentic_bp.route('/predict_sic_agentic', methods=['POST'])
def predict_sic_agentic_legacy():
    """
    Legacy compatibility endpoint that redirects to the main agentic prediction.
    This maintains backward compatibility with any existing integrations.
    """
    return predict_sic_agentic()


# Health check endpoint for monitoring
@agentic_bp.route('/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint for monitoring and load balancers.
    
    Response:
    {
        "status": "healthy" | "unhealthy" | "limited",
        "timestamp": "string"
    }
    """
    try:
        service = get_agentic_service()
        status = service.get_service_status()
        
        if status['service_initialized'] and status['services_configured']['required_services_present']:
            if status['langgraph_available']:
                health_status = "healthy"
                status_code = 200
            else:
                health_status = "limited"
                status_code = 206
        else:
            health_status = "unhealthy" 
            status_code = 503
        
        return jsonify({
            'status': health_status,
            'timestamp': datetime.now().isoformat()
        }), status_code
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503


@agentic_bp.route('/extract_revenue', methods=['POST'])
def extract_revenue_agentic():
    """
    Enhanced agentic revenue extraction endpoint.
    
    This endpoint provides intelligent agentic revenue extraction with comprehensive
    document processing, multi-strategy extraction, and validation capabilities.
    
    Request Body:
    {
        "company_name": "string (required)",
        "company_number": "string (optional)",
        "address": "string (optional)",
        "workflow_config": {  // optional configuration overrides
            "enable_vector_search": boolean,
            "extraction_timeout": float,
            "confidence_threshold": float,
            "enable_fallback_methods": boolean
        }
    }
    
    Response:
    {
        "success": boolean,
        "extracted_revenue": float,
        "revenue_currency": "string",
        "confidence_score": float,
        "extraction_method": "string",
        "alternative_revenues": [...],
        "workflow_summary": {...},
        "companies_house_data": {...},
        "document_processing_summary": {...},
        "agentic_insights": {...},
        "execution_time": float,
        "workflow_steps": [...],
        "validation_results": {...},
        "timestamp": "string"
    }
    """
    start_time = datetime.now()
    
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        data = request.get_json()
        
        # Extract request parameters first
        company_name = data.get('company_name', '').strip()
        company_number = data.get('company_number', '').strip()
        address = data.get('address', '').strip()
        transaction_id = data.get('transaction_id', '').strip()  # ✅ NEW: Accept transaction_id for direct document processing
        workflow_config = data.get('workflow_config', {})
        
        # Validate required fields - company_name, company_number, or transaction_id must be provided
        if not company_name and not transaction_id and not company_number:
            return jsonify({
                'success': False,
                'error': 'Either company_name, company_number, or transaction_id is required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Resolve company_name from DB if only company_number was provided
        if not company_name and company_number:
            try:
                from ..database.connection import get_db_connection
                with get_db_connection() as conn:
                    row = conn.execute(
                        'SELECT "Company Name" FROM companies WHERE "Company Number" = ? LIMIT 1',
                        (company_number,)
                    ).fetchone()
                    if row:
                        company_name = row[0]
            except Exception:
                pass
        
        logger.info(f"💰 Agentic revenue extraction request for: {company_name or f'transaction_id:{transaction_id}'}")
        
        # Get revenue service
        service = get_revenue_service()
        
        # Execute revenue extraction
        result = service.extract_revenue_agentic(
            company_name=company_name,
            company_number=company_number,
            address=address,
            transaction_id=transaction_id,  # ✅ NEW: Pass transaction_id to service
            workflow_config=workflow_config
        )
        
        # Add request metadata
        result['request_id'] = f"rev_{int(datetime.now().timestamp())}"
        result['timestamp'] = datetime.now().isoformat()
        
        # Determine response status code
        status_code = 200 if result.get('success', False) else 422
        
        # Log result summary
        execution_time = result.get('execution_time', 0)
        method = result.get('extraction_method', 'unknown')
        revenue = result.get('extracted_revenue')
        
        if result.get('success', False):
            logger.info(f"✅ Revenue extraction completed in {execution_time:.2f}s: £{revenue} via {method}")
        else:
            error_count = len(result.get('errors', []))
            logger.warning(f"⚠️ Revenue extraction completed with {error_count} errors in {execution_time:.2f}s")
        
        return jsonify(result), status_code
        
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        error_msg = f"Revenue extraction failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': error_msg,
            'extracted_revenue': None,
            'revenue_currency': 'GBP',
            'confidence_score': 0.0,
            'extraction_method': 'failed',
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        }), 500


def register_agentic_routes(app):
    """
    Register agentic routes with the Flask application.
    
    This function should be called from the main application factory
    to integrate agentic routes with the existing API structure.
    
    Args:
        app: Flask application instance
    """
    try:
        # Register the blueprint
        app.register_blueprint(agentic_bp)
        
        # Also register direct routes under /api for easier access
        @app.route('/api/predict_sic_agentic', methods=['POST'])
        def api_predict_sic_agentic():
            return predict_sic_agentic()
        
        @app.route('/api/extract_revenue_agentic', methods=['POST'])
        def api_extract_revenue_agentic():
            return extract_revenue_agentic()
        
        logger.info("✅ Agentic routes registered successfully")
        
        # Log available endpoints
        agentic_endpoints = [
            '/api/agentic/predict_sic',
            '/api/agentic/extract_revenue',
            '/api/agentic/status', 
            '/api/agentic/config',
            '/api/agentic/statistics',
            '/api/agentic/health',
            '/api/predict_sic_agentic',  # Direct API route
            '/api/extract_revenue_agentic'  # Direct API route
        ]
        
        logger.info(f"🚀 Agentic endpoints available: {agentic_endpoints}")
        
    except Exception as e:
        logger.error(f"❌ Failed to register agentic routes: {e}")
        raise


# Error handlers for the agentic blueprint
@agentic_bp.errorhandler(404)
def agentic_not_found(error):
    """Handle 404 errors for agentic endpoints"""
    return jsonify({
        'success': False,
        'error': 'Agentic endpoint not found',
        'available_endpoints': [
            '/api/agentic/predict_sic',
            '/api/agentic/extract_revenue',
            '/api/agentic/status',
            '/api/agentic/config',
            '/api/agentic/statistics',
            '/api/agentic/health'
        ],
        'timestamp': datetime.now().isoformat()
    }), 404


@agentic_bp.errorhandler(405)
def agentic_method_not_allowed(error):
    """Handle 405 errors for agentic endpoints"""
    return jsonify({
        'success': False,
        'error': 'Method not allowed for this agentic endpoint',
        'timestamp': datetime.now().isoformat()
    }), 405


@agentic_bp.errorhandler(500)
def agentic_internal_error(error):
    """Handle 500 errors for agentic endpoints"""
    logger.error(f"❌ Agentic internal error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal error in agentic service',
        'timestamp': datetime.now().isoformat()
    }), 500