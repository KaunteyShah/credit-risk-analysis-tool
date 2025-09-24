"""
Dedicated health check script for Azure App Service.
Ultra-fast response to avoid timeout issues.
"""

import os
import sys
from flask import Flask, jsonify

# Create the most minimal Flask app possible
app = Flask(__name__)

@app.route('/health')
def health():
    """Immediate health response"""
    return jsonify({'status': 'ok'}), 200

@app.route('/')
def home():
    """Root health response"""
    return jsonify({'status': 'running', 'app': 'credit-risk'}), 200

if __name__ == '__main__':
    # Get port immediately
    port = int(os.environ.get('PORT', '8000'))
    
    # Start immediately
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )