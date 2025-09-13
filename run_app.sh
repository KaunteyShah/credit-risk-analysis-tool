#!/bin/bash

# Credit Risk Analysis Demo - Streamlit App Launcher
# Phase 1 UI with collapsible panels and SIC accuracy analysis

echo "🏦 Starting Credit Risk Analysis Demo - Phase 1 UI"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "streamlit_app.py" ]; then
    echo "❌ Error: streamlit_app.py not found in current directory"
    echo "Please run this script from the Credit_Risk directory"
    exit 1
fi

# Check if enhanced data exists
if [ ! -f "enhanced_sample_data.pkl" ]; then
    echo "📊 Enhanced data not found. Generating now..."
    python3 preprocess_data.py
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to generate enhanced data"
        exit 1
    fi
    echo "✅ Enhanced data generated successfully"
fi

# Start Streamlit app
echo "🚀 Launching Streamlit app..."
echo "📍 URL: http://localhost:8501"
echo "💡 Press Ctrl+C to stop the application"
echo ""

python3 -m streamlit run streamlit_app.py --server.port 8501

echo ""
echo "� Credit Risk Analysis Demo stopped"
