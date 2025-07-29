"""
Custom exceptions for PDF processing operations.

This module defines specific exception classes for different types of errors
that can occur during PDF extraction and parsing operations.
"""

from typing import Optional, Dict, Any


class PDFProcessingError(Exception):
    """Base exception for all PDF processing errors."""
    
    def __init__(self, message: str, pdf_path: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.pdf_path = pdf_path
        self.details = details or {}
        
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.pdf_path:
            base_msg = f"{base_msg} (PDF: {self.pdf_path})"
        return base_msg


class PDFReadabilityError(PDFProcessingError):
    """Raised when a PDF file cannot be read or accessed."""
    
    def __init__(self, message: str, pdf_path: Optional[str] = None, 
                 original_error: Optional[Exception] = None):
        super().__init__(message, pdf_path)
        self.original_error = original_error
        if original_error:
            self.details['original_error'] = str(original_error)
            self.details['error_type'] = type(original_error).__name__


class InvoiceParsingError(PDFProcessingError):
    """Raised when invoice data cannot be parsed from PDF text."""
    
    def __init__(self, message: str, pdf_path: Optional[str] = None,
                 parsing_stage: Optional[str] = None, 
                 extracted_text: Optional[str] = None):
        super().__init__(message, pdf_path)
        self.parsing_stage = parsing_stage
        if parsing_stage:
            self.details['parsing_stage'] = parsing_stage
        if extracted_text:
            # Store first 500 chars for debugging
            self.details['text_sample'] = extracted_text[:500]


class FormatValidationError(PDFProcessingError):
    """Raised when invoice format doesn't match expected structure."""
    
    def __init__(self, message: str, pdf_path: Optional[str] = None,
                 expected_format: Optional[str] = None,
                 found_format: Optional[str] = None):
        super().__init__(message, pdf_path)
        self.expected_format = expected_format
        self.found_format = found_format
        if expected_format:
            self.details['expected_format'] = expected_format
        if found_format:
            self.details['found_format'] = found_format


class DataQualityError(PDFProcessingError):
    """Raised when extracted data fails quality validation checks."""
    
    def __init__(self, message: str, pdf_path: Optional[str] = None,
                 field_name: Optional[str] = None,
                 field_value: Optional[str] = None,
                 validation_rule: Optional[str] = None):
        super().__init__(message, pdf_path)
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule
        
        if field_name:
            self.details['field_name'] = field_name
        if field_value:
            self.details['field_value'] = str(field_value)
        if validation_rule:
            self.details['validation_rule'] = validation_rule


class LineItemParsingError(InvoiceParsingError):
    """Raised when specific line items cannot be parsed."""
    
    def __init__(self, message: str, pdf_path: Optional[str] = None,
                 line_number: Optional[int] = None,
                 line_text: Optional[str] = None):
        super().__init__(message, pdf_path, "line_item_parsing")
        self.line_number = line_number
        self.line_text = line_text
        
        if line_number is not None:
            self.details['line_number'] = line_number
        if line_text:
            self.details['line_text'] = line_text


class MetadataParsingError(InvoiceParsingError):
    """Raised when invoice metadata cannot be extracted."""
    
    def __init__(self, message: str, pdf_path: Optional[str] = None,
                 missing_fields: Optional[list] = None):
        super().__init__(message, pdf_path, "metadata_parsing")
        self.missing_fields = missing_fields or []
        
        if self.missing_fields:
            self.details['missing_fields'] = self.missing_fields


class TextExtractionError(PDFProcessingError):
    """Raised when text cannot be extracted from PDF."""
    
    def __init__(self, message: str, pdf_path: Optional[str] = None,
                 page_number: Optional[int] = None,
                 extraction_method: Optional[str] = None):
        super().__init__(message, pdf_path)
        self.page_number = page_number
        self.extraction_method = extraction_method
        
        if page_number is not None:
            self.details['page_number'] = page_number
        if extraction_method:
            self.details['extraction_method'] = extraction_method