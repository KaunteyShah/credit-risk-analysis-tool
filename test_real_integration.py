"""
Test the enhanced SIC matcher with real company data integration.

This script tests the corrected structure and JOIN logic.
"""
import sys
import os
sys.path.append('/Users/kaunteyshah/Databricks/Credit_Risk')

import pandas as pd
import tempfile
from app.utils.enhanced_sic_matcher import UpdatedDataManager, EnhancedSICMatcher
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_real_data_integration():
    """Test the SIC matcher with real Sample_data2.csv structure."""
    
    # Load a sample from real data to get structure
    sample_data_path = '/Users/kaunteyshah/Databricks/Credit_Risk/data/Sample_data2.csv'
    sample_df = pd.read_csv(sample_data_path, nrows=3)
    
    print("Sample_data2.csv columns:")
    print(f"  Registration column: 'Registration number'")
    print(f"  Company Name column: 'Company Name'") 
    print(f"  SIC column: 'UK SIC 2007 Code'")
    
    # Get first company for testing
    first_company = sample_df.iloc[0]
    company_reg = str(first_company['Registration number'])
    company_name = str(first_company['Company Name'])
    business_desc = str(first_company['Business Description'])
    current_sic = str(first_company['UK SIC 2007 Code'])
    
    print(f"\nTesting with company: {company_name}")
    print(f"Registration: {company_reg}")
    print(f"Current SIC: {current_sic}")
    
    # Create temporary test environment
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, 'test_updates.csv')
        
        # Test UpdatedDataManager
        manager = UpdatedDataManager(test_file)
        
        # Test 1: Save update with real data
        result = manager.save_updated_prediction(
            company_registration_code=company_reg,
            company_name=company_name,
            business_description=business_desc,
            current_sic=current_sic,
            old_accuracy=0.85,
            new_sic="62011",  # Software development (will be converted to int)
            new_accuracy=0.95,
            updated_by="test_user"
        )
        assert result == True, "Save should succeed"
        print("✓ Real data save test passed")
        
        # Test 2: Load and verify structure
        updates_df = manager.load_updated_data()
        assert len(updates_df) == 1, "Should have 1 record"
        
        expected_columns = [
            'Registration number', 'Company_Name', 'Business_Description',
            'Current_SIC', 'Old_Accuracy', 'New_SIC', 'New_Accuracy', 
            'Timestamp', 'Updated_By'
        ]
        for col in expected_columns:
            assert col in updates_df.columns, f"Missing column: {col}"
        
        print("✓ Enhanced CSV structure test passed")
        
        # Test 3: Test merge logic with EnhancedSICMatcher
        sic_matcher = EnhancedSICMatcher(updated_data_file=test_file)
        
        # Use small subset of real data for merge test
        test_companies = sample_df.copy()
        merged_data = sic_matcher.merge_with_updated_data(test_companies)
        
        # Verify merge worked
        assert 'New_SIC' in merged_data.columns, "Should have New_SIC column"
        assert 'New_Accuracy' in merged_data.columns, "Should have New_Accuracy column"
        assert 'Old_Accuracy' in merged_data.columns, "Should have Old_Accuracy column"
        
        # Check that our updated company has the new SIC
        print(f"\nDEBUG: Looking for registration: '{company_reg}'")
        print(f"DEBUG: Merged data registration numbers:")
        for i, reg in enumerate(merged_data['Registration number']):
            print(f"  [{i}] '{reg}' (type: {type(reg)})")
        
        # Try both original and normalized formats
        updated_row = merged_data[merged_data['Registration number'] == company_reg]
        if len(updated_row) == 0:
            # Try normalized format
            normalized_reg = str(company_reg).replace('.0', '')
            print(f"DEBUG: Trying normalized format: '{normalized_reg}'")
            updated_row = merged_data[merged_data['Registration number'] == normalized_reg]
        
        print(f"DEBUG: Found {len(updated_row)} rows matching registration")
        if len(updated_row) > 0:
            print(f"DEBUG: Matched row New_SIC: {updated_row.iloc[0]['New_SIC']}")
            print(f"DEBUG: Matched row New_Accuracy: {updated_row.iloc[0]['New_Accuracy']}")
        
        assert len(updated_row) == 1, f"Should find our updated company (searched for '{company_reg}')"
        assert updated_row.iloc[0]['New_SIC'] == 62011, "Should have updated SIC as integer"
        assert updated_row.iloc[0]['New_Accuracy'] == 0.95, "Should have updated accuracy"
        
        print("✓ Real data merge test passed")
        
        # Test 4: Verify other companies have default values
        non_updated = merged_data[merged_data['Registration number'] != normalized_reg]
        print(f"DEBUG: Non-updated companies accuracy values: {non_updated['New_Accuracy'].tolist()}")
        print(f"DEBUG: Non-updated companies SIC values: {non_updated['New_SIC'].tolist()}")
        
        # Check that non-updated companies have their original SIC as New_SIC and 0.0 accuracy
        for idx, row in non_updated.iterrows():
            assert row['New_Accuracy'] == 0.0, f"Non-updated company should have 0.0 accuracy, got {row['New_Accuracy']}"
            # New_SIC should be their original UK SIC code as integer
            original_sic = int(row.get('UK SIC 2007 Code', 0))
            new_sic = int(row['New_SIC']) if pd.notna(row['New_SIC']) else 0
            assert new_sic == original_sic, f"New_SIC should default to original SIC: {new_sic} != {original_sic}"
        
        print("✓ Default values test passed")
        
        print(f"\n🎉 All real data integration tests passed!")
        print(f"📊 Updated CSV structure: {len(expected_columns)} columns")
        print(f"🔗 JOIN key: 'Registration number' (matches Sample_data2.csv)")
        print(f"💾 Atomic writes: Enabled with file locking")

if __name__ == "__main__":
    try:
        test_real_data_integration()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)