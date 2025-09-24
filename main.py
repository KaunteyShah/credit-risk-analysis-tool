#!/usr/bin/env python3
"""
Azure App Service entry point for Credit Risk Analysis Tool.
Simple version that creates a basic Flask app without complex dependencies.
"""

import os
import sys
import logging

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging for Azure App Service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create a simple Flask application for Azure deployment
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "healthy",
        "message": "Credit Risk Analysis Tool - Basic Version",
        "version": "1.0.0"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": "2024-09-24"
    })

# For Azure App Service with Gunicorn
application = app

logger.info("✅ Simple Flask application created successfully")

if __name__ == '__main__':
    # Azure App Service uses the PORT environment variable
    port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
    
    logger.info(f"🌐 Environment variables:")
    logger.info(f"   PORT: {os.environ.get('PORT', 'not set')}")
    logger.info(f"   WEBSITES_PORT: {os.environ.get('WEBSITES_PORT', 'not set')}")
    logger.info(f"   Using port: {port}")
    
    logger.info(f"🚀 Starting Flask application on 0.0.0.0:{port}")
    logger.info(f"✅ Health check available at /health")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Failed to start Flask app: {e}")
        raise