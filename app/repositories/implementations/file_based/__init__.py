"""
File-Based Repository Implementations

This package contains repository implementations that use file-based storage (CSV, Excel).
These implementations wrap existing file handling logic into the repository interface pattern.
"""

from .file_company_repository import FileCompanyRepository

__all__ = [
    'FileCompanyRepository'
]