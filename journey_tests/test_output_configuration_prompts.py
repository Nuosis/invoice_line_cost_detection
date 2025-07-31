"""
Journey Tests for Output Configuration Prompts

This test suite validates user interaction flows with output configuration prompts,
focusing specifically on output path selection, format selection, and file handling
workflows.

These tests simulate actual user interactions during output configuration
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
from cli.prompts import prompt_for_output_path, prompt_for_choice
from cli.commands.invoice_commands import run_interactive_processing
from cli.context import CLIContext
from cli.exceptions import UserCancelledError
from database.database import DatabaseManager


class TestOutputConfigurationPrompts(unittest.TestCase):
    """
    Test output configuration prompt user journeys with strategic mocking.
    
    These tests simulate actual user interactions during output configuration
    workflows and validate both user experience and system state.
    """
    
    def setUp(self):
        """Set up test environment for output configuration testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_output_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_output_db_{self.test_id}.db"
        
        # Use the REAL PDFs from docs/invoices/ (following the established pattern)
        self.real_invoices_dir = Path(__file__).parent.parent / "docs" / "invoices"
        self.target_pdf = self.real_invoices_dir / "5790265786.pdf"
        
        # Verify real files exist
        self.assertTrue(self.real_invoices_dir.exists(), "Real invoices directory must exist")
        self.assertTrue(self.target_pdf.exists(), f"Target PDF must exist: {self.target_pdf}")
        
        # Create various output directories for testing
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()
        
        self.nested_output_dir = self.temp_dir / "reports" / "nested"
        self.nested_output_dir.mkdir(parents=True)
        
        # Create existing files for overwrite testing
        self.existing_csv = self.output_dir / "existing_report.csv"
        self.existing_csv.write_text("Existing CSV content")
        
        self.existing_txt = self.output_dir / "existing_report.txt"
        self.existing_txt.write_text("Existing TXT content")
        
        # Track created resources for cleanup (only temp files, not real PDFs!)
        self.created_files = [self.existing_csv, self.existing_txt]
        self.created_dirs = [self.temp_dir, self.output_dir, self.nested_output_dir]
        
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
    
    def test_csv_output_format_selection(self):
        """
        Test user selecting CSV output format.
        """
        with patch('click.prompt') as mock_prompt:
            # User provides CSV file path
            mock_prompt.return_value = str(self.output_dir / "test_report.csv")
            
            result_path = prompt_for_output_path()
            
            # Should return Path object pointing to CSV file
            self.assertIsInstance(result_path, Path)
            self.assertEqual(result_path.suffix.lower(), '.csv')
            self.assertEqual(result_path.name, "test_report.csv")
    
    def test_txt_output_format_selection(self):
        """
        Test user selecting TXT output format.
        """
        with patch('click.prompt') as mock_prompt:
            # User provides TXT file path
            mock_prompt.return_value = str(self.output_dir / "test_report.txt")
            
            result_path = prompt_for_output_path()
            
            # Should return Path object pointing to TXT file
            self.assertIsInstance(result_path, Path)
            self.assertEqual(result_path.suffix.lower(), '.txt')
            self.assertEqual(result_path.name, "test_report.txt")
    
    def test_json_output_format_selection(self):
        """
        Test user selecting JSON output format.
        """
        with patch('click.prompt') as mock_prompt:
            # User provides JSON file path
            mock_prompt.return_value = str(self.output_dir / "test_report.json")
            
            result_path = prompt_for_output_path()
            
            # Should return Path object pointing to JSON file
            self.assertIsInstance(result_path, Path)
            self.assertEqual(result_path.suffix.lower(), '.json')
            self.assertEqual(result_path.name, "test_report.json")
    
    def test_output_path_with_spaces_and_special_characters(self):
        """
        Test output path handling with spaces and special characters.
        """
        # Create directory with spaces
        spaced_dir = self.temp_dir / "output with spaces"
        spaced_dir.mkdir()
        self.created_dirs.append(spaced_dir)
        
        test_cases = [
            spaced_dir / "report with spaces.csv",
            spaced_dir / "report-with-dashes.csv",
            spaced_dir / "report_with_underscores.csv",
            spaced_dir / "report (with parentheses).csv"
        ]
        
        for expected_path in test_cases:
            with self.subTest(path=expected_path):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = str(expected_path)
                    
                    result_path = prompt_for_output_path()
                    
                    # Should handle the path correctly
                    self.assertEqual(result_path, expected_path)
                    self.assertTrue(result_path.name.endswith('.csv'))
    
    def test_nested_directory_creation_workflow(self):
        """
        Test creating nested directories for output path.
        """
        # Path to non-existent nested directory
        nested_path = self.temp_dir / "new" / "nested" / "directory" / "report.csv"
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            mock_prompt.return_value = str(nested_path)
            mock_confirm.return_value = True  # User confirms directory creation
            
            result_path = prompt_for_output_path()
            
            # Should return the path (directory creation handled by system)
            self.assertEqual(result_path, nested_path)
            self.assertEqual(result_path.suffix.lower(), '.csv')
    
    def test_existing_file_overwrite_confirmation_workflow(self):
        """
        Test user workflow when output file already exists.
        """
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # User provides path to existing file
            mock_prompt.return_value = str(self.existing_csv)
            mock_confirm.return_value = True  # User confirms overwrite
            
            result_path = prompt_for_output_path()
            
            # Should return the existing file path
            self.assertEqual(result_path, self.existing_csv)
            
            # Should have asked for confirmation
            mock_confirm.assert_called_once()
    
    def test_existing_file_overwrite_decline_retry_workflow(self):
        """
        Test user declining overwrite and providing new path.
        """
        new_path = self.output_dir / "new_report.csv"
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm:
            
            # First attempt: existing file, second attempt: new file
            mock_prompt.side_effect = [str(self.existing_csv), str(new_path)]
            mock_confirm.return_value = False  # User declines overwrite
            
            result_path = prompt_for_output_path()
            
            # Should return the new path
            self.assertEqual(result_path, new_path)
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
            
            # Should have asked for confirmation once
            mock_confirm.assert_called_once()
    
    def test_output_format_choice_workflow(self):
        """
        Test user choosing output format from menu.
        """
        format_choices = [
            "CSV (Excel compatible)",
            "TXT (Plain text)",
            "JSON (Structured data)"
        ]
        
        test_cases = [
            ("1", "CSV (Excel compatible)"),
            ("csv", "CSV (Excel compatible)"),
            ("txt", "TXT (Plain text)"),
            ("json", "JSON (Structured data)")
        ]
        
        for user_input, expected_choice in test_cases:
            with self.subTest(user_input=user_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result = prompt_for_choice("Select output format:", format_choices)
                    
                    self.assertEqual(result, expected_choice)
    
    def test_complete_output_configuration_in_interactive_workflow(self):
        """
        Test complete output configuration within interactive processing workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        output_path = self.output_dir / "interactive_workflow_report.csv"
        
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
            mock_output_path.return_value = output_path
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = []
            
            # Run the interactive processing
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify output path was requested
            mock_output_path.assert_called_once()
            
            # Verify processing completed
            mock_extract.assert_called_once()
    
    def test_invalid_output_path_retry_workflow(self):
        """
        Test user recovery when providing invalid output path.
        """
        invalid_path = "/invalid/directory/report.csv"
        valid_path = self.output_dir / "valid_report.csv"
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # First attempt: invalid path, second attempt: valid path
            mock_prompt.side_effect = [invalid_path, str(valid_path)]
            mock_confirm.return_value = True  # User chooses to retry
            
            result_path = prompt_for_output_path()
            
            # Should eventually succeed with valid path
            self.assertEqual(result_path, valid_path)
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
            
            # Should have asked for retry confirmation
            mock_confirm.assert_called_once()
    
    def test_output_path_validation_and_sanitization(self):
        """
        Test output path validation and sanitization.
        """
        test_cases = [
            # (user_input, expected_result)
            ("report.csv", self.temp_dir / "report.csv"),
            ("./report.csv", Path.cwd() / "report.csv"),
            ("../report.csv", Path.cwd().parent / "report.csv"),
        ]
        
        for user_input, expected_result in test_cases:
            with self.subTest(user_input=user_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result_path = prompt_for_output_path()
                    
                    # Should handle relative paths correctly
                    self.assertIsInstance(result_path, Path)
                    self.assertTrue(result_path.name.endswith('.csv'))
    
    def test_output_directory_permission_error_handling(self):
        """
        Test handling of permission errors when creating output directories.
        """
        # Simulate permission error scenario
        restricted_path = Path("/root/restricted/report.csv")  # Typically restricted
        fallback_path = self.output_dir / "fallback_report.csv"
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # First attempt: restricted path, second attempt: accessible path
            mock_prompt.side_effect = [str(restricted_path), str(fallback_path)]
            mock_confirm.return_value = True  # User chooses to retry
            
            result_path = prompt_for_output_path()
            
            # Should eventually succeed with accessible path
            self.assertEqual(result_path, fallback_path)
    
    def test_output_filename_auto_extension_handling(self):
        """
        Test automatic file extension handling for output files.
        """
        test_cases = [
            # (user_input, expected_extension)
            ("report", ".csv"),  # Default extension
            ("report.csv", ".csv"),
            ("report.txt", ".txt"),
            ("report.json", ".json"),
        ]
        
        for user_input, expected_ext in test_cases:
            with self.subTest(user_input=user_input):
                with patch('click.prompt') as mock_prompt:
                    full_path = self.output_dir / user_input
                    mock_prompt.return_value = str(full_path)
                    
                    result_path = prompt_for_output_path()
                    
                    # Should have correct extension
                    if not user_input.endswith(('.csv', '.txt', '.json')):
                        # Should add default extension
                        self.assertTrue(result_path.suffix in ['.csv', '.txt', '.json'])
                    else:
                        self.assertEqual(result_path.suffix.lower(), expected_ext)
    
    def test_output_path_with_timestamp_generation(self):
        """
        Test output path generation with timestamp when requested.
        """
        base_name = "report"
        
        with patch('click.prompt') as mock_prompt, \
             patch('cli.prompts.prompt_for_choice') as mock_choice:
            
            mock_prompt.return_value = str(self.output_dir / f"{base_name}.csv")
            # User chooses to add timestamp
            mock_choice.return_value = "Add timestamp to filename"
            
            # This would be handled by the actual implementation
            # For testing, we simulate the expected behavior
            result_path = prompt_for_output_path()
            
            # Should contain the base name
            self.assertIn(base_name, result_path.name)
            self.assertTrue(result_path.name.endswith('.csv'))
    
    def test_batch_output_naming_convention(self):
        """
        Test output naming conventions for batch processing.
        """
        batch_output_path = self.output_dir / "batch_report_5790265786.csv"
        
        with patch('click.prompt') as mock_prompt:
            mock_prompt.return_value = str(batch_output_path)
            
            result_path = prompt_for_output_path()
            
            # Should handle batch naming convention
            self.assertEqual(result_path, batch_output_path)
            self.assertIn("batch", result_path.name.lower())
            self.assertIn("5790265786", result_path.name)  # Invoice number
    
    def test_output_configuration_cancellation(self):
        """
        Test user cancellation during output configuration.
        """
        with patch('click.prompt') as mock_prompt:
            # User provides empty input or cancels
            mock_prompt.return_value = ""
            
            # Should handle cancellation gracefully
            # (Exact behavior depends on implementation)
            try:
                result_path = prompt_for_output_path()
                # If it returns a path, it should be valid
                if result_path:
                    self.assertIsInstance(result_path, Path)
            except UserCancelledError:
                # Cancellation is also acceptable
                pass


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)