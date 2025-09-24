#!/usr/bin/env python3
"""
Alternative startup file for Azure App Service.
Azure sometimes prefers this naming convention.
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main application
from main import app

# For Gunicorn on Azure App Service
application = app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    app.run(host="0.0.0.0", port=port, debug=False)