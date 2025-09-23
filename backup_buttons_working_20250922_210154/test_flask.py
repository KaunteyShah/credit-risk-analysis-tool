#!/usr/bin/env python3
"""
Simple test for the Flask app to verify it works
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from flask_app import create_app
    
    print("✅ Flask app imports successfully!")
    
    app = create_app()
    print("✅ Flask app created successfully!")
    
    # Test if we can start the app
    if __name__ == "__main__":
        print("🌐 Starting Flask application on http://localhost:5000...")
        app.run(host='0.0.0.0', port=5000, debug=True)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()