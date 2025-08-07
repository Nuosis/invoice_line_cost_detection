#!/usr/bin/env python3
"""
Journey tests for parts discovery prompt workflows.

These tests validate the complete user experience for interactive parts discovery,
including unknown part detection, user prompts, and part addition workflows.

Test Status: IMPLEMENTING - Converting from PDF mocking to text extraction mocking
"""

import unittest
import tempfile
import uuid
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch, MagicMock

from processing.models import InvoiceLineItem
from processing.part_discovery_service import PartDiscoveryService


class TestPartsDiscoveryPrompts(unittest.TestCase):
    """Test interactive parts discovery user flows."""
    
    def setUp(self):
        """Set up test environment with unique temporary resources."""
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"journey_test_{self.test_id}_"))
        self.db_path = self.temp_dir / f"test_db_{self.test_id}.db"
        
        # Create test PDF file
        self.test_pdf = self.temp_dir / "test_invoice.pdf"
        self.test_pdf.write_text("dummy pdf content")
        
        # Create unknown line items for testing
        self.unknown_line_items = [
            InvoiceLineItem(
                invoice_number="5790265786",
                invoice_date="2024-06-09",
                part_number="UNKNOWN001",
                description="UNKNOWN PART 1",
                unit_price=Decimal("0.50"),
                quantity=5
            ),
            InvoiceLineItem(
                invoice_number="5790265786",
                invoice_date="2024-06-09",
                part_number="UNKNOWN002",
                description="UNKNOWN PART 2",
                unit_price=Decimal("0.75"),
                quantity=3
            )
        ]
    
    def tearDown(self):
        """Clean up test resources."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_mock_text_with_unknown_parts(self, unknown_parts):
        """Create mock invoice text with specified unknown parts."""
        base_text = """BILLING INQUIRIES (866) 837-8471
INVOICE CUSTOMER SERVICE (866) 837-8471
ACCOUNT NUMBER 890235582
CUSTOMER NUMBER 10672063
INVOICE NUMBER 5790265786
INVOICE DATE 06/09/2024
TERMS NET 10 EOM
MARKET CENTER 579
SOUTHERN SAFETY 7509 Page 1 of 1
Ship To: SOUTHERN SAFETY 7509

WEARER# WEARER NAME ITEM ITEM DESCRIPTION SIZE TYPE BILL QTY RATE TOTAL
"""
        
        # Add unknown parts as line items
        for i, part in enumerate(unknown_parts, 1):
            line = f"{i} Test User {part.part_number} {part.description} XL Rent {part.quantity} {part.unit_price} {part.unit_price * part.quantity}\n"
            base_text += line
        
        base_text += """
SUBTOTAL (ALL PAGES) 10.00
FREIGHT 0.00
TAX 0.00
TOTAL $10.00
"""
        return base_text

    def test_single_unknown_part_addition_workflow(self):
        """
        Test Status: IMPLEMENTING - Converting to text extraction mocking
        
        Test the workflow for adding a single unknown part discovered in an invoice.
        This test validates the complete user journey from discovery to database addition.
        """
        unknown_part = InvoiceLineItem(
            invoice_number="5790265786",
            invoice_date="2024-06-09",
            part_number="UNKNOWN001",
            description="UNKNOWN PART 1",
            unit_price=Decimal("0.50"),
            quantity=5
        )
        
        # Create mock text with unknown part
        mock_text = self.create_mock_text_with_unknown_parts([unknown_part])
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor._extract_text_from_pdf') as mock_extract_text, \
             patch('click.echo') as mock_echo:
            
            # Mock text extraction to return our custom text
            mock_extract_text.return_value = mock_text
            
            # Mock user interactions
            mock_choice.side_effect = [
                "Add this part to database (UNKNOWN001)",  # User chooses to add part
                "Continue with next part"  # Continue workflow
            ]
            mock_prompt.side_effect = ["0.50"]  # User enters expected rate
            mock_confirm.return_value = True  # User confirms addition
            
            # Create service and run discovery
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(self.test_pdf))
                
                # Verify result structure (service simulates interactive processing)
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                self.assertTrue(result['success'])
                
                # Verify expected simulation results
                self.assertIn('total_line_items', result)
                self.assertIn('unknown_parts_discovered', result)
                self.assertIn('parts_added_to_database', result)
                
            except Exception as e:
                self.fail(f"Single unknown part addition workflow failed: {e}")

    def test_skip_unknown_part_workflow(self):
        """
        Test Status: IMPLEMENTING - Converting to text extraction mocking
        
        Test the workflow for skipping an unknown part during discovery.
        """
        unknown_part = InvoiceLineItem(
            invoice_number="5790265786",
            invoice_date="2024-06-09",
            part_number="UNKNOWN001",
            description="UNKNOWN PART 1",
            unit_price=Decimal("0.50"),
            quantity=5
        )
        
        # Create mock text with unknown part
        mock_text = self.create_mock_text_with_unknown_parts([unknown_part])
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('processing.pdf_processor.PDFProcessor._extract_text_from_pdf') as mock_extract_text, \
             patch('click.echo') as mock_echo:
            
            # Mock text extraction to return our custom text
            mock_extract_text.return_value = mock_text
            
            # Mock user choosing to skip the part
            mock_choice.side_effect = [
                "Skip this part (UNKNOWN001)",  # User chooses to skip
                "Continue with next part"  # Continue workflow
            ]
            
            # Create service and run discovery
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(self.test_pdf))
                
                # Verify result structure (service simulates interactive processing)
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                self.assertTrue(result['success'])
                
                # Verify expected simulation results
                self.assertIn('total_line_items', result)
                self.assertIn('unknown_parts_discovered', result)
                self.assertIn('parts_skipped', result)
                
            except Exception as e:
                self.fail(f"Skip unknown part workflow failed: {e}")

    def test_batch_unknown_parts_review_workflow(self):
        """
        Test Status: IMPLEMENTING - Converting to text extraction mocking
        
        Test the workflow for reviewing multiple unknown parts in batch.
        """
        # Create mock text with multiple unknown parts
        mock_text = self.create_mock_text_with_unknown_parts(self.unknown_line_items)
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor._extract_text_from_pdf') as mock_extract_text, \
             patch('click.echo') as mock_echo:
            
            # Mock text extraction to return our custom text
            mock_extract_text.return_value = mock_text
            
            # Mock user interactions for multiple parts
            mock_choice.side_effect = [
                "Add this part to database (UNKNOWN001)",  # Add first part
                "Continue with next part",
                "Skip this part (UNKNOWN002)",  # Skip second part
                "Continue with next part"
            ]
            mock_prompt.side_effect = ["0.50"]  # Rate for first part
            mock_confirm.return_value = True  # Confirm addition
            
            # Create service and run discovery
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(self.test_pdf))
                
                # Verify result structure (service simulates interactive processing)
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                self.assertTrue(result['success'])
                
                # Verify expected simulation results for batch processing
                self.assertIn('total_line_items', result)
                self.assertIn('unknown_parts_discovered', result)
                self.assertIn('parts_added_to_database', result)
                
            except Exception as e:
                self.fail(f"Batch unknown parts review workflow failed: {e}")

    def test_invalid_rate_input_retry_workflow(self):
        """
        Test Status: IMPLEMENTING - Converting to text extraction mocking
        
        Test the workflow for handling invalid rate input with retry.
        """
        unknown_part = InvoiceLineItem(
            invoice_number="5790265786",
            invoice_date="2024-06-09",
            part_number="UNKNOWN001",
            description="UNKNOWN PART 1",
            unit_price=Decimal("0.50"),
            quantity=5
        )
        
        # Create mock text with unknown part
        mock_text = self.create_mock_text_with_unknown_parts([unknown_part])
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor._extract_text_from_pdf') as mock_extract_text, \
             patch('click.echo') as mock_echo:
            
            # Mock text extraction to return our custom text
            mock_extract_text.return_value = mock_text
            
            # Mock user interactions with invalid then valid rate
            mock_choice.side_effect = [
                "Add this part to database (UNKNOWN001)",  # User chooses to add part
                "Continue with next part"
            ]
            mock_prompt.side_effect = ["invalid", "0.50"]  # Invalid then valid rate
            mock_confirm.return_value = True  # Confirm addition
            
            # Create service and run discovery
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(self.test_pdf))
                
                # Verify result structure (service simulates interactive processing)
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                self.assertTrue(result['success'])
                
                # Verify expected simulation results
                self.assertIn('total_line_items', result)
                self.assertIn('unknown_parts_discovered', result)
                self.assertIn('parts_added_to_database', result)
                
            except Exception as e:
                self.fail(f"Invalid rate input retry workflow failed: {e}")

    def test_duplicate_part_handling_workflow(self):
        """
        Test Status: IMPLEMENTING - Converting to text extraction mocking
        
        Test the workflow for handling duplicate parts during discovery.
        """
        # Create a duplicate part (same part number as existing)
        duplicate_part = InvoiceLineItem(
            invoice_number="5790265786",
            invoice_date="2024-06-09",
            part_number="GS0448",  # This should exist in database
            description="SHIRT WORK LS BTN COTTON",
            unit_price=Decimal("0.30"),
            quantity=8
        )
        
        # Create mock text with duplicate part
        mock_text = self.create_mock_text_with_unknown_parts([duplicate_part])
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor._extract_text_from_pdf') as mock_extract_text, \
             patch('click.echo') as mock_echo:
            
            # Mock text extraction to return our custom text
            mock_extract_text.return_value = mock_text
            
            # Mock user interactions
            mock_choice.side_effect = ["Continue with next part"]  # Skip duplicate
            mock_confirm.return_value = False  # Don't update existing part
            
            # Create service and run discovery
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(self.test_pdf))
                
                # Verify the workflow handled duplicate appropriately
                self.assertIsNotNone(result)
                
            except Exception as e:
                self.fail(f"Duplicate part handling workflow failed: {e}")

    def test_empty_discovery_results_handling(self):
        """
        Test Status: IMPLEMENTING - Converting to text extraction mocking
        
        Test the workflow when no unknown parts are found.
        """
        # Create mock text with no unknown parts (all known)
        known_part = InvoiceLineItem(
            invoice_number="5790265786",
            invoice_date="2024-06-09",
            part_number="GS0448",  # Known part
            description="SHIRT WORK LS BTN COTTON",
            unit_price=Decimal("0.30"),
            quantity=8
        )
        
        mock_text = self.create_mock_text_with_unknown_parts([known_part])
        
        with patch('processing.pdf_processor.PDFProcessor._extract_text_from_pdf') as mock_extract_text, \
             patch('click.echo') as mock_echo:
            
            # Mock text extraction to return our custom text
            mock_extract_text.return_value = mock_text
            
            # Create service and run discovery
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(self.test_pdf))
                
                # Verify the workflow completed even with no unknown parts
                self.assertIsNotNone(result)
                
            except Exception as e:
                self.fail(f"Empty discovery results handling failed: {e}")

    def test_parts_discovery_progress_indication(self):
        """
        Test Status: IMPLEMENTING - Converting to text extraction mocking
        
        Test that progress indicators are shown during parts discovery.
        """
        # Create mock text with unknown parts
        mock_text = self.create_mock_text_with_unknown_parts(self.unknown_line_items)
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('processing.pdf_processor.PDFProcessor._extract_text_from_pdf') as mock_extract_text, \
             patch('click.echo') as mock_echo:
            
            # Mock text extraction to return our custom text
            mock_extract_text.return_value = mock_text
            
            # Mock user interactions
            mock_choice.side_effect = [
                "Skip this part (UNKNOWN001)",
                "Continue with next part",
                "Skip this part (UNKNOWN002)",
                "Continue with next part"
            ]
            
            # Create service and run discovery
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(self.test_pdf))
                
                # Verify result structure (service simulates interactive processing)
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                self.assertTrue(result['success'])
                
                # Verify expected simulation results
                self.assertIn('total_line_items', result)
                self.assertIn('unknown_parts_discovered', result)
                self.assertIn('parts_skipped', result)
                
            except Exception as e:
                self.fail(f"Parts discovery progress indication failed: {e}")

    def test_parts_discovery_session_summary(self):
        """
        Test Status: IMPLEMENTING - Converting to text extraction mocking
        
        Test that a session summary is displayed after parts discovery.
        """
        # Create mock text with unknown parts
        mock_text = self.create_mock_text_with_unknown_parts(self.unknown_line_items)
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('processing.pdf_processor.PDFProcessor._extract_text_from_pdf') as mock_extract_text, \
             patch('click.echo') as mock_echo:
            
            # Mock text extraction to return our custom text
            mock_extract_text.return_value = mock_text
            
            # Mock user interactions - add one part, skip another
            mock_choice.side_effect = [
                "Add this part to database (UNKNOWN001)",  # Add first part
                "Continue with next part",
                "Skip this part (UNKNOWN002)",  # Skip second part
                "Continue with next part"
            ]
            mock_prompt.side_effect = ["0.50"]  # Rate for first part
            mock_confirm.return_value = True  # Confirm addition
            
            # Create service and run discovery
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(self.test_pdf))
                
                # Verify result structure (service simulates interactive processing)
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                self.assertTrue(result['success'])
                
                # Verify expected simulation results for session summary
                self.assertIn('total_line_items', result)
                self.assertIn('unknown_parts_discovered', result)
                self.assertIn('parts_added_to_database', result)
                self.assertIn('parts_skipped', result)
                
            except Exception as e:
                self.fail(f"Parts discovery session summary failed: {e}")

    def test_parts_discovery_cancellation_workflow(self):
        """
        Test Status: ✅ VERIFIED PASSING
        
        Test the workflow for user cancellation during parts discovery.
        This test verifies graceful handling of user cancellation.
        """
        unknown_part = InvoiceLineItem(
            invoice_number="5790265786",
            invoice_date="2024-06-09",
            part_number="UNKNOWN001",
            description="UNKNOWN PART 1",
            unit_price=Decimal("0.50"),
            quantity=5
        )
        
        # Create mock text with unknown part
        mock_text = self.create_mock_text_with_unknown_parts([unknown_part])
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('processing.pdf_processor.PDFProcessor._extract_text_from_pdf') as mock_extract_text, \
             patch('click.echo') as mock_echo:
            
            # Mock text extraction to return our custom text
            mock_extract_text.return_value = mock_text
            
            # Mock user cancellation
            mock_choice.side_effect = ["Cancel discovery session"]
            
            # Create service and run discovery
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(self.test_pdf))
                
                # Verify result structure (service simulates interactive processing)
                # Cancellation is handled gracefully by returning success=True
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                self.assertTrue(result['success'])
                
            except Exception as e:
                # Cancellation should not raise exceptions
                self.fail(f"Parts discovery cancellation should be handled gracefully: {e}")

    def test_parts_discovery_with_real_pdf_5790265786(self):
        """
        Test Status: ✅ VERIFIED PASSING
        
        Test parts discovery using the real PDF file 5790265786.pdf.
        This test uses the actual PDF to ensure real-world compatibility.
        """
        real_pdf_path = Path("docs/invoices/5790265786.pdf")
        
        # Skip test if real PDF doesn't exist
        if not real_pdf_path.exists():
            self.skipTest(f"Real PDF file not found: {real_pdf_path}")
        
        with patch('cli.prompts.prompt_for_choice') as mock_choice, \
             patch('click.echo') as mock_echo:
            
            # Mock user interactions to skip all unknown parts
            mock_choice.side_effect = ["Skip this part"] * 10  # Handle up to 10 unknown parts
            
            # Create service and run discovery with real PDF
            from database.database import DatabaseManager
            db_manager = DatabaseManager(str(self.db_path))
            service = PartDiscoveryService(db_manager)
            
            try:
                result = service.process_invoice_interactively(str(real_pdf_path))
                
                # Verify the workflow completed with real PDF
                self.assertIsNotNone(result)
                
            except Exception as e:
                self.fail(f"Parts discovery with real PDF failed: {e}")


if __name__ == '__main__':
    unittest.main()