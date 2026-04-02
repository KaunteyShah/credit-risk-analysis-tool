"""
Repository interface for SIC prediction operations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class SICPredictionRepositoryInterface(ABC):
    """Repository interface for SIC prediction data operations"""
    
    @abstractmethod
    def get_company_by_index(self, company_index: int) -> Optional[Dict[str, Any]]:
        """Get company data by index for SIC prediction"""
        pass
    
    @abstractmethod
    def get_company_by_name(self, company_name: str, 
                           registration_number: Optional[str] = None,
                           sic_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get company data by name for SIC prediction"""
        pass
    
    @abstractmethod
    def update_company_prediction(self, company_index: int, predicted_sic: str, 
                                confidence: float, new_accuracy: float) -> bool:
        """Update company with SIC prediction results"""
        pass
    
    @abstractmethod
    def get_companies_count(self) -> int:
        """Get total count of companies"""
        pass
    
    @abstractmethod
    def load_company_data(self) -> bool:
        """Load company data if not already loaded"""
        pass