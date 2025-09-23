"""
Flask Application for Credit Risk Analysis
Clean version without duplications
"""

import os
import sys
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import json

# Add the project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def clean_numeric_column(series):
    """Clean and convert a series to numeric values"""
    # Convert to string first, then clean
    cleaned = series.astype(str).str.replace(',', '').str.replace('$', '').str.replace('€', '')
    # Convert to numeric, replacing non-numeric with NaN
    return pd.to_numeric(cleaned, errors='coerce')

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'credit-risk-analysis-demo-key'
    
    # Enable CORS for all routes
    CORS(app)
    
    # Global data storage
    app.company_data = None
    app.sic_codes = None
    
    def load_company_data():
        """Load and prepare company data"""
        try:
            # Load company data
            company_file = os.path.join(project_root, 'data', 'Sample_data2.csv')
            if os.path.exists(company_file):
                app.company_data = pd.read_csv(company_file)
                print(f"Loaded {len(app.company_data)} companies")
                
                # Clean numeric columns
                numeric_columns = ['Employees (Total)', 'Sales (USD)', 'Pre Tax Profit (USD)']
                for col in numeric_columns:
                    if col in app.company_data.columns:
                        app.company_data[col] = clean_numeric_column(app.company_data[col])
                
                # Add SIC accuracy column for demo (simulate prediction confidence)
                np.random.seed(42)  # For reproducible results
                app.company_data['SIC_Accuracy'] = np.random.uniform(0.7, 0.99, len(app.company_data))
                
                # Add helper columns
                app.company_data['Needs_Revenue_Update'] = app.company_data['Sales (USD)'].isna()
                
            else:
                print(f"Company data file not found: {company_file}")
                app.company_data = pd.DataFrame()
            
            # Load SIC codes
            sic_file = os.path.join(project_root, 'data', 'SIC_codes.xlsx')
            if os.path.exists(sic_file):
                app.sic_codes = pd.read_excel(sic_file)
                print(f"Loaded {len(app.sic_codes)} SIC codes")
            else:
                print(f"SIC codes file not found: {sic_file}")
                app.sic_codes = pd.DataFrame()
                
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            app.company_data = pd.DataFrame()
            app.sic_codes = pd.DataFrame()
    
    @app.route('/')
    def index():
        """Main dashboard page with enhanced dual-panel layout"""
        return render_template('index_enhanced.html')

    @app.route('/debug')
    def debug_page():
        """Debug page to test button functionality"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Debug Buttons</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
</head>
<body>
    <div class="container mt-4">
        <h3>Button Test - Are These Visible?</h3>
        
        <div class="alert alert-info">
            <h5>Static Button Test:</h5>
            <button class="btn btn-primary btn-sm me-2">
                <i class="fas fa-robot"></i> Static Predict Button
            </button>
            <button class="btn btn-warning btn-sm">
                <i class="fas fa-sync"></i> Static Update Button
            </button>
        </div>
        
        <table class="table table-striped table-bordered">
            <thead class="table-dark">
                <tr>
                    <th>Company Name</th>
                    <th>Country</th>
                    <th>Employees</th>
                    <th>Revenue (USD)</th>
                    <th>Current SIC</th>
                    <th>SIC Accuracy</th>
                    <th>Predict SIC</th>
                    <th>Update Revenue</th>
                </tr>
            </thead>
            <tbody id="testTable">
                <tr>
                    <td>Test Company 1</td>
                    <td>USA</td>
                    <td>100</td>
                    <td>$1,000,000</td>
                    <td>1234</td>
                    <td>85%</td>
                    <td>
                        <button class="btn btn-primary btn-predict btn-sm" data-company-index="0" title="Predict SIC Code">
                            <i class="fas fa-robot"></i>
                        </button>
                    </td>
                    <td>
                        <button class="btn btn-warning btn-update btn-sm" data-company-index="0" title="Update Revenue">
                            <i class="fas fa-sync"></i>
                        </button>
                    </td>
                </tr>
                <tr>
                    <td>Test Company 2</td>
                    <td>Canada</td>
                    <td>200</td>
                    <td>$2,000,000</td>
                    <td>5678</td>
                    <td>92%</td>
                    <td>
                        <button class="btn btn-primary btn-predict btn-sm" data-company-index="1" title="Predict SIC Code">
                            <i class="fas fa-robot"></i>
                        </button>
                    </td>
                    <td>
                        <button class="btn btn-warning btn-update btn-sm" data-company-index="1" title="Update Revenue">
                            <i class="fas fa-sync"></i>
                        </button>
                    </td>
                </tr>
            </tbody>
        </table>
        
        <div id="results"></div>
    </div>

    <script>
        $(document).ready(function() {
            console.log('Debug page loaded');
            
            // Check if buttons exist
            console.log('Predict buttons found:', $('.btn-predict').length);
            console.log('Update buttons found:', $('.btn-update').length);
            
            $('.btn-predict').click(function() {
                const index = $(this).data('company-index');
                $('#results').append('<div class="alert alert-info">Predict SIC button ' + index + ' clicked!</div>');
                
                fetch('/api/predict_sic', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({company_index: index})
                })
                .then(response => response.json())
                .then(data => {
                    $('#results').append('<div class="alert alert-success">Predict API Response: ' + JSON.stringify(data) + '</div>');
                })
                .catch(error => {
                    $('#results').append('<div class="alert alert-danger">Predict Error: ' + error + '</div>');
                });
            });
            
            $('.btn-update').click(function() {
                const index = $(this).data('company-index');
                $('#results').append('<div class="alert alert-info">Update Revenue button ' + index + ' clicked!</div>');
                
                fetch('/api/update_revenue', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({company_index: index})
                })
                .then(response => response.json())
                .then(data => {
                    $('#results').append('<div class="alert alert-success">Update API Response: ' + JSON.stringify(data) + '</div>');
                })
                .catch(error => {
                    $('#results').append('<div class="alert alert-danger">Update Error: ' + error + '</div>');
                });
            });
        });
    </script>
</body>
</html>
        """

    @app.route('/api/data')
    def get_data():
        """API endpoint to get company data with basic filtering"""
        try:
            if app.company_data is None:
                load_company_data()
            
            # Get query parameters
            limit = request.args.get('limit', 50, type=int)
            page = request.args.get('page', 1, type=int)
            
            # Apply basic filters if provided
            filtered_data = app.company_data.copy()
            
            # Simple country filter
            country = request.args.get('country')
            if country and country != 'all':
                filtered_data = filtered_data[filtered_data['Country'] == country]
            
            # Calculate pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            # Get paginated data
            data_subset = filtered_data.iloc[start_idx:end_idx]
            
            # Convert to records for JSON serialization
            records = []
            for _, row in data_subset.iterrows():
                record = {}
                for col in data_subset.columns:
                    value = row[col]
                    if pd.isna(value):
                        record[col] = None
                    elif isinstance(value, (np.integer, np.floating)):
                        record[col] = float(value) if not np.isnan(value) else None
                    else:
                        record[col] = str(value)
                records.append(record)
            
            return jsonify({
                'data': records,
                'total': len(filtered_data),
                'page': page,
                'limit': limit,
                'total_pages': (len(filtered_data) + limit - 1) // limit
            })
            
        except Exception as e:
            print(f"Error in /api/data: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/filter_options')
    def get_filter_options():
        """Get available filter options"""
        try:
            if app.company_data is None:
                load_company_data()
            
            options = {
                'countries': ['all'] + sorted(app.company_data['Country'].dropna().unique().tolist()),
                'employee_range': {
                    'min': float(app.company_data['Employees (Total)'].min()),
                    'max': float(app.company_data['Employees (Total)'].max())
                },
                'revenue_range': {
                    'min': float(app.company_data['Sales (USD)'].min()),
                    'max': float(app.company_data['Sales (USD)'].max())
                },
                'accuracy_range': {
                    'min': 0.0,
                    'max': 1.0
                }
            }
            
            return jsonify(options)
            
        except Exception as e:
            print(f"Error in /api/filter_options: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/stats')
    def get_stats():
        """Get basic statistics about the data"""
        try:
            if app.company_data is None:
                load_company_data()
            
            stats = {
                'total_companies': len(app.company_data),
                'countries': app.company_data['Country'].nunique() if 'Country' in app.company_data.columns else 0,
                'avg_employees': float(app.company_data['Employees (Total)'].mean()) if 'Employees (Total)' in app.company_data.columns else 0,
                'avg_revenue': float(app.company_data['Sales (USD)'].mean()) if 'Sales (USD)' in app.company_data.columns else 0,
                'high_accuracy_count': len(app.company_data[app.company_data['SIC_Accuracy'] >= 0.9])
            }
            
            return jsonify(stats)
            
        except Exception as e:
            print(f"Error in /api/stats: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/summary')
    def get_summary():
        """API endpoint to get summary statistics"""
        try:
            if app.company_data is None:
                load_company_data()
            
            summary = {
                'total_companies': len(app.company_data),
                'avg_accuracy': float(app.company_data['SIC_Accuracy'].mean()) if len(app.company_data) > 0 and not app.company_data['SIC_Accuracy'].isna().all() else 0.0,
                'high_accuracy_count': len(app.company_data[app.company_data['SIC_Accuracy'] > 0.9]) if len(app.company_data) > 0 else 0,
                'needs_update_count': len(app.company_data[app.company_data['Needs_Revenue_Update']]) if len(app.company_data) > 0 else 0,
                'countries_count': app.company_data['Country'].nunique() if 'Country' in app.company_data.columns and len(app.company_data) > 0 else 0
            }
            
            # Convert any potential NaN values to None for JSON serialization
            for key, value in summary.items():
                if pd.isna(value):
                    summary[key] = None
            
            return jsonify(summary)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/test')
    def test_endpoint():
        """Simple test endpoint"""
        return jsonify({
            'status': 'ok',
            'message': 'API is working',
            'data_loaded': app.company_data is not None,
            'total_companies': len(app.company_data) if app.company_data is not None else 0
        })

    @app.route('/api/agents/status')
    def get_agent_status():
        """Get agent workflow status for simulation"""
        return jsonify({
            'agents': [
                {
                    'name': 'DataAnalyst',
                    'status': 'completed',
                    'progress': 100,
                    'task': 'Company data analysis'
                },
                {
                    'name': 'SICPredictor', 
                    'status': 'running',
                    'progress': 75,
                    'task': 'SIC code predictions'
                },
                {
                    'name': 'ReportGenerator',
                    'status': 'idle',
                    'progress': 0,
                    'task': 'Report generation'
                }
            ],
            'workflow_status': 'active'
        })

    @app.route('/api/predict_sic', methods=['POST'])
    def predict_sic():
        """Predict SIC code for a company"""
        try:
            data = request.get_json()
            company_index = data.get('company_index')
            
            if company_index is None:
                return jsonify({'error': 'Company index is required'}), 400
                
            if not app.company_data or company_index >= len(app.company_data):
                return jsonify({'error': 'Invalid company index'}), 400
                
            company = app.company_data[company_index]
            company_name = company.get('Company Name', 'Unknown')
            
            # Simulate SIC prediction logic
            import random
            import time
            
            # Simulate processing time
            time.sleep(random.uniform(0.5, 1.5))
            
            # Generate a simulated SIC code prediction
            predicted_sic = random.choice(['2834', '3571', '7372', '5045', '6282'])
            confidence = random.uniform(0.75, 0.95)
            
            # Update the company data with the prediction
            app.company_data[company_index]['Predicted_SIC'] = predicted_sic
            app.company_data[company_index]['SIC_Confidence'] = confidence
            app.company_data[company_index]['SIC_Accuracy'] = confidence
            
            return jsonify({
                'success': True,
                'company_name': company_name,
                'predicted_sic': predicted_sic,
                'confidence': f"{confidence:.1%}",
                'message': f'SIC code predicted for {company_name}'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/update_revenue', methods=['POST'])
    def update_revenue():
        """Update revenue for a company"""
        try:
            data = request.get_json()
            company_index = data.get('company_index')
            
            if company_index is None:
                return jsonify({'error': 'Company index is required'}), 400
                
            if not app.company_data or company_index >= len(app.company_data):
                return jsonify({'error': 'Invalid company index'}), 400
                
            company = app.company_data[company_index]
            company_name = company.get('Company Name', 'Unknown')
            
            # Simulate revenue update logic
            import random
            import time
            
            # Simulate processing time
            time.sleep(random.uniform(0.3, 1.0))
            
            # Simulate updated revenue (within 10% of original)
            current_revenue = company.get('Sales (USD)', 0)
            if current_revenue > 0:
                variation = random.uniform(0.9, 1.1)
                new_revenue = current_revenue * variation
            else:
                new_revenue = random.uniform(100000, 50000000)
            
            # Update the company data
            app.company_data[company_index]['Sales (USD)'] = new_revenue
            app.company_data[company_index]['Revenue_Updated'] = True
            app.company_data[company_index]['Needs_Revenue_Update'] = False
            
            return jsonify({
                'success': True,
                'company_name': company_name,
                'new_revenue': new_revenue,
                'formatted_revenue': f"${new_revenue:,.0f}",
                'message': f'Revenue updated for {company_name}'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Load data when app starts
    load_company_data()
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("Starting Enhanced Flask App on http://127.0.0.1:8001")
    app.run(host='0.0.0.0', port=8001, debug=True)