"""
PDF Processing module for extracting and parsing invoice data.

This module provides the main PDFProcessor class that handles PDF text extraction,
invoice metadata parsing, line item extraction, and format validation.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal, InvalidOperation
from datetime import datetime

import pdfplumber

from .models import InvoiceData, LineItem, FormatSection, InvoiceLineItem
from .exceptions import (
    PDFProcessingError,
    PDFReadabilityError,
    InvoiceParsingError,
    FormatValidationError,
    DataQualityError,
    TextExtractionError,
    MetadataParsingError,
    LineItemParsingError
)


class PDFProcessor:
    """
    Main class for processing PDF invoices and extracting structured data.
    
    This class handles the complete workflow of PDF processing including:
    - PDF readability validation
    - Text extraction using pdfplumber
    - Invoice metadata parsing
    - Line item extraction and parsing
    - Format validation (SUBTOTAL, FREIGHT, TAX, TOTAL sequence)
    - Data quality validation
    """
    
    # Regex patterns for parsing different invoice components
    INVOICE_NUMBER_PATTERNS = [
        r'INVOICE\s+NUMBER\s+(\d+)',
        r'INVOICE\s*#\s*(\d+)',
        r'Invoice\s+Number:\s*(\d+)'
    ]
    
    INVOICE_DATE_PATTERNS = [
        r'INVOICE\s+DATE\s+(\d{2}/\d{2}/\d{4})',
        r'Invoice\s+Date:\s*(\d{2}/\d{2}/\d{4})',
        r'DATE\s+(\d{2}/\d{2}/\d{4})'
    ]
    
    CUSTOMER_NUMBER_PATTERNS = [
        r'CUSTOMER\s+NUMBER\s+(\d+)',
        r'Customer\s+Number:\s*(\d+)',
        r'ACCOUNT\s+NUMBER\s+(\d+)'
    ]
    
    # Line item parsing patterns based on actual invoice formats
    # Primary pattern for most line items
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
    
    # Format section patterns
    FORMAT_SECTION_PATTERNS = {
        'SUBTOTAL': [
            r'SUBTOTAL\s*\(ALL\s+PAGES\)\s+(\d+\.\d{2})',
            r'SUBTOTAL\s+(\d+\.\d{2})',
            r'Sub\s*Total\s*:?\s*\$?(\d+\.\d{2})'
        ],
        'FREIGHT': [
            r'FREIGHT\s+(\d+\.\d{2})',
            r'Freight\s*:?\s*\$?(\d+\.\d{2})',
            r'SHIPPING\s*:?\s*\$?(\d+\.\d{2})'
        ],
        'TAX': [
            r'TAX\s+(\d+\.\d{2})',
            r'Tax\s*:?\s*\$?(\d+\.\d{2})',
            r'SALES\s*TAX\s*:?\s*\$?(\d+\.\d{2})'
        ],
        'TOTAL': [
            r'TOTAL\s+\$(\d+\.\d{2})',
            r'Total\s*:?\s*\$?(\d+\.\d{2})',
            r'GRAND\s*TOTAL\s*:?\s*\$?(\d+\.\d{2})'
        ]
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize PDFProcessor.
        
        Args:
            logger: Optional logger instance. If not provided, creates a default logger.
        """
        self.logger = logger or self._create_default_logger()
        
    def _create_default_logger(self) -> logging.Logger:
        """Create a default logger for PDF processing."""
        logger = logging.getLogger('pdf_processor')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def process_pdf(self, pdf_path: Path) -> InvoiceData:
        """
        Process a PDF invoice and extract structured data.
        
        Args:
            pdf_path: Path to the PDF file to process
            
        Returns:
            InvoiceData object containing extracted invoice information
            
        Raises:
            PDFProcessingError: For various processing errors
        """
        self.logger.info(f"Starting PDF processing for: {pdf_path}")
        
        try:
            # Initialize invoice data
            invoice_data = InvoiceData(
                pdf_path=str(pdf_path),
                extraction_timestamp=datetime.now()
            )
            
            # Step 1: Validate PDF readability
            self._validate_pdf_readability(pdf_path)
            
            # Step 2: Extract text from PDF
            raw_text = self._extract_text_from_pdf(pdf_path)
            invoice_data.raw_text = raw_text
            
            # Step 3: Parse invoice metadata
            self._parse_invoice_metadata(raw_text, invoice_data)
            
            # Step 4: Extract line items
            self._extract_line_items(raw_text, invoice_data)
            
            # Step 5: Extract format sections
            self._extract_format_sections(raw_text, invoice_data)
            
            # Step 6: Validate format structure
            self._validate_format_structure(invoice_data)
            
            # Step 7: Perform data quality validation
            self._validate_data_quality(invoice_data)
            
            self.logger.info(f"Successfully processed PDF: {pdf_path}")
            self.logger.info(f"Extracted {len(invoice_data.line_items)} line items")
            
            return invoice_data
            
        except Exception as e:
            if isinstance(e, PDFProcessingError):
                raise
            else:
                self.logger.error(f"Unexpected error processing PDF {pdf_path}: {e}")
                raise PDFProcessingError(
                    f"Unexpected error during PDF processing: {str(e)}",
                    pdf_path=str(pdf_path)
                ) from e
    
    def _validate_pdf_readability(self, pdf_path: Path) -> None:
        """
        Validate that the PDF file can be read and accessed.
        
        Args:
            pdf_path: Path to the PDF file
            
        Raises:
            PDFReadabilityError: If PDF cannot be read
        """
        try:
            if not pdf_path.exists():
                raise PDFReadabilityError(
                    f"PDF file not found: {pdf_path}",
                    pdf_path=str(pdf_path)
                )
            
            if not pdf_path.is_file():
                raise PDFReadabilityError(
                    f"Path is not a file: {pdf_path}",
                    pdf_path=str(pdf_path)
                )
            
            # Try to open the PDF
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    raise PDFReadabilityError(
                        "PDF contains no pages",
                        pdf_path=str(pdf_path)
                    )
                
                # Test text extraction on first page
                first_page_text = pdf.pages[0].extract_text()
                if not first_page_text or len(first_page_text.strip()) < 10:
                    raise PDFReadabilityError(
                        "PDF appears to contain no readable text",
                        pdf_path=str(pdf_path)
                    )
                    
        except Exception as e:
            # Handle various PDF-related errors
            if "PDF" in str(type(e).__name__) or "syntax" in str(e).lower():
                raise PDFReadabilityError(
                    f"PDF syntax error: {str(e)}",
                    pdf_path=str(pdf_path),
                    original_error=e
                )
        except Exception as e:
            if isinstance(e, PDFReadabilityError):
                raise
            raise PDFReadabilityError(
                f"Error accessing PDF: {str(e)}",
                pdf_path=str(pdf_path),
                original_error=e
            )
    
    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text content from all pages of the PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Complete text content from all pages
            
        Raises:
            TextExtractionError: If text extraction fails
        """
        try:
            full_text = ""
            page_count = 0
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            full_text += page_text + "\n"
                        page_count += 1
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to extract text from page {page_num}: {e}"
                        )
                        continue
            
            if not full_text.strip():
                raise TextExtractionError(
                    "No text could be extracted from PDF",
                    pdf_path=str(pdf_path)
                )
            
            if len(full_text.strip()) < 100:
                raise TextExtractionError(
                    f"Extracted text is too short ({len(full_text)} characters), "
                    "may indicate extraction failure",
                    pdf_path=str(pdf_path)
                )
            
            self.logger.debug(f"Extracted {len(full_text)} characters from {page_count} pages")
            return full_text
            
        except Exception as e:
            if isinstance(e, TextExtractionError):
                raise
            raise TextExtractionError(
                f"Error during text extraction: {str(e)}",
                pdf_path=str(pdf_path)
            ) from e
    
    def _parse_invoice_metadata(self, text: str, invoice_data: InvoiceData) -> None:
        """
        Parse invoice metadata (number, date, customer info) from text.
        
        Args:
            text: Extracted text from PDF
            invoice_data: InvoiceData object to populate
            
        Raises:
            MetadataParsingError: If required metadata cannot be extracted
        """
        missing_fields = []
        
        # Extract invoice number
        invoice_number = self._extract_with_patterns(text, self.INVOICE_NUMBER_PATTERNS)
        if invoice_number:
            invoice_data.invoice_number = invoice_number
        else:
            missing_fields.append('invoice_number')
        
        # Extract invoice date
        invoice_date = self._extract_with_patterns(text, self.INVOICE_DATE_PATTERNS)
        if invoice_date:
            invoice_data.invoice_date = invoice_date
        else:
            missing_fields.append('invoice_date')
        
        # Extract customer number
        customer_number = self._extract_with_patterns(text, self.CUSTOMER_NUMBER_PATTERNS)
        if customer_number:
            invoice_data.customer_number = customer_number
        
        # Extract customer name (look for "Ship To:" section)
        customer_name_match = re.search(r'Ship\s+To:\s*([A-Z\s\-]+)', text)
        if customer_name_match:
            invoice_data.customer_name = customer_name_match.group(1).strip()
        
        if missing_fields:
            raise MetadataParsingError(
                f"Required metadata fields missing: {', '.join(missing_fields)}",
                pdf_path=invoice_data.pdf_path,
                missing_fields=missing_fields
            )
        
        self.logger.debug(f"Extracted metadata - Invoice: {invoice_number}, Date: {invoice_date}")
    
    def _extract_with_patterns(self, text: str, patterns: List[str]) -> Optional[str]:
        """
        Extract data using multiple regex patterns.
        
        Args:
            text: Text to search in
            patterns: List of regex patterns to try
            
        Returns:
            First successful match or None
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_line_items(self, text: str, invoice_data: InvoiceData) -> None:
        """
        Extract line items from invoice text using multiple patterns.
        
        Args:
            text: Extracted text from PDF
            invoice_data: InvoiceData object to populate
            
        Raises:
            LineItemParsingError: If line items cannot be parsed
        """
        line_items = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines and summary lines
            if self._is_header_or_summary_line(line):
                continue
            
            line_item = self._parse_line_item(line, line_num)
            if line_item:
                line_items.append(line_item)
        
        if not line_items:
            raise LineItemParsingError(
                "No valid line items found in invoice",
                pdf_path=invoice_data.pdf_path
            )
        
        invoice_data.line_items = line_items
        self.logger.debug(f"Extracted {len(line_items)} line items")
    
    def _is_header_or_summary_line(self, line: str) -> bool:
        """
        Check if a line is a header or summary line that should be skipped.
        
        FIXED: Changed 'BILL' to 'BILL QTY' to prevent false matches with employee names
        like 'BILL LANGFORD'. Also added spaces to 'TAX ' and 'PAGE ' to prevent
        false matches with names containing these substrings.
        """
        line_upper = line.upper()
        
        # More specific patterns to avoid false positives with employee names
        skip_patterns = [
            'WEARER#', 'WEARER NAME', 'ITEM CODE', 'ITEM DESCRIPTION',
            'SIZE', 'TYPE', 'BILL QTY', 'RATE', 'TOTAL',  # Changed 'BILL' to 'BILL QTY'
            'SUBTOTAL', 'FREIGHT', 'TAX ', 'THANK YOU', 'VISIT US', 'BILLING INQUIRIES',
            'CUSTOMER SERVICE', 'ACCOUNT NUMBER', 'INVOICE NUMBER', 'INVOICE DATE',
            'PAGE ', 'SHIP TO', 'MARKET CENTER', 'ROUTE NUMBER'  # Added space to 'TAX ' and 'PAGE '
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
    
    def _parse_line_item(self, line: str, line_num: int) -> Optional[LineItem]:
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
                self.logger.warning(f"Error parsing primary pattern at line {line_num}: {e}")
        
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
                self.logger.warning(f"Error parsing special charge at line {line_num}: {e}")
        
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
                self.logger.warning(f"Error parsing non-garment item at line {line_num}: {e}")
        
        return None
    
    def _extract_format_sections(self, text: str, invoice_data: InvoiceData) -> None:
        """
        Extract format sections (SUBTOTAL, FREIGHT, TAX, TOTAL) from text.
        
        Args:
            text: Extracted text from PDF
            invoice_data: InvoiceData object to populate
            
        Raises:
            FormatValidationError: If format sections cannot be found
        """
        format_sections = []
        
        for section_type, patterns in self.FORMAT_SECTION_PATTERNS.items():
            amount = self._extract_with_patterns(text, patterns)
            if amount:
                try:
                    format_section = FormatSection(
                        section_type=section_type,
                        amount=Decimal(amount)
                    )
                    format_sections.append(format_section)
                except (ValueError, InvalidOperation) as e:
                    self.logger.warning(f"Error parsing {section_type} amount '{amount}': {e}")
        
        if len(format_sections) != 4:
            found_types = [section.section_type for section in format_sections]
            raise FormatValidationError(
                f"Expected 4 format sections (SUBTOTAL, FREIGHT, TAX, TOTAL), "
                f"found {len(format_sections)}: {found_types}",
                pdf_path=invoice_data.pdf_path,
                expected_format="SUBTOTAL, FREIGHT, TAX, TOTAL",
                found_format=", ".join(found_types)
            )
        
        invoice_data.format_sections = format_sections
        self.logger.debug("Extracted all 4 format sections")
    
    def _validate_format_structure(self, invoice_data: InvoiceData) -> None:
        """
        Validate that format sections are in the correct order.
        
        Args:
            invoice_data: InvoiceData object to validate
            
        Raises:
            FormatValidationError: If format structure is invalid
        """
        if not invoice_data.validate_format_sequence():
            expected_sequence = ['SUBTOTAL', 'FREIGHT', 'TAX', 'TOTAL']
            found_sequence = [section.section_type for section in invoice_data.format_sections]
            
            raise FormatValidationError(
                f"Format sections not in correct order. "
                f"Expected: {expected_sequence}, Found: {found_sequence}",
                pdf_path=invoice_data.pdf_path,
                expected_format=" → ".join(expected_sequence),
                found_format=" → ".join(found_sequence)
            )
    
    def _validate_data_quality(self, invoice_data: InvoiceData) -> None:
        """
        Perform data quality validation on extracted data.
        
        Args:
            invoice_data: InvoiceData object to validate
            
        Raises:
            DataQualityError: If data quality issues are found
        """
        # Validate invoice number format
        if not invoice_data.invoice_number or not invoice_data.invoice_number.isdigit():
            raise DataQualityError(
                f"Invalid invoice number format: {invoice_data.invoice_number}",
                pdf_path=invoice_data.pdf_path,
                field_name="invoice_number",
                field_value=invoice_data.invoice_number,
                validation_rule="must be numeric"
            )
        
        # Validate invoice date format
        if not invoice_data.invoice_date:
            raise DataQualityError(
                "Invoice date is missing",
                pdf_path=invoice_data.pdf_path,
                field_name="invoice_date",
                validation_rule="must be present"
            )
        
        # Validate line items
        valid_line_items = invoice_data.get_valid_line_items()
        if len(valid_line_items) == 0:
            raise DataQualityError(
                "No valid line items found",
                pdf_path=invoice_data.pdf_path,
                field_name="line_items",
                validation_rule="must have at least one valid line item"
            )
        
        # Log data quality summary
        total_items = len(invoice_data.line_items)
        valid_items = len(valid_line_items)
        if valid_items < total_items:
            invoice_data.add_processing_note(
                f"Data quality: {valid_items}/{total_items} line items are valid"
            )
        
        self.logger.debug(f"Data quality validation passed: {valid_items}/{total_items} valid line items")
    
    def extract_line_items(self, pdf_path: str) -> List['InvoiceLineItem']:
        """
        Extract line items from a PDF and return them as InvoiceLineItem objects.
        
        This method is a convenience wrapper around process_pdf() that returns
        only the line items in the format expected by the validation engine.
        
        Args:
            pdf_path: Path to the PDF file to process
            
        Returns:
            List of InvoiceLineItem objects
            
        Raises:
            PDFProcessingError: For various processing errors
        """
        from .models import InvoiceLineItem
        
        # Process the PDF to get full invoice data
        invoice_data = self.process_pdf(Path(pdf_path))
        
        # Convert LineItem objects to InvoiceLineItem objects
        invoice_line_items = []
        for line_item in invoice_data.line_items:
            invoice_line_item = InvoiceLineItem.from_line_item(
                line_item,
                invoice_number=invoice_data.invoice_number,
                invoice_date=invoice_data.invoice_date
            )
            invoice_line_items.append(invoice_line_item)
        
        return invoice_line_items
    
    def process_pdf_with_error_handling(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a PDF with comprehensive error handling and recovery.
        
        This method wraps the standard process_pdf method with additional
        error handling to provide detailed error information for e2e testing.
        
        Args:
            pdf_path: Path to the PDF file to process
            
        Returns:
            Dict containing processing results and error information
        """
        result = {
            'success': False,
            'error': None,
            'error_type': None,
            'invoice_data': None,
            'line_items_count': 0,
            'processing_time': 0
        }
        
        import time
        start_time = time.time()
        
        try:
            # Attempt to process the PDF
            invoice_data = self.process_pdf(Path(pdf_path))
            
            # If successful, populate result
            result['success'] = True
            result['invoice_data'] = invoice_data
            result['line_items_count'] = len(invoice_data.line_items) if invoice_data.line_items else 0
            result['processing_time'] = time.time() - start_time
            
            self.logger.info(f"Successfully processed PDF: {pdf_path}")
            
        except PDFProcessingError as e:
            # Handle PDF-specific processing errors
            result['error'] = str(e)
            result['error_type'] = 'PDFProcessingError'
            result['processing_time'] = time.time() - start_time
            
            self.logger.error(f"PDF processing error for {pdf_path}: {e}")
            
        except Exception as e:
            # Handle any other unexpected errors
            result['error'] = str(e)
            result['error_type'] = type(e).__name__
            result['processing_time'] = time.time() - start_time
            
            self.logger.error(f"Unexpected error processing PDF {pdf_path}: {e}")
        
        return result