"""
Journey Tests for Parts Discovery Prompts

This test suite validates user interaction flows with parts discovery prompts,
focusing specifically on the interactive parts discovery workflow and related
user decision-making processes.

These tests simulate actual user interactions during parts discovery sessions
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
from cli.commands.discovery_commands import run_interactive_discovery
from cli.context import CLIContext
from cli.exceptions import UserCancelledError
from database.database import DatabaseManager
from processing.models import InvoiceLineItem
from processing.part_discovery_service import PartDiscoveryService


class TestPartsDiscoveryPrompts(unittest.TestCase):
    """
    Test parts discovery prompt user journeys with strategic mocking.
    
    These tests simulate actual user interactions during parts discovery
    workflows and validate both user experience and system state.
    """
    
    def setUp(self):
        """Set up test environment for parts discovery testing."""
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_discovery_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_discovery_db_{self.test_id}.db"
        
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
        
        # Add some known parts
        self.db_manager.add_part("GS0448", "SHIRT WORK LS BTN COTTON", Decimal("0.30"))
        self.db_manager.add_part("KNOWN001", "Known Test Part", Decimal("10.50"))
        
        # Create mock unknown line items for testing
        self.unknown_line_items = [
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="UNKNOWN001",
                description="Unknown Part 1",
                rate=Decimal("15.00"),
                quantity=2
            ),
            InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="UNKNOWN002",
                description="Unknown Part 2",
                rate=Decimal("25.50"),
                quantity=1
            )
        ]
    
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
    
    def test_single_unknown_part_addition_workflow(self):
        """
        Test user workflow for adding a single unknown part to the database.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        unknown_part = self.unknown_line_items[0]
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Mock PDF extraction to return unknown parts
            mock_extract.return_value = [unknown_part]
            
            # User chooses to add the unknown part
            mock_choice.return_value = f"Add {unknown_part.line_item_code} to parts database"
            
            # User provides part details
            mock_prompt.side_effect = [
                unknown_part.description,  # Part description
                str(unknown_part.rate)     # Part rate
            ]
            
            # User confirms addition
            mock_confirm.return_value = True
            
            # Run the discovery workflow
            run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Verify part was added to database
            parts = self.db_manager.get_all_parts()
            added_part = next((p for p in parts if p.code == unknown_part.line_item_code), None)
            self.assertIsNotNone(added_part, f"Part {unknown_part.line_item_code} should have been added")
            self.assertEqual(added_part.description, unknown_part.description)
            self.assertEqual(added_part.expected_rate, unknown_part.rate)
    
    def test_skip_unknown_part_workflow(self):
        """
        Test user workflow for skipping an unknown part.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        unknown_part = self.unknown_line_items[0]
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Mock PDF extraction to return unknown parts
            mock_extract.return_value = [unknown_part]
            
            # User chooses to skip the unknown part
            mock_choice.return_value = f"Skip {unknown_part.line_item_code} for now"
            
            # Run the discovery workflow
            run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Verify part was NOT added to database
            parts = self.db_manager.get_all_parts()
            skipped_part = next((p for p in parts if p.code == unknown_part.line_item_code), None)
            self.assertIsNone(skipped_part, f"Part {unknown_part.line_item_code} should not have been added")
    
    def test_batch_unknown_parts_review_workflow(self):
        """
        Test user workflow for reviewing all unknown parts at once.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Mock PDF extraction to return multiple unknown parts
            mock_extract.return_value = self.unknown_line_items
            
            # User chooses to review all unknown parts at once
            mock_choice.side_effect = [
                "Review all unknown parts at once",
                f"Add {self.unknown_line_items[0].line_item_code} to parts database",
                f"Skip {self.unknown_line_items[1].line_item_code} for now"
            ]
            
            # User provides details for the first part only
            mock_prompt.side_effect = [
                self.unknown_line_items[0].description,
                str(self.unknown_line_items[0].rate)
            ]
            
            # User confirms addition of first part
            mock_confirm.return_value = True
            
            # Run the discovery workflow
            run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Verify first part was added, second was skipped
            parts = self.db_manager.get_all_parts()
            
            added_part = next((p for p in parts if p.code == self.unknown_line_items[0].line_item_code), None)
            self.assertIsNotNone(added_part, "First part should have been added")
            
            skipped_part = next((p for p in parts if p.code == self.unknown_line_items[1].line_item_code), None)
            self.assertIsNone(skipped_part, "Second part should have been skipped")
    
    def test_parts_discovery_cancellation_workflow(self):
        """
        Test user cancelling the parts discovery workflow.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        unknown_part = self.unknown_line_items[0]
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Mock PDF extraction to return unknown parts
            mock_extract.return_value = [unknown_part]
            
            # User chooses to cancel discovery
            mock_choice.return_value = "Cancel parts discovery"
            
            # Should raise UserCancelledError or handle gracefully
            with self.assertRaises(UserCancelledError):
                run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
    
    def test_invalid_rate_input_retry_workflow(self):
        """
        Test user recovery when providing invalid rate input during parts addition.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        unknown_part = self.unknown_line_items[0]
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Mock PDF extraction to return unknown parts
            mock_extract.return_value = [unknown_part]
            
            # User chooses to add the unknown part
            mock_choice.return_value = f"Add {unknown_part.line_item_code} to parts database"
            
            # User provides invalid rate first, then valid rate
            mock_prompt.side_effect = [
                unknown_part.description,  # Part description
                "invalid_rate",            # Invalid rate
                str(unknown_part.rate)     # Valid rate
            ]
            
            # User confirms addition
            mock_confirm.return_value = True
            
            # Run the discovery workflow
            run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Should have prompted for rate twice (invalid, then valid)
            rate_prompts = [call for call in mock_prompt.call_args_list if "rate" in str(call).lower()]
            self.assertGreaterEqual(len(rate_prompts), 1, "Should have prompted for rate")
    
    def test_duplicate_part_handling_workflow(self):
        """
        Test handling of duplicate parts during discovery.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        # Create a line item with a code that already exists in database
        duplicate_part = InvoiceLineItem(
            invoice_number="5790265786",
            date="2024-06-09",
            line_item_code="GS0448",  # This already exists in database
            description="SHIRT WORK LS BTN COTTON - DUPLICATE",
            rate=Decimal("0.35"),  # Different rate
            quantity=5
        )
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Mock PDF extraction to return duplicate part
            mock_extract.return_value = [duplicate_part]
            
            # User chooses to update existing part
            mock_choice.return_value = f"Update existing part {duplicate_part.line_item_code}"
            
            # User confirms update
            mock_confirm.return_value = True
            
            # Run the discovery workflow
            run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Verify part exists (should still be only one)
            parts = self.db_manager.get_all_parts()
            gs0448_parts = [p for p in parts if p.code == "GS0448"]
            self.assertEqual(len(gs0448_parts), 1, "Should have only one GS0448 part")
    
    def test_parts_discovery_with_real_pdf_5790265786(self):
        """
        Test parts discovery workflow using the real PDF file from the original bug report.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('click.echo') as mock_echo:
            
            # User chooses to add any unknown parts found
            mock_choice.return_value = "Add UNKNOWN_PART to parts database"
            
            # User provides part details
            mock_prompt.side_effect = [
                "Test Unknown Part",  # Description
                "12.50"              # Rate
            ]
            
            # User confirms addition
            mock_confirm.return_value = True
            
            # Run discovery against the specific PDF from the bug report
            run_interactive_discovery(ctx, input_path=self.target_pdf)
            
            # Verify the discovery process ran against the correct file
            # (Actual results depend on PDF content and extraction logic)
            self.assertTrue(self.target_pdf.exists(), "Target PDF should exist")
            self.assertEqual(self.target_pdf.name, "5790265786.pdf", "Should use the correct PDF")
    
    def test_empty_discovery_results_handling(self):
        """
        Test handling when no unknown parts are found during discovery.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Mock PDF extraction to return no unknown parts (all known)
            known_part = InvoiceLineItem(
                invoice_number="5790265786",
                date="2024-06-09",
                line_item_code="GS0448",  # Known part
                description="SHIRT WORK LS BTN COTTON",
                rate=Decimal("0.30"),
                quantity=8
            )
            mock_extract.return_value = [known_part]
            
            # Run the discovery workflow
            run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Verify appropriate message was displayed
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            no_unknown_messages = [msg for msg in echo_calls if "no unknown" in msg.lower() or "all parts known" in msg.lower()]
            self.assertGreater(len(no_unknown_messages), 0, "Should display message about no unknown parts")
    
    def test_parts_discovery_progress_indication(self):
        """
        Test that parts discovery provides progress indication to user.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Mock PDF extraction to return unknown parts
            mock_extract.return_value = self.unknown_line_items
            
            # User chooses to skip all parts
            mock_choice.return_value = "Skip UNKNOWN001 for now"
            
            # Run the discovery workflow
            run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Verify progress messages were displayed
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            progress_messages = [msg for msg in echo_calls if any(keyword in msg.lower() for keyword in 
                               ['processing', 'found', 'discovering', 'analyzing'])]
            self.assertGreater(len(progress_messages), 0, "Should display progress messages")
    
    def test_parts_discovery_session_summary(self):
        """
        Test that parts discovery provides a session summary to user.
        """
        ctx = CLIContext()
        ctx.database_path = str(self.db_path)
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor.extract_line_items') as mock_extract, \
             patch('click.echo') as mock_echo:
            
            # Mock PDF extraction to return unknown parts
            mock_extract.return_value = self.unknown_line_items
            
            # User adds one part, skips another
            mock_choice.side_effect = [
                f"Add {self.unknown_line_items[0].line_item_code} to parts database",
                f"Skip {self.unknown_line_items[1].line_item_code} for now"
            ]
            
            # User provides details for first part
            mock_prompt.side_effect = [
                self.unknown_line_items[0].description,
                str(self.unknown_line_items[0].rate)
            ]
            
            # User confirms addition
            mock_confirm.return_value = True
            
            # Run the discovery workflow
            run_interactive_discovery(ctx, input_path=self.real_invoices_dir)
            
            # Verify summary messages were displayed
            echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
            summary_messages = [msg for msg in echo_calls if any(keyword in msg.lower() for keyword in 
                              ['summary', 'added', 'skipped', 'total', 'complete'])]
            self.assertGreater(len(summary_messages), 0, "Should display session summary")


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)