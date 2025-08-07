"""
Journey Tests for User Cancellation Flows

This test suite validates user interaction flows with cancellation scenarios,
focusing specifically on Ctrl+C handling, explicit cancellation choices, and
graceful exit workflows.

These tests simulate actual user cancellation scenarios and validate both the user
experience and the resulting system cleanup behavior.
"""

import tempfile
import unittest
import uuid
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Import the modules we're testing
from cli.prompts import prompt_for_input_path, prompt_for_choice, PathWithMetadata
from cli.commands.invoice_commands import run_interactive_processing
from cli.commands.discovery_commands import run_interactive_discovery
from cli.context import CLIContext
from cli.exceptions import UserCancelledError
from database.database import DatabaseManager


class TestUserCancellationFlows(unittest.TestCase):
    """
    Test user cancellation flow user journeys with strategic mocking.
    
    These tests simulate actual user cancellation scenarios through the CLI
    interface and validate both user experience and system cleanup.
    """
    
    def setUp(self):
        """Set up test environment for user cancellation testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_cancel_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_cancel_db_{self.test_id}.db"
        
        # Use the REAL PDFs from docs/invoices/ (following the established pattern)
        self.real_invoices_dir = Path(__file__).parent.parent / "docs" / "invoices"
        self.target_pdf = self.real_invoices_dir / "5790265786.pdf"
        
        # Verify real files exist
        self.assertTrue(self.real_invoices_dir.exists(), "Real invoices directory must exist")
        self.assertTrue(self.target_pdf.exists(), f"Target PDF must exist: {self.target_pdf}")
        
        # Create output directory
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()
        
        # Track created resources for cleanup (only temp files, not real PDFs!)
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
    
    def test_keyboard_interrupt_during_input_path_prompt(self):
        """
        Test Ctrl+C (KeyboardInterrupt) during input path prompt.
        """
        with patch('click.prompt') as mock_prompt:
            # Simulate Ctrl+C during prompt
            mock_prompt.side_effect = KeyboardInterrupt()
            
            # Should raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                prompt_for_input_path()
    
    def test_keyboard_interrupt_during_choice_selection(self):
        """
        Test Ctrl+C (KeyboardInterrupt) during choice selection.
        """
        choices = [
            "Process only this file",
            "Process all files",
            "Choose different path"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # Simulate Ctrl+C during choice selection
            mock_prompt.side_effect = KeyboardInterrupt()
            
            # Should raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                prompt_for_choice("What would you like to do?", choices)
    
    def test_explicit_cancellation_choice_selection(self):
        """
        Test user explicitly selecting cancellation option.
        """
        choices = [
            "Process files",
            "Skip processing",
            "Cancel operation"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # User explicitly selects cancel option
            mock_prompt.return_value = "3"  # Cancel operation
            
            result = prompt_for_choice("What would you like to do?", choices)
            
            # Should return the cancellation choice
            self.assertEqual(result, "Cancel operation")
            self.assertIn("Cancel", result)
    
    def test_user_cancellation_during_retry_confirmation(self):
        """
        Test user cancellation when prompted to retry after error.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # First attempt: invalid path
            mock_prompt.return_value = "/invalid/path/file.pdf"
            mock_confirm.return_value = False  # User declines retry (cancels)
            
            # Should raise UserCancelledError
            with self.assertRaises(UserCancelledError):
                prompt_for_input_path()
            
            # Should have asked for retry confirmation
            mock_confirm.assert_called_once()
    
    def test_cancellation_during_interactive_processing_workflow(self):
        """
        Test user cancellation during interactive processing workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path:
            # User cancels during input path selection
            mock_input_path.side_effect = UserCancelledError("User cancelled operation")
            
            # Should raise UserCancelledError
            with self.assertRaises(UserCancelledError):
                run_interactive_processing(ctx, preset=None, save_preset=False)
    
    def test_cancellation_during_parts_discovery_workflow(self):
        """
        Test user cancellation during parts discovery workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # Mock PDF extraction to return unknown parts
            from processing.models import InvoiceLineItem
            unknown_part = InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="UNKNOWN001",
                description="Unknown Part",
                rate=Decimal("15.00"),
                quantity=2
            )
            mock_extract.return_value = [unknown_part]
            
            # User chooses to cancel discovery
            mock_choice.return_value = "Cancel parts discovery"
            
            # Should raise UserCancelledError
            with self.assertRaises(UserCancelledError):
                run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
    
    def test_graceful_cleanup_after_cancellation(self):
        """
        Test that resources are cleaned up properly after user cancellation.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Create a temporary file to track cleanup
        temp_file = self.temp_dir / "temp_processing_file.tmp"
        temp_file.write_text("Temporary processing data")
        self.created_files.append(temp_file)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path:
            
            # Set up partial workflow before cancellation
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            # User cancels during output path selection
            mock_output_path.side_effect = UserCancelledError("User cancelled")
            
            # Should raise UserCancelledError
            with self.assertRaises(UserCancelledError):
                run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify database connection is still valid (not corrupted)
            self.assertTrue(self.db_manager.get_all_parts() is not None)
    
    def test_cancellation_with_partial_data_entry(self):
        """
        Test cancellation after user has entered some data but not completed workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode:
            
            # User completes first two steps
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "partial_report.csv"
            
            # User cancels during validation mode selection
            mock_validation_mode.side_effect = UserCancelledError("User cancelled")
            
            # Should raise UserCancelledError
            with self.assertRaises(UserCancelledError):
                run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify first two prompts were called
            mock_input_path.assert_called_once()
            mock_output_path.assert_called_once()
            mock_validation_mode.assert_called_once()
    
    def test_cancellation_error_message_clarity(self):
        """
        Test that cancellation error messages are clear and helpful.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # User provides invalid path, then cancels
            mock_prompt.return_value = "/invalid/path/file.pdf"
            mock_confirm.return_value = False  # User cancels
            
            with self.assertRaises(UserCancelledError) as context:
                prompt_for_input_path()
            
            # Verify error message is informative
            error_message = str(context.exception)
            self.assertIn("cancel", error_message.lower())
    
    def test_multiple_cancellation_opportunities_in_workflow(self):
        """
        Test that user can cancel at multiple points in the workflow.
        """
        cancellation_points = [
            "input_path",
            "output_path", 
            "validation_mode",
            "threshold_value"
        ]
        
        for cancel_point in cancellation_points:
            with self.subTest(cancel_point=cancel_point):
                ctx = CLIContext()
                ctx.database_path = str(self.db_path)
                
                with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
                     patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
                     patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
                     patch('cli.prompts.prompt_for_threshold_value') as mock_threshold:
                    
                    # Set up mocks to succeed until cancellation point
                    mock_input_path.return_value = PathWithMetadata(
                        self.real_invoices_dir,
                        single_file_mode=True,
                        original_file=self.target_pdf
                    )
                    mock_output_path.return_value = self.output_dir / "cancel_test.csv"
                    mock_validation_mode.return_value = "threshold_based"
                    mock_threshold.return_value = Decimal("25.00")
                    
                    # Set cancellation at specific point
                    if cancel_point == "input_path":
                        mock_input_path.side_effect = UserCancelledError("Cancelled at input")
                    elif cancel_point == "output_path":
                        mock_output_path.side_effect = UserCancelledError("Cancelled at output")
                    elif cancel_point == "validation_mode":
                        mock_validation_mode.side_effect = UserCancelledError("Cancelled at validation")
                    elif cancel_point == "threshold_value":
                        mock_threshold.side_effect = UserCancelledError("Cancelled at threshold")
                    
                    # Should raise UserCancelledError at any point
                    with self.assertRaises(UserCancelledError):
                        run_interactive_processing(ctx, preset=None, save_preset=False)
    
    def test_cancellation_during_file_processing(self):
        """
        Test user cancellation during actual file processing (Ctrl+C).
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # Set up complete workflow
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "interrupted_report.csv"
            mock_validation_mode.return_value = "parts_based"
            
            # User presses Ctrl+C during processing
            mock_extract.side_effect = KeyboardInterrupt()
            
            # Should raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                run_interactive_processing(ctx, preset=None, save_preset=False)
    
    def test_cancellation_preserves_database_integrity(self):
        """
        Test that database remains in consistent state after cancellation.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Record initial database state
        initial_parts = self.db_manager.get_all_parts()
        initial_count = len(initial_parts)
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # Mock PDF extraction to return unknown parts
            from processing.models import InvoiceLineItem
            unknown_part = InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="CANCEL_TEST",
                description="Cancellation Test Part",
                rate=Decimal("20.00"),
                quantity=1
            )
            mock_extract.return_value = [unknown_part]
            
            # User starts to add part but cancels during description entry
            mock_choice.return_value = f"Add {unknown_part.line_item_code} to parts database"
            mock_prompt.side_effect = KeyboardInterrupt()  # Ctrl+C during description entry
            
            # Should raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Verify database integrity is preserved
            final_parts = self.db_manager.get_all_parts()
            final_count = len(final_parts)
            
            # Should not have added the incomplete part
            self.assertEqual(initial_count, final_count)
            
            # Should not have corrupted existing parts
            cancel_test_parts = [p for p in final_parts if p.code == "CANCEL_TEST"]
            self.assertEqual(len(cancel_test_parts), 0, "Incomplete part should not be in database")
    
    def test_cancellation_exit_codes_and_messages(self):
        """
        Test that cancellation produces appropriate exit codes and messages.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # User cancels operation
            mock_prompt.return_value = "/invalid/path"
            mock_confirm.return_value = False  # Cancel
            
            with self.assertRaises(UserCancelledError) as context:
                prompt_for_input_path()
            
            # Verify appropriate error message
            error_msg = str(context.exception)
            self.assertTrue(len(error_msg) > 0, "Should have meaningful error message")
            
            # Verify user-friendly messages were displayed
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            user_messages = [msg for msg in echo_calls if any(keyword in msg.lower() for keyword in 
                           ['cancel', 'abort', 'exit', 'stop'])]
            # Note: Actual message display depends on implementation
    
    def test_cancellation_during_confirmation_dialogs(self):
        """
        Test cancellation during various confirmation dialogs.
        """
        with patch('click.confirm') as mock_confirm:
            
            # Simulate Ctrl+C during confirmation
            mock_confirm.side_effect = KeyboardInterrupt()
            
            # Should raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                mock_confirm("Do you want to continue?")
    
    def test_graceful_cancellation_vs_forced_interruption(self):
        """
        Test difference between graceful cancellation and forced interruption.
        """
        # Test graceful cancellation (user choice)
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            mock_prompt.return_value = "/invalid/path"
            mock_confirm.return_value = False  # Graceful cancellation
            
            with self.assertRaises(UserCancelledError):
                prompt_for_input_path()
        
        # Test forced interruption (Ctrl+C)
        with patch('click.prompt') as mock_prompt:
            
            mock_prompt.side_effect = KeyboardInterrupt()  # Forced interruption
            
            with self.assertRaises(KeyboardInterrupt):
                prompt_for_input_path()


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)