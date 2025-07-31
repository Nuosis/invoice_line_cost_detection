"""
Journey Tests for Validation Mode Selection

This test suite validates user interaction flows with validation mode selection prompts,
focusing specifically on validation mode configuration, threshold value entry, and
validation strategy selection workflows.

These tests simulate actual user interactions during validation configuration
and validate both the user experience and the resulting system behavior.
"""

import tempfile
import unittest
import uuid
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Import the modules we're testing
from cli.prompts import prompt_for_validation_mode, prompt_for_threshold_value, prompt_for_choice
from cli.commands.invoice_commands import run_interactive_processing
from cli.context import CLIContext
from cli.exceptions import UserCancelledError
from database.database import DatabaseManager


class TestValidationModeSelection(unittest.TestCase):
    """
    Test validation mode selection prompt user journeys with strategic mocking.
    
    These tests simulate actual user interactions during validation mode
    configuration and validate both user experience and system state.
    """
    
    def setUp(self):
        """Set up test environment for validation mode selection testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_validation_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_validation_db_{self.test_id}.db"
        
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
        
        # Add test parts with various rates
        self.db_manager.add_part("GS0448", "SHIRT WORK LS BTN COTTON", Decimal("0.30"))
        self.db_manager.add_part("LOW_RATE", "Low Rate Part", Decimal("5.00"))
        self.db_manager.add_part("HIGH_RATE", "High Rate Part", Decimal("50.00"))
    
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
    
    def test_parts_based_validation_selection(self):
        """
        Test user selecting parts-based validation mode.
        """
        validation_modes = [
            "Parts-based validation (recommended)",
            "Threshold-based validation",
            "Both validation methods"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # User selects parts-based validation
            mock_prompt.return_value = "1"
            
            result = prompt_for_choice("Select validation mode:", validation_modes)
            
            # Should return parts-based validation
            self.assertEqual(result, "Parts-based validation (recommended)")
            self.assertIn("Parts-based", result)
            self.assertIn("recommended", result)
    
    def test_threshold_based_validation_selection(self):
        """
        Test user selecting threshold-based validation mode.
        """
        validation_modes = [
            "Parts-based validation (recommended)",
            "Threshold-based validation",
            "Both validation methods"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # User selects threshold-based validation
            mock_prompt.return_value = "2"
            
            result = prompt_for_choice("Select validation mode:", validation_modes)
            
            # Should return threshold-based validation
            self.assertEqual(result, "Threshold-based validation")
            self.assertIn("Threshold-based", result)
    
    def test_both_validation_methods_selection(self):
        """
        Test user selecting both validation methods.
        """
        validation_modes = [
            "Parts-based validation (recommended)",
            "Threshold-based validation",
            "Both validation methods"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # User selects both validation methods
            mock_prompt.return_value = "3"
            
            result = prompt_for_choice("Select validation mode:", validation_modes)
            
            # Should return both validation methods
            self.assertEqual(result, "Both validation methods")
            self.assertIn("Both", result)
    
    def test_validation_mode_text_input_matching(self):
        """
        Test validation mode selection with text input matching.
        """
        validation_modes = [
            "Parts-based validation (recommended)",
            "Threshold-based validation",
            "Both validation methods"
        ]
        
        test_cases = [
            ("parts", "Parts-based validation (recommended)"),
            ("threshold", "Threshold-based validation"),
            ("both", "Both validation methods"),
            ("PARTS", "Parts-based validation (recommended)"),  # Case insensitive
            ("Threshold", "Threshold-based validation")
        ]
        
        for user_input, expected_result in test_cases:
            with self.subTest(user_input=user_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result = prompt_for_choice("Select validation mode:", validation_modes)
                    
                    self.assertEqual(result, expected_result)
    
    def test_threshold_value_entry_workflow(self):
        """
        Test user entering threshold value for threshold-based validation.
        """
        test_threshold_values = [
            ("10.00", Decimal("10.00")),
            ("25.50", Decimal("25.50")),
            ("100", Decimal("100.00")),
            ("0.50", Decimal("0.50"))
        ]
        
        for user_input, expected_decimal in test_threshold_values:
            with self.subTest(threshold=user_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result = prompt_for_threshold_value()
                    
                    # Should return Decimal value
                    self.assertIsInstance(result, Decimal)
                    self.assertEqual(result, expected_decimal)
    
    def test_invalid_threshold_value_retry_workflow(self):
        """
        Test user recovery when providing invalid threshold value.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.echo') as mock_echo:
            
            # First attempt: invalid value, second attempt: valid value
            mock_prompt.side_effect = ["invalid_number", "25.00"]
            
            result = prompt_for_threshold_value()
            
            # Should eventually succeed with valid value
            self.assertEqual(result, Decimal("25.00"))
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
            
            # Should have displayed error message
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            error_messages = [msg for msg in echo_calls if "invalid" in msg.lower() or "error" in msg.lower()]
            self.assertGreater(len(error_messages), 0, "Should display error message for invalid threshold")
    
    def test_negative_threshold_value_handling(self):
        """
        Test handling of negative threshold values.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.echo') as mock_echo:
            
            # First attempt: negative value, second attempt: positive value
            mock_prompt.side_effect = ["-10.00", "10.00"]
            
            result = prompt_for_threshold_value()
            
            # Should eventually succeed with positive value
            self.assertEqual(result, Decimal("10.00"))
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
    
    def test_zero_threshold_value_handling(self):
        """
        Test handling of zero threshold value.
        """
        with patch('click.prompt') as mock_prompt:
            # User provides zero threshold
            mock_prompt.return_value = "0.00"
            
            result = prompt_for_threshold_value()
            
            # Should accept zero as valid threshold
            self.assertEqual(result, Decimal("0.00"))
    
    def test_complete_validation_mode_workflow_in_interactive_processing(self):
        """
        Test complete validation mode selection within interactive processing workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Set up input simulation
            from cli.prompts import PathWithMetadata
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "validation_mode_test.csv"
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = []
            
            # Run the interactive processing
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify validation mode was requested
            mock_validation_mode.assert_called_once()
            
            # Verify processing completed
            mock_extract.assert_called_once()
    
    def test_threshold_based_validation_with_threshold_entry(self):
        """
        Test threshold-based validation workflow including threshold value entry.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('cli.prompts.prompt_for_threshold_value') as mock_threshold, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Set up input simulation
            from cli.prompts import PathWithMetadata
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "threshold_validation_test.csv"
            mock_validation_mode.return_value = "threshold_based"
            mock_threshold.return_value = Decimal("30.00")
            mock_extract.return_value = []
            
            # Run the interactive processing
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify validation mode was requested
            mock_validation_mode.assert_called_once()
            
            # Verify threshold value was requested
            mock_threshold.assert_called_once()
            
            # Verify processing completed
            mock_extract.assert_called_once()
    
    def test_validation_mode_default_selection(self):
        """
        Test default validation mode selection when user provides empty input.
        """
        validation_modes = [
            "Parts-based validation (recommended)",
            "Threshold-based validation",
            "Both validation methods"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # User provides empty input (should use default)
            mock_prompt.return_value = ""
            
            result = prompt_for_choice("Select validation mode:", validation_modes, default=1)
            
            # Should return the default choice (first option)
            self.assertEqual(result, "Parts-based validation (recommended)")
    
    def test_validation_mode_invalid_choice_retry(self):
        """
        Test user recovery when providing invalid validation mode choice.
        """
        validation_modes = [
            "Parts-based validation (recommended)",
            "Threshold-based validation",
            "Both validation methods"
        ]
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.echo') as mock_echo:
            
            # First attempt: invalid choice, second attempt: valid choice
            mock_prompt.side_effect = ["invalid_mode", "parts"]
            
            result = prompt_for_choice("Select validation mode:", validation_modes)
            
            # Should eventually succeed
            self.assertEqual(result, "Parts-based validation (recommended)")
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
    
    def test_threshold_value_precision_handling(self):
        """
        Test handling of threshold values with various decimal precisions.
        """
        test_cases = [
            ("10", Decimal("10.00")),
            ("10.5", Decimal("10.50")),
            ("10.50", Decimal("10.50")),
            ("10.555", Decimal("10.555")),  # High precision
            ("0.01", Decimal("0.01")),      # Very small value
            ("999.99", Decimal("999.99"))   # Large value
        ]
        
        for user_input, expected_decimal in test_cases:
            with self.subTest(input_value=user_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result = prompt_for_threshold_value()
                    
                    self.assertEqual(result, expected_decimal)
    
    def test_validation_mode_help_text_display(self):
        """
        Test that validation mode selection displays helpful information.
        """
        validation_modes = [
            "Parts-based validation (recommended)",
            "Threshold-based validation",
            "Both validation methods"
        ]
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.echo') as mock_echo:
            
            mock_prompt.return_value = "1"
            
            result = prompt_for_choice("Select validation mode:", validation_modes)
            
            # Verify help text was displayed
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            
            # Should display the question and options
            question_displayed = any("validation mode" in str(call).lower() for call in echo_calls)
            self.assertTrue(question_displayed, "Should display validation mode question")
            
            # Should display options with numbers
            for i, mode in enumerate(validation_modes, 1):
                option_displayed = any(f"{i}" in str(call) and mode in str(call) for call in echo_calls)
                self.assertTrue(option_displayed, f"Should display option {i}: {mode}")
    
    def test_threshold_value_currency_format_handling(self):
        """
        Test handling of threshold values with currency symbols.
        """
        test_cases = [
            ("$25.00", Decimal("25.00")),
            ("25.00$", Decimal("25.00")),
            ("$25", Decimal("25.00")),
            ("25", Decimal("25.00"))
        ]
        
        for user_input, expected_decimal in test_cases:
            with self.subTest(input_value=user_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result = prompt_for_threshold_value()
                    
                    # Should strip currency symbols and parse correctly
                    self.assertEqual(result, expected_decimal)
    
    def test_validation_mode_configuration_persistence(self):
        """
        Test that validation mode configuration persists through workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Test that the selected validation mode is used consistently
        selected_mode = "threshold_based"
        threshold_value = Decimal("40.00")
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('cli.prompts.prompt_for_threshold_value') as mock_threshold, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # Set up consistent configuration
            from cli.prompts import PathWithMetadata
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "persistence_test.csv"
            mock_validation_mode.return_value = selected_mode
            mock_threshold.return_value = threshold_value
            mock_extract.return_value = []
            
            # Run the interactive processing
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify configuration was used consistently
            mock_validation_mode.assert_called_once()
            mock_threshold.assert_called_once()
    
    def test_validation_mode_with_empty_parts_database(self):
        """
        Test validation mode selection when parts database is empty.
        """
        # Create empty database
        empty_db_path = self.temp_dir / "empty_db.db"
        empty_db_manager = DatabaseManager(str(empty_db_path))
        empty_db_manager.initialize_database()
        empty_db_manager.close()
        
        validation_modes = [
            "Parts-based validation (recommended)",
            "Threshold-based validation",
            "Both validation methods"
        ]
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.echo') as mock_echo:
            
            # User selects parts-based validation despite empty database
            mock_prompt.return_value = "1"
            
            result = prompt_for_choice("Select validation mode:", validation_modes)
            
            # Should still allow parts-based selection
            self.assertEqual(result, "Parts-based validation (recommended)")
            
            # Should potentially warn about empty database
            # (Implementation-specific behavior)


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)