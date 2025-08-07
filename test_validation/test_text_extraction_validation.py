"""
Text extraction validation tests for the Invoice Rate Detection System.

This module tests the accuracy of PDF text extraction by comparing
the output of the PDFProcessor against known good extracted text files.
"""

import unittest
import tempfile
import shutil
import uuid
from pathlib import Path
from decimal import Decimal

from processing.pdf_processor import PDFProcessor
from processing.exceptions import PDFProcessingError


class TextExtractionValidationTests(unittest.TestCase):
    """
    Test suite for validating PDF text extraction accuracy.
    
    These tests verify that the PDFProcessor correctly extracts text
    from PDF invoices by comparing against known good extracted text files.
    """
    
    def setUp(self):
        """Set up test environment with real resources."""
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"text_extraction_test_{self.test_id}_"))
        
        # Initialize PDF processor
        self.pdf_processor = PDFProcessor()
        
        # Define test invoice and expected text file
        self.test_invoice_pdf = Path("docs/invoices/5790265785.pdf")
        self.expected_text_file = Path("docs/invoices/output/5790265785_extracted_text.txt")
        
        # Skip test if required files are not available
        if not self.test_invoice_pdf.exists():
            self.skipTest(f"Required PDF file {self.test_invoice_pdf} not found")
        if not self.expected_text_file.exists():
            self.skipTest(f"Required extracted text file {self.expected_text_file} not found")
    
    def tearDown(self):
        """Clean up test resources."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Cleanup error in {self.__class__.__name__}: {e}")
    
    def test_text_extraction_basic_accuracy(self):
        """Test that PDF text extraction produces reasonable output."""
        try:
            invoice_data = self.pdf_processor.process_pdf(self.test_invoice_pdf)
            extracted_text = invoice_data.raw_text
        except PDFProcessingError as e:
            self.fail(f"PDF processing failed: {e}")
        
        # Basic sanity checks
        self.assertIsNotNone(extracted_text)
        self.assertGreater(len(extracted_text), 1000, "Extracted text should be substantial")
        
        # Check for key invoice elements
        self.assertIn("5790265785", extracted_text, "Invoice number should be present")
        self.assertIn("07/17/2025", extracted_text, "Invoice date should be present")
        self.assertIn("SOUTHERN SAFETY SUPPLY", extracted_text, "Customer name should be present")
        self.assertIn("848.52", extracted_text, "Total amount should be present")
    
    def test_text_extraction_metadata_accuracy(self):
        """Test that extracted metadata matches expected values."""
        try:
            invoice_data = self.pdf_processor.process_pdf(self.test_invoice_pdf)
        except PDFProcessingError as e:
            self.fail(f"PDF processing failed: {e}")
        
        # Verify invoice metadata
        self.assertEqual(invoice_data.invoice_number, "5790265785")
        self.assertEqual(invoice_data.invoice_date, "07/17/2025")
        self.assertEqual(invoice_data.customer_number, "792516228")
    
    def test_text_extraction_line_items_count(self):
        """Test that a reasonable number of line items are extracted."""
        try:
            invoice_data = self.pdf_processor.process_pdf(self.test_invoice_pdf)
        except PDFProcessingError as e:
            self.fail(f"PDF processing failed: {e}")
        
        line_items = invoice_data.line_items
        
        # Should extract a substantial number of line items
        self.assertGreater(len(line_items), 50, "Should extract many line items")
        self.assertLess(len(line_items), 200, "Should not extract unreasonable number")
        
        # Check that we have valid line items
        valid_items = invoice_data.get_valid_line_items()
        self.assertGreater(len(valid_items), 40, "Should have many valid line items")
    
    def test_text_extraction_format_sections(self):
        """Test that format sections are correctly extracted."""
        try:
            invoice_data = self.pdf_processor.process_pdf(self.test_invoice_pdf)
        except PDFProcessingError as e:
            self.fail(f"PDF processing failed: {e}")
        
        # Verify format sections
        self.assertEqual(len(invoice_data.format_sections), 4)
        
        section_types = [section.section_type for section in invoice_data.format_sections]
        expected_types = ['SUBTOTAL', 'FREIGHT', 'TAX', 'TOTAL']
        self.assertEqual(section_types, expected_types)
        
        # Verify specific amounts
        total_section = invoice_data.get_format_section('TOTAL')
        self.assertIsNotNone(total_section)
        self.assertEqual(total_section.amount, Decimal('848.52'))


if __name__ == '__main__':
    unittest.main()