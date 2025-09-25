"""
Azure-optimized Flask application with minimal dependencies
This is a streamlined version designed specifically for Azure App Service deployment
"""

import logging
import os
import sys
from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('flask_app.log')
    ]
)
logger = logging.getLogger(__name__)

def create_fallback_company_data():
    """Create fallback company data when main data files are not available"""
    # Generate sample company data for demo
    companies = [
        "Tech Innovations Inc", "Global Manufacturing Corp", "Green Energy Solutions",
        "Financial Services Ltd", "Healthcare Solutions", "Retail Excellence",
        "Construction Dynamics", "Transport Logistics", "Food & Beverage Co",
        "Entertainment Media"
    ]
    
    data = []
    for i, company in enumerate(companies):
        data.append({
            'Company Name': company,
            'Sales (USD)': np.random.randint(1000000, 100000000),
            'Total Assets (USD)': np.random.randint(500000, 50000000),
            'Net Income (USD)': np.random.randint(-1000000, 10000000),
            'SIC Code': np.random.choice(['7372', '3711', '4953', '6021', '8071', '5411', '1542', '4213', '2024', '7812']),
            'Description': f"Sample description for {company}",
            'SIC_Accuracy': np.random.uniform(0.7, 0.95),
            'Needs_Revenue_Update': np.random.choice([True, False])
        })
    
    return pd.DataFrame(data)

def create_fallback_sic_data():
    """Create fallback SIC code data when main SIC file is not available"""
    sic_data = [
        {'SIC Code': '7372', 'Description': 'Prepackaged Software'},
        {'SIC Code': '3711', 'Description': 'Motor Vehicles and Passenger Car Bodies'},
        {'SIC Code': '4953', 'Description': 'Refuse Systems'},
        {'SIC Code': '6021', 'Description': 'National Commercial Banks'},
        {'SIC Code': '8071', 'Description': 'Medical Laboratories'},
        {'SIC Code': '5411', 'Description': 'Grocery Stores'},
        {'SIC Code': '1542', 'Description': 'General Contractors-Nonresidential Buildings'},
        {'SIC Code': '4213', 'Description': 'Trucking, Except Local'},
        {'SIC Code': '2024', 'Description': 'Ice Cream and Frozen Desserts'},
        {'SIC Code': '7812', 'Description': 'Motion Picture and Video Tape Production'}
    ]
    
    return pd.DataFrame(sic_data)

def create_azure_app():
    """Create Azure-optimized Flask application"""
    app = Flask(__name__, 
                template_folder='app/templates',
                static_folder='app/static')
    
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'azure-demo-key-2024')
    
    # Initialize data with fallback
    try:
        logger.info("Initializing Azure-optimized Flask app...")
        
        # Always use fallback data for Azure reliability
        app.company_data = create_fallback_company_data()
        app.sic_codes = create_fallback_sic_data()
        
        logger.info(f"Initialized with {len(app.company_data)} companies and {len(app.sic_codes)} SIC codes")
        
    except Exception as e:
        logger.error(f"Error during app initialization: {e}")
        # Create minimal data as final fallback
        app.company_data = pd.DataFrame([{
            'Company Name': 'Demo Company',
            'Sales (USD)': 1000000,
            'SIC Code': '7372',
            'SIC_Accuracy': 0.85,
            'Description': 'Demo company for Azure deployment'
        }])
        app.sic_codes = pd.DataFrame([{
            'SIC Code': '7372', 
            'Description': 'Prepackaged Software'
        }])
    
    @app.route('/')
    def index():
        """Main dashboard"""
        try:
            return render_template('index_enhanced.html')
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return jsonify({
                'status': 'success',
                'message': 'Credit Risk Analysis Dashboard (Azure Deployment)',
                'companies': len(app.company_data) if hasattr(app, 'company_data') else 0
            })
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'environment': 'azure',
            'companies_loaded': len(app.company_data) if hasattr(app, 'company_data') else 0,
            'sic_codes_loaded': len(app.sic_codes) if hasattr(app, 'sic_codes') else 0
        })
    
    @app.route('/api/companies')
    def get_companies():
        """Get company data"""
        try:
            if hasattr(app, 'company_data') and not app.company_data.empty:
                # Convert to JSON-serializable format
                companies_json = app.company_data.head(10).fillna('').to_dict('records')
                return jsonify({
                    'status': 'success',
                    'companies': companies_json,
                    'total_count': len(app.company_data)
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'No company data available'
                })
        except Exception as e:
            logger.error(f"Error in get_companies: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/workflow/status')
    def workflow_status():
        """Get workflow status for visualization"""
        try:
            # Return demo workflow status
            agents = [
                {'name': 'Data Ingestion Agent', 'status': 'active', 'progress': 100},
                {'name': 'Anomaly Detection Agent', 'status': 'active', 'progress': 85},
                {'name': 'Sector Classification Agent', 'status': 'processing', 'progress': 60},
                {'name': 'Results Agent', 'status': 'waiting', 'progress': 0}
            ]
            
            return jsonify({
                'status': 'success',
                'agents': agents,
                'overall_progress': 61
            })
        except Exception as e:
            logger.error(f"Error in workflow_status: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'status': 'error',
            'message': 'Endpoint not found',
            'available_endpoints': ['/health', '/api/companies', '/api/workflow/status']
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'environment': 'azure'
        }), 500
    
    return app

if __name__ == '__main__':
    # For local testing
    app = create_azure_app()
    app.run(debug=True, host='0.0.0.0', port=5000)