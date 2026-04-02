"""
Services Package - Business Logic Layer

This package contains service classes that implement business logic
separate from data access concerns. Services use repository interfaces
for data access and provide clean business operations.
"""

# Import services as they become available
try:
    from .company_service import CompanyService
    COMPANY_SERVICE_AVAILABLE = True
except ImportError:
    COMPANY_SERVICE_AVAILABLE = False

try:
    from .update_revenue_service import UpdateRevenueService
    UPDATE_REVENUE_SERVICE_AVAILABLE = True
except ImportError:
    UPDATE_REVENUE_SERVICE_AVAILABLE = False

__all__ = []

# Conditionally export services
if COMPANY_SERVICE_AVAILABLE:
    __all__.append('CompanyService')

if UPDATE_REVENUE_SERVICE_AVAILABLE:
    __all__.append('UpdateRevenueService')