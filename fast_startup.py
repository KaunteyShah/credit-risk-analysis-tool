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

print("🚀 FAST STARTUP: Minimal initialization for Azure health checks")
print(f"🐍 Python version: {sys.version}")
print(f"📍 Current directory: {os.getcwd()}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

try:
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
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
                'routes_count': len([rule for rule in app.url_map.iter_rules() if rule.endpoint != 'static'])
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
            logger.info("🔄 Starting background data loading...")
            app_state['data_loading'] = True
            
            time.sleep(2)  # Brief delay to ensure health checks are working
            
            # Import and load the main application
            from app.flask_main import create_app
            logger.info("✅ Main app imported")
            
            # Create the full application
            main_app = create_app()
            logger.info("✅ Full application created")
            
            # Add main app routes to our fast app
            for rule in main_app.url_map.iter_rules():
                if rule.endpoint not in ['health', 'health_liveness', 'health_readiness', 'home', 'static']:
                    try:
                        app.add_url_rule(
                            rule.rule,
                            endpoint=f"main_{rule.endpoint}",
                            view_func=main_app.view_functions[rule.endpoint],
                            methods=rule.methods
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Could not add route {rule.rule}: {e}")
            
            app_state['main_app_loaded'] = True
            app_state['data_loaded'] = True
            app_state['data_loading'] = False
            
            logger.info("🎉 Background loading complete - full app ready!")
            logger.info(f"📊 Total routes: {len([rule for rule in app.url_map.iter_rules()])}")
            
        except Exception as e:
            logger.error(f"❌ Background loading failed: {e}")
            app_state['data_loading'] = False
            import traceback
            traceback.print_exc()
    
    # Start background loading immediately but don't block startup
    logger.info("🚀 Starting background data loading thread...")
    background_thread = Thread(target=background_data_loading, daemon=True)
    background_thread.start()
    
    logger.info("✅ Fast startup complete - health checks ready!")
    
    if __name__ == '__main__':
        # Get port from environment
        port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
        
        logger.info(f"🚀 Starting FAST Flask app on 0.0.0.0:{port}")
        logger.info(f"🌐 Health check: /health (responds immediately)")
        logger.info(f"🏠 Home page: / (responds immediately)")
        logger.info(f"📈 Data loading happens in background thread")
        
        try:
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
        except Exception as e:
            logger.error(f"❌ Failed to start app: {e}")
            raise

except Exception as e:
    print(f"🆘 FAST STARTUP FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)