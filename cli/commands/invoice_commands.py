"""
Invoice processing commands for the CLI interface.

This module implements all invoice-related commands including:
- process: Main invoice processing with parts-based validation
- batch: Batch processing of multiple folders
- interactive: Guided interactive processing
- collect-unknowns: Collect unknown parts without validation
"""

import uuid
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from decimal import Decimal

import click

from cli.context import pass_context
from cli.validators import PART_NUMBER, PRICE, OUTPUT_FORMAT
from cli.formatters import (
    print_success, print_warning, print_error, print_info,
    format_table, write_csv, display_summary
)
from cli.progress import show_file_progress, MultiStepProgress
from cli.prompts import (
    prompt_for_input_path, prompt_for_output_path, prompt_for_output_format,
    prompt_for_validation_mode, prompt_for_threshold, show_welcome_message,
    show_processing_summary, prompt_for_next_action, prompt_for_choice
)
from cli.exceptions import CLIError, ProcessingError, UserCancelledError
from database.models import Part, PartDiscoveryLog, DatabaseError, ValidationError
from processing.validation_integration import (
    create_validation_workflow, format_validation_summary
)
from processing.validation_models import ValidationConfiguration


logger = logging.getLogger(__name__)


# Create invoice command group
@click.group(name='invoice')
def invoice_group():
    """Invoice processing commands."""
    pass


@invoice_group.command()
@click.argument('input_path', type=click.Path(exists=True), required=False)
@click.option('--output', '-o', type=click.Path(), default='report.csv',
              help='Output report file path')
@click.option('--format', '-f', type=OUTPUT_FORMAT, default='csv',
              help='Output format (csv, txt, json)')
@click.option('--interactive', '-i', is_flag=True,
              help='Enable interactive part discovery')
@click.option('--collect-unknown', is_flag=True,
              help='Collect unknown parts for later review')
@click.option('--session-id', type=str,
              help='Custom processing session ID')
@click.option('--validation-mode', type=click.Choice(['parts_based', 'threshold_based']),
              default='parts_based', help='Validation mode')
@click.option('--threshold', '-t', type=PRICE, default=Decimal('0.30'),
              help='Threshold for threshold-based mode')
@pass_context
def process(ctx, input_path, output, format, interactive, collect_unknown,
           session_id, validation_mode, threshold):
    """
    Process invoices with parts-based validation (primary command).
    
    This command processes either a single PDF invoice file or a folder
    containing multiple PDF invoices, detecting pricing anomalies using
    the master parts database.
    
    Examples:
        # Process a single PDF file
        invoice-checker process invoice.pdf --output single_report.csv
        
        # Process a folder with interactive discovery
        invoice-checker process ./invoices --interactive
        
        # Collect unknown parts without validation
        invoice-checker process ./invoices --collect-unknown
        
        # Threshold-based processing for legacy mode
        invoice-checker process invoice.pdf --threshold 0.25 --validation-mode threshold_based
    """
    try:
        # Get input path if not provided
        if not input_path:
            input_path = prompt_for_input_path()
        else:
            input_path = Path(input_path)
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get database manager
        db_manager = ctx.get_db_manager()
        
        # Process invoices
        results = _process_invoices(
            input_path=input_path,
            output_path=Path(output),
            output_format=format,
            validation_mode=validation_mode,
            threshold=threshold,
            interactive=interactive,
            collect_unknown=collect_unknown,
            session_id=session_id,
            db_manager=db_manager
        )
        
        # Display results
        display_summary("Processing Results", results)
        print_success(f"Processing complete! Report saved to: {output}")
        
    except UserCancelledError:
        print_info("Processing cancelled by user.")
    except Exception as e:
        logger.exception("Processing failed")
        raise CLIError(f"Processing failed: {e}")


@invoice_group.command()
@click.argument('input_path', type=click.Path(exists=True), required=True)
@click.option('--output-dir', '-o', type=click.Path(), default='./reports',
              help='Output directory for reports')
@click.option('--parallel', '-p', is_flag=True,
              help='Enable parallel processing')
@click.option('--max-workers', type=int, default=4,
              help='Maximum worker threads')
@click.option('--continue-on-error', is_flag=True,
              help='Continue processing if individual folders fail')
@pass_context
def batch(ctx, input_path, output_dir, parallel, max_workers, continue_on_error):
    """
    Process multiple invoice folders in batch mode.
    
    This command processes multiple folders containing invoices,
    generating separate reports for each folder.
    
    Examples:
        # Process all folders in a directory
        invoice-checker batch ./invoice_folders --parallel
        
        # Process with custom output directory
        invoice-checker batch ./invoices --output-dir ./batch_reports
    """
    try:
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all subdirectories containing PDF files
        folders_to_process = _find_invoice_folders(input_path)
        
        if not folders_to_process:
            raise CLIError(f"No folders with PDF files found in {input_path}")
        
        print_info(f"Found {len(folders_to_process)} folders to process")
        
        # Get database manager
        db_manager = ctx.get_db_manager()
        
        # Process folders
        results = _process_batch(
            folders=folders_to_process,
            output_dir=output_dir,
            parallel=parallel,
            max_workers=max_workers,
            continue_on_error=continue_on_error,
            db_manager=db_manager
        )
        
        # Display batch results
        display_summary("Batch Processing Results", results)
        print_success(f"Batch processing complete! Reports saved to: {output_dir}")
        
    except Exception as e:
        logger.exception("Batch processing failed")
        raise CLIError(f"Batch processing failed: {e}")


@invoice_group.command()
@click.option('--preset', type=str, help='Use predefined settings preset')
@click.option('--save-preset', type=str, help='Save current settings as preset')
@pass_context
def interactive(ctx, preset, save_preset):
    """
    Guided interactive processing with prompts.
    
    This command provides a user-friendly interactive workflow
    for non-technical users to process invoices step-by-step.
    
    Examples:
        # Start interactive mode
        invoice-checker interactive
        
        # Use a saved preset
        invoice-checker interactive --preset quick_scan
    """
    try:
        run_interactive_processing(ctx, preset, save_preset)
    except UserCancelledError:
        print_info("Interactive processing cancelled by user.")
    except Exception as e:
        logger.exception("Interactive processing failed")
        raise CLIError(f"Interactive processing failed: {e}")


@invoice_group.command(name='collect-unknowns')
@click.argument('input_path', type=click.Path(exists=True), required=False)
@click.option('--output', '-o', type=click.Path(), default='unknown_parts.csv',
              help='Output file for unknown parts')
@click.option('--suggest-prices', is_flag=True,
              help='Include price suggestions based on invoice data')
@pass_context
def collect_unknowns(ctx, input_path, output, suggest_prices):
    """
    Process invoices and collect unknown parts without validation.
    
    This command extracts all parts from invoices (single file or folder)
    and identifies which ones are not in the master parts database,
    useful for building the parts database.
    
    Examples:
        # Collect unknown parts from a folder
        invoice-checker collect-unknowns ./invoices
        
        # Collect unknown parts from a single file
        invoice-checker collect-unknowns invoice.pdf
        
        # Include price suggestions
        invoice-checker collect-unknowns ./invoices --suggest-prices
    """
    try:
        # Get input path if not provided
        if not input_path:
            input_path = prompt_for_input_path()
        else:
            input_path = Path(input_path)
        
        # Get database manager
        db_manager = ctx.get_db_manager()
        
        # Collect unknown parts
        results = _collect_unknown_parts(
            input_path=input_path,
            output_path=Path(output),
            suggest_prices=suggest_prices,
            db_manager=db_manager
        )
        
        # Display results
        display_summary("Unknown Parts Collection Results", results)
        print_success(f"Unknown parts saved to: {output}")
        
    except UserCancelledError:
        print_info("Collection cancelled by user.")
    except Exception as e:
        logger.exception("Unknown parts collection failed")
        raise CLIError(f"Unknown parts collection failed: {e}")


def run_interactive_processing(ctx, preset=None, save_preset=None):
    """
    Run the interactive processing workflow.
    
    This function implements the guided workflow for non-technical users,
    prompting for all necessary inputs and providing clear feedback.
    """
    show_welcome_message()
    
    try:
        # Step 1: Get input folder
        print_info("Step 1: Select invoice folder")
        input_path = prompt_for_input_path()
        
        # Check if single file mode was requested
        from cli.prompts import PathWithMetadata
        single_file_mode = isinstance(input_path, PathWithMetadata) and input_path.single_file_mode
        original_file = input_path.original_file if single_file_mode else None
        
        if single_file_mode and original_file:
            print_info(f"Processing single file: {original_file.name}")
            pdf_files = [original_file]
        else:
            # Validate input folder has PDF files
            pdf_files = list(input_path.glob("*.pdf"))
            if not pdf_files:
                print_warning(f"No PDF files found in {input_path}")
                if not click.confirm("Continue anyway?", default=False):
                    raise UserCancelledError()
            else:
                print_info(f"Found {len(pdf_files)} PDF files")
        
        # Step 2: Get output settings
        print_info("Step 2: Configure output")
        output_format = prompt_for_output_format()
        default_output = f"report.{output_format}"
        output_path = prompt_for_output_path(default=default_output)
        
        # Step 3: Select validation mode
        print_info("Step 3: Select validation mode")
        validation_mode = prompt_for_validation_mode()
        
        threshold = None
        if validation_mode == 'threshold_based':
            threshold = prompt_for_threshold()
        
        # Step 4: Configure discovery options
        print_info("Step 4: Configure part discovery")
        interactive_discovery = click.confirm(
            "Enable interactive part discovery?", default=True
        )
        
        # Step 5: Process invoices
        print_info("Step 5: Processing invoices...")
        
        session_id = str(uuid.uuid4())
        db_manager = ctx.get_db_manager()
        
        # Pass the specific files to process if in single file mode
        if single_file_mode and original_file:
            # Create a custom input path that includes the file list
            if isinstance(input_path, PathWithMetadata):
                custom_input = input_path
                custom_input.pdf_files_override = pdf_files
            else:
                # Fallback: create a new PathWithMetadata
                custom_input = PathWithMetadata(input_path)
                custom_input.pdf_files_override = pdf_files
        else:
            custom_input = input_path
            
        results = _process_invoices(
            input_path=custom_input,
            output_path=output_path,
            output_format=output_format,
            validation_mode=validation_mode,
            threshold=threshold or Decimal('0.30'),
            interactive=interactive_discovery,
            collect_unknown=False,
            session_id=session_id,
            db_manager=db_manager
        )
        
        # Step 6: Show results and next actions
        show_processing_summary(results)
        
        unknown_parts = results.get('unknown_parts', 0)
        next_action = prompt_for_next_action(unknown_parts)
        
        if next_action == "Review unknown parts" and unknown_parts > 0:
            _show_unknown_parts_review(session_id, db_manager)
        elif next_action == "Add parts to database" and unknown_parts > 0:
            _interactive_parts_addition(session_id, db_manager)
        elif next_action == "Process more invoices":
            run_interactive_processing(ctx, preset, save_preset)
        
    except UserCancelledError:
        raise
    except Exception as e:
        print_error(f"Interactive processing failed: {e}")
        raise


def _discover_pdf_files(input_path: Path) -> List[Path]:
    """
    Discover PDF files from input path.
    
    Args:
        input_path: Path to file or directory containing PDFs
        
    Returns:
        List of PDF file paths
        
    Raises:
        ProcessingError: If no PDF files are found
    """
    # Check if we have a PDF files override (for single file mode from interactive prompts)
    from cli.prompts import PathWithMetadata
    if isinstance(input_path, PathWithMetadata) and input_path.pdf_files_override:
        pdf_files = input_path.pdf_files_override
        print_info(f"Using specified PDF files: {len(pdf_files)} files to process")
        return pdf_files
    
    # Handle single file input
    if input_path.is_file():
        if input_path.suffix.lower() == '.pdf':
            pdf_files = [input_path]
            print_info(f"Processing single PDF file: {input_path.name}")
        else:
            raise ProcessingError(f"File is not a PDF: {input_path}")
    # Handle directory input
    else:
        pdf_files = list(input_path.glob("*.pdf"))
        if not pdf_files:
            raise ProcessingError(f"No PDF files found in directory: {input_path}")
        print_info(f"Found {len(pdf_files)} PDF files to process in directory: {input_path.name}")
    
    return pdf_files


def _create_validation_config(validation_mode: str, threshold: Decimal,
                            interactive: bool, collect_unknown: bool,
                            db_manager) -> ValidationConfiguration:
    """
    Create validation configuration based on mode and parameters.
    
    Args:
        validation_mode: Validation mode ('parts_based' or 'threshold_based')
        threshold: Price threshold for threshold-based mode
        interactive: Enable interactive part discovery
        collect_unknown: Enable unknown parts collection
        db_manager: Database manager for configuration access
        
    Returns:
        Configured ValidationConfiguration instance
    """
    if validation_mode == 'threshold_based':
        # For threshold-based mode, create a simple configuration
        config = ValidationConfiguration()
        config.validation_mode = 'threshold_based'
        config.threshold_value = threshold
        config.price_discrepancy_warning_threshold = threshold
        config.price_discrepancy_critical_threshold = threshold * 2
        # Disable parts-based features for threshold mode
        config.interactive_discovery = False
        config.batch_collect_unknown_parts = False
    else:
        # Use parts-based validation with database configuration
        config = ValidationConfiguration.from_database_config(db_manager)
        config.validation_mode = 'parts_based'
        config.threshold_value = threshold  # Still store threshold for reference
        # Apply common settings for parts-based mode
        config.interactive_discovery = interactive
        config.batch_collect_unknown_parts = collect_unknown
    
    return config


def _execute_validation_workflow(pdf_files: List[Path], config: ValidationConfiguration,
                               db_manager, interactive: bool, output_path: Path,
                               output_format: str) -> Dict[str, Any]:
    """
    Execute the validation workflow on PDF files.
    
    Args:
        pdf_files: List of PDF file paths to process
        config: Validation configuration
        db_manager: Database manager instance
        interactive: Enable interactive discovery
        output_path: Path for output report
        output_format: Output format ('csv', 'txt', etc.)
        
    Returns:
        Processing results and statistics
    """
    # Create validation workflow
    workflow = create_validation_workflow(db_manager, config)
    
    if len(pdf_files) == 1:
        # Single file processing
        validation_result, discovery_results = workflow.process_single_invoice(
            pdf_files[0], interactive_discovery=interactive
        )
        validation_results = [validation_result]
        
        # Generate report manually for single file - create basic processing stats
        processing_stats = {
            'successfully_processed': 1,
            'failed_processing': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0
        }
        
        report_stats = workflow.report_generator.generate_all_reports(
            validation_results, processing_stats, str(uuid.uuid4()), output_path.parent, str(output_path.parent)
        )
        
        # Get validation summary
        summary = workflow.get_validation_summary(validation_results)
        
        # Display validation summary
        print_info("\n" + format_validation_summary(summary))
        
        return summary
    else:
        # Batch processing - workflow handles report generation
        processing_stats = workflow.process_invoices_batch(
            invoice_paths=pdf_files,
            output_path=output_path,
            report_format=output_format,
            interactive_discovery=interactive
        )
        
        return processing_stats


def _generate_processing_results(validation_results: Dict[str, Any],
                               output_path: Path) -> Dict[str, Any]:
    """
    Generate processing results and statistics in legacy format.
    
    Args:
        validation_results: Results from validation workflow
        output_path: Path to output report file
        
    Returns:
        Processing statistics in legacy format for compatibility
    """
    # Convert to legacy stats format for compatibility
    stats = {
        'files_processed': validation_results.get('successful_validations',
                                                validation_results.get('successfully_processed', 0)),
        'files_failed': validation_results.get('failed_validations',
                                             validation_results.get('failed_processing', 0)),
        'anomalies_found': validation_results.get('total_anomalies', 0),
        'unknown_parts': validation_results.get('unknown_parts_discovered', 0),
        'total_overcharge': Decimal('0.00'),  # Would need to calculate from anomalies
        'report_file': str(output_path),
        'critical_anomalies': validation_results.get('critical_anomalies', 0),
        'warning_anomalies': validation_results.get('warning_anomalies', 0),
        'processing_time': validation_results.get('total_processing_time',
                                                validation_results.get('average_processing_time', 0.0))
    }
    
    return stats


def _process_invoices(input_path: Path, output_path: Path, output_format: str,
                     validation_mode: str, threshold: Decimal, interactive: bool,
                     collect_unknown: bool, session_id: str, db_manager) -> Dict[str, Any]:
    """
    Core invoice processing logic - refactored for better maintainability.
    
    This function orchestrates the complete invoice processing workflow by
    delegating specific responsibilities to focused helper functions.
    
    Args:
        input_path: Path to PDF file or directory containing PDFs
        output_path: Path for output report file
        output_format: Output format ('csv', 'txt', 'json')
        validation_mode: Validation mode ('parts_based' or 'threshold_based')
        threshold: Price threshold for threshold-based validation
        interactive: Enable interactive part discovery
        collect_unknown: Enable unknown parts collection
        session_id: Processing session identifier
        db_manager: Database manager instance
        
    Returns:
        Processing results and statistics
        
    Raises:
        ProcessingError: If processing fails
    """
    print_info("Starting invoice processing...")
    
    try:
        # Step 1: Discover and validate PDF files
        pdf_files = _discover_pdf_files(input_path)
        
        # Step 2: Create validation configuration
        config = _create_validation_config(
            validation_mode, threshold, interactive, collect_unknown, db_manager
        )
        
        # Step 3: Execute validation workflow
        validation_results = _execute_validation_workflow(
            pdf_files, config, db_manager, interactive, output_path, output_format
        )
        
        # Step 4: Generate processing results in legacy format
        return _generate_processing_results(validation_results, output_path)
        
    except Exception as e:
        logger.exception(f"Validation processing failed: {e}")
        raise ProcessingError(f"Invoice processing failed: {e}")


def _process_batch(folders: List[Path], output_dir: Path, parallel: bool,
                  max_workers: int, continue_on_error: bool, db_manager) -> Dict[str, Any]:
    """
    Process multiple folders in batch mode with proper implementation.
    
    This function processes multiple folders containing PDF invoices, generating
    separate reports for each folder. It supports both parallel and sequential
    processing modes with comprehensive error handling.
    
    Args:
        folders: List of folder paths containing PDF files
        output_dir: Directory to write output reports
        parallel: Enable parallel processing
        max_workers: Maximum number of worker threads for parallel processing
        continue_on_error: Continue processing if individual folders fail
        db_manager: Database manager instance
        
    Returns:
        Dictionary containing processing statistics and results
        
    Raises:
        ProcessingError: If batch processing fails critically
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import uuid
    from pathlib import Path
    
    stats = {
        'folders_processed': 0,
        'folders_failed': 0,
        'total_files': 0,
        'total_anomalies': 0,
        'processing_errors': []
    }
    
    def process_single_folder(folder_path: Path) -> Dict[str, Any]:
        """
        Process a single folder and return results.
        
        Args:
            folder_path: Path to folder containing PDF files
            
        Returns:
            Dictionary containing processing results for the folder
        """
        try:
            session_id = str(uuid.uuid4())
            output_file = output_dir / f"{folder_path.name}_report.csv"
            
            logger.info(f"Processing folder: {folder_path}")
            print_info(f"Processing folder: {folder_path.name}")
            
            # Use existing _process_invoices function
            result = _process_invoices(
                input_path=folder_path,
                output_path=output_file,
                output_format='csv',
                validation_mode='parts_based',
                threshold=Decimal('0.30'),
                interactive=False,
                collect_unknown=False,
                session_id=session_id,
                db_manager=db_manager
            )
            
            logger.info(f"Successfully processed folder {folder_path}: {result.get('files_processed', 0)} files")
            
            return {
                'folder': folder_path,
                'success': True,
                'result': result,
                'error': None
            }
            
        except Exception as e:
            logger.exception(f"Failed to process folder {folder_path}")
            return {
                'folder': folder_path,
                'success': False,
                'result': None,
                'error': str(e)
            }
    
    if parallel and len(folders) > 1:
        # Parallel processing using ThreadPoolExecutor
        logger.info(f"Starting parallel batch processing with {max_workers} workers")
        print_info(f"Processing {len(folders)} folders in parallel (max {max_workers} workers)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all folder processing tasks
            future_to_folder = {
                executor.submit(process_single_folder, folder): folder
                for folder in folders
            }
            
            # Process completed tasks as they finish
            for future in as_completed(future_to_folder):
                folder = future_to_folder[future]
                try:
                    result = future.result()
                    
                    if result['success']:
                        stats['folders_processed'] += 1
                        stats['total_files'] += result['result'].get('files_processed', 0)
                        stats['total_anomalies'] += result['result'].get('anomalies_found', 0)
                        print_info(f"✓ Completed: {folder.name}")
                    else:
                        stats['folders_failed'] += 1
                        stats['processing_errors'].append({
                            'folder': str(folder),
                            'error': result['error']
                        })
                        print_error(f"✗ Failed: {folder.name} - {result['error']}")
                        
                        if not continue_on_error:
                            # Cancel remaining tasks
                            for remaining_future in future_to_folder:
                                remaining_future.cancel()
                            raise ProcessingError(f"Batch processing failed on {folder}: {result['error']}")
                            
                except Exception as e:
                    stats['folders_failed'] += 1
                    error_msg = str(e)
                    stats['processing_errors'].append({
                        'folder': str(folder),
                        'error': error_msg
                    })
                    logger.exception(f"Unexpected error processing folder {folder}")
                    print_error(f"✗ Failed: {folder.name} - {error_msg}")
                    
                    if not continue_on_error:
                        raise ProcessingError(f"Batch processing failed on {folder}: {error_msg}")
    else:
        # Sequential processing
        logger.info("Starting sequential batch processing")
        print_info(f"Processing {len(folders)} folders sequentially")
        
        for i, folder in enumerate(folders, 1):
            print_info(f"[{i}/{len(folders)}] Processing: {folder.name}")
            
            result = process_single_folder(folder)
            
            if result['success']:
                stats['folders_processed'] += 1
                stats['total_files'] += result['result'].get('files_processed', 0)
                stats['total_anomalies'] += result['result'].get('anomalies_found', 0)
                print_info(f"✓ Completed: {folder.name}")
            else:
                stats['folders_failed'] += 1
                stats['processing_errors'].append({
                    'folder': str(folder),
                    'error': result['error']
                })
                print_error(f"✗ Failed: {folder.name} - {result['error']}")
                
                if not continue_on_error:
                    raise ProcessingError(f"Batch processing failed on {folder}: {result['error']}")
    
    # Log final statistics
    logger.info(f"Batch processing completed: {stats['folders_processed']} successful, {stats['folders_failed']} failed")
    
    return stats


def _collect_unknown_parts(input_path: Path, output_path: Path,
                          suggest_prices: bool, db_manager) -> Dict[str, Any]:
    """Collect unknown parts from invoices using the validation engine."""
    print_info("Starting unknown parts collection...")
    
    # Use the same PDF discovery logic as the main processing
    try:
        pdf_files = _discover_pdf_files(input_path)
    except ProcessingError as e:
        raise ProcessingError(f"Failed to find PDF files: {e}")
    
    try:
        # Create validation configuration for unknown parts collection
        config = ValidationConfiguration.from_database_config(db_manager)
        config.interactive_discovery = False
        config.batch_collect_unknown_parts = True
        
        # Create validation workflow
        workflow = create_validation_workflow(db_manager, config)
        
        # Process invoices to collect unknown parts
        processing_stats = workflow.process_invoices_batch(
            invoice_paths=pdf_files,
            output_path=output_path,
            report_format='csv',
            interactive_discovery=False
        )
        
        # Extract unknown parts information from validation results
        # This would be collected during the validation process
        unknown_parts_data = []
        
        # For now, return the processing stats
        # In a full implementation, we would extract unknown parts from validation results
        stats = {
            'files_processed': processing_stats.get('successfully_processed', 0),
            'unknown_parts_found': processing_stats.get('unknown_parts_discovered', 0),
            'output_file': str(output_path),
            'files_failed': processing_stats.get('failed_processing', 0)
        }
        
        print_info(f"Collection complete: {stats['unknown_parts_found']} unknown parts found")
        
        return stats
        
    except Exception as e:
        logger.exception(f"Unknown parts collection failed: {e}")
        raise ProcessingError(f"Unknown parts collection failed: {e}")


def _find_invoice_folders(base_path: Path) -> List[Path]:
    """Find all subdirectories containing PDF files."""
    folders = []
    
    for item in base_path.iterdir():
        if item.is_dir():
            pdf_files = list(item.glob("*.pdf"))
            if pdf_files:
                folders.append(item)
    
    return folders


def _generate_report(anomalies: List[Dict], output_path: Path, format: str):
    """Generate the final report in the specified format."""
    if format == 'csv':
        write_csv(anomalies, output_path)
    elif format == 'json':
        import json
        with open(output_path, 'w') as f:
            json.dump(anomalies, f, indent=2, default=str)
    elif format == 'txt':
        with open(output_path, 'w') as f:
            f.write(format_table(anomalies))


def _generate_empty_report(output_path: Path, format: str):
    """Generate an empty report when no anomalies are found."""
    if format == 'csv':
        with open(output_path, 'w') as f:
            f.write("No anomalies found.\n")
    elif format == 'json':
        with open(output_path, 'w') as f:
            f.write('{"message": "No anomalies found", "anomalies": []}\n')
    elif format == 'txt':
        with open(output_path, 'w') as f:
            f.write("No pricing anomalies found.\n")


def _show_unknown_parts_review(session_id: str, db_manager):
    """
    Show review of unknown parts discovered during processing.
    
    This function displays a comprehensive summary of all unknown parts found
    during the current processing session, including price analysis and occurrence
    statistics. It provides the user with an overview before deciding whether to
    add parts to the database.
    
    Args:
        session_id: Processing session ID to filter discovery logs
        db_manager: Database manager instance for data access
        
    Raises:
        CLIError: If review display fails
    """
    try:
        # Get discovery logs for this session
        logs = db_manager.get_discovery_logs(session_id=session_id)
        unknown_logs = [log for log in logs if log.action_taken == 'discovered']
        
        if not unknown_logs:
            print_info("No unknown parts found in this session.")
            return
        
        print_info(f"Found {len(unknown_logs)} unknown parts in session {session_id[:8]}...")
        
        # Group by part number for analysis
        parts_data = {}
        for log in unknown_logs:
            if log.part_number not in parts_data:
                parts_data[log.part_number] = {
                    'part_number': log.part_number,
                    'discovered_prices': [],
                    'invoices': [],
                    'descriptions': set()
                }
            
            parts_data[log.part_number]['discovered_prices'].append(log.discovered_price)
            parts_data[log.part_number]['invoices'].append(log.invoice_number)
            
            # Add description if available in log notes
            if hasattr(log, 'notes') and log.notes:
                parts_data[log.part_number]['descriptions'].add(log.notes)
        
        # Display summary table
        display_data = []
        for part_number, data in parts_data.items():
            prices = [p for p in data['discovered_prices'] if p is not None]
            if not prices:
                continue
                
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            display_data.append({
                'Part Number': part_number,
                'Occurrences': len(data['discovered_prices']),
                'Avg Price': f"${avg_price:.4f}",
                'Min Price': f"${min_price:.4f}",
                'Max Price': f"${max_price:.4f}",
                'Invoices': len(set(data['invoices'])),
                'Price Range': f"${min_price:.4f} - ${max_price:.4f}" if min_price != max_price else f"${min_price:.4f}"
            })
        
        if display_data:
            click.echo("\n" + format_table(display_data))
            
            # Offer to add parts
            if click.confirm("\nWould you like to add these parts to the database?", default=True):
                _interactive_parts_addition(session_id, db_manager)
        else:
            print_warning("No valid price data found for unknown parts.")
            
    except Exception as e:
        logger.exception("Failed to show unknown parts review")
        raise CLIError(f"Failed to show unknown parts review: {e}")


def _interactive_parts_addition(session_id: str, db_manager):
    """
    Interactive workflow for adding discovered parts to database.
    
    This function guides the user through adding unknown parts to the master
    parts database. For each part, it shows price analysis and allows the user
    to choose how to handle it (add with various price options, enter custom
    price, or skip).
    
    Args:
        session_id: Processing session ID to filter discovery logs
        db_manager: Database manager instance for data operations
        
    Raises:
        CLIError: If interactive addition workflow fails
    """
    try:
        # Get unknown parts from discovery logs
        logs = db_manager.get_discovery_logs(session_id=session_id)
        unknown_logs = [log for log in logs if log.action_taken == 'discovered']
        
        if not unknown_logs:
            print_info("No unknown parts to add.")
            return
        
        # Group by part number
        parts_to_add = {}
        for log in unknown_logs:
            if log.part_number not in parts_to_add:
                parts_to_add[log.part_number] = {
                    'prices': [],
                    'invoices': [],
                    'log_ids': [],
                    'descriptions': set()
                }
            
            if log.discovered_price is not None:
                parts_to_add[log.part_number]['prices'].append(log.discovered_price)
            parts_to_add[log.part_number]['invoices'].append(log.invoice_number)
            parts_to_add[log.part_number]['log_ids'].append(log.id)
            
            # Collect descriptions from log notes
            if hasattr(log, 'notes') and log.notes:
                parts_to_add[log.part_number]['descriptions'].add(log.notes)
        
        added_count = 0
        skipped_count = 0
        
        print_info(f"Starting interactive addition of {len(parts_to_add)} parts...")
        
        for i, (part_number, data) in enumerate(parts_to_add.items(), 1):
            click.echo(f"\n--- Part {i}/{len(parts_to_add)}: {part_number} ---")
            
            # Filter out None prices
            prices = [p for p in data['prices'] if p is not None]
            if not prices:
                print_warning(f"No valid prices found for {part_number}, skipping...")
                skipped_count += 1
                continue
            
            # Show price analysis
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            click.echo(f"Found in {len(prices)} invoice line(s)")
            click.echo(f"Price range: ${min_price:.4f} - ${max_price:.4f}")
            click.echo(f"Average price: ${avg_price:.4f}")
            
            if data['descriptions']:
                click.echo(f"Descriptions: {', '.join(list(data['descriptions'])[:3])}")
            
            # Get user decision
            choices = [
                f"Add with average price (${avg_price:.4f})",
                f"Add with minimum price (${min_price:.4f})",
                f"Add with maximum price (${max_price:.4f})",
                "Enter custom price",
                "Skip this part"
            ]
            
            try:
                choice = prompt_for_choice(f"How would you like to handle {part_number}?", choices)
                
                if choice.startswith("Add with average"):
                    authorized_price = avg_price
                elif choice.startswith("Add with minimum"):
                    authorized_price = min_price
                elif choice.startswith("Add with maximum"):
                    authorized_price = max_price
                elif choice.startswith("Enter custom"):
                    authorized_price = prompt_for_threshold("Enter authorized price for this part")
                else:  # Skip
                    print_info(f"Skipped part: {part_number}")
                    skipped_count += 1
                    continue
                
                # Get additional details
                description = click.prompt("Description (optional)", default="", type=str)
                if not description.strip():
                    # Use first available description from logs if none provided
                    description = list(data['descriptions'])[0] if data['descriptions'] else None
                
                category = click.prompt("Category (optional)", default="", type=str)
                if not category.strip():
                    category = None
                    
                notes = click.prompt("Notes (optional)", default="", type=str)
                if not notes.strip():
                    notes = None
                
                # Create and add part
                part = Part(
                    part_number=part_number,
                    authorized_price=authorized_price,
                    description=description,
                    category=category,
                    source='discovered',
                    notes=notes,
                    first_seen_invoice=data['invoices'][0] if data['invoices'] else None
                )
                
                created_part = db_manager.create_part(part)
                print_success(f"Added part {part_number} with price ${authorized_price:.4f}")
                added_count += 1
                
                # Log the successful addition
                logger.info(f"Added discovered part {part_number} with price ${authorized_price:.4f}")
                
            except UserCancelledError:
                print_info("Interactive addition cancelled by user.")
                break
            except ValidationError as e:
                print_error(f"Failed to add part {part_number}: {e}")
                skipped_count += 1
            except Exception as e:
                print_error(f"Failed to add part {part_number}: {e}")
                logger.exception(f"Failed to add part {part_number}")
                skipped_count += 1
        
        # Summary
        click.echo(f"\n{'='*50}")
        print_success(f"Interactive addition complete!")
        click.echo(f"  Parts added: {added_count}")
        click.echo(f"  Parts skipped: {skipped_count}")
        click.echo(f"  Total processed: {added_count + skipped_count}")
        
        if added_count > 0:
            print_info("New parts have been added to the master database and will be used in future processing.")
        
    except UserCancelledError:
        print_info("Interactive parts addition cancelled by user.")
    except Exception as e:
        logger.exception("Failed in interactive parts addition")
        raise CLIError(f"Interactive parts addition failed: {e}")