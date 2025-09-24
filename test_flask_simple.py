#!/usr/bin/env python3
"""
Ultra simple Flask app for testing Azure startup
"""
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return {
        "status": "SUCCESS",
        "message": "Simple Flask app is working!",
        "startup_command": "python3 test_flask_simple.py",
        "environment": "Azure App Service",
        "python_path": os.sys.executable if hasattr(os, 'sys') else "unknown"
    }

@app.route('/health')
def health():
    return {"status": "healthy", "app": "test_flask_simple"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
    print(f"🚀 Starting SIMPLE Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)