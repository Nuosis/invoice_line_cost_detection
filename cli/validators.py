"""
Input validation utilities for the CLI interface.

This module provides validation functions for user inputs, file paths,
and data formats used throughout the CLI application.
"""

import re
import os
from pathlib import Path
from typing import Optional, List, Union
from decimal import Decimal, InvalidOperation

import click

from cli.exceptions import ValidationError


def validate_part_number(part_number: str) -> str:
    """
    Validate a part number format.
    
    Args:
        part_number: Part number to validate
        
    Returns:
        Validated part number (stripped and uppercase)
        
    Raises:
        ValidationError: If part number format is invalid
    """
    if not part_number or not isinstance(part_number, str):
        raise ValidationError("Part number must be a non-empty string")
    
    # Strip whitespace and convert to uppercase for consistency
    part_number = part_number.strip().upper()
    
    if not part_number:
        raise ValidationError("Part number cannot be empty or whitespace only")
    
    # Check length constraints
    if len(part_number) < 2:
        raise ValidationError("Part number must be at least 2 characters long")
    
    if len(part_number) > 20:
        raise ValidationError("Part number cannot exceed 20 characters")
    
    # Check format (alphanumeric with allowed special characters)
    if not re.match(r'^[A-Z0-9_\-\.]+$', part_number):
        raise ValidationError(
            "Part number can only contain letters, numbers, underscores, hyphens, and periods"
        )
    
    return part_number


def validate_description(description: str) -> str:
    """
    Validate a part description.
    
    Args:
        description: Description to validate
        
    Returns:
        Validated description (stripped)
        
    Raises:
        ValidationError: If description format is invalid
    """
    if not description or not isinstance(description, str):
        raise ValidationError("Description must be a non-empty string")
    
    # Strip whitespace
    description = description.strip()
    
    if not description:
        raise ValidationError("Description cannot be empty or whitespace only")
    
    # Check length constraints
    if len(description) < 3:
        raise ValidationError("Description must be at least 3 characters long")
    
    if len(description) > 200:
        raise ValidationError("Description cannot exceed 200 characters")
    
    return description


def validate_price(price: Union[str, float, Decimal]) -> Decimal:
    """
    Validate and convert a price value.
    
    Args:
        price: Price value to validate
        
    Returns:
        Validated price as Decimal
        
    Raises:
        ValidationError: If price format is invalid
    """
    if price is None:
        raise ValidationError("Price cannot be None")
    
    try:
        # Convert to Decimal for precise handling
        if isinstance(price, str):
            # Remove currency symbols and whitespace
            price_str = price.strip().replace('$', '').replace(',', '')
            decimal_price = Decimal(price_str)
        else:
            decimal_price = Decimal(str(price))
        
        # Check if price is positive
        if decimal_price <= 0:
            raise ValidationError("Price must be positive")
        
        # Check decimal places (max 4)
        if decimal_price.as_tuple().exponent < -4:
            raise ValidationError("Price cannot have more than 4 decimal places")
        
        # Check reasonable range (0.01 to 999999.99)
        if decimal_price < Decimal('0.01'):
            raise ValidationError("Price must be at least $0.01")
        
        if decimal_price > Decimal('999999.99'):
            raise ValidationError("Price cannot exceed $999,999.99")
        
        return decimal_price
        
    except (InvalidOperation, ValueError) as e:
        raise ValidationError(f"Invalid price format: {price}")


def validate_file_path(file_path: Union[str, Path], must_exist: bool = True,
                      must_be_file: bool = True, extensions: Optional[List[str]] = None) -> Path:
    """
    Validate a file path.
    
    Args:
        file_path: File path to validate
        must_exist: Whether the file must exist
        must_be_file: Whether the path must be a file (not directory)
        extensions: List of allowed file extensions (e.g., ['.pdf', '.csv'])
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If file path is invalid
    """
    if not file_path:
        raise ValidationError("File path cannot be empty")
    
    path = Path(file_path).resolve()
    
    if must_exist and not path.exists():
        raise ValidationError(f"File does not exist: {path}")
    
    if must_exist and must_be_file and not path.is_file():
        raise ValidationError(f"Path is not a file: {path}")
    
    if extensions:
        # Normalize extensions to lowercase with dots
        normalized_extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                               for ext in extensions]
        
        if path.suffix.lower() not in normalized_extensions:
            raise ValidationError(
                f"File must have one of these extensions: {', '.join(normalized_extensions)}"
            )
    
    return path


def validate_directory_path(dir_path: Union[str, Path], must_exist: bool = True,
                           create_if_missing: bool = False) -> Path:
    """
    Validate a directory path.
    
    Args:
        dir_path: Directory path to validate
        must_exist: Whether the directory must exist
        create_if_missing: Whether to create the directory if it doesn't exist
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If directory path is invalid
    """
    if not dir_path:
        raise ValidationError("Directory path cannot be empty")
    
    path = Path(dir_path).resolve()
    
    if not path.exists():
        if create_if_missing:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValidationError(f"Cannot create directory {path}: {e}")
        elif must_exist:
            raise ValidationError(f"Directory does not exist: {path}")
    
    if path.exists() and not path.is_dir():
        raise ValidationError(f"Path is not a directory: {path}")
    
    return path


def validate_output_format(format_str: str) -> str:
    """
    Validate output format string.
    
    Args:
        format_str: Format string to validate
        
    Returns:
        Validated format string (lowercase)
        
    Raises:
        ValidationError: If format is not supported
    """
    if not format_str:
        raise ValidationError("Output format cannot be empty")
    
    format_str = format_str.lower().strip()
    valid_formats = ['csv', 'txt', 'json', 'table']
    
    if format_str not in valid_formats:
        raise ValidationError(
            f"Invalid output format '{format_str}'. "
            f"Supported formats: {', '.join(valid_formats)}"
        )
    
    return format_str


def validate_email(email: str) -> str:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email address (lowercase)
        
    Raises:
        ValidationError: If email format is invalid
    """
    if not email:
        raise ValidationError("Email address cannot be empty")
    
    email = email.strip().lower()
    
    # Basic email validation regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValidationError(f"Invalid email address format: {email}")
    
    return email


def validate_date_string(date_str: str, formats: Optional[List[str]] = None) -> str:
    """
    Validate date string format.
    
    Args:
        date_str: Date string to validate
        formats: List of allowed date formats (default: common formats)
        
    Returns:
        Validated date string
        
    Raises:
        ValidationError: If date format is invalid
    """
    if not date_str:
        raise ValidationError("Date cannot be empty")
    
    date_str = date_str.strip()
    
    if formats is None:
        formats = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
            r'^\d{2}-\d{2}-\d{4}$',  # MM-DD-YYYY
            r'^\d{1,2}/\d{1,2}/\d{4}$',  # M/D/YYYY
        ]
    
    for format_pattern in formats:
        if re.match(format_pattern, date_str):
            return date_str
    
    raise ValidationError(
        f"Invalid date format: {date_str}. "
        f"Expected formats: YYYY-MM-DD, MM/DD/YYYY, MM-DD-YYYY"
    )


def validate_positive_integer(value: Union[str, int], min_value: int = 1,
                             max_value: Optional[int] = None) -> int:
    """
    Validate positive integer value.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value (optional)
        
    Returns:
        Validated integer
        
    Raises:
        ValidationError: If value is not a valid positive integer
    """
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid integer value: {value}")
    
    if int_value < min_value:
        raise ValidationError(f"Value must be at least {min_value}")
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(f"Value cannot exceed {max_value}")
    
    return int_value


def validate_configuration_key(key: str) -> str:
    """
    Validate configuration key format.
    
    Args:
        key: Configuration key to validate
        
    Returns:
        Validated configuration key
        
    Raises:
        ValidationError: If key format is invalid
    """
    if not key:
        raise ValidationError("Configuration key cannot be empty")
    
    key = key.strip().lower()
    
    # Configuration keys should be lowercase with underscores
    if not re.match(r'^[a-z][a-z0-9_]*$', key):
        raise ValidationError(
            "Configuration key must start with a letter and contain only "
            "lowercase letters, numbers, and underscores"
        )
    
    if len(key) > 50:
        raise ValidationError("Configuration key cannot exceed 50 characters")
    
    return key


def validate_session_id(session_id: str) -> str:
    """
    Validate processing session ID format.
    
    Args:
        session_id: Session ID to validate
        
    Returns:
        Validated session ID
        
    Raises:
        ValidationError: If session ID format is invalid
    """
    if not session_id:
        raise ValidationError("Session ID cannot be empty")
    
    session_id = session_id.strip()
    
    # Session IDs should be alphanumeric with hyphens (UUID-like)
    if not re.match(r'^[a-zA-Z0-9\-]+$', session_id):
        raise ValidationError(
            "Session ID can only contain letters, numbers, and hyphens"
        )
    
    if len(session_id) < 8 or len(session_id) > 50:
        raise ValidationError("Session ID must be between 8 and 50 characters")
    
    return session_id


# Click parameter types for use with Click commands
class PartNumberType(click.ParamType):
    """Click parameter type for part numbers."""
    name = "part_number"
    
    def convert(self, value, param, ctx):
        try:
            return validate_part_number(value)
        except ValidationError as e:
            self.fail(str(e), param, ctx)


class PriceType(click.ParamType):
    """Click parameter type for prices."""
    name = "price"
    
    def convert(self, value, param, ctx):
        try:
            return validate_price(value)
        except ValidationError as e:
            self.fail(str(e), param, ctx)


class OutputFormatType(click.ParamType):
    """Click parameter type for output formats."""
    name = "format"
    
    def convert(self, value, param, ctx):
        try:
            return validate_output_format(value)
        except ValidationError as e:
            self.fail(str(e), param, ctx)


# Create instances for use in Click commands
PART_NUMBER = PartNumberType()
PRICE = PriceType()
OUTPUT_FORMAT = OutputFormatType()