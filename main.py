#!/usr/bin/env python3
"""
Main entry point for the Credit Risk Analysis application on Azure App Service.
This file serves as the entry point that Azure App Service can automatically detect.
"""
import os
import sys
import subprocess

def main():
    """Main entry point for the application."""
    print("🚀 Starting Credit Risk Analysis Application...")
    
    # Set environment variables
    os.environ['PYTHONPATH'] = '/home/site/wwwroot'
    port = os.environ.get('WEBSITES_PORT', '8000')
    
    # Install dependencies if needed
    try:
        import streamlit
        print("✅ Streamlit already installed")
    except ImportError:
        print("📦 Installing dependencies...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    
    # Start Streamlit app
    print(f"🌐 Starting Streamlit application on port {port}...")
    
    # Run Streamlit with the correct module path
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 
        'app/core/streamlit_app_langgraph_viz.py',
        '--server.port', port,
        '--server.address', '0.0.0.0',
        '--server.headless', 'true'
    ]
    
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
