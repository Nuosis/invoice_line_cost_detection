"""
Custom exception classes for the CLI interface.

This module defines CLI-specific exceptions that provide clear error messages
and appropriate exit codes for different error conditions.
"""


class CLIError(Exception):
    """Base exception for CLI-related errors."""
    
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class ValidationError(CLIError):
    """Raised when user input validation fails."""
    
    def __init__(self, message: str):
        super().__init__(f"Validation Error: {message}", exit_code=2)


class FileNotFoundError(CLIError):
    """Raised when a required file is not found."""
    
    def __init__(self, file_path: str):
        super().__init__(f"File not found: {file_path}", exit_code=3)


class DirectoryNotFoundError(CLIError):
    """Raised when a required directory is not found."""
    
    def __init__(self, directory_path: str):
        super().__init__(f"Directory not found: {directory_path}", exit_code=3)


class PermissionError(CLIError):
    """Raised when there are insufficient permissions."""
    
    def __init__(self, operation: str, path: str = None):
        message = f"Permission denied for operation: {operation}"
        if path:
            message += f" on path: {path}"
        super().__init__(message, exit_code=4)


class ConfigurationError(CLIError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str):
        super().__init__(f"Configuration Error: {message}", exit_code=5)


class ProcessingError(CLIError):
    """Raised when invoice processing fails."""
    
    def __init__(self, message: str):
        super().__init__(f"Processing Error: {message}", exit_code=6)


class DatabaseConnectionError(CLIError):
    """Raised when database connection fails."""
    
    def __init__(self, message: str = "Failed to connect to database"):
        super().__init__(f"Database Error: {message}", exit_code=7)


class UserCancelledError(CLIError):
    """Raised when user cancels an operation."""
    
    def __init__(self, message: str = "Operation cancelled by user"):
        super().__init__(message, exit_code=130)  # Standard SIGINT exit code