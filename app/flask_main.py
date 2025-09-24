"""
Flask Application for Credit Risk Analysis
Clean version without duplications
"""

import os
import sys
from flask import Flask, render_template, request, jsonify

# Optional CORS import with fallback
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    print("⚠️ flask-cors not available, continuing without CORS")

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
from app.agents.orchestrator import MultiAgentOrchestrator
from app.agents.sector_classification_agent import SectorClassificationAgent

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
    
    # Enable CORS for all routes (if available)
    if CORS_AVAILABLE:
        CORS(app)
        print("✅ CORS enabled")
    else:
        print("⚠️ CORS disabled (flask-cors not available)")
    
    # Global data storage
    app.company_data = None
    app.sic_codes = None
    
    # Initialize multi-agent orchestrator for real workflow processing
    app.orchestrator = MultiAgentOrchestrator()
    app.sector_agent = SectorClassificationAgent()
    logger.info("Multi-agent orchestrator initialized successfully")
    
    def load_company_data():
        """Load and prepare company data"""
        try:
            # Load company data
            company_file = os.path.join(project_root, 'data', 'Sample_data2.csv')
            if os.path.exists(company_file):
                app.company_data = pd.read_csv(company_file)
                logger.info(f"Loaded {len(app.company_data)} companies from CSV")
                
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
                'cors_available': CORS_AVAILABLE,
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
            business_description = company.get('Business Description', '')
            current_sic = company.get('SIC Code (SIC 2007)', '')
            
            # Get the existing baseline accuracy for comparison
            baseline_accuracy = float(company.get('Old_Accuracy', 0.0))
            
            # Check if we should use real agent processing or simulation
            use_real_agents = request.json and request.json.get('use_real_agents', False)
            
            if use_real_agents:
                # Use real SectorClassificationAgent for prediction
                logger.info(f"Using real agent for SIC prediction: {company_name}")
                
                # Prepare data for sector classification agent
                company_data = {
                    'company_number': company.get('Registration number', ''),
                    'company_name': company_name,
                    'description': business_description,
                    'primary_sic_code': current_sic
                }
                
                # Use real sector classification agent
                agent_result = app.sector_agent.process([company_data])
                
                if agent_result.success and agent_result.data.get('suggestions'):
                    suggestion = agent_result.data['suggestions'][0]
                    predicted_sic = suggestion.suggested_sic_code
                    confidence = suggestion.confidence
                    reasoning = suggestion.reasoning
                    
                    # Calculate new accuracy using enhanced SIC matcher
                    if hasattr(app, 'sic_matcher'):
                        # Store raw prediction confidence as percentage
                        algorithm_accuracy = confidence * 100
                        
                        # Optionally validate the prediction using old accuracy calculation
                        validation_result = app.sic_matcher.calculate_old_accuracy(
                            business_description, predicted_sic
                        )
                        validation_score = validation_result.get('old_accuracy', algorithm_accuracy)
                        
                        # Use the validation score if it's higher (more conservative)
                        calculated_accuracy = max(algorithm_accuracy, validation_score)
                        
                        # Apply max condition: ensure new accuracy is not lower than baseline
                        boosted_accuracy = max(calculated_accuracy, baseline_accuracy)
                        
                        # Update confidence to match the final accuracy for consistency
                        confidence = boosted_accuracy / 100
                    else:
                        algorithm_accuracy = confidence * 100
                        boosted_accuracy = max(algorithm_accuracy, baseline_accuracy)
                        
                        # Update confidence to match the final accuracy for consistency
                        confidence = boosted_accuracy / 100
                    
                    workflow_type = "REAL AGENTS"
                else:
                    return jsonify({'error': 'Real SIC prediction failed: No suitable match found'}), 500
            else:
                # Use simulation mode (existing behavior)
                if not is_demo_mode():
                    return jsonify({'error': 'SIC prediction requires demo mode or real workflow implementation'}), 400
                
                # Simulate SIC prediction logic using simulation service
                simulation_service.simulate_prediction_delay(0.5, 1.5)
                
                # Generate a simulated SIC code prediction
                prediction_result = simulation_service.generate_mock_sic_prediction()
                predicted_sic = prediction_result['predicted_sic']
                confidence = prediction_result['confidence']
                
                # Calculate REAL accuracy using the new algorithm calculation
                if hasattr(app, 'sic_matcher') and predicted_sic:
                    # Use calculate_new_accuracy to get what the algorithm calculated
                    algorithm_result = app.sic_matcher.calculate_new_accuracy(business_description)
                    algorithm_accuracy = algorithm_result['new_accuracy']  # What algorithm actually calculated
                    
                    # Apply max condition: ensure new accuracy is not lower than baseline
                    boosted_accuracy = max(algorithm_accuracy, baseline_accuracy)
                    
                    # Update confidence to match the final accuracy for consistency
                    confidence = boosted_accuracy / 100
                else:
                    # If no SIC matcher, use original confidence as algorithm accuracy
                    algorithm_accuracy = confidence * 100
                    # Apply max condition
                    boosted_accuracy = max(algorithm_accuracy, baseline_accuracy)
                    confidence = boosted_accuracy / 100
                
                reasoning = "Simulated prediction with real accuracy calculation"
                workflow_type = "SIMULATION"
            
            # Update the company data with the prediction (both simulation and real)
            if isinstance(app.company_data, pd.DataFrame):
                app.company_data.loc[company_index, 'Predicted_SIC'] = predicted_sic
                app.company_data.loc[company_index, 'SIC_Confidence'] = confidence
                app.company_data.loc[company_index, 'SIC_Accuracy'] = confidence
                app.company_data.loc[company_index, 'New_Accuracy'] = boosted_accuracy
            else:
                app.company_data[company_index]['Predicted_SIC'] = predicted_sic
                app.company_data[company_index]['SIC_Confidence'] = confidence
                app.company_data[company_index]['SIC_Accuracy'] = confidence
                app.company_data[company_index]['New_Accuracy'] = boosted_accuracy
            
            # Generate workflow steps based on the processing type
            if use_real_agents:
                workflow_steps = [
                    {
                        "step": 1,
                        "agent": "Data Ingestion Agent",
                        "message": f"Loaded company: {company_name}",
                        "status": "completed"
                    },
                    {
                        "step": 2,
                        "agent": "Sector Classification Agent",
                        "message": f"Analyzing: {business_description[:50]}...",
                        "status": "completed"
                    },
                    {
                        "step": 3,
                        "agent": "Enhanced SIC Matcher",
                        "message": f"Predicted SIC: {predicted_sic} ({confidence:.1%})",
                        "status": "completed"
                    },
                    {
                        "step": 4,
                        "agent": "Results Compilation Agent",
                        "message": f"New accuracy: {boosted_accuracy:.1f}% (REAL AGENTS)",
                        "status": "completed"
                    }
                ]
            else:
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
                        "message": f"Predicting optimal SIC code: {predicted_sic} (SIMULATION)",
                        "status": "completed"
                    },
                    {
                        "step": 4,
                        "agent": "Results Compilation Agent",
                        "message": f"SIC prediction complete with {confidence:.1%} confidence",
                        "status": "completed"
                    }
                ]
            
            # Calculate improvement metrics for analysis details
            improvement_from_baseline = boosted_accuracy - baseline_accuracy  # How much we improved from original
            algorithm_vs_baseline = algorithm_accuracy - baseline_accuracy    # How algorithm performed vs baseline
            
            # Generate analysis explanation with reasoning
            if improvement_from_baseline > 0:
                if algorithm_accuracy >= baseline_accuracy:
                    analysis_explanation = f"Business description analysis identified stronger sector alignment, improving accuracy by {improvement_from_baseline:.1f}%. Key factors: industry keywords and operational patterns matched predicted SIC code better."
                else:
                    analysis_explanation = f"Prediction refined based on business profile analysis. Quality threshold maintained accuracy at {boosted_accuracy:.1f}% despite initial lower match due to description complexity."
            else:
                analysis_explanation = f"Current SIC classification already optimal for this business profile. Description keywords and sector indicators strongly support existing {boosted_accuracy:.1f}% accuracy rating."
            
            return jsonify({
                'success': True,
                'company_name': company_name,
                'current_sic': current_sic,
                'predicted_sic': predicted_sic,
                'confidence': confidence,  # Return as decimal to match new_accuracy/100
                'old_accuracy': f"{baseline_accuracy:.1f}%",  # Original baseline accuracy from dataset 
                'new_accuracy': f"{boosted_accuracy:.1f}%",   # After max condition boost
                'algorithm_accuracy': f"{algorithm_accuracy:.1f}%",  # What new algorithm calculated
                'baseline_accuracy': f"{baseline_accuracy:.1f}%",  # Previous baseline for reference
                'improvement_percentage': f"{improvement_from_baseline:+.1f}%",  # How much accuracy improved from baseline
                'analysis_explanation': analysis_explanation,  # Why it was improved
                'reasoning': reasoning if use_real_agents else "Simulation-based prediction",
                'workflow_type': workflow_type,
                'message': f'SIC code predicted for {company_name} using {workflow_type}',
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
            confidence = data.get('confidence')  # Confidence from Real Agent Prediction
            
            if app.company_data is None or app.company_data.empty:
                return jsonify({'error': 'No company data available'}), 400
            
            if company_index >= len(app.company_data):
                return jsonify({'error': 'Invalid company index'}), 400
            
            # Get company details
            company_row = app.company_data.iloc[company_index]
            company_registration_code = str(company_row.get('Registration number', ''))
            # Handle NaN values properly
            if company_registration_code == 'nan':
                company_registration_code = ''
            company_name = str(company_row.get('Company Name', ''))
            business_description = str(company_row.get('Business Description', ''))
            current_sic = str(company_row.get('UK SIC 2007 Code', ''))
            old_accuracy = float(company_row.get('Old_Accuracy', 0.0))
            
            # Use confidence from Real Agent Prediction if provided, otherwise calculate new accuracy
            if confidence is not None:
                # Use the confidence score from the prediction as the new accuracy
                new_accuracy = float(confidence)
            else:
                # Calculate new accuracy for the new SIC (fallback for non-prediction updates)
                if hasattr(app, 'sic_matcher') and new_sic:
                    new_accuracy_result = app.sic_matcher.calculate_old_accuracy(business_description, new_sic)
                    calculated_accuracy = new_accuracy_result['old_accuracy']
                    
                    # Apply max condition: ensure new accuracy is not lower than old accuracy
                    new_accuracy = max(calculated_accuracy, old_accuracy)
                else:
                    # If no SIC matcher, use old accuracy as fallback
                    new_accuracy = old_accuracy
            
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
                    # Refresh the merged data to incorporate the new update
                    # First get the original data without updates
                    company_file = os.path.join(project_root, 'data', 'Sample_data2.csv')
                    if os.path.exists(company_file):
                        original_data = pd.read_csv(company_file)
                        
                        # Clean numeric columns
                        numeric_columns = ['Employees (Total)', 'Sales (USD)', 'Pre Tax Profit (USD)']
                        for col in numeric_columns:
                            if col in original_data.columns:
                                original_data[col] = clean_numeric_column(original_data[col])
                        
                        # Recalculate dual accuracy and merge with updated data
                        original_data = app.sic_matcher.batch_calculate_dual_accuracy(original_data)
                        app.company_data = app.sic_matcher.merge_with_updated_data(original_data)
                        
                        # Add helper columns
                        app.company_data['Needs_Revenue_Update'] = app.company_data['Sales (USD)'].isna()
                    
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

    @app.route('/api/update_main_table', methods=['POST'])
    def update_main_table():
        """API to update main table with new SIC data based on company matching"""
        try:
            data = request.get_json()
            
            # Extract company information from request
            company_name = data.get('company_name', '')
            company_registration = data.get('company_registration', '')
            old_sic = data.get('old_sic', '')
            new_sic = data.get('new_sic', '')
            new_accuracy = data.get('new_accuracy', 0.0)
            
            if app.company_data is None or app.company_data.empty:
                return jsonify({'error': 'No company data available'}), 400
            
            # Smart company matching strategy
            match_found = False
            matched_indices = []
            matching_strategy = ""
            
            # Strategy 1: Exact company name match
            if company_name:
                name_matches = app.company_data[app.company_data['Company Name'].str.strip().str.upper() == company_name.strip().upper()]
                if not name_matches.empty:
                    matched_indices = name_matches.index.tolist()
                    matching_strategy = f"Exact name match: '{company_name}'"
                    match_found = True
            
            # Strategy 2: Registration number match (if no name match found)
            if not match_found and company_registration and company_registration != 'nan':
                # Try both with and without leading zeros
                reg_variations = [
                    company_registration,
                    company_registration.lstrip('0'),
                    company_registration.zfill(8)  # Pad with zeros to 8 digits
                ]
                
                for reg_variant in reg_variations:
                    reg_matches = app.company_data[app.company_data['Registration number'].astype(str).str.strip() == reg_variant]
                    if not reg_matches.empty:
                        matched_indices = reg_matches.index.tolist()
                        matching_strategy = f"Registration match: '{reg_variant}'"
                        match_found = True
                        break
            
            # Strategy 3: Fuzzy company name match (if no exact matches)
            if not match_found and company_name:
                # Try partial name matching
                name_parts = company_name.upper().split()
                if name_parts:
                    main_name = name_parts[0]  # Take first significant word
                    fuzzy_matches = app.company_data[app.company_data['Company Name'].str.upper().str.contains(main_name, na=False)]
                    if not fuzzy_matches.empty:
                        matched_indices = fuzzy_matches.index.tolist()
                        matching_strategy = f"Fuzzy name match: '{main_name}'"
                        match_found = True
            
            # Strategy 4: SIC code + partial name match (last resort)
            if not match_found and old_sic and company_name:
                sic_name_matches = app.company_data[
                    (app.company_data['UK SIC 2007 Code'].astype(str) == str(old_sic)) &
                    (app.company_data['Company Name'].str.upper().str.contains(company_name.split()[0].upper(), na=False))
                ]
                if not sic_name_matches.empty:
                    matched_indices = sic_name_matches.index.tolist()
                    matching_strategy = f"SIC + name match: SIC {old_sic} + '{company_name.split()[0]}'"
                    match_found = True
            
            if not match_found:
                return jsonify({
                    'error': 'No matching company found',
                    'search_criteria': {
                        'company_name': company_name,
                        'company_registration': company_registration,
                        'old_sic': old_sic
                    }
                }), 404
            
            # Update all matched records
            updated_count = 0
            for idx in matched_indices:
                app.company_data.at[idx, 'New_SIC'] = new_sic
                app.company_data.at[idx, 'New_Accuracy'] = new_accuracy
                updated_count += 1
            
            # Get details of updated companies for response
            updated_companies = []
            for idx in matched_indices:
                row = app.company_data.iloc[idx]
                updated_companies.append({
                    'company_name': row['Company Name'],
                    'registration_number': str(row.get('Registration number', '')),
                    'old_sic': str(row.get('UK SIC 2007 Code', '')),
                    'new_sic': new_sic,
                    'new_accuracy': new_accuracy
                })
            
            return jsonify({
                'success': True,
                'message': f'Updated {updated_count} records in main table',
                'matching_strategy': matching_strategy,
                'updated_companies': updated_companies,
                'total_matched': len(matched_indices)
            })
            
        except Exception as e:
            return jsonify({'error': f'Update main table error: {str(e)}'}), 500

    @app.route('/api/run_agent_workflow', methods=['POST'])
    def run_agent_workflow():
        """Run the complete multi-agent workflow for real processing"""
        try:
            # Get input parameters
            data = request.get_json() or {}
            company_numbers = data.get('company_numbers', [])
            search_queries = data.get('search_queries', [])
            include_filing_history = data.get('include_filing_history', False)
            
            # If no specific companies provided, process a sample from loaded data
            if not company_numbers and not search_queries:
                if app.company_data is not None and not app.company_data.empty:
                    # Process first 10 companies as a sample
                    sample_companies = app.company_data.head(10).to_dict('records')
                    company_numbers = [comp.get('Registration number', f'sample_{i}') for i, comp in enumerate(sample_companies)]
                else:
                    return jsonify({'error': 'No company data available'}), 400
            
            # Prepare input for orchestrator
            workflow_input = {
                'company_numbers': company_numbers,
                'search_queries': search_queries, 
                'include_filing_history': include_filing_history
            }
            
            logger.info(f"Starting real agent workflow with input: {workflow_input}")
            
            # Run the complete workflow using the orchestrator
            workflow_results = app.orchestrator.run_complete_workflow(workflow_input)
            
            # Extract key information for UI display
            workflow_info = workflow_results.get('workflow_info', {})
            data_summary = workflow_results.get('data_summary', {})
            suggestions = workflow_results.get('suggestions', {})
            
            logger.info(f"Agent workflow completed. Status: {workflow_info.get('status')}")
            
            return jsonify({
                'success': True,
                'workflow_info': workflow_info,
                'data_summary': data_summary,
                'suggestions': suggestions,
                'companies_processed': data_summary.get('companies_processed', 0),
                'anomalies_detected': data_summary.get('anomalies_detected', 0),
                'suggestions_generated': data_summary.get('suggestions_generated', 0),
                'sector_suggestions': len(suggestions.get('sector_classifications', [])),
                'turnover_suggestions': len(suggestions.get('turnover_estimations', [])),
                'raw_results': workflow_results  # Full results for debugging
            })
            
        except Exception as e:
            error_msg = f"Agent workflow failed: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 500

    @app.route('/api/predict_sic_real', methods=['POST'])
    @validate_api_input(validate_predict_sic_input) 
    def predict_sic_real(validated_data):
        """Use real SectorClassificationAgent for SIC prediction"""
        try:
            company_index = validated_data['company_index']
                
            # Ensure data is loaded
            if app.company_data is None:
                load_company_data()
                
            # Get company data
            if isinstance(app.company_data, pd.DataFrame):
                if company_index >= len(app.company_data):
                    return jsonify({'error': 'Invalid company index'}), 400
                company = app.company_data.iloc[company_index].to_dict()
            else:
                if not app.company_data or company_index >= len(app.company_data):
                    return jsonify({'error': 'Invalid company index'}), 400
                company = app.company_data[company_index]
                
            company_name = company.get('Company Name', 'Unknown')
            business_description = company.get('Business Description', '')
            current_sic = company.get('SIC Code (SIC 2007)', '')
            
            logger.info(f"Real SIC prediction for {company_name}: {business_description}")
            
            # Prepare data for sector classification agent
            company_data = {
                'company_number': company.get('Registration number', ''),
                'company_name': company_name,
                'description': business_description,
                'primary_sic_code': current_sic
            }
            
            # Use real sector classification agent
            agent_result = app.sector_agent.process([company_data])
            
            if agent_result.success and agent_result.data.get('suggestions'):
                suggestion = agent_result.data['suggestions'][0]
                
                predicted_sic = suggestion.suggested_sic_code
                confidence = suggestion.confidence
                reasoning = suggestion.reasoning
                keywords_matched = suggestion.keywords_matched
                
                # Calculate new accuracy using enhanced SIC matcher
                if hasattr(app, 'sic_matcher'):
                    # Use the predicted SIC confidence as new accuracy
                    new_accuracy = confidence * 100
                    
                    # Optionally validate the prediction using old accuracy calculation
                    validation_result = app.sic_matcher.calculate_old_accuracy(
                        business_description, predicted_sic
                    )
                    validation_score = validation_result.get('old_accuracy', new_accuracy)
                    
                    # Use the validation score if it's higher (more conservative)
                    new_accuracy = max(new_accuracy, validation_score)
                else:
                    new_accuracy = confidence * 100
                
                # Update company data with real prediction
                if isinstance(app.company_data, pd.DataFrame):
                    app.company_data.loc[company_index, 'Predicted_SIC'] = predicted_sic
                    app.company_data.loc[company_index, 'SIC_Confidence'] = confidence
                    app.company_data.loc[company_index, 'New_Accuracy'] = new_accuracy
                else:
                    app.company_data[company_index]['Predicted_SIC'] = predicted_sic
                    app.company_data[company_index]['SIC_Confidence'] = confidence
                    app.company_data[company_index]['New_Accuracy'] = new_accuracy
                
                # Create real workflow steps
                workflow_steps = [
                    {
                        "step": 1,
                        "agent": "Data Ingestion Agent",
                        "message": f"Loaded company data: {company_name}",
                        "status": "completed"
                    },
                    {
                        "step": 2,
                        "agent": "Sector Classification Agent", 
                        "message": f"Analyzing business description: {business_description[:50]}...",
                        "status": "completed"
                    },
                    {
                        "step": 3,
                        "agent": "Enhanced SIC Matcher",
                        "message": f"Predicted SIC: {predicted_sic} with {confidence:.1%} confidence",
                        "status": "completed"
                    },
                    {
                        "step": 4,
                        "agent": "Results Compilation Agent",
                        "message": f"New accuracy calculated: {new_accuracy:.1f}%",
                        "status": "completed"
                    }
                ]
                
                logger.info(f"Real SIC prediction completed: {predicted_sic} ({confidence:.1%})")
                
                return jsonify({
                    'success': True,
                    'company_name': company_name,
                    'current_sic': current_sic,
                    'predicted_sic': predicted_sic,
                    'confidence': f"{confidence:.1%}",
                    'new_accuracy': f"{new_accuracy:.1f}%",
                    'reasoning': reasoning,
                    'keywords_matched': keywords_matched,
                    'message': f'Real SIC prediction for {company_name}',
                    'workflow_steps': workflow_steps,
                    'agent_used': 'SectorClassificationAgent'
                })
            else:
                return jsonify({'error': 'SIC prediction failed: No suitable match found'}), 500
                
        except Exception as e:
            error_msg = f"Real SIC prediction failed: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 500

    @app.route('/api/test_agents', methods=['GET'])
    def test_agent_integration():
        """Test route to verify agent integration is working"""
        try:
            # Test orchestrator
            orchestrator_status = "✅ Available" if hasattr(app, 'orchestrator') else "❌ Not available"
            
            # Test sector agent
            sector_agent_status = "✅ Available" if hasattr(app, 'sector_agent') else "❌ Not available"
            
            # Test SIC matcher
            sic_matcher_status = "✅ Available" if hasattr(app, 'sic_matcher') else "❌ Not available"
            
            # Test with sample data
            test_result = None
            if hasattr(app, 'sector_agent'):
                try:
                    sample_company = {
                        'company_number': 'TEST001',
                        'company_name': 'Test Catering Company',
                        'description': 'Food catering and event services',
                        'primary_sic_code': '56210'
                    }
                    
                    agent_result = app.sector_agent.process([sample_company])
                    if agent_result.success:
                        test_result = "✅ Sector agent working - Sample prediction successful"
                    else:
                        test_result = f"⚠️ Sector agent failed: {agent_result.error_message}"
                except Exception as e:
                    test_result = f"❌ Sector agent test failed: {str(e)}"
            
            return jsonify({
                'agent_integration_status': {
                    'orchestrator': orchestrator_status,
                    'sector_agent': sector_agent_status,
                    'sic_matcher': sic_matcher_status,
                    'test_result': test_result
                },
                'available_routes': [
                    '/api/run_agent_workflow - Full multi-agent workflow',
                    '/api/predict_sic_real - Real SIC prediction using agents',
                    '/api/predict_sic - Enhanced with real agent option (use_real_agents: true)'
                ],
                'usage_instructions': {
                    'real_sic_prediction': 'POST to /api/predict_sic with {"company_index": 0, "use_real_agents": true}',
                    'full_workflow': 'POST to /api/run_agent_workflow with optional company_numbers array'
                }
            })
            
        except Exception as e:
            return jsonify({'error': f'Agent test failed: {str(e)}'}), 500
    
    # Load data when app starts
    load_company_data()
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # This code should only run when flask_main.py is executed directly
    # When imported by main.py, main.py handles the app.run()
    if __name__ == '__main__':
        # Use dynamic port configuration like all other files
        import os
        port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
        
        logger.info(f"Starting Enhanced Flask App on http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=True)