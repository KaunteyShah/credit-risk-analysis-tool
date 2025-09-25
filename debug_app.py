"""
Minimal Flask app for Azure debugging - helps identify deployment issues
"""
import os
from flask import Flask, jsonify, render_template_string

def create_minimal_app():
    """Create a minimal Flask app for debugging Azure deployment issues"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'minimal-debug-key'
    
    @app.route('/')
    def home():
        return jsonify({
            'status': 'Minimal app running',
            'message': 'This is a debug version to test Azure deployment',
            'python_version': os.sys.version,
            'working_directory': os.getcwd(),
            'environment_vars': {
                'WEBSITES_PORT': os.environ.get('WEBSITES_PORT', 'Not set'),
                'PORT': os.environ.get('PORT', 'Not set'),
                'PYTHONPATH': os.environ.get('PYTHONPATH', 'Not set')
            },
            'files_exist': {
                'main.py': os.path.exists('/home/site/wwwroot/main.py'),
                'app_folder': os.path.exists('/home/site/wwwroot/app'),
                'data_folder': os.path.exists('/home/site/wwwroot/data'),
                'requirements.txt': os.path.exists('/home/site/wwwroot/requirements.txt')
            }
        })
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy', 'app': 'minimal_debug'})
    
    @app.route('/test')
    def test():
        """Test endpoint with basic functionality"""
        try:
            import pandas as pd
            import numpy as np
            return jsonify({
                'pandas_version': pd.__version__,
                'numpy_version': np.__version__,
                'test': 'success'
            })
        except Exception as e:
            return jsonify({'error': str(e), 'test': 'failed'})
    
    @app.route('/ui')
    def ui():
        """Simple UI for testing"""
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Debug App</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .status { background: #e8f5e8; padding: 20px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>Azure Deployment Debug App</h1>
            <div class="status">
                <h2>✅ App is running successfully!</h2>
                <p>This minimal version helps identify deployment issues.</p>
                <ul>
                    <li><a href="/">JSON Status</a></li>
                    <li><a href="/health">Health Check</a></li>
                    <li><a href="/test">Package Test</a></li>
                </ul>
            </div>
        </body>
        </html>
        ''')
    
    return app

# Create the minimal app instance
app = create_minimal_app()
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)