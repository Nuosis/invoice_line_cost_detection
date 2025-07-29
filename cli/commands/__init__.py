"""
CLI command modules for the Invoice Rate Detection System.

This package contains all the command implementations organized by functional area:
- invoice_commands: Invoice processing operations
- parts_commands: Parts management operations  
- database_commands: Database management operations
- config_commands: Configuration management operations
- discovery_commands: Discovery log management operations
- utils_commands: Utility operations (help, version, status)
"""

# Import command groups for easy access
from . import (
    invoice_commands,
    parts_commands,
    database_commands,
    config_commands,
    discovery_commands,
    utils_commands
)

__all__ = [
    'invoice_commands',
    'parts_commands', 
    'database_commands',
    'config_commands',
    'discovery_commands',
    'utils_commands'
]