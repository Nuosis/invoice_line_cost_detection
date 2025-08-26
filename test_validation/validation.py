#!/usr/bin/env python3
"""
Complete Invoice Validation Pipeline Script

Runs the complete validation pipeline using the new InvoiceProcessor:
1. PDF Extraction - Extract line items and metadata from PDF invoice(s)
2. Part Discovery - Discover unknown parts and optionally add to database
3. Validation - Validate parts against database with rate checking
4. Report Generation - Generate validation reports in TXT, CSV, and JSON formats

This script can process either a single PDF invoice or an entire directory of invoices.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to the path so we can import from processing
sys.path.append(str(Path(__file__).parent.parent))

from processing.invoice_processor import InvoiceProcessor, ProcessingResult, BatchProcessingResult
from database.database import DatabaseManager


def create_logger() -> logging.Logger:
    """Create a logger for the validation pipeline."""
    logger = logging.getLogger('validate_report')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def progress_callback(current: int, total: int, message: str):
    """Progress callback for CLI progress reporting."""
    percentage = (current / total) * 100 if total > 0 else 0
    print(f"Progress: {current}/{total} ({percentage:.1f}%) - {message}")


def process_single_file(input_path: Path, db_manager: DatabaseManager, logger: logging.Logger) -> ProcessingResult:
    """
    Process a single PDF file using InvoiceProcessor.
    
    Args:
        input_path: Path to PDF file
        db_manager: Database manager instance
        logger: Logger instance
        
    Returns:
        ProcessingResult with processing details
    """
    logger.info(f"Processing single file: {input_path}")
    
    # Create invoice processor
    processor = InvoiceProcessor(
        database_manager=db_manager,
        logger=logger
    )
    
    # Process the file
    result = processor.process_single_invoice(input_path)
    
    return result


def process_directory(input_path: Path, db_manager: DatabaseManager, logger: logging.Logger, output_dir: Path) -> BatchProcessingResult:
    """
    Process a directory of PDF files using InvoiceProcessor.
    
    Args:
        input_path: Path to directory
        db_manager: Database manager instance
        logger: Logger instance
        output_dir: Output directory for batch reports
        
    Returns:
        BatchProcessingResult with aggregated results
    """
    logger.info(f"Processing directory: {input_path}")
    
    # Create invoice processor with progress callback
    processor = InvoiceProcessor(
        database_manager=db_manager,
        progress_callback=progress_callback,
        logger=logger
    )
    
    # Process the directory with output path for batch reports
    result = processor.process_directory(input_path, output_path=output_dir)
    
    return result


def generate_reports_from_result(result, output_dir: Path, base_name: str, logger: logging.Logger) -> Dict[str, Path]:
    """
    Generate reports from processing result.
    
    Args:
        result: ProcessingResult or BatchProcessingResult
        output_dir: Directory to save reports
        base_name: Base name for output files
        logger: Logger instance
        
    Returns:
        Dictionary mapping format to output file path
    """
    logger.info("Generating validation reports")
    
    # Create invoice processor for report generation
    processor = InvoiceProcessor(
        database_manager=None,  # Not needed for report generation
        logger=logger
    )
    
    # Determine which validation JSON to use
    if isinstance(result, ProcessingResult):
        validation_json = result.validation_json
    elif isinstance(result, BatchProcessingResult):
        validation_json = result.aggregated_validation_json
    else:
        raise ValueError(f"Unsupported result type: {type(result)}")
    
    if not validation_json:
        logger.warning("No validation data available for report generation")
        return {}
    
    # Generate reports
    return processor.generate_reports(validation_json, output_dir, base_name)


def main():
    """Main function - run complete validation pipeline using InvoiceProcessor."""
    parser = argparse.ArgumentParser(
        description="Run complete invoice validation pipeline using InvoiceProcessor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validation.py --invoicePath docs/invoices/5790265776.pdf
  python validation.py --invoicePath /path/to/invoice.pdf
  python validation.py --invoicePath /path/to/invoices/directory

This script runs the complete validation pipeline using the new InvoiceProcessor:
1. PDF Extraction - Extract line items and metadata from PDF(s)
2. Part Discovery - Discover unknown parts (non-interactive mode)
3. Validation - Validate parts against database
4. Report Generation - Generate TXT, CSV, and JSON reports

Supports both single files and directories of PDF invoices.
Output files: <<name>>_validation.txt, <<name>>_validation.csv, <<name>>_validation.json
        """
    )
    parser.add_argument(
        "--invoicePath",
        required=True,
        help="Path to PDF invoice file or directory containing PDF invoices"
    )
    
    args = parser.parse_args()
    logger = create_logger()
    
    # Validate input path
    input_path = Path(args.invoicePath)
    if not input_path.exists():
        logger.error(f"Input path not found: {input_path}")
        return 1
    
    # Determine if it's a file or directory
    is_single_file = input_path.is_file()
    is_directory = input_path.is_dir()
    
    if is_single_file and not input_path.suffix.lower() == '.pdf':
        logger.error(f"File is not a PDF: {input_path}")
        return 1
    
    if not is_single_file and not is_directory:
        logger.error(f"Input path must be a PDF file or directory: {input_path}")
        return 1
    
    # Set up output directory
    test_validation_dir = Path(__file__).parent
    output_dir = test_validation_dir / "expectations"
    output_dir.mkdir(exist_ok=True)
    
    logger.info(f"Starting validation pipeline for: {input_path}")
    logger.info(f"Processing mode: {'Single file' if is_single_file else 'Directory'}")
    logger.info(f"Output directory: {output_dir}")
    
    try:
        # Initialize database manager
        logger.info("Initializing database manager")
        db_path = test_validation_dir / "validation.db"
        logger.info(f"Using database: {db_path}")
        db_manager = DatabaseManager(str(db_path))
        
        # Process based on input type
        if is_single_file:
            # Process single file
            result = process_single_file(input_path, db_manager, logger)
            
            if result.success:
                # Generate reports for single file
                base_name = input_path.stem
                output_files = generate_reports_from_result(result, output_dir, f"{base_name}_validation", logger)
                
                # Print summary
                print(f"\nValidation Pipeline Results:")
                print(f"  Input File: {input_path}")
                print(f"  Invoice: {result.invoice_number or 'Unknown'}")
                print(f"  Processing Time: {result.processing_time:.2f}s")
                print(f"  Line Items: {result.line_items_count}")
                print(f"  Unknown Parts: {result.unknown_parts_found}")
                print(f"  Validation Errors: {result.validation_errors}")
                
                if output_files:
                    print(f"\nGenerated Reports:")
                    for format_name, file_path in output_files.items():
                        file_size = file_path.stat().st_size
                        print(f"  {format_name.upper()}: {file_path} ({file_size} bytes)")
                
                logger.info("Single file processing completed successfully!")
                return 0
            else:
                logger.error(f"Processing failed: {result.error_message}")
                return 1
        
        else:
            # Process directory
            result = process_directory(input_path, db_manager, logger, output_dir)
            
            # Generate reports for batch processing (already generated by InvoiceProcessor)
            if result.successful_files > 0:
                # Reports are already generated by InvoiceProcessor, just get the file paths
                output_files = result.report_files
                
                # Print summary
                print(f"\nBatch Processing Results:")
                print(f"  Input Directory: {input_path}")
                print(f"  Total Files: {result.total_files}")
                print(f"  Successful: {result.successful_files}")
                print(f"  Failed: {result.failed_files}")
                print(f"  Processing Time: {result.total_processing_time:.2f}s")
                print(f"  Total Line Items: {result.total_line_items}")
                print(f"  Total Unknown Parts: {result.total_unknown_parts}")
                print(f"  Total Validation Errors: {result.total_validation_errors}")
                
                if output_files:
                    print(f"\nGenerated Reports:")
                    for format_name, file_path in output_files.items():
                        file_size = file_path.stat().st_size
                        print(f"  {format_name.upper()}: {file_path} ({file_size} bytes)")
                
                # Show individual file results
                if result.failed_files > 0:
                    print(f"\nFailed Files:")
                    for processing_result in result.processing_results:
                        if not processing_result.success:
                            print(f"  ❌ {processing_result.invoice_path}: {processing_result.error_message}")
                
                logger.info("Directory processing completed!")
                return 0 if result.failed_files == 0 else 1
            else:
                logger.error("No files were processed successfully")
                return 1
        
    except Exception as e:
        logger.error(f"Error during validation pipeline: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1
    finally:
        # Clean up database connection
        if 'db_manager' in locals():
            db_manager.close()


if __name__ == "__main__":
    sys.exit(main())