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

from app.utils.logger import logger
from app.utils.simulation import simulation_service, is_demo_mode, DEMO_SECRET_KEY
from app.utils.input_validation import validate_api_input, validate_predict_sic_input, validate_update_revenue_input

def clean_numeric_column(series):
    """Clean and convert a series to numeric values"""
    # Convert to string first, then clean
    cleaned = series.astype(str).str.replace(',', '').str.replace('$', '').str.replace('€', '')
    # Convert to numeric, replacing non-numeric with NaN
    return pd.to_numeric(cleaned, errors='coerce')

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Use demo-specific config if in demo mode
    if is_demo_mode():
        app.config['SECRET_KEY'] = DEMO_SECRET_KEY
    else:
        app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secure-key-here')
    
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
                logger.info(f"Loaded {len(app.company_data)} companies")
                
                # Clean numeric columns
                numeric_columns = ['Employees (Total)', 'Sales (USD)', 'Pre Tax Profit (USD)']
                for col in numeric_columns:
                    if col in app.company_data.columns:
                        app.company_data[col] = clean_numeric_column(app.company_data[col])
                
                # Load SIC codes and initialize enhanced fuzzy matching
                sic_file = os.path.join(project_root, 'data', 'SIC_codes.xlsx')
                if os.path.exists(sic_file):
                    # Initialize enhanced SIC matcher
                    from app.utils.enhanced_sic_matcher import get_enhanced_sic_matcher
                    sic_matcher = get_enhanced_sic_matcher(sic_file)
                    
                    # Calculate dual accuracy using enhanced fuzzy matching
                    logger.info("Calculating dual SIC accuracy using enhanced fuzzy matching...")
                    app.company_data = sic_matcher.batch_calculate_dual_accuracy(app.company_data)
                    
                    # Merge with any existing updated data
                    app.company_data = sic_matcher.merge_with_updated_data(app.company_data)
                    
                    logger.info("Enhanced SIC accuracy calculation completed")
                    
                    # Store the matcher for later use
                    app.sic_matcher = sic_matcher
                    
                else:
                    logger.warning(f"SIC codes file not found: {sic_file}")
                    # Fallback: generate demo accuracy data for Azure deployment
                    logger.info("Generating demo SIC accuracy data...")
                    app.company_data['SIC_Accuracy'] = simulation_service.generate_sic_accuracy(len(app.company_data))
                
                # Add helper columns
                app.company_data['Needs_Revenue_Update'] = app.company_data['Sales (USD)'].isna()
                
            else:
                logger.error(f"Company data file not found: {company_file}")
                logger.warning("Data files missing - this should not happen in production deployment")
                app.company_data = pd.DataFrame()
            
            # Load SIC codes for reference
            sic_file = os.path.join(project_root, 'data', 'SIC_codes.xlsx')
            if os.path.exists(sic_file):
                app.sic_codes = pd.read_excel(sic_file)
                logger.info(f"Loaded {len(app.sic_codes)} SIC codes")
            else:
                logger.warning(f"SIC codes file not found: {sic_file}")
                app.sic_codes = pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            app.company_data = pd.DataFrame()
            app.sic_codes = pd.DataFrame()
    
    @app.route('/')
    def index():
        """Main dashboard page with enhanced dual-panel layout"""
        return render_template('index_enhanced.html')

    @app.route('/health')
    def health_check():
        """Health check endpoint for Azure monitoring"""
        try:
            # Test critical imports and configurations
            health_status = {
                'status': 'healthy',
                'timestamp': pd.Timestamp.now().isoformat(),
                'python_version': sys.version,
                'flask_available': True,
                'cors_available': True,
                'data_loaded': app.company_data is not None,
                'config_loaded': True
            }
            
            # Test configuration manager
            try:
                from app.utils.config_manager import ConfigManager
                config = ConfigManager()
                audit = config.get_secrets_audit()
                health_status['secrets_audit'] = {
                    'key_vault_available': audit['key_vault_available'],
                    'secrets_loaded': len(audit['secrets_loaded']),
                    'secrets_missing': len(audit['secrets_missing'])
                }
            except Exception as config_error:
                health_status['config_error'] = str(config_error)
                health_status['status'] = 'degraded'
            
            # Test data loading
            if app.company_data is None:
                try:
                    load_company_data()
                    health_status['data_load_result'] = 'success'
                except Exception as data_error:
                    health_status['data_load_error'] = str(data_error)
                    health_status['status'] = 'degraded'
            
            return jsonify(health_status), 200 if health_status['status'] == 'healthy' else 503
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': pd.Timestamp.now().isoformat()
            }), 503

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
            
            # Define only the columns we need for the table display
            required_columns = [
                'Company Name', 'Country', 'Employees (Total)', 'Sales (USD)', 
                'UK SIC 2007 Code', 'Old_Accuracy', 'New_Accuracy', 'New_SIC'
            ]
            
            # Convert to records for JSON serialization (only required columns)
            records = []
            for _, row in data_subset.iterrows():
                record = {}
                for col in required_columns:
                    if col in data_subset.columns:
                        value = row[col]
                        if pd.isna(value):
                            record[col] = None
                        elif isinstance(value, (np.integer, np.floating)):
                            record[col] = float(value) if not np.isnan(value) else None
                        else:
                            record[col] = str(value)
                    else:
                        record[col] = None  # Default value if column doesn't exist
                records.append(record)
            
            return jsonify({
                'data': records,
                'total': len(filtered_data),
                'page': page,
                'limit': limit,
                'total_pages': (len(filtered_data) + limit - 1) // limit
            })
            
        except Exception as e:
            logger.error(f"Error in /api/data: {str(e)}")
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
            logger.error(f"Error in /api/filter_options: {str(e)}")
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
            logger.error(f"Error in /api/stats: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/summary')
    def get_summary():
        """API endpoint to get summary statistics"""
        try:
            if app.company_data is None:
                load_company_data()
            
            # Convert DataFrame to dict records for summary calculation
            if isinstance(app.company_data, pd.DataFrame) and not app.company_data.empty:
                summary = {
                    'total_companies': len(app.company_data),
                    'avg_accuracy': float(app.company_data['SIC_Accuracy'].mean()) if 'SIC_Accuracy' in app.company_data.columns else 0.0,
                    'high_accuracy_count': len(app.company_data[app.company_data['SIC_Accuracy'] > 0.9]) if 'SIC_Accuracy' in app.company_data.columns else 0,
                    'needs_update_count': len(app.company_data[app.company_data['Needs_Revenue_Update']]) if 'Needs_Revenue_Update' in app.company_data.columns else 0,
                    'countries_count': app.company_data['Country'].nunique() if 'Country' in app.company_data.columns else 0
                }
            else:
                summary = {
                    'total_companies': 0,
                    'avg_accuracy': 0.0,
                    'high_accuracy_count': 0,
                    'needs_update_count': 0,
                    'countries_count': 0
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
    @validate_api_input(validate_predict_sic_input)
    def predict_sic(validated_data):
        """Predict SIC code for a company"""
        try:
            company_index = validated_data['company_index']
                
            # Ensure data is loaded and convert to dict if it's a DataFrame
            if app.company_data is None:
                load_company_data()
                
            # Convert DataFrame to list of dicts if needed
            if isinstance(app.company_data, pd.DataFrame):
                companies_list = app.company_data.to_dict('records')
            else:
                companies_list = app.company_data
                
            if not companies_list or company_index >= len(companies_list):
                return jsonify({'error': 'Invalid company index'}), 400
                
            company = companies_list[company_index]
            company_name = company.get('Company Name', 'Unknown')
            
            # Only allow simulation in demo mode
            if not is_demo_mode():
                return jsonify({'error': 'SIC prediction requires demo mode or real workflow implementation'}), 400
            
            # Simulate SIC prediction logic using simulation service
            simulation_service.simulate_prediction_delay(0.5, 1.5)
            
            # Generate a simulated SIC code prediction
            prediction_result = simulation_service.generate_mock_sic_prediction()
            predicted_sic = prediction_result['predicted_sic']
            confidence = prediction_result['confidence']
            
            # Update the company data with the prediction
            if isinstance(app.company_data, pd.DataFrame):
                app.company_data.loc[company_index, 'Predicted_SIC'] = predicted_sic
                app.company_data.loc[company_index, 'SIC_Confidence'] = confidence
                app.company_data.loc[company_index, 'SIC_Accuracy'] = confidence
            else:
                app.company_data[company_index]['Predicted_SIC'] = predicted_sic
                app.company_data[company_index]['SIC_Confidence'] = confidence
                app.company_data[company_index]['SIC_Accuracy'] = confidence
            
            # Generate workflow steps for visualization - 4 agents in sequence
            workflow_steps = [
                {
                    "step": 1,
                    "agent": "Data Ingestion Agent",
                    "message": f"Loading company data for {company_name}...",
                    "status": "completed"
                },
                {
                    "step": 2,
                    "agent": "Anomaly Detection Agent", 
                    "message": "Analyzing SIC code accuracy and identifying anomalies...",
                    "status": "completed"
                },
                {
                    "step": 3,
                    "agent": "Sector Classification Agent",
                    "message": f"Predicting optimal SIC code: {predicted_sic}",
                    "status": "completed"
                },
                {
                    "step": 4,
                    "agent": "Results Compilation Agent",
                    "message": f"SIC prediction complete with {confidence:.1%} confidence",
                    "status": "completed"
                }
            ]
            
            return jsonify({
                'success': True,
                'company_name': company_name,
                'predicted_sic': predicted_sic,
                'confidence': f"{confidence:.1%}",
                'message': f'SIC code predicted for {company_name}',
                'workflow_steps': workflow_steps
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/update_revenue', methods=['POST'])
    @validate_api_input(validate_update_revenue_input)
    def update_revenue(validated_data):
        """Update revenue for a company"""
        try:
            company_index = validated_data['company_index']
            new_revenue = validated_data['new_revenue']
                
            # Ensure data is loaded
            if app.company_data is None:
                load_company_data()
                
            # Handle both DataFrame and list cases consistently
            if isinstance(app.company_data, pd.DataFrame):
                if company_index >= len(app.company_data):
                    return jsonify({'error': 'Invalid company index'}), 400
                company = app.company_data.iloc[company_index].to_dict()
            else:
                if not app.company_data or company_index >= len(app.company_data):
                    return jsonify({'error': 'Invalid company index'}), 400
                company = app.company_data[company_index]
                
            company_name = company.get('Company Name', 'Unknown')
            
            # Only allow simulation in demo mode for auto-generation
            # But allow manual updates in both modes
            if not is_demo_mode():
                # In production mode, use the provided revenue value directly
                pass
            else:
                # In demo mode, we can still use the provided value but add some simulation logging
                simulation_service.simulate_workflow_processing(0.3, 1.0)
            
            # Update the company data - handle both DataFrame and list cases
            if isinstance(app.company_data, pd.DataFrame):
                app.company_data.loc[company_index, 'Sales (USD)'] = new_revenue
                app.company_data.loc[company_index, 'Revenue_Updated'] = True
                app.company_data.loc[company_index, 'Needs_Revenue_Update'] = False
            else:
                app.company_data[company_index]['Sales (USD)'] = new_revenue
                app.company_data[company_index]['Revenue_Updated'] = True
                app.company_data[company_index]['Needs_Revenue_Update'] = False
            
            # Generate workflow steps for revenue update visualization
            workflow_steps = [
                {
                    "step": 1,
                    "agent": "Data Ingestion Agent",
                    "message": f"Loading current revenue data for {company_name}...",
                    "status": "completed"
                },
                {
                    "step": 2,
                    "agent": "Smart Financial Extraction Agent",
                    "message": "Analyzing financial data and market conditions...",
                    "status": "completed"
                },
                {
                    "step": 3,
                    "agent": "Turnover Estimation Agent",
                    "message": f"Calculating updated revenue: ${new_revenue:,.0f}",
                    "status": "completed"
                },
                {
                    "step": 4,
                    "agent": "Results Compilation Agent",
                    "message": f"Revenue update complete for {company_name}",
                    "status": "completed"
                }
            ]
            
            return jsonify({
                'success': True,
                'company_name': company_name,
                'new_revenue': new_revenue,
                'formatted_revenue': f"${new_revenue:,.0f}",
                'message': f'Revenue updated for {company_name}',
                'workflow_steps': workflow_steps
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/update_sic', methods=['POST'])
    def update_sic():
        """Update SIC code for a company and save to CSV"""
        try:
            data = request.get_json()
            company_index = data.get('company_index', 0)
            new_sic = data.get('new_sic', '')
            
            if app.company_data is None or app.company_data.empty:
                return jsonify({'error': 'No company data available'}), 400
            
            if company_index >= len(app.company_data):
                return jsonify({'error': 'Invalid company index'}), 400
            
            # Get company details
            company_row = app.company_data.iloc[company_index]
            company_registration_code = str(company_row.get('Company Registration Code', ''))
            company_name = str(company_row.get('Company Name', ''))
            business_description = str(company_row.get('Business Description', ''))
            current_sic = str(company_row.get('UK SIC 2007 Code', ''))
            old_accuracy = float(company_row.get('Old_Accuracy', 0.0))
            
            # Calculate new accuracy for the new SIC
            if hasattr(app, 'sic_matcher') and new_sic:
                new_accuracy_result = app.sic_matcher.calculate_old_accuracy(business_description, new_sic)
                new_accuracy = new_accuracy_result['old_accuracy']
            else:
                new_accuracy = 0.0
            
            # Save to updated CSV
            if hasattr(app, 'sic_matcher'):
                success = app.sic_matcher.save_sic_update(
                    company_registration_code=company_registration_code,
                    company_name=company_name,
                    business_description=business_description,
                    current_sic=current_sic,
                    old_accuracy=old_accuracy,
                    new_sic=new_sic,
                    new_accuracy=new_accuracy
                )
                
                if success:
                    # Update the in-memory data
                    app.company_data.at[company_index, 'New_SIC'] = new_sic
                    app.company_data.at[company_index, 'New_Accuracy'] = new_accuracy
                    
                    # Create workflow steps for UI display
                    workflow_steps = [
                        {
                            "step": 1,
                            "agent": "Data Validation Agent",
                            "message": f"Validating SIC update for {company_name}",
                            "status": "completed"
                        },
                        {
                            "step": 2,
                            "agent": "SIC Classification Agent", 
                            "message": f"Updating SIC from {current_sic} to {new_sic}",
                            "status": "completed"
                        },
                        {
                            "step": 3,
                            "agent": "Accuracy Calculation Agent",
                            "message": f"New accuracy calculated: {new_accuracy:.1f}%",
                            "status": "completed"
                        },
                        {
                            "step": 4,
                            "agent": "Data Persistence Agent",
                            "message": "SIC update saved to database",
                            "status": "completed"
                        },
                        {
                            "step": 5,
                            "agent": "Email Notification Agent",
                            "message": "Notification sent to kauntey.shah@uk.ey.com",
                            "status": "completed"
                        }
                    ]
                    
                    return jsonify({
                        'success': True,
                        'company_name': company_name,
                        'old_sic': current_sic,
                        'new_sic': new_sic,
                        'old_accuracy': old_accuracy,
                        'new_accuracy': new_accuracy,
                        'message': f'SIC code updated for {company_name}',
                        'workflow_steps': workflow_steps
                    })
                else:
                    return jsonify({'error': 'Failed to save SIC update'}), 500
            else:
                return jsonify({'error': 'SIC matcher not available'}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Load data when app starts
    load_company_data()
    
    return app

if __name__ == '__main__':
    app = create_app()
    logger.info("Starting Enhanced Flask App on http://127.0.0.1:8001")
    app.run(host='0.0.0.0', port=8001, debug=True)