"""
STEP-BY-STEP INTEGRATION: Add modular architecture to your existing flask_main.py

This shows exactly where and how to add the modular enhancements to your current Flask app.
"""

# ================================================================================
# STEP 1: Add these imports to your existing flask_main.py (around line 45)
# ================================================================================

# Add after your existing imports, before the Flask app creation:

# Modular architecture imports (optional - won't break if missing)
try:
    from app.infrastructure.di.container import get_container, get_company_service
    from app.repositories.interfaces.company_repository_interface import CompanyRepositoryInterface
    MODULAR_AVAILABLE = True
    logger.info("✅ Modular architecture components available")
except ImportError as e:
    MODULAR_AVAILABLE = False
    logger.info(f"ℹ️  Modular architecture not available: {e}")
    logger.info("   Your existing app will work normally")


# ================================================================================
# STEP 2: Enhanced Flask app creation (replace your existing create_app function)
# ================================================================================

def create_app():
    """Enhanced Flask app creation with modular architecture integration"""
    
    # Your existing Flask app setup (UNCHANGED)
    app = Flask(__name__)
    
    # Your existing CORS setup (UNCHANGED) 
    if CORS_AVAILABLE:
        CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    # Your existing configuration (UNCHANGED)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    
    # NEW: Add modular architecture routes (optional enhancement)
    if MODULAR_AVAILABLE:
        try:
            register_modular_enhancements(app)
            logger.info("✅ Modular architecture routes registered")
        except Exception as e:
            logger.warning(f"Could not register modular routes: {e}")
    
    # Your existing routes registration (UNCHANGED)
    register_existing_routes(app)
    
    return app


def register_modular_enhancements(app):
    """Register enhanced routes that demonstrate modular architecture benefits"""
    
    @app.route('/api/v2/health')
    def enhanced_health_check():
        """Enhanced health check showing modular architecture status"""
        try:
            container = get_container()
            health_status = {
                'success': True,
                'modular_architecture': 'Available',
                'existing_components': 'Preserved and enhanced',
                'benefits': [
                    'Dependency injection for better management',
                    'Repository interfaces for clean data access', 
                    'Configuration-based environment switching',
                    'Better testing with mockable components'
                ]
            }
            
            # Test if repository is working
            try:
                company_service = get_company_service()
                health_status['company_service'] = 'Available'
                health_status['repository_type'] = type(company_service.company_repository).__name__
            except Exception as e:
                health_status['company_service'] = f'Error: {e}'
            
            return jsonify(health_status)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Modular architecture health check failed'
            }), 500
    
    @app.route('/api/v2/companies')
    def enhanced_companies():
        """Enhanced companies endpoint using modular architecture"""
        try:
            limit = request.args.get('limit', type=int)
            
            if MODULAR_AVAILABLE:
                # Use enhanced modular service
                company_service = get_company_service()
                result = company_service.get_companies_data(limit or 100)
                
                # Add enhancement metadata
                result['architecture'] = 'Enhanced with modular components'
                result['benefits'] = [
                    'Clean repository interface',
                    'Dependency injection',
                    'Environment configuration'
                ]
                
                return jsonify(result)
            else:
                # Fallback to existing logic
                return jsonify({
                    'success': False,
                    'message': 'Modular architecture not available, use /api/companies'
                })
                
        except Exception as e:
            logger.error(f"Enhanced companies endpoint failed: {e}")
            return jsonify({
                'success': False, 
                'error': str(e),
                'fallback': 'Use existing /api/companies endpoint'
            }), 500
    
    @app.route('/api/v2/architecture/demo')
    def architecture_demo():
        """Demo endpoint showing modular architecture integration"""
        try:
            demo_info = {
                'success': True,
                'message': 'Modular architecture successfully integrated with existing Flask app',
                
                'your_existing_app': {
                    'preserved': True,
                    'routes': '/api/companies, /api/predict-sic, etc. (unchanged)',
                    'agents': 'SectorClassificationAgent, MultiAgentOrchestrator (unchanged)',
                    'data_layer': 'DatabricksDataManager, CSV/Excel logic (unchanged)',
                    'ui': 'All frontend components and styling (unchanged)'
                },
                
                'modular_enhancements': {
                    'added': True,
                    'routes': '/api/v2/* endpoints (enhanced versions)',
                    'dependency_injection': 'Auto-wired components based on environment',
                    'repository_interfaces': 'Clean abstraction over your data layer',
                    'configuration': 'Environment-based component switching'
                },
                
                'integration_benefits': {
                    'existing_functionality': 'Fully preserved - no breaking changes',
                    'enhanced_management': 'Better component organization with DI',
                    'flexible_configuration': 'Easy switching between environments',
                    'testing_improvements': 'Mockable interfaces for better unit tests',
                    'future_ready': 'SQLite migration path when needed'
                },
                
                'how_it_works': [
                    '1. Your existing routes (/api/*) work exactly as before',
                    '2. Enhanced routes (/api/v2/*) show modular benefits',
                    '3. Same business logic, better architecture',
                    '4. Configuration switches between file/Databricks/SQLite'
                ]
            }
            
            return jsonify(demo_info)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


def register_existing_routes(app):
    """Register all your existing routes (UNCHANGED)"""
    
    # Your existing main route
    @app.route('/')
    def home():
        """Your existing home route - works exactly as before"""
        return render_template('index.html')
    
    # Your existing companies API
    @app.route('/api/companies')
    def get_companies():
        """Your existing companies endpoint - works exactly as before"""
        # ... your existing implementation stays unchanged ...
        pass
    
    # Your existing SIC prediction API  
    @app.route('/api/predict-sic', methods=['POST'])
    def predict_sic():
        """Your existing SIC prediction - works exactly as before"""
        # ... your existing implementation stays unchanged ...
        pass
    
    # All your other existing routes...
    # (They all work exactly as they did before)


# ================================================================================
# STEP 3: Environment configuration (optional)
# ================================================================================

def configure_modular_environment():
    """Configure modular architecture based on environment"""
    
    environment = os.getenv('FLASK_ENV', 'development')
    
    if environment == 'development':
        # Local development - use file-based repositories
        os.environ['DATABASE_TYPE'] = 'files'
        logger.info("🔧 Configured for local development (file-based repositories)")
        
    elif environment == 'production':
        # Production - use your existing Databricks
        os.environ['DATABASE_TYPE'] = 'databricks' 
        logger.info("🔧 Configured for production (Databricks repositories)")
    
    elif environment == 'testing':
        # Testing - use mock repositories
        os.environ['DATABASE_TYPE'] = 'mock'
        logger.info("🔧 Configured for testing (mock repositories)")


# ================================================================================
# STEP 4: Enhanced application startup
# ================================================================================

if __name__ == '__main__':
    # Configure modular architecture (optional)
    if MODULAR_AVAILABLE:
        configure_modular_environment()
    
    # Create enhanced Flask app
    app = create_app()
    
    # Your existing startup logic
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info("🚀 Starting Flask app with modular architecture enhancements")
    logger.info(f"   Existing routes: Fully preserved and functional")
    logger.info(f"   Enhanced routes: /api/v2/* (if modular components available)")
    logger.info(f"   Port: {port}, Debug: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)


# ================================================================================
# SUMMARY: What this integration does
# ================================================================================

"""
✅ INTEGRATION SUMMARY:

1. PRESERVES YOUR EXISTING APP:
   - All existing routes work unchanged: /, /api/companies, /api/predict-sic
   - All your agents work unchanged: SectorClassificationAgent, etc.
   - All your data layer works unchanged: DatabricksDataManager, CSV/Excel
   - All your UI works unchanged: templates, static files

2. ADDS MODULAR ENHANCEMENTS:
   - /api/v2/health - Enhanced health check
   - /api/v2/companies - Companies with modular architecture
   - /api/v2/architecture/demo - Integration demonstration
   - Dependency injection for better component management
   - Repository interfaces for clean data access

3. ENVIRONMENT CONFIGURATION:
   - FLASK_ENV=development → Use file-based repositories
   - FLASK_ENV=production → Use your existing Databricks
   - Easy switching without code changes

4. GRACEFUL DEGRADATION:
   - If modular components aren't available, existing app works normally
   - No breaking changes, only enhancements

5. BENEFITS:
   - Better component management with dependency injection
   - Clean repository interfaces for testing
   - Configuration-based environment switching
   - SQLite migration readiness for future

TO USE:
1. Copy the imports and functions above into your flask_main.py
2. Set FLASK_ENV environment variable
3. Run your app - existing functionality + enhanced /api/v2/ endpoints
"""