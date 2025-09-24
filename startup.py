#!/usr/bin/env python3
"""
EMERGENCY Azure startup script to bypass all caching issues.
This script will be used as the entry point instead of main.py
to completely avoid any cached/corrupted main.py files.
"""

import os
import sys
import logging

print("🆘 EMERGENCY STARTUP: Bypassing all Azure caches")
print(f"🐍 Python version: {sys.version}")
print(f"📍 Current directory: {os.getcwd()}")
print(f"📁 Files in current directory: {os.listdir('.')}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

try:
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    logger.info("🔧 Project root added to Python path")
    
    # Import Flask directly here to avoid any import caching issues
    from flask import Flask, jsonify
    logger.info("✅ Flask imported successfully")
    
    # Create Flask app directly in this file
    app = Flask(__name__)
    logger.info("✅ Flask app created")
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'message': 'Emergency startup successful - bypassed all caches',
            'startup_method': 'emergency_bypass',
            'python_version': sys.version,
            'instance_id': os.environ.get('WEBSITE_INSTANCE_ID', 'local')
        }), 200
    
    @app.route('/')
    def home():
        return jsonify({
            'status': 'running',
            'message': 'Credit Risk Analysis - Emergency deployment active',
            'cache_bypass': True,
            'deployment_method': 'startup.py'
        }), 200
    
    logger.info("✅ Routes configured successfully")
    
    # Try to import the main application
    try:
        from app.flask_main import create_app
        logger.info("✅ Main app import successful - will upgrade to full app")
        
        # Create the full application
        main_app = create_app()
        
        # Copy all routes from main app to our emergency app
        for rule in main_app.url_map.iter_rules():
            if rule.endpoint not in ['health', 'static']:
                try:
                    app.add_url_rule(
                        rule.rule,
                        endpoint=f"main_{rule.endpoint}",
                        view_func=main_app.view_functions[rule.endpoint],
                        methods=rule.methods
                    )
                    logger.info(f"✅ Added route: {rule.rule}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not add route {rule.rule}: {e}")
        
        logger.info("🚀 Full application routes integrated into emergency app")
        
    except Exception as e:
        logger.warning(f"⚠️ Could not import main app: {e}")
        logger.info("🔧 Running in emergency mode with basic endpoints only")
    
    if __name__ == '__main__':
        # Get port from environment
        port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
        
        logger.info(f"🚀 Starting emergency Flask app on 0.0.0.0:{port}")
        logger.info(f"🌐 Health check: /health")
        logger.info(f"🏠 Home page: /")
        
        try:
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
        except Exception as e:
            logger.error(f"❌ Failed to start emergency app: {e}")
            raise

except Exception as e:
    print(f"🆘 EMERGENCY STARTUP FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)