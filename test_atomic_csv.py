"""
Test script for atomic CSV writing functionality.

This script tests the AtomicCSVWriter class to ensure data safety
during concurrent CSV operations.
"""
import sys
import os
sys.path.append('/Users/kaunteyshah/Databricks/Credit_Risk')

import pandas as pd
import tempfile
import shutil
from app.utils.atomic_csv import AtomicCSVWriter
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_atomic_csv_writer():
    """Test the AtomicCSVWriter functionality."""
    
    # Create test data
    test_data = pd.DataFrame({
        'company_name': ['Test Corp', 'Demo Ltd'],
        'sic_code': ['12345', '67890'],
        'accuracy': [0.95, 0.87]
    })
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, 'test_atomic.csv')
        
        print("Testing atomic CSV writing...")
        
        # Test 1: Basic atomic write
        result = AtomicCSVWriter.write_csv_atomic(test_data, test_file, index=False)
        assert result == True, "Atomic write should succeed"
        
        # Verify file exists and contains correct data
        assert os.path.exists(test_file), "CSV file should exist"
        loaded_data = pd.read_csv(test_file)
        assert len(loaded_data) == 2, "Should have 2 rows"
        assert 'company_name' in loaded_data.columns, "Should have company_name column"
        print("✓ Basic atomic write test passed")
        
        # Test 2: Atomic write with lock
        result = AtomicCSVWriter.write_csv_with_lock(test_data, test_file, index=False)
        assert result == True, "Locked write should succeed"
        print("✓ Locked atomic write test passed")
        
        # Test 3: Safe CSV read
        read_data = AtomicCSVWriter.read_csv_safe(test_file)
        assert len(read_data) == 2, "Should read 2 rows"
        print("✓ Safe CSV read test passed")
        
        # Test 4: Read non-existent file
        non_existent = os.path.join(temp_dir, 'non_existent.csv')
        empty_data = AtomicCSVWriter.read_csv_safe(non_existent)
        assert empty_data.empty, "Should return empty DataFrame for non-existent file"
        print("✓ Non-existent file read test passed")
        
        print("\n🎉 All atomic CSV writer tests passed!")

if __name__ == "__main__":
    try:
        test_atomic_csv_writer()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)