"""
Centralized validation utilities for CLI commands.

This module provides shared validation utilities to eliminate code duplication
across CLI commands while maintaining consistent validation behavior and error
formatting throughout the application.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Union, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from cli.exceptions import ValidationError as CLIValidationError
from cli.validators import (
    validate_part_number, validate_price, validate_file_path,
    validate_directory_path, validate_output_format, validate_configuration_key,
    validate_positive_integer, validate_session_id
)
from cli.formatters import print_error, print_warning, print_info

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ValidationSeverity(Enum):
    """Severity levels for validation results."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """
    Result of a single validation operation.
    
    Attributes:
        is_valid: Whether the validation passed
        value: The validated/transformed value (if valid)
        error_message: Human-readable error message (if invalid)
        field_name: Name of the field being validated
        severity: Severity level of the validation result
        suggestions: List of suggested fixes for validation failures
    """
    is_valid: bool
    value: Any = None
    error_message: Optional[str] = None
    field_name: Optional[str] = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    suggestions: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class BatchValidationResult(Generic[T]):
    """
    Result of batch validation operations.
    
    Attributes:
        valid_items: List of successfully validated items
        invalid_items: List of validation results for failed items
        total_count: Total number of items processed
        success_count: Number of successfully validated items
        error_count: Number of items that failed validation
        warnings: List of warning messages
    """
    valid_items: List[T]
    invalid_items: List[ValidationResult]
    total_count: int
    success_count: int
    error_count: int
    warnings: List[str]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return self.error_count > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class ValidationHelper:
    """Centralized validation utilities with consistent error handling."""
    
    @staticmethod
    def validate_single_item(value: Any, validator_func: Callable[[Any], T], 
                           field_name: str = "input") -> ValidationResult:
        """
        Validate a single item using the provided validator function.
        
        Args:
            value: Value to validate
            validator_func: Function to perform validation
            field_name: Name of the field being validated
            
        Returns:
            ValidationResult with validation outcome
        """
        try:
            validated_value = validator_func(value)
            return ValidationResult(
                is_valid=True,
                value=validated_value,
                field_name=field_name
            )
        except CLIValidationError as e:
            return ValidationResult(
                is_valid=False,
                error_message=str(e),
                field_name=field_name,
                severity=ValidationSeverity.ERROR,
                suggestions=ValidationHelper._get_validation_suggestions(field_name, str(e))
            )
        except Exception as e:
            logger.exception(f"Unexpected error validating {field_name}")
            return ValidationResult(
                is_valid=False,
                error_message=f"Unexpected validation error: {e}",
                field_name=field_name,
                severity=ValidationSeverity.CRITICAL
            )
    
    @staticmethod
    def validate_batch_input(inputs: List[Any], validator_func: Callable[[Any], T],
                           field_name: str = "input", 
                           continue_on_error: bool = True) -> BatchValidationResult[T]:
        """
        Centralized batch validation logic with comprehensive error handling.
        
        Args:
            inputs: List of values to validate
            validator_func: Function to validate each item
            field_name: Name of the field being validated
            continue_on_error: Whether to continue processing after errors
            
        Returns:
            BatchValidationResult containing validation outcomes
        """
        valid_items = []
        invalid_items = []
        warnings = []
        
        if not inputs:
            warnings.append(f"No {field_name} items provided for validation")
            return BatchValidationResult(
                valid_items=[],
                invalid_items=[],
                total_count=0,
                success_count=0,
                error_count=0,
                warnings=warnings
            )
        
        logger.info(f"Starting batch validation of {len(inputs)} {field_name} items")
        
        for i, item in enumerate(inputs):
            try:
                result = ValidationHelper.validate_single_item(
                    item, validator_func, f"{field_name}[{i}]"
                )
                
                if result.is_valid:
                    valid_items.append(result.value)
                else:
                    invalid_items.append(result)
                    
                    if not continue_on_error:
                        logger.warning(f"Stopping batch validation due to error in item {i}")
                        break
                        
            except Exception as e:
                logger.exception(f"Critical error processing {field_name} item {i}")
                error_result = ValidationResult(
                    is_valid=False,
                    error_message=f"Critical processing error: {e}",
                    field_name=f"{field_name}[{i}]",
                    severity=ValidationSeverity.CRITICAL
                )
                invalid_items.append(error_result)
                
                if not continue_on_error:
                    break
        
        success_count = len(valid_items)
        error_count = len(invalid_items)
        total_count = len(inputs)
        
        # Add warnings for low success rates
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        if success_rate < 50:
            warnings.append(f"Low success rate: {success_rate:.1f}% of {field_name} items validated successfully")
        
        logger.info(f"Batch validation complete: {success_count}/{total_count} items valid")
        
        return BatchValidationResult(
            valid_items=valid_items,
            invalid_items=invalid_items,
            total_count=total_count,
            success_count=success_count,
            error_count=error_count,
            warnings=warnings
        )
    
    @staticmethod
    def validate_csv_row_data(row_data: Dict[str, Any], 
                            field_validators: Dict[str, Callable],
                            row_number: int = 0) -> ValidationResult:
        """
        Validate a single CSV row with multiple fields.
        
        Args:
            row_data: Dictionary of field names to values
            field_validators: Dictionary mapping field names to validator functions
            row_number: Row number for error reporting
            
        Returns:
            ValidationResult for the entire row
        """
        validated_data = {}
        errors = []
        warnings = []
        
        for field_name, validator_func in field_validators.items():
            if field_name not in row_data:
                errors.append(f"Missing required field: {field_name}")
                continue
                
            field_result = ValidationHelper.validate_single_item(
                row_data[field_name], validator_func, field_name
            )
            
            if field_result.is_valid:
                validated_data[field_name] = field_result.value
            else:
                errors.append(f"{field_name}: {field_result.error_message}")
        
        # Check for extra fields
        extra_fields = set(row_data.keys()) - set(field_validators.keys())
        if extra_fields:
            warnings.append(f"Unexpected fields ignored: {', '.join(extra_fields)}")
        
        if errors:
            error_message = f"Row {row_number} validation failed: {'; '.join(errors)}"
            return ValidationResult(
                is_valid=False,
                error_message=error_message,
                field_name=f"row_{row_number}",
                suggestions=[
                    "Check field formats and required values",
                    "Ensure all required fields are present",
                    "Remove or correct invalid field values"
                ]
            )
        
        return ValidationResult(
            is_valid=True,
            value=validated_data,
            field_name=f"row_{row_number}"
        )
    
    @staticmethod
    def validate_file_batch(file_paths: List[Union[str, Path]], 
                          extensions: Optional[List[str]] = None,
                          must_exist: bool = True) -> BatchValidationResult[Path]:
        """
        Validate a batch of file paths with consistent error handling.
        
        Args:
            file_paths: List of file paths to validate
            extensions: Allowed file extensions (e.g., ['.pdf', '.csv'])
            must_exist: Whether files must exist
            
        Returns:
            BatchValidationResult containing valid file paths
        """
        def file_validator(path):
            return validate_file_path(
                path, must_exist=must_exist, extensions=extensions
            )
        
        return ValidationHelper.validate_batch_input(
            file_paths, file_validator, "file_path"
        )
    
    @staticmethod
    def validate_parts_data_batch(parts_data: List[Dict[str, Any]]) -> BatchValidationResult[Dict[str, Any]]:
        """
        Validate batch of parts data with specific field requirements.
        
        Args:
            parts_data: List of dictionaries containing part data
            
        Returns:
            BatchValidationResult containing validated parts data
        """
        field_validators = {
            'part_number': validate_part_number,
            'authorized_price': validate_price,
            # Optional fields don't need validation but will be included
        }
        
        def parts_validator(part_data):
            if not isinstance(part_data, dict):
                raise CLIValidationError("Part data must be a dictionary")
            
            result = ValidationHelper.validate_csv_row_data(
                part_data, field_validators
            )
            
            if not result.is_valid:
                raise CLIValidationError(result.error_message)
            
            return result.value
        
        return ValidationHelper.validate_batch_input(
            parts_data, parts_validator, "part_data"
        )
    
    @staticmethod
    def format_validation_errors(errors: List[ValidationResult], 
                               show_suggestions: bool = True,
                               max_errors_displayed: int = 10) -> str:
        """
        Standardized error formatting for validation results.
        
        Args:
            errors: List of ValidationResult objects with errors
            show_suggestions: Whether to include suggestions in output
            max_errors_displayed: Maximum number of errors to display
            
        Returns:
            Formatted error message string
        """
        if not errors:
            return "No validation errors found."
        
        error_lines = []
        error_lines.append(f"Found {len(errors)} validation error(s):")
        error_lines.append("-" * 50)
        
        # Group errors by severity
        critical_errors = [e for e in errors if e.severity == ValidationSeverity.CRITICAL]
        regular_errors = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        warnings = [e for e in errors if e.severity == ValidationSeverity.WARNING]
        
        # Display critical errors first
        if critical_errors:
            error_lines.append("\n🚨 CRITICAL ERRORS:")
            for error in critical_errors[:max_errors_displayed]:
                error_lines.append(f"  • {error.field_name}: {error.error_message}")
        
        # Display regular errors
        if regular_errors:
            error_lines.append("\n❌ ERRORS:")
            displayed_errors = regular_errors[:max_errors_displayed - len(critical_errors)]
            for error in displayed_errors:
                error_lines.append(f"  • {error.field_name}: {error.error_message}")
        
        # Display warnings
        if warnings:
            error_lines.append("\n⚠️  WARNINGS:")
            remaining_slots = max_errors_displayed - len(critical_errors) - len(regular_errors)
            displayed_warnings = warnings[:max(1, remaining_slots)]
            for warning in displayed_warnings:
                error_lines.append(f"  • {warning.field_name}: {warning.error_message}")
        
        # Show truncation message if needed
        total_displayed = len(critical_errors) + len(regular_errors) + len(warnings)
        if len(errors) > max_errors_displayed:
            error_lines.append(f"\n... and {len(errors) - max_errors_displayed} more errors")
        
        # Add suggestions if requested
        if show_suggestions:
            all_suggestions = []
            for error in errors[:max_errors_displayed]:
                if error.suggestions:
                    all_suggestions.extend(error.suggestions)
            
            if all_suggestions:
                error_lines.append("\n💡 SUGGESTIONS:")
                # Remove duplicates while preserving order
                unique_suggestions = list(dict.fromkeys(all_suggestions))
                for suggestion in unique_suggestions[:5]:  # Limit suggestions
                    error_lines.append(f"  • {suggestion}")
        
        return "\n".join(error_lines)
    
    @staticmethod
    def print_validation_summary(result: BatchValidationResult, 
                               operation_name: str = "validation") -> None:
        """
        Print a formatted summary of batch validation results.
        
        Args:
            result: BatchValidationResult to summarize
            operation_name: Name of the operation for display
        """
        print_info(f"\n{operation_name.title()} Summary:")
        print_info(f"  Total items: {result.total_count}")
        print_info(f"  Successful: {result.success_count}")
        print_info(f"  Failed: {result.error_count}")
        print_info(f"  Success rate: {result.success_rate:.1f}%")
        
        if result.has_warnings:
            print_warning(f"  Warnings: {len(result.warnings)}")
            for warning in result.warnings:
                print_warning(f"    • {warning}")
        
        if result.has_errors:
            error_message = ValidationHelper.format_validation_errors(
                result.invalid_items, show_suggestions=True
            )
            print_error(error_message)
    
    @staticmethod
    def _get_validation_suggestions(field_name: str, error_message: str) -> List[str]:
        """
        Generate context-specific validation suggestions.
        
        Args:
            field_name: Name of the field that failed validation
            error_message: The validation error message
            
        Returns:
            List of suggested fixes
        """
        suggestions = []
        error_lower = error_message.lower()
        field_lower = field_name.lower()
        
        if "part_number" in field_lower or "part number" in error_lower:
            suggestions.extend([
                "Use only letters, numbers, underscores, hyphens, and periods",
                "Ensure part number is 2-20 characters long",
                "Example: GP0171NAVY, ITEM-123, PART_001"
            ])
        
        elif "price" in field_lower or "price" in error_lower:
            suggestions.extend([
                "Enter a positive number (e.g., 15.50, 0.25)",
                "Use maximum 4 decimal places",
                "Remove currency symbols ($) if present"
            ])
        
        elif "file" in field_lower or "path" in field_lower:
            suggestions.extend([
                "Check that the file path is correct",
                "Ensure the file exists and is accessible",
                "Use absolute paths to avoid confusion"
            ])
        
        elif "email" in field_lower or "email" in error_lower:
            suggestions.extend([
                "Use valid email format: user@domain.com",
                "Check for typos in domain name"
            ])
        
        else:
            suggestions.extend([
                "Check the input format and try again",
                "Refer to command help for format requirements"
            ])
        
        return suggestions


# Convenience functions for common validation patterns
def validate_part_batch(part_numbers: List[str]) -> BatchValidationResult[str]:
    """Validate a batch of part numbers."""
    return ValidationHelper.validate_batch_input(
        part_numbers, validate_part_number, "part_number"
    )


def validate_price_batch(prices: List[Union[str, float]]) -> BatchValidationResult:
    """Validate a batch of prices."""
    return ValidationHelper.validate_batch_input(
        prices, validate_price, "price"
    )


def validate_config_keys_batch(keys: List[str]) -> BatchValidationResult[str]:
    """Validate a batch of configuration keys."""
    return ValidationHelper.validate_batch_input(
        keys, validate_configuration_key, "config_key"
    )