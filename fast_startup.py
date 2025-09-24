#!/usr/bin/env python3
"""
FAST Azure startup script - minimal initialization for health checks.
Defers all heavy data loading until after health checks pass.
"""

import os
import sys
import logging
from threading import Thread
import time

# Enhanced console output for Azure logs
print("=" * 80)
print("🚀 AZURE FAST STARTUP: Minimal initialization for health checks")
print(f"🐍 Python version: {sys.version}")
print(f"📍 Current directory: {os.getcwd()}")
print(f"🌐 Azure Instance ID: {os.environ.get('WEBSITE_INSTANCE_ID', 'local')}")
print(f"⚙️ Environment: {'Azure App Service' if os.environ.get('WEBSITE_INSTANCE_ID') else 'Local'}")
print("=" * 80)

# Configure enhanced logging for Azure
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] AZURE_LOG - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)  # Azure captures stderr better
    ]
)

logger = logging.getLogger('AZURE_FAST_STARTUP')
logger.info("🚀 Azure Fast Startup Logger Initialized")

try:
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    logger.info(f"📁 Project root added to Python path: {project_root}")
    print(f"AZURE_LOG: Project root: {project_root}")  # Additional console output
    
    # Import Flask quickly
    from flask import Flask, jsonify
    logger.info("✅ Flask imported")
    
    # Create minimal Flask app
    app = Flask(__name__)
    logger.info("✅ Flask app created")
    
    # Global state tracking
    app_state = {
        'startup_complete': True,  # App is ready for health checks
        'data_loading': False,     # Background data loading status
        'data_loaded': False,      # Heavy data operations complete
        'main_app_loaded': False,  # Full app routes loaded
        'startup_time': time.time()
    }
    
    @app.route('/health')
    def health():
        """FAST health check - responds immediately"""
        try:
            uptime = round(time.time() - app_state['startup_time'], 2)
            
            # Log health check request for Azure monitoring
            logger.info(f"🔍 HEALTH CHECK: Uptime={uptime}s, Data Loading={app_state['data_loading']}, Data Loaded={app_state['data_loaded']}")
            print(f"AZURE_LOG: Health check - Uptime: {uptime}s")
            
            health_data = {
                'status': 'healthy',
                'message': 'Fast startup successful - health checks active',
                'startup_method': 'fast_startup',
                'uptime_seconds': uptime,
                'port': os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)),
                'platform': 'Azure App Service' if os.environ.get('WEBSITE_INSTANCE_ID') else 'Local',
                'app_ready': app_state['startup_complete'],
                'data_loading': app_state['data_loading'],
                'data_loaded': app_state['data_loaded'],
                'main_app_loaded': app_state['main_app_loaded'],
                'routes_count': len([rule for rule in app.url_map.iter_rules() if rule.endpoint != 'static']),
                'azure_instance': os.environ.get('WEBSITE_INSTANCE_ID', 'local'),
                'logging_enabled': True
            }
            
            return jsonify(health_data), 200
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Health check failed'
            }), 503
    
    @app.route('/health/live')
    def health_liveness():
        """Liveness probe - app is running"""
        return jsonify({'status': 'alive', 'uptime': time.time() - app_state['startup_time']}), 200
    
    @app.route('/health/ready')
    def health_readiness():
        """Readiness probe - app can serve traffic"""
        return jsonify({
            'status': 'ready',
            'app_ready': app_state['startup_complete'],
            'can_serve_traffic': True
        }), 200
    
    @app.route('/')
    def home():
        """Home endpoint"""
        return jsonify({
            'status': 'running',
            'message': 'Credit Risk Analysis - Fast Startup Active',
            'startup_method': 'fast_startup.py',
            'data_status': 'loaded' if app_state['data_loaded'] else 'loading' if app_state['data_loading'] else 'pending',
            'uptime': round(time.time() - app_state['startup_time'], 2)
        }), 200
    
    def background_data_loading():
        """Background thread for heavy data loading"""
        try:
            logger.info("🔄 AZURE: Starting background data loading...")
            print("AZURE_LOG: Starting background data loading thread")
            app_state['data_loading'] = True
            
            time.sleep(2)  # Brief delay to ensure health checks are working
            
            # Import and load the main application
            logger.info("📦 AZURE: Importing main application...")
            print("AZURE_LOG: Importing flask_main module")
            from app.flask_main import create_app
            logger.info("✅ AZURE: Main app imported successfully")
            
            # Create the full application
            logger.info("🏗️ AZURE: Creating full application with 509 companies...")
            print("AZURE_LOG: Creating full Flask application")
            main_app = create_app()
            logger.info("✅ AZURE: Full application created successfully")
            
            # Add main app routes to our fast app
            routes_added = 0
            for rule in main_app.url_map.iter_rules():
                if rule.endpoint not in ['health', 'health_liveness', 'health_readiness', 'home', 'static']:
                    try:
                        app.add_url_rule(
                            rule.rule,
                            endpoint=f"main_{rule.endpoint}",
                            view_func=main_app.view_functions[rule.endpoint],
                            methods=rule.methods
                        )
                        routes_added += 1
                    except Exception as e:
                        logger.warning(f"⚠️ AZURE: Could not add route {rule.rule}: {e}")
            
            app_state['main_app_loaded'] = True
            app_state['data_loaded'] = True
            app_state['data_loading'] = False
            
            logger.info(f"🎉 AZURE: Background loading complete - full app ready!")
            logger.info(f"📊 AZURE: Total routes loaded: {len([rule for rule in app.url_map.iter_rules()])}")
            logger.info(f"🔗 AZURE: Application routes added: {routes_added}")
            print(f"AZURE_LOG: Background loading completed successfully - {routes_added} routes added")
            
        except Exception as e:
            logger.error(f"❌ AZURE: Background loading failed: {e}")
            print(f"AZURE_ERROR: Background loading failed: {e}")
            app_state['data_loading'] = False
            import traceback
            traceback.print_exc()
    
    # Start background loading immediately but don't block startup
    logger.info("🚀 AZURE: Starting background data loading thread...")
    print("AZURE_LOG: Launching background data loading thread")
    background_thread = Thread(target=background_data_loading, daemon=True)
    background_thread.start()
    
    logger.info("✅ Fast startup complete - health checks ready!")
    
    logger.info("✅ AZURE: Fast startup initialization complete!")
    print("AZURE_LOG: Fast startup initialization completed successfully")
    
    if __name__ == '__main__':
        # Get port from environment
        port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
        
        logger.info(f"🚀 AZURE: Starting FAST Flask app on 0.0.0.0:{port}")
        logger.info(f"🌐 AZURE: Health check endpoints ready: /health, /health/live, /health/ready")
        logger.info(f"🏠 AZURE: Home page ready: /")
        logger.info(f"📈 AZURE: Data loading happens in background thread")
        print(f"AZURE_LOG: Starting Flask server on port {port}")
        print("AZURE_LOG: Health check endpoints are ready for immediate response")
        
        try:
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
        except Exception as e:
            logger.error(f"❌ AZURE: Failed to start app: {e}")
            print(f"AZURE_ERROR: Flask server failed to start: {e}")
            raise

except Exception as e:
    print(f"🆘 AZURE: FAST STARTUP FAILED: {e}")
    print(f"AZURE_ERROR: Startup failure: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)