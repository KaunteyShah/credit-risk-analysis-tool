#!/usr/bin/env python3
"""
Minimal Azure App Service entry point for Credit Risk Analysis Tool.
Fast-starting version that defers heavy initialization.
"""

import os
import sys
import logging
from flask import Flask, jsonify

# Configure minimal logging for Azure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def create_minimal_app():
    """Create a minimal Flask app for fast Azure startup"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'azure-demo-key')
    
    @app.route('/health')
    def health_check():
        return jsonify({'status': 'healthy', 'message': 'Flask app is running'}), 200
    
    @app.route('/')
    def home():
        return jsonify({
            'status': 'running', 
            'message': 'Credit Risk Analysis Tool - Minimal Azure Version',
            'endpoints': ['/health', '/api/status']
        }), 200
    
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'api': 'active',
            'version': '1.0.0',
            'environment': 'azure-production'
        }), 200
    
    # Lazy load the full app when needed
    @app.route('/api/load-full-app', methods=['POST'])
    def load_full_app():
        try:
            logger.info("🔄 Loading full application features...")
            # Import the full app creation function
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from app.flask_main import create_app as create_full_app
            
            # This would require a more complex setup to merge routes
            return jsonify({
                'status': 'success',
                'message': 'Full application features can be loaded on demand'
            }), 200
        except Exception as e:
            logger.error(f"❌ Failed to load full app: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Failed to load full app: {str(e)}'
            }), 500
    
    return app

# Create the minimal Flask application
logger.info("🚀 Creating minimal Flask application for Azure...")
app = create_minimal_app()
application = app  # For Gunicorn/Azure

if __name__ == '__main__':
    # Get port from Azure environment
    port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
    
    logger.info(f"🌐 Starting minimal Flask app on port {port}")
    logger.info(f"✅ Health check: /health")
    logger.info(f"✅ Status check: /api/status")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Failed to start app: {e}")
        raise