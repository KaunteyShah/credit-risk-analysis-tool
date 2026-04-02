"""
Flask Application for Credit Risk Analysis
Clean version without duplications
"""

import os
import sys
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Optional CORS import with fallback
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    print("⚠️ flask-cors not available, continuing without CORS")

import json
import ssl
import urllib.request
import urllib.error
import sqlite3
import numpy as np

# Add the project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app_modules.utils.logger import logger
from app_modules.utils.simulation import simulation_service, is_demo_mode, DEMO_SECRET_KEY
from app_modules.utils.input_validation import (
    validate_api_input, validate_predict_sic_input, validate_predict_sic_company_id_input, 
    validate_predict_sic_robust_input, validate_update_revenue_input, validate_approve_sic_prediction_input,
    validate_toggle_demo_mode_input, validate_add_company_with_sic_input,
    validate_run_agent_workflow_input
)

# Critical imports that are used throughout
try:
    from app_modules.database.connection import DatabaseConnection
    from app_modules.repositories.implementations.file_based.sqlite_sic_prediction_repository import SQLiteSICPredictionRepository
    from app_modules.repositories.implementations.file_based.sqlite_filing_history_repository import SQLiteFilingHistoryRepository
    DATABASE_CONNECTION_AVAILABLE = True
except ImportError:
    DATABASE_CONNECTION_AVAILABLE = False
    logger.warning("DatabaseConnection not available")

try:
    from app_modules.factory import get_credit_risk_config
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False
    logger.warning("get_credit_risk_config not available")
    
    def get_credit_risk_config():
        """Fallback config function when factory import fails"""
        from app_modules.config.app_config import CreditRiskConfig
        return CreditRiskConfig()

try:
    from app_modules.utils.config_manager import ConfigManager
    CONFIG_MANAGER_CLASS_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_CLASS_AVAILABLE = False
    logger.warning("ConfigManager class not available")

try:
    from app_modules.utils.enhanced_sic_matcher import EnhancedSICMatcher
    ENHANCED_SIC_MATCHER_AVAILABLE = True
except ImportError:
    ENHANCED_SIC_MATCHER_AVAILABLE = False
    logger.warning("EnhancedSICMatcher not available")

# Traditional agent imports removed - pure agentic system only
# MultiAgentOrchestrator and SectorClassificationAgent are no longer used
# All functionality moved to agentic workflow system

try:
    from app_modules.workflows.langgraph_workflow import CreditRiskWorkflow
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False
    logger.warning("LangGraph workflow not available")

try:
    from workflow_manager import WorkflowManager
    WORKFLOW_MANAGER_AVAILABLE = True
except ImportError:
    WORKFLOW_MANAGER_AVAILABLE = False
    logger.warning("Workflow manager not available")

try:
    from app_modules.api.simple_sqlite_routes import simple_sqlite_api
    SQLITE_API_AVAILABLE = True
except ImportError:
    SQLITE_API_AVAILABLE = False
    logger.warning("Simple SQLite API routes not available")


# Import real-time reasoning service
try:
    from app_modules.services.realtime_reasoning_service import realtime_reasoning_service
    REALTIME_REASONING_AVAILABLE = True  # Re-enabled for production use
except ImportError:
    REALTIME_REASONING_AVAILABLE = False
    logger.warning("Real-time reasoning service not available")

# Import frequently used modules (moved from inside functions for performance)
try:
    DATABASE_CONNECTION_AVAILABLE = True
except ImportError:
    DATABASE_CONNECTION_AVAILABLE = False
    logger.warning("Database connection not available")

# ENHANCED_SIC_MATCHER_AVAILABLE is already set above during import

# Import SIC confidence service
try:
    from app_modules.services.sic_confidence_service import SICConfidenceService
    SIC_CONFIDENCE_SERVICE_AVAILABLE = True
except ImportError:
    SIC_CONFIDENCE_SERVICE_AVAILABLE = False
    logger.warning("SIC confidence service not available")

try:
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False
    logger.warning("Config manager not available")

try:
    SQLITE_SIC_PREDICTION_REPOSITORY_AVAILABLE = True
except ImportError:
    SQLITE_SIC_PREDICTION_REPOSITORY_AVAILABLE = False
    logger.warning("SQLite SIC prediction repository not available")

try:
    from app_modules.core.dependency_injection import get_sic_prediction_service, get_container, get_company_service, get_update_revenue_service
    DEPENDENCY_INJECTION_AVAILABLE = True
except ImportError:
    DEPENDENCY_INJECTION_AVAILABLE = False
    logger.warning("Dependency injection not available")

try:
    from app_modules.utils.simulation import set_demo_mode
    DEMO_MODE_AVAILABLE = True
except ImportError:
    DEMO_MODE_AVAILABLE = False
    logger.warning("Demo mode utilities not available")


def _ensure_database_views_exist():
    """Ensure required database views exist, create them if missing"""
    try:
        import sqlite3
        import os
        
        # Get database path from the same configuration system used by the app
        try:
            from app_modules.config.app_config import get_config
            config = get_config()
            db_path = config.database_path
        except Exception:
            # Fallback to environment variable or default
            db_path = os.getenv('DATABASE_PATH', 'data/credit_risk.db')
            if not os.path.exists(db_path):
                # Try alternative paths
                for alt_path in ['credit_risk.db', '/home/site/wwwroot/data/credit_risk.db', '/home/site/wwwroot/credit_risk.db']:
                    if os.path.exists(alt_path):
                        db_path = alt_path
                        break
        
        logger.info(f"Checking database views at: {db_path}")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if company_portal_view exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='company_portal_view'")
            if not cursor.fetchone():
                logger.info("Creating missing company_portal_view...")
                
                # Create the view
                view_sql = """
                CREATE VIEW company_portal_view AS
                SELECT 
                    -- Core company information
                    c.id as company_id,
                    c.company_number,
                    c.company_name,
                    c.status,
                    c.jurisdiction,
                    c.business_description,
                    c.ownership_type,
                    c.entity_type,
                    c.parent_company,
                    
                    -- Financial information
                    cf.sales_gbp,
                    cf.employees_single_site,
                    
                    -- SIC code information (from company_sic_codes table)
                    csc.uk_sic_2007_code,
                    csc.uk_sic_2007_description,
                    
                    -- AI prediction information (latest prediction for each company)
                    sph.predicted_sic_code,
                    sph.confidence_score,
                    sph.existing_sic_confidence,
                    sph.ch_sic_codes,
                    sph.prediction_timestamp,
                    sph.model_version,
                    sph.prediction_method,
                    
                    -- Metadata
                    c.created_at as company_created_at,
                    c.updated_at as company_updated_at
                    
                FROM companies c
                
                -- Left join with financial data (1:1 relationship)
                LEFT JOIN company_financials cf ON c.id = cf.company_id
                
                -- Left join with SIC codes (1:1 relationship, get primary SIC code)
                LEFT JOIN company_sic_codes csc ON c.id = csc.company_id AND csc.is_primary = 1
                
                -- Left join with prediction history (get most recent prediction for each company)
                LEFT JOIN (
                    SELECT 
                        company_id,
                        predicted_sic_code,
                        confidence_score,
                        existing_sic_confidence,
                        ch_sic_codes,
                        prediction_timestamp,
                        model_version,
                        prediction_method,
                        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY prediction_timestamp DESC) as rn
                    FROM sic_prediction_history
                    WHERE company_id IS NOT NULL
                ) sph ON c.id = sph.company_id AND sph.rn = 1
                
                -- Order by company name for consistent results
                ORDER BY c.company_name;
                """
                
                cursor.execute(view_sql)
                conn.commit()
                logger.info("✅ Created company_portal_view successfully")
            else:
                logger.info("✅ company_portal_view already exists")
                
    except Exception as e:
        logger.error(f"Failed to create database views: {e}")
        raise


def clean_numeric_value(value):
    """Clean and convert a value to numeric"""
    if value is None or value == '':
        return None
    # Convert to string first, then clean
    cleaned = str(value).replace(',', '').replace('$', '').replace('€', '')
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def find_data_file(filename):
    """Helper function to find data files in multiple possible locations"""
    possible_paths = [
        os.path.join(project_root, 'data', filename),
        os.path.join(os.path.dirname(__file__), '..', 'data', filename),
        os.path.join(os.getcwd(), 'data', filename),
        f'data/{filename}',
        f'./data/{filename}'
    ]
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    return None

def create_app():
    """Create and configure the Flask application"""
    # Get absolute paths for modular folders
    base_dir = os.path.dirname(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, 'modular_templates')
    static_dir = os.path.join(base_dir, 'modular_static')
    
    app = Flask(__name__, 
                template_folder=template_dir,    # Use modular templates
                static_folder=static_dir)        # Use modular static files
    
    # Custom JSON encoder to handle numpy types
    class NumpyJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.bool_, bool)):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.complexfloating):
                return {'real': float(obj.real), 'imag': float(obj.imag)}
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)
    
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
    
    # Add cache-busting headers to prevent browser cache issues
    @app.after_request
    def add_cache_control_headers(response):
        """Add cache control headers to prevent browser caching issues"""
        if request.endpoint and (request.endpoint.startswith('static') or 
                               request.path.endswith(('.js', '.css', '.html'))):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    # DATABASE-ONLY APPROACH: Remove global data storage
    # All data will be loaded from database on-demand
    # Components will be initialized through dependency injection when needed
    
    logger.info("Initializing database-only Flask app (no CSV dependencies)")

    # Initialize Enhanced SIC Matcher for database-only approach
    try:
        config = get_credit_risk_config()
        setattr(app, 'sic_matcher', EnhancedSICMatcher(config))
        logger.info("✅ Enhanced SIC matcher initialized successfully with database-only approach")
    except Exception as e:
        logger.warning(f"⚠️ Enhanced SIC matcher initialization failed: {e}")
        setattr(app, 'sic_matcher', None)

    # 🤖 Initialize Agentic Services - PURE AGENTIC SYSTEM
    try:
        # Initialize SQLite SIC Prediction Repository
        if DATABASE_CONNECTION_AVAILABLE:
            db_connection = DatabaseConnection()
            sqlite_sic_repository = SQLiteSICPredictionRepository(db_connection)
            setattr(app, 'sqlite_sic_repository', sqlite_sic_repository)
            logger.info("✅ SQLite SIC Prediction Repository initialized")
        else:
            setattr(app, 'sqlite_sic_repository', None)
            logger.warning("⚠️ SQLite SIC Prediction Repository not available")
        
        # 🤖 Initialize Agentic SIC Prediction Service (PRIMARY SYSTEM)
        try:
            from app_modules.agentic.sic_prediction.sic_service import AgenticSICPredictionService
            
            # Prepare services container for agentic workflow
            services_container = {}
            
            # Add required services for agentic workflow
            if hasattr(app, 'sqlite_sic_repository') and app.sqlite_sic_repository:
                services_container['sqlite_sic_repository'] = app.sqlite_sic_repository
            
            if hasattr(app, 'sic_matcher') and app.sic_matcher:
                services_container['enhanced_sic_matcher'] = app.sic_matcher
            
            # Add Companies House client for agentic workflow
            try:
                from app_modules.apis.companies_house_client import CompaniesHouseClient
                companies_house_client = CompaniesHouseClient()
                services_container['companies_house_client'] = companies_house_client
                # Attach to app so agentic_routes.get_agentic_service() can find it
                setattr(app, 'companies_house_client', companies_house_client)
            except Exception as ch_error:
                logger.warning(f"Companies House client not available for agentic workflow: {ch_error}")
                services_container['companies_house_client'] = None
                setattr(app, 'companies_house_client', None)
            
            # Initialize agentic service as PRIMARY system
            agentic_sic_service = AgenticSICPredictionService(
                services_container=services_container,
                config={
                    'enable_langgraph_workflow': True,
                    'enable_companies_house_integration': True,
                    'enable_enhanced_reasoning': True,
                    'enable_multi_agent_coordination': True,
                    'primary_system_mode': True  # NO FALLBACKS
                }
            )
            setattr(app, 'agentic_sic_service', agentic_sic_service)
            logger.info("🤖 Agentic SIC Prediction Service initialized as PRIMARY system!")
            logger.info("   � Pure agentic workflow - no traditional fallbacks")
            logger.info("   🤖 5-agent coordination system active")
            logger.info("   ✨ Advanced AI prediction ready")
            
        except ImportError as agentic_import_error:
            setattr(app, 'agentic_sic_service', None)
            logger.error(f"❌ Agentic SIC service import failed: {agentic_import_error}")
            logger.error("⚠️ SIC prediction will not be available")
        except Exception as agentic_error:
            setattr(app, 'agentic_sic_service', None)
            logger.error(f"❌ Agentic SIC service initialization failed: {agentic_error}")
            logger.error("⚠️ SIC prediction will not be available")
    
    except Exception as e:
        logger.error(f"❌ Service initialization error: {e}")
        logger.error("⚠️ Application will continue with limited functionality")

    # Initialize required database views
    try:
        _ensure_database_views_exist()
        logger.info("✅ Database views verified/created successfully")
    except Exception as e:
        logger.error(f"⚠️ Database view creation failed: {e}")

    # Initialize SQLite Browser Management System (dual-mode: local vs deployed)
    is_azure_webapp = os.getenv('WEBSITE_SITE_NAME') is not None
    is_local_dev = not is_azure_webapp and (
        os.getenv('FLASK_ENV') == 'development' or 
        os.getenv('ENVIRONMENT') == 'local' or
        'localhost' in os.getenv('HTTP_HOST', '') or
        not os.getenv('AZURE_SUBSCRIPTION_ID')
    )
    
    try:
        from app_modules.utils.sqlite_browser_manager import initialize_sqlite_browser_system, get_sqlite_browser_manager
        sqlite_config = {
            'database_path': config.database_path if 'config' in locals() else 'data/credit_risk.db',
            'mode': 'local' if is_local_dev else 'azure'  # Set mode based on environment
        }
        result = initialize_sqlite_browser_system(sqlite_config)
        if result.get('success'):
            mode_desc = "Local SQLite Browser" if is_local_dev else "Azure Container SQLite Browser"
            logger.info(f"✅ {mode_desc} system initialized: {result.get('action', 'ready')}")
            # Attach the manager to the Flask app
            app.sqlite_browser_manager = get_sqlite_browser_manager(sqlite_config)
        else:
            logger.warning(f"⚠️ SQLite Browser system initialization issue: {result.get('error', 'unknown')}")
            app.sqlite_browser_manager = None
    except Exception as e:
        logger.error(f"⚠️ SQLite Browser system initialization failed: {e}")
        app.sqlite_browser_manager = None

    # Register Simple SQLite API routes
    if SQLITE_API_AVAILABLE:
        try:
            app.register_blueprint(simple_sqlite_api)
            logger.info("Simple SQLite API routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register Simple SQLite API routes: {e}")
    else:
        logger.warning("Simple SQLite API routes not available")

    # Register Q&A API routes
    try:
        from app_modules.api.qa_api import qa_api
        app.register_blueprint(qa_api)
        logger.info("✅ Q&A API routes registered successfully")
        logger.info("🔍 Available Q&A endpoints:")
        logger.info("   POST /api/qa/ask - Ask questions about documents")
        logger.info("   GET /api/qa/health - Q&A system health check") 
        logger.info("   GET /api/qa/stats - Q&A system statistics")
    except Exception as e:
        logger.error(f"❌ Failed to register Q&A API routes: {e}")

    # Register Vectorization Status API routes
    try:
        from app_modules.api.vectorization_api import vectorization_api
        app.register_blueprint(vectorization_api)
        logger.info("✅ Vectorization API routes registered successfully")
        logger.info("🔍 Available Vectorization endpoints:")
        logger.info("   GET /api/vectorization/check/<company_number> - Check vectorization status")
        logger.info("   GET /api/vectorization/stats - System vectorization statistics") 
        logger.info("   GET /api/vectorization/health - Vectorization API health check")
    except Exception as e:
        logger.error(f"❌ Failed to register Vectorization API routes: {e}")

    # Register Agentic routes (SIC prediction + revenue extraction)
    try:
        from app_modules.agentic.agentic_routes import register_agentic_routes
        register_agentic_routes(app)
        logger.info("✅ Agentic routes registered successfully")
    except Exception as e:
        logger.error(f"❌ Failed to register agentic routes: {e}")

    # Register Cost-Effective Q&A API routes
    try:
        from app_modules.services.qa.cost_effective_qa_api import cost_effective_qa_bp
        app.register_blueprint(cost_effective_qa_bp)
        logger.info("💰 Cost-Effective Q&A API routes registered successfully")
        logger.info("🔍 Available Cost-Effective Q&A endpoints:")
        logger.info("   POST /api/qa/free - Generate FREE Q&A responses")
        logger.info("   GET /api/qa/cost-comparison - Compare costs vs Azure OpenAI")
        logger.info("   GET /api/qa/cost-status - Check cost configuration")
        logger.info("   GET /api/qa/install-guide - Installation guide for FREE LLM")
        logger.info("   GET /api/qa/health - Cost-effective Q&A health check")
        logger.info("💡 BENEFIT: Zero API costs with same embedding model consistency!")
    except Exception as e:
        logger.error(f"❌ Failed to register Cost-Effective Q&A API routes: {e}")
        logger.warning("💡 To enable FREE Q&A: pip install transformers torch")

    def verify_database_connection():
        """Verify database connection and tables exist"""
        try:
            db_connection = DatabaseConnection()
            
            with db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if companies table exists and has data
                cursor.execute("SELECT COUNT(*) FROM companies LIMIT 1")
                company_count = cursor.fetchone()[0]
                
                # Check if SIC codes table exists
                cursor.execute("SELECT COUNT(*) FROM sic_codes LIMIT 1") 
                sic_count = cursor.fetchone()[0]
                
                logger.info(f"Database verified: {company_count} companies, {sic_count} SIC codes")
                return True
                
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            return False
    
    @app.route('/')
    def index():
        """Main dashboard page with modular layout"""
        return render_template('dashboard.html')

    @app.route('/dashboard')
    def dashboard():
        """Dashboard page - same as index"""
        return render_template('dashboard.html')

    @app.route('/modular-dashboard')
    def modular_dashboard():
        """Modular dashboard page with SIC prediction workflow"""
        return render_template('dashboard.html')

    @app.route('/workflow')
    def workflow_agents():
        """Agent orchestration workflow page"""
        return render_template('existing_workflows.html')

    @app.route('/architecture')
    def architecture_visualization():
        """System architecture visualization page"""
        return render_template('workflow_visualization.html')

    @app.route('/filters')
    def filter_demo():
        """Interactive filtering demo page"""
        return render_template('filter_demo.html')

    @app.route('/advanced-filters')
    def advanced_filters():
        """Advanced filter page with collapsible field selector"""
        return render_template('advanced_filters.html')

    @app.route('/database-viewer')
    def database_viewer():
        """Web-based SQLite database viewer"""
        return render_template('database_viewer.html')

    @app.route('/health')
    def health_check():
        """Health check endpoint for Azure monitoring"""
        try:
            # Test critical imports and configurations
            
            # Test database connectivity
            try:
                db = DatabaseConnection()
                company_results = db.execute_query("SELECT COUNT(*) FROM companies")
                sic_results = db.execute_query("SELECT COUNT(*) FROM sic_codes")
                company_count = company_results[0][0] if company_results else 0
                sic_count = sic_results[0][0] if sic_results else 0
                data_available = company_count > 0 and sic_count > 0
            except Exception as db_error:
                data_available = False
                company_count = 0
                sic_count = 0
            
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'python_version': sys.version,
                'flask_available': True,
                'cors_available': CORS_AVAILABLE,
                'database_available': data_available,
                'companies_count': company_count,
                'sic_codes_count': sic_count,
                'config_loaded': True
            }
            
            # Test configuration manager
            try:
                if CONFIG_MANAGER_CLASS_AVAILABLE:
                    config = ConfigManager()
                    audit = config.get_secrets_audit()
                    health_status['secrets_audit'] = {
                        'key_vault_available': audit['key_vault_available'],
                        'secrets_loaded': len(audit['secrets_loaded']),
                        'secrets_missing': len(audit['secrets_missing'])
                    }
                else:
                    # Use centralized configuration as fallback
                    config = get_credit_risk_config()
                    health_status['secrets_audit'] = {
                        'key_vault_available': True,  # Assume available since config works
                        'secrets_loaded': 2,  # Basic API keys
                        'secrets_missing': 0
                    }
            except Exception as config_error:
                health_status['config_error'] = str(config_error)
                health_status['status'] = 'degraded'
            
            # Test database connectivity (no CSV data loading needed)
            if not data_available:
                try:
                    # Try to verify database again
                    test_results = db.execute_query("SELECT COUNT(*) FROM companies LIMIT 1")
                    health_status['data_load_result'] = 'database_verified'
                except Exception as data_error:
                    health_status['data_load_error'] = str(data_error)
                    health_status['status'] = 'degraded'
            
            return jsonify(health_status), 200 if health_status['status'] == 'healthy' else 503
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 503

    @app.route('/stats')
    def component_stats():
        """Component statistics endpoint for modular architecture"""
        try:
            db = DatabaseConnection()
            
            # Get database counts
            company_results = db.execute_query("SELECT COUNT(*) FROM companies")
            sic_results = db.execute_query("SELECT COUNT(*) FROM sic_codes")
            prediction_results = db.execute_query("SELECT COUNT(*) FROM sic_prediction_history")
            
            stats = {
                'status': 'active',
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'database': {
                        'companies': company_results[0][0] if company_results else 0,
                        'sic_codes': sic_results[0][0] if sic_results else 0,
                        'predictions': prediction_results[0][0] if prediction_results else 0
                    },
                    'architecture': {
                        'modular_core': True,
                        'dashboard': True,
                        'workflows': True
                    }
                }
            }
            
            return jsonify(stats), 200
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/api/modular/health')
    def modular_health_check():
        """Modular architecture health check endpoint"""
        try:
            db = DatabaseConnection()
            
            # Get database counts
            company_results = db.execute_query("SELECT COUNT(*) FROM companies")
            sic_results = db.execute_query("SELECT COUNT(*) FROM sic_codes")
            
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'database': True,
                    'modular_core': True,
                    'dashboard': True
                },
                'data': {
                    'companies': company_results[0][0] if company_results else 0,
                    'sic_codes': sic_results[0][0] if sic_results else 0
                }
            }
            
            return jsonify(health_status), 200
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/api/modular/stats')
    def modular_component_stats():
        """Modular architecture component statistics endpoint"""
        try:
            db = DatabaseConnection()
            
            # Get database counts
            company_results = db.execute_query("SELECT COUNT(*) FROM companies")
            sic_results = db.execute_query("SELECT COUNT(*) FROM sic_codes")
            prediction_results = db.execute_query("SELECT COUNT(*) FROM sic_prediction_history")
            
            stats = {
                'status': 'active',
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'database': {
                        'companies': company_results[0][0] if company_results else 0,
                        'sic_codes': sic_results[0][0] if sic_results else 0,
                        'predictions': prediction_results[0][0] if prediction_results else 0
                    },
                    'architecture': {
                        'modular_core': True,
                        'dashboard': True,
                        'workflows': True
                    }
                }
            }
            
            return jsonify(stats), 200
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/api/debug/imports')
    def debug_imports():
        """Debug endpoint to test imports"""
        import_results = {}
        
        # Test rapidfuzz
        try:
            import rapidfuzz
            import_results['rapidfuzz'] = f"SUCCESS - version: {rapidfuzz.__version__}"
        except ImportError as e:
            import_results['rapidfuzz'] = f"FAILED - {str(e)}"
        
        # Test portalocker
        try:
            import portalocker
            import_results['portalocker'] = f"SUCCESS - version: {portalocker.__version__}"
        except ImportError as e:
            import_results['portalocker'] = f"FAILED - {str(e)}"
        
        # Test AtomicCSVWriter
        try:
            from app_modules.utils.atomic_csv import AtomicCSVWriter
            import_results['AtomicCSVWriter'] = "SUCCESS"
        except ImportError as e:
            import_results['AtomicCSVWriter'] = f"FAILED - {str(e)}"
        
        # Test EnhancedSICMatcher
        try:
            from app_modules.utils.enhanced_sic_matcher import EnhancedSICMatcher
            import_results['EnhancedSICMatcher'] = "SUCCESS"
        except ImportError as e:
            import_results['EnhancedSICMatcher'] = f"FAILED - {str(e)}"
        
        # Test AI reasoning service
        ai_service_status = {}
        try:
            ai_service_status['realtime_reasoning_available'] = REALTIME_REASONING_AVAILABLE
            if REALTIME_REASONING_AVAILABLE:
                # Test OpenAI client initialization
                try:
                    from app_modules.utils.config_manager import ConfigManager
                    config = ConfigManager()
                    api_key = config.get('openai.api_key')
                    if api_key and api_key != 'dummy-key-for-local-testing' and len(api_key) > 20:
                        ai_service_status['openai_api_key'] = f"AVAILABLE - length: {len(api_key)}"
                    else:
                        ai_service_status['openai_api_key'] = f"INVALID - {api_key[:10] if api_key else 'None'}..."
                except Exception as e:
                    ai_service_status['openai_api_key'] = f"ERROR - {str(e)}"
                
                # Test reasoning service initialization
                if 'realtime_reasoning_service' in globals():
                    ai_service_status['service_initialized'] = "YES"
                    try:
                        # Test if client is available
                        if hasattr(realtime_reasoning_service, 'client') and realtime_reasoning_service.client:
                            ai_service_status['openai_client'] = "INITIALIZED"
                        else:
                            ai_service_status['openai_client'] = "NOT INITIALIZED"
                    except Exception as e:
                        ai_service_status['openai_client'] = f"ERROR - {str(e)}"
                else:
                    ai_service_status['service_initialized'] = "NO"
        except Exception as e:
            ai_service_status['error'] = str(e)
        
        return jsonify({
            'import_results': import_results,
            'enhanced_matcher_available': ENHANCED_SIC_MATCHER_AVAILABLE,
            'ai_service_status': ai_service_status
        })

    @app.route('/api/data')
    def get_data():
        """API endpoint to get company data with basic filtering"""
        try:
            db = DatabaseConnection()
            
            # Get query parameters
            limit = request.args.get('limit', 50, type=int)
            page = request.args.get('page', 1, type=int)
            
            # Calculate pagination offset
            offset = (page - 1) * limit
            
            # Use company_portal_view for consistent data access (updated to remove old_accuracy dependency)
            country = request.args.get('country')
            
            where_conditions = []
            params = []
            
            # Country filter (using jurisdiction field from company_portal_view)
            if country and country != 'all':
                where_conditions.append("jurisdiction = ?")
                params.append(country)
                
            # Build WHERE clause
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Get total count from company_portal_view
            count_query = f"SELECT COUNT(*) as total FROM company_portal_view {where_clause}"
            total_result = db.execute_query(count_query, params)
            total_count = total_result[0]['total'] if total_result else 0
            
            # Get data from company_portal_view with proper field mapping
            data_query = f"""
                SELECT 
                    company_name as "Company Name",
                    jurisdiction as "Country",
                    employees_single_site as "Employees (Total)",
                    sales_gbp as "Sales (GBP)",
                    uk_sic_2007_code as "UK SIC 2007 Code",
                    existing_sic_confidence as "Old_Accuracy",
                    confidence_score as "New_Accuracy",
                    predicted_sic_code as "New_SIC"
                FROM company_portal_view
                {where_clause}
                ORDER BY company_name
                LIMIT ? OFFSET ?
            """
            
            records = db.execute_query(data_query, params + [limit, offset])
            
            # Clean up records for JSON serialization
            cleaned_records = []
            for record in records:
                # sqlite3.Row objects can be accessed by index and key
                cleaned_record = {}
                for key in record.keys():
                    value = record[key]
                    if value is None:
                        cleaned_record[key] = None
                    elif isinstance(value, (int, float)):
                        import math
                        if isinstance(value, float) and math.isnan(value):
                            cleaned_record[key] = None
                        else:
                            cleaned_record[key] = float(value)
                    else:
                        cleaned_record[key] = str(value)
                cleaned_records.append(cleaned_record)
            
            return jsonify({
                'data': cleaned_records,
                'total': total_count,
                'page': page,
                'limit': limit,
                'total_pages': (total_count + limit - 1) // limit
            })
            
        except Exception as e:
            logger.error(f"Error in /api/data: {str(e)}")
            return jsonify({'error': str(e)}), 500

    # [DEAD ROUTE] /api/filter_options — underscore alias, no consumer. Frontend uses /api/modular/filter-options (hyphen). Safe to remove.
    @app.route('/api/filter_options')
    def get_filter_options():
        """Get available filter options"""
        try:
            db = DatabaseConnection()
            
            # Get distinct countries
            countries_query = "SELECT DISTINCT country FROM companies WHERE country IS NOT NULL ORDER BY country"
            countries_result = db.execute_query(countries_query)
            countries_list = ['all'] + [row['country'] for row in countries_result if row['country']]
            
            # Get employee range from company_financials table
            emp_range_query = """
                SELECT 
                    MIN(employees_total) as min_emp,
                    MAX(employees_total) as max_emp
                FROM company_financials 
                WHERE employees_total IS NOT NULL AND employees_total > 0
            """
            emp_result = db.execute_query(emp_range_query)
            emp_min = float(emp_result[0]['min_emp']) if emp_result and emp_result[0]['min_emp'] else 0.0
            emp_max = float(emp_result[0]['max_emp']) if emp_result and emp_result[0]['max_emp'] else 100000.0
            
            # Get revenue range from company_financials table
            revenue_range_query = """
                SELECT 
                    MIN(sales_gbp) as min_sales,
                    MAX(sales_gbp) as max_sales
                FROM company_financials 
                WHERE sales_gbp IS NOT NULL AND sales_gbp > 0
            """
            revenue_result = db.execute_query(revenue_range_query)
            sales_min = float(revenue_result[0]['min_sales']) if revenue_result and revenue_result[0]['min_sales'] else 0.0
            sales_max = float(revenue_result[0]['max_sales']) if revenue_result and revenue_result[0]['max_sales'] else 1000000000.0
            
            options = {
                'countries': countries_list,
                'employee_range': {'min': emp_min, 'max': emp_max},
                'revenue_range': {'min': sales_min, 'max': sales_max},
                'accuracy_range': {'min': 0.0, 'max': 1.0}
            }
            
            return jsonify(options)
            
        except Exception as e:
            logger.error(f"Error in /api/filter_options: {str(e)}")
            # Return safe defaults on any error
            return jsonify({
                'countries': ['all'],
                'employee_range': {'min': 0.0, 'max': 100000.0},
                'revenue_range': {'min': 0.0, 'max': 1000000000.0},
                'accuracy_range': {'min': 0.0, 'max': 1.0},
                'error': 'Using default values due to data loading error'
            }), 200  # Return 200, not 500, with defaults
    
    @app.route('/api/modular/filter-options')
    def modular_filter_options():
        """Get filter options for advanced filters"""
        try:
            import sqlite3
            import os
            
            db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'credit_risk.db')
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Get unique jurisdictions/countries
                cursor.execute("SELECT DISTINCT jurisdiction FROM companies WHERE jurisdiction IS NOT NULL ORDER BY jurisdiction")
                countries = [row[0] for row in cursor.fetchall()]
                
                # Get status options
                cursor.execute("SELECT DISTINCT status FROM companies WHERE status IS NOT NULL ORDER BY status")
                statuses = [row[0] for row in cursor.fetchall()]
                
                # Get company types
                cursor.execute("SELECT DISTINCT company_type FROM companies WHERE company_type IS NOT NULL ORDER BY company_type")
                company_types = [row[0] for row in cursor.fetchall()]
                
                # Get unique SIC codes for dashboard filter dropdown
                cursor.execute("""
                    SELECT DISTINCT csc.uk_sic_2007_code
                    FROM company_sic_codes csc
                    WHERE csc.uk_sic_2007_code IS NOT NULL AND csc.uk_sic_2007_code != ''
                    ORDER BY csc.uk_sic_2007_code
                """)
                sic_codes = [row[0] for row in cursor.fetchall()]

                return jsonify({
                    'countries': countries[:50],  # Limit to top 50
                    'statuses': statuses,
                    'company_types': company_types[:20],  # Limit to top 20
                    'sic_codes': sic_codes[:50],   # Top 50 SIC codes for filter dropdown
                    'count': {
                        'countries': len(countries),
                        'sic_codes': len(sic_codes)
                    }
                })
                
        except Exception as e:
            logger.error(f"Error in /api/modular/filter-options: {str(e)}")
            return jsonify({
                'countries': ['United Kingdom', 'United States', 'Canada'],
                'statuses': ['Active', 'Dissolved', 'Liquidation'],
                'company_types': ['Private Limited Company', 'Public Limited Company'],
                'error': 'Using default values due to database error'
            }), 200

    @app.route('/api/stats')
    def get_stats():
        """Get basic statistics about the data"""
        try:
            db = DatabaseConnection()
            
            # Get total companies count
            total_query = "SELECT COUNT(*) as total FROM companies"
            total_result = db.execute_query(total_query)
            total_companies = total_result[0]['total'] if total_result else 0
            
            # Get unique countries count
            countries_query = "SELECT COUNT(DISTINCT country) as count FROM companies WHERE country IS NOT NULL"
            countries_result = db.execute_query(countries_query)
            countries_count = countries_result[0]['count'] if countries_result else 0
            
            # Get average employees from company_financials table
            avg_emp_query = "SELECT AVG(employees_total) as avg_emp FROM company_financials WHERE employees_total IS NOT NULL AND employees_total > 0"
            avg_emp_result = db.execute_query(avg_emp_query)
            avg_employees = float(avg_emp_result[0]['avg_emp']) if avg_emp_result and avg_emp_result[0]['avg_emp'] else 0.0
            
            # Get average revenue from company_financials table
            avg_rev_query = "SELECT AVG(sales_gbp) as avg_rev FROM company_financials WHERE sales_gbp IS NOT NULL AND sales_gbp > 0"
            avg_rev_result = db.execute_query(avg_rev_query)
            avg_revenue = float(avg_rev_result[0]['avg_rev']) if avg_rev_result and avg_rev_result[0]['avg_rev'] else 0.0
            
            # Get high accuracy count from company_portal_view (using existing_sic_confidence)
            high_acc_query = "SELECT COUNT(*) as count FROM company_portal_view WHERE existing_sic_confidence >= 90"
            high_acc_result = db.execute_query(high_acc_query)
            high_accuracy_count = high_acc_result[0]['count'] if high_acc_result else 0
            
            stats = {
                'total_companies': total_companies,
                'countries': countries_count,
                'avg_employees': avg_employees,
                'avg_revenue': avg_revenue,
                'high_accuracy_count': high_accuracy_count
            }
            
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Error in /api/stats: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/summary')
    def get_summary():
        """API endpoint to get summary statistics"""
        try:
            db = DatabaseConnection()
            
            # Get total companies count
            total_query = "SELECT COUNT(*) as total FROM companies"
            total_result = db.execute_query(total_query)
            total_companies = total_result[0]['total'] if total_result else 0
            
            # Get average accuracy from company_portal_view (using existing_sic_confidence)
            avg_acc_query = "SELECT AVG(existing_sic_confidence) as avg_acc FROM company_portal_view WHERE existing_sic_confidence IS NOT NULL"
            avg_result = db.execute_query(avg_acc_query)
            avg_accuracy = float(avg_result[0]['avg_acc']) if avg_result and avg_result[0]['avg_acc'] else 0.0
            
            # Get high accuracy count (> 90) using existing_sic_confidence
            high_acc_query = "SELECT COUNT(*) as count FROM company_portal_view WHERE existing_sic_confidence > 90"
            high_acc_result = db.execute_query(high_acc_query)
            high_accuracy_count = high_acc_result[0]['count'] if high_acc_result else 0
            
            # Get needs update count (this field might not exist in database)
            needs_update_query = "SELECT COUNT(*) as count FROM companies WHERE needs_revenue_update = 1"
            try:
                needs_update_result = db.execute_query(needs_update_query)
                needs_update_count = needs_update_result[0]['count'] if needs_update_result else 0
            except:
                needs_update_count = 0  # Column might not exist
            
            # Get unique countries count
            countries_query = "SELECT COUNT(DISTINCT country) as count FROM companies WHERE country IS NOT NULL"
            countries_result = db.execute_query(countries_query)
            countries_count = countries_result[0]['count'] if countries_result else 0
            
            summary = {
                'total_companies': total_companies,
                'avg_accuracy': avg_accuracy,
                'high_accuracy_count': high_accuracy_count,
                'needs_update_count': needs_update_count,
                'countries_count': countries_count
            }
            
            return jsonify(summary)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/toggle-demo-mode', methods=['POST'])
    @validate_api_input(validate_toggle_demo_mode_input)
    def toggle_demo_mode(validated_data):
        """Toggle demo mode on/off"""
        try:
            demo_mode = validated_data['demo_mode']
            
            # Import the simulation functions
            
            # Set the new demo mode
            set_demo_mode(demo_mode)
            
            return jsonify({
                'success': True,
                'demo_mode': is_demo_mode(),
                'message': f'Demo mode {"enabled" if is_demo_mode() else "disabled"}'
            })
        except Exception as e:
            logger.error(f"Error toggling demo mode: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/demo-mode-status')
    def demo_mode_status():
        """Get current demo mode status"""
        try:
            return jsonify({
                'demo_mode': is_demo_mode(),
                'mode_description': 'Demo Mode' if is_demo_mode() else 'Real Fuzzy Matching'
            })
        except Exception as e:
            logger.error(f"Error getting demo mode status: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/companies')
    def get_companies():
        """
        API endpoint to get filtered company data - MIGRATED TO MODULAR ARCHITECTURE
        
        This endpoint now uses:
        - CompanyService for business logic
        - CompanyRepository for data access
        - Dependency injection for component management
        
        MAINTAINS EXACT SAME API COMPATIBILITY:
        - Same URL: /api/companies
        - Same parameters: page, limit, country, search
        - Same response format: {data: [], total: int, page: int, limit: int, total_pages: int}
        - Same filtering logic: country filter, search filter, pagination
        """
        try:
            # Get query parameters (exact same as before migration)
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 50, type=int)
            country = request.args.get('country', 'all')
            search = request.args.get('search', '')
            
            # FORCE DATABASE-ONLY APPROACH - Use database directly for company data with proper confidence calculation
            logger.info(f"Loading companies from database - page={page}, limit={limit}, country={country}, search='{search}'")
            
            # Connect to database using configuration
            import sqlite3
            config = get_credit_risk_config()
            conn = config.get_database_connection()
            cursor = conn.cursor()
            
            # Build WHERE clause for filters
            where_conditions = []
            params = []
            
            # Country filter (using jurisdiction field)
            if country and country != 'all':
                where_conditions.append("jurisdiction = ?")
                params.append(country)
            
            # Search filter (company name)
            if search:
                where_conditions.append("company_name LIKE ?")
                params.append(f"%{search}%")
            
            # Build WHERE clause
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM company_portal_view {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Calculate pagination
            offset = (page - 1) * limit
            
            # Get paginated data from database
            data_query = f"""
                SELECT 
                    company_name,
                    jurisdiction,
                    employees_single_site,
                    sales_gbp,
                    uk_sic_2007_code,
                    existing_sic_confidence,
                    confidence_score,
                    ch_sic_codes,
                    predicted_sic_code,
                    company_id,
                    unique_id,
                    company_number
                FROM company_portal_view 
                {where_clause}
                ORDER BY company_name
                LIMIT ? OFFSET ?
            """
            
            cursor.execute(data_query, params + [limit, offset])
            rows = cursor.fetchall()
            
            # Convert to JSON-compatible format with proper field mapping for UI compatibility
            records = []
            for row in rows:
                record = {
                    'Company Name': row[0] or '',
                    'company_name': row[0] or '',  # Add both formats for compatibility
                    'Country': row[1] or '',  
                    'Employees (Total)': int(row[2]) if row[2] is not None else None,
                    'Sales (GBP)': float(row[3]) if row[3] is not None else None,
                    'sales_gbp': float(row[3]) if row[3] is not None else None,
                    'UK SIC 2007 Code': row[4] or '',
                    'uk_sic_2007_code': row[4] or '',
                    'Old_Accuracy': float(row[5]) if row[5] is not None else 0,  # existing_sic_confidence from database
                    'existing_sic_confidence': float(row[5]) if row[5] is not None else 0,
                    'New_Accuracy': float(row[6]) if row[6] is not None else 0,   # confidence_score from predictions
                    'confidence_score': float(row[6]) if row[6] is not None else 0,
                    'ch_sic_codes': row[7] or '',  # Companies House SIC codes
                    'predicted_sic_code': row[8] or '',  # Predicted SIC code
                    'company_id': row[9] if row[9] is not None else None,
                    'unique_id': row[10] or '',
                    'company_number': row[11] or ''
                }
                records.append(record)
            
            conn.close()
            
            return jsonify({
                'data': records,
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit if total > 0 else 0
            })
            
        except Exception as e:
            logger.error(f"Error in database-only /api/companies endpoint: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/companies/portal')
    def get_companies_portal():
        """
        API endpoint to get company data from the company_portal_view
        
        This endpoint uses the database view that combines:
        - Companies: company_number, company_name, status, jurisdiction, business_description, ownership_type, entity_type, parent_company
        - Company Financials: sales_gbp, employees_single_site  
        - Company SIC Codes: uk_sic_2007_code, uk_sic_2007_description
        - SIC Prediction History: predicted_sic_code, confidence_score, existing_sic_confidence, ai_reasoning, existing_sic_reasoning
        
        Returns the same format as /api/companies for compatibility
        """
        try:
            # Get query parameters
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 50, type=int)
            country = request.args.get('country', 'all')
            search = request.args.get('search', '')
            
            # 🔄 Cache-busting parameters for screen refresh
            force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
            cache_bust = request.args.get('cache_bust', '')
            
            if force_refresh:
                logger.info(f"🔄 Force refresh requested with cache_bust: {cache_bust}")
            
            # Get sorting parameters
            sort_key = request.args.get('sort_key', '')
            sort_direction = request.args.get('sort_direction', 'asc')
            sort_type = request.args.get('sort_type', 'string')
            
            # Connect to database using configuration
            import sqlite3
            config = get_credit_risk_config()
            conn = config.get_database_connection()
            cursor = conn.cursor()
            
            # Build WHERE clause for filters
            where_conditions = []
            where_conditions_direct = []  # For direct table queries
            params = []
            
            # Country filter (using jurisdiction field)
            if country and country != 'all':
                where_conditions.append("cpv.jurisdiction = ?")  # For view queries
                where_conditions_direct.append("c.jurisdiction = ?")  # For direct queries
                params.append(country)
            
            # Search filter (company name)
            if search:
                where_conditions.append("cpv.company_name LIKE ?")  # For view queries
                where_conditions_direct.append("c.company_name LIKE ?")  # For direct queries
                params.append(f"%{search}%")
            
            # Build WHERE clauses
            where_clause = ""
            where_clause_direct = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
                where_clause_direct = "WHERE " + " AND ".join(where_conditions_direct)
            
            # Get total count (use appropriate query based on force_refresh)
            if force_refresh:
                count_query = f"SELECT COUNT(DISTINCT c.id) FROM companies c LEFT JOIN company_financials cf ON c.id = cf.company_id {where_clause_direct}"
            else:
                count_query = f"SELECT COUNT(*) FROM company_portal_view cpv {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Calculate pagination
            offset = (page - 1) * limit
            
            # Build ORDER BY clause with sorting support
            if force_refresh:
                # Direct table column names for force refresh
                sort_column_map = {
                    'index': 'c.id',
                    'company_name': 'c.company_name',
                    'company_number': 'c.company_number', 
                    'business_description': 'c.business_description',
                    'parent_company': 'c.parent_company',
                    'status': 'c.status',
                    'ownership_type': 'c.ownership_type',
                    'entity_type': 'c.entity_type',
                    'country': 'c.jurisdiction',
                    'revenue': 'cf.sales_gbp',
                    'employees': 'cf.employees_single_site',
                    'current_sic': 'csc.uk_sic_2007_code',
                    'sic_description': 'csc.uk_sic_2007_description',
                    'existing_sic_confidence': 'sph_latest.existing_sic_confidence',
                    'predicted_sic': 'sph_latest.predicted_sic_code',
                    'predicted_confidence': 'sph_latest.confidence_score',
                    'ch_sic_codes': 'sph_latest.ch_sic_codes'
                }
                # Default order for force refresh
                order_clause = "ORDER BY c.company_name ASC"
            else:
                # View column names for normal queries
                sort_column_map = {
                    'index': 'cpv.company_id',
                    'company_name': 'cpv.company_name',
                    'company_number': 'cpv.company_number', 
                    'business_description': 'cpv.business_description',
                    'parent_company': 'cpv.parent_company',
                    'status': 'cpv.status',
                    'ownership_type': 'cpv.ownership_type',
                    'entity_type': 'cpv.entity_type',
                    'country': 'cpv.jurisdiction',
                    'revenue': 'cpv.sales_gbp',
                    'employees': 'cpv.employees_single_site',
                    'current_sic': 'cpv.uk_sic_2007_code',
                    'sic_description': 'cpv.uk_sic_2007_description',
                    'existing_sic_confidence': 'cpv.existing_sic_confidence',
                    'predicted_sic': 'cpv.predicted_sic_code',
                    'predicted_confidence': 'cpv.confidence_score',
                    'ch_sic_codes': 'cpv.ch_sic_codes'
                }
                # Default order for normal queries
                order_clause = "ORDER BY cpv.company_name ASC"
            
            # Apply custom sorting if provided
            if sort_key and sort_key in sort_column_map:
                sort_column = sort_column_map[sort_key]
                sort_dir = 'DESC' if sort_direction.lower() == 'desc' else 'ASC'
                
                # Handle NULL values by putting them last
                if sort_type == 'number':
                    order_clause = f"ORDER BY {sort_column} IS NULL, {sort_column} {sort_dir}"
                else:
                    order_clause = f"ORDER BY {sort_column} COLLATE NOCASE {sort_dir}"
                
                logger.info(f"🔄 Server-side sorting: {sort_key} ({sort_type}) {sort_direction} -> {order_clause}")
            else:
                logger.info("📊 Default sorting: company_name ASC")
            
            # 🔄 Choose query strategy based on force_refresh
            if force_refresh:
                # Force refresh: Bypass company_portal_view and query tables directly for latest data
                logger.info("🔄 Using direct table queries for force refresh")
                data_query = f"""
                    SELECT DISTINCT
                        c.id as company_id,
                        c.unique_id,
                        c.company_number,
                        c.company_name,
                        c.status,
                        c.jurisdiction,
                        c.business_description,
                        c.ownership_type,
                        c.entity_type,
                        c.parent_company,
                        cf.sales_gbp,
                        cf.employees_single_site,
                        csc.uk_sic_2007_code,
                        csc.uk_sic_2007_description,
                        COALESCE(sph_latest.predicted_sic_code, '') as predicted_sic_code,
                        COALESCE(sph_latest.confidence_score, 0.0) as confidence_score,
                        COALESCE(sph_latest.existing_sic_confidence, 0.0) as existing_sic_confidence,
                        COALESCE(sph_latest.ch_sic_codes, '') as ch_sic_codes,
                        sph_latest.prediction_timestamp,
                        sph_latest.model_version,
                        sph_latest.prediction_method,
                        sph_latest.ai_reasoning,
                        sph_latest.existing_sic_reasoning,
                        sph_latest.prediction_timestamp as sph_prediction_timestamp,
                        sph_latest.existing_sic_calculation_timestamp
                    FROM companies c
                    LEFT JOIN company_financials cf ON c.id = cf.company_id
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id AND csc.is_primary = 1
                    LEFT JOIN (
                        SELECT 
                            company_id,
                            predicted_sic_code,
                            confidence_score,
                            existing_sic_confidence,
                            ch_sic_codes,
                            ch_sic_description,
                            ai_reasoning,
                            existing_sic_reasoning,
                            prediction_timestamp,
                            existing_sic_calculation_timestamp,
                            model_version,
                            prediction_method,
                            ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY prediction_timestamp DESC) as rn
                        FROM sic_prediction_history
                        WHERE company_id IS NOT NULL
                    ) sph_latest ON c.id = sph_latest.company_id AND sph_latest.rn = 1
                    {where_clause_direct}
                    {order_clause}
                    LIMIT ? OFFSET ?
                """
            else:
                # Normal query: Use company_portal_view for performance
                data_query = f"""
                    SELECT 
                        cpv.company_id,
                        cpv.unique_id,
                        cpv.company_number,
                        cpv.company_name,
                        cpv.status,
                        cpv.jurisdiction,
                        cpv.business_description,
                        cpv.ownership_type,
                        cpv.entity_type,
                        cpv.parent_company,
                        cpv.sales_gbp,
                        cpv.employees_single_site,
                        cpv.uk_sic_2007_code,
                        cpv.uk_sic_2007_description,
                        cpv.predicted_sic_code,
                        cpv.confidence_score,
                        cpv.existing_sic_confidence,
                        cpv.ch_sic_codes,
                        cpv.prediction_timestamp,
                        cpv.model_version,
                        cpv.prediction_method,
                        sph_latest.ai_reasoning,
                        sph_latest.existing_sic_reasoning,
                        sph_latest.prediction_timestamp as sph_prediction_timestamp,
                        sph_latest.existing_sic_calculation_timestamp
                    FROM company_portal_view cpv
                    LEFT JOIN (
                        SELECT 
                            company_id,
                            ai_reasoning,
                            existing_sic_reasoning,
                            prediction_timestamp,
                            existing_sic_calculation_timestamp,
                            ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY prediction_timestamp DESC) as rn
                        FROM sic_prediction_history
                        WHERE company_id IS NOT NULL
                    ) sph_latest ON cpv.company_id = sph_latest.company_id AND sph_latest.rn = 1
                    {where_clause}
                    {order_clause}
                    LIMIT ? OFFSET ?
                """
            
            cursor.execute(data_query, params + [limit, offset])
            rows = cursor.fetchall()

            # Convert to JSON-compatible format
            records = []
            for row in rows:
                record = {
                    'company_id': row[0],
                    'unique_id': row[1] or '',
                    'company_number': row[2] or '',
                    'company_name': row[3] or '',
                    'status': row[4] or '',
                    'jurisdiction': row[5] or '',
                    'business_description': row[6] or '',
                    'ownership_type': row[7] or '',
                    'entity_type': row[8] or '',
                    'parent_company': row[9] or '',
                    'sales_gbp': float(row[10]) if row[10] is not None else None,
                    'employees_single_site': int(row[11]) if row[11] is not None else None,
                    'uk_sic_2007_code': row[12] or '',
                    'uk_sic_2007_description': row[13] or '',
                    'predicted_sic_code': row[14] or '',
                    'confidence_score': float(row[15]) if row[15] is not None else None,
                    'existing_sic_confidence': float(row[16]) if row[16] is not None else None,
                    'ch_sic_codes': row[17] or '',
                    'prediction_timestamp': row[18] or '',
                    'model_version': row[19] or '',
                    'prediction_method': row[20] or '',
                    'ai_reasoning': row[21] or '',
                    'existing_sic_reasoning': row[22] or '',
                    'sph_prediction_timestamp': row[23] or '',
                    'existing_sic_calculation_timestamp': row[24] or ''
                }
                records.append(record)
            
            conn.close()
            
            response_data = {
                'data': records,  # Keep as 'data' for frontend compatibility
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit if total > 0 else 0,
                'sort_key': sort_key,
                'sort_direction': sort_direction,
                'sort_type': sort_type,
                'force_refresh': force_refresh,  # Include cache-busting info
                'cache_bust': cache_bust
            }
            
            # 🔄 Add cache-busting headers for force refresh
            response = jsonify(response_data)
            if force_refresh:
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                logger.info("🔄 Added cache-busting headers for force refresh response")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in /api/companies/portal: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/companies/with-filing-data')
    def get_companies_with_filing_data():
        """
        API endpoint to get list of companies that have filing history data
        Used to update filing data availability indicators in the UI
        """
        try:
            # Connect to database
            config = get_credit_risk_config()
            conn = config.get_database_connection()
            cursor = conn.cursor()
            
            # Query to get companies that have filing data
            # Join with companies table to get id (primary key)
            query = """
                SELECT DISTINCT 
                    c.id as company_id,
                    f.company_name,
                    f.company_registration_number,
                    f.filing_date,
                    f.data_ingestion_timestamp
                FROM company_filing_history_accounts f
                JOIN companies c ON c.unique_id = f.unique_id
                ORDER BY f.data_ingestion_timestamp DESC
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Convert to JSON format
            companies_with_filing = []
            for row in rows:
                companies_with_filing.append({
                    'company_id': row[0],
                    'company_name': row[1],
                    'company_registration_number': row[2],
                    'filing_date': row[3],
                    'data_ingestion_timestamp': row[4]
                })
            
            conn.close()
            
            return jsonify({
                'success': True,
                'data': companies_with_filing,
                'count': len(companies_with_filing)
            })
            
        except Exception as e:
            logger.error(f"Error in /api/companies/with-filing-data: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/company/<int:company_id>/details')
    def get_company_comprehensive_details(company_id):
        """
        Get comprehensive company details with AI reasoning
        Handles both cases:
        1. When predicted SIC doesn't exist - explain why low score / generate real-time reasoning
        2. When predicted SIC exists - show existing AI reasoning for predicted score rationale
        """
        try:
            # Connect to database
            config = get_credit_risk_config()
            conn = config.get_database_connection()
            cursor = conn.cursor()
            
            # Get comprehensive company data from updated company_portal_view with unique_id
            company_query = """
                SELECT 
                    cpv.company_id,
                    cpv.unique_id,
                    cpv.company_number,
                    cpv.company_name,
                    cpv.status,
                    cpv.jurisdiction,
                    cpv.business_description,
                    cpv.ownership_type,
                    cpv.entity_type,
                    cpv.parent_company,
                    cpv.sales_gbp,
                    cpv.employees_single_site,
                    cpv.uk_sic_2007_code,
                    cpv.uk_sic_2007_description,
                    cpv.predicted_sic_code,
                    cpv.confidence_score,
                    cpv.existing_sic_confidence,
                    cpv.prediction_timestamp,
                    cpv.model_version,
                    cpv.prediction_method,
                    sph_latest.ai_reasoning,
                    sph_latest.existing_sic_reasoning,
                    sph_latest.prediction_timestamp as sph_prediction_timestamp,
                    sph_latest.existing_sic_calculation_timestamp
                FROM company_portal_view cpv
                LEFT JOIN (
                    SELECT 
                        company_id,
                        ai_reasoning,
                        existing_sic_reasoning,
                        prediction_timestamp,
                        existing_sic_calculation_timestamp,
                        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY prediction_timestamp DESC) as rn
                    FROM sic_prediction_history
                    WHERE company_id IS NOT NULL
                ) sph_latest ON cpv.company_id = sph_latest.company_id AND sph_latest.rn = 1
                WHERE cpv.company_id = ?
            """
            
            cursor.execute(company_query, (company_id,))
            company_row = cursor.fetchone()
            
            if not company_row:
                conn.close()
                return jsonify({
                    'error': f'Company not found with ID: {company_id}',
                    'company_id': company_id,
                    'status': 'error'
                }), 404
            
            # Convert to dictionary
            company_data = {
                'company_id': company_row[0],
                'unique_id': company_row[1] or '',
                'company_number': company_row[2] or '',
                'company_name': company_row[3] or '',
                'status': company_row[4] or '',
                'jurisdiction': company_row[5] or '',
                'business_description': company_row[6] or '',
                'ownership_type': company_row[7] or '',
                'entity_type': company_row[8] or '',
                'parent_company': company_row[9] or '',
                'sales_gbp': float(company_row[10]) if company_row[10] is not None else None,
                'employees_single_site': int(company_row[11]) if company_row[11] is not None else None,
                'uk_sic_2007_code': company_row[12] or '',
                'uk_sic_2007_description': company_row[13] or '',
                'predicted_sic_code': company_row[14] or '',
                'confidence_score': float(company_row[15]) if company_row[15] is not None else None,
                'existing_sic_confidence': float(company_row[16]) if company_row[16] is not None else None,
                'prediction_timestamp': company_row[17] or '',
                'model_version': company_row[18] or '',
                'prediction_method': company_row[19] or '',
                'ai_reasoning': company_row[20] or '',
                'existing_sic_reasoning': company_row[21] or '',
                'sph_prediction_timestamp': company_row[22] or '',
                'existing_sic_calculation_timestamp': company_row[23] or ''
            }
            
            # Determine reasoning strategy based on data availability
            has_predicted_sic = bool(company_data['predicted_sic_code'])
            has_existing_ai_reasoning = bool(company_data['ai_reasoning'] and len(company_data['ai_reasoning']) > 50)
            has_existing_sic_reasoning = bool(company_data['existing_sic_reasoning'] and len(company_data['existing_sic_reasoning']) > 50)
            
            reasoning_to_return = None
            reasoning_source = None
            
            # CONDITIONAL APPROACH: Use our new conditional AI reasoning logic
            # This ensures the JavaScript modal gets contextually appropriate reasoning
            if REALTIME_REASONING_AVAILABLE:
                try:
                    # Use the new conditional reasoning that considers predicted SIC
                    result = realtime_reasoning_service.generate_realtime_reasoning(company_id)
                    
                    if result.get("success"):
                        reasoning_to_return = result.get("reasoning")
                        reasoning_source = f'realtime_conditional_{result.get("source", "generated")}'
                        logger.info(f"Generated conditional AI reasoning for company {company_id} (source: {result.get('source')})")
                    else:
                        logger.warning(f"Conditional reasoning failed: {result.get('error')}")
                        reasoning_to_return = None
                    
                    # DEBUG: Check if reasoning_to_return is None despite successful generation
                    if reasoning_to_return is None:
                        logger.warning(f"⚠️ Conditional reasoning generation returned None, checking nested company_data for existing content")
                        # Fallback to nested reasoning if available
                        if has_existing_sic_reasoning:
                            reasoning_to_return = company_data['existing_sic_reasoning']
                            reasoning_source = 'existing_sic_reasoning_nested_fallback'
                            logger.info(f"Using nested existing_sic_reasoning as fallback for company {company_id}")
                    
                except Exception as realtime_error:
                    logger.warning(f"Real-time existing SIC reasoning failed for company {company_id}: {realtime_error}")
                    # Fallback hierarchy: existing SIC reasoning -> AI reasoning -> error message
                    if has_existing_sic_reasoning:
                        reasoning_to_return = company_data['existing_sic_reasoning']
                        reasoning_source = 'existing_sic_reasoning_fallback'
                        logger.info(f"Using stored existing SIC reasoning as fallback for company {company_id}")
                    elif has_existing_ai_reasoning:
                        reasoning_to_return = company_data['ai_reasoning']
                        reasoning_source = 'existing_ai_reasoning_fallback'
                        logger.info(f"Using stored AI reasoning as fallback for company {company_id}")
                    else:
                        reasoning_to_return = 'AI reasoning temporarily unavailable. Please check OpenAI API configuration.'
                        reasoning_source = 'error'
            else:
                # Real-time service unavailable - use stored content hierarchy
                if has_existing_sic_reasoning:
                    reasoning_to_return = company_data['existing_sic_reasoning']
                    reasoning_source = 'existing_sic_reasoning_stored'
                    logger.info(f"Real-time service unavailable, using stored existing SIC reasoning for company {company_id}")
                elif has_existing_ai_reasoning:
                    reasoning_to_return = company_data['ai_reasoning']
                    reasoning_source = 'existing_ai_reasoning_stored'
                    logger.info(f"Real-time service unavailable, using stored AI reasoning for company {company_id}")
                else:
                    reasoning_to_return = 'Real-time reasoning service not available and no stored reasoning found.'
                    reasoning_source = 'unavailable'
            
            conn.close()
            
            # Return comprehensive response
            response_data = {
                'company_id': company_id,
                'company_data': company_data,
                'existing_sic_reasoning': reasoning_to_return,
                'reasoning_source': reasoning_source,
                'generated_at': datetime.now().isoformat(),
                'status': 'success',
                'has_predicted_sic': has_predicted_sic,
                'has_existing_ai_reasoning': has_existing_ai_reasoning,
                'has_existing_sic_reasoning': has_existing_sic_reasoning
            }
            
            return jsonify(response_data)
                
        except Exception as e:
            logger.error(f"Error getting comprehensive company details for {company_id}: {str(e)}")
            return jsonify({
                'error': str(e),
                'company_id': company_id,
                'status': 'error'
            }), 500

    @app.route('/api/company/<int:company_id>/filing-history')
    def get_company_filing_history(company_id):
        """Get filing history for a specific company"""
        try:
            # Get company data from the companies portal API (same source as the dashboard)
            logger.info(f"Getting filing history for company ID: {company_id}")
            
            # Connect to get companies data the same way the dashboard does
            config = get_credit_risk_config()
            conn = config.get_database_connection()
            cursor = conn.cursor()
            
            # Get company from company_portal_view (same as main API)
            company_query = """
                SELECT 
                    company_name,
                    unique_id,
                    jurisdiction,
                    employees_single_site,
                    sales_gbp,
                    uk_sic_2007_code,
                    existing_sic_confidence,
                    confidence_score
                FROM company_portal_view 
                WHERE company_id = ?
            """
            cursor.execute(company_query, (company_id,))
            company_row = cursor.fetchone()
            
            if not company_row:
                conn.close()
                return jsonify({
                    'error': f'Company not found with ID: {company_id}',
                    'company_id': company_id,
                    'status': 'error'
                }), 404
            
            company_name = company_row[0]  # company_name
            company_unique_id = company_row[1]  # unique_id
            
            # Use the same database connection as the main portal API  
            # Check for existing filing data using unique_id
            existing_query = """
                SELECT * FROM company_filing_history_accounts 
                WHERE unique_id = ? 
                ORDER BY data_ingestion_timestamp DESC 
                LIMIT 1
            """
            cursor.execute(existing_query, (company_unique_id,))
            existing_filing = cursor.fetchone()
            
            if existing_filing:
                # Convert existing filing to dictionary and return
                # Convert sqlite3.Row to dict manually
                filing_data = {}
                for i, column in enumerate(cursor.description):
                    filing_data[column[0]] = existing_filing[i]
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': filing_data,
                    'source': 'database',
                    'company_id': company_id,
                    'status': 'success'
                })
            else:
                # No existing data found
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'No filing history available for this company',
                    'message': 'Use the "Fetch Financial Info" button to retrieve data from Companies House',
                    'company_id': company_id,
                    'company_name': company_name,
                    'status': 'no_data'
                }), 404
                
        except Exception as e:
            logger.error(f"Error getting filing history for company {company_id}: {str(e)}")
            return jsonify({
                'error': str(e),
                'company_id': company_id,
                'status': 'error'
            }), 500

    @app.route('/api/company/<int:company_id>/update-filing-history', methods=['POST'])
    def update_company_filing_history(company_id):
        """Fetch and store latest filing history from Companies House API using existing workflow"""
        try:
            # Get company data from the companies portal API (same source as the dashboard)
            logger.info(f"Getting company data for ID: {company_id}")
            
            # Connect to get companies data the same way the dashboard does
            config = get_credit_risk_config()
            conn = config.get_database_connection()
            cursor = conn.cursor()
            
            # Get company from company_portal_view (same as main API)
            company_query = """
                SELECT 
                    company_name,
                    jurisdiction,
                    employees_single_site,
                    sales_gbp,
                    uk_sic_2007_code,
                    existing_sic_confidence,
                    confidence_score
                FROM company_portal_view 
                WHERE company_id = ?
            """
            cursor.execute(company_query, (company_id,))
            company_row = cursor.fetchone()
            
            if not company_row:
                conn.close()
                logger.error(f"Company not found with ID: {company_id}")
                return jsonify({
                    'success': False,
                    'error': f'Company not found with ID: {company_id}',
                    'company_id': company_id
                }), 404
            
            company_name = company_row[0]  # company_name
            
            # First, check if we already have filing data for this company in our database
            # Use the same connection as the main portal API
            # Check for existing filing data
            existing_query = """
                SELECT * FROM company_filing_history_accounts 
                WHERE company_name = ? 
                ORDER BY data_ingestion_timestamp DESC 
                LIMIT 1
            """
            cursor.execute(existing_query, (company_name,))
            existing_filing = cursor.fetchone()
            
            if existing_filing:
                # Convert existing filing to dictionary manually
                filing_data = {}
                for i, column in enumerate(cursor.description):
                    filing_data[column[0]] = existing_filing[i]
                conn.close()
                
                logger.info(f"✅ Found existing filing data for {company_name}")
                return jsonify({
                    'success': True,
                    'data': filing_data,
                    'source': 'database_cache',
                    'company_id': company_id,
                    'action': 'retrieved',
                    'transaction_id': filing_data.get('transaction_id'),
                    'status': 'success'
                })
            
            conn.close()
            
            # No existing data - try to fetch from Companies House using the established workflow
            # Use the same workflow as SIC updates: company_number first, then name+status+address fallback
            from app_modules.apis.companies_house_client import CompaniesHouseClient
            
            try:
                companies_house = CompaniesHouseClient()
                
                # Get additional company info from portal view for the workflow
                conn = config.get_database_connection()
                cursor = conn.cursor()
                
                # Get more detailed company info including any existing company_number
                extended_query = """
                    SELECT 
                        company_name,
                        company_number,
                        jurisdiction,
                        status,
                        business_description,
                        sales_gbp,
                        uk_sic_2007_code
                    FROM company_portal_view 
                    WHERE company_id = ?
                """
                cursor.execute(extended_query, (company_id,))
                company_row = cursor.fetchone()
                conn.close()
                
                # Extract company details
                if not company_row:
                    logger.error(f"Company details not found for ID: {company_id}")
                    return jsonify({
                        'success': False,
                        'error': 'Company not found in database',
                        'company_id': company_id,
                        'status': 'not_found'
                    }), 404
                
                company_name = company_row[0]
                existing_company_number = company_row[1] if len(company_row) > 1 else None
                jurisdiction = company_row[2] if len(company_row) > 2 else None
                company_status = company_row[3] if len(company_row) > 3 else "active"
                business_description = company_row[4] if len(company_row) > 4 else None
                
                # STEP 1: Check if we have a company_number (direct approach)
                logger.info(f"Checking company_number for {company_name}: {repr(existing_company_number)}")
                
                if existing_company_number and existing_company_number.strip():
                    # STEP 1: Use existing company_number (direct approach)
                    logger.info(f"✅ Using existing company number: {existing_company_number} for {company_name}")
                    company_info = companies_house.get_company_by_number(existing_company_number)
                    
                    if company_info:
                        logger.info(f"✅ Found company via company_number: {existing_company_number}")
                    else:
                        logger.warning(f"❌ Company number {existing_company_number} not found in Companies House API")
                else:
                    # STEP 2: Fallback to name + status + address matching (established workflow)
                    logger.info(f"📋 No company number available, using name+status+address matching for: {company_name}")
                    
                    # Use business description or jurisdiction as address hint if available
                    address_hint = None
                    if business_description and "address" in business_description.lower():
                        address_hint = business_description
                    elif jurisdiction and jurisdiction != "United Kingdom":
                        address_hint = jurisdiction
                    
                    company_info = companies_house.get_company_by_name_and_address(
                        company_name=company_name,
                        address=address_hint,
                        status=company_status or "active"
                    )
                    
                    if company_info:
                        logger.info(f"✅ Found company via name+address matching: {company_name}")
                    else:
                        logger.warning(f"❌ Company not found via name+address matching: {company_name}")
                
                if not company_info:
                    logger.warning(f"Company not found in Companies House: {company_name}")
                    return jsonify({
                        'success': False,
                        'error': 'Company registration number does not exist or company not found in Companies House registry',
                        'company_id': company_id,
                        'company_name': company_name,
                        'message': 'This company may not be registered with Companies House UK or may have a different registered name',
                        'status': 'not_found'
                    }), 404
                
                # Found company - now get filing history
                company_number = company_info.get('company_number')
                if not company_number:
                    return jsonify({
                        'success': False,
                        'error': 'Company found but no valid company number available',
                        'company_id': company_id,
                        'status': 'invalid_company_number'
                    }), 400
                
                # Use the existing filing history method
                filing_result = companies_house.get_latest_financial_filing(company_number)
                
                if filing_result and filing_result.get('success'):
                    logger.info(f"✅ Successfully fetched filing data for {company_name} ({company_number})")
                    
                    # Store the filing data in the database
                    try:
                        # Get the unique_id for this company
                        conn = config.get_database_connection()
                        cursor = conn.cursor()
                        
                        unique_id_query = """
                            SELECT unique_id FROM company_portal_view 
                            WHERE company_id = ?
                        """
                        cursor.execute(unique_id_query, (company_id,))
                        unique_id_row = cursor.fetchone()
                        conn.close()
                        
                        if unique_id_row:
                            company_unique_id = unique_id_row[0]
                            
                            # Prepare data for the repository
                            filing_data_to_store = {
                                'unique_id': company_unique_id,
                                'company_registration_number': company_number,
                                'company_name': company_name,
                                'company_address': '',  # Will be empty unless we fetch from company_info
                                'filing_details': filing_result['data']['latest_filing'],
                                'raw_api_response': filing_result['data']['raw_api_response']
                            }
                            
                            # Initialize repository and store data
                            db_connection = DatabaseConnection()
                            filing_repository = SQLiteFilingHistoryRepository(db_connection)
                            
                            storage_success = filing_repository.insert_filing_record(filing_data_to_store)
                            
                            if storage_success:
                                logger.info(f"✅ Stored filing data in database for {company_name}")
                            else:
                                logger.warning(f"⚠️ Failed to store filing data for {company_name}, but API data available")
                                
                        else:
                            logger.warning(f"⚠️ Could not find unique_id for company_id {company_id}")
                            
                    except Exception as store_error:
                        logger.error(f"Error storing filing data: {store_error}")
                        # Continue anyway since we have the API data
                    
                    return jsonify({
                        'success': True,
                        'data': filing_result.get('data'),
                        'source': 'companies_house_api',
                        'company_id': company_id,
                        'action': 'fetched',
                        'company_number': company_number,
                        'status': 'success'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'No filing history available for this company',
                        'company_id': company_id,
                        'company_number': company_number,
                        'status': 'no_filings'
                    }), 404
                    
            except Exception as ch_error:
                logger.error(f"Companies House API error for {company_name}: {ch_error}")
                return jsonify({
                    'success': False,
                    'error': 'Company registration number does not exist or Companies House API unavailable',
                    'company_id': company_id,
                    'company_name': company_name,
                    'details': str(ch_error),
                    'status': 'api_error'
                }), 503
                
        except Exception as e:
            logger.error(f"Error updating filing history for company {company_id}: {str(e)}")
            return jsonify({
                'error': str(e),
                'company_id': company_id,
                'status': 'error'
            }), 500

    @app.route('/api/data/reload', methods=['POST'])
    def force_reload_data():
        """Force reload company data - useful for production debugging"""
        try:
            logger.info("🔄 Force reloading company data via API...")
            verify_database_connection()
            
            # Get company count from database
            db_connection = DatabaseConnection()
            total_companies = 0
            try:
                count_results = db_connection.execute_query("SELECT COUNT(*) as count FROM companies")
                if count_results:
                    total_companies = count_results[0]['count']
                data_loaded = True
            except Exception as db_e:
                logger.warning(f"Could not query company count: {db_e}")
                data_loaded = False
                
            return jsonify({
                'status': 'success',
                'message': 'Data reloaded successfully',
                'company_data_loaded': data_loaded,
                'total_companies': total_companies,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error reloading data: {str(e)}")
            return jsonify({
                'status': 'error', 
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    # [DEAD ROUTE] /api/agents/status — returns hardcoded mock agent list. No frontend consumer; /agents page removed. Safe to remove.
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

    @app.route('/api/open-sqlite-browser', methods=['POST'])
    def open_sqlite_browser():
        """Redirect to built-in web database viewer"""
        return jsonify({
            'status': 'ready',
            'container_url': '/database-viewer',
            'message': 'Opening built-in web database viewer...'
        })

    def _open_sqlite_browser_legacy():
        """Legacy: Open DB Browser for SQLite with the database using Azure Container Instance or local app"""
        try:
            import subprocess
            import platform
            
            # Get the database path
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')
            
            # Enhanced environment detection
            is_azure = bool(os.getenv('WEBSITE_SITE_NAME') or os.getenv('WEBSITE_HOSTNAME'))
            is_local = not is_azure
            
            logger.info(f"SQLite browser request - Environment: {'Azure' if is_azure else 'Local'}")
            
            if is_azure:
                # Use Azure Container Instance for SQLite browser
                if hasattr(app, 'sqlite_browser_manager'):
                    try:
                        container_status = app.sqlite_browser_manager.get_container_status()
                        
                        if container_status == 'stopped':
                            logger.info("Starting SQLite browser container...")
                            result = app.sqlite_browser_manager.start_container()
                            if result['success']:
                                return jsonify({
                                    'status': 'starting',
                                    'message': 'SQLite Browser container is starting up. It will be available shortly.',
                                    'container_url': result.get('url', 'URL will be available once container is ready'),
                                    'estimated_wait': '30-60 seconds'
                                })
                            else:
                                return jsonify({
                                    'status': 'error',
                                    'error': f'Failed to start container: {result.get("error", "Unknown error")}'
                                }), 500
                        
                        elif container_status == 'running':
                            container_url = app.sqlite_browser_manager.get_container_url()
                            if container_url:
                                return jsonify({
                                    'status': 'ready',
                                    'message': 'SQLite Browser is ready to use!',
                                    'container_url': container_url,
                                    'action': 'open_url'
                                })
                            else:
                                return jsonify({
                                    'status': 'error',
                                    'error': 'Container is running but URL not available'
                                }), 500
                        
                        elif container_status == 'starting':
                            return jsonify({
                                'status': 'starting',
                                'message': 'SQLite Browser container is already starting up. Please wait...',
                                'estimated_wait': '30-60 seconds'
                            })
                        
                        elif container_status == 'auth_failed':
                            return jsonify({
                                'status': 'unavailable',
                                'message': 'SQLite Browser container service is not available',
                                'reason': 'Azure authentication not configured for container management',
                                'alternative': 'You can still view and manage data using the web interface above, or download the database file for local viewing',
                                'suggestion': 'To enable container-based SQLite browser, configure managed identity for this Azure Web App'
                            })
                        
                        else:
                            return jsonify({
                                'status': 'error',
                                'error': f'Container in unexpected state: {container_status}'
                            }), 500
                            
                    except Exception as e:
                        logger.error(f"Error with SQLite browser container: {str(e)}")
                        return jsonify({
                            'status': 'error',
                            'error': f'Container management error: {str(e)}'
                        }), 500
                else:
                    is_azure_webapp = os.getenv('WEBSITE_SITE_NAME') is not None
                    error_msg = 'SQLite browser is not available in Azure Web App environment' if is_azure_webapp else 'SQLite browser container manager not initialized'
                    return jsonify({
                        'status': 'error',
                        'error': error_msg,
                        'alternative': 'Use the web interface or download the database file to view locally'
                    }), 500
            
            else:
                # Local environment - use traditional desktop application
                system = platform.system()
                logger.info(f"Opening local SQLite browser on {system}")
                
                # Check if database file exists
                if not os.path.exists(db_path):
                    return jsonify({
                        'status': 'error',
                        'error': f'Database file not found: {db_path}'
                    }), 404
                
                # Platform-specific commands
                if system == 'Darwin':  # macOS
                    cmd = ['open', '-a', 'DB Browser for SQLite', db_path]
                elif system == 'Linux':
                    cmd = ['sqlitebrowser', db_path]
                elif system == 'Windows':
                    cmd = ['start', '', 'sqlitebrowser.exe', db_path]
                else:
                    return jsonify({
                        'status': 'error',
                        'error': f'Unsupported platform: {system}. Cannot open SQLite browser.',
                        'suggestion': 'Please install DB Browser for SQLite and open the database manually.',
                        'database_path': db_path
                    }), 400
                
                # Execute the command in background
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return jsonify({
                        'status': 'success',
                        'message': f'Opening SQLite Browser with local database on {system}',
                        'database_path': db_path,
                        'action': 'local_app_launched'
                    })
                except subprocess.CalledProcessError as e:
                    return jsonify({
                        'status': 'error',
                        'error': f'Failed to launch SQLite browser: {str(e)}',
                        'suggestion': 'Please ensure DB Browser for SQLite is installed.',
                        'database_path': db_path
                    }), 500
                
        except FileNotFoundError as e:
            logger.error(f"SQLite Browser not found: {str(e)}")
            return jsonify({
                'status': 'error', 
                'error': 'SQLite Browser application not found. Please install DB Browser for SQLite.',
                'download_url': 'https://sqlitebrowser.org/dl/'
            }), 404
        except Exception as e:
            logger.error(f"Error opening SQLite Browser: {str(e)}")
            return jsonify({
                'status': 'error', 
                'error': str(e)
            }), 500

    @app.route('/api/open-vector-sqlite-browser', methods=['POST'])
    def open_vector_sqlite_browser():
        """Redirect to built-in web database viewer (vector DB tab)"""
        return jsonify({
            'status': 'ready',
            'container_url': '/database-viewer?db=vector',
            'message': 'Opening built-in web vector database viewer...'
        })

    def _open_vector_sqlite_browser_legacy():
        """Legacy: Open DB Browser for SQLite with the vector database using Azure Container Instance or local app"""
        try:
            import subprocess
            import platform
            
            # Get the vector database path
            vector_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vector_database.db')
            
            # Enhanced environment detection
            is_azure = bool(os.getenv('WEBSITE_SITE_NAME') or os.getenv('WEBSITE_HOSTNAME'))
            is_local = not is_azure
            
            logger.info(f"Vector SQLite browser request - Environment: {'Azure' if is_azure else 'Local'}")
            
            if is_azure:
                # Use Azure Container Instance for SQLite browser
                if hasattr(app, 'sqlite_browser_manager'):
                    try:
                        container_status = app.sqlite_browser_manager.get_container_status()
                        
                        if container_status == 'stopped':
                            logger.info("Starting Vector SQLite browser container...")
                            result = app.sqlite_browser_manager.start_container()
                            if result['success']:
                                return jsonify({
                                    'status': 'starting',
                                    'message': 'Vector SQLite Browser container is starting up. It will be available shortly.',
                                    'container_url': result.get('url', 'URL will be available once container is ready'),
                                    'estimated_wait': '30-60 seconds'
                                })
                            else:
                                return jsonify({
                                    'status': 'error',
                                    'error': f'Failed to start container: {result.get("error", "Unknown error")}'
                                }), 500
                        
                        elif container_status == 'running':
                            container_url = app.sqlite_browser_manager.get_container_url()
                            return jsonify({
                                'status': 'ready',
                                'message': 'Vector SQLite Browser container is ready!',
                                'container_url': container_url
                            })
                        
                        else:
                            return jsonify({
                                'status': 'info',
                                'message': f'Vector SQLite browser container status: {container_status}. Attempting to restart...'
                            })
                            
                    except Exception as e:
                        logger.error(f"Error with Vector SQLite browser container: {str(e)}")
                        return jsonify({
                            'status': 'error',
                            'error': f'Container management error: {str(e)}'
                        }), 500
                else:
                    is_azure_webapp = os.getenv('WEBSITE_SITE_NAME') is not None
                    error_msg = 'Vector SQLite browser is not available in Azure Web App environment' if is_azure_webapp else 'Vector SQLite browser container manager not initialized'
                    return jsonify({
                        'status': 'error',
                        'error': error_msg,
                        'alternative': 'Use the web interface or download the vector database file to view locally'
                    }), 500
            
            else:
                # Local environment - use traditional desktop application
                system = platform.system()
                logger.info(f"Opening local Vector SQLite browser on {system}")
                
                # Check if vector database file exists
                if not os.path.exists(vector_db_path):
                    return jsonify({
                        'status': 'error',
                        'error': f'Vector database file not found: {vector_db_path}'
                    }), 404
                
                # Platform-specific commands
                if system == 'Darwin':  # macOS
                    cmd = ['open', '-a', 'DB Browser for SQLite', vector_db_path]
                elif system == 'Linux':
                    cmd = ['sqlitebrowser', vector_db_path]
                elif system == 'Windows':
                    cmd = ['start', '', 'sqlitebrowser.exe', vector_db_path]
                else:
                    return jsonify({
                        'status': 'error',
                        'error': f'Unsupported platform: {system}. Cannot open Vector SQLite browser.',
                        'suggestion': 'Please install DB Browser for SQLite and open the vector database manually.',
                        'database_path': vector_db_path
                    }), 400
                
                # Execute the command in background
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return jsonify({
                        'status': 'success',
                        'message': f'Opening Vector SQLite Browser with local vector database on {system}',
                        'database_path': vector_db_path,
                        'action': 'local_app_launched'
                    })
                except subprocess.CalledProcessError as e:
                    return jsonify({
                        'status': 'error',
                        'error': f'Failed to launch Vector SQLite browser: {str(e)}',
                        'suggestion': 'Please ensure DB Browser for SQLite is installed.',
                        'database_path': vector_db_path
                    }), 500
                
        except FileNotFoundError as e:
            logger.error(f"Vector SQLite Browser not found: {str(e)}")
            return jsonify({
                'status': 'error', 
                'error': 'SQLite Browser application not found. Please install DB Browser for SQLite.',
                'download_url': 'https://sqlitebrowser.org/dl/'
            }), 404
        except Exception as e:
            logger.error(f"Error opening Vector SQLite Browser: {str(e)}")
            return jsonify({
                'status': 'error', 
                'error': str(e)
            }), 500

    @app.route('/api/sqlite-browser-status', methods=['GET'])
    def sqlite_browser_status():
        """Get the current status of the SQLite browser container"""
        try:
            # Check if we're in Azure environment
            is_azure = os.getenv('WEBSITE_SITE_NAME')
            
            if is_azure:
                if hasattr(app, 'sqlite_browser_manager'):
                    try:
                        status = app.sqlite_browser_manager.get_container_status()
                        url = app.sqlite_browser_manager.get_container_url() if status == 'running' else None
                        
                        return jsonify({
                            'success': True,
                            'container_status': status,
                            'container_url': url,
                            'environment': 'azure',
                            'last_check': app.sqlite_browser_manager.last_db_check.isoformat() if hasattr(app.sqlite_browser_manager, 'last_db_check') else None
                        })
                    except Exception as e:
                        logger.error(f"Error checking container status: {str(e)}")
                        return jsonify({
                            'success': False,
                            'error': str(e),
                            'environment': 'azure'
                        }), 500
                else:
                    return jsonify({
                        'success': False,
                        'error': 'SQLite browser manager not initialized',
                        'environment': 'azure'
                    }), 500
            else:
                return jsonify({
                    'success': True,
                    'message': 'Local environment - using desktop SQLite browser application',
                    'environment': 'local'
                })
                
        except Exception as e:
            logger.error(f"Error in sqlite_browser_status: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ── Web-based SQLite Viewer APIs ─────────────────────────────────────────

    @app.route('/api/database/tables')
    def db_list_tables():
        """List all tables in the selected database"""
        try:
            import sqlite3
            db_name = request.args.get('db', 'main')
            if db_name == 'vector':
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vector_database.db')
            else:
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')

            conn = sqlite3.connect(db_path)
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [{'name': row[0]} for row in cur.fetchall()]
            conn.close()
            return jsonify(tables)
        except Exception as e:
            logger.error(f"db_list_tables error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/database/schema/<table_name>')
    def db_table_schema(table_name):
        """Return column info for a table"""
        try:
            import sqlite3
            db_name = request.args.get('db', 'main')
            if db_name == 'vector':
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vector_database.db')
            else:
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')

            conn = sqlite3.connect(db_path)
            cur = conn.execute(f"PRAGMA table_info('{table_name}')")
            columns = [{'name': row[1], 'type': row[2], 'notnull': bool(row[3]), 'pk': bool(row[5])} for row in cur.fetchall()]
            conn.close()
            return jsonify({'table': table_name, 'columns': columns})
        except Exception as e:
            logger.error(f"db_table_schema error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/database/statistics')
    def db_statistics():
        """Return basic stats for the main database"""
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')
            conn = sqlite3.connect(db_path)

            companies = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
            try:
                sic = conn.execute("SELECT COUNT(*) FROM sic_codes").fetchone()[0]
            except Exception:
                sic = 0
            conn.close()

            size_bytes = os.path.getsize(db_path)
            if size_bytes >= 1024 * 1024:
                db_size = f"{size_bytes / 1024 / 1024:.1f} MB"
            else:
                db_size = f"{size_bytes / 1024:.0f} KB"

            return jsonify({'companies': companies, 'sic_codes': sic, 'db_size': db_size})
        except Exception as e:
            logger.error(f"db_statistics error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/database/query', methods=['POST'])
    def db_execute_query():
        """Execute a read-only SQL query and return results"""
        try:
            import sqlite3
            payload = request.get_json() or {}
            query = (payload.get('query') or '').strip()
            db_name = payload.get('db', 'main')

            if not query:
                return jsonify({'success': False, 'error': 'No query provided'}), 400

            # Block mutating statements for safety
            q_upper = query.upper().lstrip()
            for keyword in ('INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'REPLACE', 'TRUNCATE'):
                if q_upper.startswith(keyword):
                    return jsonify({'success': False, 'error': f'Write operation "{keyword}" is not allowed via the viewer.'}), 403

            if db_name == 'vector':
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vector_database.db')
            else:
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(query)
            rows = cur.fetchmany(500)  # cap at 500 rows
            columns = [d[0] for d in cur.description] if cur.description else []
            data = [{col: row[col] for col in columns} for row in rows]
            conn.close()

            return jsonify({'success': True, 'columns': columns, 'data': data, 'row_count': len(data)})
        except Exception as e:
            logger.error(f"db_execute_query error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # ── End Web-based SQLite Viewer APIs ──────────────────────────────────────

    @app.route('/api/activity-log', methods=['POST'])
    def save_activity_log():
        """Save activity log entry to database"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data or not data.get('user_action') or not data.get('action_description'):
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields: user_action and action_description'
                }), 400
            
            # Get client info
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            
            # Prepare SQL query
            query = """
                INSERT INTO activity_log 
                (user_action, action_description, company_id, company_name, action_type, 
                 session_id, ip_address, user_agent, additional_data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            
            params = [
                data.get('user_action'),
                data.get('action_description'),
                data.get('company_id'),
                data.get('company_name'),
                data.get('action_type', 'info'),
                data.get('session_id'),
                ip_address,
                user_agent,
                data.get('additional_data')
            ]
            
            # Execute query
            with get_credit_risk_config().get_database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                activity_id = cursor.lastrowid
            
            logger.info(f"Activity logged: {data.get('user_action')} - {data.get('action_description')}")
            
            return jsonify({
                'success': True,
                'activity_id': activity_id,
                'message': 'Activity logged successfully'
            })
            
        except Exception as e:
            logger.error(f"Error saving activity log: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/activity-log', methods=['GET'])
    def get_activity_logs():
        """Get recent activity logs for display"""
        try:
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            action_type = request.args.get('type')  # Filter by type if specified
            
            # Build query
            query = """
                SELECT id, user_action, action_description, company_id, company_name, 
                       action_type, session_id, timestamp
                FROM activity_log
            """
            params = []
            
            if action_type:
                query += " WHERE action_type = ?"
                params.append(action_type)
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # Execute query
            with get_credit_risk_config().get_database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                activities = []
                for row in rows:
                    activity = dict(zip(columns, row))
                    activities.append(activity)
            
            return jsonify({
                'success': True,
                'activities': activities,
                'total': len(activities)
            })
            
        except Exception as e:
            logger.error(f"Error retrieving activity logs: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # [REVIEW] /api/sqlite/companies/search — also defined in api/sqlite_routes.py (unregistered blueprint).
    # This flask_main copy IS live. Confirm if any frontend consumer exists before removing.
    @app.route('/api/sqlite/companies/search', methods=['GET'])
    def sqlite_companies_search():
        """SQLite-specific companies search endpoint for frontend data tables"""
        try:
            # Get search parameters
            query = request.args.get('q', '').strip()
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            # Build SQL query for SQLite search - Join companies with SIC data
            if query:
                # Search across multiple fields using company_portal_view
                sql_query = """
                    SELECT 
                        company_id,
                        company_name,
                        company_number,
                        status,
                        jurisdiction as postcode,
                        business_description,
                        uk_sic_2007_code as sic_code,
                        uk_sic_2007_description as sic_description,
                        existing_sic_confidence as prediction_accuracy
                    FROM company_portal_view
                    WHERE 
                        company_name LIKE ? 
                        OR uk_sic_2007_description LIKE ?
                        OR business_description LIKE ?
                    ORDER BY company_name 
                    LIMIT ? OFFSET ?
                """
                search_term = f"%{query}%"
                params = (search_term, search_term, search_term, limit, offset)
            else:
                # Return all companies if no search query using company_portal_view
                sql_query = """
                    SELECT 
                        company_id,
                        company_name,
                        company_number,
                        status,
                        jurisdiction as postcode,
                        business_description,
                        uk_sic_2007_code as sic_code,
                        uk_sic_2007_description as sic_description,
                        existing_sic_confidence as prediction_accuracy
                    FROM company_portal_view
                    ORDER BY company_name 
                    LIMIT ? OFFSET ?
                """
                params = (limit, offset)
            
            # Execute query - Use same path pattern as other functions
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')
            if not os.path.exists(db_path):
                # Fallback to root directory database
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credit_risk.db')
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            
            cursor = conn.cursor()
            cursor.execute(sql_query, params)
            results = cursor.fetchall()
            
            # Get total count for pagination using company_portal_view
            if query:
                count_query = """
                    SELECT COUNT(*) as total 
                    FROM company_portal_view
                    WHERE 
                        company_name LIKE ? 
                        OR uk_sic_2007_description LIKE ?
                        OR business_description LIKE ?
                """
                cursor.execute(count_query, (search_term, search_term, search_term))
            else:
                cursor.execute("SELECT COUNT(*) as total FROM company_portal_view")
            
            total_count = cursor.fetchone()['total']
            conn.close()
            
            # Convert results to list of dictionaries
            companies = []
            for row in results:
                company = {}
                for key in row.keys():
                    company[key] = row[key]
                companies.append(company)
            
            return jsonify({
                'success': True,
                'companies': companies,
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'search_query': query,
                'database_type': 'sqlite'
            })
            
        except Exception as e:
            logger.error(f"Error in SQLite companies search: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'companies': [],
                'total': 0
            }), 500

    # [DEAD ROUTES — OLD LANGGRAPH BLOCK] /api/workflow/structure|execute|status|visualization
    # Superseded by /api/modular/workflow/* endpoints. app.langgraph_workflow is never set.
    # Frontend does NOT call any of these. All four routes below safe to remove together.
    @app.route('/api/workflow/structure')
    def get_workflow_structure():
        """Get LangGraph workflow structure for visualization"""
        try:
            if getattr(app, 'langgraph_workflow', None) is None:
                # Return mock structure when workflow is not available
                mock_structure = {
                    'nodes': [
                        {'id': 'start', 'type': 'start', 'label': 'Start', 'x': 100, 'y': 100},
                        {'id': 'data_ingestion', 'type': 'process', 'label': 'Data Ingestion', 'x': 250, 'y': 100},
                        {'id': 'analysis', 'type': 'process', 'label': 'Analysis', 'x': 400, 'y': 100},
                        {'id': 'end', 'type': 'end', 'label': 'End', 'x': 550, 'y': 100}
                    ],
                    'edges': [
                        {'from': 'start', 'to': 'data_ingestion'},
                        {'from': 'data_ingestion', 'to': 'analysis'},
                        {'from': 'analysis', 'to': 'end'}
                    ]
                }
                return jsonify({
                    'success': True,
                    'structure': mock_structure,
                    'langgraph_available': False,
                    'message': 'Workflow visualization using mock data (LangGraph not available)'
                })
            
            structure = app.langgraph_workflow.get_workflow_visualization()
            return jsonify({
                'success': True,
                'structure': structure,
                'langgraph_available': True
            })
        except Exception as e:
            logger.error(f"Error getting workflow structure: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/workflow/execute', methods=['POST'])
    def execute_workflow():
        """Execute the LangGraph workflow"""
        try:
            if app.langgraph_workflow is None:
                return jsonify({
                    'success': False,
                    'error': 'LangGraph workflow not available in this environment',
                    'message': 'Workflow execution requires LangGraph dependencies',
                    'status': 'unavailable'
                }), 503
            
            # Get request data
            data = request.get_json() or {}
            
            # Prepare workflow input
            # Get company data from database instead of app attribute
            db_connection = DatabaseConnection()
            company_data = []
            try:
                companies_raw = db_connection.execute_query("""
                    SELECT c.*, cf.sales_gbp, cf.total_assets, cf.liabilities
                    FROM companies c
                    LEFT JOIN company_financials cf ON c.id = cf.company_id
                    LIMIT 100
                """)
                company_data = [dict(row) for row in companies_raw] if companies_raw else []
            except Exception as db_e:
                logger.warning(f"Could not load company data for workflow: {db_e}")
                
            workflow_input = {
                'company_data': company_data,
                'session_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'user_initiated': True,
                    'demo_mode': is_demo_mode()
                }
            }
            
            # Execute the workflow
            result = app.langgraph_workflow.execute_workflow(workflow_input)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/workflow/status/<session_id>')
    def get_workflow_status(session_id):
        """Get status of a specific workflow session"""
        # This would typically query a database or cache
        # For now, return a simulated status
        return jsonify({
            'session_id': session_id,
            'status': 'completed',
            'progress': 100,
            'stages': [
                {'name': 'data_ingestion', 'status': 'completed', 'progress': 100},
                {'name': 'anomaly_detection', 'status': 'completed', 'progress': 100},
                {'name': 'sector_classification', 'status': 'completed', 'progress': 100},
                {'name': 'turnover_estimation', 'status': 'completed', 'progress': 100}
            ]
        })

    @app.route('/api/workflow/visualization')
    def get_workflow_visualization():
        """Get workflow visualization data for frontend"""
        try:
            if app.langgraph_workflow is None:
                # Return mock visualization when workflow is not available
                mock_structure = {
                    'nodes': [
                        {'id': 'start', 'type': 'start', 'label': 'Start', 'x': 100, 'y': 100, 'current_status': 'idle', 'progress': 0},
                        {'id': 'data_ingestion', 'type': 'process', 'label': 'Data Ingestion', 'x': 250, 'y': 100, 'current_status': 'idle', 'progress': 0},
                        {'id': 'analysis', 'type': 'process', 'label': 'Analysis', 'x': 400, 'y': 100, 'current_status': 'idle', 'progress': 0},
                        {'id': 'end', 'type': 'end', 'label': 'End', 'x': 550, 'y': 100, 'current_status': 'idle', 'progress': 0}
                    ],
                    'edges': [
                        {'from': 'start', 'to': 'data_ingestion'},
                        {'from': 'data_ingestion', 'to': 'analysis'},
                        {'from': 'analysis', 'to': 'end'}
                    ]
                }
                
                execution_history = [
                    {
                        'session_id': 'mock_session',
                        'start_time': '2024-09-25T10:00:00Z',
                        'end_time': '2024-09-25T10:05:00Z',
                        'status': 'mock_data',
                        'nodes_executed': ['data_ingestion', 'analysis']
                    }
                ]
                
                return jsonify({
                    'success': True,
                    'structure': mock_structure,
                    'execution_history': execution_history,
                    'langgraph_available': False,
                    'message': 'Mock visualization data (LangGraph not available)'
                })
            
            # Get the workflow structure
            structure = app.langgraph_workflow.get_workflow_visualization()
            
            # Add real-time status (simulated for now)
            for node in structure['nodes']:
                node['current_status'] = 'idle'
                node['progress'] = 0
                node['last_execution'] = None
                
            # Add execution history (simulated)
            execution_history = [
                {
                    'session_id': 'session_001',
                    'start_time': '2024-09-25T10:00:00Z',
                    'end_time': '2024-09-25T10:05:00Z',
                    'status': 'completed',
                    'nodes_executed': ['data_ingestion', 'anomaly_detection', 'sector_classification']
                }
            ]
            
            return jsonify({
                'success': True,
                'workflow_structure': structure,
                'execution_history': execution_history,
                'available_actions': ['start_workflow', 'pause_workflow', 'view_logs']
            })
            
        except Exception as e:
            logger.error(f"Error getting workflow visualization: {str(e)}")
            return jsonify({'error': str(e)}), 500

    # [DEPRECATED ROUTE] /api/modular/predict-sic — uses old EnhancedSICMatcher (non-agentic). No frontend consumer.
    # Superseded by /api/predict_sic_agentic (pure agentic). Safe to remove.
    @app.route('/api/modular/predict-sic', methods=['POST'])
    @validate_api_input(validate_predict_sic_robust_input)
    def predict_sic_modular(validated_data):
        """Modular predict SIC code for a company - supports both company_id and unique_id"""
        try:
            # Extract identifiers - now supports both company_id and unique_id
            company_id = validated_data.get('company_id')
            unique_id = validated_data.get('unique_id')
            company_name = validated_data.get('company_name')  # Optional validation field
            
            # Determine which identifier was provided
            identifier = company_id if company_id else unique_id
            identifier_type = 'company_id' if company_id else 'unique_id'
            
            logger.info(f"🔮 Modular SIC Prediction for {identifier_type}: {identifier}")
            
            # Use repository for robust company lookup
            db_connection = DatabaseConnection()
            repo = SQLiteSICPredictionRepository(db_connection)
            company = repo._get_company_by_identifier(identifier)
            
            if not company:
                return jsonify({'error': f'Company not found with {identifier_type}: {identifier}'}), 404
            
            found_company_name = company.get('company_name', '')  # Use database field name
            
            # If company_name was provided, validate it matches for consistency (optional validation)
            if company_name and found_company_name.strip().lower() != company_name.strip().lower():
                return jsonify({
                    'error': f'Company name mismatch. Expected: {company_name}, Found: {found_company_name}',
                    identifier_type: identifier
                }), 400
            
            # Use the found company name for the rest of the process
            actual_company_name = found_company_name
            
            # Use simulation service for demo
            if is_demo_mode():
                prediction_result = simulation_service.generate_mock_sic_prediction()
                return jsonify({
                    'success': True,
                    'predicted_sic': prediction_result['predicted_sic'],
                    'confidence': prediction_result['confidence'],
                    'description': prediction_result['description'],
                    'method': 'simulation',
                    'message': f'SIC prediction completed for {actual_company_name}',
                    'company_name': actual_company_name,
                    identifier_type: identifier
                })
            
            # Real prediction logic using EnhancedSICMatcher
            if not ENHANCED_SIC_MATCHER_AVAILABLE:
                return jsonify({'error': 'Enhanced SIC matcher not available - check rapidfuzz dependency'}), 500
            
            # Get business description from company data (check multiple field names)
            business_description = (company.get('Business Description', '') or 
                                  company.get('business_description', '') or 
                                  company.get('Business_Description', ''))
            if not business_description:
                return jsonify({'error': 'Business description not found for company'}), 404

            # Get current SIC code from company data - prioritize database fields first
            current_sic = company.get('uk_sic_2007_code', '') or company.get('existing_sic_code', '') or company.get('SIC Code (SIC 2007)', '')

            # Create SIC matcher and perform prediction
            config = get_credit_risk_config()
            sic_matcher = EnhancedSICMatcher(config)

            # Calculate new accuracy (this is the main prediction method)
            prediction_result = sic_matcher.calculate_new_accuracy(business_description)

            if not prediction_result or not prediction_result.get('predicted_sic_code'):
                return jsonify({
                    'error': 'No suitable SIC prediction found',
                    'message': f'Could not predict SIC for {actual_company_name}',
                    'company_name': actual_company_name,
                    identifier_type: identifier
                }), 404

            return jsonify({
                'success': True,
                'predicted_sic': prediction_result['predicted_sic_code'],
                'confidence': round(prediction_result['new_accuracy'], 1),
                'description': prediction_result['predicted_sic_description'],
                'current_sic': current_sic,  # Include current SIC in response
                'method': 'modular',
                'message': f'SIC prediction completed for {actual_company_name}',
                'company_name': actual_company_name,
                identifier_type: identifier
            })
            
        except Exception as e:
            logger.error(f"❌ Modular SIC Prediction error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    # [DEAD ROUTE] /api/predict_sic — old non-agentic SIC prediction (simulation + EnhancedSICMatcher).
    # No frontend consumer (JS calls /api/predict_sic_agentic). Safe to remove.
    @app.route('/api/predict_sic', methods=['POST'])
    @validate_api_input(validate_predict_sic_robust_input)
    def predict_sic(validated_data):
        """Predict SIC code for a company - ROBUST: accepts both company_id and unique_id"""
        try:
            # Get identifier (company_id or unique_id) and company_name (optional) from validated data
            company_id = validated_data.get('company_id')
            unique_id = validated_data.get('unique_id')  
            company_name = validated_data.get('company_name')  # Optional in hybrid approach
            
            # Use whichever identifier is available (robust approach)
            identifier = str(company_id) if company_id else unique_id
            
            # ROBUST DATABASE LOOKUP: Use both company_id and unique_id for exact company matching
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')
            db_connection = DatabaseConnection(db_path)
            repo = SQLiteSICPredictionRepository(db_connection)
            company = repo.get_company_by_unique_id(identifier)
            
            if not company:
                return jsonify({'error': f'Company not found with identifier: {identifier}'}), 404
                
            # Get the actual company name from database
            found_company_name = company.get('company_name', '')
            
            # If company_name was provided, validate it matches for consistency (optional validation)
            if company_name and found_company_name.strip().lower() != company_name.strip().lower():
                return jsonify({
                    'error': f'Company name mismatch. Expected: {company_name}, Found: {found_company_name}',
                    'identifier': identifier
                }), 400
            
            # Use the found company name for the rest of the process
            actual_company_name = found_company_name
            
            # Get the company index (row number) for backward compatibility with existing prediction logic
            with db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT company_name FROM companies ORDER by id")
                all_companies = cursor.fetchall()
                company_index = None
                for i, (name,) in enumerate(all_companies):
                    if name.strip().lower() == actual_company_name.strip().lower():
                        company_index = i
                        break
                
                if company_index is None:
                    return jsonify({'error': f'Company index not found: {actual_company_name}'}), 404
            
            # MODULAR ARCHITECTURE: Try using service-based approach first
            try:
                if MODULAR_AVAILABLE:
                    sic_service = get_sic_prediction_service(app)
                    
                    use_real_agents = bool(request.json and request.json.get('use_real_agents', False))
                    
                    result = sic_service.predict_sic_for_company(
                        company_index, use_real_agents, app
                    )
                    
                    if result and 'error' not in result:
                        return jsonify(result)
                    elif result and 'error' in result:
                        # If modular approach has validation error, return it
                        return jsonify(result), 400
            except Exception as modular_error:
                logger.warning(f"Modular SIC prediction failed, using fallback: {modular_error}")
            
            # DATABASE-ONLY APPROACH: Get company data directly from database
            db_connection = DatabaseConnection()
            
            with db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get company details by company_id using company_portal_view
                cursor.execute("""
                    SELECT company_name, business_description, uk_sic_2007_code, 
                           existing_sic_confidence
                    FROM company_portal_view
                    WHERE company_id = ?
                """, (company_id,))
                
                company_row = cursor.fetchone()
            
            if not company_row:
                return jsonify({'error': 'Invalid company ID or company not found'}), 400
            
            company_name = company_row[0] or 'Unknown'
            business_description = company_row[1] or ''
            current_sic = company_row[2] or ''
            baseline_accuracy = float(company_row[3] or 0.0)
            
            # Create enhanced SIC matcher instance for database-only operations
            config = get_credit_risk_config()
            sic_matcher = EnhancedSICMatcher(config)
            
            # Initialize prediction variables
            predicted_sic = current_sic
            confidence = 0.0
            reasoning = ""
            workflow_type = "UNKNOWN"
            algorithm_accuracy = baseline_accuracy
            boosted_accuracy = baseline_accuracy
            
            # 🤖 USE AGENTIC WORKFLOW - NEW PRIMARY SYSTEM
            logger.info(f"🤖 Using AGENTIC SIC prediction workflow for: {company_name}")
            
            # Check if agentic service is available
            if not (hasattr(app, 'agentic_sic_service') and app.agentic_sic_service):
                return jsonify({
                    'error': 'Agentic SIC service not available',
                    'message': 'Please ensure agentic components are properly configured'
                }), 500
            
            # Execute agentic workflow
            try:
                agentic_result = app.agentic_sic_service.predict_sic_agentic(
                    company_name=company_name,
                    business_description=business_description,
                    company_number='',  # Not available in database-only mode
                    address='',
                    workflow_config=request.json.get('workflow_config', {}) if request.json else {}
                )
                
                # Extract results from agentic workflow - use results as-is without external boosting
                predicted_sic = agentic_result.get('predicted_sic_code', current_sic)
                confidence = agentic_result.get('confidence_score', 0.0)
                reasoning = agentic_result.get('reasoning', 'Agentic workflow prediction')
                
                # Use agentic workflow results without modification
                algorithm_accuracy = confidence * 100
                boosted_accuracy = algorithm_accuracy  # No external boosting for agentic workflow
                
                workflow_type = "AGENTIC_WORKFLOW"
                
            except Exception as agentic_error:
                logger.error(f"❌ Agentic workflow failed: {agentic_error}")
                return jsonify({
                    'error': f'Agentic SIC prediction failed: {str(agentic_error)}',
                    'message': 'Please check agentic service configuration'
                }), 500
            
            # DATABASE-ONLY: Predictions are stored in memory for UI display only
            # They will be saved to database only when user approves them via /api/approve_sic_prediction
            logger.info(f"🔮 SIC prediction completed for {company_name}: {predicted_sic} ({confidence:.1%})")
            logger.info(f"📝 Prediction ready for manual approval - not auto-saved to database")
            
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
            elif workflow_type == "ENHANCED_FUZZY_MATCHING":
                workflow_steps = [
                    {
                        "step": 1,
                        "agent": "Data Ingestion Agent",
                        "message": f"Loading company data for {company_name}...",
                        "status": "completed"
                    },
                    {
                        "step": 2,
                        "agent": "Enhanced SIC Matcher",
                        "message": f"Analyzing business description with 751 SIC codes...",
                        "status": "completed"
                    },
                    {
                        "step": 3,
                        "agent": "Fuzzy Matching Algorithm",
                        "message": f"Best match found: {predicted_sic} (Real Fuzzy Matching)",
                        "status": "completed"
                    },
                    {
                        "step": 4,
                        "agent": "Results Compilation Agent",
                        "message": f"Fuzzy match accuracy: {boosted_accuracy:.1f}%",
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
            
            # PREDICTION WORKFLOW COMPLETE - DO NOT AUTO-SAVE TO DATABASE
            # Predictions are only displayed in UI and saved when user manually approves them
            logger.info(f"🔮 SIC prediction completed for {company_name}: {predicted_sic} ({confidence:.1%})")
            logger.info(f"📝 Prediction ready for manual approval - not auto-saved to database")
            
            return jsonify({
                'success': True,
                'company_name': company_name,
                'company_index': company_index,  # Add this for frontend approval
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

    # [DUPLICATE ROUTE] /api/predict_sic_agentic — also registered earlier by agentic_routes.py
    # (register_agentic_routes → @app.route('/api/predict_sic_agentic'), function api_predict_sic_agentic).
    # The agentic_routes version (registered at line ~495) wins. This ~300-line block is shadow code.
    # Safe to remove this entire function once confirmed the agentic_routes alias works correctly.
    # 🤖 AGENTIC SIC PREDICTION ENDPOINT - PRIMARY SYSTEM
    @app.route('/api/predict_sic_agentic', methods=['POST'])
    def predict_sic_agentic():
        """
        🤖 AGENTIC SIC PREDICTION - Primary AI workflow with 5-agent coordination
        
        This is the main SIC prediction system using advanced agentic workflow.
        No fallbacks - pure agentic processing with LangGraph coordination.
        """
        try:
            # Validate request data
            if not request.json:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            # Extract input parameters with flexible input support
            company_name = request.json.get('company_name', '').strip()
            business_description = request.json.get('business_description', '').strip()
            company_number = request.json.get('company_number', '').strip()
            address = request.json.get('address', '').strip()
            
            # 🔑 UNIQUE_ID LOOKUP: Use unique_id instead of company_index for existing data lookup
            company_id = None  # Track the actual database ID
            unique_id = request.json.get('unique_id')  # Primary lookup method
            company = None     # Initialize company variable for field mapping
            
            # If unique_id provided, load from existing data using proper unique_id lookup
            if unique_id:
                try:
                    # Use unique_id-based repository lookup - NO row position confusion
                    if hasattr(app, 'sqlite_sic_repository') and app.sqlite_sic_repository:
                        company_data = app.sqlite_sic_repository.get_company_by_unique_id(unique_id)
                        if company_data:
                            # Store company data for later field mapping
                            company = company_data
                            # DUAL-KEY VALIDATION: Extract both company_id and unique_id
                            company_id = company.get('id')  # Primary database ID
                            fetched_unique_id = company.get('unique_id', '')  # Unique business identifier
                            company_name = company.get('company_name', '') or company.get('Company Name', '')
                            business_description = company.get('business_description', '') or company.get('Business Description', '')
                            company_number = company.get('company_number', '')
                            
                            # Validation: Ensure unique_id matches and we have company_id
                            if not company_id or fetched_unique_id != unique_id:
                                logger.warning(f"⚠️ Incomplete company identification - ID: {company_id}, Unique ID: {unique_id}")
                        else:
                            return jsonify({'error': f'Company not found with unique_id: {unique_id}'}), 400
                    else:
                        # Fallback to direct database access with unique_id lookup
                        db_connection = DatabaseConnection()
                        with db_connection.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT c.id, c.unique_id, c.company_name, c.business_description, c.company_number,
                                       csc.uk_sic_2007_code, COALESCE(sph.existing_sic_confidence, 0) as existing_sic_confidence
                                FROM companies c
                                LEFT JOIN company_sic_codes csc ON c.id = csc.company_id AND csc.is_primary = 1
                                LEFT JOIN sic_prediction_history sph ON c.id = sph.company_id
                                WHERE c.unique_id = ?
                            """, (unique_id,))
                            row = cursor.fetchone()
                            if row:
                                company_id, unique_id, company_name, business_description, company_number, uk_sic_code, existing_conf = row
                                # Create company data dict for field mapping
                                company = {
                                    'id': company_id,
                                    'unique_id': unique_id,
                                    'company_name': company_name,
                                    'business_description': business_description,
                                    'company_number': company_number,
                                    'uk_sic_2007_code': uk_sic_code,
                                    'existing_sic_confidence': existing_conf
                                }
                            else:
                                return jsonify({'error': f'Company not found with unique_id: {unique_id}'}), 400
                except Exception as fallback_error:
                    logger.warning(f"⚠️ Agentic lookup failed, using fallback: {fallback_error}")
                    return jsonify({'error': f'Failed to load company data: {str(fallback_error)}'}), 400
            
            # Validate we have minimum required data
            if not company_name and not business_description:
                return jsonify({
                    'error': 'Either company_name or business_description must be provided',
                    'fallback_available': True,
                    'message': 'Use /api/predict_sic for traditional prediction method'
                }), 400
            
            # 🔒 COMPANY VALIDATION: Only allow predictions for registered companies
            if company_name and not unique_id:  # Skip validation for unique_id lookups
                db_connection = DatabaseConnection()
                with db_connection.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id FROM companies 
                        WHERE company_name = ? OR UPPER(TRIM(company_name)) = UPPER(TRIM(?))
                        LIMIT 1
                    """, (company_name, company_name))
                    
                    company_exists = cursor.fetchone()
                    if not company_exists:
                        return jsonify({
                            'error': f'Company "{company_name}" not found in registered companies database',
                            'message': 'Only predictions for registered companies are allowed to maintain data integrity',
                            'suggestion': 'Check company name spelling or use unique_id for existing companies'
                        }), 400
                    
                    logger.info(f"✅ Company validation passed for '{company_name}'")
            
            # 🤖 EXECUTE AGENTIC WORKFLOW - PRIMARY SYSTEM
            # Check if agentic service is available
            if not (hasattr(app, 'agentic_sic_service') and app.agentic_sic_service):
                return jsonify({
                    'success': False,
                    'error': 'Agentic SIC service not initialized',
                    'message': 'Please ensure agentic components are properly configured'
                }), 500
            
            logger.info("🤖 Executing AGENTIC SIC prediction workflow")
            
            # Execute the advanced 5-agent workflow with dual-key validation
            workflow_config = request.json.get('workflow_config', {})
            if company_id and unique_id:
                # Add dual-key validation to workflow config for existing companies
                workflow_config.update({
                    'company_id': company_id,
                    'unique_id': unique_id,
                    'validation_mode': 'dual_key'
                })
                logger.info(f"🔑 Using dual-key validation: ID={company_id}, Unique={unique_id}")
            
            result = app.agentic_sic_service.predict_sic_agentic(
                company_name=company_name,
                business_description=business_description,
                company_number=company_number,
                address=address,
                workflow_config=workflow_config
            )
            
            # 🔍 DEBUG: Log result structure before building response
            logger.info(f"🔍 FLASK DEBUG: Result keys from agentic service: {list(result.keys()) if result else 'None'}")
            logger.info(f"🔍 FLASK DEBUG: Has ai_reasoning_explanation? {result.get('ai_reasoning_explanation', 'MISSING')}")
            
            # Get current SIC and existing SIC confidence from agentic service result
            current_sic = result.get('current_sic')
            existing_sic_confidence = result.get('existing_sic_confidence')
            
            logger.info(f"🔍 FLASK DEBUG: Using agentic service result - current_sic: '{current_sic}', existing_sic_confidence: {existing_sic_confidence}")
            
            # Extract Companies House SIC codes from validation data for API response
            companies_house_validation = result.get('companies_house_validation', {})
            ch_sic_codes = None
            if companies_house_validation.get('success', False):
                ch_sic_codes = companies_house_validation.get('sic_codes', [])
                logger.info(f"✅ CH SIC codes extracted for API response: {ch_sic_codes}")
            else:
                logger.info("⚠️ No CH SIC codes available from workflow")
            
            # Return agentic workflow results including Companies House validation data and current SIC info
            return jsonify({
                'success': True,
                'workflow_type': 'AGENTIC_MULTI_AGENT',
                'company_name': company_name,
                'predicted_sic_code': result.get('predicted_sic_code'),
                'confidence_score': result.get('confidence_score', 0.0),
                'current_sic': current_sic,  # Include current/existing SIC code
                'existing_sic_confidence': existing_sic_confidence,  # Include existing SIC confidence
                # 🎯 CONFIDENCE DISPLAY FIX: Add old_accuracy field for frontend compatibility
                'old_accuracy': f"{existing_sic_confidence:.1f}%" if existing_sic_confidence is not None else "0.0%",
                'new_accuracy': f"{result.get('confidence_score', 0.0) * 100:.1f}%",  # Format for frontend display (convert decimal to percentage)
                'reasoning': result.get('reasoning', ''),
                'workflow_steps': result.get('workflow_steps', []),
                'agent_decisions': result.get('agent_decisions', []),
                'execution_time_ms': result.get('execution_time_ms', 0),
                'nodes_executed': result.get('nodes_executed', []),
                'validation_results': result.get('validation_results', {}),
                'companies_house_validation': result.get('companies_house_validation', {}),  # Include CH data
                'ch_sic_codes': ch_sic_codes,  # 🔧 FIX: Extract CH SIC codes for client response
                'workflow_config': workflow_config,  # Include dual-key validation config
                # Dashboard reasoning fields for UI display
                'ai_reasoning_explanation': result.get('ai_reasoning_explanation', ''),
                'ch_comparison_explanation': result.get('ch_comparison_explanation', ''),
                'message': f'🤖 Agentic AI prediction completed for {company_name}'
            })

        
        except Exception as e:
            logger.error(f"❌ Agentic endpoint error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'fallback_available': True,
                'message': 'Use /api/predict_sic for traditional prediction method'
            }), 500

    @app.route('/api/update_revenue', methods=['POST'])
    @validate_api_input(validate_update_revenue_input)
    def update_revenue(validated_data):
        """Update revenue for a company"""
        try:
            company_name = validated_data['company_name']
            new_revenue = validated_data['revenue']
            company_number = validated_data.get('company_number')  # Optional
                
            # Use database instead of app.company_data
            db_connection = DatabaseConnection()
            
            # Get company by name (proper lookup instead of OFFSET)
            companies = db_connection.execute_query("""
                SELECT c.*, cf.sales_gbp 
                FROM companies c 
                LEFT JOIN company_financials cf ON c.id = cf.company_id 
                WHERE c.company_name = ?
            """, (company_name,))
            
            if not companies:
                return jsonify({'error': 'Invalid company index'}), 400
                
            company = dict(companies[0])
            company_name = company.get('company_name', 'Unknown')
            company_id = company['id']
            
            # Only allow simulation in demo mode for auto-generation
            # But allow manual updates in both modes
            if not is_demo_mode():
                # In production mode, use the provided revenue value directly
                pass
            else:
                # In demo mode, we can still use the provided value but add some simulation logging
                simulation_service.simulate_workflow_processing(0.3, 1.0)
            
            # Update or insert the company financial data in database
            existing_financials = db_connection.execute_query("""
                SELECT id FROM company_financials WHERE company_id = ?
            """, (company_id,))
            
            if existing_financials:
                # Update existing record
                db_connection.execute_update("""
                    UPDATE company_financials 
                    SET sales_gbp = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE company_id = ?
                """, (new_revenue, company_id))
            else:
                # Insert new financial record
                db_connection.execute_update("""
                    INSERT INTO company_financials (company_id, sales_gbp, created_at, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (company_id, new_revenue))
            
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

    @app.route('/api/modular/update-revenue-agentic', methods=['POST'])
    def update_revenue_agentic():
        """Update revenue using agentic workflow"""
        try:
            # Validate request data manually for agentic workflow
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Validate required fields for agentic workflow
            if 'company_name' not in data:
                return jsonify({'error': 'company_name is required'}), 400
            
            company_name = data['company_name'].strip()
            company_number = data.get('company_number', '').strip() if data.get('company_number') else None
            transaction_id = data.get('transaction_id', '').strip() if data.get('transaction_id') else None
            
            if not company_name:
                return jsonify({'error': 'company_name cannot be empty'}), 400
            
            if not DEPENDENCY_INJECTION_AVAILABLE:
                return jsonify({'error': 'Dependency injection not available'}), 500
            
            # Get update revenue service from DI container
            try:
                update_revenue_service = get_update_revenue_service()
                
                logger.info(f"🚀 Revenue agentic request: company={company_name!r}, number={company_number!r}, transaction_id={transaction_id!r}")
                
                # Execute agentic workflow (synchronous call) - EXTRACT ONLY, DON'T SAVE
                result = update_revenue_service.update_revenue_agentic(
                    company_name=company_name,
                    company_number=company_number,
                    transaction_id=transaction_id or ''
                )
                
                # Sanitize result for JSON serialization
                def sanitize_for_json(obj):
                    """Convert all problematic types to native Python types for JSON serialization."""
                    import numpy as np
                    
                    # Handle all boolean types
                    if isinstance(obj, bool):
                        return bool(obj)  # Ensure it's native Python bool
                    elif str(type(obj)) in ['<class \'numpy.bool_\'>', '<class \'numpy.bool8\'>']:
                        return bool(obj)
                    
                    # Handle numpy numeric types
                    elif isinstance(obj, (np.bool_, np.integer, np.floating, np.complexfloating)):
                        return obj.item()
                    elif str(type(obj)).startswith("<class 'numpy"):
                        # Catch any other numpy types
                        return obj.item() if hasattr(obj, 'item') else str(obj)
                    elif hasattr(obj, 'dtype'):
                        # Additional catch for objects with dtype
                        return obj.item() if hasattr(obj, 'item') else str(obj)
                    
                    # Handle collections
                    elif isinstance(obj, dict):
                        return {sanitize_for_json(k): sanitize_for_json(v) for k, v in obj.items()}
                    elif isinstance(obj, (list, tuple)):
                        return [sanitize_for_json(item) for item in obj]
                    
                    # Default: return as-is
                    else:
                        return obj
                
                sanitized_result = sanitize_for_json(result)
                
                # Debug: Test if sanitized result is JSON serializable
                try:
                    import json
                    json.dumps(sanitized_result)
                    print("✅ DEBUG: Sanitized result is JSON serializable")
                except Exception as debug_e:
                    print(f"❌ DEBUG: Sanitized result is NOT JSON serializable: {debug_e}")
                    print(f"❌ DEBUG: Error type: {type(debug_e)}")
                    # Return a simple error response instead
                    return jsonify({'error': f'JSON serialization error: {str(debug_e)}'}), 500
                
                # Use custom JSON encoder to handle any remaining numpy types
                from flask import make_response
                response_json = json.dumps(sanitized_result, cls=NumpyJSONEncoder)
                return make_response(response_json, 200, {'Content-Type': 'application/json'})
                
            except ImportError as e:
                # UpdateRevenueService not available, return helpful error
                return jsonify({
                    'error': 'Agentic revenue service not available',
                    'details': str(e),
                    'message': 'Please ensure all agentic components are properly installed'
                }), 503
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/modular/revenue-progress/<company_number>', methods=['GET'])
    def revenue_progress(company_number):
        """Poll for real-time progress of an in-flight revenue agentic workflow."""
        import json as _json, os as _os, re as _re
        safe = _re.sub(r'[^A-Za-z0-9_-]', '_', company_number or 'unknown')
        path = f'/tmp/revenue_progress_{safe}.json'
        try:
            with open(path) as _f:
                data = _json.load(_f)
            return jsonify(data), 200
        except FileNotFoundError:
            return jsonify({'node': 'waiting', 'step': 0, 'message': 'Waiting for workflow to start...', 'percentage': 0}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/modular/get-exchange-rate', methods=['GET'])
    def get_exchange_rate():
        """Returns 1.0 — sales values are already stored in GBP (converted offline)."""
        from datetime import datetime
        return jsonify({
            'rate': 1.0,
            'source': 'pre_converted',
            'message': 'Values already stored in GBP — no conversion needed',
            'timestamp': datetime.now().isoformat()
        }), 200

    @app.route('/api/modular/approve-revenue-updates', methods=['POST'])
    def approve_revenue_updates():
        """Approve and save revenue updates to the company_financials table"""
        try:
            # Validate request data
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Required fields
            required_fields = ['company_id', 'latest_revenue', 'latest_profit', 
                             'revenue_year', 'period_type', 'extraction_confidence']
            
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Extract and validate data
            company_id = data['company_id']
            latest_revenue = float(data['latest_revenue'])
            latest_profit = float(data['latest_profit'])
            revenue_year = int(data['revenue_year'])
            period_type = data['period_type']
            extraction_confidence = float(data['extraction_confidence'])
            extraction_date = data.get('extraction_date', datetime.now().isoformat())
            
            # Validate period_type
            if period_type not in ['Annual', 'Interim']:
                return jsonify({'error': 'Invalid period_type. Must be "Annual" or "Interim"'}), 400
            
            # Get database connection
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')
            
            # Update the company_financials table
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check if company exists in company_financials table
                cursor.execute("""
                    SELECT COUNT(*) FROM company_financials WHERE company_id = ?
                """, (company_id,))
                
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    # Update existing record
                    cursor.execute("""
                        UPDATE company_financials 
                        SET latest_revenue = ?, 
                            latest_profit = ?, 
                            revenue_year = ?, 
                            period_type = ?, 
                            extraction_confidence = ?, 
                            extraction_date = ?
                        WHERE company_id = ?
                    """, (latest_revenue, latest_profit, revenue_year, period_type, 
                         extraction_confidence, extraction_date, company_id))
                else:
                    # Insert new record - we need to provide defaults for required fields
                    cursor.execute("""
                        INSERT INTO company_financials 
                        (company_id, latest_revenue, latest_profit, revenue_year, 
                         period_type, extraction_confidence, extraction_date,
                         sales_gbp, cost_usd, net_profit_usd, profit_margin_percent)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)
                    """, (company_id, latest_revenue, latest_profit, revenue_year, 
                         period_type, extraction_confidence, extraction_date))
                
                conn.commit()
                rows_affected = cursor.rowcount
                
                logger.info(f"✅ Revenue updates approved for company_id {company_id}: "
                           f"£{latest_revenue:,.0f} revenue, £{latest_profit:,.0f} profit "
                           f"({period_type} {revenue_year}, confidence: {extraction_confidence:.1%})")
                
                return jsonify({
                    'success': True,
                    'message': 'Revenue updates saved successfully',
                    'company_id': company_id,
                    'rows_affected': rows_affected,
                    'data': {
                        'latest_revenue': latest_revenue,
                        'latest_profit': latest_profit,
                        'revenue_year': revenue_year,
                        'period_type': period_type,
                        'extraction_confidence': extraction_confidence,
                        'extraction_date': extraction_date
                    }
                })
                
        except ValueError as e:
            return jsonify({'error': f'Invalid data type: {str(e)}'}), 400
        except sqlite3.Error as e:
            logger.error(f"❌ Database error in approve_revenue_updates: {str(e)}")
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        except Exception as e:
            logger.error(f"❌ Error in approve_revenue_updates: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/modular/approve-sic-prediction', methods=['POST'])
    @validate_api_input(validate_approve_sic_prediction_input)
    def approve_sic_prediction_modular(validated_data):
        """Approve and save a SIC prediction to database using unique_id or company_id (modular approach)"""
        import json
        try:
            # Use validated data instead of raw request
            unique_id = validated_data.get('unique_id')
            company_id = validated_data.get('company_id')
            predicted_sic = str(validated_data['predicted_sic'])  # 🔧 FIX: Ensure predicted_sic is always a string
            confidence = validated_data['confidence']
            workflow_type = validated_data.get('workflow_type', 'modular')  # Default to 'modular'
            
            # Extract Companies House SIC data if provided
            ch_sic_codes_list = validated_data.get('ch_sic_codes', [])
            # 🔧 FIX: Ensure all SIC codes in the list are strings for type consistency
            if ch_sic_codes_list:
                ch_sic_codes_list = [str(code) for code in ch_sic_codes_list]
            ch_sic_description = validated_data.get('ch_sic_description', '')
            
            # 🔧 FIX: If CH codes not provided in request, retrieve from existing agentic prediction
            logger.info(f"🔍 CH RETRIEVAL DEBUG: ch_sic_codes_list={ch_sic_codes_list}, ch_sic_description='{ch_sic_description}'")
            if not ch_sic_codes_list or ch_sic_description.strip() == '':
                logger.info(f"🔍 CH RETRIEVAL: Attempting to retrieve CH codes from database for company {unique_id or company_id}")
                try:
                    # Use the correct database path
                    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')
                    db_connection = DatabaseConnection(db_path)
                    
                    with db_connection.get_connection() as conn:
                        cursor = conn.cursor()
                        
                        # Get the most recent prediction with CH data for this company (agentic or any method)
                        # 🔧 FIX: Handle unique_id and company_id separately for SQL query
                        uid_param = unique_id if unique_id else None
                        cid_param = str(company_id) if company_id else None
                        cursor.execute("""
                            SELECT ch_sic_codes, ch_sic_description 
                            FROM sic_prediction_history 
                            WHERE (unique_id = ? OR company_id = ?) 
                            AND (ch_sic_codes IS NOT NULL AND ch_sic_codes != '')
                            ORDER BY prediction_timestamp DESC
                            LIMIT 1
                        """, (uid_param, cid_param))
                        
                        ch_result = cursor.fetchone()
                        if ch_result:
                            existing_ch_codes, existing_ch_description = ch_result
                            if existing_ch_codes and not ch_sic_codes_list:
                                # Parse existing CH codes from JSON string
                                try:
                                    parsed_codes = json.loads(existing_ch_codes) if existing_ch_codes else []
                                    # Ensure all codes are strings
                                    ch_sic_codes_list = [str(code) for code in parsed_codes]
                                except json.JSONDecodeError:
                                    # Handle legacy single code format
                                    ch_sic_codes_list = [str(existing_ch_codes)] if existing_ch_codes else []
                                logger.info(f"✅ Retrieved CH codes from agentic prediction: {ch_sic_codes_list}")
                            
                            if existing_ch_description and not ch_sic_description:
                                ch_sic_description = existing_ch_description
                                logger.info(f"✅ Retrieved CH description from agentic prediction: {ch_sic_description}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not retrieve CH codes from agentic prediction: {e}")
                    # Continue with empty values - not a critical failure
            
            # Check for exact match with Companies House SIC codes and boost confidence to 100%
            # Both predicted_sic and ch_sic_codes_list are now guaranteed to be strings
            if ch_sic_codes_list and predicted_sic in ch_sic_codes_list:
                logger.info(f"🎯 EXACT MATCH: Predicted SIC {predicted_sic} matches CH SIC codes {ch_sic_codes_list} - boosting confidence to 100%")
                confidence = 100.0
            
            # Convert ch_sic_codes to single string format (matching agentic flow)
            # Use the first SIC code as a single string, not JSON array
            ch_sic_codes = str(ch_sic_codes_list[0]).strip() if ch_sic_codes_list else ''
            
            # Convert confidence from decimal (0.90) to percentage (90.0) if needed
            if confidence <= 1.0:
                confidence = confidence * 100
            confidence = round(confidence, 1)
            
            # Get company data using robust identifier lookup (supports both unique_id and company_id)
            
            # Use the correct database path
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credit_risk.db')
            db_connection = DatabaseConnection(db_path)
            repo = SQLiteSICPredictionRepository(db_connection)
            
            # Use robust lookup - try unique_id first, then company_id as fallback
            identifier = unique_id if unique_id else str(company_id)
            company = repo._get_company_by_identifier(identifier)
            
            if not company:
                identifier_type = "unique_id" if unique_id else "company_id"
                return jsonify({'error': f'Company not found with {identifier_type}: {identifier}'}), 404
            
            # Extract company data
            company_name = company.get('company_name', 'Unknown')  # Use database field name
            business_description = company.get('business_description', '')  # Use database field name
            current_sic = company.get('uk_sic_2007_code', '')
            
            logger.info(f"🔍 Approving SIC for {company_name} (unique_id: {unique_id}): {predicted_sic} with {confidence}% confidence")
            
            # Check if EnhancedSICMatcher is available
            if not ENHANCED_SIC_MATCHER_AVAILABLE:
                return jsonify({'error': 'Enhanced SIC matcher not available - check rapidfuzz dependency'}), 500
            
            # Create enhanced SIC matcher instance for database operations
            config = get_credit_risk_config()
            sic_matcher = EnhancedSICMatcher(config)
            
            # Get predicted SIC description
            predicted_sic_description = sic_matcher.get_sic_description(predicted_sic)
            
            # For modular approach, we'll use a simplified approval process
            # Generate AI reasoning explanation for the company detail modal
            try:
                logger.info(f"🔍 Generating AI reasoning for: business_description='{business_description[:50] if business_description else 'None'}...', predicted_sic='{predicted_sic}', confidence={confidence}")
                ai_reasoning = sic_matcher.generate_ai_reasoning(
                    business_description=business_description,
                    predicted_sic_code=predicted_sic,
                    predicted_sic_description=predicted_sic_description,
                    confidence_score=confidence,
                    company_name=company_name,
                    current_sic=current_sic
                )
                logger.info(f"🤖 Generated AI reasoning (length={len(ai_reasoning)}): {ai_reasoning[:100]}...")
            except Exception as e:
                logger.error(f"❌ Error generating AI reasoning: {e}")
                ai_reasoning = f"AI reasoning generation failed: {str(e)}"
            
            # Approve prediction should NOT recalculate existing SIC confidence
            # Use the stored database value to preserve the original "Old" confidence
            existing_sic_confidence = company.get('existing_sic_confidence')  # Use actual stored confidence
            
            # Save the approved prediction to database with CH codes as single string
            # Now we pass CH codes in single string format (matching agentic flow)
            company_id = company.get('id') or company.get('company_id') or unique_id
            success = sic_matcher.save_prediction_to_db(
                company_id=company_id,
                company_name=company_name,
                business_description=business_description,
                predicted_sic_code=predicted_sic,
                predicted_sic_description=predicted_sic_description,
                confidence_score=confidence,
                existing_sic_confidence=existing_sic_confidence,
                model_version=config.model_version,
                prediction_method=f"MODULAR_APPROVED_{workflow_type}",
                ai_reasoning=ai_reasoning,
                ch_sic_codes=ch_sic_codes,  # Now saving as single string (e.g., "52290")
                ch_sic_description=ch_sic_description
            )
            
            if success:
                logger.info(f"✅ Approved prediction saved for {company_name}: {predicted_sic} ({predicted_sic_description})")
                
                return jsonify({
                    'success': True,
                    'message': f'SIC prediction approved and saved for {company_name}',
                    'predicted_sic': predicted_sic,
                    'predicted_description': predicted_sic_description,
                    'confidence': confidence,
                    'method': f"MODULAR_APPROVED_{workflow_type}",
                    'ai_reasoning': ai_reasoning,
                    'company_name': company_name,
                    'unique_id': unique_id,
                    'ch_sic_codes': ch_sic_codes_list,  # Include CH SIC codes for frontend display
                    'ch_sic_description': ch_sic_description  # Include CH SIC description for frontend display
                })
            else:
                return jsonify({'error': 'Failed to save approved prediction to database'}), 500
                
        except Exception as e:
            logger.error(f"❌ Error approving modular SIC prediction: {e}")
            return jsonify({'error': str(e)}), 500



    # [DEPRECATED ROUTE] /api/run_agent_workflow — already returns HTTP 410 Gone internally.
    # Comment in code says "Traditional multi-agent orchestrator removed". No frontend consumer. Safe to remove.
    @app.route('/api/run_agent_workflow', methods=['POST'])
    @validate_api_input(validate_run_agent_workflow_input)
    def run_agent_workflow(validated_data):
        """Run the complete multi-agent workflow for real processing"""
        try:
            # Get input parameters from validated data
            company_numbers = validated_data.get('company_numbers', [])
            search_queries = validated_data.get('search_queries', [])
            include_filing_history = validated_data.get('include_filing_history', False)
            
            # If no specific companies provided, process a sample from database
            if not company_numbers and not search_queries:
                db_connection = DatabaseConnection()
                sample_companies = db_connection.execute_query("""
                    SELECT registration_number FROM companies 
                    WHERE registration_number IS NOT NULL 
                    LIMIT 10
                """)
                if sample_companies:
                    company_numbers = [comp['registration_number'] for comp in sample_companies]
                else:
                    return jsonify({'error': 'No company data available'}), 400
            
            # Prepare input for orchestrator
            workflow_input = {
                'company_numbers': company_numbers,
                'search_queries': search_queries, 
                'include_filing_history': include_filing_history
            }
            
            logger.info(f"Starting real agent workflow with input: {workflow_input}")
            
            # TODO: Replace with pure agentic workflow execution
            # Traditional multi-agent orchestrator removed - use agentic SIC service instead
            return jsonify({
                'error': 'Traditional agent workflow deprecated - use agentic endpoints instead',
                'message': 'Please use /api/predict_sic_agentic for modern agentic SIC prediction',
                'workflow_input': workflow_input
            }), 410  # 410 Gone - endpoint deprecated
            
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

    # [DEBUG ROUTE] /api/test_agents — development/debug endpoint. Tests agentic service availability.
    # Not needed in production. No frontend consumer. Safe to remove.
    @app.route('/api/test_agents', methods=['GET'])
    def test_agent_integration():
        """Test route to verify agent integration is working"""
        try:
            # Test agentic services (pure agentic system)
            agentic_sic_status = "✅ Available" if hasattr(app, 'agentic_sic_service') else "❌ Not available"
            
            # Test enhanced SIC matcher
            sic_matcher_status = "✅ Available" if hasattr(app, 'sic_matcher') else "❌ Not available"
            
            # Traditional agents removed in pure agentic system
            
            # Test with sample data using agentic system
            test_result = None
            if hasattr(app, 'agentic_sic_service') and app.agentic_sic_service:
                try:
                    # Test agentic SIC prediction service instead of legacy sector agent
                    agentic_test = app.agentic_sic_service.predict_sic_agentic(
                        company_name='Test Catering Company',
                        business_description='Food catering and event services',
                        company_number='TEST001',
                        address=''
                    )
                    if agentic_test.get('predicted_sic_code'):
                        test_result = "✅ Agentic SIC service working - Sample prediction successful"
                    else:
                        test_result = f"⚠️ Agentic SIC service failed: {agentic_test.get('error', 'Unknown error')}"
                except Exception as e:
                    test_result = f"❌ Agentic SIC service test failed: {str(e)}"
            else:
                test_result = "❌ Agentic SIC service not available"
            
            return jsonify({
                'agentic_system_status': {
                    'agentic_sic_service': agentic_sic_status,
                    'sic_matcher': sic_matcher_status,
                    'system_type': 'pure_agentic',
                    'test_result': test_result
                },
                'available_routes': [
                    '/api/predict-sic - Pure agentic SIC prediction',
                    '/api/companies - Company listing and search',
                    '/api/sic-codes - SIC code management'
                ],
                'usage_instructions': {
                    'agentic_sic_prediction': 'POST to /api/predict_sic_agentic with {"unique_id": "RK86750341"} or {"company_name": "SHELL PLC"}',
                    'company_search': 'GET /api/companies with optional filters'
                }
            })
            
        except Exception as e:
            return jsonify({'error': f'Agent test failed: {str(e)}'}), 500

    # Load data when app starts
    verify_database_connection()
    
    # =====================================================================
    # MODULAR ARCHITECTURE ENHANCEMENTS (Added to existing Flask app)
    # =====================================================================
    
    # Try to import modular architecture components
    try:
        from app_modules.infrastructure.di.container import get_container, get_company_service
        MODULAR_AVAILABLE = True
        logger.info("✅ Modular architecture components available")
    except ImportError as e:
        MODULAR_AVAILABLE = False
        logger.info(f"ℹ️  Modular components not available: {e}")
        logger.info("   Your existing app works normally")
    
    # Workflow API endpoints for existing_workflows.html
    @app.route('/api/modular/workflows', methods=['GET'])
    def get_workflows():
        """Get all available agentic workflows"""
        try:
            # Pure agentic system workflows
            workflows = [{
                "id": "agentic_sic_prediction",
                "name": "Agentic SIC Code Prediction",
                "description": "Pure agentic multi-agent SIC code prediction with LangGraph coordination",
                "status": "operational",
                "type": "langgraph_workflow"
            }]
            return jsonify(workflows)
        except Exception as e:
            logger.error(f"Error loading agentic workflows: {e}")
            return jsonify({'error': 'Failed to load agentic workflows'}), 500

    @app.route('/api/modular/workflows/<workflow_id>', methods=['GET'])
    def get_workflow(workflow_id):
        """Get agentic workflow details"""
        try:
            if workflow_id == "agentic_sic_prediction":
                return jsonify({
                    "id": "agentic_sic_prediction",
                    "name": "Agentic SIC Prediction",
                    "description": "LangGraph-coordinated multi-agent SIC code prediction",
                    "agents": ["data_collection", "data_enrichment", "sic_prediction", "confidence_scoring", "result_validation"],
                    "connections": ["sequential_with_validation"],
                    "status": "operational"
                })
            else:
                return jsonify({'error': 'Workflow not found'}), 404
        except Exception as e:
            logger.error(f"Error loading agentic workflow {workflow_id}: {e}")
            return jsonify({'error': 'Failed to load agentic workflow'}), 500

    @app.route('/api/modular/workflow/agents', methods=['GET'])
    def get_workflow_agents():
        """Get agentic workflow agents"""
        try:
            workflow_id = request.args.get('workflow_id', 'agentic_sic_prediction')
            if workflow_id == 'agentic_sic_prediction':
                agents = [
                    {
                        "id": "data_collection_agent",
                        "name": "Data Collection Agent",
                        "type": "data_collection",
                        "status": "operational",
                        "description": "Collects company data from multiple sources"
                    },
                    {
                        "id": "data_enrichment_agent",
                        "name": "Data Enrichment Agent", 
                        "type": "data_enrichment",
                        "status": "operational",
                        "description": "Enriches data with external APIs"
                    },
                    {
                        "id": "sic_prediction_agent",
                        "name": "SIC Prediction Agent",
                        "type": "classification",
                        "status": "operational", 
                        "description": "Predicts SIC codes using ML models"
                    },
                    {
                        "id": "confidence_scoring_agent",
                        "name": "Confidence Scoring Agent",
                        "type": "scoring",
                        "status": "operational",
                        "description": "Scores prediction confidence"
                    },
                    {
                        "id": "result_validation_agent",
                        "name": "Result Validation Agent",
                        "type": "validation",
                        "status": "operational",
                        "description": "Validates and formats final results"
                    }
                ]
                connections = ["sequential_langgraph_workflow"]
                return jsonify({"agents": agents, "connections": connections})
            else:
                return jsonify({'error': 'Agentic workflow not found'}), 404
        except Exception as e:
            logger.error(f"Error loading agentic workflow agents: {e}")
            return jsonify({'error': 'Failed to load agentic workflow agents'}), 500

    @app.route('/api/modular/workflow/execute', methods=['POST'])
    def execute_modular_workflow():
        """Execute agentic workflow for a specific agent step"""
        try:
            execution_data = request.get_json() or {}
            workflow_id = execution_data.get('workflow_id', 'agentic_sic_prediction')
            agent_id = execution_data.get('agent_id', '')
            agent_type = execution_data.get('agent_type', '')

            # company_name is required by AgenticSICPredictionService.predict_sic_agentic()
            # The workflow UI may call this without a company — return a friendly status
            company_name = execution_data.get('company_name', '').strip()
            business_description = execution_data.get('business_description', '').strip()

            if not company_name:
                # No company selected — return operational status instead of 500
                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'message': f'Agent {agent_id or agent_type} is operational. Select a company to run a live prediction.',
                    'workflow_id': workflow_id,
                    'agent_id': agent_id,
                    'requires_company': True
                })

            if workflow_id == 'agentic_sic_prediction' and hasattr(app, 'agentic_sic_service') and app.agentic_sic_service:
                result = app.agentic_sic_service.predict_sic_agentic(
                    company_name=company_name,
                    business_description=business_description
                )
                logger.info(f"🤖 Executed agentic workflow for: {company_name}")
                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'workflow_id': workflow_id,
                    'company_name': company_name,
                    'prediction_result': result,
                    'message': f'Prediction complete for {company_name}'
                })
            else:
                return jsonify({'success': False, 'status': 'unavailable', 'error': 'Agentic workflow not available'}), 503

        except Exception as e:
            logger.error(f"Error executing agentic workflow: {e}")
            return jsonify({'success': False, 'error': f'Agentic workflow execution failed: {str(e)}'}), 500

    # Log the enhancement integration
    if MODULAR_AVAILABLE:
        logger.info("🚀 Modular architecture enhancements integrated successfully")
        logger.info("   Enhanced modular components available for development")
        logger.info("   Your existing endpoints: Fully preserved and functional")
    else:
        logger.info("ℹ️  Modular architecture components not available")
        logger.info("   Your existing Flask app works perfectly without them")

    if WORKFLOW_MANAGER_AVAILABLE:
        logger.info("🔄 Workflow API endpoints added")
        logger.info("   Workflow endpoints: /api/modular/workflows, /api/modular/workflow/agents, /api/modular/workflow/execute")

    # =====================================================================
    # SIC CONFIDENCE MANAGEMENT ENDPOINTS
    # =====================================================================
    
    @app.route('/api/calculate_sic_confidence', methods=['POST'])
    def calculate_sic_confidence_endpoint():
        """
        Calculate existing SIC confidence for companies
        
        Supports two modes:
        1. Single company: {"company_id": 123}
        2. Batch mode: {} (calculates for all companies needing confidence)
        """
        try:
            data = request.get_json() or {}
            company_id = data.get('company_id')
            
            # Check if service is available
            if not SIC_CONFIDENCE_SERVICE_AVAILABLE:
                return jsonify({
                    'success': False,
                    'error': 'SIC confidence service not available',
                    'message': 'Service initialization failed'
                }), 503
            
            # Import and initialize the service
            service = SICConfidenceService()
            
            if company_id:
                # Calculate for single company
                logger.info(f"📊 Calculating SIC confidence for company ID: {company_id}")
                result = service.calculate_for_company(company_id)
                
                if result['success']:
                    logger.info(f"✅ SIC confidence calculated: {result['existing_sic_confidence']:.1f}%")
                else:
                    logger.error(f"❌ SIC confidence calculation failed: {result['error']}")
                    
                return jsonify(result)
            else:
                # Calculate for all companies needing confidence
                logger.info("📊 Calculating SIC confidence for all companies needing it...")
                result = service.calculate_for_new_companies()
                
                if result['success']:
                    logger.info(f"✅ Batch confidence calculation completed: {result['success_count']}/{result['total']} companies")
                else:
                    logger.error(f"❌ Batch confidence calculation failed: {result['error']}")
                    
                return jsonify(result)
                
        except Exception as e:
            logger.error(f"❌ SIC confidence endpoint error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'SIC confidence calculation failed'
            }), 500

    @app.route('/api/add_company_with_sic', methods=['POST'])
    @validate_api_input(validate_add_company_with_sic_input)
    def add_company_with_sic_endpoint(validated_data):
        """
        Add a new company and automatically calculate existing SIC confidence
        
        Expected data:
        {
            "company_name": "New Company Ltd",
            "business_description": "Software development services", 
            "existing_sic_code": "62020",
            "existing_sic_description": "Computer programming activities",
            "company_number": "12345678" (optional)
        }
        """
        try:
            # Extract validated company data
            company_name = validated_data['company_name']
            business_description = validated_data['business_description']
            existing_sic_code = validated_data['existing_sic_code']
            existing_sic_description = validated_data.get('existing_sic_description', '')
            company_number = validated_data.get('company_number', '')
            
            logger.info(f"🏢 Adding new company with automatic SIC confidence: {company_name}")
            
            # Add company to database first
            db_connection = DatabaseConnection()
            
            # Generate unique_id for new company (outside the with block for scope)
            import random
            import string
            
            def generate_unique_id():
                """Generate a 10-digit alphanumeric unique ID"""
                # Format: 2 letters + 8 digits (e.g., AB12345678)
                letters = ''.join(random.choices(string.ascii_uppercase, k=2))
                numbers = ''.join(random.choices(string.digits, k=8))
                return f"{letters}{numbers}"
            
            # Generate unique_id and ensure it's not already used
            unique_id = None
            with db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                while True:
                    unique_id = generate_unique_id()
                    cursor.execute("SELECT COUNT(*) FROM companies WHERE unique_id = ?", (unique_id,))
                    if cursor.fetchone()[0] == 0:
                        break
                
                # Insert into companies table with unique_id
                cursor.execute("""
                    INSERT INTO companies (company_number, company_name, business_description, unique_id)
                    VALUES (?, ?, ?, ?)
                """, (company_number, company_name, business_description, unique_id))
                
                company_id = cursor.lastrowid
                
                # Validate company_id was created properly
                if not company_id:
                    raise Exception("Failed to get company ID after insert")
                
                # Insert into company_sic_codes table
                cursor.execute("""
                    INSERT INTO company_sic_codes (company_id, company_name, uk_sic_2007_code, uk_sic_2007_description, is_primary)
                    VALUES (?, ?, ?, ?, 1)
                """, (company_id, company_name, existing_sic_code, existing_sic_description))
                
                conn.commit()
                logger.info(f"✅ Company added to database with ID: {company_id}")
            
            # Automatically calculate existing SIC confidence
            service = SICConfidenceService()
            
            confidence_result = service.calculate_for_company(int(company_id))
            
            if confidence_result['success']:
                logger.info(f"✅ Automatic SIC confidence calculated: {confidence_result['existing_sic_confidence']:.1f}%")
                
                return jsonify({
                    'success': True,
                    'message': f'Company {company_name} added with automatic SIC confidence calculation',
                    'company_id': company_id,
                    'unique_id': unique_id,
                    'company_name': company_name,
                    'existing_sic_code': existing_sic_code,
                    'existing_sic_confidence': confidence_result['existing_sic_confidence'],
                    'existing_ai_reasoning': confidence_result.get('existing_ai_reasoning', 'AI reasoning not available'),
                    'existing_sic_confidence_category': confidence_result.get('existing_sic_confidence_category', 'Uncategorized'),
                    'existing_sic_calculation_timestamp': confidence_result.get('existing_sic_calculation_timestamp', 'No timestamp available'),
                    'confidence_calculation': 'automatic',
                    'workflow_steps': [
                        {'step': 1, 'status': 'completed', 'message': f'Added company: {company_name}'},
                        {'step': 2, 'status': 'completed', 'message': f'Added SIC code: {existing_sic_code}'},
                        {'step': 3, 'status': 'completed', 'message': f'Calculated confidence: {confidence_result["existing_sic_confidence"]:.1f}% ({confidence_result.get("existing_sic_confidence_category", "Uncategorized")})'},
                        {'step': 4, 'status': 'completed', 'message': 'Generated AI reasoning for SIC classification'},
                        {'step': 5, 'status': 'completed', 'message': 'Company ready for SIC predictions'}
                    ]
                })
            else:
                # Company added but confidence calculation failed
                logger.warning(f"⚠️ Company added but confidence calculation failed: {confidence_result['error']}")
                return jsonify({
                    'success': True,
                    'message': f'Company {company_name} added but confidence calculation failed',
                    'company_id': company_id,
                    'unique_id': unique_id,
                    'company_name': company_name,
                    'existing_sic_code': existing_sic_code,
                    'existing_sic_confidence': None,
                    'confidence_error': confidence_result['error'],
                    'note': 'You can manually run confidence calculation later'
                })
                
        except Exception as e:
            logger.error(f"❌ Add company with SIC endpoint error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Failed to add company with automatic SIC confidence'
            }), 500

    # === SIC Confidence Retrieval API Endpoints ===
    
    @app.route('/api/sic-confidence/existing/<int:company_id>', methods=['GET'])
    def get_existing_sic_confidence(company_id):
        """Get existing SIC confidence for a company"""
        try:
            logger.info(f"🔍 Getting existing SIC confidence for company {company_id}")

            if not SIC_CONFIDENCE_SERVICE_AVAILABLE:
                return jsonify({'success': False, 'error': 'SIC confidence service not available', 'company_id': company_id}), 503

            service = SICConfidenceService()
            result = service.calculate_for_company(company_id)
            
            if result and result.get('success', False):
                logger.info(f"✅ Retrieved SIC confidence: {result.get('existing_sic_confidence', 0):.1f}%")
                return jsonify(result)
            else:
                logger.warning(f"⚠️ No SIC confidence data found for company {company_id}")
                return jsonify({
                    'success': False,
                    'error': 'No SIC confidence data found',
                    'company_id': company_id
                }), 404
                
        except Exception as e:
            logger.error(f"❌ Get existing SIC confidence error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'company_id': company_id
            }), 500
    
    @app.route('/api/sic-confidence/batch-calculate', methods=['POST'])
    def batch_calculate_sic_confidence():
        """Calculate SIC confidence for multiple companies"""
        try:
            logger.info("🔄 Starting batch SIC confidence calculation")

            if not SIC_CONFIDENCE_SERVICE_AVAILABLE:
                return jsonify({'success': False, 'error': 'SIC confidence service not available'}), 503

            service = SICConfidenceService()
            result = service.calculate_for_new_companies()
            
            logger.info(f"✅ Batch calculation completed: {result.get('processed', 0)} companies processed")
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ Batch SIC confidence calculation error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Failed to perform batch SIC confidence calculation'
            }), 500
    
    @app.route('/api/sic-confidence/stats', methods=['GET'])
    def get_sic_confidence_stats():
        """Get statistics about SIC confidence calculations"""
        try:
            import sqlite3
            logger.info("📊 Getting SIC confidence statistics")
            
            # Use app config to get database path
            db_file_path = app.config.get('DATABASE_PATH', 'data/credit_risk.db')
            
            with sqlite3.connect(db_file_path) as conn:
                cursor = conn.cursor()
                
                # Get confidence statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_companies,
                        COUNT(existing_sic_confidence) as companies_with_confidence,
                        AVG(existing_sic_confidence) as average_confidence,
                        MIN(existing_sic_confidence) as min_confidence,
                        MAX(existing_sic_confidence) as max_confidence
                    FROM sic_prediction_history
                """)
                
                row = cursor.fetchone()
                
                # Get confidence by category
                cursor.execute("""
                    SELECT 
                        existing_sic_confidence_category,
                        COUNT(*) as count
                    FROM sic_prediction_history
                    WHERE existing_sic_confidence_category IS NOT NULL
                    GROUP BY existing_sic_confidence_category
                    ORDER BY count DESC
                """)
                
                categories = cursor.fetchall()
                
                stats = {
                    'success': True,
                    'total_companies': row[0] if row else 0,
                    'companies_with_confidence': row[1] if row else 0,
                    'coverage_percentage': round((row[1] / row[0] * 100), 2) if row and row[0] > 0 else 0,
                    'average_confidence': round(row[2], 2) if row and row[2] else 0,
                    'min_confidence': row[3] if row else 0,
                    'max_confidence': row[4] if row else 0,
                    'confidence_categories': [
                        {'category': cat[0], 'count': cat[1]} 
                        for cat in categories
                    ]
                }
                
                logger.info(f"✅ SIC confidence stats: {stats['companies_with_confidence']}/{stats['total_companies']} companies")
                return jsonify(stats)
                
        except Exception as e:
            logger.error(f"❌ Get SIC confidence stats error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Failed to get SIC confidence statistics'
            }), 500

    # Log SIC confidence management endpoints
    logger.info("🎯 SIC Confidence Management endpoints added")
    logger.info("   /api/calculate_sic_confidence - Calculate existing SIC confidence")
    logger.info("   /api/add_company_with_sic - Add company with automatic confidence calculation")
    logger.info("   /api/sic-confidence/existing/<company_id> - Get existing SIC confidence")
    logger.info("   /api/sic-confidence/batch-calculate - Batch calculate SIC confidence")
    logger.info("   /api/sic-confidence/stats - Get SIC confidence statistics")
    
    return app

# Create app instance at module level for imports
app = create_app()

if __name__ == '__main__':
    # App is already created above
    
    # This code should only run when flask_main.py is executed directly
    # When imported by main.py, main.py handles the app.run()
    if __name__ == '__main__':
        # Use port 5001 to avoid AirPlay conflict on macOS
        port = 5001
        
        logger.info(f"Starting Enhanced Flask App on http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=True)