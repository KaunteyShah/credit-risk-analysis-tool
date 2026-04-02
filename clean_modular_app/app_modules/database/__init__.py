"""
Database module for SQLite integration following modular architecture.
Provides database connection management, models, and repositories.
"""

from .connection import DatabaseConnection
from .models import (
    Company,
    SICCode,
    CompanySICCode,
    CompanyFinancial,
    APIAuditLog,
    SICPredictionHistory
)

__all__ = [
    'DatabaseConnection',
    'Company',
    'SICCode', 
    'CompanySICCode',
    'CompanyFinancial',
    'APIAuditLog',
    'SICPredictionHistory'
]