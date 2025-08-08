#!/usr/bin/env python3
"""
Simple parts extraction script for invoice PDFs.

Shows what database fields are populated when parts are extracted from invoices.
Uses the PDF processor directly to test line item detection in isolation.
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
    logger = logging.getLogger('parts_extractor')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def extract_parts_using_pdf_processor(pdf_path: Path, logger: logging.Logger) -> Optional[InvoiceData]:
    """
    Extract parts from an invoice using the enhanced table-based extraction.
    Uses the new process_pdf method which leverages table extraction with text fallback.
    """
    try:
        logger.info(f"Processing: {pdf_path.name}")
        logger.info("Processing PDF with enhanced table extraction...")

        # Create PDF processor instance
        processor = PDFProcessor(logger=logger)
        
        # Use the enhanced process_pdf method which includes table-based line item extraction
        invoice_data = processor.process_pdf(pdf_path)
        
        logger.info(f"Successfully processed PDF: {pdf_path.name}")
        logger.info(f"Extracted {len(invoice_data.line_items)} line items")

        return invoice_data

    except Exception as e:
        logger.error(f"Error processing {pdf_path.name}: {e}")
        return None


def create_simple_parts_report(invoice_data: InvoiceData, output_file: Path, logger: logging.Logger) -> Optional[Dict[str, Any]]:
    """Create a simple JSON report showing database fields for extracted parts from LineItem objects."""
    try:
        if not invoice_data.line_items:
            logger.error("No line items found in invoice data")
            return None
        
        logger.info(f"Found {len(invoice_data.line_items)} line items from extract_text_from_pdf + _extract_line_items")
        
        # Build JSON structure showing database field values from LineItem objects created by _parse_line_item
        invoice_number = invoice_data.invoice_number or 'UNKNOWN'
        invoice_date = invoice_data.invoice_date or 'UNKNOWN'
        
        # Create the report structure with enhanced metadata and format sections
        report_data = {
            "extraction_method": "PDFProcessor.process_pdf (table-based line item extraction with text fallback)",
            "invoice_metadata": {
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "customer_number": invoice_data.customer_number,
                "customer_name": invoice_data.customer_name,
                "total_line_items": len(invoice_data.line_items),
                "parts_with_item_codes": 0
            },
            "format_sections": [],
            "parts": [],
            "summary": {
                "total_parts_detected": 0,
                "parts_with_rates": 0,
                "parts_with_descriptions": 0,
                "parts_with_item_types": 0,
                "format_sections_found": 0
            }
        }
        
        # Add format sections data (SUBTOTAL, FREIGHT, TAX, TOTAL)
        if hasattr(invoice_data, 'format_sections') and invoice_data.format_sections:
            for section in invoice_data.format_sections:
                section_data = {
                    "section_type": section.section_type,
                    "amount": float(section.amount) if section.amount else None
                }
                report_data["format_sections"].append(section_data)
            report_data["summary"]["format_sections_found"] = len(invoice_data.format_sections)
        
        # Process each line item (items with item_code OR service charges with descriptions become parts)
        for line_item in invoice_data.line_items:
            # Include items with item_code OR service charges/items with descriptions and rates
            # This includes both regular parts and service charges like "NAME EMBL CHARGE", "PREP CHARGE"
            if not line_item.item_code and not line_item.description:
                continue
            
            # Skip items without rates (these are likely category headers or invalid entries)
            if not line_item.rate:
                continue
                
            part_data = {
                # Database fields that would be populated when adding to Parts table
                "database_fields": {
                    "part_number": line_item.item_code or None,  # Only actual item codes, null for service charges
                    "authorized_price": float(line_item.rate) if line_item.rate else None,  # From _parse_line_item
                    "description": line_item.description or None,  # From _parse_line_item
                    "item_type": line_item.item_type or None,  # From _parse_line_item - now a database field
                    "category": None,  # Empty - not extracted from invoices
                    "source": "discovered",  # All invoice parts are 'discovered'
                    "first_seen_invoice": invoice_number,  # From metadata parsing
                    "is_active": True,  # New parts are active by default
                    "notes": None  # Empty - not extracted from invoices
                },
                
                # Additional extracted data from LineItem (created by _parse_line_item)
                "lineitem_fields": {
                    "line_number": line_item.line_number or None,  # From _parse_line_item
                    "raw_text": line_item.raw_text or None  # From _parse_line_item
                }
            }
            
            report_data["parts"].append(part_data)
            
            # Update summary counts
            report_data["summary"]["total_parts_detected"] += 1
            if line_item.rate is not None:
                report_data["summary"]["parts_with_rates"] += 1
            if line_item.description:
                report_data["summary"]["parts_with_descriptions"] += 1
            if line_item.item_type:
                report_data["summary"]["parts_with_item_types"] += 1
        
        # Update metadata count
        report_data["invoice_metadata"]["parts_with_item_codes"] = report_data["summary"]["total_parts_detected"]
        
        # Write JSON report
        with open(output_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(report_data, jsonfile, indent=2, ensure_ascii=False)
        
        return report_data
        
    except Exception as e:
        logger.error(f"Error creating report: {e}")
        return None


def main():
    """Main function - builds on extract_lines.py approach using individual methods."""
    parser = argparse.ArgumentParser(description="Extract parts and show database field values using extract_text_from_pdf + _extract_line_items + _parse_line_item")
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
    output_file = output_dir / f"{pdf_path.stem}_parts.json"
    
    # Remove existing output file if it exists
    if output_file.exists():
        logger.info(f"Removing existing output file: {output_file}")
        output_file.unlink()
    
    # Process invoice using extract_text_from_pdf + _extract_line_items + _parse_line_item methods
    invoice_data = extract_parts_using_pdf_processor(pdf_path, logger)
    if invoice_data is None:
        return 1
    
    # Create report
    if create_simple_parts_report(invoice_data, output_file, logger):
        parts_count = len(invoice_data.line_items)
        valid_parts_count = len([item for item in invoice_data.line_items if hasattr(item, 'item_code') and item.item_code])
        invoice_number = invoice_data.invoice_number or 'UNKNOWN'
        invoice_date = invoice_data.invoice_date or 'UNKNOWN'
        
        print(f"\nPARTS DATABASE FIELDS REPORT")
        print(f"Method: PDFProcessor.process_pdf (table-based line item extraction)")
        print(f"Invoice: {invoice_number}")
        print(f"Date: {invoice_date}")
        print(f"Line Items Found: {parts_count}")
        print(f"Valid Parts (with item_code): {valid_parts_count}")
        print(f"Output: {output_file}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())