"""
Dependency injection container for modular architecture
"""
import os
from typing import Dict, Any, Optional

# Repository interfaces
from app.repositories.interfaces.company_repository_interface import CompanyRepositoryInterface
from app.repositories.interfaces.sic_prediction_repository_interface import SICPredictionRepositoryInterface

# Repository implementations
from app.repositories.implementations.file_based.file_company_repository import FileCompanyRepository
from app.repositories.implementations.file_based.file_sic_prediction_repository import FileSICPredictionRepository

# Services
from app.services.company_service import CompanyService
from app.services.sic_prediction_service import SICPredictionService


class DIContainer:
    """Dependency injection container"""
    
    def __init__(self, app=None):
        """Initialize with optional Flask app reference"""
        self.app = app
        self._services = {}
        self._repositories = {}
    
    def get_company_repository(self) -> CompanyRepositoryInterface:
        """Get company repository based on configuration"""
        if 'company_repository' not in self._repositories:
            database_type = os.getenv('DATABASE_TYPE', 'files').lower()
            
            if database_type == 'files':
                self._repositories['company_repository'] = FileCompanyRepository()
            # elif database_type == 'databricks':
            #     self._repositories['company_repository'] = DatabricksCompanyRepository()
            # elif database_type == 'sqlite':
            #     self._repositories['company_repository'] = SQLiteCompanyRepository()
            else:
                # Default to files
                self._repositories['company_repository'] = FileCompanyRepository()
        
        return self._repositories['company_repository']
    
    def get_sic_prediction_repository(self) -> SICPredictionRepositoryInterface:
        """Get SIC prediction repository based on configuration"""
        if 'sic_prediction_repository' not in self._repositories:
            database_type = os.getenv('DATABASE_TYPE', 'files').lower()
            
            if database_type == 'files':
                self._repositories['sic_prediction_repository'] = FileSICPredictionRepository(self.app)
            # elif database_type == 'databricks':
            #     self._repositories['sic_prediction_repository'] = DatabricksSICPredictionRepository(self.app)
            # elif database_type == 'sqlite':
            #     self._repositories['sic_prediction_repository'] = SQLiteSICPredictionRepository(self.app)
            else:
                # Default to files
                self._repositories['sic_prediction_repository'] = FileSICPredictionRepository(self.app)
        
        return self._repositories['sic_prediction_repository']
    
    def get_company_service(self) -> CompanyService:
        """Get company service with injected repository"""
        if 'company_service' not in self._services:
            repository = self.get_company_repository()
            self._services['company_service'] = CompanyService(repository)
        
        return self._services['company_service']
    
    def get_sic_prediction_service(self) -> SICPredictionService:
        """Get SIC prediction service with injected repository"""
        if 'sic_prediction_service' not in self._services:
            repository = self.get_sic_prediction_repository()
            self._services['sic_prediction_service'] = SICPredictionService(repository)
        
        return self._services['sic_prediction_service']


# Global container instance
_container: Optional[DIContainer] = None


def get_container(app=None) -> DIContainer:
    """Get the global DI container"""
    global _container
    if _container is None or (app and _container.app != app):
        _container = DIContainer(app)
    return _container


def get_company_service(app=None) -> CompanyService:
    """Convenience function to get company service"""
    container = get_container(app)
    return container.get_company_service()


def get_sic_prediction_service(app=None) -> SICPredictionService:
    """Convenience function to get SIC prediction service"""
    container = get_container(app)
    return container.get_sic_prediction_service()