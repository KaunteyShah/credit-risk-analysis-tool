"""
Dependency Injection Package

This package provides dependency injection capabilities for the application,
enabling clean separation of concerns and easy testing.
"""

from .container import DIContainer, get_container, get_service, get_company_service, get_company_repository

__all__ = [
    'DIContainer',
    'get_container', 
    'get_service',
    'get_company_service',
    'get_company_repository'
]