#!/bin/bash
set -e

echo "🚀 Azure App Service Startup Script"
echo "Timestamp: $(date)"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"

echo "🔍 Environment variables:"
echo "  PORT: $PORT"
echo "  WEBSITES_PORT: $WEBSITES_PORT"
echo "  PYTHONPATH: $PYTHONPATH"

echo "📁 Directory contents:"
ls -la

echo "🔍 Looking for main.py..."
if [ -f "main.py" ]; then
    echo "✅ Found main.py in current directory"
    echo "📝 main.py first 10 lines:"
    head -10 main.py
else
    echo "❌ main.py not found in current directory"
    echo "🔎 Searching for main.py..."
    find . -name "main.py" -type f 2>/dev/null || echo "No main.py found anywhere"
fi

echo "🔍 Looking for app directory..."
if [ -d "app" ]; then
    echo "✅ Found app directory"
    echo "📁 app directory contents:"
    ls -la app/
    
    echo "🔍 Checking flask_main.py..."
    if [ -f "app/flask_main.py" ]; then
        echo "✅ Found app/flask_main.py"
    else
        echo "❌ app/flask_main.py not found"
    fi
else
    echo "❌ app directory not found"
fi

echo "� Setting up environment..."
export PYTHONPATH="/home/site/wwwroot:$PYTHONPATH"
export PORT=${PORT:-${WEBSITES_PORT:-8000}}

echo "📦 Testing critical imports..."
python -c "
try:
    print('Testing imports...')
    import sys
    print(f'Python path: {sys.path[:3]}...')
    
    from app.flask_main import create_app
    print('✅ Successfully imported create_app')
    
    app = create_app()
    print('✅ Successfully created Flask app')
    print('✅ All imports successful')
    
except Exception as e:
    print(f'❌ Import error: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

echo "Starting the application with MINIMAL startup for container stability..."
exec python minimal_startup.py