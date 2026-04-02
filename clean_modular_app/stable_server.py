#!/usr/bin/env python3
"""
Stable Flask Server - Credit Risk Analysis Tool
Production-ready server configuration without debug mode issues
"""

import os
import sys
import signal
import logging
from werkzeug.serving import WSGIRequestHandler

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Configure logging for the stable server"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('stable_server.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n🛑 Shutting down server gracefully...')
    sys.exit(0)

def main():
    """Main entry point for the stable server"""
    logger = setup_logging()
    
    print("🚀 Starting Stable Credit Risk Analysis Server")
    print("=" * 50)
    
    try:
        # Set environment variables
        os.environ['DATABASE_TYPE'] = 'sqlite'
        os.environ['FLASK_ENV'] = 'production'
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        
        # Import and create Flask app
        logger.info("Creating Flask application...")
        from app_modules.flask_main import create_app
        app = create_app()
        logger.info("✅ Flask application created successfully")
        
        # Configure port
        port = int(os.environ.get('PORT', 5002))
        
        print(f"🎯 Stable server starting at: http://localhost:{port}")
        print("📊 Database: SQLite (509 companies, 751 SIC codes)")
        print("🔧 Configuration: Production-ready, no reloader")
        print("=" * 50)
        print("💡 Press Ctrl+C to stop the server")
        print()
        
        # Disable Werkzeug request logging for cleaner output
        WSGIRequestHandler.log_request = lambda self, *args, **kwargs: None
        
        # Start the server with stable configuration
        logger.info(f"Starting server on port {port}...")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,           # Disable debug mode completely
            use_reloader=False,    # No auto-restart
            use_debugger=False,    # No debugger
            threaded=True,         # Enable threading
            processes=1            # Single process
        )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\n✅ Server stopped gracefully")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n🔧 Troubleshooting tips:")
        print("1. Check if port 5002 is in use: lsof -i :5002")
        print("2. Kill existing processes: lsof -ti:5002 | xargs kill -9")
        print("3. Check database permissions: ls -la data/credit_risk.db")
        return False

if __name__ == '__main__':
    main()