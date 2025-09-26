#!/bin/bash
echo "🚀 Starting Credit Risk Analysis App on Azure App Service..."

cd /home/site/wwwroot

# Install dependencies if not already installed
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    echo "Installing from requirements.txt..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt --user
elif [ -f "requirements-azure.txt" ]; then
    echo "Installing from requirements-azure.txt..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements-azure.txt --user
else
    echo "Installing essential packages..."
    python -m pip install --upgrade pip
    python -m pip install flask flask-cors pandas numpy requests python-dotenv gunicorn --user
fi

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