#!/usr/bin/env python3
"""
Azure App Service entry point for Credit Risk Analysis Tool.
Simple version that creates a basic Flask app without complex dependencies.
"""

import os
import sys
import logging

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging for Azure App Service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create a simple Flask application for Azure deployment
from flask import Flask, jsonify, request, render_template_string
import json
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Simple HTML template for file upload
UPLOAD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Credit Risk Analysis Tool</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .upload-box { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
        .result { background: #f0f0f0; padding: 20px; margin: 20px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Credit Risk Analysis Tool</h1>
        <p>Upload a CSV file to analyze credit risk data</p>
        
        <form action="/upload" method="post" enctype="multipart/form-data">
            <div class="upload-box">
                <input type="file" name="file" accept=".csv" required>
                <br><br>
                <button type="submit">Upload and Analyze</button>
            </div>
        </form>
        
        {% if result %}
        <div class="result">
            <h3>Analysis Result:</h3>
            <pre>{{ result }}</pre>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(UPLOAD_TEMPLATE)

@app.route('/api')
def api_info():
    return jsonify({
        "status": "healthy",
        "message": "Credit Risk Analysis Tool - API",
        "version": "1.0.0",
        "endpoints": ["/", "/api", "/health", "/upload"]
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": "2024-09-24"
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({"error": "Please upload a CSV file"}), 400
        
        # Read file content
        content = file.read().decode('utf-8')
        lines = content.strip().split('\n')
        
        if len(lines) < 2:
            return jsonify({"error": "CSV file must have at least 2 lines (header + data)"}), 400
        
        # Parse basic info
        header = lines[0].split(',')
        data_rows = len(lines) - 1
        
        result = {
            "filename": file.filename,
            "columns": len(header),
            "column_names": [col.strip() for col in header],
            "data_rows": data_rows,
            "total_size": len(content),
            "status": "success",
            "message": f"Successfully processed {data_rows} rows with {len(header)} columns"
        }
        
        # Return JSON for API calls, HTML for browser
        if request.headers.get('Accept') == 'application/json':
            return jsonify(result)
        else:
            return render_template_string(UPLOAD_TEMPLATE, result=json.dumps(result, indent=2))
            
    except Exception as e:
        error_result = {"error": str(e), "status": "failed"}
        if request.headers.get('Accept') == 'application/json':
            return jsonify(error_result), 500
        else:
            return render_template_string(UPLOAD_TEMPLATE, result=json.dumps(error_result, indent=2))

# For Azure App Service with Gunicorn
application = app

logger.info("✅ Simple Flask application created successfully")

if __name__ == '__main__':
    # Azure App Service uses the PORT environment variable
    port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
    
    logger.info(f"🌐 Environment variables:")
    logger.info(f"   PORT: {os.environ.get('PORT', 'not set')}")
    logger.info(f"   WEBSITES_PORT: {os.environ.get('WEBSITES_PORT', 'not set')}")
    logger.info(f"   Using port: {port}")
    
    logger.info(f"🚀 Starting Flask application on 0.0.0.0:{port}")
    logger.info(f"✅ Health check available at /health")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Failed to start Flask app: {e}")
        raise