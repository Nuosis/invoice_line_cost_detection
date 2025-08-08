"""
PDF Processing Module for Invoice Rate Detection System.

This module provides simplified PDF extraction and parsing capabilities
for invoice processing, including text extraction and structured data output.
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
from .report_generator import generate_reports
from .part_discovery import discover_parts_from_json

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
    'generate_reports',
    'discover_parts_from_json'
]