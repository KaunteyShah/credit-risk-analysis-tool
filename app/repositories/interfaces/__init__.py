"""
Repository Interfaces Package

This package defines abstract contracts for data access operations.
These interfaces provide clean separation between business logic and data storage,
enabling easy testing and future storage backend changes.
"""

from .base_repository import BaseRepositoryInterface
from .company_repository_interface import CompanyRepositoryInterface
from .sic_repository_interface import SicRepositoryInterface
from .revenue_repository_interface import RevenueRepositoryInterface
from .workflow_repository_interface import WorkflowRepositoryInterface

__all__ = [
    'BaseRepositoryInterface',
    'CompanyRepositoryInterface', 
    'SicRepositoryInterface',
    'RevenueRepositoryInterface',
    'WorkflowRepositoryInterface'
]