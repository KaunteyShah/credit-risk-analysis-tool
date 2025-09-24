#!/bin/bash
echo "Custom build script starting..."

# Ensure pip is up to date
python -m pip install --upgrade pip

# Install requirements with verbose output
pip install -r requirements.txt --verbose --no-cache-dir

# Verify critical packages are installed
echo "Verifying package installations..."
python -c "import flask; print('Flask installed:', flask.__version__)"
python -c "import flask_cors; print('Flask-CORS installed')"
python -c "import pandas; print('Pandas installed:', pandas.__version__)"
python -c "import numpy; print('Numpy installed:', numpy.__version__)"

echo "Custom build script completed."