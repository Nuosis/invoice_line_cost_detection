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
    # Primary pattern for most line items - improved to handle color codes and mixed case names
    LINE_ITEM_PATTERN = re.compile(
        r'(\d+)\s+'  # Wearer number (1-3 digits)
        r'([A-Z][A-Za-z\s\-\.]+?)\s+'  # Wearer name (starts with capital, allows mixed case)
        r'([A-Z0-9]+(?:NAVY|NVOT|CHAR|LGOT|SCGR|BLAK|WHIT|SLVN|GREY)?)\s+'  # Item code with color suffixes
        r'(.+?)\s+'  # Description (non-greedy to avoid capturing size)
        r'([A-Z0-9X]+|X)\s+'  # Size (handles 1XLR, 2XLL, 40X28, X, etc.)
        r'(Rent|Loss\s+Charge|Ruin\s+charge|PREP\s+CHARGE|X)\s+'  # Type (added Loss Charge and X)
        r'(\d+)\s+'  # Quantity
        r'(\d+\.\d{2,3})\s+'  # Rate (2-3 decimal places)
        r'(\d+\.\d{2})'  # Total
    )
    
    # Alternative pattern for special charges (NAME EMBL CHARGE, PREP CHARGE, etc.)
    SPECIAL_CHARGE_PATTERN = re.compile(
        r'(\d+)\s+'  # Wearer number
        r'([A-Z][A-Za-z\s\-\.]+?)\s+'  # Wearer name (improved for mixed case)
        r'(NAME\s+EMBL\s+CHARGE|PREP\s+CHARGE)\s+'  # Special charge type
        r'(\d+)\s+'  # Quantity
        r'(\d+\.\d{2,3})\s+'  # Rate
        r'(\d+\.\d{2})'  # Total
    )
    
    # Pattern for non-garment items (mats, towels, etc.) - improved with color codes
    NON_GARMENT_PATTERN = re.compile(
        r'^([A-Z0-9]+(?:NAVY|NVOT|CHAR|LGOT|SCGR|BLAK|WHIT|SLVN|GREY)?)\s+'  # Item code with anchoring
        r'(.+?)\s+'  # Description
        r'(Rent|X)\s+'  # Type
        r'(\d+)\s+'  # Quantity
        r'(\d+\.\d{2,3})\s+'  # Rate
        r'(\d+\.\d{2})$'  # Total (end of line anchor)
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
        
        Uses EXCLUSIVE table extraction for line items - no fallback to text extraction.
        If table extraction fails, the method will raise an exception.
        
        Args:
            pdf_path: Path to the PDF file to process
            
        Returns:
            InvoiceData object containing extracted invoice information
            
        Raises:
            PDFProcessingError: For various processing errors
            LineItemParsingError: If table extraction fails or finds no valid line items
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
            
            # Step 2: Extract text from PDF (needed for metadata and format sections)
            raw_text = self._extract_text_from_pdf(pdf_path)
            invoice_data.raw_text = raw_text
            
            # Step 3: Parse invoice metadata
            self._parse_invoice_metadata(raw_text, invoice_data)
            
            # Step 4: Extract line items using table extraction (EXCLUSIVE - no fallback)
            self.logger.info("Attempting table-based line item extraction")
            tables = self._extract_tables(pdf_path)
            if not tables:
                raise LineItemParsingError(
                    "No tables found in PDF - table extraction is required",
                    pdf_path=str(pdf_path)
                )
            
            table_line_items = self._extract_line_items_from_tables(tables)
            if not table_line_items:
                raise LineItemParsingError(
                    "Table extraction found tables but no valid line items could be extracted",
                    pdf_path=str(pdf_path)
                )
            
            invoice_data.line_items = table_line_items
            invoice_data.add_processing_note(f"Line items extracted from {len(tables)} tables")
            self.logger.info(f"Successfully extracted {len(table_line_items)} line items from tables")
            
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
                self.logger.info(f"[H1] PDF opened successfully, found {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            page_text_length = len(page_text)
                            full_text += page_text + "\n"
                            self.logger.info(f"[H1] Page {page_num}: extracted {page_text_length} characters")
                            # Log first 200 characters of each page for verification
                            preview = page_text[:200].replace('\n', ' ').strip()
                            self.logger.info(f"[H1] Page {page_num} preview: {preview}...")
                        else:
                            self.logger.warning(f"[H1] Page {page_num}: no text extracted (empty page_text)")
                        page_count += 1
                    except Exception as e:
                        self.logger.error(f"[H1] Failed to extract text from page {page_num}: {e}")
                        continue
            
            total_length = len(full_text)
            stripped_length = len(full_text.strip())
            self.logger.info(f"[H1] Text extraction complete: {total_length} total chars, {stripped_length} after strip")
            
            if not full_text.strip():
                self.logger.error(f"[H1] CRITICAL: No text extracted from PDF - full_text is empty after strip")
                raise TextExtractionError(
                    "No text could be extracted from PDF",
                    pdf_path=str(pdf_path)
                )
            
            if len(full_text.strip()) < 100:
                self.logger.error(f"[H1] CRITICAL: Extracted text too short ({len(full_text)} characters)")
                raise TextExtractionError(
                    f"Extracted text is too short ({len(full_text)} characters), "
                    "may indicate extraction failure",
                    pdf_path=str(pdf_path)
                )
            
            self.logger.info(f"[H1] SUCCESS: Extracted {len(full_text)} characters from {page_count} pages")
            return full_text
            
        except Exception as e:
            if isinstance(e, TextExtractionError):
                self.logger.error(f"[H1] Text extraction failed with TextExtractionError: {e}")
                raise
            self.logger.error(f"[H1] Text extraction failed with unexpected error: {e}")
            raise TextExtractionError(
                f"Error during text extraction: {str(e)}",
                pdf_path=str(pdf_path)
            ) from e
    
    def _extract_tables(self, pdf_path: Path) -> List[List[List[str]]]:
        """
        Extract tables from all pages of the PDF using camelot-py.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of tables, where each table is a list of rows,
            and each row is a list of cell values
            
        Raises:
            TextExtractionError: If table extraction fails
        """

        try:
            import camelot
            import pandas as pd
            
            all_tables = []
            
            # Extract tables using camelot - try both methods and pick the best result
            lattice_tables = []
            stream_tables = []
            
            # Try lattice method first
            try:
                self.logger.info(f"[H2] Attempting camelot lattice method...")
                lattice_tables = camelot.read_pdf(str(pdf_path), flavor='lattice', pages='all')
                self.logger.info(f"[H2] Lattice method found {len(lattice_tables)} tables")
            except Exception as e:
                self.logger.error(f"[H2] Camelot lattice method failed: {e}")
            
            # Try stream method
            try:
                self.logger.info(f"[H2] Attempting camelot stream method...")
                stream_tables = camelot.read_pdf(str(pdf_path), flavor='stream', pages='all')
                self.logger.info(f"[H2] Stream method found {len(stream_tables)} tables")
            except Exception as e:
                self.logger.error(f"[H2] Camelot stream method failed: {e}")
            
            # Choose the better result based on table structure quality
            camelot_tables = self._choose_best_tables(lattice_tables, stream_tables)
            
            if not camelot_tables:
                self.logger.error("[H2] CRITICAL: Both camelot methods failed or returned no tables")
                return []
            
            self.logger.info(f"[H2] Selected {len(camelot_tables)} tables for processing")
            
            # Convert camelot tables to our format
            for table_idx, camelot_table in enumerate(camelot_tables):
                try:
                    # Get the DataFrame and convert to list of lists
                    df = camelot_table.df
                    self.logger.info(f"[H2] Processing table {table_idx + 1}: {df.shape[0]} rows x {df.shape[1]} columns")
                    
                    # Convert DataFrame to list of lists
                    table_data = []
                    for row_idx, (_, row) in enumerate(df.iterrows()):
                        # Clean up cells - strip whitespace and handle NaN values
                        cleaned_row = [
                            str(cell).strip() if pd.notna(cell) and str(cell).strip() else ""
                            for cell in row
                        ]
                        # Only add rows that have at least one non-empty cell
                        if any(cell for cell in cleaned_row):
                            table_data.append(cleaned_row)
                            if row_idx < 3:  # Log first 3 rows for verification
                                self.logger.info(f"[H2] Table {table_idx + 1} row {row_idx + 1}: {cleaned_row}")
                    
                    if table_data:  # Only add non-empty tables
                        all_tables.append(table_data)
                        self.logger.info(f"[H2] Table {table_idx + 1} processed: {len(table_data)} valid rows")
                    else:
                        self.logger.warning(f"[H2] Table {table_idx + 1} had no valid rows after cleaning")
                        
                except Exception as e:
                    self.logger.error(f"[H2] Error processing table {table_idx + 1}: {e}")
                    continue
            
            if not all_tables:
                self.logger.error("[H2] CRITICAL: No tables found in PDF after processing")
            else:
                self.logger.info(f"[H2] SUCCESS: Extracted {len(all_tables)} tables using camelot-py")
            
            return all_tables
            
        except ImportError:
            self.logger.error("[H2] CRITICAL: camelot-py not installed. Please install with: pip install camelot-py[cv]")
            return []
        except Exception as e:
            if isinstance(e, TextExtractionError):
                self.logger.error(f"[H2] Table extraction failed with TextExtractionError: {e}")
                raise
            self.logger.error(f"[H2] Table extraction failed with unexpected error: {e}")
            raise TextExtractionError(
                f"Error during table extraction with camelot: {str(e)}",
                pdf_path=str(pdf_path)
            ) from e
    
    def _choose_best_tables(self, lattice_tables, stream_tables):
        """
        Choose the better table extraction result between lattice and stream methods.
        
        Args:
            lattice_tables: Tables extracted using lattice method
            stream_tables: Tables extracted using stream method
            
        Returns:
            The better set of filtered and deduplicated tables
        """
        # If one method failed, use the other
        if not lattice_tables and stream_tables:
            self.logger.info("Using stream method results (lattice failed)")
            filtered_tables = self._filter_and_deduplicate_tables(stream_tables)
            self.logger.info(f"Filtered stream tables: {len(stream_tables)} -> {len(filtered_tables)}")
            return filtered_tables
        elif lattice_tables and not stream_tables:
            self.logger.info("Using lattice method results (stream failed)")
            filtered_tables = self._filter_and_deduplicate_tables(lattice_tables)
            self.logger.info(f"Filtered lattice tables: {len(lattice_tables)} -> {len(filtered_tables)}")
            return filtered_tables
        elif not lattice_tables and not stream_tables:
            return []
        
        # Both methods returned results, filter and compare quality
        filtered_lattice = self._filter_and_deduplicate_tables(lattice_tables)
        filtered_stream = self._filter_and_deduplicate_tables(stream_tables)
        
        lattice_score = sum(self._score_individual_table(table.df) for table in filtered_lattice)
        stream_score = sum(self._score_individual_table(table.df) for table in filtered_stream)
        
        if stream_score > lattice_score:
            self.logger.info(f"Using stream method results (score: {stream_score} vs lattice: {lattice_score})")
            self.logger.info(f"Filtered stream tables: {len(stream_tables)} -> {len(filtered_stream)}")
            return filtered_stream
        else:
            self.logger.info(f"Using lattice method results (score: {lattice_score} vs stream: {stream_score})")
            self.logger.info(f"Filtered lattice tables: {len(lattice_tables)} -> {len(filtered_lattice)}")
            return filtered_lattice
    
    def _filter_and_deduplicate_tables(self, tables):
        """
        Filter out garbage tables and deduplicate similar tables.
        
        Args:
            tables: List of camelot table objects
            
        Returns:
            List of filtered and deduplicated table objects
        """
        if not tables:
            return []
        
        # Score and filter tables
        scored_tables = []
        rejected_count = 0
        
        for table in tables:
            try:
                df = table.df
                score = self._score_individual_table(df)
                if score > 0:  # Only include tables with positive scores
                    scored_tables.append((table, score))
                else:
                    rejected_count += 1
                    self.logger.debug(f"Rejected table with score {score}")
            except Exception as e:
                rejected_count += 1
                self.logger.debug(f"Rejected table due to error: {e}")
        
        if rejected_count > 0:
            self.logger.info(f"Rejected {rejected_count} garbage/low-quality tables")
        
        # Deduplicate similar tables (keep the highest scoring version)
        deduplicated_tables = self._deduplicate_tables(scored_tables)
        
        if len(scored_tables) != len(deduplicated_tables):
            duplicate_count = len(scored_tables) - len(deduplicated_tables)
            self.logger.info(f"Removed {duplicate_count} duplicate tables")
        
        # Return just the table objects (without scores)
        return [table for table, _ in deduplicated_tables]
    
    def _score_table_quality(self, tables):
        """
        Score the quality of extracted tables based on structure and content.
        
        Args:
            tables: List of camelot table objects
            
        Returns:
            Quality score (higher is better)
        """
        if not tables:
            return 0
        
        # Filter and score tables, then deduplicate
        scored_tables = []
        for table in tables:
            try:
                df = table.df
                score = self._score_individual_table(df)
                if score > 0:  # Only include tables with positive scores
                    scored_tables.append((table, score))
            except Exception:
                continue
        
        # Deduplicate similar tables (keep the highest scoring version)
        deduplicated_tables = self._deduplicate_tables(scored_tables)
        
        # Return total score of deduplicated tables
        return sum(score for _, score in deduplicated_tables)
    
    def _score_individual_table(self, df):
        """
        Score an individual table based on structure and content quality.
        
        Args:
            df: pandas DataFrame of the table
            
        Returns:
            Quality score (0 or negative means reject table)
        """
        rows, cols = df.shape
        
        # Basic structure scoring
        col_score = min(cols * 10, 100)  # Cap at 100 points for columns
        row_score = min(rows * 2, 50)   # Cap at 50 points for rows
        
        # Heavy penalty for tables that are too narrow (likely poorly extracted)
        if cols < 3:
            col_score *= 0.1
        
        # Content-based validation
        content_score = self._score_table_content(df)
        
        # Noise detection - reject tables with too much header/footer noise
        noise_penalty = self._calculate_noise_penalty(df)
        
        # Structure bonus for reasonable dimensions
        if 5 <= cols <= 15 and 3 <= rows <= 100:
            structure_bonus = 20
        else:
            structure_bonus = 0
        
        total_score = col_score + row_score + content_score + structure_bonus - noise_penalty
        
        # Reject garbage tables (invoice headers, pure text blocks, etc.)
        if self._is_garbage_table(df):
            return -1000  # Strong negative score to reject
        
        return max(0, total_score)  # Don't return negative scores
    
    def _score_table_content(self, df):
        """
        Score table based on content patterns that indicate line item data.
        
        Args:
            df: pandas DataFrame
            
        Returns:
            Content quality score
        """
        score = 0
        
        # Look for line item indicators
        text_content = ' '.join(df.astype(str).values.flatten()).upper()
        
        # CRITICAL FIX: Strong positive indicators for line item tables
        line_item_indicators = [
            'WEARER', 'ITEM', 'DESCRIPTION', 'SIZE', 'TYPE', 'QTY', 'RATE', 'TOTAL',
            'RENT', 'BILL', 'QUANTITY', 'AMOUNT', 'PRICE'
        ]
        
        for indicator in line_item_indicators:
            if indicator in text_content:
                score += 25  # Increased from 15 to 25 for stronger weighting
        
        # CRITICAL FIX: Heavy penalty for A/R balance and summary tables
        ar_balance_indicators = [
            'A/R BALANCES', 'CURRENT', '1-30 DAYS', '31-60 DAYS', '61-90 DAYS',
            '91-120 DAYS', 'OVER 120 DAYS', 'TOTAL DUE'
        ]
        
        ar_penalty = 0
        for indicator in ar_balance_indicators:
            if indicator in text_content:
                ar_penalty += 100  # Heavy penalty for A/R balance tables
        
        score -= ar_penalty
        
        # Look for part number patterns (alphanumeric codes)
        import re
        part_pattern = r'\b[A-Z]{2,3}\d{3,4}[A-Z]*\b'  # Pattern like GS0448NAVY, GP0171NAVY
        part_matches = len(re.findall(part_pattern, text_content))
        score += min(part_matches * 10, 100)  # Increased from 5 to 10, cap increased to 100
        
        # Look for numeric data (rates, quantities, totals)
        numeric_pattern = r'\b\d+\.\d{2,3}\b'  # Decimal numbers like rates
        numeric_matches = len(re.findall(numeric_pattern, text_content))
        score += min(numeric_matches * 3, 50)  # Increased from 2 to 3, cap increased to 50
        
        # CRITICAL FIX: Bonus for tables with employee/wearer names
        name_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last name pattern
            r'\b[A-Z][A-Za-z]+ [A-Z][A-Za-z]+\b'  # Mixed case names
        ]
        
        name_matches = 0
        for pattern in name_patterns:
            name_matches += len(re.findall(pattern, text_content))
        
        if name_matches > 0:
            score += min(name_matches * 5, 50)  # Bonus for employee names
        
        return score
    
    def _calculate_noise_penalty(self, df):
        """
        Calculate penalty for noisy tables with too much header/footer content.
        
        Args:
            df: pandas DataFrame
            
        Returns:
            Noise penalty score
        """
        penalty = 0
        text_content = ' '.join(df.astype(str).values.flatten()).upper()
        
        # Noise indicators (invoice header/footer content)
        noise_indicators = [
            'BILLING INQUIRIES', 'CUSTOMER SERVICE', 'INVOICE NUMBER', 'INVOICE DATE',
            'ACCOUNT NUMBER', 'CUSTOMER NUMBER', 'PAY YOUR BILL', 'HTTP://', 'WWW.',
            'TERMS', 'NET 30', 'PO #', 'NAID', 'MARKET CENTER', 'ROUTE NUMBER',
            'PAGE', 'OF', 'SHIP TO:', 'SUITE', 'DRIVE', 'STREET', 'AVE', 'BLVD'
        ]
        
        for indicator in noise_indicators:
            if indicator in text_content:
                penalty += 25  # Heavy penalty for noise
        
        # Penalty for tables with too many empty cells
        empty_cells = df.isnull().sum().sum() + (df == '').sum().sum()
        total_cells = df.size
        if total_cells > 0:
            empty_ratio = empty_cells / total_cells
            if empty_ratio > 0.5:  # More than 50% empty
                penalty += 50
        
        return penalty
    
    def _is_garbage_table(self, df):
        """
        Determine if a table is garbage (invoice header, pure text, etc.).
        
        Args:
            df: pandas DataFrame
            
        Returns:
            True if table should be rejected as garbage
        """
        rows, cols = df.shape
        
        # Reject very small tables
        if rows < 3 or cols < 3:
            return True
        
        # Reject tables that are mostly empty
        non_empty_cells = (~df.isnull() & (df != '')).sum().sum()
        if non_empty_cells < (rows * cols * 0.3):  # Less than 30% filled
            return True
        
        text_content = ' '.join(df.astype(str).values.flatten()).upper()
        
        # CRITICAL FIX: Strong garbage indicators including A/R balance tables
        garbage_indicators = [
            'BILLING INQUIRIES',
            'CUSTOMER SERVICE',
            'PAY YOUR BILL',
            'HTTP://MYACCOUNT',
            'INVOICE\nCUSTOMER SERVICE',
            # A/R Balance table indicators
            'A/R BALANCES AS OF',
            'TOTAL DUE',
            'CURRENT',
            '1-30 DAYS',
            '31-60 DAYS',
            '61-90 DAYS',
            '91-120 DAYS',
            'OVER 120 DAYS'
        ]
        
        for indicator in garbage_indicators:
            if indicator in text_content:
                return True
        
        # CRITICAL FIX: Specific check for A/R balance table pattern
        ar_balance_pattern_count = 0
        ar_balance_keywords = ['TOTAL DUE', 'CURRENT', '1-30 DAYS', '31-60 DAYS', 'OVER 120 DAYS']
        for keyword in ar_balance_keywords:
            if keyword in text_content:
                ar_balance_pattern_count += 1
        
        # If we find 3 or more A/R balance keywords, it's definitely an A/R balance table
        if ar_balance_pattern_count >= 3:
            return True
        
        # Check if table has line item characteristics
        line_item_words = ['WEARER', 'ITEM', 'RATE', 'QTY', 'TOTAL', 'RENT', 'DESCRIPTION']
        has_line_items = any(word in text_content for word in line_item_words)
        
        # CRITICAL FIX: Look for employee/wearer names (strong indicator of line item table)
        import re
        name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'  # First Last name pattern
        name_matches = len(re.findall(name_pattern, text_content))
        
        # If table has employee names, it's likely a line item table, not garbage
        if name_matches > 2:  # Multiple employee names found
            return False
        
        # If it's a large table with no line item indicators, it's likely garbage
        if rows > 10 and not has_line_items:
            return True
        
        return False
    
    def _deduplicate_tables(self, scored_tables):
        """
        Remove duplicate or very similar tables, keeping the highest scoring version.
        
        Args:
            scored_tables: List of (table, score) tuples
            
        Returns:
            List of deduplicated (table, score) tuples
        """
        if len(scored_tables) <= 1:
            return scored_tables
        
        # Sort by score (highest first)
        scored_tables.sort(key=lambda x: x[1], reverse=True)
        
        deduplicated = []
        for table, score in scored_tables:
            df = table.df
            
            # Check if this table is similar to any already accepted table
            is_duplicate = False
            for existing_table, _ in deduplicated:
                if self._tables_are_similar(df, existing_table.df):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append((table, score))
        
        return deduplicated
    
    def _tables_are_similar(self, df1, df2, similarity_threshold=0.7):
        """
        Check if two tables are similar (likely duplicates with different noise levels).
        
        Args:
            df1, df2: pandas DataFrames to compare
            similarity_threshold: Minimum similarity ratio to consider tables similar
            
        Returns:
            True if tables are similar enough to be considered duplicates
        """
        # Quick dimension check
        if abs(df1.shape[0] - df2.shape[0]) > 10:  # Very different row counts
            return False
        
        # Compare content similarity
        text1 = ' '.join(df1.astype(str).values.flatten()).upper()
        text2 = ' '.join(df2.astype(str).values.flatten()).upper()
        
        # Simple similarity check based on common words
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= similarity_threshold
    
    def _extract_line_items_from_tables(self, tables: List[List[List[str]]]) -> List[LineItem]:
        """
        Extract line items from table data.
        
        Args:
            tables: List of tables extracted from PDF
            
        Returns:
            List of LineItem objects extracted from tables
        """

        line_items = []
        
        for table_idx, table in enumerate(tables):
            if not table:
                self.logger.warning(f"[H2] Table {table_idx + 1} is empty, skipping")
                continue
                
            self.logger.info(f"[H2] Processing table {table_idx + 1} with {len(table)} rows")
            
            # Find the header row to identify column positions
            header_row_idx = self._find_header_row(table)
            if header_row_idx is None:
                self.logger.warning(f"[H2] No header row found in table {table_idx + 1}, skipping")
                continue
            
            header_row = table[header_row_idx]
            self.logger.info(f"[H2] Table {table_idx + 1} header row at index {header_row_idx}: {header_row}")
            
            column_mapping = self._map_table_columns(header_row)
            
            if not column_mapping:
                self.logger.warning(f"[H2] No recognizable columns found in table {table_idx + 1}, skipping")
                continue
            
            self.logger.info(f"[H2] Table {table_idx + 1} column mapping: {column_mapping}")
            
            # Process data rows (skip header and any rows before it)
            data_rows_processed = 0
            valid_line_items = 0
            
            for row_idx in range(header_row_idx + 1, len(table)):
                row = table[row_idx]
                
                # Skip empty rows or rows that don't have enough columns
                if not row or len(row) < max(column_mapping.values()) + 1:
                    self.logger.debug(f"[H2] Table {table_idx + 1} row {row_idx + 1}: skipped (empty or insufficient columns)")
                    continue
                
                data_rows_processed += 1
                if data_rows_processed <= 3:  # Log first 3 data rows for verification
                    self.logger.info(f"[H2] Table {table_idx + 1} data row {row_idx + 1}: {row}")
                
                parsed_line_items = self._parse_table_row_to_line_item(row, column_mapping, row_idx + 1)
                if parsed_line_items:
                    for line_item in parsed_line_items:
                        valid_line_items += 1
                        line_items.append(line_item)
                        if valid_line_items <= 3:  # Log first 3 parsed line items
                            self.logger.info(f"[H2] Parsed line item {valid_line_items}: code={line_item.item_code}, desc={line_item.description}, rate={line_item.rate}")
                else:
                    self.logger.debug(f"[H2] Table {table_idx + 1} row {row_idx + 1}: failed to parse as line item")
            
            self.logger.info(f"[H2] Table {table_idx + 1} results: {data_rows_processed} data rows processed, {valid_line_items} valid line items extracted")
        
        if not line_items:
            self.logger.error(f"[H2] CRITICAL: No line items extracted from any of the {len(tables)} tables")
        else:
            self.logger.info(f"[H2] SUCCESS: Extracted {len(line_items)} line items from {len(tables)} tables")
        
        return line_items
    
    def _find_header_row(self, table: List[List[str]]) -> Optional[int]:
        """
        Find the header row in a table by looking for column header keywords.
        
        Args:
            table: Table data as list of rows
            
        Returns:
            Index of header row, or None if not found
        """
        header_keywords = [
            'WEARER', 'ITEM', 'DESCRIPTION', 'SIZE', 'TYPE', 'QTY', 'RATE', 'TOTAL',
            'BILL', 'QUANTITY', 'AMOUNT', 'PRICE', 'CODE'
        ]
        
        for row_idx, row in enumerate(table):
            if not row:
                continue
            
            # Convert row to uppercase for comparison
            row_upper = [str(cell).upper() for cell in row]
            row_text = ' '.join(row_upper)
            
            # Count how many header keywords are found in this row
            keyword_count = sum(1 for keyword in header_keywords if keyword in row_text)
            
            # If we find at least 3 header keywords, consider this the header row
            if keyword_count >= 3:
                return row_idx
        
        return None
    
    def _map_table_columns(self, header_row: List[str]) -> Dict[str, int]:
        """
        Map table columns to their purposes based on header row.
        
        Args:
            header_row: Header row from table
            
        Returns:
            Dictionary mapping column purposes to column indices
        """
        column_mapping = {}
        
        for col_idx, header in enumerate(header_row):
            if not header:
                continue
            
            header_upper = str(header).upper()
            
            # Map common column headers to their purposes
            if 'ITEM' in header_upper and 'CODE' in header_upper:
                column_mapping['item_code'] = col_idx
            elif 'ITEM' in header_upper and 'DESCRIPTION' in header_upper:
                column_mapping['description'] = col_idx
            elif header_upper == 'ITEM':  # Exact match for "ITEM" column (item codes)
                column_mapping['item_code'] = col_idx
            elif 'DESCRIPTION' in header_upper:
                column_mapping['description'] = col_idx
            elif 'RATE' in header_upper:
                column_mapping['rate'] = col_idx
            elif 'TOTAL' in header_upper:
                column_mapping['total'] = col_idx
            elif 'TYPE' in header_upper:
                column_mapping['type'] = col_idx
            elif 'QTY' in header_upper or 'QUANTITY' in header_upper:
                column_mapping['quantity'] = col_idx
            elif 'SIZE' in header_upper:
                column_mapping['size'] = col_idx
            elif 'WEARER' in header_upper:
                column_mapping['wearer'] = col_idx
        
        # Handle common table misalignment issues
        # If TYPE column is mapped but the previous column is empty,
        # the actual TYPE data might be in the previous column
        if 'type' in column_mapping:
            type_col_idx = column_mapping['type']
            if (type_col_idx > 0 and
                type_col_idx < len(header_row) and
                not header_row[type_col_idx - 1].strip()):
                # Check if the previous column might contain the actual TYPE data
                # by looking at a few data rows if available
                self.logger.debug(f"TYPE column at index {type_col_idx} may be misaligned, "
                                f"previous column {type_col_idx - 1} is empty in header")
                # Adjust mapping to use the previous column for TYPE data
                column_mapping['type'] = type_col_idx - 1
                self.logger.debug(f"Adjusted TYPE column mapping from {type_col_idx} to {type_col_idx - 1}")
        
        return column_mapping
    
    def _parse_table_row_to_line_item(self, row: List[str], column_mapping: Dict[str, int], line_number: int) -> List[LineItem]:
        """
        Parse a table row into LineItem objects, handling multi-line cells.
        
        Args:
            row: Table row data
            column_mapping: Mapping of column purposes to indices
            line_number: Line number for debugging
            
        Returns:
            List of LineItem objects if parsing successful, empty list otherwise
        """

        try:
            line_items = []
            
            # CRITICAL FIX: Handle multi-line cells by splitting on newlines
            # Check if any cells contain newlines (multi-line data)
            has_multiline = any('\n' in str(cell) for cell in row)
            
            if has_multiline:
                self.logger.info(f"[H2] Row {line_number} contains multi-line data, splitting into individual line items")
                
                # Split each cell by newlines and get the maximum number of lines
                split_cells = []
                max_lines = 0
                
                for cell in row:
                    if cell and '\n' in str(cell):
                        lines = [line.strip() for line in str(cell).split('\n') if line.strip()]
                        split_cells.append(lines)
                        max_lines = max(max_lines, len(lines))
                    else:
                        # Single value, repeat for all lines
                        split_cells.append([str(cell).strip() if cell else ''])
                
                self.logger.info(f"[H2] Row {line_number} split into {max_lines} individual line items")
                
                # Create individual line items from each line
                for line_idx in range(max_lines):
                    individual_row = []
                    for cell_lines in split_cells:
                        if line_idx < len(cell_lines):
                            individual_row.append(cell_lines[line_idx])
                        elif len(cell_lines) == 1:
                            # Single value, use for all lines
                            individual_row.append(cell_lines[0])
                        else:
                            individual_row.append('')
                    
                    # Parse this individual row
                    line_item = self._parse_single_line_item(individual_row, column_mapping, f"{line_number}.{line_idx + 1}")
                    if line_item:
                        line_items.append(line_item)
            else:
                # Single line item
                line_item = self._parse_single_line_item(row, column_mapping, line_number)
                if line_item:
                    line_items.append(line_item)
            
            self.logger.info(f"[H2] Row {line_number} SUCCESS: created {len(line_items)} line items")
            return line_items
            
        except Exception as e:
            self.logger.error(f"[H2] Row {line_number} ERROR: Exception parsing table row: {e}")
            return []
    
    def _parse_single_line_item(self, row: List[str], column_mapping: Dict[str, int], line_number) -> Optional[LineItem]:
        """
        Parse a single row into a LineItem object.
        
        Args:
            row: Single row data
            column_mapping: Mapping of column purposes to indices
            line_number: Line number for debugging
            
        Returns:
            LineItem object if parsing successful, None otherwise
        """
        try:
            # Extract data based on column mapping
            item_code = None
            description = None
            item_type = None
            rate = None
            total = None
            quantity = 1  # Default quantity
            
            # Get item code
            if 'item_code' in column_mapping:
                item_code = row[column_mapping['item_code']].strip() if row[column_mapping['item_code']] else None
                self.logger.debug(f"[H2] Row {line_number} item_code: '{item_code}'")
            
            # Get description
            if 'description' in column_mapping:
                description = row[column_mapping['description']].strip() if row[column_mapping['description']] else None
                self.logger.debug(f"[H2] Row {line_number} description: '{description}'")
            
            # Get item type
            if 'type' in column_mapping:
                item_type = row[column_mapping['type']].strip() if row[column_mapping['type']] else None
                self.logger.debug(f"[H2] Row {line_number} item_type: '{item_type}'")
            
            # Get rate
            if 'rate' in column_mapping:
                rate_str = row[column_mapping['rate']].strip() if row[column_mapping['rate']] else None
                self.logger.debug(f"[H2] Row {line_number} rate_str: '{rate_str}'")
                if rate_str:
                    try:
                        rate = Decimal(rate_str)
                        self.logger.debug(f"[H2] Row {line_number} parsed rate: {rate}")
                    except (ValueError, InvalidOperation):
                        self.logger.warning(f"[H2] Row {line_number} invalid rate value '{rate_str}'")
            
            # Get total
            if 'total' in column_mapping:
                total_str = row[column_mapping['total']].strip() if row[column_mapping['total']] else None
                self.logger.debug(f"[H2] Row {line_number} total_str: '{total_str}'")
                if total_str:
                    try:
                        # Clean up total string (remove extra spaces)
                        total_str = total_str.replace('  ', '').strip()
                        total = Decimal(total_str)
                        self.logger.debug(f"[H2] Row {line_number} parsed total: {total}")
                    except (ValueError, InvalidOperation):
                        self.logger.warning(f"[H2] Row {line_number} invalid total value '{total_str}'")
            
            # Get quantity if available
            if 'quantity' in column_mapping:
                qty_str = row[column_mapping['quantity']].strip() if row[column_mapping['quantity']] else None
                if qty_str:
                    try:
                        quantity = int(float(qty_str))
                        self.logger.debug(f"[H2] Row {line_number} parsed quantity: {quantity}")
                    except (ValueError, TypeError):
                        quantity = 1  # Default to 1 if conversion fails
                        self.logger.debug(f"[H2] Row {line_number} defaulted quantity to 1")
            
            # Skip rows that don't have essential data
            if not description or not rate:
                self.logger.debug(f"[H2] Row {line_number} SKIPPED: missing essential data (description='{description}', rate='{rate}')")
                return None
            
            # Create LineItem
            line_item = LineItem(
                item_code=item_code,
                description=description,
                item_type=item_type,
                rate=rate,
                quantity=quantity,
                total=total,
                line_number=line_number,
                raw_text=' | '.join(row)  # Join row cells for debugging
            )
            
            self.logger.debug(f"[H2] Row {line_number} SUCCESS: created LineItem with code='{item_code}', desc='{description}', rate={rate}")
            return line_item
            
        except Exception as e:
            self.logger.error(f"[H2] Row {line_number} ERROR: Exception parsing single line item: {e}")
            return None
    
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
                    item_code=item_code,
                    description=description,
                    item_type=item_type,
                    rate=rate,
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
                    item_code=charge_type.replace(' ', '_'),  # Convert to code format
                    description=charge_type,
                    item_type="Charge",
                    rate=rate,
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
                    item_code=item_code,
                    description=description,
                    item_type=item_type,
                    rate=rate,
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
        **DEPRECATED** for new summary validation process
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

# === Module-level extraction functions for CLI ===

def extract_text_from_pdf(input_path):
    """
    Extract raw text from a PDF invoice.
    """
    processor = PDFProcessor()
    return processor._extract_text_from_pdf(Path(input_path))

def extract_lines_from_pdf(input_path):
    """
    Extract line items from a PDF invoice using EXCLUSIVE table extraction.
    Returns list of dicts with invoice_number added to each line item.
    
    Raises:
        LineItemParsingError: If table extraction fails or finds no valid line items
    """
    processor = PDFProcessor()
    invoice_data = processor.process_pdf(Path(input_path))
    invoice_number = getattr(invoice_data, "invoice_number", None)
    # Convert each line item to a dict
    result = []
    for item in getattr(invoice_data, "line_items", []):
        # Try to use ._asdict() if it's a namedtuple, else __dict__
        if hasattr(item, "_asdict"):
            d = item._asdict()
        elif hasattr(item, "__dict__"):
            d = dict(item.__dict__)
        else:
            d = dict(item)
        d["invoice_number"] = invoice_number
        result.append(d)
    return result

def extract_parts_from_pdf(input_path):
    """
    Extract parts from a PDF invoice using EXCLUSIVE table extraction.
    Returns list of dicts with all fields relevant to the parts database.
    
    This function provides the exact same output as extract_parts.py but uses
    table extraction exclusively - no fallback to text extraction.
    
    Raises:
        LineItemParsingError: If table extraction fails or finds no valid line items
    """
    lines = extract_lines_from_pdf(input_path)
    parts = []
    for line in lines:
        part = {
            "part_number": line.get("item_code"),
            "authorized_price": str(line.get("rate")) if line.get("rate") is not None else None,
            "description": line.get("description"),
            "item_type": line.get("item_type"),
            "first_seen_invoice": line.get("invoice_number"),
        }
        parts.append(part)
    return parts