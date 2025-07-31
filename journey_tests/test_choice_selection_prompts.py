"""
Journey Tests for Choice Selection Prompts

This test suite validates user interaction flows with choice selection prompts,
focusing specifically on the `prompt_for_choice()` function and related
user decision-making workflows.

These tests simulate actual user choice selections and validate both the user
experience and the resulting system behavior.
"""

import tempfile
import unittest
import uuid
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the modules we're testing
from cli.prompts import prompt_for_choice
from cli.exceptions import UserCancelledError


class TestChoiceSelectionPrompts(unittest.TestCase):
    """
    Test choice selection prompt user journeys with strategic mocking.
    
    These tests simulate actual user choice selections through the CLI
    interface and validate both user experience and system state.
    """
    
    def setUp(self):
        """Set up test environment for choice selection testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_choice_test_{self.test_id}_"))
        
        # Use the REAL PDFs from docs/invoices/ (following the established pattern)
        self.real_invoices_dir = Path(__file__).parent.parent / "docs" / "invoices"
        self.target_pdf = self.real_invoices_dir / "5790265786.pdf"
        
        # Verify real files exist
        self.assertTrue(self.real_invoices_dir.exists(), "Real invoices directory must exist")
        self.assertTrue(self.target_pdf.exists(), f"Target PDF must exist: {self.target_pdf}")
        
        # Get all real PDF files for testing
        self.real_pdf_files = list(self.real_invoices_dir.glob("*.pdf"))
        self.assertGreater(len(self.real_pdf_files), 0, "Must have real PDF files for testing")
        
        # Track created resources for cleanup (only temp directories, not real PDFs!)
        self.created_files = []  # No fake files to clean up
        self.created_dirs = [self.temp_dir]
    
    def tearDown(self):
        """Clean up all resources created during the test."""
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
    
    def test_single_choice_selection_from_multiple_options(self):
        """
        Test user selecting a single choice from multiple options.
        """
        choices = [
            f"Process only this file ({self.target_pdf.name})",
            f"Process all {len(self.real_pdf_files)} PDF files in {self.real_invoices_dir.name}",
            "Choose a different path"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # User selects option 1 (index 0)
            mock_prompt.return_value = "1"
            
            result = prompt_for_choice("What would you like to do?", choices)
            
            # Should return the first choice
            self.assertEqual(result, choices[0])
            
            # Should have prompted once
            mock_prompt.assert_called_once()
    
    def test_choice_selection_with_numeric_input(self):
        """
        Test user providing numeric input for choice selection.
        """
        choices = [
            "Parts-based validation",
            "Threshold-based validation",
            "Skip validation"
        ]
        
        test_cases = [
            ("1", choices[0]),  # First option
            ("2", choices[1]),  # Second option
            ("3", choices[2]),  # Third option
        ]
        
        for user_input, expected_choice in test_cases:
            with self.subTest(user_input=user_input, expected=expected_choice):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result = prompt_for_choice("Select validation mode:", choices)
                    
                    self.assertEqual(result, expected_choice)
    
    def test_choice_selection_with_text_input(self):
        """
        Test user providing text input that matches choice text.
        """
        choices = [
            "CSV format",
            "TXT format", 
            "JSON format"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # User types partial match
            mock_prompt.return_value = "CSV"
            
            result = prompt_for_choice("Select output format:", choices)
            
            # Should match the CSV option
            self.assertEqual(result, "CSV format")
    
    def test_invalid_choice_retry_flow(self):
        """
        Test user recovery when providing invalid choice input.
        """
        choices = [
            "Option A",
            "Option B",
            "Option C"
        ]
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.echo') as mock_echo:
            
            # First attempt: invalid choice, second attempt: valid choice
            mock_prompt.side_effect = ["invalid", "2"]
            
            result = prompt_for_choice("Select an option:", choices)
            
            # Should eventually succeed with valid choice
            self.assertEqual(result, "Option B")
            
            # Should have prompted twice
            self.assertEqual(mock_prompt.call_count, 2)
            
            # Should have displayed error message
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            error_messages = [msg for msg in echo_calls if "invalid" in msg.lower() or "error" in msg.lower()]
            self.assertGreater(len(error_messages), 0, "Should display error message for invalid choice")
    
    def test_choice_selection_with_default_option(self):
        """
        Test choice selection when a default option is provided.
        """
        choices = [
            "Use default settings",
            "Custom configuration",
            "Advanced options"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # User presses Enter (empty input) to use default
            mock_prompt.return_value = ""
            
            result = prompt_for_choice("Configuration options:", choices, default=1)
            
            # Should return the default choice (index 1)
            self.assertEqual(result, choices[0])  # Default is 1-based, so index 0
    
    def test_batch_vs_single_file_choice_workflow_with_real_pdfs(self):
        """
        Test the specific workflow for choosing between batch and single file processing using real PDFs.
        """
        # Use the real PDF file from the original bug report
        choices = [
            f"Process only this file ({self.target_pdf.name})",
            f"Process all {len(self.real_pdf_files)} PDF files in {self.real_invoices_dir.name}",
            "Choose a different path"
        ]
        
        # Test single file selection
        with patch('click.prompt') as mock_prompt:
            mock_prompt.return_value = "1"
            
            result = prompt_for_choice("What would you like to do?", choices)
            
            self.assertEqual(result, choices[0])
            self.assertIn("Process only this file", result)
            self.assertIn(self.target_pdf.name, result)
            self.assertIn("5790265786.pdf", result)  # Specific file from bug report
        
        # Test batch processing selection
        with patch('click.prompt') as mock_prompt:
            mock_prompt.return_value = "2"
            
            result = prompt_for_choice("What would you like to do?", choices)
            
            self.assertEqual(result, choices[1])
            self.assertIn("Process all", result)
            self.assertIn(str(len(self.real_pdf_files)), result)
    
    def test_validation_mode_choice_selection(self):
        """
        Test validation mode selection choices.
        """
        choices = [
            "Parts-based validation (recommended)",
            "Threshold-based validation",
            "Both validation methods"
        ]
        
        test_scenarios = [
            ("1", "Parts-based validation (recommended)"),
            ("parts", "Parts-based validation (recommended)"),
            ("threshold", "Threshold-based validation"),
            ("both", "Both validation methods")
        ]
        
        for user_input, expected_result in test_scenarios:
            with self.subTest(user_input=user_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result = prompt_for_choice("Select validation mode:", choices)
                    
                    self.assertEqual(result, expected_result)
    
    def test_output_format_choice_selection(self):
        """
        Test output format selection choices.
        """
        choices = [
            "CSV (Excel compatible)",
            "TXT (Plain text)",
            "JSON (Structured data)"
        ]
        
        format_mappings = [
            ("1", "CSV (Excel compatible)"),
            ("csv", "CSV (Excel compatible)"),
            ("txt", "TXT (Plain text)"),
            ("json", "JSON (Structured data)")
        ]
        
        for user_input, expected_format in format_mappings:
            with self.subTest(user_input=user_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result = prompt_for_choice("Select output format:", choices)
                    
                    self.assertEqual(result, expected_format)
    
    def test_parts_discovery_action_choices(self):
        """
        Test parts discovery action selection choices.
        """
        unknown_part = "UNKNOWN_PART_001"
        choices = [
            f"Add {unknown_part} to parts database",
            f"Skip {unknown_part} for now",
            "Review all unknown parts at once",
            "Cancel parts discovery"
        ]
        
        with patch('click.prompt') as mock_prompt:
            # Test adding part to database
            mock_prompt.return_value = "1"
            
            result = prompt_for_choice(f"Unknown part found: {unknown_part}", choices)
            
            self.assertEqual(result, choices[0])
            self.assertIn("Add", result)
            self.assertIn(unknown_part, result)
    
    def test_choice_menu_display_formatting(self):
        """
        Test that choice menus are displayed with proper formatting.
        """
        choices = [
            "First option",
            "Second option with longer text",
            "Third option"
        ]
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.echo') as mock_echo:
            
            mock_prompt.return_value = "1"
            
            result = prompt_for_choice("Test menu:", choices)
            
            # Verify menu was displayed
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            
            # Should display the question
            question_displayed = any("Test menu:" in str(call) for call in echo_calls)
            self.assertTrue(question_displayed, "Should display the question")
            
            # Should display numbered options
            for i, choice in enumerate(choices, 1):
                option_displayed = any(f"{i}" in str(call) and choice in str(call) for call in echo_calls)
                self.assertTrue(option_displayed, f"Should display option {i}: {choice}")
    
    def test_case_insensitive_choice_matching(self):
        """
        Test that choice matching is case-insensitive.
        """
        choices = [
            "Process Files",
            "Skip Processing",
            "Exit Application"
        ]
        
        case_variations = [
            ("process", "Process Files"),
            ("SKIP", "Skip Processing"),
            ("Exit", "Exit Application"),
            ("exit application", "Exit Application")
        ]
        
        for user_input, expected_choice in case_variations:
            with self.subTest(user_input=user_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = user_input
                    
                    result = prompt_for_choice("What would you like to do?", choices)
                    
                    self.assertEqual(result, expected_choice)
    
    def test_partial_text_matching_in_choices(self):
        """
        Test that partial text matching works for choice selection.
        """
        choices = [
            "Generate detailed report with validation results",
            "Generate summary report only",
            "Skip report generation"
        ]
        
        partial_matches = [
            ("detailed", "Generate detailed report with validation results"),
            ("summary", "Generate summary report only"),
            ("skip", "Skip report generation")
        ]
        
        for partial_input, expected_choice in partial_matches:
            with self.subTest(partial_input=partial_input):
                with patch('click.prompt') as mock_prompt:
                    mock_prompt.return_value = partial_input
                    
                    result = prompt_for_choice("Report options:", choices)
                    
                    self.assertEqual(result, expected_choice)
    
    def test_multiple_consecutive_invalid_choices_with_eventual_success(self):
        """
        Test recovery through multiple invalid choices before success.
        """
        choices = [
            "Valid Option A",
            "Valid Option B",
            "Valid Option C"
        ]
        
        with patch('click.prompt') as mock_prompt, \
             patch('click.echo') as mock_echo:
            
            # Multiple invalid attempts, then success
            mock_prompt.side_effect = ["invalid1", "invalid2", "99", "2"]
            
            result = prompt_for_choice("Select an option:", choices)
            
            # Should eventually succeed
            self.assertEqual(result, "Valid Option B")
            
            # Should have prompted four times
            self.assertEqual(mock_prompt.call_count, 4)
            
            # Should have displayed multiple error messages
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            error_messages = [msg for msg in echo_calls if "invalid" in msg.lower()]
            self.assertGreaterEqual(len(error_messages), 3, "Should display error for each invalid choice")
    
    def test_empty_choices_list_handling(self):
        """
        Test handling of empty choices list (edge case).
        """
        with self.assertRaises(ValueError):
            prompt_for_choice("Select from empty list:", [])
    
    def test_choice_selection_with_real_pdf_names(self):
        """
        Test choice selection with real PDF file names from docs/invoices/.
        """
        # Use actual PDF filenames from the real directory
        real_pdf_names = [pdf.name for pdf in self.real_pdf_files[:3]]  # Use first 3
        choices = [f"Process {name}" for name in real_pdf_names]
        
        with patch('click.prompt') as mock_prompt:
            mock_prompt.return_value = "2"
            
            result = prompt_for_choice("Select PDF to process:", choices)
            
            self.assertEqual(result, choices[1])
            self.assertIn("Process", result)
            self.assertIn(".pdf", result)


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)