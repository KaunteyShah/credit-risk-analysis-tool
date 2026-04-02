"""
Main application routes (non-API endpoints)
"""
from flask import Flask, render_template, jsonify, g
from app.utils.centralized_logging import get_logger
logger = get_logger(__name__)


def register_main_routes(app: Flask) -> None:
    """Register main application routes"""
    
    @app.route('/')
    def index():
        """Main application page"""
        return render_template('enhanced_app.html')
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        data_manager = g.data_manager
        
        health_status = {
            'status': 'healthy',
            'data_loaded': data_manager.is_data_loaded(),
            'timestamp': None  # Can add timestamp if needed
        }
        
        return jsonify(health_status)
    
    @app.route('/debug')
    def debug():
        """Debug information endpoint"""
        try:
            data_manager = g.data_manager
            
            # Get basic stats
            company_data = data_manager.company_data
            sic_codes = data_manager.sic_codes
            
            debug_info = {
                'company_data_loaded': not company_data.empty,
                'company_count': len(company_data) if not company_data.empty else 0,
                'sic_codes_loaded': not sic_codes.empty,
                'sic_count': len(sic_codes) if not sic_codes.empty else 0,
                'columns': list(company_data.columns) if not company_data.empty else [],
                'orchestrator_available': data_manager.orchestrator is not None,
                'sector_agent_available': data_manager.sector_agent is not None,
                'sic_matcher_available': data_manager.sic_matcher is not None
            }
            
            # Add sample data if available
            if not company_data.empty:
                debug_info['sample_company'] = company_data.iloc[0].to_dict()
            
            return jsonify(debug_info)
            
        except Exception as e:
            logger.error(f"Debug endpoint error: {e}")
            return jsonify({
                'error': str(e),
                'company_data_loaded': False,
                'company_count': 0
            }), 500