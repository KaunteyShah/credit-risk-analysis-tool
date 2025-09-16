#!/bin/bash
echo "🚀 Starting Credit Risk Analysis Application..."

# Set Python path
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Install dependencies
echo "📦 Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Start Streamlit app
echo "🌐 Starting Streamlit application..."
python -m streamlit run app/core/streamlit_app_langgraph_viz.py \
  --server.port=8000 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --logger.level=info
