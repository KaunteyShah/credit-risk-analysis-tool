#!/usr/bin/env python3
"""
Test Lightweight Flask Server - Bypassing Heavy Data Loading for Testing
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_lightweight_app():
    """Create a lightweight Flask app for testing without heavy data loading"""
    app = Flask(__name__, 
                template_folder='modular_templates',
                static_folder='modular_static')
    CORS(app)
    
    # Mock data for testing
    mock_companies = [
        {"company_name": "Test Company 1", "country": "United States", "sic_code": "1234"},
        {"company_name": "Test Company 2", "country": "Canada", "sic_code": "5678"},
        {"company_name": "Test Company 3", "country": "United Kingdom", "sic_code": "9012"}
    ]
    
    @app.route('/api/modular/health', methods=['GET'])
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'company_service': {'status': 'operational'},
                'sic_service': {'status': 'operational'}
            },
            'data': {
                'loaded': True,
                'company_count': len(mock_companies),
                'lightweight_mode': True
            }
        })
    
    @app.route('/api/modular/companies', methods=['GET'])
    def companies():
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        return jsonify({
            'companies': mock_companies,
            'total': len(mock_companies),
            'page': page,
            'per_page': limit,
            'lightweight_mode': True
        })
    
    @app.route('/api/modular/companies/<int:company_index>', methods=['GET'])
    def company_details(company_index):
        if 0 <= company_index < len(mock_companies):
            company = mock_companies[company_index]
            return jsonify({
                **company,
                'lightweight_mode': True,
                'ai_reasoning': 'Test reasoning for lightweight mode',
                'index': company_index
            })
        return jsonify({'error': 'Company not found'}), 404
    
    @app.route('/api/modular/filter-options', methods=['GET'])
    def filter_options():
        return jsonify({
            'countries': ['United States', 'Canada', 'United Kingdom'],
            'sectors': ['Technology', 'Finance', 'Healthcare'],
            'lightweight_mode': True
        })
    
    return app

if __name__ == "__main__":
    print("🚀 Starting Lightweight Test Server...")
    app = create_test_lightweight_app()
    print(f"✅ Lightweight server ready with {len(list(app.url_map.iter_rules()))} routes")
    print("   🎯 No heavy data loading - fast responses guaranteed!")
    app.run(host='127.0.0.1', port=5004, debug=False)