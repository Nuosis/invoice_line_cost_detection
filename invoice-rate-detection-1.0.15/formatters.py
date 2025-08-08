"""
Output formatting utilities for the CLI interface.

This module provides functions for formatting output, setting up logging,
and displaying data in various formats (table, CSV, JSON).
"""

import sys
import logging
import json
import csv
from typing import List, Dict, Any, Optional, Union, TextIO
from decimal import Decimal
from datetime import datetime
from pathlib import Path

import click


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Setup logging configuration for the CLI application.
    
    Args:
        verbose: Enable verbose (DEBUG) logging
        quiet: Suppress non-essential output (WARNING+ only)
    """
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Suppress verbose output from third-party libraries unless in debug mode
    if not verbose:
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)


def format_currency(amount: Union[Decimal, float, int]) -> str:
    """
    Format a numeric amount as currency.
    
    Args:
        amount: Numeric amount to format
        
    Returns:
        Formatted currency string
    """
    if amount is None:
        return "N/A"
    
    try:
        return f"${float(amount):.2f}"
    except (ValueError, TypeError):
        return str(amount)


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object as a string.
    
    Args:
        dt: Datetime object to format
        format_str: Format string for datetime formatting
        
    Returns:
        Formatted datetime string or "N/A" if None
    """
    if dt is None:
        return "N/A"
    
    try:
        return dt.strftime(format_str)
    except (ValueError, AttributeError):
        return str(dt)


def format_boolean(value: Optional[bool]) -> str:
    """
    Format a boolean value for display.
    
    Args:
        value: Boolean value to format
        
    Returns:
        "Yes", "No", or "N/A"
    """
    if value is None:
        return "N/A"
    return "Yes" if value else "No"


def truncate_text(text: Optional[str], max_length: int = 50) -> str:
    """
    Truncate text to a maximum length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def format_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None,
                 tablefmt: str = "grid") -> str:
    """
    Format data as a table using tabulate.
    
    Args:
        data: List of dictionaries containing row data
        headers: Optional list of column headers
        tablefmt: Table format style
        
    Returns:
        Formatted table string
    """
    if not data:
        return "No data to display."
    
    try:
        from tabulate import tabulate
        
        if headers is None:
            headers = list(data[0].keys()) if data else []
        
        # Convert data to list of lists for tabulate
        rows = []
        for row in data:
            formatted_row = []
            for header in headers:
                value = row.get(header, "")
                
                # Format special types
                if isinstance(value, (Decimal, float)) and header.lower() in ['price', 'amount', 'cost']:
                    formatted_row.append(format_currency(value))
                elif isinstance(value, datetime):
                    formatted_row.append(format_datetime(value))
                elif isinstance(value, bool):
                    formatted_row.append(format_boolean(value))
                elif isinstance(value, str) and len(value) > 50:
                    formatted_row.append(truncate_text(value))
                else:
                    formatted_row.append(str(value) if value is not None else "")
            
            rows.append(formatted_row)
        
        return tabulate(rows, headers=headers, tablefmt=tablefmt)
    
    except ImportError:
        # Fallback to simple formatting if tabulate is not available
        return format_simple_table(data, headers)


def format_simple_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> str:
    """
    Simple table formatting fallback when tabulate is not available.
    
    Args:
        data: List of dictionaries containing row data
        headers: Optional list of column headers
        
    Returns:
        Simple formatted table string
    """
    if not data:
        return "No data to display."
    
    if headers is None:
        headers = list(data[0].keys()) if data else []
    
    # Calculate column widths
    col_widths = {}
    for header in headers:
        col_widths[header] = len(header)
        for row in data:
            value = str(row.get(header, ""))
            col_widths[header] = max(col_widths[header], len(value))
    
    # Build table
    lines = []
    
    # Header
    header_line = " | ".join(header.ljust(col_widths[header]) for header in headers)
    lines.append(header_line)
    lines.append("-" * len(header_line))
    
    # Data rows
    for row in data:
        row_line = " | ".join(
            str(row.get(header, "")).ljust(col_widths[header]) 
            for header in headers
        )
        lines.append(row_line)
    
    return "\n".join(lines)


def format_json(data: Any, indent: int = 2) -> str:
    """
    Format data as JSON string.
    
    Args:
        data: Data to format as JSON
        indent: JSON indentation level
        
    Returns:
        Formatted JSON string
    """
    def json_serializer(obj):
        """Custom JSON serializer for special types."""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    try:
        return json.dumps(data, indent=indent, default=json_serializer, ensure_ascii=False)
    except TypeError as e:
        return f"Error formatting JSON: {e}"


def write_csv(data: List[Dict[str, Any]], output_file: Union[str, Path, TextIO],
              headers: Optional[List[str]] = None) -> None:
    """
    Write data to a CSV file.
    
    Args:
        data: List of dictionaries containing row data
        output_file: Output file path or file object
        headers: Optional list of column headers
    """
    if not data:
        return
    
    if headers is None:
        headers = list(data[0].keys()) if data else []
    
    # Handle file path or file object
    if isinstance(output_file, (str, Path)):
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            _write_csv_to_file(data, f, headers)
    else:
        _write_csv_to_file(data, output_file, headers)


def _write_csv_to_file(data: List[Dict[str, Any]], file_obj: TextIO, headers: List[str]) -> None:
    """
    Internal function to write CSV data to a file object.
    
    Args:
        data: List of dictionaries containing row data
        file_obj: File object to write to
        headers: List of column headers
    """
    writer = csv.DictWriter(file_obj, fieldnames=headers)
    writer.writeheader()
    
    for row in data:
        # Convert special types for CSV output
        csv_row = {}
        for header in headers:
            value = row.get(header)
            
            if isinstance(value, Decimal):
                csv_row[header] = float(value)
            elif isinstance(value, datetime):
                csv_row[header] = value.isoformat()
            elif value is None:
                csv_row[header] = ""
            else:
                csv_row[header] = str(value)
        
        writer.writerow(csv_row)


def print_success(message: str) -> None:
    """Print a success message with green checkmark."""
    click.echo(click.style(f"✓ {message}", fg='green'))


def print_warning(message: str) -> None:
    """Print a warning message with yellow warning symbol."""
    click.echo(click.style(f"⚠ Warning: {message}", fg='yellow'))


def print_error(message: str) -> None:
    """Print an error message with red X symbol."""
    click.echo(click.style(f"✗ Error: {message}", fg='red'), err=True)


def print_info(message: str) -> None:
    """Print an info message with blue info symbol."""
    click.echo(click.style(f"ℹ {message}", fg='blue'))


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation.
    
    Args:
        message: Confirmation message
        default: Default value if user just presses Enter
        
    Returns:
        True if user confirms, False otherwise
    """
    return click.confirm(message, default=default)


def prompt_for_input(message: str, default: Optional[str] = None, 
                    hide_input: bool = False, type=None) -> Any:
    """
    Prompt user for input with optional default and type conversion.
    
    Args:
        message: Prompt message
        default: Default value if user just presses Enter
        hide_input: Hide input (for passwords)
        type: Click type for input validation
        
    Returns:
        User input with appropriate type conversion
    """
    return click.prompt(message, default=default, hide_input=hide_input, type=type)


def display_summary(title: str, stats: Dict[str, Any]) -> None:
    """
    Display a formatted summary with title and statistics.
    
    Args:
        title: Summary title
        stats: Dictionary of statistics to display
    """
    click.echo(f"\n{title}")
    click.echo("=" * len(title))
    
    for key, value in stats.items():
        # Format the key (convert underscores to spaces and title case)
        formatted_key = key.replace('_', ' ').title()
        
        # Format the value based on type
        if isinstance(value, (Decimal, float)) and 'price' in key.lower():
            formatted_value = format_currency(value)
        elif isinstance(value, datetime):
            formatted_value = format_datetime(value)
        elif isinstance(value, bool):
            formatted_value = format_boolean(value)
        else:
            formatted_value = str(value)
        
        click.echo(f"  {formatted_key}: {formatted_value}")


# Aliases for backward compatibility with discovery_commands
def format_success(message: str) -> str:
    """Format a success message and return it as a string."""
    return click.style(f"✓ {message}", fg='green')


def format_error(message: str) -> str:
    """Format an error message and return it as a string."""
    return click.style(f"✗ Error: {message}", fg='red')


def format_warning(message: str) -> str:
    """Format a warning message and return it as a string."""
    return click.style(f"⚠ Warning: {message}", fg='yellow')


def format_info(message: str) -> str:
    """Format an info message and return it as a string."""
    return click.style(f"ℹ {message}", fg='blue')


class ReportFormatter:
    """
    Report formatting class for generating various output formats.
    
    This class provides methods for formatting validation results, parts data,
    and other report information in different output formats (CSV, JSON, table).
    """
    
    def __init__(self, output_format: str = 'csv'):
        """
        Initialize the report formatter.
        
        Args:
            output_format: Default output format ('csv', 'json', 'table')
        """
        self.output_format = output_format.lower()
        self.supported_formats = ['csv', 'json', 'table', 'txt']
    
    def format_validation_results(self, results: List[Dict[str, Any]],
                                 output_format: Optional[str] = None) -> str:
        """
        Format validation results for output.
        
        Args:
            results: List of validation result dictionaries
            output_format: Override default output format
            
        Returns:
            Formatted results string
        """
        format_type = output_format or self.output_format
        
        if format_type == 'json':
            return format_json(results)
        elif format_type == 'table':
            return format_table(results)
        elif format_type in ['csv', 'txt']:
            return self._format_csv_string(results)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def format_parts_list(self, parts: List[Dict[str, Any]],
                         output_format: Optional[str] = None) -> str:
        """
        Format parts list for output.
        
        Args:
            parts: List of part dictionaries
            output_format: Override default output format
            
        Returns:
            Formatted parts list string
        """
        format_type = output_format or self.output_format
        
        if format_type == 'json':
            return format_json(parts)
        elif format_type == 'table':
            return format_table(parts)
        elif format_type in ['csv', 'txt']:
            return self._format_csv_string(parts)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def format_statistics(self, stats: Dict[str, Any],
                         output_format: Optional[str] = None) -> str:
        """
        Format statistics for output.
        
        Args:
            stats: Statistics dictionary
            output_format: Override default output format
            
        Returns:
            Formatted statistics string
        """
        format_type = output_format or self.output_format
        
        if format_type == 'json':
            return format_json(stats)
        elif format_type == 'table':
            # Convert stats dict to list of dicts for table formatting
            stats_list = [{'Metric': k, 'Value': v} for k, v in stats.items()]
            return format_table(stats_list)
        else:
            # Default to simple key-value format
            lines = []
            for key, value in stats.items():
                formatted_key = key.replace('_', ' ').title()
                if isinstance(value, (Decimal, float)) and 'price' in key.lower():
                    formatted_value = format_currency(value)
                elif isinstance(value, datetime):
                    formatted_value = format_datetime(value)
                elif isinstance(value, bool):
                    formatted_value = format_boolean(value)
                else:
                    formatted_value = str(value)
                lines.append(f"{formatted_key}: {formatted_value}")
            return '\n'.join(lines)
    
    def write_report(self, data: List[Dict[str, Any]], output_file: Union[str, Path],
                    headers: Optional[List[str]] = None) -> None:
        """
        Write report data to a file.
        
        Args:
            data: Report data to write
            output_file: Output file path
            headers: Optional column headers
        """
        output_path = Path(output_file)
        
        if output_path.suffix.lower() == '.json':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(format_json(data))
        elif output_path.suffix.lower() == '.csv':
            write_csv(data, output_path, headers)
        else:
            # Default to text format
            with open(output_path, 'w', encoding='utf-8') as f:
                if self.output_format == 'table':
                    f.write(format_table(data, headers))
                else:
                    f.write(self._format_csv_string(data, headers))
    
    def _format_csv_string(self, data: List[Dict[str, Any]],
                          headers: Optional[List[str]] = None) -> str:
        """
        Format data as CSV string.
        
        Args:
            data: Data to format
            headers: Optional column headers
            
        Returns:
            CSV formatted string
        """
        if not data:
            return "No data to display."
        
        import io
        output = io.StringIO()
        
        if headers is None:
            headers = list(data[0].keys()) if data else []
        
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        for row in data:
            # Convert special types for CSV output
            csv_row = {}
            for header in headers:
                value = row.get(header)
                
                if isinstance(value, Decimal):
                    csv_row[header] = float(value)
                elif isinstance(value, datetime):
                    csv_row[header] = value.isoformat()
                elif value is None:
                    csv_row[header] = ""
                else:
                    csv_row[header] = str(value)
            
            writer.writerow(csv_row)
        
        return output.getvalue()