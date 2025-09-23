#!/usr/bin/env python3
"""
Verification script for Credit Risk Analysis Application
Run this to verify all dependencies and data files are properly configured
"""

import sys
import os
import subprocess
import importlib.util

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.11+")
        return False

def check_file_exists(filepath, description):
    """Check if a required file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - NOT FOUND")
        return False

def check_package_installed(package_name):
    """Check if a Python package is installed"""
    spec = importlib.util.find_spec(package_name)
    if spec is not None:
        print(f"✅ {package_name} - Installed")
        return True
    else:
        print(f"❌ {package_name} - NOT INSTALLED")
        return False

def main():
    """Main verification function"""
    print("🔍 Credit Risk Analysis - Deployment Verification")
    print("=" * 60)
    
    all_checks_passed = True
    
    # Check Python version
    print("\n1. Python Version Check:")
    if not check_python_version():
        all_checks_passed = False
    
    # Check essential files
    print("\n2. Essential Files Check:")
    essential_files = [
        ("main.py", "Application entry point"),
        ("requirements.txt", "Dependencies file"),
        ("data/Sample_data2.csv", "Sample company data"),
        ("data/SIC_codes.xlsx", "SIC classification codes"),
        ("app/core/streamlit_app_langgraph_viz.py", "Main Streamlit app"),
        ("app/__init__.py", "App module init")
    ]
    
    for filepath, description in essential_files:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    
    # Check critical Python packages
    print("\n3. Critical Dependencies Check:")
    critical_packages = [
        "streamlit",
        "pandas", 
        "plotly",
        "numpy",
        "openpyxl"
    ]
    
    for package in critical_packages:
        if not check_package_installed(package):
            all_checks_passed = False
    
    # Check data structure
    print("\n4. Data Structure Check:")
    try:
        import pandas as pd
        df = pd.read_csv("data/Sample_data2.csv")
        print(f"✅ CSV Data: {df.shape[0]} companies, {df.shape[1]} columns")
        
        # Check for essential columns
        required_cols = ["Company Name", "Employees (Total)", "Business Description"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"⚠️  Missing columns: {missing_cols}")
        else:
            print("✅ All essential columns present")
            
    except Exception as e:
        print(f"❌ Data loading error: {e}")
        all_checks_passed = False
    
    # Final result
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("🎉 ALL CHECKS PASSED! Ready to run the application.")
        print("\n📋 To start the app:")
        print("   python main.py")
        print("\n🌐 Then open: http://localhost:8000")
    else:
        print("❌ SOME CHECKS FAILED! Please review the issues above.")
        print("\n💡 Common fixes:")
        print("   - Install missing packages: pip install -r requirements.txt")
        print("   - Check if you're in the correct directory")
        print("   - Verify all files were downloaded from git")
    
    return all_checks_passed

if __name__ == "__main__":
    main()
