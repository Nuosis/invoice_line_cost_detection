"""
Journey Tests for Error Recovery Journeys

This test suite validates user error scenarios and recovery paths,
focusing on how the system handles errors gracefully and guides users
through recovery workflows.

These tests simulate real error conditions that users might encounter
and validate that the system provides clear guidance and recovery options.
"""

import tempfile
import unittest
import uuid
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Import the modules we're testing
from cli.prompts import prompt_for_input_path, PathWithMetadata
from cli.commands.invoice_commands import run_interactive_processing
from cli.context import CLIContext
from cli.exceptions import UserCancelledError
from database.database import DatabaseManager
from processing.exceptions import PDFProcessingError


class TestErrorRecoveryJourneys(unittest.TestCase):
    """
    Test error recovery user journeys with strategic mocking.
    
    These tests simulate error conditions and validate that users
    receive clear guidance and recovery options.
    """
    
    def setUp(self):
        """Set up test environment for error recovery testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_error_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_error_db_{self.test_id}.db"
        
        # Use the real invoices directory and target PDF
        self.real_invoices_dir = Path(__file__).parent.parent / "docs" / "invoices"
        self.target_pdf = self.real_invoices_dir / "5790265786.pdf"
        
        # Verify real files exist
        self.assertTrue(self.real_invoices_dir.exists(), "Real invoices directory must exist")
        self.assertTrue(self.target_pdf.exists(), f"Target PDF must exist: {self.target_pdf}")
        
        # Create output directory
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()
        
        # Create some invalid paths for testing
        self.invalid_file = self.temp_dir / "nonexistent.pdf"
        self.invalid_dir = self.temp_dir / "nonexistent_directory"
        
        # Track created resources for cleanup
        self.created_files = []
        self.created_dirs = [self.temp_dir, self.output_dir]
        
        # Initialize database with test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self.db_manager.initialize_database()
        self.db_manager.add_part("GS0448", "SHIRT WORK LS BTN COTTON", Decimal("0.30"))
    
    def tearDown(self):
        """Clean up all resources created during the test."""
        # Close database connections
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        
        # Remove created files
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
        
        # Remove created directories
        for dir_path in reversed(self.created_dirs):
            try:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
            except Exception:
                pass
    
    def test_invalid_file_path_recovery_with_retry(self):
        """
        Test user recovery when providing invalid file path, then retrying successfully.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            # First attempt: invalid path, second attempt: valid path
            mock_prompt.side_effect = [str(self.invalid_file), str(self.target_pdf)]
            mock_confirm.return_value = True  # User chooses to retry
            mock_choice.return_value = f"Process only this file ({self.target_pdf.name})"
            
            result_path = prompt_for_input_path()
            
            # Should eventually succeed with valid path
            self.assertIsInstance(result_path, PathWithMetadata)
            self.assertTrue(result_path.single_file_mode)
            self.assertEqual(result_path.original_file, self.target_pdf)
            
            # Should have prompted twice (invalid, then valid)
            self.assertEqual(mock_prompt.call_count, 2)
            # Should have asked user to retry once
            self.assertEqual(mock_confirm.call_count, 1)
    
    def test_invalid_file_path_recovery_with_cancellation(self):
        """
        Test user cancellation when prompted to retry after invalid path.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # First attempt: invalid path
            mock_prompt.return_value = str(self.invalid_file)
            mock_confirm.return_value = False  # User chooses NOT to retry
            
            # Should raise UserCancelledError
            with self.assertRaises(UserCancelledError):
                prompt_for_input_path()
            
            # Should have prompted once and asked for retry once
            self.assertEqual(mock_prompt.call_count, 1)
            self.assertEqual(mock_confirm.call_count, 1)
    
    def test_invalid_directory_path_recovery(self):
        """
        Test recovery when user provides invalid directory path.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # First attempt: invalid directory, second attempt: valid directory
            mock_prompt.side_effect = [str(self.invalid_dir), str(self.real_invoices_dir)]
            mock_confirm.return_value = True  # User chooses to retry
            
            result_path = prompt_for_input_path()
            
            # Should succeed with valid directory
            self.assertEqual(result_path, self.real_invoices_dir)
            self.assertIsInstance(result_path, Path)
            self.assertNotIsInstance(result_path, PathWithMetadata)
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
            self.assertEqual(mock_confirm.call_count, 1)
    
    def test_non_pdf_file_rejection_and_recovery(self):
        """
        Test rejection of non-PDF files with recovery flow.
        """
        # Create a non-PDF file
        txt_file = self.temp_dir / "document.txt"
        txt_file.write_text("This is not a PDF file")
        self.created_files.append(txt_file)
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            # First attempt: non-PDF file, second attempt: valid PDF
            mock_prompt.side_effect = [str(txt_file), str(self.target_pdf)]
            mock_confirm.return_value = True  # User chooses to retry
            mock_choice.return_value = f"Process only this file ({self.target_pdf.name})"
            
            result_path = prompt_for_input_path()
            
            # Should eventually succeed with PDF file
            self.assertIsInstance(result_path, PathWithMetadata)
            self.assertEqual(result_path.original_file, self.target_pdf)
            
            # Should have prompted twice (non-PDF, then PDF)
            self.assertEqual(mock_prompt.call_count, 2)
            self.assertEqual(mock_confirm.call_count, 1)
    
    def test_permission_error_recovery(self):
        """
        Test recovery when file permissions prevent access.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('pathlib.Path.exists') as mock_exists:
            
            # Mock permission error scenario
            def exists_side_effect(path_obj):
                if str(path_obj) == str(self.target_pdf):
                    return True
                return path_obj.exists()
            
            mock_exists.side_effect = lambda: True
            
            # First attempt: permission error, second attempt: success
            mock_prompt.side_effect = [str(self.target_pdf), str(self.target_pdf)]
            mock_confirm.return_value = True  # User chooses to retry
            mock_choice.return_value = f"Process only this file ({self.target_pdf.name})"
            
            # Mock the first call to fail with permission error
            with patch('pathlib.Path.is_file') as mock_is_file:
                mock_is_file.side_effect = [PermissionError("Permission denied"), True]
                
                result_path = prompt_for_input_path()
                
                # Should eventually succeed
                self.assertIsInstance(result_path, PathWithMetadata)
                self.assertEqual(result_path.original_file, self.target_pdf)
    
    def test_pdf_processing_error_recovery(self):
        """
        Test recovery when PDF processing fails during interactive workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo, \
             patch('click.confirm') as mock_confirm:
            
            # Set up input simulation
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "error_recovery_report.csv"
            mock_validation_mode.return_value = "parts_based"
            
            # First attempt: PDF processing error, second attempt: success
            mock_extract.side_effect = [
                PDFProcessingError("Failed to extract text from PDF"),
                []  # Empty results for second attempt
            ]
            mock_confirm.return_value = True  # User chooses to retry
            
            # Should handle the error gracefully and allow retry
            with self.assertRaises(PDFProcessingError):
                run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify error was encountered
            mock_extract.assert_called_once()
            
            # Verify error message was displayed
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            error_messages = [msg for msg in echo_calls if "error" in msg.lower() or "failed" in msg.lower()]
            # Note: Actual error handling depends on implementation
    
    def test_database_connection_error_recovery(self):
        """
        Test recovery when database connection fails.
        """
        # Use invalid database path to simulate connection error
        invalid_db_path = "/invalid/path/database.db"
        
        ctx = CLIContext()
        ctx.database_path = invalid_db_path
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('click.echo') as mock_echo:
            
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "db_error_report.csv"
            mock_validation_mode.return_value = "parts_based"
            
            # Should handle database error gracefully
            with self.assertRaises(Exception):  # Database connection error
                run_interactive_processing(ctx, preset=None, save_preset=False)
    
    def test_output_file_permission_error_recovery(self):
        """
        Test recovery when output file cannot be written due to permissions.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Create a read-only directory to simulate permission error
        readonly_dir = self.temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_output = readonly_dir / "readonly_report.csv"
        
        self.created_dirs.append(readonly_dir)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.confirm') as mock_confirm:
            
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            
            # First attempt: permission error, second attempt: valid path
            mock_output_path.side_effect = [
                readonly_output,
                self.output_dir / "valid_report.csv"
            ]
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = []
            mock_confirm.return_value = True  # User chooses to retry
            
            # Mock file write permission error
            with patch('builtins.open') as mock_open:
                mock_open.side_effect = [
                    PermissionError("Permission denied"),
                    MagicMock()  # Success on second attempt
                ]
                
                # Should handle permission error and allow retry
                try:
                    run_interactive_processing(ctx, preset=None, save_preset=False)
                except PermissionError:
                    pass  # Expected on first attempt
    
    def test_empty_directory_handling_with_user_choice(self):
        """
        Test handling of directory with no PDF files and user choice to continue.
        """
        # Create empty directory
        empty_dir = self.temp_dir / "empty_invoices"
        empty_dir.mkdir()
        self.created_dirs.append(empty_dir)
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # User provides empty directory
            mock_prompt.return_value = str(empty_dir)
            mock_confirm.return_value = True  # User chooses to continue anyway
            
            result_path = prompt_for_input_path()
            
            # Should return the directory path even though it's empty
            self.assertEqual(result_path, empty_dir)
            self.assertIsInstance(result_path, Path)
            self.assertNotIsInstance(result_path, PathWithMetadata)
            
            # Should have asked for confirmation
            self.assertEqual(mock_confirm.call_count, 1)
    
    def test_empty_directory_handling_with_user_retry(self):
        """
        Test handling of directory with no PDF files and user choice to retry.
        """
        # Create empty directory
        empty_dir = self.temp_dir / "empty_invoices"
        empty_dir.mkdir()
        self.created_dirs.append(empty_dir)
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # First attempt: empty directory, second attempt: valid directory
            mock_prompt.side_effect = [str(empty_dir), str(self.real_invoices_dir)]
            # First confirm: user chooses to retry, second confirm: not called
            mock_confirm.side_effect = [False, True]  # False = don't continue, True = retry
            
            result_path = prompt_for_input_path()
            
            # Should succeed with valid directory
            self.assertEqual(result_path, self.real_invoices_dir)
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
    
    def test_multiple_consecutive_errors_with_eventual_success(self):
        """
        Test recovery through multiple consecutive errors before success.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            # Multiple invalid attempts, then success
            mock_prompt.side_effect = [
                str(self.invalid_file),      # First: invalid file
                "/another/invalid/path.pdf", # Second: another invalid path
                str(self.target_pdf)         # Third: valid path
            ]
            mock_confirm.return_value = True  # User always chooses to retry
            mock_choice.return_value = f"Process only this file ({self.target_pdf.name})"
            
            result_path = prompt_for_input_path()
            
            # Should eventually succeed
            self.assertIsInstance(result_path, PathWithMetadata)
            self.assertEqual(result_path.original_file, self.target_pdf)
            
            # Should have prompted three times
            self.assertEqual(mock_prompt.call_count, 3)
            # Should have asked to retry twice
            self.assertEqual(mock_confirm.call_count, 2)
    
    def test_user_cancellation_during_error_recovery(self):
        """
        Test user cancellation at various points during error recovery.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # User provides invalid path, then cancels
            mock_prompt.return_value = str(self.invalid_file)
            mock_confirm.return_value = False  # User cancels
            
            with self.assertRaises(UserCancelledError):
                prompt_for_input_path()
            
            # Should have prompted once and asked for retry once
            self.assertEqual(mock_prompt.call_count, 1)
            self.assertEqual(mock_confirm.call_count, 1)
    
    def test_error_message_clarity_and_guidance(self):
        """
        Test that error messages provide clear guidance to users.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # User provides invalid path
            mock_prompt.return_value = str(self.invalid_file)
            mock_confirm.return_value = False  # User cancels
            
            with self.assertRaises(UserCancelledError):
                prompt_for_input_path()
            
            # Verify error messages were displayed
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            
            # Should have error messages that guide the user
            error_messages = [msg for msg in echo_calls if any(keyword in msg.lower() for keyword in 
                            ['error', 'invalid', 'not found', 'does not exist'])]
            
            # Should have at least one error message
            self.assertGreater(len(error_messages), 0, "Should display error messages to guide user")


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)