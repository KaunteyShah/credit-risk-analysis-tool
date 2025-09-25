#!/bin/bash
echo "🚀 Starting Credit Risk Analysis App on Azure App Service..."

cd /home/site/wwwroot

# Export Python path
export PYTHONPATH=/home/site/wwwroot

# Get the port from Azure environment
export PORT=${WEBSITES_PORT:-8000}

echo "📍 Starting application on port $PORT"

# Use Gunicorn for production deployment with proper configuration
if command -v gunicorn &> /dev/null; then
    echo "🔧 Using Gunicorn for production deployment"
    exec gunicorn --config gunicorn.conf.py main:app
else
    echo "⚠️ Gunicorn not found, falling back to Flask dev server"
    exec python3 main.py
fi