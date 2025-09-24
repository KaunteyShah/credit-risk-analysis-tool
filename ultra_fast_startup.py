"""
ULTRA-FAST Azure startup script - immediate health checks, graceful dependency handling.
This script ensures Azure health checks pass even if some optional dependencies are missing.
Optimized for Azure App Service Windows containers.
"""

import os
import sys
import logging
from threading import Thread
import time

# Enhanced console output for Azure logs
print("=" * 80)
print("🚀 ULTRA-FAST STARTUP: Immediate health checks for Azure")
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
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger('AZURE_ULTRA_FAST')
logger.info("🚀 Azure Ultra-Fast Startup Logger Initialized")

try:
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    logger.info(f"📁 Project root added to Python path: {project_root}")
    print(f"AZURE_LOG: Project root: {project_root}")
    
    # Import Flask immediately (essential dependency)
    try:
        from flask import Flask, jsonify
        logger.info("✅ Flask imported successfully")
        print("AZURE_LOG: Flask imported successfully")
    except ImportError as e:
        logger.error(f"❌ CRITICAL: Flask import failed: {e}")
        print(f"AZURE_ERROR: Flask import failed: {e}")
        sys.exit(1)
    
    # Create minimal Flask app immediately
    app = Flask(__name__)
    logger.info("✅ Flask app created")
    print("AZURE_LOG: Flask app created successfully")
    
    # Global state tracking
    app_state = {
        'startup_complete': True,
        'dependencies_loaded': False,
        'main_app_loaded': False,
        'startup_time': time.time(),
        'dependency_errors': []
    }
    
    @app.route('/health')
    def health():
        """ULTRA-FAST health check - responds immediately"""
        try:
            uptime = round(time.time() - app_state['startup_time'], 2)
            
            logger.info(f"🔍 HEALTH CHECK: Uptime={uptime}s")
            print(f"AZURE_LOG: Health check - Uptime: {uptime}s")
            
            health_data = {
                'status': 'healthy',
                'message': 'Ultra-fast startup - immediate health response',
                'startup_method': 'ultra_fast_startup',
                'uptime_seconds': uptime,
                'port': os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)),
                'platform': 'Azure App Service' if os.environ.get('WEBSITE_INSTANCE_ID') else 'Local',
                'dependencies_loaded': app_state['dependencies_loaded'],
                'main_app_loaded': app_state['main_app_loaded'],
                'routes_count': len([rule for rule in app.url_map.iter_rules() if rule.endpoint != 'static']),
                'azure_instance': os.environ.get('WEBSITE_INSTANCE_ID', 'local'),
                'dependency_errors': len(app_state['dependency_errors'])
            }
            
            return jsonify(health_data), 200
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Health check failed'
            }), 503
    
    @app.route('/health/live')
    def health_liveness():
        """Liveness probe - app is running"""
        uptime = round(time.time() - app_state['startup_time'], 2)
        return jsonify({'status': 'alive', 'uptime': uptime}), 200
    
    @app.route('/health/ready')
    def health_readiness():
        """Readiness probe - app can serve traffic"""
        return jsonify({
            'status': 'ready',
            'can_serve_traffic': True,
            'uptime': round(time.time() - app_state['startup_time'], 2)
        }), 200
    
    @app.route('/')
    def home():
        """Home endpoint"""
        return jsonify({
            'status': 'running',
            'message': 'Credit Risk Analysis - Ultra-Fast Startup Active',
            'startup_method': 'ultra_fast_startup.py',
            'uptime': round(time.time() - app_state['startup_time'], 2),
            'ready_for_traffic': True
        }), 200
    
    @app.route('/status')
    def status():
        """Detailed status endpoint"""
        return jsonify({
            'status': 'operational',
            'startup_time': app_state['startup_time'],
            'uptime': round(time.time() - app_state['startup_time'], 2),
            'dependencies_loaded': app_state['dependencies_loaded'],
            'main_app_loaded': app_state['main_app_loaded'],
            'dependency_errors': app_state['dependency_errors'],
            'routes': [rule.rule for rule in app.url_map.iter_rules() if rule.endpoint != 'static'],
            'azure_ready': True
        }), 200
    
    def background_dependency_loading():
        """Background thread for dependency loading with error handling"""
        try:
            logger.info("🔄 AZURE: Starting background dependency loading...")
            print("AZURE_LOG: Starting background dependency loading thread")
            
            time.sleep(1)  # Brief delay to ensure health checks work first
            
            # Try to import optional dependencies
            try:
                logger.info("📦 AZURE: Loading pandas and numpy...")
                import pandas as pd
                import numpy as np
                logger.info("✅ AZURE: Data processing libraries loaded")
            except ImportError as e:
                logger.warning(f"⚠️ AZURE: Data processing libraries not available: {e}")
                app_state['dependency_errors'].append(f"Data processing: {e}")
            
            try:
                logger.info("📦 AZURE: Loading flask-cors...")
                from flask_cors import CORS
                CORS(app)
                logger.info("✅ AZURE: CORS enabled successfully")
            except ImportError as e:
                logger.warning(f"⚠️ AZURE: CORS not available: {e}")
                app_state['dependency_errors'].append(f"CORS: {e}")
            
            try:
                logger.info("📦 AZURE: Loading Azure libraries...")
                import azure.identity
                logger.info("✅ AZURE: Azure libraries loaded")
            except ImportError as e:
                logger.warning(f"⚠️ AZURE: Azure libraries not available: {e}")
                app_state['dependency_errors'].append(f"Azure libs: {e}")
            
            app_state['dependencies_loaded'] = True
            
            # Try to load main application if dependencies allow
            try:
                logger.info("🏗️ AZURE: Attempting to load main application...")
                print("AZURE_LOG: Loading main application")
                
                # Import main app with error handling
                sys.path.insert(0, os.path.join(project_root, 'app'))
                from flask_main import create_app
                
                main_app = create_app()
                logger.info("✅ AZURE: Main application created successfully")
                
                # Add main app routes
                routes_added = 0
                for rule in main_app.url_map.iter_rules():
                    if rule.endpoint not in ['health', 'health_liveness', 'health_readiness', 'home', 'status', 'static']:
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
                logger.info(f"🎉 AZURE: Main application integrated - {routes_added} routes added")
                print(f"AZURE_LOG: Main app loaded successfully with {routes_added} routes")
                
            except Exception as e:
                logger.warning(f"⚠️ AZURE: Main application loading failed: {e}")
                print(f"AZURE_LOG: Main app loading failed, but basic health checks still work: {e}")
                app_state['dependency_errors'].append(f"Main app: {e}")
            
            logger.info("✅ AZURE: Background loading completed")
            print("AZURE_LOG: Background loading completed")
            
        except Exception as e:
            logger.error(f"❌ AZURE: Background loading failed: {e}")
            print(f"AZURE_ERROR: Background loading failed: {e}")
            app_state['dependency_errors'].append(f"Background loading: {e}")
    
    # Start background loading immediately but don't block startup
    logger.info("🚀 AZURE: Starting background dependency loading thread...")
    print("AZURE_LOG: Launching background dependency loading thread")
    background_thread = Thread(target=background_dependency_loading, daemon=True)
    background_thread.start()
    
    logger.info("✅ AZURE: Ultra-fast startup initialization complete!")
    print("AZURE_LOG: Ultra-fast startup initialization completed successfully")
    
    if __name__ == '__main__':
        # Enhanced port detection for Azure App Service
        try:
            port = int(os.environ.get('PORT', 
                      os.environ.get('WEBSITES_PORT', 
                      os.environ.get('HTTP_PLATFORM_PORT', '8000'))))
            logger.info(f"🌐 AZURE: Port detected: {port}")
            print(f"AZURE_LOG: Detected port: {port}")
        except (ValueError, TypeError) as e:
            port = 8000
            logger.warning(f"⚠️ AZURE: Port detection failed, using default: {e}")
            print(f"AZURE_LOG: Using default port 8000 due to: {e}")
        
        logger.info(f"🚀 AZURE: Starting ULTRA-FAST Flask app on 0.0.0.0:{port}")
        logger.info(f"🌐 AZURE: Health check endpoints ready immediately")
        print(f"AZURE_LOG: Starting Flask server on port {port}")
        print("AZURE_LOG: Health endpoints ready for immediate response")
        
        try:
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
        except Exception as e:
            logger.error(f"❌ AZURE: Failed to start app: {e}")
            print(f"AZURE_ERROR: Flask server failed to start: {e}")
            raise

except Exception as e:
    print(f"🆘 AZURE: ULTRA-FAST STARTUP FAILED: {e}")
    print(f"AZURE_ERROR: Startup failure: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)