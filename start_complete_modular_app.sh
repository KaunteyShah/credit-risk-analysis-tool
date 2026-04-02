#!/bin/bash

# Complete Modular Web Application Startup Script
echo "🚀 Starting Complete Modular Web Application"
echo "============================================="
echo ""
echo "🏗️  Architecture: 100% Modular (Web + API)"
echo "🔧 Components:"
echo "   • Repository Pattern (FileCompanyRepository, FileSICPredictionRepository)"
echo "   • Service Layer (CompanyService, SICPredictionService)"
echo "   • Dependency Injection (DIContainer)"
echo "   • Web Interface (HTML Templates + CSS + JavaScript)"
echo "   • API Endpoints (REST APIs with JSON responses)"
echo ""
echo "🌐 URL: http://localhost:5002"
echo ""
echo "📄 Available Pages:"
echo "   • /                     - Main Dashboard (Company Data + Filtering)"
echo "   • /workflow             - Architecture Workflow Visualization"
echo "   • /api-status           - API Status Monitoring & Performance"
echo "   • /company/{index}      - Individual Company Detail Pages"
echo ""
echo "🔗 API Endpoints:"
echo "   • GET  /api/modular/health            - Component health check"
echo "   • GET  /api/modular/companies         - Paginated companies with filtering"
echo "   • GET  /api/modular/companies/{index} - Company details with AI reasoning"
echo "   • POST /api/modular/predict-sic       - SIC prediction using modular services"
echo "   • GET  /api/modular/stats             - Architecture statistics"
echo "   • GET  /api/modular/filter-options    - Available filter options"
echo ""
echo "✨ Features:"
echo "   • Real-time company search & filtering"
echo "   • Paginated data display with performance tracking"
echo "   • Company details with AI-generated reasoning"
echo "   • SIC code prediction using modular architecture"
echo "   • Interactive workflow visualization"
echo "   • API status monitoring with response time charts"
echo "   • 100% modular - zero fallbacks to original code"
echo ""
echo "🎯 This represents the complete migration of the credit risk application"
echo "   from monolithic architecture to clean modular architecture!"
echo ""

# Set environment for modular architecture
export DATABASE_TYPE=files

# Navigate to project directory
cd "$(dirname "$0")"

# Start the complete modular Flask app
python3 complete_modular_app.py