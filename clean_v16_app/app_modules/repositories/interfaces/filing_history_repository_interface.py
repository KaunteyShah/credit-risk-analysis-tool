"""
Repository interface for Companies House filing history operations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class FilingHistoryRepositoryInterface(ABC):
    """Repository interface for Companies House filing history data operations"""
    
    @abstractmethod
    def insert_filing_record(self, filing_data: Dict[str, Any]) -> bool:
        """
        Insert a new filing history record
        
        Args:
            filing_data: Complete filing information including API response
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_latest_filing_by_unique_id(self, unique_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent filing record for a company by unique_id
        
        Args:
            unique_id: Company unique identifier
            
        Returns:
            Latest filing record or None
        """
        pass
    
    @abstractmethod
    def get_filing_history_by_unique_id(self, unique_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get filing history for a company by unique_id
        
        Args:
            unique_id: Company unique identifier
            limit: Maximum number of records to return
            
        Returns:
            List of filing records (most recent first)
        """
        pass
    
    @abstractmethod
    def check_filing_exists(self, unique_id: str, transaction_id: str) -> bool:
        """
        Check if a specific filing already exists
        
        Args:
            unique_id: Company unique identifier
            transaction_id: Filing transaction ID from Companies House
            
        Returns:
            True if filing exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_companies_without_recent_filings(self, days_threshold: int = 365) -> List[Dict[str, Any]]:
        """
        Get companies that don't have recent filing data
        
        Args:
            days_threshold: Number of days to consider as "recent"
            
        Returns:
            List of companies needing filing updates
        """
        pass
    
    @abstractmethod
    def get_all_latest_filings_for_portal(self) -> List[Dict[str, Any]]:
        """
        Get latest filing for each company (for company portal view)
        
        Returns:
            List of latest filings grouped by unique_id
        """
        pass
    
    @abstractmethod
    def update_filing_record(self, unique_id: str, transaction_id: str, 
                           updated_data: Dict[str, Any]) -> bool:
        """
        Update an existing filing record
        
        Args:
            unique_id: Company unique identifier
            transaction_id: Filing transaction ID
            updated_data: Updated filing information
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_old_filings(self, days_to_keep: int = 730) -> int:
        """
        Clean up old filing records (optional maintenance)
        
        Args:
            days_to_keep: Number of days of history to retain
            
        Returns:
            Number of records deleted
        """
        pass

    @abstractmethod
    def update_extracted_revenue(self, unique_id: str, transaction_id: str, 
                               extracted_revenue: str) -> bool:
        """
        Update the extracted_revenue field for a specific filing record
        
        Args:
            unique_id: Company unique identifier
            transaction_id: Filing transaction ID
            extracted_revenue: The extracted revenue value to store
            
        Returns:
            True if successful, False otherwise
        """
        pass