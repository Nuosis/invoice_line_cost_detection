"""
Unit tests for PDF processing functionality.
"""

import pytest
from pathlib import Path
from decimal import Decimal
from unittest.mock import Mock, patch

from processing.pdf_processor import PDFProcessor
from processing.models import InvoiceData, LineItem, FormatSection
from processing.exceptions import (
    PDFReadabilityError,
    InvoiceParsingError,
    FormatValidationError,
    DataQualityError
)


class TestPDFProcessor:
    """Test cases for PDFProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = PDFProcessor()
        self.sample_pdf_path = Path('docs/invoices/5790265775.pdf')
    
    def test_processor_initialization(self):
        """Test PDFProcessor initialization."""
        processor = PDFProcessor()
        assert processor is not None
        assert processor.logger is not None
    
    def test_validate_pdf_readability_success(self):
        """Test successful PDF readability validation."""
        if self.sample_pdf_path.exists():
            # Should not raise an exception
            self.processor._validate_pdf_readability(self.sample_pdf_path)
    
    def test_validate_pdf_readability_file_not_found(self):
        """Test PDF readability validation with non-existent file."""
        non_existent_path = Path('non_existent_file.pdf')
        
        with pytest.raises(PDFReadabilityError) as exc_info:
            self.processor._validate_pdf_readability(non_existent_path)
        
        assert "PDF file not found" in str(exc_info.value)
    
    def test_extract_with_patterns_success(self):
        """Test successful pattern extraction."""
        text = "INVOICE NUMBER 1234567890"
        patterns = [r'INVOICE\s+NUMBER\s+(\d+)']
        
        result = self.processor._extract_with_patterns(text, patterns)
        assert result == "1234567890"
    
    def test_extract_with_patterns_no_match(self):
        """Test pattern extraction with no matches."""
        text = "Some random text"
        patterns = [r'INVOICE\s+NUMBER\s+(\d+)']
        
        result = self.processor._extract_with_patterns(text, patterns)
        assert result is None
    
    def test_extract_with_patterns_multiple_patterns(self):
        """Test pattern extraction with multiple patterns."""
        text = "Invoice Number: 1234567890"
        patterns = [
            r'INVOICE\s+NUMBER\s+(\d+)',  # Won't match
            r'Invoice\s+Number:\s*(\d+)'  # Will match
        ]
        
        result = self.processor._extract_with_patterns(text, patterns)
        assert result == "1234567890"
    
    @pytest.mark.skipif(
        not Path('docs/invoices/5790265775.pdf').exists(),
        reason="Sample PDF not available"
    )
    def test_process_pdf_integration(self):
        """Integration test for complete PDF processing."""
        invoice_data = self.processor.process_pdf(self.sample_pdf_path)
        
        # Verify basic structure
        assert isinstance(invoice_data, InvoiceData)
        assert invoice_data.invoice_number == "5790265775"
        assert invoice_data.invoice_date == "07/17/2025"
        assert invoice_data.customer_number == "792516052"
        
        # Verify line items
        assert len(invoice_data.line_items) > 0
        assert len(invoice_data.get_valid_line_items()) > 0
        
        # Verify format sections
        assert len(invoice_data.format_sections) == 4
        section_types = [section.section_type for section in invoice_data.format_sections]
        assert section_types == ['SUBTOTAL', 'FREIGHT', 'TAX', 'TOTAL']
        
        # Verify amounts
        total_section = invoice_data.get_format_section('TOTAL')
        assert total_section is not None
        assert total_section.amount == Decimal('529.14')
        
        # Verify validation
        assert invoice_data.is_valid()
        assert invoice_data.validate_format_sequence()


class TestInvoiceData:
    """Test cases for InvoiceData model."""
    
    def test_invoice_data_initialization(self):
        """Test InvoiceData initialization."""
        invoice_data = InvoiceData()
        assert invoice_data.line_items == []
        assert invoice_data.format_sections == []
        assert invoice_data.extraction_timestamp is not None
    
    def test_invoice_data_validation_empty(self):
        """Test validation of empty invoice data."""
        invoice_data = InvoiceData()
        assert not invoice_data.is_valid()
    
    def test_invoice_data_validation_complete(self):
        """Test validation of complete invoice data."""
        # Create sample line item
        line_item = LineItem(
            item_code="TEST001",
            rate=Decimal('1.00')
        )
        
        # Create sample format sections
        format_sections = [
            FormatSection('SUBTOTAL', Decimal('1.00')),
            FormatSection('FREIGHT', Decimal('0.00')),
            FormatSection('TAX', Decimal('0.00')),
            FormatSection('TOTAL', Decimal('1.00'))
        ]
        
        invoice_data = InvoiceData(
            invoice_number="TEST123",
            invoice_date="01/01/2025",
            line_items=[line_item],
            format_sections=format_sections
        )
        
        assert invoice_data.is_valid()
    
    def test_get_format_section(self):
        """Test getting specific format section."""
        format_sections = [
            FormatSection('SUBTOTAL', Decimal('100.00')),
            FormatSection('FREIGHT', Decimal('10.00')),
            FormatSection('TAX', Decimal('5.00')),
            FormatSection('TOTAL', Decimal('115.00'))
        ]
        
        invoice_data = InvoiceData(format_sections=format_sections)
        
        total_section = invoice_data.get_format_section('TOTAL')
        assert total_section is not None
        assert total_section.amount == Decimal('115.00')
        
        # Test case insensitive
        subtotal_section = invoice_data.get_format_section('subtotal')
        assert subtotal_section is not None
        assert subtotal_section.amount == Decimal('100.00')
        
        # Test non-existent section
        missing_section = invoice_data.get_format_section('MISSING')
        assert missing_section is None
    
    def test_validate_format_sequence_correct(self):
        """Test format sequence validation with correct order."""
        format_sections = [
            FormatSection('SUBTOTAL', Decimal('100.00')),
            FormatSection('FREIGHT', Decimal('10.00')),
            FormatSection('TAX', Decimal('5.00')),
            FormatSection('TOTAL', Decimal('115.00'))
        ]
        
        invoice_data = InvoiceData(format_sections=format_sections)
        assert invoice_data.validate_format_sequence()
    
    def test_validate_format_sequence_incorrect(self):
        """Test format sequence validation with incorrect order."""
        format_sections = [
            FormatSection('FREIGHT', Decimal('10.00')),
            FormatSection('SUBTOTAL', Decimal('100.00')),
            FormatSection('TAX', Decimal('5.00')),
            FormatSection('TOTAL', Decimal('115.00'))
        ]
        
        invoice_data = InvoiceData(format_sections=format_sections)
        assert not invoice_data.validate_format_sequence()
    
    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        # Create sample data
        line_item = LineItem(
            item_code="TEST001",
            description="Test Item",
            rate=Decimal('1.50')
        )
        
        format_section = FormatSection('TOTAL', Decimal('3.00'))
        
        original_data = InvoiceData(
            invoice_number="TEST123",
            invoice_date="01/01/2025",
            line_items=[line_item],
            format_sections=[format_section]
        )
        
        # Convert to dict and back
        data_dict = original_data.to_dict()
        restored_data = InvoiceData.from_dict(data_dict)
        
        # Verify restoration
        assert restored_data.invoice_number == original_data.invoice_number
        assert restored_data.invoice_date == original_data.invoice_date
        assert len(restored_data.line_items) == len(original_data.line_items)
        assert len(restored_data.format_sections) == len(original_data.format_sections)


class TestLineItem:
    """Test cases for LineItem model."""
    
    def test_line_item_initialization(self):
        """Test LineItem initialization."""
        line_item = LineItem(
            item_code="TEST001",
            description="Test Item",
            rate=Decimal('1.50')
        )
        
        assert line_item.item_code == "TEST001"
        assert line_item.description == "Test Item"
        assert line_item.rate == Decimal('1.50')
    
    def test_line_item_validation_valid(self):
        """Test validation of valid line item."""
        line_item = LineItem(
            item_code="TEST001",
            description="Test Item",
            rate=Decimal('1.50')
        )
        
        assert line_item.is_valid()
    
    def test_line_item_validation_invalid(self):
        """Test validation of invalid line item."""
        # Missing required fields
        line_item = LineItem()
        assert not line_item.is_valid()
        
        # Missing description
        line_item = LineItem(item_code="TEST001", rate=Decimal('1.50'))
        assert not line_item.is_valid()

        # Missing rate
        line_item = LineItem(item_code="TEST001", description="Test Item")
        assert not line_item.is_valid()

        # Valid line item
        line_item = LineItem(item_code="TEST001", description="Test Item", rate=Decimal('1.50'))
        assert line_item.is_valid()
    
    def test_line_item_type_conversion(self):
        """Test automatic type conversion in LineItem."""
        line_item = LineItem(
            item_code="TEST001",
            rate="1.50"  # String
        )
        
        assert isinstance(line_item.rate, Decimal)
        assert line_item.rate == Decimal('1.50')


class TestFormatSection:
    """Test cases for FormatSection model."""
    
    def test_format_section_initialization(self):
        """Test FormatSection initialization."""
        section = FormatSection('TOTAL', Decimal('100.00'))
        
        assert section.section_type == 'TOTAL'
        assert section.amount == Decimal('100.00')
    
    def test_format_section_type_conversion(self):
        """Test automatic type conversion in FormatSection."""
        section = FormatSection('TOTAL', "100.50")  # String amount
        
        assert isinstance(section.amount, Decimal)
        assert section.amount == Decimal('100.50')
    
    def test_format_section_to_dict(self):
        """Test FormatSection serialization."""
        section = FormatSection('TOTAL', Decimal('100.00'))
        section_dict = section.to_dict()
        
        assert section_dict['section_type'] == 'TOTAL'
        assert section_dict['amount'] == 100.00  # Converted to float
        assert 'raw_text' in section_dict
        assert 'line_number' in section_dict


if __name__ == '__main__':
    pytest.main([__file__])