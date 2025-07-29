"""
Centralized error handling utilities for CLI commands.

This module provides a comprehensive error handling system that:
- Handles specific error types with appropriate recovery suggestions
- Provides consistent error message formatting
- Offers actionable guidance to users for error recovery
- Implements a decorator pattern for easy application across commands
"""

import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps

from cli.exceptions import CLIError, ProcessingError, ValidationError as CLIValidationError
from cli.formatters import print_error, print_warning, print_info
from database.models import DatabaseError, PartNotFoundError, ConfigurationError, ValidationError

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling with recovery suggestions."""
    
    @staticmethod
    def handle_database_error(error: DatabaseError, context: Dict[str, Any]) -> None:
        """
        Handle database-related errors with specific recovery actions.
        
        Args:
            error: The database error that occurred
            context: Additional context about the operation that failed
        """
        error_msg = str(error).lower()
        
        if "database is locked" in error_msg:
            print_error("Database is currently locked by another process")
            print_info("Recovery suggestions:")
            print_info("  1. Close any other instances of the application")
            print_info("  2. Wait a few seconds and try again")
            print_info("  3. Restart the application if the problem persists")
            print_info("  4. Check if another user is accessing the database")
            
        elif "no such table" in error_msg:
            print_error("Database schema is incomplete or corrupted")
            print_info("Recovery suggestions:")
            print_info("  1. Run: invoice-checker database migrate")
            print_info("  2. If that fails, restore from a backup:")
            print_info("     invoice-checker database restore <backup-file>")
            print_info("  3. As a last resort, delete the database file to recreate it")
            
        elif "disk" in error_msg and ("full" in error_msg or "space" in error_msg):
            print_error("Insufficient disk space for database operation")
            print_info("Recovery suggestions:")
            print_info("  1. Free up disk space on your system")
            print_info("  2. Move the database to a location with more space")
            print_info("  3. Run database maintenance to reclaim space:")
            print_info("     invoice-checker database maintenance")
            
        elif "permission" in error_msg or "access" in error_msg:
            print_error("Permission denied accessing database")
            print_info("Recovery suggestions:")
            print_info("  1. Check file permissions on the database directory")
            print_info("  2. Run the application with appropriate permissions")
            print_info("  3. Ensure the database file is not read-only")
            
        elif "corrupt" in error_msg or "malformed" in error_msg:
            print_error("Database file appears to be corrupted")
            print_info("Recovery suggestions:")
            print_info("  1. Restore from a recent backup:")
            print_info("     invoice-checker database restore <backup-file>")
            print_info("  2. Check database integrity:")
            print_info("     invoice-checker database maintenance --verify-integrity")
            print_info("  3. Contact support if corruption persists")
            
        else:
            print_error(f"Database error: {error}")
            print_info("Recovery suggestions:")
            print_info("  1. Check database status: invoice-checker status")
            print_info("  2. Try running database maintenance:")
            print_info("     invoice-checker database maintenance")
            print_info("  3. If problems persist, restore from backup")
    
    @staticmethod
    def handle_processing_error(error: ProcessingError, context: Dict[str, Any]) -> None:
        """
        Handle processing-related errors with recovery actions.
        
        Args:
            error: The processing error that occurred
            context: Additional context including file paths, operation type
        """
        error_msg = str(error).lower()
        file_path = context.get('file_path', 'unknown')
        operation = context.get('operation', 'processing')
        
        if "pdf" in error_msg:
            print_error(f"PDF processing failed for: {file_path}")
            print_info("Recovery suggestions:")
            print_info("  1. Verify the PDF file is not corrupted:")
            print_info("     - Try opening the file in a PDF viewer")
            print_info("     - Check file size (should not be 0 bytes)")
            print_info("  2. Try processing other files to isolate the issue")
            print_info("  3. Check if the PDF requires a password")
            print_info("  4. Ensure the PDF contains text (not just images)")
            print_info("  5. Try converting the PDF to a newer format")
            
        elif "validation" in error_msg:
            print_error(f"Validation failed for: {file_path}")
            print_info("Recovery suggestions:")
            print_info("  1. Check if parts database is populated:")
            print_info("     invoice-checker parts list")
            print_info("  2. Try threshold-based validation mode:")
            print_info("     invoice-checker process --validation-mode threshold_based")
            print_info("  3. Run with interactive flag for manual review:")
            print_info("     invoice-checker process --interactive")
            print_info("  4. Collect unknown parts first:")
            print_info("     invoice-checker collect-unknowns")
            
        elif "permission" in error_msg or "access" in error_msg:
            print_error(f"Permission denied accessing: {file_path}")
            print_info("Recovery suggestions:")
            print_info("  1. Check file and directory permissions")
            print_info("  2. Ensure you have read access to input files")
            print_info("  3. Ensure you have write access to output directory")
            print_info("  4. Try running with administrator privileges if needed")
            
        elif "not found" in error_msg or "no such file" in error_msg:
            print_error(f"File or directory not found: {file_path}")
            print_info("Recovery suggestions:")
            print_info("  1. Verify the file path is correct")
            print_info("  2. Check if the file has been moved or deleted")
            print_info("  3. Use absolute paths instead of relative paths")
            print_info("  4. Ensure the file extension is correct (.pdf)")
            
        elif "memory" in error_msg or "out of memory" in error_msg:
            print_error("Insufficient memory for processing")
            print_info("Recovery suggestions:")
            print_info("  1. Process files in smaller batches")
            print_info("  2. Close other applications to free memory")
            print_info("  3. Process files individually instead of in batch")
            print_info("  4. Consider upgrading system memory")
            
        else:
            print_error(f"Processing error during {operation}: {error}")
            print_info("Recovery suggestions:")
            print_info("  1. Try processing a single file to isolate the issue")
            print_info("  2. Check system resources (disk space, memory)")
            print_info("  3. Verify input file format and integrity")
            print_info("  4. Review the error details above for specific guidance")
    
    @staticmethod
    def handle_validation_error(error: ValidationError, context: Dict[str, Any]) -> None:
        """
        Handle input validation errors.
        
        Args:
            error: The validation error that occurred
            context: Additional context including field name, value
        """
        field_name = context.get('field_name', 'input')
        value = context.get('value', 'unknown')
        
        print_error(f"Input validation failed: {error}")
        
        if "part_number" in str(error).lower():
            print_info("Part number requirements:")
            print_info("  - Must contain only letters, numbers, underscores, hyphens, and periods")
            print_info("  - Cannot be empty or contain only whitespace")
            print_info("  - Example: GP0171NAVY, ITEM-123, PART_001")
            
        elif "price" in str(error).lower():
            print_info("Price requirements:")
            print_info("  - Must be a positive number")
            print_info("  - Maximum 4 decimal places")
            print_info("  - Example: 15.50, 0.25, 100.0000")
            
        elif "email" in str(error).lower():
            print_info("Email format requirements:")
            print_info("  - Must be a valid email address")
            print_info("  - Example: user@example.com")
            
        else:
            print_info(f"Please check the {field_name} value: {value}")
            print_info("Refer to the command help for format requirements:")
            print_info("  invoice-checker <command> --help")
    
    @staticmethod
    def handle_part_not_found_error(error: PartNotFoundError, context: Dict[str, Any]) -> None:
        """
        Handle part not found errors.
        
        Args:
            error: The part not found error
            context: Additional context including part number
        """
        part_number = context.get('part_number', 'unknown')
        
        print_error(f"Part not found: {error}")
        print_info("Recovery suggestions:")
        print_info("  1. Check if the part number is spelled correctly")
        print_info("  2. List available parts: invoice-checker parts list")
        print_info("  3. Search for similar parts:")
        print_info(f"     invoice-checker parts list | grep -i {part_number[:4]}")
        print_info("  4. Add the part if it should exist:")
        print_info(f"     invoice-checker parts add {part_number} <price>")
        print_info("  5. Import parts from a CSV file if you have bulk data")
    
    @staticmethod
    def handle_configuration_error(error: ConfigurationError, context: Dict[str, Any]) -> None:
        """
        Handle configuration-related errors.
        
        Args:
            error: The configuration error
            context: Additional context including config key
        """
        config_key = context.get('config_key', 'unknown')
        
        print_error(f"Configuration error: {error}")
        print_info("Recovery suggestions:")
        print_info("  1. Check current configuration:")
        print_info("     invoice-checker config list")
        print_info("  2. Reset configuration to defaults:")
        print_info("     invoice-checker config reset")
        print_info("  3. Set specific configuration value:")
        print_info(f"     invoice-checker config set {config_key} <value>")
        print_info("  4. Restore configuration from backup if available")
    
    @staticmethod
    def handle_cli_validation_error(error: CLIValidationError, context: Dict[str, Any]) -> None:
        """
        Handle CLI-specific validation errors.
        
        Args:
            error: The CLI validation error
            context: Additional context about the validation failure
        """
        print_error(f"Command validation failed: {error}")
        command = context.get('command', 'unknown')
        print_info("Recovery suggestions:")
        print_info(f"  1. Check command syntax: invoice-checker {command} --help")
        print_info("  2. Verify all required arguments are provided")
        print_info("  3. Check argument formats and types")
        print_info("  4. Use interactive mode for guided input:")
        print_info("     invoice-checker interactive")
    
    @staticmethod
    def with_error_handling(error_context: Optional[Dict[str, Any]] = None):
        """
        Decorator for consistent error handling across commands.
        
        Args:
            error_context: Additional context to include in error handling
            
        Returns:
            Decorator function that wraps command functions with error handling
        """
        if error_context is None:
            error_context = {}
            
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                    
                except DatabaseError as e:
                    logger.exception(f"Database error in {func.__name__}")
                    ErrorHandler.handle_database_error(e, error_context)
                    raise CLIError(f"Database operation failed: {e}")
                    
                except ProcessingError as e:
                    logger.exception(f"Processing error in {func.__name__}")
                    ErrorHandler.handle_processing_error(e, error_context)
                    raise CLIError(f"Processing failed: {e}")
                    
                except ValidationError as e:
                    logger.debug(f"Validation error in {func.__name__}: {e}")
                    ErrorHandler.handle_validation_error(e, error_context)
                    raise CLIError(f"Validation failed: {e}")
                    
                except CLIValidationError as e:
                    logger.debug(f"CLI validation error in {func.__name__}: {e}")
                    ErrorHandler.handle_cli_validation_error(e, error_context)
                    raise CLIError(f"Command validation failed: {e}")
                    
                except PartNotFoundError as e:
                    logger.debug(f"Part not found in {func.__name__}: {e}")
                    ErrorHandler.handle_part_not_found_error(e, error_context)
                    raise CLIError(f"Part not found: {e}")
                    
                except ConfigurationError as e:
                    logger.warning(f"Configuration error in {func.__name__}: {e}")
                    ErrorHandler.handle_configuration_error(e, error_context)
                    raise CLIError(f"Configuration error: {e}")
                    
                except FileNotFoundError as e:
                    logger.error(f"File not found in {func.__name__}: {e}")
                    print_error(f"File not found: {e}")
                    print_info("Recovery suggestions:")
                    print_info("  1. Verify the file path is correct")
                    print_info("  2. Check if the file exists and is accessible")
                    print_info("  3. Use absolute paths instead of relative paths")
                    raise CLIError(f"File not found: {e}")
                    
                except PermissionError as e:
                    logger.error(f"Permission error in {func.__name__}: {e}")
                    print_error(f"Permission denied: {e}")
                    print_info("Recovery suggestions:")
                    print_info("  1. Check file and directory permissions")
                    print_info("  2. Run with appropriate user privileges")
                    print_info("  3. Ensure files are not locked by other processes")
                    raise CLIError(f"Permission denied: {e}")
                    
                except KeyboardInterrupt:
                    logger.info(f"User interrupted {func.__name__}")
                    print_info("\nOperation cancelled by user.")
                    raise CLIError("Operation cancelled by user", exit_code=130)
                    
                except Exception as e:
                    logger.exception(f"Unexpected error in {func.__name__}")
                    print_error(f"Unexpected error: {e}")
                    print_info("This may be a bug. Please report it with the following details:")
                    print_info(f"  - Command: {func.__name__}")
                    print_info(f"  - Error: {type(e).__name__}: {e}")
                    print_info(f"  - Context: {error_context}")
                    print_info("Recovery suggestions:")
                    print_info("  1. Try the operation again")
                    print_info("  2. Check system resources (disk space, memory)")
                    print_info("  3. Restart the application")
                    print_info("  4. Contact support if the problem persists")
                    raise CLIError(f"Unexpected error: {e}")
                    
            return wrapper
        return decorator


# Convenience functions for common error handling patterns
def handle_file_operation_error(error: Exception, file_path: str, operation: str) -> None:
    """
    Handle common file operation errors with appropriate suggestions.
    
    Args:
        error: The exception that occurred
        file_path: Path to the file being operated on
        operation: Description of the operation being performed
    """
    context = {'file_path': file_path, 'operation': operation}
    
    if isinstance(error, ProcessingError):
        ErrorHandler.handle_processing_error(error, context)
    elif isinstance(error, FileNotFoundError):
        print_error(f"File not found during {operation}: {file_path}")
        print_info("Recovery suggestions:")
        print_info("  1. Verify the file path is correct")
        print_info("  2. Check if the file has been moved or deleted")
        print_info("  3. Ensure you have read permissions for the file")
    elif isinstance(error, PermissionError):
        print_error(f"Permission denied during {operation}: {file_path}")
        print_info("Recovery suggestions:")
        print_info("  1. Check file permissions")
        print_info("  2. Ensure the file is not locked by another process")
        print_info("  3. Run with appropriate user privileges")
    else:
        print_error(f"Error during {operation} on {file_path}: {error}")


def handle_database_operation_error(error: Exception, operation: str, **context) -> None:
    """
    Handle common database operation errors.
    
    Args:
        error: The exception that occurred
        operation: Description of the database operation
        **context: Additional context for error handling
    """
    context['operation'] = operation
    
    if isinstance(error, DatabaseError):
        ErrorHandler.handle_database_error(error, context)
    elif isinstance(error, PartNotFoundError):
        ErrorHandler.handle_part_not_found_error(error, context)
    elif isinstance(error, ConfigurationError):
        ErrorHandler.handle_configuration_error(error, context)
    else:
        print_error(f"Error during {operation}: {error}")
        print_info("Try checking database status: invoice-checker status")


# Export the main decorator for easy use
error_handler = ErrorHandler.with_error_handling