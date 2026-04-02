"""
Infrastructure Package

This package contains infrastructure components like dependency injection,
configuration management, and cross-cutting concerns.
"""

from .di import get_service, get_company_service, get_company_repository

__all__ = [
    'get_service',
    'get_company_service', 
    'get_company_repository'
]