#!/bin/bash

echo "🚀 Starting Credit Risk Analysis Application..."

# Ensure we're in the right directory
cd /home/site/wwwroot

# Find Python executable
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v /opt/python/3.11.0/bin/python &> /dev/null; then
    PYTHON_CMD="/opt/python/3.11.0/bin/python"
elif command -v /usr/bin/python3 &> /dev/null; then
    PYTHON_CMD="/usr/bin/python3"
else
    echo "❌ Python not found!"
    exit 1
fi

echo "🐍 Using Python: $PYTHON_CMD"

# Install dependencies
echo "📦 Installing Python dependencies..."
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install -r requirements.txt

# Set environment variables
export PYTHONPATH="/home/site/wwwroot:$PYTHONPATH"
export WEBSITES_PORT=8000

# Start Streamlit app
echo "🌐 Starting Streamlit application on port $WEBSITES_PORT..."
$PYTHON_CMD -m streamlit run app/core/streamlit_app_langgraph_viz.py \
  --server.port=$WEBSITES_PORT \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --browser.gatherUsageStats=false
