#!/usr/bin/env python3
"""
Test script to validate the complete invoice processing flow.

This script tests the processing of invoice 5790265775.pdf through each step:
1. PDF text extraction
2. Table-based line item extraction  
3. Invoice metadata parsing
4. Format sections extraction
5. Data validation
6. Report generation

Usage:
    python test_invoice_processing_flow.py
"""

import sys
import logging
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from processing.pdf_processor import PDFProcessor
from processing.invoice_processor import InvoiceProcessor
from processing.validation_engine import ValidationEngine
from database.database import DatabaseManager
from cli.formatters import print_success, print_error, print_info, print_warning

def setup_logging():
    """Setup detailed logging for validation."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Enable debug logging for key components
    logging.getLogger('pdf_processor').setLevel(logging.DEBUG)
    logging.getLogger('invoice_processor').setLevel(logging.DEBUG)
    logging.getLogger('validation_engine').setLevel(logging.DEBUG)

def test_pdf_text_extraction(pdf_path: Path):
    """Test Step 1: PDF text extraction."""
    print_info("=" * 80)
    print_info("STEP 1: Testing PDF Text Extraction")
    print_info("=" * 80)
    
    try:
        processor = PDFProcessor()
        raw_text = processor._extract_text_from_pdf(pdf_path)
        
        print_success(f"✓ Text extraction successful")
        print_info(f"  - Extracted {len(raw_text)} characters")
        print_info(f"  - Text preview (first 200 chars): {raw_text[:200]}...")
        
        # Verify key invoice elements are present
        required_elements = [
            "INVOICE NUMBER",
            "5790265775", 
            "INVOICE DATE",
            "07/17/2025",
            "WEARER",
            "ITEM",
            "DESCRIPTION",
            "SUBTOTAL",
            "FREIGHT",
            "TAX",
            "TOTAL"
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in raw_text:
                missing_elements.append(element)
        
        if missing_elements:
            print_warning(f"  - Missing elements: {missing_elements}")
        else:
            print_success(f"  - All required elements found in text")
        
        return raw_text
        
    except Exception as e:
        print_error(f"✗ Text extraction failed: {e}")
        raise

def test_table_extraction(pdf_path: Path):
    """Test Step 2: Table-based line item extraction."""
    print_info("=" * 80)
    print_info("STEP 2: Testing Table-Based Line Item Extraction")
    print_info("=" * 80)
    
    try:
        processor = PDFProcessor()
        
        # Extract tables
        tables = processor._extract_tables(pdf_path)
        print_success(f"✓ Table extraction successful")
        print_info(f"  - Found {len(tables)} tables")
        
        if not tables:
            print_error("✗ No tables found - this will cause line item extraction to fail")
            return []
        
        # Extract line items from tables
        line_items = processor._extract_line_items_from_tables(tables)
        print_success(f"✓ Line item extraction successful")
        print_info(f"  - Extracted {len(line_items)} line items")
        
        # Show first few line items for verification
        print_info("  - Sample line items:")
        for i, item in enumerate(line_items[:5]):
            print_info(f"    {i+1}. Code: {item.item_code}, Desc: {item.description}, Rate: {item.rate}")
        
        if len(line_items) > 5:
            print_info(f"    ... and {len(line_items) - 5} more")
        
        return line_items
        
    except Exception as e:
        print_error(f"✗ Table extraction failed: {e}")
        raise

def test_full_pdf_processing(pdf_path: Path):
    """Test Step 3: Complete PDF processing."""
    print_info("=" * 80)
    print_info("STEP 3: Testing Complete PDF Processing")
    print_info("=" * 80)
    
    try:
        processor = PDFProcessor()
        invoice_data = processor.process_pdf(pdf_path)
        
        print_success(f"✓ Complete PDF processing successful")
        print_info(f"  - Invoice Number: {invoice_data.invoice_number}")
        print_info(f"  - Invoice Date: {invoice_data.invoice_date}")
        print_info(f"  - Customer Number: {invoice_data.customer_number}")
        print_info(f"  - Customer Name: {invoice_data.customer_name}")
        print_info(f"  - Line Items: {len(invoice_data.line_items)}")
        print_info(f"  - Format Sections: {len(invoice_data.format_sections)}")
        
        # Verify format sections
        format_types = [section.section_type for section in invoice_data.format_sections]
        expected_format_types = ['SUBTOTAL', 'FREIGHT', 'TAX', 'TOTAL']
        
        print_info(f"  - Format section types: {format_types}")
        if format_types == expected_format_types:
            print_success(f"  - Format sections in correct order")
        else:
            print_warning(f"  - Format sections order issue. Expected: {expected_format_types}")
        
        # Show format section amounts
        for section in invoice_data.format_sections:
            print_info(f"    {section.section_type}: ${section.amount}")
        
        return invoice_data
        
    except Exception as e:
        print_error(f"✗ Complete PDF processing failed: {e}")
        raise

def test_invoice_processor_flow(pdf_path: Path):
    """Test Step 4: Invoice processor workflow."""
    print_info("=" * 80)
    print_info("STEP 4: Testing Invoice Processor Workflow")
    print_info("=" * 80)
    
    try:
        # Initialize database manager (in-memory for testing)
        db_manager = DatabaseManager(":memory:")
        
        # Create invoice processor
        processor = InvoiceProcessor(db_manager)
        
        # Process single invoice
        result = processor.process_single_invoice(pdf_path)
        
        if result.success:
            print_success(f"✓ Invoice processor workflow successful")
            print_info(f"  - Invoice Number: {result.invoice_number}")
            print_info(f"  - Line Items Count: {result.line_items_count}")
            print_info(f"  - Processing Time: {result.processing_time:.2f}s")
            print_info(f"  - Unknown Parts Found: {result.unknown_parts_found}")
            print_info(f"  - Validation Errors: {result.validation_errors}")
            
            # Show validation summary if available
            if result.validation_json:
                summary = result.validation_json.get('validation_summary', {})
                print_info(f"  - Validation Summary:")
                print_info(f"    - Total Parts: {summary.get('total_parts', 0)}")
                print_info(f"    - Passed Parts: {summary.get('passed_parts', 0)}")
                print_info(f"    - Failed Parts: {summary.get('failed_parts', 0)}")
                print_info(f"    - Unknown Parts: {summary.get('unknown_parts', 0)}")
        else:
            print_error(f"✗ Invoice processor workflow failed: {result.error_message}")
            print_info(f"  - Error Type: {result.error_type}")
            print_info(f"  - Processing Time: {result.processing_time:.2f}s")
        
        return result
        
    except Exception as e:
        print_error(f"✗ Invoice processor workflow failed: {e}")
        raise

def validate_expected_data(invoice_data, expected_data):
    """Test Step 5: Validate extracted data against expected values."""
    print_info("=" * 80)
    print_info("STEP 5: Validating Extracted Data Against Expected Values")
    print_info("=" * 80)
    
    validation_passed = True
    
    # Expected data from the invoice file content
    expected = {
        'invoice_number': '5790265775',
        'invoice_date': '07/17/2025',
        'customer_number': '792516052',
        'subtotal': Decimal('529.14'),
        'freight': Decimal('0.00'),
        'tax': Decimal('0.00'),
        'total': Decimal('529.14'),
        'min_line_items': 50  # Based on the invoice content, there should be many line items
    }
    
    # Validate invoice metadata
    if invoice_data.invoice_number == expected['invoice_number']:
        print_success(f"✓ Invoice number correct: {invoice_data.invoice_number}")
    else:
        print_error(f"✗ Invoice number mismatch: got {invoice_data.invoice_number}, expected {expected['invoice_number']}")
        validation_passed = False
    
    if invoice_data.invoice_date == expected['invoice_date']:
        print_success(f"✓ Invoice date correct: {invoice_data.invoice_date}")
    else:
        print_error(f"✗ Invoice date mismatch: got {invoice_data.invoice_date}, expected {expected['invoice_date']}")
        validation_passed = False
    
    if invoice_data.customer_number == expected['customer_number']:
        print_success(f"✓ Customer number correct: {invoice_data.customer_number}")
    else:
        print_error(f"✗ Customer number mismatch: got {invoice_data.customer_number}, expected {expected['customer_number']}")
        validation_passed = False
    
    # Validate format sections
    subtotal = invoice_data.get_subtotal_amount()
    if subtotal == expected['subtotal']:
        print_success(f"✓ Subtotal correct: ${subtotal}")
    else:
        print_error(f"✗ Subtotal mismatch: got ${subtotal}, expected ${expected['subtotal']}")
        validation_passed = False
    
    freight = invoice_data.get_freight_amount()
    if freight == expected['freight']:
        print_success(f"✓ Freight correct: ${freight}")
    else:
        print_error(f"✗ Freight mismatch: got ${freight}, expected ${expected['freight']}")
        validation_passed = False
    
    tax = invoice_data.get_tax_amount()
    if tax == expected['tax']:
        print_success(f"✓ Tax correct: ${tax}")
    else:
        print_error(f"✗ Tax mismatch: got ${tax}, expected ${expected['tax']}")
        validation_passed = False
    
    total = invoice_data.get_total_amount()
    if total == expected['total']:
        print_success(f"✓ Total correct: ${total}")
    else:
        print_error(f"✗ Total mismatch: got ${total}, expected ${expected['total']}")
        validation_passed = False
    
    # Validate line items count
    line_items_count = len(invoice_data.line_items)
    if line_items_count >= expected['min_line_items']:
        print_success(f"✓ Line items count adequate: {line_items_count} (expected at least {expected['min_line_items']})")
    else:
        print_error(f"✗ Line items count too low: got {line_items_count}, expected at least {expected['min_line_items']}")
        validation_passed = False
    
    # Validate some specific line items from the invoice
    expected_items = [
        {'item_code': 'GOS218NVOT', 'description': 'JACKET HIP EVIS 65/35', 'rate': Decimal('0.75')},
        {'item_code': 'GP0171NAVY', 'description': 'PANT WORK DURAPRES COTTON', 'rate': Decimal('0.30')},
        {'item_code': 'GS0448NVOT', 'description': 'SHIRT WORK LS BTN COTTON', 'rate': Decimal('0.30')},
        {'item_code': 'GS0449NVOT', 'description': 'SHIRT WORK SS BTN COTTON', 'rate': Decimal('0.30')},
    ]
    
    found_items = 0
    for expected_item in expected_items:
        for line_item in invoice_data.line_items:
            if (line_item.item_code == expected_item['item_code'] and 
                expected_item['description'] in line_item.description and
                line_item.rate == expected_item['rate']):
                found_items += 1
                print_success(f"✓ Found expected item: {expected_item['item_code']} - {expected_item['description']} @ ${expected_item['rate']}")
                break
        else:
            print_warning(f"⚠ Expected item not found: {expected_item['item_code']} - {expected_item['description']} @ ${expected_item['rate']}")
    
    if found_items >= len(expected_items) // 2:  # At least half should be found
        print_success(f"✓ Found {found_items}/{len(expected_items)} expected line items")
    else:
        print_error(f"✗ Only found {found_items}/{len(expected_items)} expected line items")
        validation_passed = False
    
    return validation_passed

def main():
    """Main test function."""
    print_info("INVOICE PROCESSING FLOW VALIDATION")
    print_info("Testing invoice: docs/invoices/5790265775.pdf")
    print_info("=" * 80)
    
    # Setup logging
    setup_logging()
    
    # Define test file path
    pdf_path = Path("docs/invoices/5790265775.pdf")
    
    if not pdf_path.exists():
        print_error(f"Test file not found: {pdf_path}")
        return False
    
    try:
        # Step 1: Test PDF text extraction
        raw_text = test_pdf_text_extraction(pdf_path)
        
        # Step 2: Test table extraction
        line_items = test_table_extraction(pdf_path)
        
        # Step 3: Test complete PDF processing
        invoice_data = test_full_pdf_processing(pdf_path)
        
        # Step 4: Test invoice processor workflow
        processor_result = test_invoice_processor_flow(pdf_path)
        
        # Step 5: Validate extracted data
        validation_passed = validate_expected_data(invoice_data, {})
        
        # Final summary
        print_info("=" * 80)
        print_info("VALIDATION SUMMARY")
        print_info("=" * 80)
        
        if validation_passed and processor_result.success:
            print_success("✓ ALL TESTS PASSED - Invoice processing flow is working correctly")
            print_info("The system successfully:")
            print_info("  - Extracted text from PDF")
            print_info("  - Parsed tables and line items")
            print_info("  - Extracted invoice metadata")
            print_info("  - Processed format sections")
            print_info("  - Validated data integrity")
            print_info("  - Generated validation reports")
            return True
        else:
            print_error("✗ SOME TESTS FAILED - Review the output above for details")
            return False
            
    except Exception as e:
        print_error(f"✗ CRITICAL ERROR during validation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)