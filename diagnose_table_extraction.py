#!/usr/bin/env python3
"""
Diagnostic script to analyze table extraction issues.

This script focuses specifically on the table extraction problem where
line items are getting misaligned and wrong data is being associated
with the wrong parts.

Usage:
    python diagnose_table_extraction.py
"""

import sys
import logging
from pathlib import Path
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from processing.pdf_processor import PDFProcessor

def setup_logging():
    """Setup detailed logging for diagnosis."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def analyze_raw_table_data(pdf_path: Path):
    """Analyze the raw table data extraction."""
    print("=" * 80)
    print("ANALYZING RAW TABLE DATA EXTRACTION")
    print("=" * 80)
    
    processor = PDFProcessor()
    
    try:
        # Extract tables using camelot
        tables = processor._extract_tables(pdf_path)
        
        print(f"Found {len(tables)} tables")
        
        for table_idx, table in enumerate(tables):
            print(f"\n--- TABLE {table_idx + 1} ---")
            print(f"Rows: {len(table)}")
            print(f"Columns: {len(table[0]) if table else 0}")
            
            # Show first 10 rows of each table
            for row_idx, row in enumerate(table[:10]):
                print(f"Row {row_idx + 1:2d}: {row}")
            
            if len(table) > 10:
                print(f"... and {len(table) - 10} more rows")
            
            # Look for the specific JOSEPH HENRY lines that are problematic
            joseph_henry_rows = []
            for row_idx, row in enumerate(table):
                if any('JOSEPH HENRY' in str(cell) for cell in row):
                    joseph_henry_rows.append((row_idx, row))
            
            if joseph_henry_rows:
                print(f"\nJOSEPH HENRY rows in table {table_idx + 1}:")
                for row_idx, row in joseph_henry_rows:
                    print(f"  Row {row_idx + 1}: {row}")
        
        return tables
        
    except Exception as e:
        print(f"Error extracting tables: {e}")
        import traceback
        traceback.print_exc()
        return []

def analyze_line_item_extraction(pdf_path: Path):
    """Analyze the line item extraction process."""
    print("\n" + "=" * 80)
    print("ANALYZING LINE ITEM EXTRACTION PROCESS")
    print("=" * 80)
    
    processor = PDFProcessor()
    
    try:
        # Extract tables
        tables = processor._extract_tables(pdf_path)
        
        if not tables:
            print("No tables found!")
            return []
        
        # Process each table
        all_line_items = []
        
        for table_idx, table in enumerate(tables):
            print(f"\n--- PROCESSING TABLE {table_idx + 1} ---")
            
            # Find header row
            header_row_idx = processor._find_header_row(table)
            if header_row_idx is None:
                print(f"No header row found in table {table_idx + 1}")
                continue
            
            header_row = table[header_row_idx]
            print(f"Header row at index {header_row_idx}: {header_row}")
            
            # Map columns
            column_mapping = processor._map_table_columns(header_row)
            print(f"Column mapping: {column_mapping}")
            
            # Process data rows - focus on JOSEPH HENRY rows
            joseph_henry_line_items = []
            
            for row_idx in range(header_row_idx + 1, len(table)):
                row = table[row_idx]
                
                # Check if this row contains JOSEPH HENRY
                if any('JOSEPH HENRY' in str(cell) for cell in row):
                    print(f"\nProcessing JOSEPH HENRY row {row_idx + 1}: {row}")
                    
                    # Parse this row
                    parsed_line_items = processor._parse_table_row_to_line_item(row, column_mapping, row_idx + 1)
                    
                    for item in parsed_line_items:
                        print(f"  Parsed: code={item.item_code}, desc={item.description}, rate={item.rate}, type={item.item_type}")
                        joseph_henry_line_items.append(item)
                        all_line_items.append(item)
            
            print(f"\nJOSEPH HENRY line items from table {table_idx + 1}:")
            for i, item in enumerate(joseph_henry_line_items):
                print(f"  {i+1}. {item.item_code} - {item.description} - ${item.rate} ({item.item_type})")
        
        return all_line_items
        
    except Exception as e:
        print(f"Error in line item extraction: {e}")
        import traceback
        traceback.print_exc()
        return []

def compare_with_expected_data():
    """Compare extracted data with expected values from the invoice."""
    print("\n" + "=" * 80)
    print("EXPECTED DATA FROM INVOICE (JOSEPH HENRY SECTION)")
    print("=" * 80)
    
    expected_joseph_henry_items = [
        {
            'line': 'PREP CHARGE',
            'item_code': None,
            'description': 'PREP CHARGE',
            'rate': Decimal('1.000'),
            'quantity': 1,
            'total': Decimal('1.00'),
            'type': 'PREP CHARGE'
        },
        {
            'line': 'GOS218NVOT JACKET HIP EVIS 65/35',
            'item_code': 'GOS218NVOT',
            'description': 'JACKET HIP EVIS 65/35',
            'rate': Decimal('0.750'),
            'quantity': 2,
            'total': Decimal('1.50'),
            'type': 'Rent'
        },
        {
            'line': 'GP0171NAVY PANT WORK DURAPRES COTTON (Rent)',
            'item_code': 'GP0171NAVY',
            'description': 'PANT WORK DURAPRES COTTON',
            'rate': Decimal('0.300'),
            'quantity': 15,
            'total': Decimal('4.50'),
            'type': 'Rent'
        },
        {
            'line': 'GP0171NAVY PANT WORK DURAPRES COTTON (Ruin charge)',
            'item_code': 'GP0171NAVY',
            'description': 'PANT WORK DURAPRES COTTON',
            'rate': Decimal('17.500'),
            'quantity': 1,
            'total': Decimal('17.50'),
            'type': 'Ruin charge'
        },
        {
            'line': 'GS0448NVOT SHIRT WORK LS BTN COTTON',
            'item_code': 'GS0448NVOT',
            'description': 'SHIRT WORK LS BTN COTTON',
            'rate': Decimal('0.300'),
            'quantity': 15,
            'total': Decimal('4.50'),
            'type': 'Rent'
        },
        {
            'line': 'GS0449NVOT SHIRT WORK SS BTN COTTON',
            'item_code': 'GS0449NVOT',
            'description': 'SHIRT WORK SS BTN COTTON',
            'rate': Decimal('0.300'),
            'quantity': 15,
            'total': Decimal('4.50'),
            'type': 'Rent'
        }
    ]
    
    print("Expected JOSEPH HENRY line items:")
    for i, item in enumerate(expected_joseph_henry_items):
        print(f"  {i+1}. {item['item_code']} - {item['description']} - ${item['rate']} ({item['type']}) - Qty: {item['quantity']} - Total: ${item['total']}")
    
    return expected_joseph_henry_items

def main():
    """Main diagnostic function."""
    print("TABLE EXTRACTION DIAGNOSTIC")
    print("Analyzing invoice: docs/invoices/5790265775.pdf")
    print("Focus: JOSEPH HENRY line items data misalignment issue")
    
    # Setup logging
    setup_logging()
    
    # Define test file path
    pdf_path = Path("docs/invoices/5790265775.pdf")
    
    if not pdf_path.exists():
        print(f"Test file not found: {pdf_path}")
        return False
    
    try:
        # Step 1: Analyze raw table data
        tables = analyze_raw_table_data(pdf_path)
        
        # Step 2: Analyze line item extraction
        extracted_items = analyze_line_item_extraction(pdf_path)
        
        # Step 3: Show expected data
        expected_items = compare_with_expected_data()
        
        # Step 4: Summary and analysis
        print("\n" + "=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        print(f"Tables found: {len(tables)}")
        print(f"Line items extracted: {len(extracted_items)}")
        print(f"Expected JOSEPH HENRY items: {len(expected_items)}")
        
        # Look for the specific problematic items
        print("\nLooking for problematic items:")
        
        # Find GP0171NAVY items
        gp0171_items = [item for item in extracted_items if item.item_code == 'GP0171NAVY']
        print(f"\nGP0171NAVY items found: {len(gp0171_items)}")
        for i, item in enumerate(gp0171_items):
            print(f"  {i+1}. Rate: ${item.rate}, Type: {item.item_type}, Desc: {item.description}")
        
        # Check if we're getting the ruin charge correctly
        ruin_charge_items = [item for item in extracted_items if item.item_type and 'ruin' in item.item_type.lower()]
        print(f"\nRuin charge items found: {len(ruin_charge_items)}")
        for i, item in enumerate(ruin_charge_items):
            print(f"  {i+1}. Code: {item.item_code}, Rate: ${item.rate}, Type: {item.item_type}")
        
        # Analysis
        print("\nISSUE ANALYSIS:")
        if len(gp0171_items) >= 2:
            rent_item = next((item for item in gp0171_items if item.item_type == 'Rent'), None)
            ruin_item = next((item for item in gp0171_items if 'ruin' in (item.item_type or '').lower()), None)
            
            if rent_item and ruin_item:
                print(f"✓ Found both GP0171NAVY Rent (${rent_item.rate}) and Ruin charge (${ruin_item.rate}) items")
                if ruin_item.rate == Decimal('17.500'):
                    print("✓ Ruin charge rate is correct (17.50)")
                else:
                    print(f"✗ Ruin charge rate is wrong: got ${ruin_item.rate}, expected $17.50")
            else:
                print("✗ Missing either Rent or Ruin charge item for GP0171NAVY")
        else:
            print("✗ Not enough GP0171NAVY items found")
        
        return True
        
    except Exception as e:
        print(f"CRITICAL ERROR during diagnosis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)