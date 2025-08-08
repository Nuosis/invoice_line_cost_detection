#!/usr/bin/env python3
"""
Simple line extraction script for invoice PDFs.

Shows all detected line items from invoices for visual validation of line parsing.
Uses the PDF processor directly to test line item detection in isolation.
Unlike extract_parts.py which focuses on parts with item codes, this shows ALL lines.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add the project root to the path so we can import from the processing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the extract_text_from_pdf function from the processing module
from processing.pdf_processor import extract_text_from_pdf, PDFProcessor
from processing.models import InvoiceData


def create_logger() -> logging.Logger:
    """Create a simple logger."""
    logger = logging.getLogger('lines_extractor')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def extract_lines_using_pdf_processor(pdf_path: Path, logger: logging.Logger) -> Optional[InvoiceData]:
    """Extract all line items from an invoice using the PDF processor's enhanced process_pdf method."""
    try:
        logger.info(f"Processing: {pdf_path.name}")
        
        # Create PDF processor instance
        processor = PDFProcessor(logger=logger)
        
        # Use the enhanced process_pdf method which leverages table extraction with text fallback
        logger.info("Processing PDF with enhanced table extraction...")
        invoice_data = processor.process_pdf(pdf_path)
        
        logger.info(f"Successfully processed PDF: {pdf_path.name}")
        logger.info(f"Extracted {len(invoice_data.line_items)} line items")
        
        # Log which extraction method was used
        if invoice_data.processing_notes:
            for note in invoice_data.processing_notes:
                if "table" in note.lower():
                    logger.info("Used table-based line item extraction")
                    break
        
        return invoice_data
        
    except Exception as e:
        logger.error(f"Error processing {pdf_path.name}: {e}")
        return None


def create_lines_validation_report(invoice_data: InvoiceData, output_file: Path, logger: logging.Logger) -> Optional[Dict[str, Any]]:
    """Create a simple JSON report showing exactly what PDFProcessor._extract_line_items detected."""
    try:
        if not invoice_data.line_items:
            logger.error("No line items found in invoice data")
            return None
        
        logger.info(f"Found {len(invoice_data.line_items)} line items from PDFProcessor._extract_line_items")
        
        # Build simple JSON structure showing exactly what was extracted
        invoice_number = invoice_data.invoice_number or 'UNKNOWN'
        invoice_date = invoice_data.invoice_date or 'UNKNOWN'
        
        # Line items are now extracted exclusively using table-based extraction
        extraction_method = "PDFProcessor.process_pdf (table-based line item extraction)"
        
        # Create the report structure - no custom validation, just raw extraction results
        report_data = {
            "extraction_method": extraction_method,
            "invoice_metadata": {
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "total_lines_detected": len(invoice_data.line_items)
            },
            "line_items": [],
            "summary": {
                "total_lines_detected": len(invoice_data.line_items),
                "lines_with_item_codes": 0,
                "lines_with_descriptions": 0,
                "lines_with_rates": 0,
                "lines_with_item_types": 0
            }
        }
        
        # Process each line item - show exactly what PDFProcessor extracted
        for i, line_item in enumerate(invoice_data.line_items, 1):
            # Build line item data showing raw extraction results
            line_data = {
                # Core line identification
                "line_number": line_item.line_number or i,
                "raw_text": (line_item.raw_text or '').strip(),
                
                # Extracted components (exactly as PDFProcessor found them)
                "item_code": line_item.item_code or None,
                "description": line_item.description or None,
                "rate": float(line_item.rate) if line_item.rate is not None else None,
                "item_type": line_item.item_type or None,
                
                # PDFProcessor's built-in validation result
                "processor_is_valid": line_item.is_valid()
            }
            
            report_data["line_items"].append(line_data)
            
            # Update summary counts (simple counts, no custom logic)
            if line_item.item_code:
                report_data["summary"]["lines_with_item_codes"] += 1
            if line_item.description:
                report_data["summary"]["lines_with_descriptions"] += 1
            if line_item.rate is not None:
                report_data["summary"]["lines_with_rates"] += 1
            if line_item.item_type:
                report_data["summary"]["lines_with_item_types"] += 1
        
        # Write JSON report
        with open(output_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(report_data, jsonfile, indent=2, ensure_ascii=False)
        
        return report_data
        
    except Exception as e:
        logger.error(f"Error creating lines validation report: {e}")
        return None


def main():
    """Main function - uses extract_text_from_pdf and _extract_line_items to test line item extraction for visual validation."""
    parser = argparse.ArgumentParser(description="Extract all line items for visual validation using extract_text_from_pdf and _extract_line_items")
    parser.add_argument("--invoicePath", required=True, help="Path to PDF invoice")
    
    args = parser.parse_args()
    logger = create_logger()
    
    # Validate input
    pdf_path = Path(args.invoicePath)
    if not pdf_path.exists():
        logger.error(f"File not found: {pdf_path}")
        return 1
    
    if not pdf_path.suffix.lower() == '.pdf':
        logger.error(f"Not a PDF: {pdf_path}")
        return 1
    
    # Set output - use path relative to this script's location
    script_dir = Path(__file__).parent
    output_dir = script_dir / "expectations"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{pdf_path.stem}_lines.json"
    
    # Remove existing output file if it exists
    if output_file.exists():
        logger.info(f"Removing existing output file: {output_file}")
        output_file.unlink()
    
    # Process invoice using extract_text_from_pdf and _extract_line_items methods
    invoice_data = extract_lines_using_pdf_processor(pdf_path, logger)
    if invoice_data is None:
        return 1
    
    # Create report
    report_data = create_lines_validation_report(invoice_data, output_file, logger)
    if report_data:
        # Get counts from the report data
        total_lines = report_data["summary"]["total_lines_detected"]
        lines_with_codes = report_data["summary"]["lines_with_item_codes"]
        lines_with_descriptions = report_data["summary"]["lines_with_descriptions"]
        lines_with_rates = report_data["summary"]["lines_with_rates"]
        lines_with_types = report_data["summary"]["lines_with_item_types"]
        
        invoice_number = invoice_data.invoice_number or 'UNKNOWN'
        invoice_date = invoice_data.invoice_date or 'UNKNOWN'
        
        print(f"\nLINE EXTRACTION VERIFICATION REPORT")
        print(f"Method: {report_data['extraction_method']}")
        print(f"Invoice: {invoice_number}")
        print(f"Date: {invoice_date}")
        print(f"Total Lines Detected: {total_lines}")
        print(f"Lines with Item Codes: {lines_with_codes}")
        print(f"Lines with Descriptions: {lines_with_descriptions}")
        print(f"Lines with Rates: {lines_with_rates}")
        print(f"Lines with Item Types: {lines_with_types}")
        print(f"Output: {output_file}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())