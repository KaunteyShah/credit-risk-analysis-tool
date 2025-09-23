#!/usr/bin/env python3
"""
Test script to verify data loading
"""
import os
import sys
import pandas as pd

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from flask_app import load_company_data, load_sic_codes
    
    print("Testing data loading...")
    
    # Test company data loading
    print("Loading company data...")
    company_data = load_company_data()
    if company_data is not None:
        print(f"✅ Company data loaded successfully: {len(company_data)} rows")
        print(f"Columns: {list(company_data.columns)}")
        print("Sample data:")
        print(company_data.head())
    else:
        print("❌ Failed to load company data")
    
    # Test SIC codes loading
    print("\nLoading SIC codes...")
    sic_codes = load_sic_codes()
    if sic_codes is not None:
        print(f"✅ SIC codes loaded successfully: {len(sic_codes)} rows")
        print(sic_codes.head())
    else:
        print("❌ Failed to load SIC codes")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()