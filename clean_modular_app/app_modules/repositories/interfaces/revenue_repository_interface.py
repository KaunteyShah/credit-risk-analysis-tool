"""
Revenue Repository Interface

This interface defines operations for revenue and financial data management.
It handles revenue calculations, predictions, and financial analytics.
"""

from abc import abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
from .base_repository import BaseRepositoryInterface

class RevenueRepositoryInterface(BaseRepositoryInterface[Dict[str, Any]]):
    """Interface for revenue and financial data operations"""
    
    @abstractmethod
    def get_all_revenue_data(self) -> pd.DataFrame:
        """
        Get all revenue data across companies
        
        Returns:
            pd.DataFrame: Revenue data with columns:
                - Company_Registration: Company identifier
                - Revenue: Actual revenue
                - Estimated_Turnover: Estimated turnover
                - Revenue_Source: Source of revenue data
                - Last_Updated: When revenue was last updated
        """
        pass
    
    @abstractmethod
    def get_company_revenue(self, registration: str) -> Optional[Dict[str, Any]]:
        """
        Get revenue data for a specific company
        
        Args:
            registration (str): Company registration number
            
        Returns:
            Optional[Dict[str, Any]]: Revenue data if found, None otherwise
        """
        pass
    
    @abstractmethod
    def estimate_revenue_from_business_description(self, business_description: str, 
                                                 sic_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Estimate revenue based on business description and SIC code
        
        Args:
            business_description (str): Company business description
            sic_code (Optional[str]): SIC code for more accurate estimation
            
        Returns:
            Dict[str, Any]: Revenue estimation with:
                - estimated_revenue: Estimated revenue value
                - confidence: Estimation confidence
                - method: Estimation method used
                - range: Revenue range (min, max)
        """
        pass
    
    @abstractmethod
    def get_revenue_statistics_by_sic(self, sic_code: str) -> Dict[str, Any]:
        """
        Get revenue statistics for companies in a specific SIC code
        
        Args:
            sic_code (str): SIC code to analyze
            
        Returns:
            Dict[str, Any]: Revenue statistics for the SIC code
        """
        pass
    
    @abstractmethod
    def get_revenue_distribution(self) -> Dict[str, Any]:
        """
        Get overall revenue distribution statistics
        
        Returns:
            Dict[str, Any]: Revenue distribution data with percentiles, quartiles
        """
        pass
    
    @abstractmethod
    def update_company_revenue_data(self, registration: str, revenue: float, 
                                  source: str = "user_input") -> bool:
        """
        Update revenue data for a company
        
        Args:
            registration (str): Company registration number
            revenue (float): New revenue value
            source (str): Source of the revenue data
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_companies_without_revenue_data(self) -> pd.DataFrame:
        """
        Get companies that don't have revenue data
        
        Returns:
            pd.DataFrame: Companies missing revenue information
        """
        pass
    
    @abstractmethod
    def calculate_revenue_growth_potential(self, registration: str) -> Dict[str, Any]:
        """
        Calculate revenue growth potential for a company
        
        Args:
            registration (str): Company registration number
            
        Returns:
            Dict[str, Any]: Growth potential analysis
        """
        pass
    
    @abstractmethod
    def get_industry_revenue_benchmarks(self, sic_code: str) -> Dict[str, Any]:
        """
        Get revenue benchmarks for a specific industry (SIC code)
        
        Args:
            sic_code (str): SIC code for industry analysis
            
        Returns:
            Dict[str, Any]: Industry revenue benchmarks
        """
        pass