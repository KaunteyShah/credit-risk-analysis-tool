#!/bin/bash

echo "🚀 Starting Credit Risk Analysis Application..."

# Ensure we're in the right directory
cd /home/site/wwwroot

# Install dependencies
echo "📦 Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Set environment variables
export PYTHONPATH="/home/site/wwwroot:$PYTHONPATH"
export WEBSITES_PORT=8000

# Start Streamlit app
echo "🌐 Starting Streamlit application on port $WEBSITES_PORT..."
python -m streamlit run app/core/streamlit_app_langgraph_viz.py \
  --server.port=$WEBSITES_PORT \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --browser.gatherUsageStats=false
