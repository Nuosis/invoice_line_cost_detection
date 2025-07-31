#!/usr/bin/env python3
"""
CORRECTED Line Item Parser for 5790265775_extracted_text.txt

This script fixes the critical bug in the original PDFProcessor where 'BILL' in skip patterns
was incorrectly excluding employee names like "BILL LANGFORD".
"""

import re
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LineItem:
    """Represents a single line item from an invoice with validation results."""
    wearer_number: Optional[str] = None
    wearer_name: Optional[str] = None
    item_code: Optional[str] = None
    description: Optional[str] = None
    size: Optional[str] = None
    item_type: Optional[str] = None
    quantity: Optional[int] = None
    rate: Optional[Decimal] = None
    total: Optional[Decimal] = None
    line_number: Optional[int] = None
    raw_text: Optional[str] = None
    
    # Validation fields
    expected_rate: Optional[Decimal] = None
    validation_result: Optional[str] = None  # 'PASS' or 'FAIL'
    issue_type: Optional[str] = None  # 'RATE_HIGH', 'RATE_LOW', etc.
    validation_message: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if line item has minimum required data."""
        return (
            self.item_code is not None and
            self.item_code.strip() != "" and
            self.rate is not None and
            self.quantity is not None
        )
    
    def validate_with_database(self, mock_db: 'MockDatabase') -> None:
        """Validate this line item against the mock database."""
        if self.is_valid() and self.item_code:
            validation_result = mock_db.validate_rate(self.item_code, self.rate)
            self.expected_rate = mock_db.get_expected_rate(self.item_code)
            self.validation_result = validation_result['validation_result']
            self.issue_type = validation_result['issue_type']
            self.validation_message = validation_result['message']


class MockDatabase:
    """
    Mock database that returns expected rate of 0.30 for all items.
    This simulates how the actual validation system will work.
    """
    
    def __init__(self):
        """Initialize mock database with expected rate of 0.30 for all items."""
        self.expected_rate = Decimal('0.30')
        self.logger_messages = []
    
    def log(self, message: str):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] MOCK_DB: {message}"
        self.logger_messages.append(log_entry)
        print(log_entry)
    
    def get_expected_rate(self, item_code: str) -> Decimal:
        """
        Mock database lookup that returns 0.30 for all items.
        In the real system, this would query the parts database.
        """
        self.log(f"Database lookup for item '{item_code}' -> Expected rate: ${self.expected_rate}")
        return self.expected_rate
    
    def validate_rate(self, item_code: str, actual_rate: Decimal) -> Dict[str, Any]:
        """
        Validate an item's rate against the expected database rate.
        
        Returns:
            Dict with validation result details
        """
        expected_rate = self.get_expected_rate(item_code)
        
        if actual_rate == expected_rate:
            result = {
                'is_valid': True,
                'validation_result': 'PASS',
                'issue_type': None,
                'message': f"Rate matches expected: ${expected_rate}"
            }
        else:
            if actual_rate > expected_rate:
                issue_type = 'RATE_HIGH'
                message = f"Rate ${actual_rate} is higher than expected ${expected_rate}"
            else:
                issue_type = 'RATE_LOW'
                message = f"Rate ${actual_rate} is lower than expected ${expected_rate}"
            
            result = {
                'is_valid': False,
                'validation_result': 'FAIL',
                'issue_type': issue_type,
                'message': message
            }
        
        self.log(f"Validation for '{item_code}': {result['validation_result']} - {result['message']}")
        return result


class LineItemParser:
    """
    CORRECTED Line item parser that fixes the 'BILL' skip pattern bug.
    Now includes rate validation using mock database.
    """
    
    # Exact same regex patterns from PDFProcessor
    LINE_ITEM_PATTERN = re.compile(
        r'(\d+)\s+'  # Wearer number
        r'([A-Z\s\-\.]+?)\s+'  # Wearer name (non-greedy, includes hyphens and periods)
        r'([A-Z0-9]+)\s+'  # Item code
        r'(.+?)\s+'  # Description (non-greedy)
        r'([A-Z0-9X]+)\s+'  # Size (includes X for sizes like 1XLR, 2XLL)
        r'(Rent|Ruin\s+charge|PREP\s+CHARGE|Loss\s+Charge)\s+'  # Type
        r'(\d+)\s+'  # Quantity
        r'(\d+\.\d{2,3})\s+'  # Rate (2-3 decimal places)
        r'(\d+\.\d{2})'  # Total
    )
    
    # Alternative pattern for special charges (NAME EMBL CHARGE, PREP CHARGE, etc.)
    SPECIAL_CHARGE_PATTERN = re.compile(
        r'(\d+)\s+'  # Wearer number
        r'([A-Z\s\-\.]+?)\s+'  # Wearer name
        r'(NAME\s+EMBL\s+CHARGE|PREP\s+CHARGE)\s+'  # Special charge type
        r'(\d+)\s+'  # Quantity
        r'(\d+\.\d{2,3})\s+'  # Rate
        r'(\d+\.\d{2})'  # Total
    )
    
    # Pattern for non-garment items (mats, towels, etc.)
    NON_GARMENT_PATTERN = re.compile(
        r'([A-Z0-9]+)\s+'  # Item code
        r'(.+?)\s+'  # Description
        r'(Rent|X)\s+'  # Type
        r'(\d+)\s+'  # Quantity
        r'(\d+\.\d{2,3})\s+'  # Rate
        r'(\d+\.\d{2})'  # Total
    )
    
    def __init__(self, mock_db: MockDatabase = None):
        """Initialize the parser with optional mock database for validation."""
        self.logger_messages = []
        self.mock_db = mock_db or MockDatabase()
    
    def log(self, message: str):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logger_messages.append(log_entry)
        print(log_entry)
    
    def is_header_or_summary_line(self, line: str) -> bool:
        """
        CORRECTED: Check if a line is a header or summary line that should be skipped.
        
        This fixes the bug where 'BILL' was incorrectly matching employee names like 'BILL LANGFORD'.
        """
        line_upper = line.upper()
        
        # More specific patterns to avoid false positives with employee names
        skip_patterns = [
            'WEARER#', 'WEARER NAME', 'ITEM CODE', 'ITEM DESCRIPTION', 
            'SIZE', 'TYPE', 'BILL QTY', 'RATE', 'TOTAL',  # Changed 'BILL' to 'BILL QTY'
            'SUBTOTAL', 'FREIGHT', 'TAX ', 'THANK YOU', 'VISIT US', 'BILLING INQUIRIES',
            'CUSTOMER SERVICE', 'ACCOUNT NUMBER', 'INVOICE NUMBER', 'INVOICE DATE',
            'PAGE ', 'SHIP TO', 'MARKET CENTER', 'ROUTE NUMBER'
        ]
        
        # Check for exact header patterns first
        for pattern in skip_patterns:
            if pattern in line_upper:
                return True
        
        # Additional check: if line starts with header-like patterns but has no numeric data
        header_start_patterns = [
            'WEARER', 'ITEM', 'DESCRIPTION', 'SIZE', 'TYPE'
        ]
        
        # Only skip if it's clearly a header line (not a data line with employee names)
        words = line_upper.split()
        if len(words) > 0:
            # Skip if first word is a header pattern and line doesn't look like data
            if words[0] in header_start_patterns and not any(char.isdigit() for char in line):
                return True
        
        return False
    
    def parse_line_item(self, line: str, line_num: int) -> Optional[LineItem]:
        """
        Parse a single line item using multiple patterns.
        
        Args:
            line: Line text to parse
            line_num: Line number for debugging
            
        Returns:
            LineItem object if parsing successful, None otherwise
        """
        # Try primary line item pattern first
        match = self.LINE_ITEM_PATTERN.search(line)
        if match:
            try:
                wearer_number = match.group(1)
                wearer_name = match.group(2).strip()
                item_code = match.group(3)
                description = match.group(4).strip()
                size = match.group(5)
                item_type = match.group(6)
                quantity = int(match.group(7))
                rate = Decimal(match.group(8))
                total = Decimal(match.group(9))
                
                return LineItem(
                    wearer_number=wearer_number,
                    wearer_name=wearer_name,
                    item_code=item_code,
                    description=description,
                    size=size,
                    item_type=item_type,
                    quantity=quantity,
                    rate=rate,
                    total=total,
                    line_number=line_num,
                    raw_text=line
                )
            except (ValueError, InvalidOperation) as e:
                self.log(f"Error parsing primary pattern at line {line_num}: {e}")
        
        # Try special charge pattern
        match = self.SPECIAL_CHARGE_PATTERN.search(line)
        if match:
            try:
                wearer_number = match.group(1)
                wearer_name = match.group(2).strip()
                charge_type = match.group(3)
                quantity = int(match.group(4))
                rate = Decimal(match.group(5))
                total = Decimal(match.group(6))
                
                return LineItem(
                    wearer_number=wearer_number,
                    wearer_name=wearer_name,
                    item_code=charge_type.replace(' ', '_'),  # Convert to code format
                    description=charge_type,
                    size="N/A",
                    item_type="Charge",
                    quantity=quantity,
                    rate=rate,
                    total=total,
                    line_number=line_num,
                    raw_text=line
                )
            except (ValueError, InvalidOperation) as e:
                self.log(f"Error parsing special charge at line {line_num}: {e}")
        
        # Try non-garment pattern
        match = self.NON_GARMENT_PATTERN.search(line)
        if match:
            try:
                item_code = match.group(1)
                description = match.group(2).strip()
                item_type = match.group(3)
                quantity = int(match.group(4))
                rate = Decimal(match.group(5))
                total = Decimal(match.group(6))
                
                return LineItem(
                    wearer_number="N/A",
                    wearer_name="NON-GARMENT",
                    item_code=item_code,
                    description=description,
                    size="N/A",
                    item_type=item_type,
                    quantity=quantity,
                    rate=rate,
                    total=total,
                    line_number=line_num,
                    raw_text=line
                )
            except (ValueError, InvalidOperation) as e:
                self.log(f"Error parsing non-garment item at line {line_num}: {e}")
        
        return None
    
    def extract_line_items(self, text: str) -> List[LineItem]:
        """
        Extract line items from invoice text using multiple patterns.
        
        Args:
            text: Extracted text from PDF
            
        Returns:
            List of LineItem objects
        """
        line_items = []
        lines = text.split('\n')
        
        self.log(f"Processing {len(lines)} lines of text")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines and summary lines (CORRECTED LOGIC)
            if self.is_header_or_summary_line(line):
                continue
            
            line_item = self.parse_line_item(line, line_num)
            if line_item:
                line_items.append(line_item)
                self.log(f"Parsed line {line_num}: {line_item.item_code} - {line_item.description}")
        
        self.log(f"Extracted {len(line_items)} line items")
        return line_items


def main():
    """Main function to parse line items from the extracted text file."""
    print("=" * 80)
    print("CORRECTED LINE ITEM PARSER FOR 5790265775_extracted_text.txt")
    print("FIXES BUG: 'BILL' pattern incorrectly excluding employee names")
    print("=" * 80)
    
    # Read the extracted text file
    text_file_path = "5790265775_extracted_text.txt"
    
    try:
        with open(text_file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        print(f"Successfully read {len(text_content)} characters from {text_file_path}")
        
        # Initialize parser
        parser = LineItemParser()
        
        # Extract line items
        line_items = parser.extract_line_items(text_content)
        
        # Perform rate validation using mock database
        print(f"\n🔍 PERFORMING RATE VALIDATION (Mock Database: All items expected at $0.30)")
        print("=" * 80)
        
        validation_passed = 0
        validation_failed = 0
        
        for item in line_items:
            if item.is_valid():
                item.validate_with_database(parser.mock_db)
                if item.validation_result == 'PASS':
                    validation_passed += 1
                else:
                    validation_failed += 1
        
        # Generate detailed log with validation results
        log_filename = "5790265775_line_items_WITH_VALIDATION_log.txt"
        with open(log_filename, 'w', encoding='utf-8') as log_file:
            log_file.write("# CORRECTED Line Items with Rate Validation from 5790265775_extracted_text.txt\n")
            log_file.write(f"# BUG FIX: Changed 'BILL' to 'BILL QTY' in skip patterns\n")
            log_file.write(f"# This fixes the issue where BILL LANGFORD and BILLY HEARON were excluded\n")
            log_file.write(f"# VALIDATION: Mock database expects all items to have rate $0.30\n")
            log_file.write(f"# Extraction timestamp: {datetime.now().isoformat()}\n")
            log_file.write(f"# Total line items found: {len(line_items)}\n")
            log_file.write(f"# Validation results: {validation_passed} PASS, {validation_failed} FAIL\n")
            log_file.write("# " + "=" * 77 + "\n\n")
            
            # Write parsing log
            log_file.write("## PARSING LOG\n")
            for log_message in parser.logger_messages:
                log_file.write(f"{log_message}\n")
            
            # Write mock database log
            log_file.write("\n## MOCK DATABASE VALIDATION LOG\n")
            for log_message in parser.mock_db.logger_messages:
                log_file.write(f"{log_message}\n")
            
            log_file.write("\n" + "=" * 80 + "\n")
            log_file.write("## EXTRACTED LINE ITEMS WITH VALIDATION\n")
            log_file.write("=" * 80 + "\n\n")
            
            # Write detailed line items with validation
            valid_items = 0
            langford_items = 0
            hearon_items = 0
            
            for i, item in enumerate(line_items, 1):
                log_file.write(f"LINE ITEM #{i:02d}\n")
                log_file.write(f"  Wearer Number: {item.wearer_number}\n")
                log_file.write(f"  Wearer Name: {item.wearer_name}\n")
                log_file.write(f"  Item Code: {item.item_code}\n")
                log_file.write(f"  Description: {item.description}\n")
                log_file.write(f"  Size: {item.size}\n")
                log_file.write(f"  Item Type: {item.item_type}\n")
                log_file.write(f"  Quantity: {item.quantity}\n")
                log_file.write(f"  Rate: ${item.rate}\n")
                log_file.write(f"  Total: ${item.total}\n")
                log_file.write(f"  Line Number: {item.line_number}\n")
                log_file.write(f"  Is Valid: {item.is_valid()}\n")
                
                # Validation results
                if item.is_valid():
                    log_file.write(f"  Expected Rate: ${item.expected_rate}\n")
                    log_file.write(f"  Validation Result: {item.validation_result}\n")
                    log_file.write(f"  Issue Type: {item.issue_type}\n")
                    log_file.write(f"  Validation Message: {item.validation_message}\n")
                else:
                    log_file.write(f"  Expected Rate: N/A (invalid line item)\n")
                    log_file.write(f"  Validation Result: N/A\n")
                    log_file.write(f"  Issue Type: N/A\n")
                    log_file.write(f"  Validation Message: N/A\n")
                
                log_file.write(f"  Raw Text: {item.raw_text}\n")
                log_file.write("-" * 40 + "\n")
                
                if item.is_valid():
                    valid_items += 1
                
                # Count LANGFORD and HEARON items
                if item.wearer_name and 'LANGFORD' in item.wearer_name.upper():
                    langford_items += 1
                if item.wearer_name and 'HEARON' in item.wearer_name.upper():
                    hearon_items += 1
            
            # Write summary
            log_file.write("\n" + "=" * 80 + "\n")
            log_file.write("## SUMMARY\n")
            log_file.write("=" * 80 + "\n")
            log_file.write(f"Total line items extracted: {len(line_items)}\n")
            log_file.write(f"Valid line items: {valid_items}\n")
            log_file.write(f"Invalid line items: {len(line_items) - valid_items}\n")
            log_file.write(f"\n🎯 BUG FIX VERIFICATION:\n")
            log_file.write(f"BILL LANGFORD items found: {langford_items}\n")
            log_file.write(f"BILLY HEARON items found: {hearon_items}\n")
            log_file.write(f"Bug fix status: {'✓ SUCCESS' if (langford_items > 0 and hearon_items > 0) else '✗ FAILED'}\n")
            
            # Validation summary
            log_file.write(f"\n🔍 VALIDATION SUMMARY:\n")
            log_file.write(f"Expected rate (all items): $0.30\n")
            log_file.write(f"Validation PASSED: {validation_passed} items\n")
            log_file.write(f"Validation FAILED: {validation_failed} items\n")
            if (validation_passed + validation_failed) > 0:
                success_rate = (validation_passed / (validation_passed + validation_failed) * 100)
                log_file.write(f"Validation success rate: {success_rate:.1f}%\n")
            else:
                log_file.write(f"Validation success rate: N/A\n")
            
            # Group by item code
            item_codes = {}
            for item in line_items:
                if item.item_code:
                    if item.item_code not in item_codes:
                        item_codes[item.item_code] = 0
                    item_codes[item.item_code] += 1
            
            log_file.write(f"\nUnique item codes found: {len(item_codes)}\n")
            log_file.write("\nItem code frequency:\n")
            for code, count in sorted(item_codes.items()):
                log_file.write(f"  {code}: {count} occurrences\n")
        
        print(f"\n✅ CORRECTED parsing with validation completed!")
        print(f"📊 Results: {len(line_items)} total items, {sum(1 for item in line_items if item.is_valid())} valid")
        print(f"🔍 Validation results: {validation_passed} PASS, {validation_failed} FAIL")
        print(f"📄 Detailed log with validation saved to: {log_filename}")
        
        # Count LANGFORD and HEARON items
        langford_count = sum(1 for item in line_items if item.wearer_name and 'LANGFORD' in item.wearer_name.upper())
        hearon_count = sum(1 for item in line_items if item.wearer_name and 'HEARON' in item.wearer_name.upper())
        
        print(f"\n🎯 BUG FIX VERIFICATION:")
        print(f"BILL LANGFORD items found: {langford_count}")
        print(f"BILLY HEARON items found: {hearon_count}")
        print(f"Bug fix status: {'✓ SUCCESS' if (langford_count > 0 and hearon_count > 0) else '✗ FAILED'}")
        
        # Show validation summary
        if validation_failed > 0:
            print(f"\n⚠️  VALIDATION ISSUES DETECTED:")
            print(f"   {validation_failed} items have rates different from expected $0.30")
            print(f"   This demonstrates how the validation system will flag rate discrepancies")
        else:
            print(f"\n✅ ALL RATES MATCH EXPECTED VALUE ($0.30)")
        
        # Display first few items as preview
        print("\nFirst 5 line items (preview):")
        print("-" * 80)
        for i, item in enumerate(line_items[:5], 1):
            print(f"{i:2d}. {item.wearer_name} | {item.item_code} | {item.description} | Qty: {item.quantity} | Rate: ${item.rate}")
        
        if len(line_items) > 5:
            print(f"... and {len(line_items) - 5} more items (see log file for complete list)")
        
    except FileNotFoundError:
        print(f"Error: Could not find file '{text_file_path}'")
        print("Make sure you're running this script from the docs/invoices/output/ directory")
    except Exception as e:
        print(f"Error processing file: {e}")


if __name__ == "__main__":
    main()