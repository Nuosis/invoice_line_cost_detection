#!/usr/bin/env python3
"""
Invoice text extraction script for PDF validation.

This script extracts raw text from PDF invoices using the same method as the PDFProcessor
to validate text extraction functionality. It's designed to be run as a standalone
validation tool for testing text extraction from invoice PDFs.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Add the project root to the path so we can import from the processing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the extract_text_from_pdf function from the processing module
from processing.pdf_processor import extract_text_from_pdf


def create_logger() -> logging.Logger:
    """Create a logger for invoice text extraction."""
    logger = logging.getLogger('invoice_text_extractor')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def extract_invoice_text_with_logging(pdf_path: Path, logger: logging.Logger) -> Optional[str]:
    """
    Extract text content from PDF invoice using the processing module's extract_text_from_pdf function.
    
    This function wraps the processing module's extract_text_from_pdf function
    and adds logging specific to invoice text validation.
    
    Args:
        pdf_path: Path to the PDF invoice file
        logger: Logger instance
        
    Returns:
        Complete text content from all pages, or None if extraction fails
    """
    try:
        logger.info(f"Starting text extraction from invoice: {pdf_path.name}")
        
        # Use the processing module's extract_text_from_pdf function
        full_text = extract_text_from_pdf(str(pdf_path))
        
        if not full_text or not full_text.strip():
            logger.error(f"No text could be extracted from invoice PDF: {pdf_path}")
            return None
        
        # Validate extracted text quality
        text_length = len(full_text.strip())
        if text_length < 100:
            logger.warning(
                f"Extracted text is suspiciously short ({text_length} characters) "
                f"from {pdf_path.name}, may indicate extraction failure"
            )
        
        # Count approximate pages for logging (based on page breaks)
        page_count = full_text.count('\n\n') + 1  # Rough estimate
        logger.info(f"Successfully extracted {text_length} characters from approximately {page_count} pages")
        
        # Log some basic content validation
        if "invoice" in full_text.lower():
            logger.info("Text contains 'invoice' keyword - good sign")
        else:
            logger.warning("Text does not contain 'invoice' keyword - may not be an invoice")
            
        return full_text
        
    except Exception as e:
        logger.error(f"Error during text extraction from invoice {pdf_path}: {e}")
        return None


def main():
    """Main function to extract text from a specified PDF invoice for validation."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF invoice for validation using the same method as PDFProcessor"
    )
    parser.add_argument(
        "--invoicePath",
        required=True,
        help="Path to the PDF invoice file to process"
    )
    
    args = parser.parse_args()
    logger = create_logger()
    
    # Validate input file
    pdf_path = Path(args.invoicePath)
    if not pdf_path.exists():
        logger.error(f"Invoice file not found: {pdf_path}")
        return 1
    
    if not pdf_path.suffix.lower() == '.pdf':
        logger.error(f"File is not a PDF: {pdf_path}")
        return 1
    
    # Define output directory - use path relative to this script's location
    script_dir = Path(__file__).parent
    output_dir = script_dir / "expectations"
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Processing invoice for text validation: {pdf_path.name}")
    
    # Extract text using the processing module's extract_text_from_pdf function
    extracted_text = extract_invoice_text_with_logging(pdf_path, logger)
    
    if extracted_text is not None:
        # Save extracted text to output file
        output_file = output_dir / f"{pdf_path.stem}_invoice_text.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Add header with metadata for validation
                f.write(f"# Invoice text extracted from: {pdf_path.name}\n")
                f.write(f"# Extraction method: processing.pdf_processor.extract_text_from_pdf()\n")
                f.write(f"# Text length: {len(extracted_text)} characters\n")
                f.write(f"# Validation purpose: Text extraction verification\n")
                f.write(f"# " + "=" * 70 + "\n\n")
                f.write(extracted_text)
            
            logger.info(f"Successfully saved extracted invoice text to: {output_file}")
            logger.info(f"Text length: {len(extracted_text)} characters")
            
            # Print summary for validation
            print(f"\nINVOICE TEXT EXTRACTION VALIDATION")
            print(f"Invoice: {pdf_path.name}")
            print(f"Text Length: {len(extracted_text)} characters")
            print(f"Output File: {output_file}")
            print(f"Status: SUCCESS")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to save extracted text for {pdf_path.name}: {e}")
            return 1
    else:
        logger.error(f"Failed to extract text from invoice: {pdf_path.name}")
        print(f"\nINVOICE TEXT EXTRACTION VALIDATION")
        print(f"Invoice: {pdf_path.name}")
        print(f"Status: FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())