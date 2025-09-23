#!/bin/bash
# Credit Risk Analysis - Quick Start Script for macOS/Linux

echo "🚀 Credit Risk Analysis - Quick Start"
echo "======================================"

# Check if Python is available
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.11+ first."
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "🔧 Setting up virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
fi

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip and install requirements
echo "📥 Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Run verification
echo "🔍 Verifying setup..."
python verify_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup complete! Starting the application..."
    echo "🌐 The app will be available at: http://localhost:8000"
    echo ""
    python main.py
else
    echo "❌ Setup verification failed. Please check the errors above."
    exit 1
fi
