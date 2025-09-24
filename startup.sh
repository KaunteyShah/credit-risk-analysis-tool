#!/bin/bash
set -e

echo "🚀 Azure App Service Startup Script"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Directory contents:"
ls -la

echo "🔍 Looking for main.py..."
if [ -f "main.py" ]; then
    echo "✅ Found main.py in current directory"
else
    echo "❌ main.py not found in current directory"
    echo "Directory structure:"
    find . -name "main.py" -type f 2>/dev/null || echo "No main.py found anywhere"
fi

echo "🔍 Looking for app directory..."
if [ -d "app" ]; then
    echo "✅ Found app directory"
    ls -la app/
else
    echo "❌ app directory not found"
fi

echo "🐍 Starting Python application..."
export PYTHONPATH="/home/site/wwwroot:$PYTHONPATH"
export PORT=${PORT:-8000}

# Try to start the application
python main.py