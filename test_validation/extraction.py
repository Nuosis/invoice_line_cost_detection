#!/usr/bin/env python3
"""
Extraction Runner Script

Runs the complete extraction validation suite:
1. extract_invoice_text.py - Text extraction verification
2. extract_lines.py - Line detection verification (Type I/II error detection)
3. extract_parts.py - Parts database field verification

This script provides a single entry point to run all extraction validation
scripts in sequence for comprehensive PDF processing verification.
"""

import argparse
import csv
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Add the parent directory to the path so we can import from processing
sys.path.append(str(Path(__file__).parent.parent))
from processing.pdf_processor import PDFProcessor


def create_logger() -> logging.Logger:
    """Create a logger for the extraction runner."""
    logger = logging.getLogger('extraction_runner')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def extract_tables_to_csv(pdf_path: str, output_dir: str, logger: logging.Logger) -> Tuple[bool, str]:
    """
    Extract tables from a PDF invoice and save to CSV files.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save output files
        logger: Logger instance
        
    Returns:
        Tuple of (success, output_message)
    """
    try:
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            return False, f"PDF file not found: {pdf_path}"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Initialize processor
        processor = PDFProcessor()
        
        # Extract tables
        logger.info(f"Extracting tables from: {pdf_file.name}")
        tables = processor._extract_tables(pdf_file)
        
        # Prepare results
        results = {
            "pdf_file": str(pdf_file),
            "total_tables": len(tables),
            "tables_info": [],
            "output_files": []
        }
        
        if not tables:
            logger.warning("No tables found in PDF")
            return True, "No tables found in PDF - this may be normal for text-based invoices"
        
        # Save each table to a separate CSV file
        base_name = pdf_file.stem
        
        for table_idx, table in enumerate(tables):
            if not table:
                continue
                
            # Create CSV filename
            csv_filename = f"{base_name}_table_{table_idx + 1}.csv"
            csv_path = output_dir / csv_filename
            
            # Write table to CSV
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write all rows
                for row in table:
                    writer.writerow(row)
            
            # Record table info
            table_info = {
                "table_number": table_idx + 1,
                "rows": len(table),
                "columns": len(table[0]) if table else 0,
                "csv_file": str(csv_path)
            }
            results["tables_info"].append(table_info)
            results["output_files"].append(str(csv_path))
            
            logger.info(f"Table {table_idx + 1}: {len(table)} rows, {len(table[0]) if table else 0} columns -> {csv_filename}")
        
        # Also save a summary JSON file
        summary_path = output_dir / f"{base_name}_tables_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(results, jsonfile, indent=2)
        
        results["summary_file"] = str(summary_path)
        logger.info(f"Summary saved to: {summary_path.name}")
        
        success_msg = f"Successfully extracted {len(tables)} tables to CSV files"
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Error during table extraction: {e}"
        logger.error(error_msg)
        return False, error_msg


def run_extraction_script(script_name: str, invoice_path: str, logger: logging.Logger) -> Tuple[bool, str]:
    """
    Run a single extraction script and return success status and output.
    
    Args:
        script_name: Name of the script to run (without .py extension)
        invoice_path: Path to the PDF invoice
        logger: Logger instance
        
    Returns:
        Tuple of (success, output_message)
    """
    script_path = Path(__file__).parent / f"{script_name}.py"
    
    if not script_path.exists():
        error_msg = f"Script not found: {script_path}"
        logger.error(error_msg)
        return False, error_msg
    
    try:
        logger.info(f"Running {script_name}.py...")
        
        # Run the script with the absolute invoice path
        result = subprocess.run(
            [sys.executable, str(script_path), "--invoicePath", invoice_path],
            capture_output=True,
            text=True,
            cwd=script_path.parent
        )
        
        if result.returncode == 0:
            logger.info(f"✅ {script_name}.py completed successfully")
            return True, result.stdout
        else:
            error_msg = f"❌ {script_name}.py failed with return code {result.returncode}"
            if result.stderr:
                error_msg += f"\nError: {result.stderr}"
            logger.error(error_msg)
            return False, error_msg
            
    except Exception as e:
        error_msg = f"❌ Error running {script_name}.py: {e}"
        logger.error(error_msg)
        return False, error_msg


def main():
    """Main function - runs all extraction scripts in sequence."""
    parser = argparse.ArgumentParser(
        description="Run complete extraction validation suite (text, lines, parts)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extraction.py --invoicePath docs/invoices/5790265785.pdf
  python extraction.py --invoicePath /path/to/invoice.pdf

This script runs three extraction validation scripts in sequence:
1. extract_invoice_text.py - Verifies text extraction accuracy
2. extract_lines.py - Verifies line detection (Type I/II error detection)
3. extract_parts.py - Verifies parts database field mapping

All outputs are saved to the expectations/ directory.
        """
    )
    parser.add_argument(
        "--invoicePath", 
        required=True, 
        help="Path to PDF invoice file to process"
    )
    
    args = parser.parse_args()
    logger = create_logger()
    
    # Validate input file and convert to absolute path
    pdf_path = Path(args.invoicePath)
    
    # If path is relative, resolve it relative to the current working directory
    if not pdf_path.is_absolute():
        pdf_path = pdf_path.resolve()
    
    if not pdf_path.exists():
        logger.error(f"Invoice file not found: {pdf_path}")
        return 1
    
    if not pdf_path.suffix.lower() == '.pdf':
        logger.error(f"File is not a PDF: {pdf_path}")
        return 1
    
    # Define extraction scripts to run in order
    extraction_scripts = [
        ("extract_invoice_text", "Text Extraction Verification"),
        ("extract_lines", "Line Detection Verification"),
        ("extract_parts", "Parts Database Field Verification"),
        ("extract_tables", "Table Extraction to CSV")
    ]
    
    logger.info("=" * 80)
    logger.info("EXTRACTION VALIDATION SUITE")
    logger.info("=" * 80)
    logger.info(f"Processing: {pdf_path.name}")
    logger.info(f"Full path: {pdf_path}")
    logger.info("")
    
    # Track results
    results: List[Tuple[str, bool, str]] = []
    overall_success = True
    
    # Run each extraction script with absolute path
    for script_name, description in extraction_scripts:
        logger.info(f"Step {len(results) + 1}/4: {description}")
        logger.info("-" * 60)
        
        # Handle table extraction specially (it's not a separate script)
        if script_name == "extract_tables":
            expectations_dir = Path(__file__).parent / "expectations"
            success, output = extract_tables_to_csv(str(pdf_path), str(expectations_dir), logger)
        else:
            success, output = run_extraction_script(script_name, str(pdf_path), logger)
        
        results.append((script_name, success, output))
        
        if not success:
            overall_success = False
            logger.error(f"Failed: {description}")
        else:
            logger.info(f"Success: {description}")
        
        logger.info("")
    
    # Print summary
    logger.info("=" * 80)
    logger.info("EXTRACTION VALIDATION SUMMARY")
    logger.info("=" * 80)
    
    for script_name, success, output in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{script_name:25} {status}")
    
    logger.info("")
    
    if overall_success:
        logger.info("🎉 All extraction validation scripts completed successfully!")
        logger.info("")
        logger.info("Output files generated in expectations/ directory:")
        
        # List expected output files
        expectations_dir = Path(__file__).parent / "expectations"
        stem = pdf_path.stem
        expected_files = [
            f"{stem}_extracted_text.txt",
            f"{stem}_lines.json",
            f"{stem}_parts.json",
            f"{stem}_tables_summary.json"
        ]
        
        for filename in expected_files:
            file_path = expectations_dir / filename
            if file_path.exists():
                logger.info(f"  ✅ {filename}")
            else:
                logger.info(f"  ❓ {filename} (may not have been created)")
        
        # Also check for table CSV files
        table_files = list(expectations_dir.glob(f"{stem}_table_*.csv"))
        if table_files:
            logger.info(f"  ✅ {len(table_files)} table CSV file(s)")
            for table_file in sorted(table_files):
                logger.info(f"    - {table_file.name}")
        
        logger.info("")
        logger.info("Use these files to:")
        logger.info("  • Verify text extraction accuracy")
        logger.info("  • Identify Type I/II errors in line detection")
        logger.info("  • Validate parts database field mapping")
        logger.info("  • Analyze table structure and data extraction")
        
        return 0
    else:
        logger.error("❌ Some extraction validation scripts failed!")
        logger.error("Check the error messages above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())