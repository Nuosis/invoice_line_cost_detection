"""
Invoice Processor - Main orchestrator for invoice processing workflows.

This module provides the main InvoiceProcessor class that serves as the bridge
between the CLI and the processing engine. It handles both single file and
directory processing with interactive mode support.

Key Features:
- Single file and directory batch processing
- Human-in-the-loop for unknown parts during line processing
- CLI progress reporting for batch operations
- Comprehensive error handling and recovery
- Integration with all existing processing components

Usage Examples:

    # Basic single file processing
    from processing.invoice_processor import InvoiceProcessor
    from database.database import DatabaseManager
    
    db_manager = DatabaseManager("invoices.db")
    processor = InvoiceProcessor(db_manager)
    result = processor.process_single_invoice("invoice.pdf")
    
    # Directory processing with progress callback
    def progress_callback(current, total, message):
        print(f"Progress: {current}/{total} - {message}")
    
    processor = InvoiceProcessor(db_manager, progress_callback=progress_callback)
    batch_result = processor.process_directory("/path/to/invoices")
    
    # Interactive mode for unknown parts discovery
    processor = InvoiceProcessor(db_manager, interactive_mode=True)
    result = processor.process_with_discovery("invoice.pdf")
    
    # Convenience functions for quick processing
    from processing.invoice_processor import process_single_file, process_directory_batch
    
    # Process single file
    result = process_single_file("invoice.pdf", db_manager)
    
    # Process directory with progress reporting
    batch_result = process_directory_batch(
        "/path/to/invoices",
        db_manager,
        progress_callback=progress_callback
    )
    
    # Generate reports from results
    processor = InvoiceProcessor(db_manager)
    if result.success:
        reports = processor.generate_reports(
            result.validation_json,
            Path("./reports"),
            "invoice_validation"
        )
        # reports = {'json': Path, 'txt': Path, 'csv': Path}

CLI Integration Examples:

    # Using the updated validation.py script
    
    # Process single PDF file
    python validation.py --invoicePath /path/to/invoice.pdf
    
    # Process entire directory of PDFs
    python validation.py --invoicePath /path/to/invoices/
    
    # Both modes support:
    # - Automatic PDF discovery in directories
    # - Progress reporting for batch operations
    # - Human-in-the-loop for unknown parts (when interactive_mode=True)
    # - Comprehensive error handling and recovery
    # - Multiple report formats (JSON, TXT, CSV)

Architecture:

    The InvoiceProcessor orchestrates the complete workflow:
    
    1. PDF Processing (PDFProcessor)
       - Text extraction using pdfplumber
       - Table-based line item extraction
       - Invoice metadata parsing
    
    2. Part Discovery (SimplePartDiscoveryService)
       - Unknown part identification
       - Interactive prompts for new parts
       - Database integration for part storage
    
    3. Validation (ValidationEngine)
       - Parts validation against database
       - Rate checking and error detection
       - Comprehensive validation reporting
    
    4. Report Generation (SimpleReportGenerator)
       - Multiple format support (JSON, TXT, CSV)
       - Batch aggregation for directory processing
       - Detailed error and summary reporting

Error Handling:

    The processor provides comprehensive error handling:
    
    - Individual file failures don't stop batch processing
    - Detailed error messages with context
    - Processing time tracking for performance monitoring
    - Graceful degradation when components fail
    - Clean database connection management
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import time

from .pdf_processor import PDFProcessor
from .validation_engine import ValidationEngine
from .part_discovery import SimplePartDiscoveryService
from .report_generator import SimpleReportGenerator
from .exceptions import PDFProcessingError
from .report_utils import get_documents_directory, get_report_summary_message
from database.database import DatabaseManager


@dataclass
class ProcessingResult:
    """Result of processing a single invoice."""
    success: bool
    invoice_path: str
    invoice_number: Optional[str] = None
    extraction_json: Optional[Dict[str, Any]] = None
    validation_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    processing_time: float = 0.0
    line_items_count: int = 0
    unknown_parts_found: int = 0
    validation_errors: int = 0


@dataclass
class BatchProcessingResult:
    """Result of processing multiple invoices."""
    total_files: int
    successful_files: int
    failed_files: int
    processing_results: List[ProcessingResult] = field(default_factory=list)
    aggregated_validation_json: Optional[Dict[str, Any]] = None
    total_processing_time: float = 0.0
    total_line_items: int = 0
    total_unknown_parts: int = 0
    total_validation_errors: int = 0
    report_files: Dict[str, Path] = field(default_factory=dict)


class InvoiceProcessor:
    """
    Main orchestrator for invoice processing workflows.
    
    This class serves as the bridge between the CLI and the processing engine,
    handling both single file and directory processing with interactive mode support.
    """
    
    def __init__(self, 
                 database_manager: DatabaseManager,
                 interactive_mode: bool = False,
                 progress_callback: Optional[Callable[[int, int, str], None]] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the invoice processor.
        
        Args:
            database_manager: Database manager for parts operations
            interactive_mode: Enable human-in-the-loop for unknown parts
            progress_callback: Callback function for progress updates (current, total, message)
            logger: Optional logger instance
        """
        self.db_manager = database_manager
        self.interactive_mode = interactive_mode
        self.progress_callback = progress_callback
        self.logger = logger or self._create_default_logger()
        
        # Initialize processing components
        self.pdf_processor = PDFProcessor(self.logger)
        self.validation_engine = ValidationEngine(self.db_manager, self.interactive_mode)
        self.discovery_service = SimplePartDiscoveryService(self.db_manager, self.interactive_mode)
        self.report_generator = SimpleReportGenerator()
        
        # Processing statistics
        self.reset_statistics()
    
    def _create_default_logger(self) -> logging.Logger:
        """Create a default logger for invoice processing."""
        logger = logging.getLogger('invoice_processor')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def reset_statistics(self):
        """Reset processing statistics."""
        self.total_invoices_processed = 0
        self.total_unknown_parts_discovered = 0
        self.total_validation_errors = 0
        self.total_line_items_processed = 0
    
    def process_single_invoice(self, 
                             file_path: Union[str, Path], 
                             output_path: Optional[Union[str, Path]] = None) -> ProcessingResult:
        """
        Process a single invoice file through the complete pipeline.
        
        Args:
            file_path: Path to the PDF invoice file
            output_path: Optional output directory for reports
            
        Returns:
            ProcessingResult with processing details and results
        """
        file_path = Path(file_path)
        start_time = time.time()
        
        result = ProcessingResult(
            success=False,
            invoice_path=str(file_path),
            processing_time=0.0
        )
        
        try:
            self.logger.info(f"Processing single invoice: {file_path}")
            
            # Step 1: Extract data from PDF
            extraction_json = self._extract_invoice_data(file_path)
            result.extraction_json = extraction_json
            result.invoice_number = extraction_json.get('invoice_metadata', {}).get('invoice_number')
            result.line_items_count = len(extraction_json.get('parts', []))
            
            # Step 2: Discover unknown parts (with human-in-the-loop if enabled)
            extraction_json = self._discover_parts(extraction_json)
            
            # Step 3: Validate against database
            validation_json = self._validate_invoice(extraction_json)
            result.validation_json = validation_json
            
            # Update statistics
            result.unknown_parts_found = validation_json.get('validation_summary', {}).get('unknown_parts', 0)
            result.validation_errors = validation_json.get('validation_summary', {}).get('failed_parts', 0)
            
            # Mark as successful
            result.success = True
            result.processing_time = time.time() - start_time
            
            self.logger.info(f"Successfully processed invoice {result.invoice_number}")
            
        except Exception as e:
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.processing_time = time.time() - start_time
            
            self.logger.error(f"Error processing invoice {file_path}: {e}")
            
            # Don't re-raise - let caller handle the error result
        
        return result
    
    def process_directory(self, 
                         input_dir: Union[str, Path],
                         output_path: Optional[Union[str, Path]] = None,
                         recursive: bool = True) -> BatchProcessingResult:
        """
        Process all PDF invoices in a directory.
        
        Args:
            input_dir: Directory containing PDF invoices
            output_path: Optional output directory for reports
            recursive: Whether to search subdirectories
            
        Returns:
            BatchProcessingResult with aggregated results and reports
        """
        input_dir = Path(input_dir)
        start_time = time.time()
        
        self.logger.info(f"Starting directory processing: {input_dir}")
        
        # Find all PDF files
        pdf_files = self._find_pdf_files(input_dir, recursive)
        
        if not pdf_files:
            self.logger.warning(f"No PDF files found in {input_dir}")
            return BatchProcessingResult(
                total_files=0,
                successful_files=0,
                failed_files=0,
                total_processing_time=time.time() - start_time
            )
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Initialize batch result
        batch_result = BatchProcessingResult(
            total_files=len(pdf_files),
            successful_files=0,
            failed_files=0
        )
        
        # Process each file
        all_validation_results = []
        
        for i, pdf_file in enumerate(pdf_files, 1):
            # Update progress
            if self.progress_callback:
                self.progress_callback(i, len(pdf_files), f"Processing {pdf_file.name}")
            
            # Process single invoice
            result = self.process_single_invoice(pdf_file, output_path)
            batch_result.processing_results.append(result)
            
            # Update batch statistics
            if result.success:
                batch_result.successful_files += 1
                batch_result.total_line_items += result.line_items_count
                batch_result.total_unknown_parts += result.unknown_parts_found
                batch_result.total_validation_errors += result.validation_errors
                
                # Collect validation results for aggregation
                if result.validation_json:
                    all_validation_results.append(result.validation_json)
            else:
                batch_result.failed_files += 1
            
            self.logger.info(f"Processed {i}/{len(pdf_files)}: {pdf_file.name} "
                           f"({'SUCCESS' if result.success else 'FAILED'})")
        
        # Generate individual reports for each invoice AND batch reports
        if output_path:
            output_path = Path(output_path)
            
            # Generate individual reports for each successful invoice
            for result in batch_result.processing_results:
                if result.success and result.validation_json:
                    invoice_base_name = Path(result.invoice_path).stem
                    individual_reports = self.generate_reports(
                        result.validation_json,
                        output_path,
                        f"{invoice_base_name}_validation"
                    )
                    self.logger.info(f"Generated individual reports for {invoice_base_name}: {list(individual_reports.keys())}")
            
            # Generate consolidated batch reports
            if all_validation_results:
                batch_result.aggregated_validation_json = self._create_batch_validation_json(all_validation_results)
                batch_result.report_files = self._generate_batch_reports(
                    batch_result.aggregated_validation_json,
                    output_path
                )
        
        batch_result.total_processing_time = time.time() - start_time
        
        self.logger.info(f"Directory processing complete: {batch_result.successful_files}/{batch_result.total_files} successful")
        
        return batch_result
    
    def process_with_discovery(self, 
                             input_path: Union[str, Path],
                             output_path: Optional[Union[str, Path]] = None) -> Union[ProcessingResult, BatchProcessingResult]:
        """
        Process with interactive part discovery enabled.
        
        This is a convenience method that enables interactive mode and processes
        either a single file or directory based on the input path.
        
        Args:
            input_path: Path to PDF file or directory
            output_path: Optional output directory for reports
            
        Returns:
            ProcessingResult for single file or BatchProcessingResult for directory
        """
        # Temporarily enable interactive mode
        original_interactive_mode = self.interactive_mode
        self.interactive_mode = True
        
        # Update discovery service to interactive mode
        self.discovery_service = SimplePartDiscoveryService(self.db_manager, True)
        self.validation_engine = ValidationEngine(self.db_manager, True)
        
        try:
            input_path = Path(input_path)
            
            if input_path.is_file():
                return self.process_single_invoice(input_path, output_path)
            elif input_path.is_dir():
                return self.process_directory(input_path, output_path)
            else:
                raise ValueError(f"Input path does not exist: {input_path}")
        
        finally:
            # Restore original interactive mode
            self.interactive_mode = original_interactive_mode
            self.discovery_service = SimplePartDiscoveryService(self.db_manager, original_interactive_mode)
            self.validation_engine = ValidationEngine(self.db_manager, original_interactive_mode)
    
    def generate_reports(self,
                        validation_json: Dict[str, Any],
                        output_dir: Optional[Path] = None,
                        base_name: str = "validation_report",
                        auto_open: bool = True,
                        preferred_format: str = "csv",
                        generate_all_formats: bool = True) -> Dict[str, Path]:
        """
        Generate validation reports in multiple formats.
        
        Args:
            validation_json: Validation results to generate reports from
            output_dir: Directory to save reports (MUST be provided - no default fallback)
            base_name: Base name for report files
            auto_open: Whether to automatically open the generated reports
            preferred_format: Preferred format for auto-opening (default: "csv")
            generate_all_formats: Whether to generate all formats or just the preferred one
            
        Returns:
            Dictionary mapping format to output file path
        """
        # CRITICAL: Use the provided output_dir, don't fallback to documents directory
        # This ensures files go to the user's selected location
        if output_dir is None:
            # This should not happen in normal operation - CLI should always provide path
            self.logger.warning("No output directory provided, using current working directory")
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)
        
        # Ensure the output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Using output directory: {output_dir}")
        
        # Generate reports with new parameters - PASS THE EXACT PATH
        reports = self.report_generator.generate_reports(
            validation_json,
            output_base_path=str(output_dir),  # This is the user's selected path
            auto_open=auto_open,
            preferred_format=preferred_format,
            generate_all_formats=generate_all_formats
        )
        
        # The report generator now handles file writing and auto-opening
        # Return the actual file paths from the report generator
        invoice_num = validation_json.get('invoice_metadata', {}).get('invoice_number')
        if not invoice_num or invoice_num.lower() == 'unknown':
            base_name = "report"
        else:
            base_name = invoice_num
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        date_folder = datetime.now().strftime('%Y%m%d')
        
        # Build paths that match the report generator's structure
        output_files = {}
        if generate_all_formats or preferred_format == 'json':
            output_files['json'] = output_dir / date_folder / f"{base_name}_validation_{timestamp}.json"
        if generate_all_formats or preferred_format == 'txt':
            output_files['txt'] = output_dir / date_folder / f"{base_name}_report_{timestamp}.txt"
        if generate_all_formats or preferred_format == 'csv':
            output_files['csv'] = output_dir / date_folder / f"{base_name}_analysis_{timestamp}.csv"
        
        self.logger.info(f"Generated reports in directory: {output_dir / date_folder}")
        return output_files
    
    def _extract_invoice_data(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Step 1: Extract data from PDF invoice.
        
        Args:
            pdf_path: Path to PDF invoice file
            
        Returns:
            Extraction JSON with invoice metadata and parts data
        """
        self.logger.debug("Step 1: Extracting data from PDF invoice")
        
        # Process the PDF to get structured data
        invoice_data = self.pdf_processor.process_pdf(pdf_path)
        
        # Convert to extraction JSON format expected by validation engine
        extraction_json = {
            'invoice_metadata': {
                'invoice_number': invoice_data.invoice_number,
                'invoice_date': invoice_data.invoice_date,
                'customer_number': invoice_data.customer_number,
                'customer_name': invoice_data.customer_name,
                'total_line_items': len(invoice_data.line_items),
                'pdf_path': str(pdf_path),
                'extraction_timestamp': invoice_data.extraction_timestamp.isoformat() if invoice_data.extraction_timestamp else None
            },
            'format_sections': [section.to_dict() for section in invoice_data.format_sections],
            'parts': []
        }
        
        # Convert line items to parts format
        for line_item in invoice_data.line_items:
            if line_item.is_valid():
                part_data = {
                    'database_fields': {
                        'part_number': line_item.item_code,
                        'authorized_price': float(line_item.rate) if line_item.rate else None,
                        'description': line_item.description,
                        'item_type': line_item.item_type,
                        'category': None,  # Will be determined by database lookup
                        'source': 'extracted',
                        'first_seen_invoice': invoice_data.invoice_number
                    },
                    'lineitem_fields': {
                        'line_number': line_item.line_number,
                        'quantity': line_item.quantity,
                        'total': float(line_item.total) if line_item.total else None,
                        'raw_text': line_item.raw_text
                    }
                }
                extraction_json['parts'].append(part_data)
        
        self.logger.debug(f"Extracted {len(extraction_json['parts'])} valid parts from invoice {invoice_data.invoice_number}")
        return extraction_json
    
    def _discover_parts(self, extraction_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Discover unknown parts and optionally add to database.
        
        Args:
            extraction_json: Extraction data from step 1
            
        Returns:
            Same extraction JSON (discovery service doesn't modify it)
        """
        self.logger.debug("Step 2: Discovering unknown parts")
        
        # Discover and process unknown parts
        result_json = self.discovery_service.discover_and_add_parts(extraction_json)
        
        self.logger.debug("Part discovery completed")
        return result_json
    
    def _validate_invoice(self, extraction_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Validate parts against database.
        
        Args:
            extraction_json: Extraction data from previous steps
            
        Returns:
            Validation JSON with error_lines and validation_summary
        """
        self.logger.debug("Step 3: Validating parts against database")
        
        # Validate the invoice
        validation_json = self.validation_engine.validate_invoice_json(extraction_json)
        
        summary = validation_json.get('validation_summary', {})
        self.logger.debug(f"Validation completed: {summary.get('passed_parts', 0)} passed, "
                         f"{summary.get('failed_parts', 0)} failed, "
                         f"{summary.get('unknown_parts', 0)} unknown")
        
        return validation_json
    
    def _find_pdf_files(self, directory: Path, recursive: bool = True) -> List[Path]:
        """
        Find all PDF files in a directory.
        
        Args:
            directory: Directory to search
            recursive: Whether to search subdirectories
            
        Returns:
            List of PDF file paths
        """
        pdf_files = []
        
        if recursive:
            # Use rglob for recursive search
            pdf_files = list(directory.rglob("*.pdf"))
            pdf_files.extend(list(directory.rglob("*.PDF")))
        else:
            # Use glob for non-recursive search
            pdf_files = list(directory.glob("*.pdf"))
            pdf_files.extend(list(directory.glob("*.PDF")))
        
        # Remove duplicates and sort
        pdf_files = sorted(list(set(pdf_files)))
        
        return pdf_files
    
    def _create_batch_validation_json(self, validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create batch validation JSON with array of invoice objects (not merged).
        
        Args:
            validation_results: List of validation JSON results
            
        Returns:
            Batch validation JSON with invoices array and merged parts/error_lines for CSV
        """
        if not validation_results:
            return {}
        
        # Calculate batch summary
        batch_summary = {
            'total_parts': 0,
            'passed_parts': 0,
            'failed_parts': 0,
            'unknown_parts': 0,
            'total_invoices': len(validation_results)
        }
        
        # Collect ALL parts and error lines from all invoices for batch CSV
        all_parts = []
        all_error_lines = []
        
        for validation_json in validation_results:
            summary = validation_json.get('validation_summary', {})
            batch_summary['total_parts'] += summary.get('total_parts', 0)
            batch_summary['passed_parts'] += summary.get('passed_parts', 0)
            batch_summary['failed_parts'] += summary.get('failed_parts', 0)
            batch_summary['unknown_parts'] += summary.get('unknown_parts', 0)
            
            # Collect ALL parts from this invoice for the merged batch CSV
            parts = validation_json.get('parts', [])
            all_parts.extend(parts)
            
            # Collect ALL error lines from this invoice for the merged batch CSV
            error_lines = validation_json.get('error_lines', [])
            all_error_lines.extend(error_lines)
        
        # Create batch validation JSON structure
        batch_validation = {
            'batch_metadata': {
                'total_invoices': len(validation_results),
                'processing_timestamp': datetime.now().isoformat(),
                'batch_type': 'directory_processing'
            },
            'batch_summary': batch_summary,
            'invoices': validation_results,  # Array of complete invoice validation objects (each with their own error_lines)
            'parts': all_parts,  # ALL parts from ALL invoices merged for CSV generation
            'error_lines': all_error_lines,  # ALL error lines from ALL invoices merged for CSV generation
            'validation_summary': batch_summary  # For compatibility with report generator
        }
        
        return batch_validation
    
    def _aggregate_validation_results(self, validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Legacy method - kept for compatibility. Use _create_batch_validation_json instead.
        """
        return self._create_batch_validation_json(validation_results)
    
    def _generate_batch_reports(self, aggregated_validation_json: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
        """
        Generate batch reports for aggregated validation results.
        
        Args:
            aggregated_validation_json: Aggregated validation results
            output_dir: Directory to save reports
            
        Returns:
            Dictionary mapping format to output file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"batch_validation_report_{timestamp}"
        
        return self.generate_reports(aggregated_validation_json, output_dir, base_name)


# Convenience functions for CLI integration
def create_invoice_processor(database_manager: DatabaseManager, 
                           interactive_mode: bool = False,
                           progress_callback: Optional[Callable[[int, int, str], None]] = None) -> InvoiceProcessor:
    """
    Create an InvoiceProcessor instance with standard configuration.
    
    Args:
        database_manager: Database manager instance
        interactive_mode: Enable interactive part discovery
        progress_callback: Optional progress callback for CLI
        
    Returns:
        Configured InvoiceProcessor instance
    """
    return InvoiceProcessor(
        database_manager=database_manager,
        interactive_mode=interactive_mode,
        progress_callback=progress_callback
    )


def process_single_file(pdf_path: Union[str, Path],
                       database_manager: DatabaseManager,
                       output_path: Optional[Union[str, Path]] = None,
                       interactive_mode: bool = False) -> ProcessingResult:
    """
    Convenience function to process a single PDF file.
    
    Args:
        pdf_path: Path to PDF file
        database_manager: Database manager instance
        output_path: Optional output directory
        interactive_mode: Enable interactive part discovery
        
    Returns:
        ProcessingResult with processing details
    """
    processor = create_invoice_processor(database_manager, interactive_mode)
    return processor.process_single_invoice(pdf_path, output_path)


def process_directory_batch(input_dir: Union[str, Path],
                          database_manager: DatabaseManager,
                          output_path: Optional[Union[str, Path]] = None,
                          interactive_mode: bool = False,
                          recursive: bool = True,
                          progress_callback: Optional[Callable[[int, int, str], None]] = None) -> BatchProcessingResult:
    """
    Convenience function to process a directory of PDF files.
    
    Args:
        input_dir: Directory containing PDF files
        database_manager: Database manager instance
        output_path: Optional output directory
        interactive_mode: Enable interactive part discovery
        recursive: Search subdirectories
        progress_callback: Optional progress callback for CLI
        
    Returns:
        BatchProcessingResult with aggregated results
    """
    processor = create_invoice_processor(database_manager, interactive_mode, progress_callback)
    return processor.process_directory(input_dir, output_path, recursive)