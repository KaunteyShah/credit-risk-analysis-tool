"""
Base Repository Interface

This abstract base class defines common operations that all repositories should support.
It provides a foundation for consistent data access patterns across the application.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
import pandas as pd

T = TypeVar('T')

class BaseRepositoryInterface(ABC, Generic[T]):
    """Abstract base repository interface"""
    
    @abstractmethod
    def get_all(self) -> pd.DataFrame:
        """
        Get all records as a pandas DataFrame
        
        Returns:
            pd.DataFrame: All records in the repository
        """
        pass
    
    @abstractmethod
    def get_by_id(self, record_id: str) -> Optional[T]:
        """
        Get a single record by its ID
        
        Args:
            record_id (str): The unique identifier for the record
            
        Returns:
            Optional[T]: The record if found, None otherwise
        """
        pass
    
    @abstractmethod
    def search(self, criteria: Dict[str, Any]) -> pd.DataFrame:
        """
        Search for records matching the given criteria
        
        Args:
            criteria (Dict[str, Any]): Search criteria
            
        Returns:
            pd.DataFrame: Matching records
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Get total number of records
        
        Returns:
            int: Total record count
        """
        pass
    
    @abstractmethod
    def exists(self, record_id: str) -> bool:
        """
        Check if a record exists
        
        Args:
            record_id (str): The unique identifier to check
            
        Returns:
            bool: True if record exists, False otherwise
        """
        pass