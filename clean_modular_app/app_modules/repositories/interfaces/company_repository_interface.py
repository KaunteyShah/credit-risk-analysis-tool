"""
Company Repository Interface

This interface defines all operations related to company data management.
It abstracts the data source (files, database, API) from the business logic.
"""

from abc import abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
from .base_repository import BaseRepositoryInterface

class CompanyRepositoryInterface(BaseRepositoryInterface[Dict[str, Any]]):
    """
Repository interface for company data operations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class CompanyRepositoryInterface(ABC):
    """Repository interface for company data operations"""
    
    @abstractmethod
    def get_companies_paginated(self, page: int, limit: int, country: Optional[str] = None, 
                               search: Optional[str] = None) -> Dict[str, Any]:
        """Get paginated companies with optional filtering"""
        pass
    
    @abstractmethod
    def get_company_by_index(self, company_index: int) -> Optional[Dict[str, Any]]:
        """Get company data by index with comprehensive details"""
        pass
    
    @abstractmethod
    def get_company_by_name(self, company_name: str, 
                           registration_number: Optional[str] = None,
                           sic_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get company data by name with optional filtering by registration and SIC"""
        pass
    
    @abstractmethod
    def get_companies_count(self) -> int:
        """Get total count of companies"""
        pass
    
    @abstractmethod
    def load_company_data(self) -> bool:
        """Load company data if not already loaded"""
        pass
    
    @abstractmethod
    def get_all_companies(self) -> pd.DataFrame:
        """
        Get all company data as DataFrame
        
        Returns:
            pd.DataFrame: All company records with standard columns:
                - Company_Registration: Unique company identifier
                - Company_Name: Company name
                - Business_Description: Business description
                - SIC_Code: Standard Industrial Classification code
                - Revenue: Company revenue/turnover
                - ... other company fields
        """
        pass
    
    @abstractmethod
    def get_company_by_registration(self, registration: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific company by registration number
        
        Args:
            registration (str): Company registration number
            
        Returns:
            Optional[Dict[str, Any]]: Company data if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_companies_paginated(self, page: int = 1, limit: int = 50, 
                               country: Optional[str] = None, 
                               search: Optional[str] = None) -> Dict[str, Any]:
        """
        Get paginated company data with filtering (matches /api/companies exactly)
        
        Args:
            page (int): Page number (1-based)
            limit (int): Records per page
            country (Optional[str]): Country filter ('all' or specific country)
            search (Optional[str]): Search term for company names
            
        Returns:
            Dict[str, Any]: {
                'data': List[Dict], # Company records in exact format
                'total': int,       # Total records (after filtering)
                'page': int,        # Current page
                'limit': int,       # Records per page
                'total_pages': int  # Total pages
            }
        """
        pass

    @abstractmethod
    def get_companies_by_sic_code(self, sic_code: str) -> pd.DataFrame:
        """
        Get all companies with a specific SIC code
        
        Args:
            sic_code (str): SIC code to filter by
            
        Returns:
            pd.DataFrame: Companies with the specified SIC code
        """
        pass
    
    @abstractmethod
    def search_companies_by_name(self, name_query: str) -> pd.DataFrame:
        """
        Search companies by name (partial match)
        
        Args:
            name_query (str): Company name search term
            
        Returns:
            pd.DataFrame: Companies matching the name query
        """
        pass
    
    @abstractmethod
    def update_company_sic_prediction(self, registration: str, sic_code: str, 
                                    confidence: float, algorithm: str) -> bool:
        """
        Update a company's predicted SIC code
        
        Args:
            registration (str): Company registration number
            sic_code (str): Predicted SIC code
            confidence (float): Prediction confidence (0.0 to 1.0)
            algorithm (str): Algorithm used for prediction
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def update_company_revenue(self, registration: str, revenue: float) -> bool:
        """
        Update a company's revenue/turnover data
        
        Args:
            registration (str): Company registration number
            revenue (float): Updated revenue value
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_companies_requiring_sic_prediction(self) -> pd.DataFrame:
        """
        Get companies that need SIC code prediction
        
        Returns:
            pd.DataFrame: Companies without SIC codes or with low confidence predictions
        """
        pass
    
    @abstractmethod
    def get_revenue_statistics(self) -> Dict[str, Any]:
        """
        Get revenue statistics across all companies
        
        Returns:
            Dict[str, Any]: Statistics including mean, median, min, max revenue
        """
        pass
    
    @abstractmethod
    def get_companies_by_revenue_range(self, min_revenue: float, 
                                     max_revenue: float) -> pd.DataFrame:
        """
        Get companies within a specific revenue range
        
        Args:
            min_revenue (float): Minimum revenue
            max_revenue (float): Maximum revenue
            
        Returns:
            pd.DataFrame: Companies within the revenue range
        """
        pass
    
    @abstractmethod
    def is_data_loaded(self) -> bool:
        """Check if data is loaded without triggering load"""
        pass
        
    @abstractmethod
    def get_data_status(self) -> Dict[str, Any]:
        """Get data loading status without triggering load"""
        pass
    
    @abstractmethod
    def refresh_data(self) -> bool:
        """Refresh/reload company data from source after updates"""
        pass