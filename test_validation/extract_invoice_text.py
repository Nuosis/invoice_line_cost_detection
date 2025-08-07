#!/usr/bin/env python3
"""
Text extraction script for invoice PDFs.

This script uses the exact same text extraction method as the PDFProcessor
to extract text from all PDFs in the docs/invoices/ directory and save
the extracted text to docs/invoices/output/.
"""

import logging
from pathlib import Path
from typing import Optional
import pdfplumber


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


def extract_text_from_pdf(pdf_path: Path, logger: logging.Logger) -> Optional[str]:
    """
    Extract text content from all pages of the PDF using the same method as PDFProcessor.
    
    This is the exact same implementation as PDFProcessor._extract_text_from_pdf()
    
    Args:
        pdf_path: Path to the PDF file
        logger: Logger instance
        
    Returns:
        Complete text content from all pages, or None if extraction fails
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
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {e}"
                    )
                    continue
        
        if not full_text.strip():
            logger.error(f"No text could be extracted from PDF: {pdf_path}")
            return None
        
        if len(full_text.strip()) < 100:
            logger.warning(
                f"Extracted text is too short ({len(full_text)} characters) "
                f"from {pdf_path}, may indicate extraction failure"
            )
        
        logger.info(f"Extracted {len(full_text)} characters from {page_count} pages: {pdf_path.name}")
        return full_text
        
    except Exception as e:
        logger.error(f"Error during text extraction from {pdf_path}: {e}")
        return None


def main():
    """Main function to extract text from all PDFs in docs/invoices/."""
    logger = create_logger()
    
    # Define paths
    invoices_dir = Path("docs/invoices")
    output_dir = Path("docs/invoices/output")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(invoices_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.error(f"No PDF files found in {invoices_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF
    successful_extractions = 0
    failed_extractions = 0
    
    for pdf_path in sorted(pdf_files):
        logger.info(f"Processing: {pdf_path.name}")
        
        # Extract text using the same method as PDFProcessor
        extracted_text = extract_text_from_pdf(pdf_path, logger)
        
        if extracted_text is not None:
            # Save extracted text to output file
            output_file = output_dir / f"{pdf_path.stem}_extracted_text.txt"
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    # Add header with metadata
                    f.write(f"# Text extracted from: {pdf_path.name}\n")
                    f.write(f"# Extraction method: Same as PDFProcessor._extract_text_from_pdf()\n")
                    f.write(f"# Text length: {len(extracted_text)} characters\n")
                    f.write(f"# =" * 70 + "\n\n")
                    f.write(extracted_text)
                
                logger.info(f"Saved extracted text to: {output_file}")
                successful_extractions += 1
                
            except Exception as e:
                logger.error(f"Failed to save text for {pdf_path.name}: {e}")
                failed_extractions += 1
        else:
            logger.error(f"Failed to extract text from: {pdf_path.name}")
            failed_extractions += 1
    
    # Summary
    logger.info(f"\nExtraction Summary:")
    logger.info(f"  Successful: {successful_extractions}")
    logger.info(f"  Failed: {failed_extractions}")
    logger.info(f"  Total: {len(pdf_files)}")
    
    if successful_extractions > 0:
        logger.info(f"Extracted text files saved to: {output_dir}")


if __name__ == "__main__":
    main()