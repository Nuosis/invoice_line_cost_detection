"""
PDF Processing Module for Invoice Rate Detection System.

This module provides comprehensive PDF extraction and parsing capabilities
for invoice processing, including text extraction, data validation, and
structured data output for the validation engine.
"""

from .pdf_processor import PDFProcessor
from .models import InvoiceData, LineItem, FormatSection
from .exceptions import (
    PDFProcessingError,
    PDFReadabilityError,
    InvoiceParsingError,
    FormatValidationError,
    DataQualityError
)
from .integration import (
    PDFProcessingIntegrator,
    create_integrator,
    process_invoices_for_cli
)

__all__ = [
    'PDFProcessor',
    'InvoiceData',
    'LineItem',
    'FormatSection',
    'PDFProcessingError',
    'PDFReadabilityError',
    'InvoiceParsingError',
    'FormatValidationError',
    'DataQualityError',
    'PDFProcessingIntegrator',
    'create_integrator',
    'process_invoices_for_cli'
]