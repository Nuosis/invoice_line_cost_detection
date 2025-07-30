"""
Database package for the Invoice Rate Detection System.

This package provides database management functionality including:
- DatabaseManager for CRUD operations
- Model classes for data structures
- Migration utilities
- Database utilities
"""

from .database import DatabaseManager
from .models import Part, Configuration, PartDiscoveryLog, DEFAULT_CONFIG
from .models import ValidationError, DatabaseError, PartNotFoundError, ConfigurationError
from .db_migration import DatabaseMigration

__all__ = [
    'DatabaseManager',
    'Part',
    'Configuration',
    'PartDiscoveryLog',
    'DEFAULT_CONFIG',
    'ValidationError',
    'DatabaseError',
    'PartNotFoundError',
    'ConfigurationError',
    'DatabaseMigration'
]