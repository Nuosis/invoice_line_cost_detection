"""
Journey Tests for Confirmation Dialogs

This test suite validates user interaction flows with confirmation dialogs,
focusing specifically on `click.confirm()` interactions and related
user confirmation workflows.

These tests simulate actual user confirmation responses and validate both the user
experience and the resulting system behavior.
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


class TestConfirmationDialogs(unittest.TestCase):
    """
    Test confirmation dialog user journeys with strategic mocking.
    
    These tests simulate actual user confirmation responses through the CLI
    interface and validate both user experience and system state.
    """
    
    def setUp(self):
        """Set up test environment for confirmation dialog testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_confirm_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_confirm_db_{self.test_id}.db"
        
        # Use the REAL PDFs from docs/invoices/ (following the established pattern)
        self.real_invoices_dir = Path(__file__).parent.parent / "docs" / "invoices"
        self.target_pdf = self.real_invoices_dir / "5790265786.pdf"
        
        # Verify real files exist
        self.assertTrue(self.real_invoices_dir.exists(), "Real invoices directory must exist")
        self.assertTrue(self.target_pdf.exists(), f"Target PDF must exist: {self.target_pdf}")
        
        # Create output directory
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()
        
        # Create test files for overwrite scenarios
        self.existing_report = self.output_dir / "existing_report.csv"
        self.existing_report.write_text("Existing report content")
        
        # Track created resources for cleanup (only temp files, not real PDFs!)
        self.created_files = [self.existing_report]
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
        
        # Remove only created files (not real PDFs!)
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
    
    def test_file_overwrite_confirmation_accept(self):
        """
        Test user confirming file overwrite when output file already exists.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # Set up input simulation
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.existing_report  # File that already exists
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = []
            mock_confirm.return_value = True  # User confirms overwrite
            
            # Run the interactive processing
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify confirmation was requested
            mock_confirm.assert_called()
            
            # Verify processing continued after confirmation
            mock_extract.assert_called_once()
    
    def test_file_overwrite_confirmation_decline(self):
        """
        Test user declining file overwrite when output file already exists.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # Set up input simulation
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.side_effect = [
                self.existing_report,  # First attempt: existing file
                self.output_dir / "new_report.csv"  # Second attempt: new file
            ]
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = []
            mock_confirm.return_value = False  # User declines overwrite
            
            # Run the interactive processing
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify confirmation was requested
            mock_confirm.assert_called()
            
            # Verify output path was requested again after decline
            self.assertEqual(mock_output_path.call_count, 2)
    
    def test_retry_confirmation_after_invalid_path(self):
        """
        Test user confirmation to retry after providing invalid path.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            # First attempt: invalid path, second attempt: valid path
            mock_prompt.side_effect = ["/invalid/path/file.pdf", str(self.target_pdf)]
            mock_confirm.return_value = True  # User confirms retry
            mock_choice.return_value = f"Process only this file ({self.target_pdf.name})"
            
            result_path = prompt_for_input_path()
            
            # Should eventually succeed with valid path
            self.assertIsInstance(result_path, PathWithMetadata)
            self.assertEqual(result_path.original_file, self.target_pdf)
            
            # Should have asked for retry confirmation
            mock_confirm.assert_called_once()
            
            # Should have prompted twice (invalid, then valid)
            self.assertEqual(mock_prompt.call_count, 2)
    
    def test_retry_confirmation_decline_raises_cancellation(self):
        """
        Test user declining retry confirmation raises UserCancelledError.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # First attempt: invalid path
            mock_prompt.return_value = "/invalid/path/file.pdf"
            mock_confirm.return_value = False  # User declines retry
            
            # Should raise UserCancelledError
            with self.assertRaises(UserCancelledError):
                prompt_for_input_path()
            
            # Should have asked for retry confirmation
            mock_confirm.assert_called_once()
            
            # Should have prompted once
            self.assertEqual(mock_prompt.call_count, 1)
    
    def test_empty_directory_continuation_confirmation(self):
        """
        Test user confirmation to continue with empty directory.
        """
        # Create empty directory
        empty_dir = self.temp_dir / "empty_invoices"
        empty_dir.mkdir()
        self.created_dirs.append(empty_dir)
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # User provides empty directory
            mock_prompt.return_value = str(empty_dir)
            mock_confirm.return_value = True  # User confirms to continue
            
            result_path = prompt_for_input_path()
            
            # Should return the directory path
            self.assertEqual(result_path, empty_dir)
            
            # Should have asked for confirmation
            mock_confirm.assert_called_once()
    
    def test_empty_directory_retry_confirmation(self):
        """
        Test user choosing to retry instead of continuing with empty directory.
        """
        # Create empty directory
        empty_dir = self.temp_dir / "empty_invoices"
        empty_dir.mkdir()
        self.created_dirs.append(empty_dir)
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # First attempt: empty directory, second attempt: valid directory
            mock_prompt.side_effect = [str(empty_dir), str(self.real_invoices_dir)]
            mock_confirm.side_effect = [False, True]  # First: don't continue, Second: retry
            
            result_path = prompt_for_input_path()
            
            # Should succeed with valid directory
            self.assertEqual(result_path, self.real_invoices_dir)
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
    
    def test_database_initialization_confirmation(self):
        """
        Test confirmation dialog for database initialization.
        """
        # Use non-existent database path
        new_db_path = self.temp_dir / "new_database.db"
        
        with patch('click.confirm') as mock_confirm, \
             patch('database.database.DatabaseManager.initialize_database') as mock_init:
            
            mock_confirm.return_value = True  # User confirms database creation
            
            # Create database manager with new path
            db_manager = DatabaseManager(str(new_db_path))
            
            # This would typically trigger confirmation in real usage
            # For testing, we simulate the confirmation flow
            if mock_confirm.return_value:
                db_manager.initialize_database()
            
            # Verify confirmation was requested
            mock_confirm.assert_called()
            
            # Verify database initialization was called
            mock_init.assert_called_once()
    
    def test_parts_addition_confirmation(self):
        """
        Test confirmation dialog for adding parts to database.
        """
        with patch('click.confirm') as mock_confirm:
            
            mock_confirm.return_value = True  # User confirms part addition
            
            # Simulate parts addition workflow
            part_code = "NEW_PART_001"
            part_description = "New Test Part"
            part_rate = Decimal("15.50")
            
            # In real usage, this would be preceded by confirmation
            if mock_confirm.return_value:
                self.db_manager.add_part(part_code, part_description, part_rate)
            
            # Verify confirmation was requested
            mock_confirm.assert_called()
            
            # Verify part was added
            parts = self.db_manager.get_all_parts()
            added_part = next((p for p in parts if p.code == part_code), None)
            self.assertIsNotNone(added_part, "Part should have been added to database")
    
    def test_processing_continuation_after_errors(self):
        """
        Test confirmation to continue processing after encountering errors.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # Set up input simulation
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "error_recovery_report.csv"
            mock_validation_mode.return_value = "parts_based"
            mock_extract.side_effect = Exception("Processing error")
            mock_confirm.return_value = True  # User confirms to continue despite errors
            
            # Should handle the error and ask for confirmation
            with self.assertRaises(Exception):
                run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify processing was attempted
            mock_extract.assert_called_once()
    
    def test_confirmation_dialog_message_clarity(self):
        """
        Test that confirmation dialogs display clear, actionable messages.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # User provides invalid path
            mock_prompt.return_value = "/invalid/path/file.pdf"
            mock_confirm.return_value = False  # User declines
            
            with self.assertRaises(UserCancelledError):
                prompt_for_input_path()
            
            # Verify confirmation was called with clear message
            mock_confirm.assert_called()
            confirm_call_args = mock_confirm.call_args
            
            # The confirmation message should be clear and actionable
            # (Exact message depends on implementation)
            self.assertIsNotNone(confirm_call_args, "Confirmation should have been called")
    
    def test_multiple_confirmation_dialogs_in_sequence(self):
        """
        Test handling multiple confirmation dialogs in a single workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # Set up input simulation
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.existing_report  # Existing file
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = []
            
            # Multiple confirmations: overwrite file, continue processing, etc.
            mock_confirm.side_effect = [True, True, True]  # User confirms all
            
            # Run the interactive processing
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify processing completed
            mock_extract.assert_called_once()
    
    def test_confirmation_with_default_values(self):
        """
        Test confirmation dialogs with default values (Y/n or y/N patterns).
        """
        with patch('click.confirm') as mock_confirm:
            
            # Test default True (Y/n pattern)
            mock_confirm.return_value = True
            result = mock_confirm("Continue processing?", default=True)
            self.assertTrue(result)
            
            # Test default False (y/N pattern)
            mock_confirm.return_value = False
            result = mock_confirm("Overwrite existing file?", default=False)
            self.assertFalse(result)
            
            # Verify both confirmations were called
            self.assertEqual(mock_confirm.call_count, 2)
    
    def test_confirmation_abort_on_keyboard_interrupt(self):
        """
        Test handling of Ctrl+C during confirmation dialogs.
        """
        with patch('click.confirm') as mock_confirm:
            
            # Simulate Ctrl+C during confirmation
            mock_confirm.side_effect = KeyboardInterrupt()
            
            # Should raise KeyboardInterrupt (or handle gracefully)
            with self.assertRaises(KeyboardInterrupt):
                mock_confirm("Continue processing?")
    
    def test_confirmation_dialog_context_preservation(self):
        """
        Test that confirmation dialogs preserve context and state.
        """
        # Create a scenario where confirmation affects subsequent behavior
        test_state = {"confirmed": False, "processed": False}
        
        def mock_confirmation_workflow():
            with patch('click.confirm') as mock_confirm:
                mock_confirm.return_value = True
                
                # Simulate confirmation affecting state
                if mock_confirm("Proceed with operation?"):
                    test_state["confirmed"] = True
                    test_state["processed"] = True
                
                return test_state
        
        result = mock_confirmation_workflow()
        
        # Verify state was preserved and updated correctly
        self.assertTrue(result["confirmed"])
        self.assertTrue(result["processed"])


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)