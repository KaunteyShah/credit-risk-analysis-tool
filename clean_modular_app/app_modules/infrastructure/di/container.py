"""
Dependency Injection Container

This module provides a simple dependency injection container that wires
components together based on configuration. It enables clean separation
of concerns and easy testing with mock dependencies.
"""

import os
from typing import Dict, Any, TypeVar, Callable, Optional
from app_modules.utils.logger import logger

T = TypeVar('T')

class DIContainer:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, Any] = {}
        
        logger.info("Dependency injection container initialized")
    
    def register_singleton(self, name: str, factory: Callable[[], T]) -> None:
        """Register a singleton service factory"""
        self._factories[name] = factory
        logger.info(f"Registered singleton factory: {name}")
    
    def register_transient(self, name: str, factory: Callable[[], T]) -> None:
        """Register a transient service factory (new instance each time)"""
        self._services[name] = factory
        logger.info(f"Registered transient factory: {name}")
    
    def get(self, name: str) -> Any:
        """Get service instance"""
        # Check for singleton first
        if name in self._singletons:
            return self._singletons[name]
        
        # Create singleton if factory exists
        if name in self._factories:
            instance = self._factories[name]()
            self._singletons[name] = instance
            logger.info(f"Created singleton instance: {name}")
            return instance
        
        # Create transient instance
        if name in self._services:
            instance = self._services[name]()
            logger.info(f"Created transient instance: {name}")
            return instance
        
        raise KeyError(f"Service '{name}' not registered")
    
    def has(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self._factories or name in self._services

# Global container instance
_container: Optional[DIContainer] = None

def get_container() -> DIContainer:
    """Get global DI container instance"""
    global _container
    if _container is None:
        _container = DIContainer()
        _configure_container(_container)
    return _container

def _configure_container(container: DIContainer) -> None:
    """Configure the DI container with default services"""
    from app_modules.repositories.implementations.file_based.file_company_repository import FileCompanyRepository
    from app_modules.services.company_service import CompanyService
    
    # Configuration-based repository selection
    database_type = os.getenv('DATABASE_TYPE', 'file')
    
    if database_type == 'sqlite':
        # TODO: Register SQLite repository when implemented
        logger.info("SQLite database type configured (not implemented yet)")
        # For now, fall back to file repository
        container.register_singleton('company_repository', lambda: FileCompanyRepository())
    else:
        # Default to file-based repository
        container.register_singleton('company_repository', lambda: FileCompanyRepository())
    
    # Register services
    container.register_singleton('company_service', lambda: CompanyService(
        container.get('company_repository')
    ))
    
    logger.info(f"DI container configured with database_type: {database_type}")

# Convenience functions
def get_service(service_name: str) -> Any:
    """Get service instance from container"""
    return get_container().get(service_name)

def get_company_service():
    """Get CompanyService instance"""
    return get_service('company_service')

def get_company_repository():
    """Get CompanyRepository instance"""  
    return get_service('company_repository')