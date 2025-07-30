"""
Comprehensive test suite for the centralized error handling system.

This module tests the error handling functionality including:
- Specific error handlers for different error types
- Recovery suggestions for common scenarios
- Error handling decorator functionality
- Integration with CLI commands
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys

from cli.error_handlers import (
    ErrorHandler, error_handler, handle_file_operation_error,
    handle_database_operation_error
)
from cli.exceptions import CLIError, ProcessingError, ValidationError as CLIValidationError
from database.models import DatabaseError, PartNotFoundError, ConfigurationError, ValidationError
from cli.formatters import print_error, print_info


class TestErrorHandlerSpecificMethods:
    """Test specific error handling methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
        self.mock_context = {'operation': 'test_operation', 'file_path': '/test/path'}
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_database_error_locked_database(self, mock_print_info, mock_print_error):
        """Test handling of locked database error."""
        error = DatabaseError("database is locked")
        
        self.error_handler.handle_database_error(error, self.mock_context)
        
        mock_print_error.assert_called_once_with("Database is currently locked by another process")
        assert mock_print_info.call_count >= 4  # Multiple recovery suggestions
        
        # Check that recovery suggestions are provided
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("Close any other instances" in call for call in info_calls)
        assert any("Wait a few seconds" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_database_error_missing_table(self, mock_print_info, mock_print_error):
        """Test handling of missing table error."""
        error = DatabaseError("no such table: parts")
        
        self.error_handler.handle_database_error(error, self.mock_context)
        
        mock_print_error.assert_called_once_with("Database schema is incomplete or corrupted")
        
        # Check for migration suggestion
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("invoice-checker database migrate" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_database_error_disk_space(self, mock_print_info, mock_print_error):
        """Test handling of disk space error."""
        error = DatabaseError("disk full")
        
        self.error_handler.handle_database_error(error, self.mock_context)
        
        mock_print_error.assert_called_once_with("Insufficient disk space for database operation")
        
        # Check for disk space recovery suggestions
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("Free up disk space" in call for call in info_calls)
        assert any("database maintenance" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_database_error_permission(self, mock_print_info, mock_print_error):
        """Test handling of permission error."""
        error = DatabaseError("permission denied")
        
        self.error_handler.handle_database_error(error, self.mock_context)
        
        mock_print_error.assert_called_once_with("Permission denied accessing database")
        
        # Check for permission recovery suggestions
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("file permissions" in call for call in info_calls)
        assert any("appropriate permissions" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_database_error_corruption(self, mock_print_info, mock_print_error):
        """Test handling of database corruption error."""
        error = DatabaseError("database is corrupt")
        
        self.error_handler.handle_database_error(error, self.mock_context)
        
        mock_print_error.assert_called_once_with("Database file appears to be corrupted")
        
        # Check for corruption recovery suggestions
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("Restore from a recent backup" in call for call in info_calls)
        assert any("verify-integrity" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_processing_error_pdf(self, mock_print_info, mock_print_error):
        """Test handling of PDF processing error."""
        error = ProcessingError("PDF processing failed")
        context = {'file_path': '/test/invoice.pdf', 'operation': 'pdf_processing'}
        
        self.error_handler.handle_processing_error(error, context)
        
        mock_print_error.assert_called_once_with("PDF processing failed for: /test/invoice.pdf")
        
        # Check for PDF-specific recovery suggestions
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("PDF file is not corrupted" in call for call in info_calls)
        assert any("requires a password" in call for call in info_calls)
        assert any("contains text" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_processing_error_validation(self, mock_print_info, mock_print_error):
        """Test handling of validation processing error."""
        error = ProcessingError("validation failed")
        context = {'file_path': '/test/invoice.pdf', 'operation': 'validation'}
        
        self.error_handler.handle_processing_error(error, context)
        
        mock_print_error.assert_called_once_with("Validation failed for: /test/invoice.pdf")
        
        # Check for validation-specific recovery suggestions
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("parts database is populated" in call for call in info_calls)
        assert any("threshold-based validation" in call for call in info_calls)
        assert any("--interactive" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_processing_error_memory(self, mock_print_info, mock_print_error):
        """Test handling of memory error."""
        error = ProcessingError("out of memory")
        
        self.error_handler.handle_processing_error(error, self.mock_context)
        
        mock_print_error.assert_called_once_with("Insufficient memory for processing")
        
        # Check for memory-specific recovery suggestions
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("smaller batches" in call for call in info_calls)
        assert any("close other applications" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_validation_error_part_number(self, mock_print_info, mock_print_error):
        """Test handling of part number validation error."""
        error = ValidationError("Part number can only contain letters")
        context = {'field_name': 'part_number', 'value': 'INVALID@PART'}
        
        self.error_handler.handle_validation_error(error, context)
        
        mock_print_error.assert_called_once_with(f"Input validation failed: {error}")
        
        # Check for part number format guidance
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("Part number requirements" in call for call in info_calls)
        assert any("letters, numbers, underscores" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_validation_error_price(self, mock_print_info, mock_print_error):
        """Test handling of price validation error."""
        error = ValidationError("Price must be positive")
        context = {'field_name': 'price', 'value': '-5.00'}
        
        self.error_handler.handle_validation_error(error, context)
        
        mock_print_error.assert_called_once_with(f"Input validation failed: {error}")
        
        # Check for price format guidance
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("Price requirements" in call for call in info_calls)
        assert any("positive number" in call for call in info_calls)
        assert any("4 decimal places" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_part_not_found_error(self, mock_print_info, mock_print_error):
        """Test handling of part not found error."""
        error = PartNotFoundError("Part GP0171NAVY not found")
        context = {'part_number': 'GP0171NAVY'}
        
        self.error_handler.handle_part_not_found_error(error, context)
        
        mock_print_error.assert_called_once_with(f"Part not found: {error}")
        
        # Check for part not found recovery suggestions
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("spelled correctly" in call for call in info_calls)
        assert any("parts list" in call for call in info_calls)
        assert any("parts add GP0171NAVY" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_configuration_error(self, mock_print_info, mock_print_error):
        """Test handling of configuration error."""
        error = ConfigurationError("Invalid configuration value")
        context = {'config_key': 'validation_mode'}
        
        self.error_handler.handle_configuration_error(error, context)
        
        mock_print_error.assert_called_once_with(f"Configuration error: {error}")
        
        # Check for configuration recovery suggestions
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("config list" in call for call in info_calls)
        assert any("config reset" in call for call in info_calls)
        assert any("config set validation_mode" in call for call in info_calls)


class TestErrorHandlerDecorator:
    """Test the error handling decorator functionality."""
    
    def test_decorator_catches_database_error(self):
        """Test that decorator catches and handles database errors."""
        @error_handler({'operation': 'test_db_op'})
        def test_function():
            raise DatabaseError("Test database error")
        
        with pytest.raises(CLIError) as exc_info:
            test_function()
        
        assert "Database operation failed" in str(exc_info.value)
    
    def test_decorator_catches_processing_error(self):
        """Test that decorator catches and handles processing errors."""
        @error_handler({'operation': 'test_processing'})
        def test_function():
            raise ProcessingError("Test processing error")
        
        with pytest.raises(CLIError) as exc_info:
            test_function()
        
        assert "Processing failed" in str(exc_info.value)
    
    def test_decorator_catches_validation_error(self):
        """Test that decorator catches and handles validation errors."""
        @error_handler({'operation': 'test_validation'})
        def test_function():
            raise ValidationError("Test validation error")
        
        with pytest.raises(CLIError) as exc_info:
            test_function()
        
        assert "Validation failed" in str(exc_info.value)
    
    def test_decorator_catches_part_not_found_error(self):
        """Test that decorator catches and handles part not found errors."""
        @error_handler({'part_number': 'TEST123'})
        def test_function():
            raise PartNotFoundError("Part TEST123 not found")
        
        with pytest.raises(CLIError) as exc_info:
            test_function()
        
        assert "Part not found" in str(exc_info.value)
    
    def test_decorator_catches_configuration_error(self):
        """Test that decorator catches and handles configuration errors."""
        @error_handler({'config_key': 'test_key'})
        def test_function():
            raise ConfigurationError("Test config error")
        
        with pytest.raises(CLIError) as exc_info:
            test_function()
        
        assert "Configuration error" in str(exc_info.value)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_decorator_catches_file_not_found_error(self, mock_print_info, mock_print_error):
        """Test that decorator catches and handles file not found errors."""
        @error_handler({'file_path': '/test/file.pdf'})
        def test_function():
            raise FileNotFoundError("File not found")
        
        with pytest.raises(CLIError) as exc_info:
            test_function()
        
        assert "File not found" in str(exc_info.value)
        mock_print_error.assert_called_once()
        mock_print_info.assert_called()
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_decorator_catches_permission_error(self, mock_print_info, mock_print_error):
        """Test that decorator catches and handles permission errors."""
        @error_handler({'operation': 'file_access'})
        def test_function():
            raise PermissionError("Permission denied")
        
        with pytest.raises(CLIError) as exc_info:
            test_function()
        
        assert "Permission denied" in str(exc_info.value)
        mock_print_error.assert_called_once()
        mock_print_info.assert_called()
    
    @patch('cli.error_handlers.print_info')
    def test_decorator_catches_keyboard_interrupt(self, mock_print_info):
        """Test that decorator catches and handles keyboard interrupt."""
        @error_handler({'operation': 'long_running'})
        def test_function():
            raise KeyboardInterrupt()
        
        with pytest.raises(CLIError) as exc_info:
            test_function()
        
        assert exc_info.value.exit_code == 130
        assert "cancelled by user" in str(exc_info.value)
        mock_print_info.assert_called_once_with("\nOperation cancelled by user.")
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    @patch('cli.error_handlers.logger')
    def test_decorator_catches_unexpected_error(self, mock_logger, mock_print_info, mock_print_error):
        """Test that decorator catches and handles unexpected errors."""
        @error_handler({'operation': 'test_unexpected'})
        def test_function():
            raise RuntimeError("Unexpected runtime error")
        
        with pytest.raises(CLIError) as exc_info:
            test_function()
        
        assert "Unexpected error" in str(exc_info.value)
        mock_logger.exception.assert_called_once()
        mock_print_error.assert_called_once()
        mock_print_info.assert_called()
        
        # Check that bug reporting guidance is provided
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("may be a bug" in call for call in info_calls)
    
    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata."""
        @error_handler({'operation': 'test'})
        def test_function():
            """Test function docstring."""
            return "success"
        
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring."
    
    def test_decorator_allows_successful_execution(self):
        """Test that decorator allows successful function execution."""
        @error_handler({'operation': 'test'})
        def test_function(x, y):
            return x + y
        
        result = test_function(2, 3)
        assert result == 5
    
    def test_decorator_with_no_context(self):
        """Test that decorator works with no error context provided."""
        @error_handler()
        def test_function():
            raise DatabaseError("Test error")
        
        with pytest.raises(CLIError):
            test_function()


class TestConvenienceFunctions:
    """Test convenience functions for common error handling patterns."""
    
    @patch('cli.error_handlers.ErrorHandler.handle_processing_error')
    def test_handle_file_operation_error_processing(self, mock_handle):
        """Test file operation error handling for processing errors."""
        error = ProcessingError("File processing failed")
        
        handle_file_operation_error(error, "/test/file.pdf", "processing")
        
        mock_handle.assert_called_once_with(
            error, 
            {'file_path': '/test/file.pdf', 'operation': 'processing'}
        )
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_file_operation_error_file_not_found(self, mock_print_info, mock_print_error):
        """Test file operation error handling for file not found."""
        error = FileNotFoundError("File not found")
        
        handle_file_operation_error(error, "/test/file.pdf", "reading")
        
        mock_print_error.assert_called_once_with("File not found during reading: /test/file.pdf")
        mock_print_info.assert_called()
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_handle_file_operation_error_permission(self, mock_print_info, mock_print_error):
        """Test file operation error handling for permission errors."""
        error = PermissionError("Permission denied")
        
        handle_file_operation_error(error, "/test/file.pdf", "writing")
        
        mock_print_error.assert_called_once_with("Permission denied during writing: /test/file.pdf")
        mock_print_info.assert_called()
    
    @patch('cli.error_handlers.ErrorHandler.handle_database_error')
    def test_handle_database_operation_error_database(self, mock_handle):
        """Test database operation error handling for database errors."""
        error = DatabaseError("Database connection failed")
        
        handle_database_operation_error(error, "connection", test_key="test_value")
        
        mock_handle.assert_called_once_with(
            error,
            {'operation': 'connection', 'test_key': 'test_value'}
        )
    
    @patch('cli.error_handlers.ErrorHandler.handle_part_not_found_error')
    def test_handle_database_operation_error_part_not_found(self, mock_handle):
        """Test database operation error handling for part not found."""
        error = PartNotFoundError("Part not found")
        
        handle_database_operation_error(error, "part_lookup", part_number="TEST123")
        
        mock_handle.assert_called_once_with(
            error,
            {'operation': 'part_lookup', 'part_number': 'TEST123'}
        )
    
    @patch('cli.error_handlers.ErrorHandler.handle_configuration_error')
    def test_handle_database_operation_error_configuration(self, mock_handle):
        """Test database operation error handling for configuration errors."""
        error = ConfigurationError("Config error")
        
        handle_database_operation_error(error, "config_update", config_key="test_key")
        
        mock_handle.assert_called_once_with(
            error,
            {'operation': 'config_update', 'config_key': 'test_key'}
        )


class TestErrorHandlerIntegration:
    """Test integration of error handling with actual CLI patterns."""
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_realistic_database_error_scenario(self, mock_print_info, mock_print_error):
        """Test a realistic database error scenario."""
        @error_handler({'operation': 'part_creation', 'command': 'parts add'})
        def create_part_command():
            # Simulate a database locked error during part creation
            raise DatabaseError("database is locked")
        
        with pytest.raises(CLIError) as exc_info:
            create_part_command()
        
        # Verify error message
        assert "Database operation failed" in str(exc_info.value)
        
        # Verify specific error handling was called
        mock_print_error.assert_called_once_with("Database is currently locked by another process")
        
        # Verify recovery suggestions were provided
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("Close any other instances" in call for call in info_calls)
    
    @patch('cli.error_handlers.print_error')
    @patch('cli.error_handlers.print_info')
    def test_realistic_processing_error_scenario(self, mock_print_info, mock_print_error):
        """Test a realistic processing error scenario."""
        @error_handler({'operation': 'invoice_processing', 'file_path': '/invoices/test.pdf'})
        def process_invoice_command():
            # Simulate a PDF processing error
            raise ProcessingError("PDF processing failed - file is corrupted")
        
        with pytest.raises(CLIError) as exc_info:
            process_invoice_command()
        
        # Verify error message
        assert "Processing failed" in str(exc_info.value)
        
        # Verify specific error handling was called
        mock_print_error.assert_called_once_with("PDF processing failed for: /invoices/test.pdf")
        
        # Verify PDF-specific recovery suggestions
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("PDF file is not corrupted" in call for call in info_calls)
    
    def test_error_context_propagation(self):
        """Test that error context is properly propagated through the decorator."""
        context_data = {
            'operation': 'test_operation',
            'file_path': '/test/file.pdf',
            'part_number': 'TEST123'
        }
        
        @error_handler(context_data)
        def test_function():
            raise PartNotFoundError("Part not found")
        
        with patch.object(ErrorHandler, 'handle_part_not_found_error') as mock_handle:
            with pytest.raises(CLIError):
                test_function()
            
            # Verify context was passed correctly
            mock_handle.assert_called_once()
            call_args = mock_handle.call_args
            assert call_args[0][1] == context_data  # Second argument should be context
    
    @patch('cli.error_handlers.logger')
    def test_logging_integration(self, mock_logger):
        """Test that errors are properly logged."""
        @error_handler({'operation': 'test_logging'})
        def test_function():
            raise DatabaseError("Test database error")
        
        with pytest.raises(CLIError):
            test_function()
        
        # Verify that the error was logged
        mock_logger.exception.assert_called_once_with("Database error in test_function")


if __name__ == '__main__':
    pytest.main([__file__])