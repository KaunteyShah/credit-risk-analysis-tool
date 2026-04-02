"""
Repository interfaces defining data access patterns.
Abstract base classes for implementing repository pattern.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from ..models import Company, SICCode, CompanySICCode, CompanyFinancial, APIAuditLog, SICPredictionHistory


class BaseRepository(ABC):
    """
    Abstract base repository defining common data access patterns.
    """
    
    @abstractmethod
    def create(self, entity: Any) -> Optional[int]:
        """Create a new entity and return its ID."""
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[Any]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    def update(self, entity_id: int, updates: Dict[str, Any]) -> bool:
        """Update entity by ID with provided data."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete entity by ID."""
        pass
    
    @abstractmethod
    def list_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Any]:
        """List all entities with optional pagination."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Get total count of entities."""
        pass


class ICompanyRepository(BaseRepository):
    """
    Interface for Company data access operations.
    """
    
    @abstractmethod
    def get_by_company_number(self, company_number: str) -> Optional[Company]:
        """Get company by company number."""
        pass
    
    @abstractmethod
    def search_by_name(self, name: str, limit: Optional[int] = None) -> List[Company]:
        """Search companies by name pattern."""
        pass
    
    @abstractmethod
    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[Company]:
        """Get companies by status."""
        pass
    
    @abstractmethod
    def get_companies_with_sic_codes(self, company_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Get companies with their associated SIC codes."""
        pass
    
    @abstractmethod
    def search_companies(self, filters: Dict[str, Any], limit: Optional[int] = None, offset: Optional[int] = None) -> List[Company]:
        """Advanced search with multiple filters."""
        pass


class ISICCodeRepository(BaseRepository):
    """
    Interface for SIC Code data access operations.
    """
    
    @abstractmethod
    def get_by_sic_code(self, sic_code: str) -> Optional[SICCode]:
        """Get SIC code by code value."""
        pass
    
    @abstractmethod
    def search_by_description(self, description: str, limit: Optional[int] = None) -> List[SICCode]:
        """Search SIC codes by description pattern."""
        pass
    
    @abstractmethod
    def get_by_section(self, section: str) -> List[SICCode]:
        """Get SIC codes by section."""
        pass
    
    @abstractmethod
    def get_hierarchical_structure(self) -> Dict[str, Any]:
        """Get SIC codes organized by hierarchical structure."""
        pass


class ICompanySICCodeRepository(BaseRepository):
    """
    Interface for Company-SIC Code junction operations.
    """
    
    @abstractmethod
    def get_by_company_id(self, company_id: int) -> List[CompanySICCode]:
        """Get all SIC codes for a company."""
        pass
    
    @abstractmethod
    def get_by_sic_code_id(self, sic_code_id: int) -> List[CompanySICCode]:
        """Get all companies for a SIC code."""
        pass
    
    @abstractmethod
    def add_sic_to_company(self, company_id: int, sic_code_id: int, is_primary: bool = False) -> Optional[int]:
        """Associate a SIC code with a company."""
        pass
    
    @abstractmethod
    def remove_sic_from_company(self, company_id: int, sic_code_id: int) -> bool:
        """Remove SIC code association from company."""
        pass
    
    @abstractmethod
    def set_primary_sic(self, company_id: int, sic_code_id: int) -> bool:
        """Set a SIC code as primary for a company."""
        pass


class ICompanyFinancialRepository(BaseRepository):
    """
    Interface for Company Financial data access operations.
    """
    
    @abstractmethod
    def get_by_company_id(self, company_id: int) -> List[CompanyFinancial]:
        """Get all financial records for a company."""
        pass
    
    @abstractmethod
    def get_latest_by_company_id(self, company_id: int) -> Optional[CompanyFinancial]:
        """Get latest financial record for a company."""
        pass
    
    @abstractmethod
    def get_by_period(self, start_date: str, end_date: str) -> List[CompanyFinancial]:
        """Get financial records within a period."""
        pass
    
    @abstractmethod
    def get_financial_summary(self, company_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get financial summary statistics."""
        pass


class IAPIAuditLogRepository(BaseRepository):
    """
    Interface for API Audit Log data access operations.
    """
    
    @abstractmethod
    def log_request(self, endpoint: str, method: str, request_params: Optional[str] = None, 
                   response_status: Optional[int] = None, response_time_ms: Optional[float] = None,
                   user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> Optional[int]:
        """Log an API request."""
        pass
    
    @abstractmethod
    def get_by_endpoint(self, endpoint: str, limit: Optional[int] = None) -> List[APIAuditLog]:
        """Get audit logs for specific endpoint."""
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: str, end_date: str) -> List[APIAuditLog]:
        """Get audit logs within date range."""
        pass
    
    @abstractmethod
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        pass


class ISICPredictionHistoryRepository(BaseRepository):
    """
    Interface for SIC Prediction History data access operations.
    """
    
    @abstractmethod
    def get_by_company_id(self, company_id: int) -> List[SICPredictionHistory]:
        """Get prediction history for a company."""
        pass
    
    @abstractmethod
    def add_prediction(self, company_id: int, input_text: str, predicted_sic_code: str,
                      confidence_score: float, model_version: str) -> Optional[int]:
        """Add a new prediction record."""
        pass
    
    @abstractmethod
    def get_model_performance(self, model_version: Optional[str] = None) -> Dict[str, Any]:
        """Get model performance statistics."""
        pass
    
    @abstractmethod
    def get_recent_predictions(self, limit: int = 100) -> List[SICPredictionHistory]:
        """Get recent predictions."""
        pass