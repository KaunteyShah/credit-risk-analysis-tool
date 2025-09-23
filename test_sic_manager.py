"""
Test script for enhanced SIC matcher with atomic CSV operations.

This script tests the UpdatedDataManager class to ensure safe CSV operations.
"""
import sys
import os
sys.path.append('/Users/kaunteyshah/Databricks/Credit_Risk')

import tempfile
import shutil
from app.utils.enhanced_sic_matcher import UpdatedDataManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_updated_data_manager():
    """Test the UpdatedDataManager with atomic CSV operations."""
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, 'test_updated_predictions.csv')
        
        print("Testing UpdatedDataManager with atomic CSV...")
        
        # Create UpdatedDataManager instance
        manager = UpdatedDataManager(test_file)
        
        # Test 1: File initialization
        assert os.path.exists(test_file), "CSV file should be created"
        print("✓ File initialization test passed")
        
        # Test 2: Save a prediction
        result = manager.save_updated_prediction(
            company_registration_code="12345678",
            company_name="Test Corp",
            business_description="Software development",
            current_sic="62012",
            old_accuracy=0.85,
            new_sic="62011",
            new_accuracy=0.95,
            updated_by="test_user"
        )
        assert result == True, "Save should succeed"
        print("✓ Save prediction test passed")
        
        # Test 3: Load data
        df = manager.load_updated_data()
        assert len(df) == 1, "Should have 1 record"
        assert df.iloc[0]['Company_Name'] == "Test Corp", "Company name should match"
        print("✓ Load data test passed")
        
        # Test 4: Update existing record
        result = manager.save_updated_prediction(
            company_registration_code="12345678",
            company_name="Test Corp",
            business_description="Software development",
            current_sic="62011",
            old_accuracy=0.95,
            new_sic="62020",
            new_accuracy=0.98,
            updated_by="test_user2"
        )
        assert result == True, "Update should succeed"
        
        # Verify only one record exists (updated, not duplicated)
        df = manager.load_updated_data()
        assert len(df) == 1, "Should still have 1 record after update"
        assert df.iloc[0]['New_SIC'] == "62020", "SIC should be updated"
        assert df.iloc[0]['New_Accuracy'] == 0.98, "Accuracy should be updated"
        print("✓ Update existing record test passed")
        
        print("\n🎉 All UpdatedDataManager tests passed!")

if __name__ == "__main__":
    try:
        test_updated_data_manager()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)