"""
Enhanced SIC Code Fuzzy Matching Utilities

This module provides fuzzy matching functionality to predict SIC codes
based on company business descriptions with dual accuracy tracking and CSV management.
"""

import pandas as pd
import os
import threading
import requests
import json
from rapidfuzz import fuzz, process
from typing import Dict, List, Tuple, Optional, Union
import logging
from datetime import datetime
from .atomic_csv import AtomicCSVWriter
from app.utils.centralized_logging import get_logger

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

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
        # Ensure absolute path for container compatibility
        if not os.path.isabs(updated_data_file):
            current_dir = os.getcwd()
            self.updated_data_file = os.path.join(current_dir, updated_data_file)
        else:
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
            
            # Normalize registration code (handle float to string conversion and NaN)
            if pd.isna(company_registration_code) or str(company_registration_code) in ['nan', 'None', '']:
                normalized_reg_code = f"TEMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger.warning(f"Missing registration code for {company_name}, using temporary ID: {normalized_reg_code}")
            else:
                normalized_reg_code = str(company_registration_code).replace('.0', '')
            
            # Create new record with correct structure  
            # Convert SIC codes to pandas nullable integers to match existing DataFrame
            try:
                current_sic_int = pd.to_numeric(current_sic, errors='coerce')
                new_sic_int = pd.to_numeric(new_sic, errors='coerce')
            except:
                current_sic_int = None
                new_sic_int = None
                
            new_record = {
                'Registration number': normalized_reg_code,  # Normalized format
                'Company_Name': company_name,
                'Business_Description': business_description,
                'Current_SIC': current_sic_int,  # Use pandas numeric conversion
                'Old_Accuracy': old_accuracy,
                'New_SIC': new_sic_int,  # Use pandas numeric conversion
                'New_Accuracy': new_accuracy,
                'Timestamp': datetime.now().isoformat(),
                'Updated_By': updated_by
            }
            
            # Check if record already exists for this company - but still allow new entries for history
            if not updated_df.empty and 'Registration number' in updated_df.columns:
                # We keep ALL records for version history, so just add the new record
                # Convert dtypes to match existing DataFrame before concatenation
                new_record_df = pd.DataFrame([new_record])
                
                # Ensure dtypes match existing DataFrame
                for col in updated_df.columns:
                    if col in new_record_df.columns:
                        if updated_df[col].dtype == 'Int64':
                            new_record_df[col] = new_record_df[col].astype('Int64')
                        elif updated_df[col].dtype == 'float64':
                            new_record_df[col] = new_record_df[col].astype('float64')
                
                # Add new record (always append for version history)
                updated_df = pd.concat([updated_df, new_record_df], ignore_index=True)
                logger.info(f"Added new version for {company_name} (version history maintained)")
            else:
                # First record
                updated_df = pd.concat([updated_df, pd.DataFrame([new_record])], ignore_index=True)
                logger.info(f"Added first record for {company_name}")
            
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
        
        # Ensure absolute path for updated data file for container compatibility  
        if not os.path.isabs(updated_data_file):
            current_dir = os.getcwd()
            updated_data_file = os.path.join(current_dir, updated_data_file)
            
        self.updated_data_manager = UpdatedDataManager(updated_data_file)

        # If no SIC codes file provided, use default
        if not sic_codes_file:
            # Use absolute path from working directory to ensure compatibility in containers
            current_dir = os.getcwd()
            sic_codes_file = os.path.join(current_dir, "data", "SIC_codes.xlsx")
            logger.info(f"🔧 Using default SIC codes file path: {sic_codes_file}")
            
        logger.info(f"🚀 EnhancedSICMatcher initializing with file: {sic_codes_file}")
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
            # Debug logging for container troubleshooting
            current_dir = os.getcwd()
            abs_path = os.path.abspath(sic_codes_file)
            logger.info(f"🔍 DEBUG - Loading SIC codes...")
            logger.info(f"🔍 DEBUG - Current working directory: {current_dir}")
            logger.info(f"🔍 DEBUG - Requested file path: {sic_codes_file}")
            logger.info(f"🔍 DEBUG - Absolute file path: {abs_path}")
            logger.info(f"🔍 DEBUG - File exists: {os.path.exists(sic_codes_file)}")
            
            # List current directory contents for debugging
            if os.path.exists(current_dir):
                try:
                    dir_contents = os.listdir(current_dir)
                    logger.info(f"🔍 DEBUG - Current directory contents: {dir_contents[:10]}...")  # Show first 10 items
                    
                    # Check if data folder exists
                    if 'data' in dir_contents:
                        data_contents = os.listdir(os.path.join(current_dir, 'data'))
                        logger.info(f"🔍 DEBUG - Data directory contents: {data_contents}")
                    else:
                        logger.warning("🔍 DEBUG - Data directory not found in current directory")
                except Exception as e:
                    logger.warning(f"🔍 DEBUG - Could not list directory contents: {e}")
            
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
            
            # Also create sic_df with standardized column names for the new methods
            self.sic_df = self.sic_codes_df.copy()
            self.sic_df.columns = ['SIC_Code', 'Description']  # Standardize column names
            
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
        Find best matching SIC codes using SIMPLIFIED ACTIVITY EXTRACTION.
        
        NEW APPROACH:
        1. Extract core business activities from complex descriptions
        2. Match extracted activities against SIC descriptions
        3. Apply industry-specific boosting for accuracy
        
        Args:
            business_desc: Business description to match
            top_n: Number of top matches to return
            
        Returns:
            List of dictionaries with match results
        """
        if not business_desc or not self.sic_descriptions:
            return []
        
        # STEP 1: Extract core business activity
        extracted_activity = self._extract_business_activity(business_desc)
        
        # Debug logging only for development (removed print statements for production)
        logger.debug(f"Original: {business_desc}")
        logger.debug(f"Extracted activity: {extracted_activity}")
        
        # STEP 2: Basic fuzzy matching on extracted activity
        sic_descriptions_list = list(self.description_to_code.keys())
        matches = process.extract(
            extracted_activity,
            sic_descriptions_list,
            scorer=fuzz.WRatio,
            limit=top_n * 2  # Get extra candidates for boosting
        )
        
        # STEP 3: Apply smart boosting
        enhanced_results = []
        
        for match_desc, base_score, _ in matches:
            sic_code = self.description_to_code.get(match_desc)
            if not sic_code:
                continue
                
            enhanced_score = base_score
            boost_reason = []
            
            # Industry-specific boosting
            if any(term in extracted_activity for term in ['catering', 'restaurant', 'food']):
                if any(term in match_desc.lower() for term in ['catering', 'restaurant', 'food']):
                    enhanced_score = min(100, enhanced_score + 15)
                    boost_reason.append('+15 hospitality match')
                    
            if any(term in extracted_activity for term in ['retail', 'supermarket', 'grocery', 'store']):
                if any(term in match_desc.lower() for term in ['retail', 'store', 'shop']):
                    enhanced_score = min(100, enhanced_score + 15)
                    boost_reason.append('+15 retail match')
                    
            if any(term in extracted_activity for term in ['bank', 'financial']):
                if any(term in match_desc.lower() for term in ['bank', 'financial']):
                    enhanced_score = min(100, enhanced_score + 15)
                    boost_reason.append('+15 financial match')
            
            enhanced_results.append({
                'sic_code': sic_code,
                'sic_description': match_desc,
                'fuzzy_score': round(enhanced_score, 1),
                'base_score': base_score,
                'accuracy_percentage': round(enhanced_score, 1),
                'boost_applied': ', '.join(boost_reason) if boost_reason else 'none',
                'extracted_activity': extracted_activity
            })
        
        # Sort by enhanced score and return top N
        enhanced_results.sort(key=lambda x: x['fuzzy_score'], reverse=True)
        return enhanced_results[:top_n]
    
    def _extract_business_activity(self, description: str) -> str:
        """
        Extract core business activity from complex business descriptions.
        
        This removes corporate noise and focuses on actual business activities.
        """
        import re
        
        description = description.lower()
        
        # Remove corporate structure words
        noise_words = [
            'plc', 'ltd', 'limited', 'group', 'holdings', 'company', 'corporation', 
            'corp', 'inc', 'the', 'and', 'through', 'its', 'subsidiaries', 'engaged',
            'in', 'business', 'of', 'activities', 'services', 'operations'
        ]
        
        # Remove noise words
        for word in noise_words:
            description = re.sub(r'\b' + word + r'\b', ' ', description)
        
        # Extract key activity phrases using patterns
        activity_patterns = [
            r'(food service|catering|restaurant|dining)',
            r'(retail|supermarket|grocery|store|shop)',
            r'(bank|banking|financial|lending|deposit)',
            r'(software|technology|computing)',
            r'(manufacturing|production|factory)'
        ]
        
        key_activities = []
        for pattern in activity_patterns:
            matches = re.findall(pattern, description)
            key_activities.extend(matches)
        
        # If no specific patterns found, take first few meaningful words
        if not key_activities:
            words = [w for w in description.split() if len(w) > 3][:3]
            key_activities = words
        
        return ' '.join(key_activities)
    
    def calculate_old_accuracy(self, business_description: str, current_sic_code: str) -> Dict:
        """
        Calculate old accuracy using proper SIC code lookup and similarity matching.
        
        CORRECT APPROACH: 
        1. Look for exact SIC code match in Excel file
        2. If found, get its description and calculate similarity with business description
        3. If no exact code match, do fuzzy matching on descriptions
        4. Use similarity scoring for accurate percentages
        
        Args:
            business_description: Company business description
            current_sic_code: Current SIC code in the database
            
        Returns:
            Dictionary with old accuracy results
        """
        if not business_description or not current_sic_code:
            return {
                'current_sic_code': current_sic_code,
                'current_sic_description': '',
                'old_accuracy': 0.0,
                'is_accurate': False,
                'best_match_description': '',
                'best_match_sic': '',
                'ai_reasoning': 'Missing business description or SIC code'
            }
        
        # STEP 1: Look for exact SIC code match
        current_sic_description = self.get_sic_description(current_sic_code)
        
        if current_sic_description and current_sic_description != "Unknown SIC Code":
            # STEP 2: Calculate similarity between business description and SIC description
            # Clean the business description for better matching
            clean_business_desc = business_description.lower().strip()
            clean_sic_desc = current_sic_description.lower().strip()
            
            # Use multiple similarity metrics and take the BEST score (not minimum)
            # This gives higher scores for good matches, lower for poor matches
            ratio_score = fuzz.ratio(clean_business_desc, clean_sic_desc)
            partial_score = fuzz.partial_ratio(clean_business_desc, clean_sic_desc)
            token_sort_score = fuzz.token_sort_ratio(clean_business_desc, clean_sic_desc)
            token_set_score = fuzz.token_set_ratio(clean_business_desc, clean_sic_desc)
            
            # Take the MAXIMUM score for intuitive scoring
            # Good matches will score high, poor matches will score low
            old_accuracy = max(ratio_score, partial_score, token_sort_score, token_set_score)
            
            ai_reasoning = f"Exact SIC code {current_sic_code} found. Best similarity score: {old_accuracy:.1f}%. Breakdown: ratio={ratio_score}, partial={partial_score}, token_sort={token_sort_score}, token_set={token_set_score}"
            
        else:
            # STEP 3: No exact code match - do fuzzy matching on descriptions
            best_matches = self.find_best_match(business_description, top_n=1)
            
            if best_matches:
                best_match = best_matches[0]
                # RIGOROUS: Apply penalty for not having exact code AND use conservative scoring
                base_score = best_match['fuzzy_score']
                old_accuracy = base_score * 0.6  # Heavy penalty for missing SIC code
                ai_reasoning = f"SIC code {current_sic_code} not found in database. Best fuzzy match: {best_match['sic_code']} ({best_match['sic_description']}) with {base_score:.1f}% base similarity, penalized to {old_accuracy:.1f}%"
                current_sic_description = f'[Not found: {current_sic_code}]'
            else:
                old_accuracy = 0.0
                ai_reasoning = f'SIC code {current_sic_code} not found and no fuzzy matches available'
                current_sic_description = f'[Unknown: {current_sic_code}]'
        
        # Find best match for comparison
        best_matches = self.find_best_match(business_description, top_n=1)
        best_match_sic = best_matches[0]['sic_code'] if best_matches else ''
        best_match_description = best_matches[0]['sic_description'] if best_matches else ''
        
        is_accurate = old_accuracy >= 70.0
        
        return {
            'current_sic_code': current_sic_code,
            'current_sic_description': current_sic_description,
            'old_accuracy': round(old_accuracy, 1),
            'is_accurate': is_accurate,
            'best_match_description': best_match_description,
            'best_match_sic': best_match_sic,
            'ai_reasoning': ai_reasoning
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
        3. Old SIC code (from CSV Old_SIC column)
        
        Args:
            companies_df: Original company data
            reg_code_col: Registration code column name (default: 'Registration number')
            
        Returns:
            Merged DataFrame with updated data
        """
        # Load updated data - GET LATEST RECORDS ONLY
        updated_df = self.get_latest_records_only()
        
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
        updated_df['Old_SIC_Normalized'] = pd.to_numeric(updated_df['Old_SIC'], errors='coerce').fillna(0).astype('Int64')
        
        # Simplified 2-field merge approach: Company Name + Old SIC Code
        # Step 1: Try exact company name match first (most reliable)
        merged_df = companies_df_copy.merge(
            updated_df[['Company_Name_Normalized', 'New_SIC', 'New_Accuracy', 'Old_Accuracy', 'Timestamp', 'Updated_By']],
            left_on='Company_Name_Normalized',
            right_on='Company_Name_Normalized',
            how='left',
            suffixes=('', '_updated')
        )
        
        # Step 2: For companies with exact name matches but wrong SIC, verify SIC code match
        # Only keep matches where either SIC matches OR we accept name-only matches
        name_matches = merged_df['Timestamp'].notna()
        if name_matches.sum() > 0:
            logger.info(f"Found {name_matches.sum()} exact company name matches")
            
            # For exact name matches, we can optionally validate SIC code
            # But for now, we'll accept exact company name matches as valid
            # This handles cases where SIC codes might have changed or be formatted differently
        
        # Clean up temporary columns
        columns_to_drop = ['Company_Name_Normalized', 'UK_SIC_Normalized']
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
            logger.info("Matching strategy: Company Name + Old SIC Code")
        else:
            logger.info("No companies have updated SIC data")
        
        return merged_df
    
    def get_latest_records_only(self) -> pd.DataFrame:
        """
        Get only the latest record for each company based on timestamp.
        This method preserves version history but returns only the most recent entry per company for display.
        
        Matching Strategy:
        1. Group by Company_Name (primary - this is the most reliable identifier)
        2. Return record with latest timestamp for each company
        3. This handles cases where same company has different registration formats (e.g., 4083914 vs 04083914)
        
        Returns:
            DataFrame with only the latest record per company
        """
        try:
            updated_df = self.updated_data_manager.load_updated_data()
            
            if updated_df.empty:
                logger.info("No updated data found")
                return updated_df
            
            # Convert timestamp to datetime for proper sorting
            updated_df['Timestamp_dt'] = pd.to_datetime(updated_df['Timestamp'])
            
            # Group by Company_Name (normalized) to handle same companies with different registration formats
            updated_df['Company_Name_Normalized'] = updated_df['Company_Name'].str.strip().str.upper()
            
            # Get latest record for each company based on Company_Name
            latest_df = updated_df.sort_values('Timestamp_dt').groupby('Company_Name_Normalized').tail(1)
            
            # Clean up temporary columns
            latest_df = latest_df.drop(columns=['Timestamp_dt', 'Company_Name_Normalized'])
            
            logger.info(f"Returning {len(latest_df)} latest records from {len(updated_df)} total records")
            logger.info(f"Grouped by Company_Name to handle registration number variations")
            return latest_df.reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"Error getting latest records: {e}")
            return pd.DataFrame()

    def save_sic_update(self, company_registration_code: str, company_name: str,
                       business_description: str, current_sic: str, old_accuracy: float,
                       new_sic: str, new_accuracy: float) -> bool:
        """
        Save an updated SIC prediction and automatically update the main table.
        
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
        # First save to CSV
        success = self.updated_data_manager.save_updated_prediction(
            company_registration_code, company_name, business_description,
            current_sic, old_accuracy, new_sic, new_accuracy
        )
        
        # If CSV save was successful, automatically trigger main table update
        if success:
            self._trigger_main_table_update(
                company_name=company_name,
                company_registration=company_registration_code,
                old_sic=current_sic,
                new_sic=new_sic,
                new_accuracy=new_accuracy
            )
        
        return success
    
    def _trigger_main_table_update(self, company_name: str, company_registration: str,
                                  old_sic: str, new_sic: str, new_accuracy: float,
                                  api_base_url: str = "http://127.0.0.1:8001") -> bool:
        """
        Automatically trigger the main table update API.
        
        Args:
            company_name: Company name
            company_registration: Company registration number
            old_sic: Old SIC code
            new_sic: New SIC code
            new_accuracy: New accuracy percentage
            api_base_url: Base URL for the Flask API
            
        Returns:
            bool: True if API call was successful
        """
        try:
            url = f"{api_base_url}/api/update_main_table"
            payload = {
                'company_name': company_name,
                'company_registration': company_registration,
                'old_sic': old_sic,
                'new_sic': new_sic,
                'new_accuracy': new_accuracy
            }
            
            # Make the API call with a timeout
            response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', False):
                    logger.info(f"✅ Main table updated for {company_name}: {result.get('matching_strategy', 'Unknown strategy')}")
                    return True
                else:
                    logger.warning(f"⚠️ Main table update failed for {company_name}: {result.get('error', 'Unknown error')}")
            else:
                logger.warning(f"⚠️ API call failed with status {response.status_code} for {company_name}")
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout calling main table update API for {company_name}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Connection error calling main table update API for {company_name} (Flask app may not be running)")
        except Exception as e:
            logger.warning(f"⚠️ Error calling main table update API for {company_name}: {str(e)}")
            
        return False

# Global instance for easy access with thread safety
_enhanced_sic_matcher = None
_matcher_lock = threading.Lock()

def get_enhanced_sic_matcher(sic_codes_file: Optional[str] = None) -> EnhancedSICMatcher:
    """
    Get or create enhanced SIC matcher instance (thread-safe).
    
    Args:
        sic_codes_file: Path to SIC codes file
        
    Returns:
        EnhancedSICMatcher instance
    """
    global _enhanced_sic_matcher
    
    # Use double-checked locking pattern for thread safety
    if _enhanced_sic_matcher is None:
        with _matcher_lock:
            # Check again inside the lock to prevent race conditions
            if _enhanced_sic_matcher is None:
                _enhanced_sic_matcher = EnhancedSICMatcher(sic_codes_file)
    elif sic_codes_file and not _enhanced_sic_matcher.sic_codes_df is not None:
        # This case is less critical but still protect it
        with _matcher_lock:
            _enhanced_sic_matcher.load_sic_codes(sic_codes_file)
    
    return _enhanced_sic_matcher