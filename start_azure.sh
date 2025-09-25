#!/bin/bash
# Alternative startup script with better error handling for Azure App Service

echo "🚀 Azure App Service - Credit Risk Analysis Tool"
echo "================================================"

# Set working directory
cd /home/site/wwwroot
echo "📍 Working directory: $(pwd)"

# Set Python path
export PYTHONPATH=/home/site/wwwroot
echo "🐍 PYTHONPATH: $PYTHONPATH"

# Check Azure environment variables
echo "🔧 Environment Check:"
echo "  - WEBSITES_PORT: ${WEBSITES_PORT:-'Not set'}"
echo "  - PORT: ${PORT:-'Not set'}"
echo "  - Python Version: $(python3 --version)"

# Determine port
if [ -n "$WEBSITES_PORT" ]; then
    BIND_PORT=$WEBSITES_PORT
    echo "✅ Using WEBSITES_PORT: $BIND_PORT"
elif [ -n "$PORT" ]; then
    BIND_PORT=$PORT
    echo "✅ Using PORT: $BIND_PORT"
else
    BIND_PORT=8000
    echo "⚠️ No port specified, defaulting to: $BIND_PORT"
fi

export PORT=$BIND_PORT

# Check if required files exist
echo "📂 File Check:"
for file in "main.py" "app/flask_main.py" "requirements.txt"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file exists"
    else
        echo "  ❌ $file missing"
    fi
done

# Install dependencies if needed
if [ ! -f "/tmp/.deps_installed" ]; then
    echo "📦 Installing dependencies..."
    python3 -m pip install --no-cache-dir -r requirements.txt
    touch /tmp/.deps_installed
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Test Python imports
echo "🧪 Testing critical imports..."
python3 -c "
try:
    import flask, pandas, numpy, gunicorn
    print('✅ All critical packages imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Import test passed"
else
    echo "❌ Import test failed"
    exit 1
fi

# Start the application with Gunicorn
echo "🌐 Starting application with Gunicorn on port $BIND_PORT..."
exec gunicorn \
    --bind "0.0.0.0:$BIND_PORT" \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "main:app"