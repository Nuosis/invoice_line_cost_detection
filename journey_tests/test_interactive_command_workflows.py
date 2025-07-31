"""
Journey Tests for Interactive Command Workflows

This test suite validates complete user journeys through the interactive
CLI commands, focusing on the full workflow from command invocation to
report generation.

These tests simulate the complete user experience of running interactive
commands and validate both the user interface and the resulting system state.

IMPORTANT: Tests specifically against 5790265786.pdf - the file from the original bug report!
"""

import tempfile
import unittest
import uuid
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Import the modules we're testing
from cli.commands.invoice_commands import run_interactive_processing
from cli.context import CLIContext
from database.database import DatabaseManager
from processing.models import InvoiceLineItem, ValidationResult


class TestInteractiveCommandWorkflows(unittest.TestCase):
    """
    Test complete interactive command workflows with strategic mocking.
    
    These tests simulate actual user interactions through complete CLI
    command workflows, validating both user experience and system state.
    
    Tests specifically against 5790265786.pdf - the file from the original bug!
    """
    
    def setUp(self):
        """Set up test environment for interactive command testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_interactive_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_interactive_db_{self.test_id}.db"
        
        # Use the SPECIFIC PDF file from the original bug report
        self.real_invoices_dir = Path(__file__).parent.parent / "docs" / "invoices"
        self.target_pdf = self.real_invoices_dir / "5790265786.pdf"
        
        # Verify the target PDF exists
        self.assertTrue(self.real_invoices_dir.exists(), "Real invoices directory must exist")
        self.assertTrue(self.target_pdf.exists(), f"Target PDF must exist: {self.target_pdf}")
        
        # Get all real PDF files for batch testing
        self.all_pdf_files = list(self.real_invoices_dir.glob("*.pdf"))
        self.assertGreater(len(self.all_pdf_files), 0, "Must have real PDF files for testing")
        
        # Create output directory
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()
        
        # Track created resources for cleanup (only temp files, not real PDFs!)
        self.created_files = []  # No fake PDFs to clean up
        self.created_dirs = [self.temp_dir, self.output_dir]
        
        # Initialize database with test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self.db_manager.initialize_database()
        
        # Add some test parts to the database (including GS0448 from the original error)
        self.db_manager.add_part("GS0448", "SHIRT WORK LS BTN COTTON", Decimal("0.30"))
        self.db_manager.add_part("TEST001", "Test Part 1", Decimal("10.50"))
        self.db_manager.add_part("TEST002", "Test Part 2", Decimal("25.75"))
    
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
    
    def test_complete_single_file_interactive_workflow_5790265786(self):
        """
        Test complete interactive workflow for single file processing using 5790265786.pdf.
        
        This simulates the exact user journey that caused the original PathWithMetadata bug!
        """
        # Create CLI context
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Mock realistic line items that might be extracted from invoice 5790265786
        mock_line_items = [
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="GS0448",
                description="SHIRT WORK LS BTN COTTON",
                rate=Decimal("0.345"),  # Slightly higher than expected rate (0.30)
                quantity=8
            ),
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="UNKNOWN001",
                description="Unknown Part from Invoice",
                rate=Decimal("15.00"),
                quantity=2
            )
        ]
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Set up user input simulation using the EXACT PDF from the bug report
            from cli.prompts import PathWithMetadata
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir, 
                single_file_mode=True, 
                original_file=self.target_pdf
            )
            
            mock_output_path.return_value = self.output_dir / "5790265786_report.csv"
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = mock_line_items
            
            # Run the interactive processing - this would have failed with the original bug!
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify user prompts were called
            mock_input_path.assert_called_once()
            mock_output_path.assert_called_once()
            mock_validation_mode.assert_called_once()
            
            # Verify processing occurred with the specific PDF
            mock_extract.assert_called_once()
            
            # Verify the exact PDF file (5790265786.pdf) was used in processing
            extract_call_args = mock_extract.call_args
            self.assertIn("5790265786.pdf", str(extract_call_args))
            
            # Verify output was generated (check echo calls for success messages)
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            success_messages = [msg for msg in echo_calls if "success" in msg.lower() or "complete" in msg.lower()]
            self.assertGreater(len(success_messages), 0, "Should have success messages")
    
    def test_pathwithmetadata_bug_reproduction_5790265786(self):
        """
        Test that reproduces the exact PathWithMetadata bug scenario with 5790265786.pdf.
        
        This test specifically validates that the AttributeError bug is fixed.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Mock line items from the specific invoice
        mock_line_items = [
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="GS0448",
                description="SHIRT WORK LS BTN COTTON",
                rate=Decimal("0.345"),
                quantity=8
            )
        ]
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # Create PathWithMetadata exactly as it would be created in the bug scenario
            from cli.prompts import PathWithMetadata
            path_with_metadata = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            
            mock_input_path.return_value = path_with_metadata
            mock_output_path.return_value = self.output_dir / "bug_reproduction_report.csv"
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = mock_line_items
            
            # Test the specific attributes that were causing the AttributeError
            # These operations would have failed with the original bug
            self.assertTrue(hasattr(path_with_metadata, '_single_file_mode'))
            self.assertTrue(hasattr(path_with_metadata, '_original_file'))
            self.assertTrue(hasattr(path_with_metadata, '_pdf_files_override'))
            
            # Test setting attributes (this was failing in the original bug)
            path_with_metadata._single_file_mode = True
            self.assertTrue(path_with_metadata._single_file_mode)
            
            path_with_metadata._original_file = self.target_pdf
            self.assertEqual(path_with_metadata._original_file, self.target_pdf)
            
            path_with_metadata._pdf_files_override = [self.target_pdf]
            self.assertEqual(path_with_metadata._pdf_files_override, [self.target_pdf])
            
            # Verify Path delegation still works
            self.assertTrue(path_with_metadata.exists())
            self.assertTrue(path_with_metadata.is_dir())
            self.assertEqual(str(path_with_metadata), str(self.real_invoices_dir))
            
            # Run the processing to ensure no AttributeError occurs
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify processing completed successfully
            mock_extract.assert_called_once()
    
    def test_batch_processing_with_5790265786_in_directory(self):
        """
        Test batch processing workflow when 5790265786.pdf is in the directory.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Mock batch processing results including our target PDF
        mock_line_items_batch = [
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="GS0448",
                description="SHIRT WORK LS BTN COTTON",
                rate=Decimal("0.345"),
                quantity=8
            ),
            InvoiceLineItem(
                invoice_number="5790265775",
                date="2024-06-08",
                line_item_code="TEST001",
                description="Test Part 1",
                rate=Decimal("12.00"),
                quantity=3
            )
        ]
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Set up batch processing simulation using the real invoice directory
            mock_input_path.return_value = self.real_invoices_dir  # Regular Path for batch
            mock_output_path.return_value = self.output_dir / "batch_with_5790265786_report.csv"
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = mock_line_items_batch
            
            # Run the interactive processing
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify all prompts were called
            mock_input_path.assert_called_once()
            mock_output_path.assert_called_once()
            mock_validation_mode.assert_called_once()
            
            # Verify batch processing occurred with directory containing 5790265786.pdf
            mock_extract.assert_called_once()
            
            # Verify the directory containing our target PDF was used
            extract_call_args = mock_extract.call_args
            self.assertIn(str(self.real_invoices_dir), str(extract_call_args))
            
            # Verify success output
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            success_messages = [msg for msg in echo_calls if "success" in msg.lower() or "complete" in msg.lower()]
            self.assertGreater(len(success_messages), 0, "Should have success messages for batch processing")
    
    def test_threshold_validation_with_5790265786(self):
        """
        Test threshold-based validation workflow with 5790265786.pdf.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Mock line items with rates that would trigger threshold validation
        mock_line_items = [
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="GS0448",
                description="SHIRT WORK LS BTN COTTON",
                rate=Decimal("0.345"),  # This should trigger threshold if set to 0.30
                quantity=8
            ),
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="HIGH_RATE_ITEM",
                description="High Rate Item",
                rate=Decimal("50.00"),  # This should definitely trigger threshold
                quantity=1
            )
        ]
        
        with patch('cli.prompts.prompt_for_input_path') as mock_input_path, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('cli.prompts.prompt_for_threshold_value') as mock_threshold, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Set up threshold validation simulation with 5790265786.pdf
            from cli.prompts import PathWithMetadata
            mock_input_path.return_value = PathWithMetadata(
                self.real_invoices_dir,
                single_file_mode=True,
                original_file=self.target_pdf
            )
            mock_output_path.return_value = self.output_dir / "5790265786_threshold_report.csv"
            mock_validation_mode.return_value = "threshold_based"
            mock_threshold.return_value = Decimal("40.00")  # Threshold value
            mock_extract.return_value = mock_line_items
            
            # Run the interactive processing
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify threshold prompt was called
            mock_threshold.assert_called_once()
            
            # Verify all other prompts were called
            mock_input_path.assert_called_once()
            mock_output_path.assert_called_once()
            mock_validation_mode.assert_called_once()
            
            # Verify 5790265786.pdf was used
            extract_call_args = mock_extract.call_args
            self.assertIn("5790265786.pdf", str(extract_call_args))
    
    def test_file_validation_5790265786_exists_and_accessible(self):
        """
        Test that 5790265786.pdf exists and is accessible for processing.
        """
        # Verify the target PDF file exists and is valid
        self.assertTrue(self.target_pdf.exists(), f"5790265786.pdf must exist: {self.target_pdf}")
        self.assertTrue(self.target_pdf.is_file(), f"5790265786.pdf must be a file: {self.target_pdf}")
        self.assertEqual(self.target_pdf.suffix.lower(), '.pdf', f"Must be a PDF file: {self.target_pdf}")
        self.assertEqual(self.target_pdf.name, '5790265786.pdf', f"Must be the correct filename: {self.target_pdf}")
        
        # Verify file is readable
        try:
            with open(self.target_pdf, 'rb') as f:
                # Read first few bytes to ensure file is accessible
                header = f.read(10)
                self.assertGreater(len(header), 0, "File should be readable")
        except Exception as e:
            self.fail(f"5790265786.pdf should be readable: {e}")
    
    def test_original_bug_scenario_exact_reproduction(self):
        """
        Test the exact scenario that caused the original AttributeError bug.
        
        This reproduces the user's exact input: providing 5790265786.pdf path
        and choosing option 1 (Process only this file).
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        mock_line_items = [
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="GS0448",
                description="SHIRT WORK LS BTN COTTON",
                rate=Decimal("0.345"),
                quantity=8
            )
        ]
        
        # Mock the exact user interaction from the bug report
        with patch('click.prompt') as mock_prompt, \
             patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('cli.prompts.prompt_for_output_path') as mock_output_path, \
             patch('cli.prompts.prompt_for_validation_mode') as mock_validation_mode, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract:
            
            # User provides the exact path from the bug report
            mock_prompt.return_value = str(self.target_pdf)
            
            # User chooses option 1 (Process only this file) - exact choice from bug report
            mock_choice.return_value = f"Process only this file ({self.target_pdf.name})"
            
            mock_output_path.return_value = self.output_dir / "exact_bug_reproduction.csv"
            mock_validation_mode.return_value = "parts_based"
            mock_extract.return_value = mock_line_items
            
            # This call would have failed with the original AttributeError bug
            # Now it should work correctly
            run_interactive_processing(ctx, preset=None, save_preset=False)
            
            # Verify the prompts were called as expected
            mock_prompt.assert_called_once()
            mock_choice.assert_called_once()
            mock_output_path.assert_called_once()
            mock_validation_mode.assert_called_once()
            mock_extract.assert_called_once()
            
            # Verify the exact PDF was processed
            extract_call_args = mock_extract.call_args
            self.assertIn("5790265786.pdf", str(extract_call_args))


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)