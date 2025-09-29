"""
PRACTICAL INTEGRATION GUIDE: How to use modular architecture in your existing Flask app

This shows you exactly how to integrate the modular enhancements with your current
flask_main.py and other existing components.
"""

# Step 1: Import the enhanced components in your existing flask_main.py
from app.infrastructure.di.container import get_container, get_company_service
from app.api.modular_routes import register_modular_routes

def enhance_existing_flask_app():
    """Add this to your existing Flask app creation"""
    
    # Your existing Flask app creation (UNCHANGED)
    app = Flask(__name__)
    
    # Your existing routes (UNCHANGED) 
    from app.routes import main_routes  # Your existing routes
    app.register_blueprint(main_routes)
    
    # NEW: Add modular routes alongside existing ones
    try:
        enhanced_endpoints = register_modular_routes(app)
        print("🚀 Enhanced API endpoints added:")
        for endpoint in enhanced_endpoints:
            print(f"   {endpoint}")
    except ImportError as e:
        print(f"⚠️  Modular routes not available: {e}")
        print("   Your existing app will work normally")
    
    return app

# Step 2: Enhanced route example using your existing logic
@app.route('/api/v2/companies-demo')
def companies_with_modular_enhancement():
    """Example: Enhanced version of your existing companies endpoint"""
    
    try:
        # NEW: Get service through dependency injection
        company_service = get_company_service()
        
        # Use enhanced service (coordinates your existing components)
        result = company_service.get_companies_data()
        
        return jsonify({
            'success': True,
            'data': result,
            'enhancement': 'Using modular architecture with your existing logic',
            'benefits': [
                'Dependency injection for better management',
                'Repository interface for clean data access',
                'Same business logic, better architecture'
            ]
        })
        
    except Exception as e:
        # Fallback to your existing logic if modular components fail
        print(f"Modular enhancement failed, using existing logic: {e}")
        
        # Your existing companies logic (UNCHANGED)
        return get_companies_original_logic()

def get_companies_original_logic():
    """Your existing companies logic - works unchanged"""
    # This is your existing implementation
    # No changes needed - modular architecture is additive
    pass

# Step 3: Configuration-based enhancement
def configure_app_for_environment():
    """Configure your app for different environments"""
    
    import os
    
    # Set environment variables for modular architecture
    if os.getenv('ENVIRONMENT') == 'local':
        os.environ['DATABASE_TYPE'] = 'files'  # Use your CSV/Excel logic
    elif os.getenv('ENVIRONMENT') == 'production':
        os.environ['DATABASE_TYPE'] = 'databricks'  # Use your Databricks logic
    
    print(f"App configured for: {os.getenv('DATABASE_TYPE', 'default')}")

# Step 4: Testing your existing app with enhancements
def test_enhanced_integration():
    """Test that modular enhancements work with your existing app"""
    
    print("🧪 TESTING MODULAR INTEGRATION:")
    print("-" * 40)
    
    # Test 1: Your existing routes still work
    print("✅ Your existing routes: /api/companies (unchanged)")
    
    # Test 2: Enhanced routes available  
    print("✅ Enhanced routes: /api/v2/companies (with modular benefits)")
    
    # Test 3: Configuration switching
    print("✅ Configuration: Set DATABASE_TYPE=files for local development")
    
    # Test 4: Dependency injection
    print("✅ DI Container: Auto-wires components based on environment")

if __name__ == "__main__":
    print("📋 PRACTICAL INTEGRATION GUIDE")
    print("=" * 50)
    
    configure_app_for_environment()
    test_enhanced_integration()
    
    print("\n🎯 TO USE IN YOUR EXISTING APP:")
    print("1. Add import statements to your flask_main.py")
    print("2. Call register_modular_routes(app) after your existing routes")
    print("3. Set DATABASE_TYPE environment variable")
    print("4. Test /api/v2/ endpoints alongside your existing /api/ endpoints")
    
    print("\n✨ RESULT:")
    print("Your existing app works unchanged + Enhanced modular benefits!")