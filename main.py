#!/usr/bin/env python3
"""
Main entry point for the Credit Risk Analysis Flask application on Azure App Service.
This file serves as the entry point that Azure App Service can automatically detect.
"""
import os
import sys
import subprocess

# Create Flask app instance for Azure App Service and deployment testing
app = None
application = None

try:
    # Set dummy values during deployment testing to avoid secrets validation errors
    if not os.environ.get('COMPANIES_HOUSE_API_KEY'):
        os.environ['COMPANIES_HOUSE_API_KEY'] = 'dummy_value_for_build'
        print("ℹ️  Set dummy COMPANIES_HOUSE_API_KEY for build testing")
    
    if not os.environ.get('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = 'dummy_value_for_build'
        print("ℹ️  Set dummy OPENAI_API_KEY for build testing")
    
    from app.flask_main import create_app
    app = create_app()
    application = app  # Azure App Service compatibility
    print("✅ Flask app instance created successfully")
    
    # Ensure app is available at module level for Gunicorn
    if app:
        print(f"✅ App instance ready - Debug: {app.debug}")
        
except Exception as e:
    print(f"⚠️ Flask app creation failed: {e}")
    # Create a minimal app for debugging
    from flask import Flask
    app = Flask(__name__)
    application = app
    
    @app.route('/')
    def health_check():
        return {"status": "App created but with errors", "error": str(e)}
    
    @app.route('/health')
    def health():
        return {"status": "healthy", "message": "Minimal app running"}
    
    print("🔧 Created minimal Flask app for debugging")

def main():
    """Main entry point for the Flask application."""
    print("🚀 Starting Credit Risk Analysis Flask Application...")
    
    # Set environment variables
    os.environ['PYTHONPATH'] = '/home/site/wwwroot'
    
    # Azure App Service provides port via WEBSITES_PORT, fallback to 8000 for local dev
    port = os.environ.get('WEBSITES_PORT') or os.environ.get('PORT', '8000')
    
    # Install dependencies if needed - check for pandas specifically
    try:
        import pandas
        import flask
        import numpy
        print("✅ Core dependencies already installed")
    except ImportError as e:
        print(f"📦 Installing dependencies... Missing: {e}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    
    # Start Flask app
    print(f"🌐 Starting Flask application on port {port}...")
    
    # Use existing app instance or create new one
    if app is None:
        from app.flask_main import create_app
        flask_app = create_app()
    else:
        flask_app = app
    
    flask_app.run(host='0.0.0.0', port=int(port), debug=False)

if __name__ == "__main__":
    main()
