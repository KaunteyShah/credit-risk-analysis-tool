"""
Enhanced SIC Code Fuzzy Matching Utilities

This module provides fuzzy matching functionality to predict SIC codes
based on company business descriptions with dual accuracy tracking and CSV management.
"""

import pandas as pd
import os
from rapidfuzz import fuzz, process
from typing import Dict, List, Tuple, Optional, Union
import logging
from datetime import datetime
from .atomic_csv import AtomicCSVWriter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UpdatedDataManager:
    """
    Manages the updated SIC predictions CSV file with dual accuracy tracking.
    """
    
    def __init__(self, updated_data_file: str = "data/updated_sic_predictions.csv"):
        """
        Initialize the updated data manager.
        
        Args:
            updated_data_file: Path to the updated predictions CSV file
        """
        self.updated_data_file = updated_data_file
        self.ensure_updated_file_exists()
    
    def ensure_updated_file_exists(self):
        """
        Create the updated data CSV file if it doesn't exist.
        """
        if not os.path.exists(self.updated_data_file):
            # Create file with correct column structure
            columns = [
                'Registration number',  # Match Sample_data2.csv
                'Company_Name',
                'Business_Description', 
                'Current_SIC',
                'Old_Accuracy',
                'New_SIC',
                'New_Accuracy',
                'Timestamp',
                'Updated_By'
            ]
            empty_df = pd.DataFrame(columns=columns)
            # Use atomic write to prevent corruption
            if not AtomicCSVWriter.write_csv_with_lock(empty_df, self.updated_data_file, index=False):
                logger.error(f"Failed to create updated data file: {self.updated_data_file}")
                raise Exception(f"Could not create updated data file")
            logger.info(f"Created updated data file: {self.updated_data_file}")
    
    def load_updated_data(self) -> pd.DataFrame:
        """
        Load the updated predictions data safely.
        
        Returns:
            DataFrame with updated predictions
        """
        try:
            df = AtomicCSVWriter.read_csv_safe(self.updated_data_file)
            if not df.empty:
                logger.info(f"Loaded {len(df)} updated records")
            else:
                logger.info("No updated records found - returning empty DataFrame")
            return df
        except Exception as e:
            logger.error(f"Error loading updated data: {e}")
            return pd.DataFrame()
    
    def save_updated_prediction(self, company_registration_code: str, company_name: str, 
                              business_description: str, current_sic: str, old_accuracy: float,
                              new_sic: str, new_accuracy: float, updated_by: str = "system") -> bool:
        """
        Save an updated SIC prediction with atomic CSV writing.
        
        Args:
            company_registration_code: Company registration code
            company_name: Company name
            business_description: Business description
            current_sic: Current SIC code
            old_accuracy: Old accuracy percentage
            new_sic: New SIC code prediction
            new_accuracy: New accuracy percentage
            updated_by: User who made the update
            
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            # Ensure the file exists
            self.ensure_updated_file_exists()
            
            # Load existing data
            updated_df = self.load_updated_data()
            
            # Normalize registration code (handle float to string conversion)
            normalized_reg_code = str(company_registration_code).replace('.0', '')
            
            # Create new record with correct structure
            new_record = {
                'Registration number': normalized_reg_code,  # Normalized format
                'Company_Name': company_name,
                'Business_Description': business_description,
                'Current_SIC': int(current_sic) if str(current_sic).isdigit() else None,  # Ensure integer format
                'Old_Accuracy': old_accuracy,
                'New_SIC': int(new_sic) if str(new_sic).isdigit() else None,  # Ensure integer format 
                'New_Accuracy': new_accuracy,
                'Timestamp': datetime.now().isoformat(),
                'Updated_By': updated_by
            }
            
            # Check if record already exists for this company
            if not updated_df.empty and 'Registration number' in updated_df.columns:
                # Normalize registration codes for comparison
                updated_df['Registration number'] = updated_df['Registration number'].astype(str).str.replace('.0', '', regex=False)
                existing_mask = updated_df['Registration number'] == normalized_reg_code
                
                if existing_mask.any():
                    # Update existing record
                    updated_df.loc[existing_mask, 'New_SIC'] = new_sic
                    updated_df.loc[existing_mask, 'New_Accuracy'] = new_accuracy
                    updated_df.loc[existing_mask, 'Timestamp'] = new_record['Timestamp']
                    updated_df.loc[existing_mask, 'Updated_By'] = updated_by
                    logger.info(f"Updated existing record for {company_name}")
                else:
                    # Add new record
                    updated_df = pd.concat([updated_df, pd.DataFrame([new_record])], ignore_index=True)
                    logger.info(f"Added new record for {company_name}")
            else:
                # Add new record (first record or empty DataFrame)
                updated_df = pd.concat([updated_df, pd.DataFrame([new_record])], ignore_index=True)
                logger.info(f"Added new record for {company_name}")
            
            # Save back to CSV using atomic write
            if AtomicCSVWriter.write_csv_with_lock(updated_df, self.updated_data_file, index=False):
                logger.info(f"Successfully saved updated prediction for {company_name}")
                return True
            else:
                logger.error(f"Failed to save updated prediction for {company_name}")
                return False
            
        except Exception as e:
            logger.error(f"Error saving updated prediction: {e}")
            return False

class EnhancedSICMatcher:
    """
    Enhanced SIC code fuzzy matching with dual accuracy tracking.
    """
    
    def __init__(self, sic_codes_file: Optional[str] = None, updated_data_file: str = "data/updated_sic_predictions.csv"):
        """
        Initialize the enhanced SIC matcher.
        
        Args:
            sic_codes_file: Path to the SIC codes Excel file
            updated_data_file: Path to the updated predictions CSV file
        """
        self.sic_codes_df = None
        self.sic_descriptions = {}  # {code: description}
        self.description_to_code = {}  # {description: code}
        self.updated_data_manager = UpdatedDataManager(updated_data_file)
        
        if sic_codes_file:
            self.load_sic_codes(sic_codes_file)
    
    def load_sic_codes(self, sic_codes_file: str) -> bool:
        """
        Load SIC codes from Excel file.
        
        Args:
            sic_codes_file: Path to the SIC codes Excel file
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(sic_codes_file):
                logger.error(f"SIC codes file not found: {sic_codes_file}")
                return False
            
            self.sic_codes_df = pd.read_excel(sic_codes_file)
            
            # Check if required columns exist - try multiple possible column names
            possible_code_columns = ['SIC Code', 'Section A', 'Code']
            possible_desc_columns = ['Description', 'Agriculture, Forestry and Fishing', 'Desc']
            
            code_col = None
            desc_col = None
            
            for col in possible_code_columns:
                if col in self.sic_codes_df.columns:
                    code_col = col
                    break
            
            for col in possible_desc_columns:
                if col in self.sic_codes_df.columns:
                    desc_col = col
                    break
            
            if not code_col or not desc_col:
                logger.error(f"Required columns not found. Available columns: {list(self.sic_codes_df.columns)}")
                return False
            
            # Build lookup dictionaries using the detected column names
            for _, row in self.sic_codes_df.iterrows():
                sic_code = str(row[code_col]).strip()
                description = str(row[desc_col]).strip()
                
                self.sic_descriptions[sic_code] = description
                self.description_to_code[description] = sic_code
            
            logger.info(f"Loaded {len(self.sic_descriptions)} SIC codes")
            return True
            
        except Exception as e:
            logger.error(f"Error loading SIC codes: {e}")
            return False
    
    def get_sic_description(self, sic_code: str) -> str:
        """
        Get description for a SIC code.
        
        Args:
            sic_code: The SIC code
            
        Returns:
            Description of the SIC code
        """
        return self.sic_descriptions.get(str(sic_code).strip(), "Unknown SIC Code")
    
    def find_best_match(self, business_desc: str, top_n: int = 3) -> List[Dict]:
        """
        Find best matching SIC codes for a business description.
        
        Args:
            business_desc: Business description to match
            top_n: Number of top matches to return
            
        Returns:
            List of dictionaries with match results
        """
        if not business_desc or not self.sic_descriptions:
            return []
        
        # Get list of all SIC descriptions for matching
        sic_descriptions_list = list(self.description_to_code.keys())
        
        # Use rapidfuzz to find best matches
        matches = process.extract(
            business_desc,
            sic_descriptions_list,
            scorer=fuzz.WRatio,  # Weighted ratio for better matching
            limit=top_n
        )
        
        results = []
        for match_desc, score, _ in matches:
            sic_code = self.description_to_code.get(match_desc)
            if sic_code:
                results.append({
                    'sic_code': sic_code,
                    'sic_description': match_desc,
                    'fuzzy_score': score,
                    'accuracy_percentage': round(score, 1)
                })
        
        return results
    
    def calculate_old_accuracy(self, business_description: str, current_sic_code: str) -> Dict:
        """
        Calculate old accuracy (fuzzy match between business description and current SIC).
        
        Args:
            business_description: Company business description
            current_sic_code: Current SIC code in the database
            
        Returns:
            Dictionary with old accuracy results
        """
        if not business_description or not current_sic_code:
            return {
                'current_sic_code': current_sic_code,
                'current_sic_description': self.get_sic_description(current_sic_code) if current_sic_code else '',
                'old_accuracy': 0.0,
                'is_accurate': False
            }
        
        # Get description of current SIC code
        current_sic_description = self.get_sic_description(current_sic_code)
        
        # Calculate fuzzy match between business description and current SIC description
        if current_sic_description and current_sic_description != "Unknown SIC Code":
            fuzzy_score = fuzz.WRatio(business_description, current_sic_description)
            is_accurate = fuzzy_score >= 90.0
        else:
            fuzzy_score = 0.0
            is_accurate = False
        
        return {
            'current_sic_code': current_sic_code,
            'current_sic_description': current_sic_description,
            'old_accuracy': round(fuzzy_score, 1),
            'is_accurate': is_accurate
        }
    
    def calculate_new_accuracy(self, business_description: str) -> Dict:
        """
        Calculate new accuracy (best predicted SIC match).
        
        Args:
            business_description: Company business description
            
        Returns:
            Dictionary with new accuracy results (predicted SIC)
        """
        if not business_description:
            return {
                'predicted_sic_code': None,
                'predicted_sic_description': '',
                'new_accuracy': 0.0,
                'is_accurate': False
            }
        
        # Get the best match prediction
        best_matches = self.find_best_match(business_description, top_n=1)
        
        if not best_matches:
            return {
                'predicted_sic_code': None,
                'predicted_sic_description': '',
                'new_accuracy': 0.0,
                'is_accurate': False
            }
        
        best_match = best_matches[0]
        new_accuracy = best_match['accuracy_percentage']
        is_accurate = new_accuracy >= 90.0
        
        return {
            'predicted_sic_code': best_match['sic_code'],
            'predicted_sic_description': best_match['sic_description'],
            'new_accuracy': new_accuracy,
            'is_accurate': is_accurate
        }
    
    def get_dual_accuracy(self, business_description: str, current_sic_code: str) -> Dict:
        """
        Get both old and new accuracy calculations.
        
        Args:
            business_description: Company business description
            current_sic_code: Current SIC code
            
        Returns:
            Dictionary with both accuracy calculations
        """
        old_accuracy = self.calculate_old_accuracy(business_description, current_sic_code)
        new_accuracy = self.calculate_new_accuracy(business_description)
        
        return {
            'old_accuracy': old_accuracy,
            'new_accuracy': new_accuracy
        }
    
    def batch_calculate_dual_accuracy(self, companies_df: pd.DataFrame, 
                                    business_desc_col: str = 'Business Description',
                                    sic_code_col: str = 'UK SIC 2007 Code') -> pd.DataFrame:
        """
        Calculate dual accuracy for a batch of companies.
        
        Args:
            companies_df: DataFrame containing company data
            business_desc_col: Column name for business descriptions
            sic_code_col: Column name for current SIC codes
            
        Returns:
            DataFrame with dual accuracy columns added
        """
        if companies_df.empty:
            return companies_df
        
        result_df = companies_df.copy()
        
        # Initialize new columns
        result_df['Old_Accuracy'] = 0.0
        result_df['New_Accuracy'] = 0.0  # This is for automatic prediction accuracy, not user updates
        result_df['Predicted_SIC'] = ''
        result_df['Predicted_SIC_Description'] = ''
        # Note: New_SIC column will be added later in merge_with_updated_data() and should remain null until user action
        
        # Create lists to store results
        old_accuracies = []
        new_accuracies = []
        predicted_sics = []
        predicted_sic_descriptions = []
        
        logger.info(f"Calculating dual accuracy for {len(companies_df)} companies...")
        
        for idx, row in companies_df.iterrows():
            business_desc = str(row.get(business_desc_col, '')).strip()
            current_sic = str(row.get(sic_code_col, '')).strip()
            
            if business_desc and business_desc != 'nan':
                dual_accuracy = self.get_dual_accuracy(business_desc, current_sic)
                
                # Old accuracy
                old_acc = dual_accuracy['old_accuracy']
                old_accuracies.append(old_acc['old_accuracy'])
                
                # New accuracy
                new_acc = dual_accuracy['new_accuracy']
                new_accuracies.append(new_acc['new_accuracy'])
                predicted_sics.append(new_acc.get('predicted_sic_code', ''))
                predicted_sic_descriptions.append(new_acc.get('predicted_sic_description', ''))
            else:
                # Default values for empty business descriptions
                old_accuracies.append(0.0)
                new_accuracies.append(0.0)
                predicted_sics.append('')
                predicted_sic_descriptions.append('')
        
        # Assign all values at once
        result_df['Old_Accuracy'] = old_accuracies
        result_df['New_Accuracy'] = new_accuracies
        result_df['Predicted_SIC'] = predicted_sics
        result_df['Predicted_SIC_Description'] = predicted_sic_descriptions
        
        logger.info("Dual accuracy calculation completed")
        return result_df
    
    def merge_with_updated_data(self, companies_df: pd.DataFrame, 
                               reg_code_col: str = 'Registration number') -> pd.DataFrame:
        """
        Merge company data with updated predictions data using multi-field matching.
        
        Matching Strategy:
        1. Company Name (exact match)
        2. Registration Number (if available) 
        3. Current SIC code (OLD_SIC)
        
        Args:
            companies_df: Original company data
            reg_code_col: Registration code column name (default: 'Registration number')
            
        Returns:
            Merged DataFrame with updated data
        """
        # Load updated data
        updated_df = self.updated_data_manager.load_updated_data()
        
        if updated_df.empty:
            logger.info("No updated data found")
            # Add empty columns for consistency - New_SIC should be null until user clicks "Predict SIC"
            companies_df['New_SIC'] = None  # Empty until user action
            # CRITICAL FIX: Clear automatic New_Accuracy for companies without user predictions
            companies_df['New_Accuracy'] = None  # Should be null until user clicks "Predict SIC"
            return companies_df
        
        # Prepare data for multi-field matching
        companies_df_copy = companies_df.copy()
        
        # Normalize registration numbers for comparison (handle float to string conversion)
        companies_df_copy[reg_code_col] = companies_df_copy[reg_code_col].astype(str).str.replace('.0', '', regex=False)
        updated_df['Registration number'] = updated_df['Registration number'].astype(str).str.replace('.0', '', regex=False)
        
        # Normalize company names for comparison (strip whitespace, convert to uppercase)
        companies_df_copy['Company_Name_Normalized'] = companies_df_copy['Company Name'].str.strip().str.upper()
        updated_df['Company_Name_Normalized'] = updated_df['Company_Name'].str.strip().str.upper()
        
        # Convert SIC codes to consistent format for comparison
        companies_df_copy['UK_SIC_Normalized'] = pd.to_numeric(companies_df_copy['UK SIC 2007 Code'], errors='coerce').fillna(0).astype('Int64')
        updated_df['Current_SIC_Normalized'] = pd.to_numeric(updated_df['Current_SIC'], errors='coerce').fillna(0).astype('Int64')
        
        # Multi-field merge approach
        # Step 1: Try exact match on all three fields (most precise)
        merged_df = companies_df_copy.merge(
            updated_df[['Registration number', 'Company_Name_Normalized', 'Current_SIC_Normalized', 
                       'New_SIC', 'New_Accuracy', 'Old_Accuracy', 'Timestamp', 'Updated_By']],
            left_on=[reg_code_col, 'Company_Name_Normalized', 'UK_SIC_Normalized'],
            right_on=['Registration number', 'Company_Name_Normalized', 'Current_SIC_Normalized'],
            how='left',
            suffixes=('', '_updated')
        )
        
        # Step 2: For unmatched records, try Company Name + SIC match (handles missing registration numbers)
        unmatched_mask = merged_df['Timestamp'].isnull()
        if unmatched_mask.sum() > 0:
            # Get the original indices of unmatched companies
            unmatched_indices = merged_df[unmatched_mask].index
            unmatched_companies = companies_df_copy.loc[unmatched_indices]
            
            # Try matching on Company Name + SIC only
            name_sic_matches = unmatched_companies.merge(
                updated_df[['Company_Name_Normalized', 'Current_SIC_Normalized', 
                           'New_SIC', 'New_Accuracy', 'Old_Accuracy', 'Timestamp', 'Updated_By']],
                left_on=['Company_Name_Normalized', 'UK_SIC_Normalized'],
                right_on=['Company_Name_Normalized', 'Current_SIC_Normalized'],
                how='inner',
                suffixes=('', '_name_sic_match')
            )
            
            # Update the merged DataFrame with name+SIC matches
            if not name_sic_matches.empty:
                for original_idx in name_sic_matches.index:
                    if original_idx in merged_df.index:
                        match = name_sic_matches.loc[original_idx]
                        merged_df.at[original_idx, 'New_SIC'] = match['New_SIC']
                        merged_df.at[original_idx, 'New_Accuracy_updated'] = match['New_Accuracy']
                        merged_df.at[original_idx, 'Old_Accuracy_updated'] = match['Old_Accuracy']
                        merged_df.at[original_idx, 'Timestamp'] = match['Timestamp']
                        merged_df.at[original_idx, 'Updated_By'] = match['Updated_By']
        
        # Clean up temporary columns
        columns_to_drop = ['Company_Name_Normalized', 'UK_SIC_Normalized', 'Registration number_updated', 
                          'Company_Name_Normalized_updated', 'Current_SIC_Normalized']
        for col in columns_to_drop:
            if col in merged_df.columns:
                merged_df = merged_df.drop(columns=[col])
        
        # For companies WITH user predictions, override the automatic accuracy with user prediction accuracy
        # For companies WITHOUT user predictions, keep automatic accuracy and New_SIC = None
        user_prediction_mask = merged_df['Timestamp'].notna()
        
        # Update accuracy columns for companies with user predictions
        if 'New_Accuracy_updated' in merged_df.columns:
            merged_df.loc[user_prediction_mask, 'New_Accuracy'] = merged_df.loc[user_prediction_mask, 'New_Accuracy_updated']
            merged_df = merged_df.drop(columns=['New_Accuracy_updated'])
            
        if 'Old_Accuracy_updated' in merged_df.columns:
            merged_df.loc[user_prediction_mask, 'Old_Accuracy'] = merged_df.loc[user_prediction_mask, 'Old_Accuracy_updated'] 
            merged_df = merged_df.drop(columns=['Old_Accuracy_updated'])
        
        # CRITICAL FIX: Clear New_Accuracy for companies WITHOUT user predictions
        # New_Accuracy should only show for companies where user clicked "Predict SIC"
        no_user_prediction_mask = ~user_prediction_mask
        merged_df.loc[no_user_prediction_mask, 'New_Accuracy'] = None
        
        # Ensure New_SIC remains null for companies without user predictions
        # (companies with user predictions already have their New_SIC set from the merge)
        
        # Update count logging
        updated_count = merged_df['Timestamp'].notna().sum()
        if updated_count > 0:
            logger.info(f"Found {updated_count} companies with updated SIC data")
            logger.info("Matching strategy: Company Name + Registration Number + Current SIC")
        else:
            logger.info("No companies have updated SIC data")
        
        return merged_df
        
        return merged_df
    
    def save_sic_update(self, company_registration_code: str, company_name: str,
                       business_description: str, current_sic: str, old_accuracy: float,
                       new_sic: str, new_accuracy: float) -> bool:
        """
        Save an updated SIC prediction.
        
        Args:
            company_registration_code: Company registration code
            company_name: Company name
            business_description: Business description
            current_sic: Current SIC code
            old_accuracy: Old accuracy percentage
            new_sic: New SIC code to save
            new_accuracy: New accuracy percentage
            
        Returns:
            bool: True if saved successfully
        """
        return self.updated_data_manager.save_updated_prediction(
            company_registration_code, company_name, business_description,
            current_sic, old_accuracy, new_sic, new_accuracy
        )

# Global instance for easy access
_enhanced_sic_matcher = None

def get_enhanced_sic_matcher(sic_codes_file: Optional[str] = None) -> EnhancedSICMatcher:
    """
    Get or create enhanced SIC matcher instance.
    
    Args:
        sic_codes_file: Path to SIC codes file
        
    Returns:
        EnhancedSICMatcher instance
    """
    global _enhanced_sic_matcher
    
    if _enhanced_sic_matcher is None:
        _enhanced_sic_matcher = EnhancedSICMatcher(sic_codes_file)
    elif sic_codes_file and not _enhanced_sic_matcher.sic_codes_df is not None:
        _enhanced_sic_matcher.load_sic_codes(sic_codes_file)
    
    return _enhanced_sic_matcher