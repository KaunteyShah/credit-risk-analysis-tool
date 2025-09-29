"""
File-based implementation of SIC prediction repository
"""
import pandas as pd
from typing import Dict, Any, Optional
from app.repositories.interfaces.sic_prediction_repository_interface import SICPredictionRepositoryInterface


class FileSICPredictionRepository(SICPredictionRepositoryInterface):
    """File-based repository for SIC prediction operations"""
    
    def __init__(self, app):
        """Initialize with Flask app reference for data access"""
        self.app = app
        # Import and initialize the company repository for data access
        from app.repositories.implementations.file_based.file_company_repository import FileCompanyRepository
        self.company_repository = FileCompanyRepository()
    
    def get_company_by_index(self, company_index: int) -> Optional[Dict[str, Any]]:
        """Get company data by index for SIC prediction"""
        return self.company_repository.get_company_by_index(company_index)
    
    def get_company_by_name(self, company_name: str, 
                           registration_number: Optional[str] = None,
                           sic_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get company data by name for SIC prediction"""
        return self.company_repository.get_company_by_name(company_name, registration_number, sic_code)
    
    def update_company_prediction(self, company_index: int, predicted_sic: str, 
                                confidence: float, new_accuracy: float) -> bool:
        """Update company with SIC prediction results"""
        try:
            if self.app.company_data is None:
                return False
                
            # Update the company data with the prediction
            if isinstance(self.app.company_data, pd.DataFrame):
                self.app.company_data.loc[company_index, 'Predicted_SIC'] = predicted_sic
                self.app.company_data.loc[company_index, 'SIC_Confidence'] = confidence
                self.app.company_data.loc[company_index, 'New_Accuracy'] = new_accuracy
            else:
                self.app.company_data[company_index]['Predicted_SIC'] = predicted_sic
                self.app.company_data[company_index]['SIC_Confidence'] = confidence
                self.app.company_data[company_index]['New_Accuracy'] = new_accuracy
            
            return True
            
        except Exception:
            return False
    
    def get_companies_count(self) -> int:
        """Get total count of companies"""
        try:
            if not self.load_company_data():
                return 0
                
            if isinstance(self.app.company_data, pd.DataFrame):
                return len(self.app.company_data)
            elif self.app.company_data:
                return len(self.app.company_data)
            else:
                return 0
                
        except Exception:
            return 0
    
    def load_company_data(self) -> bool:
        """Load company data if not already loaded"""
        try:
            if self.app.company_data is None:
                # Call the app's load_company_data function
                # This preserves the existing data loading logic
                from app.flask_main import load_company_data
                load_company_data()
            
            return self.app.company_data is not None
            
        except Exception:
            return False