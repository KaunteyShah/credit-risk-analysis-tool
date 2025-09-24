"""
DEPENDENCY CHECK - Verify Azure package installations
This script checks if all required packages are properly installed
"""

import sys
import os

print("=" * 60)
print("🔍 DEPENDENCY CHECK: Verifying Package Installations")
print(f"🐍 Python: {sys.version}")
print(f"📍 Current directory: {os.getcwd()}")
print("=" * 60)

# Check essential packages
required_packages = [
    'flask',
    'flask_cors',
    'pandas',
    'numpy',
    'azure.identity',
    'azure.keyvault.secrets'
]

installed_packages = []
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
        installed_packages.append(package)
        print(f"✅ {package} - INSTALLED")
    except ImportError as e:
        missing_packages.append(package)
        print(f"❌ {package} - MISSING: {e}")

print("=" * 60)
print(f"📊 SUMMARY:")
print(f"✅ Installed: {len(installed_packages)}")
print(f"❌ Missing: {len(missing_packages)}")

if missing_packages:
    print(f"🚨 Missing packages: {missing_packages}")
    print("💡 These packages need to be installed for full functionality")
    
# Try to install missing packages
if missing_packages:
    print("🔧 Attempting to install missing packages...")
    try:
        import subprocess
        for package in missing_packages:
            if package == 'flask_cors':
                cmd = [sys.executable, '-m', 'pip', 'install', 'flask-cors>=4.0.1']
            else:
                cmd = [sys.executable, '-m', 'pip', 'install', package]
            
            print(f"Installing {package}...")
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✅ {package} installed successfully")
    except Exception as e:
        print(f"❌ Failed to install packages: {e}")

print("=" * 60)
print("🎯 DEPENDENCY CHECK COMPLETE")