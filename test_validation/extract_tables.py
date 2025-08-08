#!/usr/bin/env python3
"""
Table extraction script for testing PDF table extraction using pdfplumber.

This script extracts tables from PDF invoices and outputs the results to CSV files
for observation and analysis.
"""

import sys
import csv
import json
from pathlib import Path
from typing import List, Dict, Any

# Add the parent directory to the path so we can import from processing
sys.path.append(str(Path(__file__).parent.parent))

from processing.pdf_processor import PDFProcessor


def extract_tables_to_csv(pdf_path: str, output_dir: str = None) -> Dict[str, Any]:
    """
    Extract tables from a PDF invoice and save to CSV files.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save output files (defaults to same as script)
        
    Returns:
        Dictionary with extraction results and metadata
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Set up output directory - default to expectations directory
    if output_dir is None:
        output_dir = Path(__file__).parent / "expectations"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize processor
    processor = PDFProcessor()
    
    # Extract tables
    print(f"Extracting tables from: {pdf_file.name}")
    tables = processor._extract_tables(pdf_file)
    
    # Prepare results
    results = {
        "pdf_file": str(pdf_file),
        "total_tables": len(tables),
        "tables_info": [],
        "output_files": []
    }
    
    if not tables:
        print("No tables found in PDF")
        return results
    
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
        
        print(f"Table {table_idx + 1}: {len(table)} rows, {len(table[0]) if table else 0} columns -> {csv_filename}")
    
    # Also save a summary JSON file
    summary_path = output_dir / f"{base_name}_tables_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(results, jsonfile, indent=2)
    
    results["summary_file"] = str(summary_path)
    print(f"Summary saved to: {summary_path.name}")
    
    return results


def main():
    """Main function to run table extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract tables from PDF invoices and save to CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_tables.py --invoicePath ../docs/invoices/5790265786.pdf
  python extract_tables.py --invoicePath /path/to/invoice.pdf --outputDir /path/to/output
        """
    )
    parser.add_argument(
        "--invoicePath",
        required=True,
        help="Path to PDF invoice file to process"
    )
    parser.add_argument(
        "--outputDir",
        help="Directory to save output files (defaults to same directory as script)"
    )
    
    args = parser.parse_args()
    pdf_path = args.invoicePath
    output_dir = args.outputDir
    
    try:
        results = extract_tables_to_csv(pdf_path, output_dir)
        
        print("\n" + "="*50)
        print("EXTRACTION SUMMARY")
        print("="*50)
        print(f"PDF File: {results['pdf_file']}")
        print(f"Total Tables Found: {results['total_tables']}")
        
        if results['tables_info']:
            print("\nTable Details:")
            for info in results['tables_info']:
                print(f"  Table {info['table_number']}: {info['rows']} rows × {info['columns']} columns")
        
        if results['output_files']:
            print(f"\nOutput Files Created: {len(results['output_files'])}")
            for file_path in results['output_files']:
                print(f"  - {Path(file_path).name}")
        
        print(f"\nSummary: {Path(results['summary_file']).name}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()