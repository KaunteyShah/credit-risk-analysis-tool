"""
SIC Repository Interface

This interface defines operations for Standard Industrial Classification (SIC) code management.
It handles SIC code lookups, mappings, and hierarchical relationships.
"""

from abc import abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
from .base_repository import BaseRepositoryInterface

class SicRepositoryInterface(BaseRepositoryInterface[Dict[str, Any]]):
    """Interface for SIC code operations"""
    
    @abstractmethod
    def get_all_sic_codes(self) -> pd.DataFrame:
        """
        Get all SIC codes with descriptions
        
        Returns:
            pd.DataFrame: All SIC codes with columns:
                - SIC_Code: The SIC code
                - Description: SIC code description
                - Section: SIC section (A, B, C, etc.)
                - Division: SIC division
                - Group: SIC group
        """
        pass
    
    @abstractmethod
    def get_sic_code_details(self, sic_code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific SIC code
        
        Args:
            sic_code (str): The SIC code to lookup
            
        Returns:
            Optional[Dict[str, Any]]: SIC code details if found, None otherwise
        """
        pass
    
    @abstractmethod
    def search_sic_codes_by_description(self, description_query: str) -> pd.DataFrame:
        """
        Search SIC codes by description keywords
        
        Args:
            description_query (str): Keywords to search in descriptions
            
        Returns:
            pd.DataFrame: SIC codes matching the description query
        """
        pass
    
    @abstractmethod
    def get_sic_codes_by_section(self, section: str) -> pd.DataFrame:
        """
        Get all SIC codes in a specific section
        
        Args:
            section (str): SIC section (A, B, C, etc.)
            
        Returns:
            pd.DataFrame: SIC codes in the specified section
        """
        pass
    
    @abstractmethod
    def get_sic_hierarchy(self) -> Dict[str, Any]:
        """
        Get the hierarchical structure of SIC codes
        
        Returns:
            Dict[str, Any]: Hierarchical structure with sections, divisions, groups
        """
        pass
    
    @abstractmethod
    def predict_sic_from_description(self, business_description: str) -> Dict[str, Any]:
        """
        Predict SIC code based on business description
        
        Args:
            business_description (str): Company business description
            
        Returns:
            Dict[str, Any]: Prediction result with:
                - sic_code: Predicted SIC code
                - confidence: Prediction confidence
                - alternatives: Alternative predictions
                - method: Prediction method used
        """
        pass
    
    @abstractmethod
    def get_similar_sic_codes(self, sic_code: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get SIC codes similar to the given one
        
        Args:
            sic_code (str): Reference SIC code
            limit (int): Maximum number of similar codes to return
            
        Returns:
            List[Dict[str, Any]]: Similar SIC codes with similarity scores
        """
        pass
    
    @abstractmethod
    def validate_sic_code(self, sic_code: str) -> bool:
        """
        Validate if a SIC code exists and is properly formatted
        
        Args:
            sic_code (str): SIC code to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_sic_mapping_confidence_stats(self) -> Dict[str, Any]:
        """
        Get statistics about SIC code prediction confidence across all companies
        
        Returns:
            Dict[str, Any]: Statistics about prediction confidence levels
        """
        pass