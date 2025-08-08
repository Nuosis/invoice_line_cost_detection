#!/usr/bin/env python3
"""
Text extraction script for invoice PDFs.

This script uses the exact same text extraction method as the PDFProcessor
to extract text from a specified PDF invoice and save the extracted text
to test_validation/expectations/.
"""

import argparse
import logging
from pathlib import Path
from typing import Optional

# Import the extract_text_from_pdf function from the processing module
from processing.pdf_processor import extract_text_from_pdf


def create_logger() -> logging.Logger:
    """Create a logger for text extraction."""
    logger = logging.getLogger('text_extractor')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def extract_text_with_logging(pdf_path: Path, logger: logging.Logger) -> Optional[str]:
    """
    Extract text content from PDF using the processing module's extract_text_from_pdf function.
    
    This function wraps the processing module's extract_text_from_pdf function
    and adds logging specific to the test validation context.
    
    Args:
        pdf_path: Path to the PDF file
        logger: Logger instance
        
    Returns:
        Complete text content from all pages, or None if extraction fails
    """
    try:
        # Use the processing module's extract_text_from_pdf function
        full_text = extract_text_from_pdf(str(pdf_path))
        
        if not full_text or not full_text.strip():
            logger.error(f"No text could be extracted from PDF: {pdf_path}")
            return None
        
        if len(full_text.strip()) < 100:
            logger.warning(
                f"Extracted text is too short ({len(full_text)} characters) "
                f"from {pdf_path}, may indicate extraction failure"
            )
        
        # Count pages for logging (approximate based on page breaks)
        page_count = full_text.count('\n\n') + 1  # Rough estimate
        logger.info(f"Extracted {len(full_text)} characters from approximately {page_count} pages: {pdf_path.name}")
        return full_text
        
    except Exception as e:
        logger.error(f"Error during text extraction from {pdf_path}: {e}")
        return None


def main():
    """Main function to extract text from a specified PDF invoice."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF invoice using the same method as PDFProcessor"
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
    
    logger.info(f"Processing invoice: {pdf_path.name}")
    
    # Extract text using the processing module's extract_text_from_pdf function
    extracted_text = extract_text_with_logging(pdf_path, logger)
    
    if extracted_text is not None:
        # Save extracted text to output file
        output_file = output_dir / f"{pdf_path.stem}_extracted_text.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Add header with metadata
                f.write(f"# Text extracted from: {pdf_path.name}\n")
                f.write(f"# Extraction method: processing.pdf_processor.extract_text_from_pdf()\n")
                f.write(f"# Text length: {len(extracted_text)} characters\n")
                f.write(f"# =" * 70 + "\n\n")
                f.write(extracted_text)
            
            logger.info(f"Successfully saved extracted text to: {output_file}")
            logger.info(f"Text length: {len(extracted_text)} characters")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to save text for {pdf_path.name}: {e}")
            return 1
    else:
        logger.error(f"Failed to extract text from: {pdf_path.name}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())