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

def perform_credit_risk_analysis(headers, data_rows, available_columns):
    """
    Perform basic credit risk analysis without pandas
    """
    analysis = {
        "summary": {},
        "risk_distribution": {},
        "recommendations": []
    }
    
    try:
        # Parse all data rows
        parsed_data = []
        for row_text in data_rows:
            row_values = [cell.strip() for cell in row_text.split(',')]
            if len(row_values) == len(headers):
                row_dict = dict(zip(headers, row_values))
                parsed_data.append(row_dict)
        
        total_companies = len(parsed_data)
        analysis["summary"]["total_companies"] = total_companies
        
        if total_companies == 0:
            return analysis
        
        # Analyze credit scores if available
        if 'credit_score' in available_columns:
            credit_scores = []
            for row in parsed_data:
                try:
                    score = float(row['credit_score'])
                    if 300 <= score <= 850:  # Valid credit score range
                        credit_scores.append(score)
                except (ValueError, KeyError):
                    continue
            
            if credit_scores:
                avg_credit = sum(credit_scores) / len(credit_scores)
                min_credit = min(credit_scores)
                max_credit = max(credit_scores)
                
                analysis["summary"]["credit_score_stats"] = {
                    "average": round(avg_credit, 2),
                    "minimum": min_credit,
                    "maximum": max_credit,
                    "companies_with_scores": len(credit_scores)
                }
                
                # Credit score risk categories
                excellent = sum(1 for s in credit_scores if s >= 750)
                good = sum(1 for s in credit_scores if 700 <= s < 750)
                fair = sum(1 for s in credit_scores if 650 <= s < 700)
                poor = sum(1 for s in credit_scores if s < 650)
                
                analysis["risk_distribution"]["credit_score_risk"] = {
                    "excellent_750_plus": excellent,
                    "good_700_749": good,
                    "fair_650_699": fair,
                    "poor_below_650": poor
                }
        
        # Analyze annual revenue if available
        if 'annual_revenue' in available_columns:
            revenues = []
            for row in parsed_data:
                try:
                    revenue = float(row['annual_revenue'])
                    if revenue >= 0:  # Valid revenue
                        revenues.append(revenue)
                except (ValueError, KeyError):
                    continue
            
            if revenues:
                avg_revenue = sum(revenues) / len(revenues)
                total_revenue = sum(revenues)
                
                analysis["summary"]["revenue_stats"] = {
                    "average_revenue": round(avg_revenue, 2),
                    "total_revenue": round(total_revenue, 2),
                    "companies_with_revenue": len(revenues)
                }
                
                # Revenue size categories
                large = sum(1 for r in revenues if r >= 10000000)  # 10M+
                medium = sum(1 for r in revenues if 1000000 <= r < 10000000)  # 1M-10M
                small = sum(1 for r in revenues if r < 1000000)  # <1M
                
                analysis["risk_distribution"]["company_size"] = {
                    "large_10m_plus": large,
                    "medium_1m_to_10m": medium,
                    "small_under_1m": small
                }
        
        # Analyze existing risk levels if available
        if 'risk_level' in available_columns:
            risk_levels = {}
            for row in parsed_data:
                risk = row.get('risk_level', '').strip().lower()
                if risk:
                    risk_levels[risk] = risk_levels.get(risk, 0) + 1
            
            analysis["risk_distribution"]["existing_risk_levels"] = risk_levels
        
        # Industry analysis if available
        if 'industry' in available_columns:
            industries = {}
            for row in parsed_data:
                industry = row.get('industry', '').strip()
                if industry:
                    industries[industry] = industries.get(industry, 0) + 1
            
            analysis["summary"]["industry_distribution"] = industries
        
        # Generate recommendations
        recommendations = []
        
        if 'credit_score' in analysis.get("summary", {}):
            avg_score = analysis["summary"]["credit_score_stats"]["average"]
            if avg_score < 650:
                recommendations.append("Portfolio has low average credit score. Consider additional risk mitigation.")
            elif avg_score > 750:
                recommendations.append("Portfolio has strong credit scores. Low credit risk profile.")
        
        if 'company_size' in analysis.get("risk_distribution", {}):
            small_cos = analysis["risk_distribution"]["company_size"]["small_under_1m"]
            if small_cos > total_companies * 0.7:
                recommendations.append("Portfolio is heavily weighted toward smaller companies. Monitor cash flow closely.")
        
        if not recommendations:
            recommendations.append("Portfolio analysis complete. Continue monitoring key risk indicators.")
        
        analysis["recommendations"] = recommendations
        
    except Exception as e:
        analysis["error"] = f"Analysis error: {str(e)}"
    
    return analysis

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
        header = [col.strip().lower() for col in lines[0].split(',')]
        data_rows = len(lines) - 1
        
        # Define required and optional columns for credit risk analysis
        required_columns = ['company_name']  # Start with minimal requirement
        optional_columns = ['annual_revenue', 'credit_score', 'industry', 'risk_level', 'employees', 'debt_to_equity']
        
        # Check for required columns
        missing_required = [col for col in required_columns if col not in header]
        if missing_required:
            return jsonify({
                "error": f"Missing required columns: {missing_required}",
                "required_columns": required_columns,
                "found_columns": header
            }), 400
        
        # Check which optional columns are present
        found_optional = [col for col in optional_columns if col in header]
        
        # Basic data quality checks
        sample_data = []
        issues = []
        
        for i, line in enumerate(lines[1:6]):  # Check first 5 data rows
            try:
                row_data = [cell.strip() for cell in line.split(',')]
                if len(row_data) != len(header):
                    issues.append(f"Row {i+2}: Expected {len(header)} columns, got {len(row_data)}")
                else:
                    sample_data.append(dict(zip(header, row_data)))
            except Exception as e:
                issues.append(f"Row {i+2}: Parsing error - {str(e)}")
        
        # Calculate risk assessment capability
        risk_features = len(found_optional)
        analysis_capability = "Basic" if risk_features < 2 else "Enhanced" if risk_features < 4 else "Advanced"
        
        # Perform basic credit risk analysis
        analysis_results = perform_credit_risk_analysis(header, lines[1:], found_optional)
        
        result = {
            "filename": file.filename,
            "columns": len(header),
            "column_names": header,
            "data_rows": data_rows,
            "total_size": len(content),
            "status": "success",
            "validation": {
                "required_columns_present": True,
                "found_optional_columns": found_optional,
                "analysis_capability": analysis_capability,
                "data_quality_issues": issues
            },
            "sample_data": sample_data[:3],  # Show first 3 rows
            "analysis": analysis_results,
            "message": f"Successfully analyzed {data_rows} rows. Analysis capability: {analysis_capability}"
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