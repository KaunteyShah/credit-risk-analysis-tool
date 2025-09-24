#!/bin/bash
# Azure Linux startup wrapper
# Ensures we use python3 explicitly

echo "🚀 Azure Linux Startup Wrapper"
echo "🐍 Using Python3 for main Flask application"

# Use python3 explicitly
exec python3 app/flask_main.py