"""
ERROR: This script should NOT be running!
Azure should be executing app/flask_main.py instead.
"""

import os
from flask import Flask, jsonify

print("🚨 ERROR: minimal_startup.py is still being executed!")
print("🚨 Azure should be running app/flask_main.py instead")
print("🚨 Check startup.txt, Procfile, and Azure App Service configuration")
app = Flask(__name__)

@app.route('/')
def error_message():
    return {
        "ERROR": "WRONG STARTUP SCRIPT RUNNING",
        "message": "minimal_startup.py should not be running",
        "expected": "app/flask_main.py should be running",
        "check": "Azure App Service startup configuration"
    }

@app.route('/health')
def health():
    return {"status": "ERROR", "message": "Wrong script running"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', os.environ.get('WEBSITES_PORT', 8000)))
    print(f"🚨 WRONG SCRIPT RUNNING ON PORT {port}")
    app.run(host='0.0.0.0', port=port, debug=False)