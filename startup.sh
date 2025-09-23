#!/bin/bash

echo "🚀 Starting Credit Risk Analysis Application"
echo "📅 $(date)"

# Install dependencies
echo "📦 Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Set environment variables for Azure
export PYTHONPATH="${PYTHONPATH}:/home/site/wwwroot"
export FLASK_APP=main.py
export FLASK_ENV=production

# Start the application
echo "🌟 Starting Flask application..."
python main.py