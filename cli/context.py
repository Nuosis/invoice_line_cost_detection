"""
CLI Context module for the Invoice Rate Detection System.

This module provides the shared context and decorators used across CLI commands,
preventing circular imports between cli.main and command modules.
"""

import os
import click
from database.database import DatabaseManager


class CLIContext:
    """Context object to share state between CLI commands."""
    
    def __init__(self):
        self.verbose = False
        self.quiet = False
        # Check for environment variable first, then use default
        self.database_path = os.environ.get('INVOICE_CHECKER_DB', "invoice_detection.db")
        self.config_file = None
        self.db_manager = None
    
    def get_db_manager(self) -> DatabaseManager:
        """Get or create database manager instance."""
        if self.db_manager is None:
            # Always check for updated environment variable
            current_db_path = os.environ.get('INVOICE_CHECKER_DB', self.database_path)
            self.db_manager = DatabaseManager(current_db_path)
        return self.db_manager


# Pass context between commands
pass_context = click.make_pass_decorator(CLIContext, ensure=True)


def get_context() -> CLIContext:
    """
    Get the current CLI context.
    
    Returns:
        Current CLIContext instance
    """
    ctx = click.get_current_context(silent=True)
    if ctx and hasattr(ctx, 'obj') and isinstance(ctx.obj, CLIContext):
        return ctx.obj
    # Return a new context if none exists
    return CLIContext()