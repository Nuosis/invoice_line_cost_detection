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
    
    def get_db_manager(self, skip_version_check: bool = False) -> DatabaseManager:
        """Get or create database manager instance."""
        if self.db_manager is None:
            # Always check for updated environment variable
            current_db_path = os.environ.get('INVOICE_CHECKER_DB', self.database_path)
            self.db_manager = DatabaseManager(current_db_path, skip_version_check=skip_version_check)
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


class ProcessingContext:
    """
    Context object for processing workflows and interactive sessions.
    
    This class manages state and configuration for invoice processing,
    part discovery, and interactive workflows.
    """
    
    def __init__(self):
        """Initialize the processing context."""
        self.input_path = None
        self.output_path = None
        self.batch_mode = False
        self.session_id = None
        self.validation_mode = "parts_based"
        self.error_recovery_mode = False
        self.dry_run = False
        self.force = False
        self.verbose = False
        self.quiet = False
        self.config = {}
        self.session_data = {}
        self.processing_stats = {}
    
    def set_input_path(self, path: str):
        """Set the input path for processing."""
        self.input_path = path
    
    def get_input_path(self) -> str:
        """Get the input path for processing."""
        return self.input_path
    
    def set_output_path(self, path: str):
        """Set the output path for reports."""
        self.output_path = path
    
    def get_output_path(self) -> str:
        """Get the output path for reports."""
        return self.output_path
    
    
    def set_batch_mode(self, enabled: bool):
        """Enable or disable batch processing mode."""
        self.batch_mode = enabled
    
    def is_batch_mode(self) -> bool:
        """Check if batch mode is enabled."""
        return self.batch_mode
    
    def set_session_id(self, session_id: str):
        """Set the session ID for tracking."""
        self.session_id = session_id
    
    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self.session_id
    
    def set_validation_mode(self, mode: str):
        """Set the validation mode."""
        self.validation_mode = mode
    
    def get_validation_mode(self) -> str:
        """Get the validation mode."""
        return self.validation_mode
    
    def set_error_recovery_mode(self, enabled: bool):
        """Enable or disable error recovery mode."""
        self.error_recovery_mode = enabled
    
    def is_error_recovery_mode(self) -> bool:
        """Check if error recovery mode is enabled."""
        return self.error_recovery_mode
    
    def set_dry_run(self, enabled: bool):
        """Enable or disable dry run mode."""
        self.dry_run = enabled
    
    def is_dry_run(self) -> bool:
        """Check if dry run mode is enabled."""
        return self.dry_run
    
    def set_force(self, enabled: bool):
        """Enable or disable force mode."""
        self.force = enabled
    
    def is_force(self) -> bool:
        """Check if force mode is enabled."""
        return self.force
    
    def set_verbose(self, enabled: bool):
        """Enable or disable verbose mode."""
        self.verbose = enabled
    
    def is_verbose(self) -> bool:
        """Check if verbose mode is enabled."""
        return self.verbose
    
    def set_quiet(self, enabled: bool):
        """Enable or disable quiet mode."""
        self.quiet = enabled
    
    def is_quiet(self) -> bool:
        """Check if quiet mode is enabled."""
        return self.quiet
    
    def set_config(self, key: str, value: any):
        """Set a configuration value."""
        self.config[key] = value
    
    def get_config(self, key: str, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set_session_data(self, key: str, value: any):
        """Set session-specific data."""
        self.session_data[key] = value
    
    def get_session_data(self, key: str, default=None):
        """Get session-specific data."""
        return self.session_data.get(key, default)
    
    def update_processing_stats(self, stats: dict):
        """Update processing statistics."""
        self.processing_stats.update(stats)
    
    def get_processing_stats(self) -> dict:
        """Get processing statistics."""
        return self.processing_stats.copy()
    
    def reset(self):
        """Reset the context to initial state."""
        self.__init__()
    
    def to_dict(self) -> dict:
        """Convert context to dictionary for serialization."""
        return {
            'input_path': self.input_path,
            'output_path': self.output_path,
            'batch_mode': self.batch_mode,
            'session_id': self.session_id,
            'validation_mode': self.validation_mode,
            'error_recovery_mode': self.error_recovery_mode,
            'dry_run': self.dry_run,
            'force': self.force,
            'verbose': self.verbose,
            'quiet': self.quiet,
            'config': self.config,
            'session_data': self.session_data,
            'processing_stats': self.processing_stats
        }
    
    def from_dict(self, data: dict):
        """Load context from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)