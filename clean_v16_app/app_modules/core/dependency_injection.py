"""
Dependency injection container for modular architecture
"""
import os
from typing import Dict, Any, Optional

# Repository interfaces
from app_modules.repositories.interfaces.company_repository_interface import CompanyRepositoryInterface
from app_modules.repositories.interfaces.sic_prediction_repository_interface import SICPredictionRepositoryInterface

# Repository implementations
from app_modules.repositories.implementations.file_based.file_company_repository import FileCompanyRepository
from app_modules.repositories.implementations.file_based.file_sic_prediction_repository import FileSICPredictionRepository

# Services
from app_modules.services.company_service import CompanyService
from app_modules.services.sic_prediction_service import SICPredictionService

# Import UpdateRevenueService conditionally
try:
    from app_modules.services.update_revenue_service import UpdateRevenueService
    UPDATE_REVENUE_SERVICE_AVAILABLE = True
except ImportError:
    UPDATE_REVENUE_SERVICE_AVAILABLE = False


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
            
            if database_type == 'sqlite':
                # For SQLite, we'll use a modified file repository that handles database updates
                from app_modules.repositories.implementations.file_based.sqlite_sic_prediction_repository import SQLiteSICPredictionRepository
                from app_modules.database.connection import DatabaseConnection
                db_connection = DatabaseConnection()
                self._repositories['sic_prediction_repository'] = SQLiteSICPredictionRepository(db_connection)
            elif database_type == 'files':
                self._repositories['sic_prediction_repository'] = FileSICPredictionRepository(self.app)
            # elif database_type == 'databricks':
            #     self._repositories['sic_prediction_repository'] = DatabricksSICPredictionRepository(self.app)
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
    
    def get_update_revenue_service(self):
        """Get update revenue service with injected dependencies"""
        if UPDATE_REVENUE_SERVICE_AVAILABLE:
            if 'update_revenue_service' not in self._services:
                self._services['update_revenue_service'] = UpdateRevenueService(self)
            return self._services['update_revenue_service']
        else:
            raise ImportError("UpdateRevenueService not available")


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


def get_update_revenue_service(app=None):
    """Convenience function to get update revenue service"""
    container = get_container(app)
    return container.get_update_revenue_service()