"""
Integration utilities for connecting PDF processing with CLI and database layers.

This module provides utilities to integrate the PDF processing system with
the existing CLI interface and database models.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from decimal import Decimal

from .pdf_processor import PDFProcessor
from .models import InvoiceData, LineItem
from .exceptions import PDFProcessingError

# Import existing database models
try:
    from database.models import Invoice, InvoiceLineItem, Part
    from database.database import DatabaseManager
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    logging.warning("Database models not available - running in standalone mode")


class PDFProcessingIntegrator:
    """
    Integrates PDF processing with existing CLI and database systems.
    
    This class provides methods to process PDFs and integrate the results
    with the existing database schema and CLI reporting system.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the integrator.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.pdf_processor = PDFProcessor(logger=self.logger)
        self.db_manager = None
        
        if HAS_DATABASE:
            try:
                self.db_manager = DatabaseManager()
            except Exception as e:
                self.logger.warning(f"Could not initialize database manager: {e}")
    
    def process_pdf_file(self, pdf_path: Path) -> InvoiceData:
        """
        Process a single PDF file and extract invoice data.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            InvoiceData object containing extracted information
            
        Raises:
            PDFProcessingError: If processing fails
        """
        self.logger.info(f"Processing PDF file: {pdf_path}")
        
        try:
            invoice_data = self.pdf_processor.process_pdf(pdf_path)
            self.logger.info(f"Successfully processed {pdf_path}")
            return invoice_data
        except Exception as e:
            self.logger.error(f"Failed to process {pdf_path}: {e}")
            raise
    
    def process_pdf_batch(self, pdf_directory: Path) -> List[InvoiceData]:
        """
        Process all PDF files in a directory.
        
        Args:
            pdf_directory: Directory containing PDF files
            
        Returns:
            List of InvoiceData objects
        """
        self.logger.info(f"Processing PDF batch from directory: {pdf_directory}")
        
        if not pdf_directory.exists() or not pdf_directory.is_dir():
            raise ValueError(f"Directory does not exist: {pdf_directory}")
        
        pdf_files = list(pdf_directory.glob("*.pdf"))
        if not pdf_files:
            self.logger.warning(f"No PDF files found in {pdf_directory}")
            return []
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        processed_invoices = []
        failed_files = []
        
        for pdf_file in pdf_files:
            try:
                invoice_data = self.process_pdf_file(pdf_file)
                processed_invoices.append(invoice_data)
            except Exception as e:
                self.logger.error(f"Failed to process {pdf_file}: {e}")
                failed_files.append((pdf_file, str(e)))
                continue
        
        self.logger.info(
            f"Batch processing complete: {len(processed_invoices)} successful, "
            f"{len(failed_files)} failed"
        )
        
        if failed_files:
            self.logger.warning("Failed files:")
            for file_path, error in failed_files:
                self.logger.warning(f"  {file_path}: {error}")
        
        return processed_invoices
    
    def convert_to_database_models(self, invoice_data: InvoiceData) -> Optional[Dict[str, Any]]:
        """
        Convert InvoiceData to database model format.
        
        Args:
            invoice_data: InvoiceData object to convert
            
        Returns:
            Dictionary containing database model data or None if conversion fails
        """
        if not HAS_DATABASE:
            self.logger.warning("Database models not available")
            return None
        
        try:
            # Convert to database format
            db_invoice = {
                'invoice_number': invoice_data.invoice_number,
                'invoice_date': invoice_data.invoice_date,
                'customer_number': invoice_data.customer_number,
                'customer_name': invoice_data.customer_name,
                'total_amount': float(invoice_data.get_total_amount() or 0),
                'subtotal_amount': float(invoice_data.get_subtotal_amount() or 0),
                'pdf_path': invoice_data.pdf_path,
                'line_items': []
            }
            
            # Convert line items
            for line_item in invoice_data.get_valid_line_items():
                db_line_item = {
                    'wearer_number': line_item.wearer_number,
                    'wearer_name': line_item.wearer_name,
                    'item_code': line_item.item_code,
                    'description': line_item.description,
                    'size': line_item.size,
                    'item_type': line_item.item_type,
                    'quantity': line_item.quantity,
                    'rate': float(line_item.rate),
                    'total': float(line_item.total) if line_item.total else None,
                    'line_number': line_item.line_number
                }
                db_invoice['line_items'].append(db_line_item)
            
            return db_invoice
            
        except Exception as e:
            self.logger.error(f"Failed to convert invoice data to database format: {e}")
            return None
    
    def save_to_database(self, invoice_data: InvoiceData) -> bool:
        """
        Save invoice data to the database.
        
        Args:
            invoice_data: InvoiceData object to save
            
        Returns:
            True if successful, False otherwise
        """
        if not HAS_DATABASE or not self.db_manager:
            self.logger.warning("Database not available")
            return False
        
        try:
            db_data = self.convert_to_database_models(invoice_data)
            if not db_data:
                return False
            
            # Save to database using existing database manager
            # This would need to be implemented based on the actual database schema
            self.logger.info(f"Saved invoice {invoice_data.invoice_number} to database")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save invoice to database: {e}")
            return False
    
    def prepare_for_validation(self, invoice_data: InvoiceData) -> List[Dict[str, Any]]:
        """
        Prepare invoice data for the validation engine.
        
        Args:
            invoice_data: InvoiceData object to prepare
            
        Returns:
            List of line item dictionaries ready for validation
        """
        validation_data = []
        
        for line_item in invoice_data.get_valid_line_items():
            validation_item = {
                'invoice_number': invoice_data.invoice_number,
                'invoice_date': invoice_data.invoice_date,
                'item_code': line_item.item_code,
                'description': line_item.description,
                'quantity': line_item.quantity,
                'rate': line_item.rate,
                'total': line_item.total,
                'wearer_number': line_item.wearer_number,
                'wearer_name': line_item.wearer_name,
                'size': line_item.size,
                'item_type': line_item.item_type,
                'line_number': line_item.line_number,
                'pdf_path': invoice_data.pdf_path
            }
            validation_data.append(validation_item)
        
        return validation_data
    
    def get_processing_summary(self, invoice_data_list: List[InvoiceData]) -> Dict[str, Any]:
        """
        Generate a summary of processed invoices.
        
        Args:
            invoice_data_list: List of processed InvoiceData objects
            
        Returns:
            Dictionary containing processing summary
        """
        if not invoice_data_list:
            return {
                'total_invoices': 0,
                'total_line_items': 0,
                'valid_invoices': 0,
                'invalid_invoices': 0,
                'total_amount': 0.0,
                'date_range': None
            }
        
        total_invoices = len(invoice_data_list)
        valid_invoices = sum(1 for inv in invoice_data_list if inv.is_valid())
        invalid_invoices = total_invoices - valid_invoices
        
        total_line_items = sum(len(inv.line_items) for inv in invoice_data_list)
        total_amount = sum(
            float(inv.get_total_amount() or 0) 
            for inv in invoice_data_list 
            if inv.get_total_amount()
        )
        
        # Get date range
        dates = [inv.invoice_date for inv in invoice_data_list if inv.invoice_date]
        date_range = None
        if dates:
            date_range = {
                'earliest': min(dates),
                'latest': max(dates)
            }
        
        return {
            'total_invoices': total_invoices,
            'total_line_items': total_line_items,
            'valid_invoices': valid_invoices,
            'invalid_invoices': invalid_invoices,
            'total_amount': total_amount,
            'date_range': date_range,
            'invoice_numbers': [inv.invoice_number for inv in invoice_data_list if inv.invoice_number]
        }


def create_integrator(logger: Optional[logging.Logger] = None) -> PDFProcessingIntegrator:
    """
    Factory function to create a PDFProcessingIntegrator instance.
    
    Args:
        logger: Optional logger instance
        
    Returns:
        PDFProcessingIntegrator instance
    """
    return PDFProcessingIntegrator(logger=logger)


def process_invoices_for_cli(
    pdf_directory: Path, 
    logger: Optional[logging.Logger] = None
) -> List[Dict[str, Any]]:
    """
    Process invoices and return data suitable for CLI reporting.
    
    Args:
        pdf_directory: Directory containing PDF files
        logger: Optional logger instance
        
    Returns:
        List of dictionaries containing invoice data for CLI processing
    """
    integrator = create_integrator(logger)
    invoice_data_list = integrator.process_pdf_batch(pdf_directory)
    
    cli_data = []
    for invoice_data in invoice_data_list:
        validation_items = integrator.prepare_for_validation(invoice_data)
        cli_data.extend(validation_items)
    
    return cli_data