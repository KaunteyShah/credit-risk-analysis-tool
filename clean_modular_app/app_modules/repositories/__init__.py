"""
Repository Package - Data Access Layer

This package provides data access abstraction through repository interfaces
and implementations. It enables clean separation between business logic 
and data storage, supporting multiple storage backends.
"""

# Import core interfaces
from .interfaces.company_repository_interface import CompanyRepositoryInterface
from .interfaces.sic_repository_interface import SicRepositoryInterface
from .interfaces.revenue_repository_interface import RevenueRepositoryInterface
from .interfaces.workflow_repository_interface import WorkflowRepositoryInterface

# Import implementations when they're available
try:
    from .implementations.file_based.file_company_repository import FileCompanyRepository
    FILE_IMPLEMENTATIONS_AVAILABLE = True
except ImportError:
    FILE_IMPLEMENTATIONS_AVAILABLE = False

__all__ = [
    # Interfaces
    'CompanyRepositoryInterface',
    'SicRepositoryInterface', 
    'RevenueRepositoryInterface',
    'WorkflowRepositoryInterface',
    # Implementation availability flags
    'FILE_IMPLEMENTATIONS_AVAILABLE'
]

# Conditionally add implementations if available
if FILE_IMPLEMENTATIONS_AVAILABLE:
    __all__.extend(['FileCompanyRepository'])