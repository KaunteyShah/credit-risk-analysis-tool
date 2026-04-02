#!/usr/bin/env python3
"""
Flask Application - Credit Risk Analysis Tool
Single entry point for the complete enterprise application with database integration
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main Flask app from app_modules
from app_modules.flask_main import create_app

def main():
    """Main entry point for the Credit Risk Analysis Tool"""
    print("🚀 Starting Credit Risk Analysis Tool")
    print("=" * 50)
    
    try:
        # Set the database type to SQLite for local development
        os.environ['DATABASE_TYPE'] = 'sqlite'
        
        # Create the Flask application
        print("📦 Creating Flask application...")
        app = create_app()
        print("✅ Flask application created successfully")
        
    except Exception as e:
        print(f"❌ Failed to create Flask application: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Configure port - use 5002 to avoid conflicts
    port = int(os.environ.get('PORT', 5002))
    
    print(f"🎯 Application will be available at: http://localhost:{port}")
    print("📊 Database: SQLite (509 companies, 751 SIC codes)")
    print("🔍 Enhanced Filtering: http://localhost:{port}/filters")
    print("📈 Dashboard: http://localhost:{port}/dashboard") 
    print("🛠️  API Health Check: http://localhost:{port}/health")
    print("=" * 50)
    print("💡 Press Ctrl+C to stop the server")
    print()
    
    try:
        # Start the Flask server with stable configuration
        print(f"🚀 Starting stable Flask server on port {port}...")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            use_reloader=False,  # Disable reloader to prevent restart loops
            threaded=True,       # Enable threading for better performance
            use_debugger=False   # Disable debugger for stability
        )
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()
        print("🔄 Try running: lsof -ti:5002 | xargs kill -9")
        return False

if __name__ == '__main__':
    main()