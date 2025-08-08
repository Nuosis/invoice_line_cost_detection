#!/usr/bin/env python3
"""
Invoice validation script using the simplified validation engine.

This script:
1. Loads the PDF extraction JSON (from extract_parts.py)
2. Validates parts using the simplified validation engine
3. Outputs <<invoice>>_validation.json with error_lines array

Usage:
    python test_validation/validate_invoice.py --invoicePath path/to/invoice.pdf --dbPath path/to/database.db
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processing.validation_engine import ValidationEngine
from database.database import DatabaseManager


def create_logger() -> logging.Logger:
    """Create a logger for the validation script."""
    logger = logging.getLogger('invoice_validation')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def main():
    """Main function for the invoice validation script."""
    parser = argparse.ArgumentParser(description="Validate invoice using simplified validation engine")
    parser.add_argument("--invoicePath", required=True, help="Path to PDF invoice")
    parser.add_argument("--dbPath", help="Path to SQLite database (default: test_validation/test_parts_review_<<invoice>>.db)")
    parser.add_argument("--outputDir", help="Directory to store validation output (default: ./test_validation/expectations/)")
    parser.add_argument("--interactive", action="store_true", help="Enable interactive part discovery")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = create_logger()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate input
    pdf_path = Path(args.invoicePath)
    if not pdf_path.exists():
        logger.error(f"File not found: {pdf_path}")
        return 1
    if not pdf_path.suffix.lower() == '.pdf':
        logger.error(f"Not a PDF: {pdf_path}")
        return 1
    
    invoice_stem = pdf_path.stem
    
    # Set up database path
    if args.dbPath:
        db_path = Path(args.dbPath)
    else:
        # Use the database created by database_parts_review.py
        db_path = Path("test_validation") / f"test_parts_review_{invoice_stem}.db"
    
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        logger.info("Run database_parts_review.py first to create the parts database")
        return 1
    
    # Set up output directory
    if args.outputDir:
        output_dir = Path(args.outputDir)
    else:
        output_dir = Path(__file__).parent / "expectations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Look for the PDF extraction JSON (created by extract_parts.py)
    parts_json_path = output_dir / f"{invoice_stem}_parts.json"
    if not parts_json_path.exists():
        logger.error(f"Parts extraction JSON not found: {parts_json_path}")
        logger.info("Run extract_parts.py first to create the parts extraction JSON")
        return 1
    
    try:
        logger.info(f"Starting validation for invoice: {pdf_path}")
        
        # Load the PDF extraction JSON
        logger.info(f"Loading parts extraction JSON: {parts_json_path}")
        with open(parts_json_path, 'r', encoding='utf-8') as f:
            extraction_json = json.load(f)
        
        logger.info(f"Loaded extraction with {len(extraction_json.get('parts', []))} parts")
        
        # Initialize database manager
        logger.info("Initializing database manager...")
        db_manager = DatabaseManager(str(db_path))
        
        # Initialize simplified validation engine
        logger.info("Initializing validation engine...")
        validation_engine = ValidationEngine(db_manager, interactive_mode=args.interactive)
        
        # Validate using the new JSON-based approach
        logger.info("Running validation...")
        validation_result = validation_engine.validate_invoice_json(extraction_json)
        
        # Log validation summary
        summary = validation_result.get('validation_summary', {})
        logger.info(f"Validation complete:")
        logger.info(f"  Total parts: {summary.get('total_parts', 0)}")
        logger.info(f"  Passed: {summary.get('passed_parts', 0)}")
        logger.info(f"  Failed: {summary.get('failed_parts', 0)}")
        logger.info(f"  Unknown: {summary.get('unknown_parts', 0)}")
        logger.info(f"  Error lines: {len(validation_result.get('error_lines', []))}")
        
        # Save validation result JSON
        validation_output_path = output_dir / f"{invoice_stem}_validation.json"
        logger.info(f"Saving validation result: {validation_output_path}")
        
        with open(validation_output_path, 'w', encoding='utf-8') as f:
            json.dump(validation_result, f, indent=2, default=str)
        
        logger.info("Validation complete!")
        logger.info(f"Validation result saved to: {validation_output_path}")
        
        # Show error lines if any
        error_lines = validation_result.get('error_lines', [])
        if error_lines:
            logger.info(f"\nFound {len(error_lines)} error lines:")
            for i, error in enumerate(error_lines[:5], 1):  # Show first 5 errors
                logger.info(f"  {i}. Line {error.get('line_number', '?')}: {error.get('error_message', 'Unknown error')}")
            if len(error_lines) > 5:
                logger.info(f"  ... and {len(error_lines) - 5} more errors")
        else:
            logger.info("\n✅ No validation errors found!")
        
        return 0
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())