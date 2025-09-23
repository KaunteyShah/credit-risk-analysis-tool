"""
Flask Application for Credit Risk Analysis
Enhanced version with dual-panel UI and filtering - Working Version
"""

import os
import sys
from flask import Flask, render_template, request, jsonify
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
    
    # Global data storage
    app.company_data = None
    app.sic_codes = None
    
    @app.route('/')
    def index():
        """Main dashboard page with enhanced dual-panel layout"""
        return render_template('index_enhanced.html')
    
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
    
    # Load data when app starts
    load_company_data()
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("Starting Enhanced Flask App on http://127.0.0.1:8000")
    app.run(host='0.0.0.0', port=8000, debug=True)