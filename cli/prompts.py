"""
Interactive prompt utilities for the CLI interface.

This module provides functions for interactive user input, confirmations,
and guided workflows for the CLI application.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal

import click

from cli.validators import (
    validate_part_number, validate_price, validate_file_path,
    validate_directory_path, validate_output_format
)
from cli.exceptions import ValidationError, UserCancelledError
from cli.formatters import print_info, print_warning, format_currency


def prompt_for_input_path(message: str = "Enter path to folder containing PDF invoices",
                         must_exist: bool = True) -> Path:
    """
    Prompt user for an input path (file or directory).
    
    Args:
        message: Prompt message
        must_exist: Whether the path must exist
        
    Returns:
        Validated Path object
        
    Raises:
        UserCancelledError: If user cancels input
    """
    while True:
        try:
            path_str = click.prompt(message, type=str)
            if not path_str.strip():
                raise ValidationError("Path cannot be empty")
            
            path = Path(path_str.strip()).expanduser().resolve()
            
            if must_exist and not path.exists():
                print_warning(f"Path does not exist: {path}")
                if not click.confirm("Would you like to try a different path?", default=True):
                    raise UserCancelledError()
                continue
            
            return path
            
        except ValidationError as e:
            print_warning(str(e))
            if not click.confirm("Would you like to try again?", default=True):
                raise UserCancelledError()
        except click.Abort:
            raise UserCancelledError()


def prompt_for_output_path(message: str = "Enter output file path",
                          default: str = "report.csv") -> Path:
    """
    Prompt user for an output file path.
    
    Args:
        message: Prompt message
        default: Default file path
        
    Returns:
        Validated Path object
        
    Raises:
        UserCancelledError: If user cancels input
    """
    while True:
        try:
            path_str = click.prompt(message, default=default, type=str)
            path = Path(path_str.strip()).expanduser().resolve()
            
            # Check if parent directory exists
            if not path.parent.exists():
                if click.confirm(f"Create directory {path.parent}?", default=True):
                    path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    continue
            
            # Check if file already exists
            if path.exists():
                if not click.confirm(f"File {path} already exists. Overwrite?", default=False):
                    continue
            
            return path
            
        except ValidationError as e:
            print_warning(str(e))
            if not click.confirm("Would you like to try again?", default=True):
                raise UserCancelledError()
        except click.Abort:
            raise UserCancelledError()


def prompt_for_output_format(message: str = "Select output format",
                           default: str = "csv") -> str:
    """
    Prompt user to select output format.
    
    Args:
        message: Prompt message
        default: Default format
        
    Returns:
        Selected format string
        
    Raises:
        UserCancelledError: If user cancels input
    """
    formats = {
        '1': 'csv',
        '2': 'txt',
        '3': 'json'
    }
    
    while True:
        try:
            click.echo(f"\n{message}:")
            click.echo("  1) CSV (recommended for Excel)")
            click.echo("  2) TXT (plain text)")
            click.echo("  3) JSON (structured data)")
            
            choice = click.prompt("Enter choice", default='1', type=str)
            
            if choice in formats:
                return formats[choice]
            elif choice.lower() in formats.values():
                return choice.lower()
            else:
                print_warning("Invalid choice. Please select 1, 2, or 3.")
                continue
                
        except click.Abort:
            raise UserCancelledError()


def prompt_for_validation_mode(message: str = "Select validation mode") -> str:
    """
    Prompt user to select validation mode.
    
    Args:
        message: Prompt message
        
    Returns:
        Selected validation mode
        
    Raises:
        UserCancelledError: If user cancels input
    """
    modes = {
        '1': 'parts_based',
        '2': 'threshold_based'
    }
    
    while True:
        try:
            click.echo(f"\n{message}:")
            click.echo("  1) Parts-based validation (recommended)")
            click.echo("     Uses master parts database for price validation")
            click.echo("  2) Threshold-based validation")
            click.echo("     Flags items above a price threshold")
            
            choice = click.prompt("Enter choice", default='1', type=str)
            
            if choice in modes:
                return modes[choice]
            else:
                print_warning("Invalid choice. Please select 1 or 2.")
                continue
                
        except click.Abort:
            raise UserCancelledError()


def prompt_for_threshold(message: str = "Enter price threshold",
                        default: float = 0.30) -> Decimal:
    """
    Prompt user for price threshold.
    
    Args:
        message: Prompt message
        default: Default threshold value
        
    Returns:
        Validated threshold as Decimal
        
    Raises:
        UserCancelledError: If user cancels input
    """
    while True:
        try:
            threshold_str = click.prompt(
                f"{message} (items above this price will be flagged)",
                default=str(default),
                type=str
            )
            
            return validate_price(threshold_str)
            
        except ValidationError as e:
            print_warning(str(e))
            if not click.confirm("Would you like to try again?", default=True):
                raise UserCancelledError()
        except click.Abort:
            raise UserCancelledError()


def prompt_for_part_details(part_number: Optional[str] = None) -> Dict[str, Any]:
    """
    Prompt user for part details when adding a new part.
    
    Args:
        part_number: Pre-filled part number (optional)
        
    Returns:
        Dictionary containing part details
        
    Raises:
        UserCancelledError: If user cancels input
    """
    details = {}
    
    try:
        # Part number
        if part_number:
            details['part_number'] = validate_part_number(part_number)
            click.echo(f"Part number: {details['part_number']}")
        else:
            while True:
                try:
                    part_num = click.prompt("Part number", type=str)
                    details['part_number'] = validate_part_number(part_num)
                    break
                except ValidationError as e:
                    print_warning(str(e))
                    if not click.confirm("Would you like to try again?", default=True):
                        raise UserCancelledError()
        
        # Authorized price
        while True:
            try:
                price_str = click.prompt("Authorized price", type=str)
                details['authorized_price'] = validate_price(price_str)
                break
            except ValidationError as e:
                print_warning(str(e))
                if not click.confirm("Would you like to try again?", default=True):
                    raise UserCancelledError()
        
        # Optional fields
        details['description'] = click.prompt("Description (optional)", default="", type=str)
        details['category'] = click.prompt("Category (optional)", default="", type=str)
        details['notes'] = click.prompt("Notes (optional)", default="", type=str)
        
        # Convert empty strings to None
        for key in ['description', 'category', 'notes']:
            if not details[key].strip():
                details[key] = None
        
        return details
        
    except click.Abort:
        raise UserCancelledError()


def prompt_for_confirmation(message: str, default: bool = False,
                          show_details: Optional[Dict[str, Any]] = None) -> bool:
    """
    Prompt user for confirmation with optional details display.
    
    Args:
        message: Confirmation message
        default: Default response
        show_details: Optional details to display before confirmation
        
    Returns:
        True if user confirms, False otherwise
        
    Raises:
        UserCancelledError: If user cancels input
    """
    try:
        if show_details:
            click.echo("\nDetails:")
            for key, value in show_details.items():
                formatted_key = key.replace('_', ' ').title()
                if isinstance(value, Decimal):
                    formatted_value = format_currency(value)
                else:
                    formatted_value = str(value) if value is not None else "N/A"
                click.echo(f"  {formatted_key}: {formatted_value}")
            click.echo()
        
        return click.confirm(message, default=default)
        
    except click.Abort:
        raise UserCancelledError()


def prompt_for_choice(message: str, choices: List[str],
                     default: Optional[str] = None) -> str:
    """
    Prompt user to select from a list of choices.
    
    Args:
        message: Prompt message
        choices: List of available choices
        default: Default choice (optional)
        
    Returns:
        Selected choice
        
    Raises:
        UserCancelledError: If user cancels input
    """
    while True:
        try:
            click.echo(f"\n{message}:")
            for i, choice in enumerate(choices, 1):
                marker = " (default)" if choice == default else ""
                click.echo(f"  {i}) {choice}{marker}")
            
            if default:
                default_index = str(choices.index(default) + 1)
                choice_str = click.prompt("Enter choice", default=default_index, type=str)
            else:
                choice_str = click.prompt("Enter choice", type=str)
            
            try:
                choice_index = int(choice_str) - 1
                if 0 <= choice_index < len(choices):
                    return choices[choice_index]
                else:
                    print_warning(f"Invalid choice. Please select 1-{len(choices)}.")
                    continue
            except ValueError:
                # Check if user entered the choice name directly
                for choice in choices:
                    if choice.lower() == choice_str.lower():
                        return choice
                
                print_warning(f"Invalid choice. Please select 1-{len(choices)}.")
                continue
                
        except click.Abort:
            raise UserCancelledError()


def prompt_for_multiple_choice(message: str, choices: List[str],
                              min_selections: int = 0,
                              max_selections: Optional[int] = None) -> List[str]:
    """
    Prompt user to select multiple items from a list of choices.
    
    Args:
        message: Prompt message
        choices: List of available choices
        min_selections: Minimum number of selections required
        max_selections: Maximum number of selections allowed
        
    Returns:
        List of selected choices
        
    Raises:
        UserCancelledError: If user cancels input
    """
    while True:
        try:
            click.echo(f"\n{message}:")
            click.echo("(Enter comma-separated numbers, e.g., '1,3,5')")
            
            for i, choice in enumerate(choices, 1):
                click.echo(f"  {i}) {choice}")
            
            selection_str = click.prompt("Enter selections", type=str)
            
            if not selection_str.strip():
                if min_selections == 0:
                    return []
                else:
                    print_warning(f"You must select at least {min_selections} item(s).")
                    continue
            
            try:
                # Parse comma-separated selections
                selections = []
                for part in selection_str.split(','):
                    part = part.strip()
                    if part:
                        choice_index = int(part) - 1
                        if 0 <= choice_index < len(choices):
                            if choices[choice_index] not in selections:
                                selections.append(choices[choice_index])
                        else:
                            print_warning(f"Invalid choice: {part}")
                            selections = []
                            break
                
                if not selections and selection_str.strip():
                    continue
                
                # Validate selection count
                if len(selections) < min_selections:
                    print_warning(f"You must select at least {min_selections} item(s).")
                    continue
                
                if max_selections and len(selections) > max_selections:
                    print_warning(f"You can select at most {max_selections} item(s).")
                    continue
                
                return selections
                
            except ValueError:
                print_warning("Invalid input. Please enter comma-separated numbers.")
                continue
                
        except click.Abort:
            raise UserCancelledError()


def show_welcome_message():
    """Display welcome message for interactive mode."""
    click.echo("=" * 60)
    click.echo("    Invoice Rate Detection System")
    click.echo("=" * 60)
    click.echo()
    click.echo("Welcome! This tool will help you process PDF invoices")
    click.echo("and detect pricing anomalies.")
    click.echo()
    click.echo("You can press Ctrl+C at any time to cancel.")
    click.echo()


def show_processing_summary(stats: Dict[str, Any]):
    """
    Display processing summary after completion.
    
    Args:
        stats: Dictionary containing processing statistics
    """
    click.echo()
    click.echo("=" * 50)
    click.echo("    Processing Complete!")
    click.echo("=" * 50)
    
    files_processed = stats.get('files_processed', 0)
    anomalies_found = stats.get('anomalies_found', 0)
    unknown_parts = stats.get('unknown_parts', 0)
    total_overcharge = stats.get('total_overcharge', 0)
    report_file = stats.get('report_file', 'N/A')
    
    click.echo(f"Files processed: {files_processed}")
    click.echo(f"Anomalies found: {anomalies_found}")
    if unknown_parts > 0:
        click.echo(f"Unknown parts: {unknown_parts}")
    if total_overcharge > 0:
        click.echo(f"Total overcharge: {format_currency(total_overcharge)}")
    click.echo(f"Report saved: {report_file}")
    click.echo()
    
    if anomalies_found > 0:
        print_info(f"Found {anomalies_found} pricing anomalies. Check the report for details.")
    else:
        print_info("No pricing anomalies found. All prices appear to be correct.")


def prompt_for_next_action(unknown_parts: int = 0) -> str:
    """
    Prompt user for next action after processing.
    
    Args:
        unknown_parts: Number of unknown parts discovered
        
    Returns:
        Selected action
        
    Raises:
        UserCancelledError: If user cancels input
    """
    actions = ["Exit"]
    
    if unknown_parts > 0:
        actions.insert(0, "Review unknown parts")
        actions.insert(1, "Add parts to database")
    
    actions.insert(-1, "Process more invoices")
    
    try:
        return prompt_for_choice("What would you like to do next?", actions, default="Exit")
    except UserCancelledError:
        return "Exit"