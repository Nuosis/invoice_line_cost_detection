"""
Validation Test Suite for Invoice Rate Detection System.

This package contains comprehensive validation tests that verify the accuracy
and reliability of the entire invoice processing pipeline, from PDF text
extraction to final validation reports.

Test Categories:
- Text Extraction Validation: Verifies PDF processing accuracy
- CLI Validation Output: Tests CLI command execution and output generation
- Expectation Document Management: Creates and manages expected results

Usage:
    # Run all validation tests
    PYTHONPATH=. python test_validation/run_validation_tests.py
    
    # Run specific test categories
    PYTHONPATH=. python -m pytest test_validation/test_text_extraction_validation.py -v
    PYTHONPATH=. python -m pytest test_validation/test_cli_validation_output.py -v
    PYTHONPATH=. python -m pytest test_validation/test_expectation_generator.py -v
"""

__version__ = "1.0.0"
__author__ = "Invoice Rate Detection System"

# Import main test classes for easy access
from .test_text_extraction_validation import TextExtractionValidationTests
from .test_cli_validation_output import (
    CLIValidationOutputTests,
    CLIValidationIntegrationTests
)
from .test_expectation_generator import (
    ExpectationGeneratorTests,
    ExpectationTemplateValidationTests,
    ExpectationDocumentGenerator
)

__all__ = [
    'TextExtractionValidationTests',
    'CLIValidationOutputTests', 
    'CLIValidationIntegrationTests',
    'ExpectationGeneratorTests',
    'ExpectationTemplateValidationTests',
    'ExpectationDocumentGenerator'
]