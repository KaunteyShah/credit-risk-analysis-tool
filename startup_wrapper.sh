#!/bin/bash
# Azure Linux startup wrapper
# Ensures we use python3 explicitly

echo "🚀 Azure Linux Startup Wrapper"
echo "🐍 Using Python3 for minimal_startup.py"

# Use python3 explicitly
exec python3 minimal_startup.py