#!/bin/bash

# Pure Modular Architecture Demo Startup Script
echo "🚀 Starting Pure Modular Flask App Demo"
echo "========================================"
echo ""
echo "🏗️  Architecture: 100% Modular (No Fallbacks)"
echo "🔧 Components: Repository Pattern + Service Layer + Dependency Injection"
echo "🌐 URL: http://localhost:5001"
echo ""
echo "Available Endpoints:"
echo "  GET  /                              - Home page with architecture info"
echo "  GET  /api/modular/health            - Health check for modular components"
echo "  GET  /api/modular/companies         - Paginated companies (pure modular)"
echo "  GET  /api/modular/companies/{index} - Company details with AI reasoning"
echo "  POST /api/modular/predict-sic       - SIC prediction (pure modular)"
echo "  GET  /api/modular/stats             - Architecture statistics"
echo ""
echo "🎯 This app demonstrates PURE modular architecture without any fallbacks!"
echo ""

# Set environment for modular architecture
export DATABASE_TYPE=files

# Navigate to project directory
cd "$(dirname "$0")"

# Start the pure modular Flask app
python3 pure_modular_app.py