#!/usr/bin/env python3
"""
Main entry point for the Credit Risk Analysis Flask application on Azure App Service.
This file serves as the entry point that Azure App Service can automatically detect.
"""
import os
import sys
import subprocess

def main():
    """Main entry point for the Flask application."""
    print("🚀 Starting Credit Risk Analysis Flask Application...")
    
    # Set environment variables
    os.environ['PYTHONPATH'] = '/home/site/wwwroot'
    port = os.environ.get('WEBSITES_PORT', '8000')
    
    # Install dependencies if needed
    try:
        import flask
        print("✅ Flask already installed")
    except ImportError:
        print("📦 Installing dependencies...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    
    # Start Flask app
    print(f"🌐 Starting Flask application on port {port}...")
    
    # Import and run the Flask app
    from app.flask_app import create_app
    
    app = create_app()
    app.run(host='0.0.0.0', port=int(port), debug=False)

if __name__ == "__main__":
    main()
