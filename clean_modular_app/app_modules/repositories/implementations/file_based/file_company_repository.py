"""
File-Based Company Repository Implementation

This repository implementation wraps the existing CSV/Excel file handling logic
from flask_main.py, preserving all current functionality while providing
clean repository interface compliance.
"""

import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any

from app_modules.repositories.interfaces.company_repository_interface import CompanyRepositoryInterface
from app_modules.utils.logger import logger
from app_modules.utils.simulation import simulation_service, is_demo_mode

class FileCompanyRepository(CompanyRepositoryInterface):
    """
    File-based repository implementation using existing CSV/Excel logic.
    
    This implementation preserves all the original data loading and processing
    logic from flask_main.py while providing a clean repository interface.
    """
    
    def __init__(self, data_path: str = None):
        """Initialize repository with data path"""
        self.data_path = data_path or 'data'
        self._company_data: Optional[pd.DataFrame] = None
        self._sic_codes: Optional[pd.DataFrame] = None
        self._sic_matcher = None
        self._data_loaded = False
        
        logger.info("FileCompanyRepository initialized")
    
    def _clean_numeric_column(self, series):
        """Clean and convert a series to numeric values (from flask_main.py)"""
        cleaned = series.astype(str).str.replace(',', '').str.replace('$', '').str.replace('€', '')
        return pd.to_numeric(cleaned, errors='coerce')
    
    def _find_data_file(self, filename: str) -> Optional[str]:
        """Helper function to find data files with relative paths"""        
        possible_paths = [
            os.path.join('data', filename),
            os.path.join('.', 'data', filename),
            os.path.join('..', 'data', filename),
            os.path.join('..', '..', 'data', filename),
            filename,  # In case it's already a full path
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        # If not found in relative paths, try from current working directory
        cwd_path = os.path.join(os.getcwd(), 'data', filename)
        if os.path.exists(cwd_path):
            return cwd_path
            
        return None
    
    def _ensure_data_loaded(self):
        """Ensure data is loaded before operations"""
        if not self._data_loaded:
            self._load_company_data()
    
    def _load_company_data(self):
        """
        Load and prepare company data with robust error handling.
        
        This method extracts and preserves the exact logic from flask_main.py
        load_company_data() function to ensure identical behavior.
        """
        try:
            logger.info("Loading company data...")
            
            # Find company data file (exact logic from flask_main.py)
            company_file = self._find_data_file('Sample_data2.csv')
            if company_file:
                logger.info(f"Found company data file at: {company_file}")
                
                try:
                    self._company_data = pd.read_csv(company_file)
                    logger.info(f"Loaded {len(self._company_data)} companies from CSV")
                    
                    # Clean numeric columns (exact logic from flask_main.py)
                    numeric_columns = ['Employees (Total)', 'Sales (USD)', 'Pre Tax Profit (USD)']
                    for col in numeric_columns:
                        if col in self._company_data.columns:
                            self._company_data[col] = self._clean_numeric_column(self._company_data[col])
                    
                    # Load SIC codes and initialize enhanced fuzzy matching
                    sic_file = self._find_data_file('SIC_codes.xlsx')
                    if sic_file:
                        logger.info(f"Found SIC codes file at: {sic_file}")
                        try:
                            # Try to initialize enhanced SIC matcher (exact logic from flask_main.py)
                            try:
                                from app_modules.utils.enhanced_sic_matcher import get_enhanced_sic_matcher
                                logger.info("Enhanced SIC matcher import successful")
                                
                                self._sic_matcher = get_enhanced_sic_matcher(sic_file)
                                logger.info("Enhanced SIC matcher initialization successful")
                                
                                # Calculate dual accuracy using enhanced fuzzy matching
                                logger.info("Calculating dual SIC accuracy using enhanced fuzzy matching...")
                                self._company_data = self._sic_matcher.batch_calculate_dual_accuracy(self._company_data)
                                
                                # Merge with any existing updated data
                                self._company_data = self._sic_matcher.merge_with_updated_data(self._company_data)
                                
                                logger.info("Enhanced SIC accuracy calculation completed")
                                
                            except ImportError as import_error:
                                logger.warning(f"Enhanced SIC matcher not available: {import_error}")
                                self._sic_matcher = None
                                self._generate_accuracy_data()
                            
                            except Exception as matcher_error:
                                logger.error(f"Enhanced SIC matcher initialization failed: {matcher_error}")
                                self._sic_matcher = None
                                self._generate_accuracy_data()
                                
                        except Exception as sic_error:
                            logger.error(f"Enhanced SIC matcher failed: {sic_error}")
                            self._sic_matcher = None
                            self._generate_accuracy_data()
                    else:
                        logger.warning(f"SIC codes file not found")
                        self._generate_accuracy_data()
                        
                except Exception as data_error:
                    logger.error(f"Error processing company data: {data_error}")
                    raise Exception(f"Failed to process company data: {data_error}")
                    
            else:
                raise FileNotFoundError("Company data file not found in any expected location!")
            
            # Load SIC codes for reference (exact logic from flask_main.py)
            try:
                sic_file = self._find_data_file('SIC_codes.xlsx')
                if sic_file:
                    self._sic_codes = pd.read_excel(sic_file)
                    logger.info(f"Loaded {len(self._sic_codes)} SIC codes")
                else:
                    logger.warning("SIC codes file not found")
                    self._sic_codes = None
            except Exception as sic_error:
                logger.error(f"Error loading SIC codes: {sic_error}")
                self._sic_codes = None
            
            self._data_loaded = True
            logger.info("Company data loading completed successfully")
                
        except Exception as e:
            logger.error(f"Critical error loading data: {str(e)}")
            raise Exception(f"Data loading failed: {str(e)}")
    
    def _generate_accuracy_data(self):
        """Generate accuracy data when SIC matcher is not available"""
        logger.info("Generating SIC accuracy data...")
        
        # Add required columns for consistency (exact logic from flask_main.py)
        if 'Old_Accuracy' not in self._company_data.columns:
            if is_demo_mode():
                self._company_data['Old_Accuracy'] = simulation_service.generate_sic_accuracy(len(self._company_data)) * 100
            else:
                # Use default accuracy when not in demo mode
                self._company_data['Old_Accuracy'] = np.random.uniform(70, 90, len(self._company_data))
        if 'New_Accuracy' not in self._company_data.columns:
            self._company_data['New_Accuracy'] = None
    
    # Repository Interface Implementation
    
    def get_companies_paginated(self, page: int = 1, limit: int = 50, 
                               country: Optional[str] = None, 
                               search: Optional[str] = None) -> Dict[str, Any]:
        """
        Get paginated company data with filtering - EXACT replica of /api/companies logic
        
        This method replicates the exact filtering, pagination, and response format
        from the original /api/companies route handler.
        """
        try:
            self._ensure_data_loaded()
            
            # Handle empty dataset (exact logic from original)
            if self._company_data is None or len(self._company_data) == 0:
                return {
                    'data': [],
                    'total': 0,
                    'page': page,
                    'limit': limit,
                    'total_pages': 0
                }
            
            # Start with full dataset (exact logic from original)
            filtered_data = self._company_data.copy()
            
            # Apply country filter (exact logic from original)
            if country and country != 'all' and 'Country' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['Country'] == country]
            
            # Apply search filter if provided (exact logic from original)
            if search and 'Company Name' in filtered_data.columns:
                filtered_data = filtered_data[
                    filtered_data['Company Name'].str.contains(search, case=False, na=False)
                ]
            
            # Calculate pagination (exact logic from original)
            total = len(filtered_data)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            # Get paginated data (exact logic from original)
            data_subset = filtered_data.iloc[start_idx:end_idx]
            
            # Convert to JSON-compatible format (exact logic from original)
            records = []
            for idx, (original_idx, row) in enumerate(data_subset.iterrows()):
                # Get the actual dataset index
                dataset_index = original_idx if isinstance(original_idx, int) else idx
                record = {
                    '_index': dataset_index,  # Add the original dataset index
                    'Company Name': str(row.get('Company Name', '')),
                    'Country': str(row.get('Country', '')),
                    'Employees (Total)': float(row['Employees (Total)']) if pd.notna(row.get('Employees (Total)')) else None,
                    'Sales (USD)': float(row['Sales (USD)']) if pd.notna(row.get('Sales (USD)')) else None,
                    'UK SIC 2007 Code': str(row.get('UK SIC 2007 Code', '')),
                    'Old_Accuracy': float(row.get('Old_Accuracy', 0)) if pd.notna(row.get('Old_Accuracy')) else 0,
                    'New_Accuracy': float(row.get('New_Accuracy', 0)) if pd.notna(row.get('New_Accuracy')) else 0,
                    'New_SIC': str(row.get('New_SIC', '')) if pd.notna(row.get('New_SIC')) else None
                }
                records.append(record)
            
            # Return exact same response format as original
            return {
                'data': records,
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error in get_companies_paginated: {str(e)}")
            # Return empty result on error (same as original)
            return {
                'data': [],
                'total': 0,
                'page': page,
                'limit': limit,
                'total_pages': 0,
                'error': str(e)
            }

    def get_all_companies(self) -> pd.DataFrame:
        """Get all company data as DataFrame"""
        self._ensure_data_loaded()
        if self._company_data is None:
            raise Exception("Company data not available")
        return self._company_data.copy()
    
    def get_company_by_registration(self, registration: str) -> Optional[Dict[str, Any]]:
        """Get a specific company by registration number"""
        self._ensure_data_loaded()
        if self._company_data is None:
            return None
            
        company_row = self._company_data[
            self._company_data['Company_Registration'] == registration
        ]
        
        return company_row.iloc[0].to_dict() if not company_row.empty else None
    
    def get_companies_by_sic_code(self, sic_code: str) -> pd.DataFrame:
        """Get all companies with a specific SIC code"""
        self._ensure_data_loaded()
        if self._company_data is None:
            return pd.DataFrame()
            
        return self._company_data[
            self._company_data['SIC_Code'] == sic_code
        ].copy()
    
    def search_companies_by_name(self, name_query: str) -> pd.DataFrame:
        """Search companies by name (partial match)"""
        self._ensure_data_loaded()
        if self._company_data is None:
            return pd.DataFrame()
            
        return self._company_data[
            self._company_data['Company_Name'].str.contains(name_query, case=False, na=False)
        ].copy()
    
    def update_company_sic_prediction(self, registration: str, sic_code: str, 
                                    confidence: float, algorithm: str) -> bool:
        """Update a company's predicted SIC code"""
        self._ensure_data_loaded()
        if self._company_data is None:
            return False
            
        mask = self._company_data['Company_Registration'] == registration
        if not mask.any():
            return False
            
        # Update the prediction data
        self._company_data.loc[mask, 'Predicted_SIC'] = sic_code
        self._company_data.loc[mask, 'New_Accuracy'] = confidence * 100  # Convert to percentage
        self._company_data.loc[mask, 'Algorithm_Used'] = algorithm
        
        logger.info(f"Updated SIC prediction for {registration}: {sic_code} (confidence: {confidence:.2f})")
        return True
    
    def update_company_revenue(self, registration: str, revenue: float) -> bool:
        """Update a company's revenue/turnover data"""
        self._ensure_data_loaded()
        if self._company_data is None:
            return False
            
        mask = self._company_data['Company_Registration'] == registration
        if not mask.any():
            return False
            
        # Update revenue (try multiple possible column names)
        revenue_columns = ['Sales (USD)', 'Revenue', 'Turnover']
        updated = False
        for col in revenue_columns:
            if col in self._company_data.columns:
                self._company_data.loc[mask, col] = revenue
                updated = True
                break
        
        if updated:
            logger.info(f"Updated revenue for {registration}: ${revenue:,.2f}")
        
        return updated
    
    def get_companies_requiring_sic_prediction(self) -> pd.DataFrame:
        """Get companies that need SIC code prediction"""
        self._ensure_data_loaded()
        if self._company_data is None:
            return pd.DataFrame()
            
        # Companies without SIC codes or with low confidence predictions
        needs_prediction = (
            self._company_data['SIC_Code'].isna() | 
            (self._company_data['Old_Accuracy'] < 80)
        )
        
        return self._company_data[needs_prediction].copy()
    
    def get_revenue_statistics(self) -> Dict[str, Any]:
        """Get revenue statistics across all companies"""
        self._ensure_data_loaded()
        if self._company_data is None:
            return {}
            
        # Try to find revenue column
        revenue_col = None
        for col in ['Sales (USD)', 'Revenue', 'Turnover']:
            if col in self._company_data.columns:
                revenue_col = col
                break
        
        if revenue_col is None:
            return {'error': 'No revenue column found'}
            
        revenue_data = self._company_data[revenue_col].dropna()
        
        return {
            'count': len(revenue_data),
            'mean': float(revenue_data.mean()),
            'median': float(revenue_data.median()),
            'min': float(revenue_data.min()),
            'max': float(revenue_data.max()),
            'std': float(revenue_data.std())
        }
    
    def get_companies_by_revenue_range(self, min_revenue: float, 
                                     max_revenue: float) -> pd.DataFrame:
        """Get companies within a specific revenue range"""
        self._ensure_data_loaded()
        if self._company_data is None:
            return pd.DataFrame()
            
        # Find revenue column
        revenue_col = None
        for col in ['Sales (USD)', 'Revenue', 'Turnover']:
            if col in self._company_data.columns:
                revenue_col = col
                break
        
        if revenue_col is None:
            return pd.DataFrame()
            
        return self._company_data[
            (self._company_data[revenue_col] >= min_revenue) &
            (self._company_data[revenue_col] <= max_revenue)
        ].copy()
    
    # Base Repository Interface Methods
    
    def get_all(self) -> pd.DataFrame:
        """Get all records as DataFrame (base method)"""
        return self.get_all_companies()
    
    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get record by ID (base method)"""
        return self.get_company_by_registration(record_id)
    
    def search(self, criteria: Dict[str, Any]) -> pd.DataFrame:
        """Search records by criteria (base method)"""
        if 'name' in criteria:
            return self.search_companies_by_name(criteria['name'])
        elif 'sic_code' in criteria:
            return self.get_companies_by_sic_code(criteria['sic_code'])
        else:
            return self.get_all_companies()
    
    def count(self) -> int:
        """Get total number of records"""
        self._ensure_data_loaded()
        return len(self._company_data) if self._company_data is not None else 0
    
    def exists(self, record_id: str) -> bool:
        """Check if a record exists"""
        return self.get_company_by_registration(record_id) is not None
    
    def get_company_by_index(self, company_index: int) -> Optional[Dict[str, Any]]:
        """Get company data by index with comprehensive details"""
        try:
            # Ensure data is loaded
            if self._company_data is None:
                self._load_company_data()
            
            if self._company_data is None or company_index < 0 or company_index >= len(self._company_data):
                return None
            
            # Get company data at index and handle NaN values
            company_series = self._company_data.iloc[company_index]
            # Replace NaN values with None (which becomes null in JSON)
            company = company_series.where(pd.notnull(company_series), None).to_dict()
            return company
            
        except Exception as e:
            logger.error(f"Error getting company by index {company_index}: {e}")
            return None
    
    def get_company_by_name(self, company_name: str, 
                           registration_number: Optional[str] = None,
                           sic_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get company data by name with optional filtering by registration and SIC"""
        try:
            # Ensure data is loaded
            if self._company_data is None:
                self._load_company_data()
            
            if self._company_data is None:
                return None
            
            # Start with name-based filtering (case-insensitive)
            matches = self._company_data[
                self._company_data['Company Name'].str.upper() == company_name.upper()
            ]
            
            # If no exact match, try fuzzy matching
            if matches.empty:
                # Try contains matching
                matches = self._company_data[
                    self._company_data['Company Name'].str.upper().str.contains(
                        company_name.upper(), na=False
                    )
                ]
            
            # Additional filtering by registration number if provided
            if registration_number and not matches.empty:
                # Check multiple possible registration fields
                reg_matches = pd.DataFrame()
                
                for reg_field in ['Company Registration Number', 'Registration Number', 'Company Number']:
                    if reg_field in matches.columns:
                        field_matches = matches[
                            matches[reg_field].astype(str).str.upper() == registration_number.upper()
                        ]
                        if not field_matches.empty:
                            reg_matches = field_matches
                            break
                
                if not reg_matches.empty:
                    matches = reg_matches
            
            # Additional filtering by SIC code if provided
            if sic_code and not matches.empty:
                if 'SIC Code (SIC 2007)' in matches.columns:
                    sic_matches = matches[
                        matches['SIC Code (SIC 2007)'].astype(str) == sic_code
                    ]
                    if not sic_matches.empty:
                        matches = sic_matches
            
            # Return the first match (most relevant)
            if not matches.empty:
                company = matches.iloc[0].to_dict()
                logger.info(f"Found company by name '{company_name}': {company.get('Company Name')}")
                return company
            
            logger.warning(f"No company found with name '{company_name}'")
            return None
            
        except Exception as e:
            logger.error(f"Error getting company by name '{company_name}': {e}")
            return None
    
    def get_companies_count(self) -> int:
        """Get total count of companies - with lazy loading"""
        try:
            # Use lazy loading pattern
            self._ensure_data_loaded()
            
            return len(self._company_data) if self._company_data is not None else 0
            
        except Exception as e:
            logger.error(f"Error getting companies count: {e}")
            return 0
    
    def is_data_loaded(self) -> bool:
        """Check if data is loaded without triggering load"""
        return self._data_loaded and self._company_data is not None
        
    def get_data_status(self) -> Dict[str, Any]:
        """Get data loading status without triggering load"""
        return {
            'loaded': self._data_loaded,
            'has_company_data': self._company_data is not None,
            'has_sic_codes': self._sic_codes is not None,
            'has_sic_matcher': self._sic_matcher is not None,
            'company_count': len(self._company_data) if self._company_data is not None else 0
        }
    
    def load_company_data(self) -> bool:
        """Load company data if not already loaded"""
        try:
            if self._company_data is None:
                self._load_company_data()
            
            return self._company_data is not None
            
        except Exception:
            return False
    
    # Additional properties for compatibility
    
    @property
    def sic_matcher(self):
        """Get SIC matcher instance (for compatibility with existing code)"""
        self._ensure_data_loaded()
        return self._sic_matcher
    
    @property
    def sic_codes(self) -> Optional[pd.DataFrame]:
        """Get SIC codes DataFrame (for compatibility with existing code)"""
        self._ensure_data_loaded()
        return self._sic_codes
    
    def refresh_data(self) -> bool:
        """Refresh/reload company data from source after updates"""
        try:
            logger.info("Refreshing company data after SIC update...")
            
            # Reset loaded flag to force reload
            self._data_loaded = False
            self._company_data = None
            
            # Reload data with updated information
            self._load_company_data()
            
            logger.info("Company data refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh company data: {e}")
            return False