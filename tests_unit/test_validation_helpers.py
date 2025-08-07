"""
Unit tests for CLI validation helpers.

This module tests the centralized validation utilities to ensure they provide
consistent validation behavior and error formatting across CLI commands.
"""

import pytest
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

from cli.validation_helpers import (
    ValidationHelper, ValidationResult, BatchValidationResult, ValidationSeverity,
    validate_part_batch, validate_price_batch, validate_config_keys_batch
)
from cli.exceptions import ValidationError as CLIValidationError
from cli.validators import validate_part_number, validate_price, validate_configuration_key


class TestValidationResult:
    """Test ValidationResult data class."""
    
    def test_valid_result_creation(self):
        """Test creating a valid ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            value="GP0171NAVY",
            field_name="part_number"
        )
        
        assert result.is_valid is True
        assert result.value == "GP0171NAVY"
        assert result.field_name == "part_number"
        assert result.error_message is None
        assert result.severity == ValidationSeverity.ERROR
        assert result.suggestions == []
    
    def test_invalid_result_creation(self):
        """Test creating an invalid ValidationResult."""
        suggestions = ["Use only alphanumeric characters", "Check format"]
        result = ValidationResult(
            is_valid=False,
            error_message="Invalid part number format",
            field_name="part_number",
            severity=ValidationSeverity.CRITICAL,
            suggestions=suggestions
        )
        
        assert result.is_valid is False
        assert result.value is None
        assert result.error_message == "Invalid part number format"
        assert result.field_name == "part_number"
        assert result.severity == ValidationSeverity.CRITICAL
        assert result.suggestions == suggestions
    
    def test_post_init_suggestions_default(self):
        """Test that suggestions defaults to empty list."""
        result = ValidationResult(is_valid=True, value="test")
        assert result.suggestions == []


class TestBatchValidationResult:
    """Test BatchValidationResult data class."""
    
    def test_batch_result_creation(self):
        """Test creating a BatchValidationResult."""
        valid_items = ["GP0171NAVY", "ITEM123"]
        invalid_items = [
            ValidationResult(is_valid=False, error_message="Invalid format", field_name="item[2]")
        ]
        warnings = ["Low success rate"]
        
        result = BatchValidationResult(
            valid_items=valid_items,
            invalid_items=invalid_items,
            total_count=3,
            success_count=2,
            error_count=1,
            warnings=warnings
        )
        
        assert result.valid_items == valid_items
        assert result.invalid_items == invalid_items
        assert result.total_count == 3
        assert result.success_count == 2
        assert result.error_count == 1
        assert result.warnings == warnings
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        result = BatchValidationResult(
            valid_items=["item1", "item2"],
            invalid_items=[],
            total_count=4,
            success_count=2,
            error_count=2,
            warnings=[]
        )
        
        assert result.success_rate == 50.0
    
    def test_success_rate_zero_total(self):
        """Test success rate with zero total count."""
        result = BatchValidationResult(
            valid_items=[],
            invalid_items=[],
            total_count=0,
            success_count=0,
            error_count=0,
            warnings=[]
        )
        
        assert result.success_rate == 0.0
    
    def test_has_errors_property(self):
        """Test has_errors property."""
        result_with_errors = BatchValidationResult(
            valid_items=[], invalid_items=[], total_count=1,
            success_count=0, error_count=1, warnings=[]
        )
        result_without_errors = BatchValidationResult(
            valid_items=[], invalid_items=[], total_count=1,
            success_count=1, error_count=0, warnings=[]
        )
        
        assert result_with_errors.has_errors is True
        assert result_without_errors.has_errors is False
    
    def test_has_warnings_property(self):
        """Test has_warnings property."""
        result_with_warnings = BatchValidationResult(
            valid_items=[], invalid_items=[], total_count=0,
            success_count=0, error_count=0, warnings=["Warning message"]
        )
        result_without_warnings = BatchValidationResult(
            valid_items=[], invalid_items=[], total_count=0,
            success_count=0, error_count=0, warnings=[]
        )
        
        assert result_with_warnings.has_warnings is True
        assert result_without_warnings.has_warnings is False


class TestValidationHelper:
    """Test ValidationHelper class methods."""
    
    def test_validate_single_item_success(self):
        """Test successful single item validation."""
        result = ValidationHelper.validate_single_item(
            "GP0171NAVY", validate_part_number, "part_number"
        )
        
        assert result.is_valid is True
        assert result.value == "GP0171NAVY"
        assert result.field_name == "part_number"
        assert result.error_message is None
    
    def test_validate_single_item_failure(self):
        """Test failed single item validation."""
        result = ValidationHelper.validate_single_item(
            "invalid!", validate_part_number, "part_number"
        )
        
        assert result.is_valid is False
        assert result.value is None
        assert result.field_name == "part_number"
        assert result.error_message is not None
        assert result.severity == ValidationSeverity.ERROR
        assert len(result.suggestions) > 0
    
    def test_validate_single_item_unexpected_error(self):
        """Test handling of unexpected errors in single item validation."""
        def failing_validator(value):
            raise RuntimeError("Unexpected error")
        
        result = ValidationHelper.validate_single_item(
            "test", failing_validator, "test_field"
        )
        
        assert result.is_valid is False
        assert result.severity == ValidationSeverity.CRITICAL
        assert "Unexpected validation error" in result.error_message
    
    def test_validate_batch_input_success(self):
        """Test successful batch validation."""
        inputs = ["GP0171NAVY", "ITEM123", "PART_001"]
        result = ValidationHelper.validate_batch_input(
            inputs, validate_part_number, "part_number"
        )
        
        assert result.total_count == 3
        assert result.success_count == 3
        assert result.error_count == 0
        assert len(result.valid_items) == 3
        assert len(result.invalid_items) == 0
        assert result.success_rate == 100.0
        assert not result.has_errors
    
    def test_validate_batch_input_mixed_results(self):
        """Test batch validation with mixed valid/invalid items."""
        inputs = ["GP0171NAVY", "invalid!", "ITEM123", ""]
        result = ValidationHelper.validate_batch_input(
            inputs, validate_part_number, "part_number", continue_on_error=True
        )
        
        assert result.total_count == 4
        assert result.success_count == 2
        assert result.error_count == 2
        assert len(result.valid_items) == 2
        assert len(result.invalid_items) == 2
        assert result.success_rate == 50.0
        assert result.has_errors
    
    def test_validate_batch_input_empty_list(self):
        """Test batch validation with empty input list."""
        result = ValidationHelper.validate_batch_input(
            [], validate_part_number, "part_number"
        )
        
        assert result.total_count == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert len(result.valid_items) == 0
        assert len(result.invalid_items) == 0
        assert result.has_warnings
        assert "No part_number items provided" in result.warnings[0]
    
    def test_validate_batch_input_stop_on_error(self):
        """Test batch validation stopping on first error."""
        inputs = ["GP0171NAVY", "invalid!", "ITEM123"]
        result = ValidationHelper.validate_batch_input(
            inputs, validate_part_number, "part_number", continue_on_error=False
        )
        
        assert result.success_count == 1
        assert result.error_count == 1
        # Should stop after first error
        assert result.total_count == 3  # Total count is still the input length
    
    def test_validate_csv_row_data_success(self):
        """Test successful CSV row validation."""
        row_data = {
            'part_number': 'GP0171NAVY',
            'authorized_price': '15.50',
            'description': 'Navy Work Pants'
        }
        field_validators = {
            'part_number': validate_part_number,
            'authorized_price': validate_price
        }
        
        result = ValidationHelper.validate_csv_row_data(
            row_data, field_validators, row_number=1
        )
        
        assert result.is_valid is True
        assert result.value['part_number'] == 'GP0171NAVY'
        assert result.value['authorized_price'] == Decimal('15.50')
        assert result.field_name == "row_1"
    
    def test_validate_csv_row_data_missing_field(self):
        """Test CSV row validation with missing required field."""
        row_data = {
            'part_number': 'GP0171NAVY'
            # Missing 'authorized_price'
        }
        field_validators = {
            'part_number': validate_part_number,
            'authorized_price': validate_price
        }
        
        result = ValidationHelper.validate_csv_row_data(
            row_data, field_validators, row_number=2
        )
        
        assert result.is_valid is False
        assert "Missing required field: authorized_price" in result.error_message
        assert result.field_name == "row_2"
    
    def test_validate_csv_row_data_invalid_field(self):
        """Test CSV row validation with invalid field value."""
        row_data = {
            'part_number': 'invalid!',
            'authorized_price': '15.50'
        }
        field_validators = {
            'part_number': validate_part_number,
            'authorized_price': validate_price
        }
        
        result = ValidationHelper.validate_csv_row_data(
            row_data, field_validators, row_number=3
        )
        
        assert result.is_valid is False
        assert "part_number:" in result.error_message
        assert result.field_name == "row_3"
    
    def test_validate_file_batch_success(self):
        """Test successful file batch validation."""
        with patch('cli.validators.validate_file_path') as mock_validate:
            mock_validate.side_effect = lambda x, **kwargs: Path(x)
            
            file_paths = ['file1.pdf', 'file2.pdf']
            result = ValidationHelper.validate_file_batch(
                file_paths, extensions=['.pdf'], must_exist=False
            )
            
            assert result.success_count == 2
            assert result.error_count == 0
            assert len(result.valid_items) == 2
    
    def test_validate_parts_data_batch_success(self):
        """Test successful parts data batch validation."""
        parts_data = [
            {'part_number': 'GP0171NAVY', 'authorized_price': Decimal('15.50')},
            {'part_number': 'ITEM123', 'authorized_price': Decimal('25.00')}
        ]
        
        result = ValidationHelper.validate_parts_data_batch(parts_data)
        
        assert result.success_count == 2
        assert result.error_count == 0
        assert len(result.valid_items) == 2
    
    def test_validate_parts_data_batch_invalid_data(self):
        """Test parts data batch validation with invalid data."""
        parts_data = [
            {'part_number': 'GP0171NAVY', 'authorized_price': Decimal('15.50')},
            {'part_number': 'invalid!', 'authorized_price': Decimal('25.00')},
            "not_a_dict"
        ]
        
        result = ValidationHelper.validate_parts_data_batch(parts_data)
        
        assert result.success_count == 1
        assert result.error_count == 2
        assert result.has_errors
    
    def test_format_validation_errors_empty_list(self):
        """Test formatting empty error list."""
        formatted = ValidationHelper.format_validation_errors([])
        assert "No validation errors found" in formatted
    
    def test_format_validation_errors_with_errors(self):
        """Test formatting validation errors."""
        errors = [
            ValidationResult(
                is_valid=False,
                error_message="Invalid part number",
                field_name="part_number",
                severity=ValidationSeverity.ERROR,
                suggestions=["Use alphanumeric characters"]
            ),
            ValidationResult(
                is_valid=False,
                error_message="Critical system error",
                field_name="system",
                severity=ValidationSeverity.CRITICAL
            )
        ]
        
        formatted = ValidationHelper.format_validation_errors(errors, show_suggestions=True)
        
        assert "Found 2 validation error(s)" in formatted
        assert "CRITICAL ERRORS:" in formatted
        assert "ERRORS:" in formatted
        assert "SUGGESTIONS:" in formatted
        assert "Invalid part number" in formatted
        assert "Critical system error" in formatted
        assert "Use alphanumeric characters" in formatted
    
    def test_format_validation_errors_max_display_limit(self):
        """Test formatting with maximum display limit."""
        errors = [
            ValidationResult(
                is_valid=False,
                error_message=f"Error {i}",
                field_name=f"field_{i}"
            ) for i in range(15)
        ]
        
        formatted = ValidationHelper.format_validation_errors(errors, max_errors_displayed=5)
        
        assert "... and 10 more errors" in formatted
    
    def test_get_validation_suggestions_part_number(self):
        """Test getting suggestions for part number validation."""
        suggestions = ValidationHelper._get_validation_suggestions(
            "part_number", "Invalid part number format"
        )
        
        assert any("alphanumeric" in s.lower() for s in suggestions)
        assert any("example" in s.lower() for s in suggestions)
    
    def test_get_validation_suggestions_price(self):
        """Test getting suggestions for price validation."""
        suggestions = ValidationHelper._get_validation_suggestions(
            "price", "Invalid price format"
        )
        
        assert any("positive number" in s.lower() for s in suggestions)
        assert any("decimal" in s.lower() for s in suggestions)
    
    def test_get_validation_suggestions_generic(self):
        """Test getting generic suggestions."""
        suggestions = ValidationHelper._get_validation_suggestions(
            "unknown_field", "Some error"
        )
        
        assert any("input format" in s.lower() for s in suggestions)
        assert any("help" in s.lower() for s in suggestions)
    
    @patch('cli.validation_helpers.print_info')
    @patch('cli.validation_helpers.print_warning')
    @patch('cli.validation_helpers.print_error')
    def test_print_validation_summary(self, mock_error, mock_warning, mock_info):
        """Test printing validation summary."""
        result = BatchValidationResult(
            valid_items=["item1", "item2"],
            invalid_items=[
                ValidationResult(is_valid=False, error_message="Error", field_name="field")
            ],
            total_count=3,
            success_count=2,
            error_count=1,
            warnings=["Warning message"]
        )
        
        ValidationHelper.print_validation_summary(result, "test operation")
        
        # Verify print functions were called
        assert mock_info.call_count >= 4  # Summary info calls
        assert mock_warning.call_count >= 1  # Warning calls
        assert mock_error.call_count >= 1  # Error calls


class TestConvenienceFunctions:
    """Test convenience functions for common validation patterns."""
    
    def test_validate_part_batch_success(self):
        """Test part number batch validation."""
        part_numbers = ["GP0171NAVY", "ITEM123", "PART_001"]
        result = validate_part_batch(part_numbers)
        
        assert result.success_count == 3
        assert result.error_count == 0
        assert len(result.valid_items) == 3
    
    def test_validate_part_batch_with_errors(self):
        """Test part number batch validation with errors."""
        part_numbers = ["GP0171NAVY", "invalid!", "ITEM123"]
        result = validate_part_batch(part_numbers)
        
        assert result.success_count == 2
        assert result.error_count == 1
        assert result.has_errors
    
    def test_validate_price_batch_success(self):
        """Test price batch validation."""
        prices = ["15.50", "25.00", "100.0000"]
        result = validate_price_batch(prices)
        
        assert result.success_count == 3
        assert result.error_count == 0
        assert all(isinstance(item, Decimal) for item in result.valid_items)
    
    def test_validate_price_batch_with_errors(self):
        """Test price batch validation with errors."""
        prices = ["15.50", "-5.00", "invalid", "25.00"]
        result = validate_price_batch(prices)
        
        assert result.success_count == 2
        assert result.error_count == 2
        assert result.has_errors
    
    def test_validate_config_keys_batch_success(self):
        """Test configuration keys batch validation."""
        config_keys = ["validation_mode", "price_threshold", "batch_size"]
        result = validate_config_keys_batch(config_keys)
        
        assert result.success_count == 3
        assert result.error_count == 0
        assert len(result.valid_items) == 3
    
    def test_validate_config_keys_batch_with_errors(self):
        """Test configuration keys batch validation with errors."""
        config_keys = ["validation_mode", "Invalid-Key!", "batch_size"]
        result = validate_config_keys_batch(config_keys)
        
        assert result.success_count == 2
        assert result.error_count == 1
        assert result.has_errors


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple validation helpers."""
    
    def test_csv_import_workflow_simulation(self):
        """Test simulating a complete CSV import validation workflow."""
        # Simulate CSV data with mixed valid/invalid entries
        csv_data = [
            {'part_number': 'GP0171NAVY', 'authorized_price': Decimal('15.50')},
            {'part_number': 'ITEM123', 'authorized_price': Decimal('25.00')},
            {'part_number': 'invalid!', 'authorized_price': Decimal('30.00')},
            {'part_number': 'PART_001', 'authorized_price': Decimal('-5.00')},  # Invalid price
            {'part_number': 'VALID_PART', 'authorized_price': Decimal('45.00')}
        ]
        
        # Validate the batch
        result = ValidationHelper.validate_parts_data_batch(csv_data)
        
        # Should have some valid and some invalid items
        assert result.total_count == 5
        assert result.success_count == 3  # GP0171NAVY, ITEM123, VALID_PART
        assert result.error_count == 2   # invalid!, negative price
        assert result.has_errors
        
        # Verify error formatting works
        error_message = ValidationHelper.format_validation_errors(
            result.invalid_items, show_suggestions=True
        )
        assert "validation error(s)" in error_message
        assert "SUGGESTIONS:" in error_message
    
    def test_file_validation_workflow(self):
        """Test file validation workflow."""
        with patch('cli.validation_helpers.validate_file_path') as mock_validate:
            # Mock some files as valid, some as invalid
            def mock_file_validator(path, **kwargs):
                if 'invalid' in str(path):
                    raise CLIValidationError("File not found")
                return Path(path)
            
            mock_validate.side_effect = mock_file_validator
            
            file_paths = [
                'valid_file1.pdf',
                'valid_file2.pdf',
                'invalid_file.pdf',
                'another_valid.pdf'
            ]
            
            result = ValidationHelper.validate_file_batch(
                file_paths, extensions=['.pdf'], must_exist=True
            )
            
            assert result.success_count == 3
            assert result.error_count == 1
            assert result.has_errors
    
    def test_error_recovery_suggestions(self):
        """Test that error recovery suggestions are contextually appropriate."""
        # Test part number validation suggestions
        part_result = ValidationHelper.validate_single_item(
            "invalid!", validate_part_number, "part_number"
        )
        
        assert not part_result.is_valid
        assert any("alphanumeric" in s.lower() for s in part_result.suggestions)
        assert any("example" in s.lower() for s in part_result.suggestions)
        
        # Test price validation suggestions
        price_result = ValidationHelper.validate_single_item(
            "-5.00", validate_price, "price"
        )
        
        assert not price_result.is_valid
        assert any("positive" in s.lower() for s in price_result.suggestions)