"""
ULTRA-FAST Azure startup script - immediate health response.
This script starts Flask server instantly for Azure health checks.
"""

import os
import sys

# Immediate startup logging
print("🚀 ULTRA-FAST STARTUP: Starting immediately for Azure health checks")

# Quick CORS check without installation delay
flask_cors_available = False
try:
    import flask_cors
    flask_cors_available = True
    print("✅ flask-cors available")
except ImportError:
    print("⚠️ flask-cors not available, will run without CORS")

try:
    # Essential imports only
    from flask import Flask, jsonify
    print("✅ Flask imported")
    
    # Create Flask app immediately
    app = Flask(__name__)
    print("✅ Flask app created")
    
    # Optional CORS setup if available (no delays)
    if flask_cors_available:
        try:
            from flask_cors import CORS
            CORS(app)
            print("✅ CORS enabled")
        except Exception:
            print("⚠️ CORS setup skipped")
    
    # IMMEDIATE health endpoint - critical for Azure
    @app.route('/health')
    def health():
        """Immediate health response for Azure"""
        return jsonify({
            'status': 'healthy',
            'message': 'Ultra-fast startup active'
        }), 200
    
    @app.route('/')
    def home():
        """Root endpoint"""
        return jsonify({
            'status': 'running',
            'message': 'Credit Risk Analysis - Ultra Fast Startup',
            'health_endpoint': '/health'
        }), 200
    
    # Quick port detection
    def get_port():
        """Fast port detection for Azure"""
        return int(os.environ.get('PORT', 
                  os.environ.get('WEBSITES_PORT', 
                  os.environ.get('HTTP_PLATFORM_PORT', '8000'))))
    
    if __name__ == '__main__':
        port = get_port()
        print(f"🚀 Starting Flask on port {port}")
        
        # Start Flask immediately
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True,
            use_reloader=False  # Critical for Azure containers
        )

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("⚠️ Exiting - Flask not available")
    sys.exit(1)
except Exception as e:
    print(f"❌ Startup failed: {e}")
    sys.exit(1)