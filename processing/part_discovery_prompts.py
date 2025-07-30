"""
Interactive prompts for the Part Discovery workflow.

This module provides user-friendly CLI prompts for discovering and adding
unknown parts to the master parts database during invoice processing.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List
from dataclasses import asdict

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, FloatPrompt
from rich.text import Text

from cli.exceptions import UserCancelledError, ValidationError
from cli.validators import validate_part_number, validate_price, validate_description
from processing.part_discovery_models import UnknownPartContext
from database.models import Part


logger = logging.getLogger(__name__)


class PartDiscoveryPrompt:
    """
    Interactive prompt handler for part discovery workflow.
    
    This class provides user-friendly prompts for discovering unknown parts
    and collecting the necessary information to add them to the database.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the prompt handler.
        
        Args:
            console: Rich console instance for formatted output
        """
        self.console = console or Console()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def prompt_for_unknown_part(self, context: UnknownPartContext, 
                              occurrence_count: int = 1) -> Dict[str, Any]:
        """
        Prompt user for action on an unknown part.
        
        Args:
            context: Unknown part context with discovered information
            occurrence_count: Number of times this part appears in current session
            
        Returns:
            Dictionary with user decision and part details if applicable
            
        Raises:
            UserCancelledError: If user cancels the operation
        """
        try:
            # Display unknown part information
            self._display_unknown_part_info(context, occurrence_count)
            
            # Get user decision
            action = self._prompt_for_action()
            
            result = {'action': action}
            
            if action == 'add_to_database_now':
                # Collect part details for immediate addition
                part_details = self._collect_part_details(context)
                result['part_details'] = part_details
            elif action == 'add_to_database_later':
                # Collect minimal details for later review
                part_details = self._collect_minimal_part_details(context)
                result['part_details'] = part_details
            
            return result
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise UserCancelledError("User cancelled part discovery")
        except Exception as e:
            self.logger.error(f"Error in part discovery prompt: {e}")
            raise
    
    def _display_unknown_part_info(self, context: UnknownPartContext, occurrence_count: int):
        """Display information about the unknown part."""
        # Create a rich table for part information
        table = Table(title="Unknown Part Discovered", show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan", width=20)
        table.add_column("Value", style="white")
        
        # Add part information rows
        table.add_row("Part Number", context.part_number or "N/A")
        table.add_row("Description", context.description or "N/A")
        table.add_row("Discovered Price", f"${context.discovered_price:.2f}" if context.discovered_price else "N/A")
        table.add_row("Quantity", str(context.quantity) if context.quantity else "N/A")
        table.add_row("Size", context.size or "N/A")
        table.add_row("Item Type", context.item_type or "N/A")
        table.add_row("Invoice Number", context.invoice_number or "N/A")
        table.add_row("Invoice Date", context.invoice_date or "N/A")
        
        if occurrence_count > 1:
            table.add_row("Occurrences", f"{occurrence_count} times in this session", style="yellow")
        
        self.console.print()
        self.console.print(table)
        self.console.print()
    
    def _prompt_for_action(self) -> str:
        """Prompt user for action to take on unknown part."""
        self.console.print("[bold]What would you like to do with this unknown part?[/bold]")
        self.console.print()
        
        choices = [
            ("1", "add_to_database_now", "Add to database now (with full details)"),
            ("2", "add_to_database_later", "Mark for later review (collect for batch processing)"),
            ("3", "skip_this_part", "Skip this part (don't add to database)"),
            ("4", "skip_all_remaining", "Skip all remaining unknown parts"),
            ("5", "stop_processing", "Stop processing and exit")
        ]
        
        for key, _, description in choices:
            self.console.print(f"  [cyan]{key}[/cyan]. {description}")
        
        self.console.print()
        
        while True:
            try:
                choice = Prompt.ask(
                    "Enter your choice",
                    choices=[key for key, _, _ in choices],
                    default="1"
                )
                
                # Map choice to action
                action_map = {key: action for key, action, _ in choices}
                return action_map[choice]
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.console.print(f"[red]Invalid choice. Please try again.[/red]")
    
    def _collect_part_details(self, context: UnknownPartContext) -> Dict[str, Any]:
        """Collect full part details for immediate database addition."""
        self.console.print("\n[bold]Please provide details for the new part:[/bold]")
        
        details = {}
        
        # Part number (pre-filled from context)
        part_number = context.part_number
        if part_number:
            confirm_part_number = Confirm.ask(
                f"Use part number '{part_number}'?",
                default=True
            )
            if not confirm_part_number:
                part_number = self._prompt_for_part_number()
        else:
            part_number = self._prompt_for_part_number()
        
        details['part_number'] = part_number
        
        # Authorized price
        suggested_price = context.discovered_price
        if suggested_price:
            self.console.print(f"Discovered price: ${suggested_price:.2f}")
            use_discovered = Confirm.ask("Use this as the authorized price?", default=True)
            if use_discovered:
                details['authorized_price'] = suggested_price
            else:
                details['authorized_price'] = self._prompt_for_price()
        else:
            details['authorized_price'] = self._prompt_for_price()
        
        # Description
        suggested_description = context.description
        if suggested_description:
            self.console.print(f"Discovered description: {suggested_description}")
            use_discovered = Confirm.ask("Use this description?", default=True)
            if use_discovered:
                details['description'] = suggested_description
            else:
                details['description'] = self._prompt_for_description()
        else:
            details['description'] = self._prompt_for_description()
        
        # Category (optional)
        details['category'] = Prompt.ask(
            "Category (optional)",
            default="",
            show_default=False
        ) or None
        
        # Size (from context or prompt)
        if context.size:
            details['size'] = context.size
        else:
            details['size'] = Prompt.ask(
                "Size (optional)",
                default="",
                show_default=False
            ) or None
        
        # Item type (from context or prompt)
        if context.item_type:
            details['item_type'] = context.item_type
        else:
            details['item_type'] = Prompt.ask(
                "Item type (optional)",
                default="",
                show_default=False
            ) or None
        
        # Notes
        details['notes'] = Prompt.ask(
            "Notes (optional)",
            default="Added via interactive discovery",
            show_default=True
        )
        
        return details
    
    def _collect_minimal_part_details(self, context: UnknownPartContext) -> Dict[str, Any]:
        """Collect minimal part details for later review."""
        details = {
            'part_number': context.part_number,
            'discovered_price': context.discovered_price,
            'description': context.description,
            'size': context.size,
            'item_type': context.item_type,
            'notes': 'Marked for later review'
        }
        
        # Allow user to add a quick note
        note = Prompt.ask(
            "Add a note for later review (optional)",
            default="",
            show_default=False
        )
        if note:
            details['notes'] = f"Marked for later review: {note}"
        
        return details
    
    def _prompt_for_part_number(self) -> str:
        """Prompt for part number with validation."""
        while True:
            try:
                part_number = Prompt.ask("Part number", default="").strip()
                if not part_number:
                    self.console.print("[red]Part number is required.[/red]")
                    continue
                
                # Validate part number
                validate_part_number(part_number)
                return part_number
                
            except ValidationError as e:
                self.console.print(f"[red]{e}[/red]")
            except KeyboardInterrupt:
                raise
    
    def _prompt_for_price(self) -> Decimal:
        """Prompt for authorized price with validation."""
        while True:
            try:
                price_str = Prompt.ask("Authorized price ($)", default="")
                if not price_str:
                    self.console.print("[red]Price is required.[/red]")
                    continue
                
                # Remove $ if present
                price_str = price_str.replace('$', '').strip()
                price = Decimal(price_str)
                
                # Validate price
                validate_price(price)
                return price
                
            except (InvalidOperation, ValueError):
                self.console.print("[red]Please enter a valid price (e.g., 15.50).[/red]")
            except ValidationError as e:
                self.console.print(f"[red]{e}[/red]")
            except KeyboardInterrupt:
                raise
    
    def _prompt_for_description(self) -> str:
        """Prompt for part description with validation."""
        while True:
            try:
                description = Prompt.ask("Description", default="").strip()
                if not description:
                    self.console.print("[red]Description is required.[/red]")
                    continue
                
                # Validate description
                validate_description(description)
                return description
                
            except ValidationError as e:
                self.console.print(f"[red]{e}[/red]")
            except KeyboardInterrupt:
                raise
    
    def display_discovery_summary(self, session_summary: Dict[str, Any]):
        """Display a summary of the discovery session."""
        self.console.print()
        
        panel_content = []
        panel_content.append(f"Session ID: {session_summary.get('session_id', 'N/A')}")
        panel_content.append(f"Unique parts discovered: {session_summary.get('unique_parts_discovered', 0)}")
        panel_content.append(f"Total occurrences: {session_summary.get('total_occurrences', 0)}")
        panel_content.append(f"Parts added to database: {session_summary.get('parts_added', 0)}")
        panel_content.append(f"Parts skipped: {session_summary.get('parts_skipped', 0)}")
        
        if session_summary.get('processing_time'):
            panel_content.append(f"Processing time: {session_summary['processing_time']:.2f} seconds")
        
        panel = Panel(
            "\n".join(panel_content),
            title="Discovery Session Summary",
            title_align="left",
            border_style="green"
        )
        
        self.console.print(panel)
        self.console.print()
    
    def display_batch_review_prompt(self, unknown_parts_data: List[Dict[str, Any]]) -> bool:
        """
        Display unknown parts for batch review and ask if user wants to process them.
        
        Args:
            unknown_parts_data: List of unknown parts with aggregated information
            
        Returns:
            True if user wants to process the parts, False otherwise
        """
        if not unknown_parts_data:
            self.console.print("[yellow]No unknown parts found for review.[/yellow]")
            return False
        
        self.console.print(f"\n[bold]Found {len(unknown_parts_data)} unknown parts for review:[/bold]\n")
        
        # Create table for unknown parts summary
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Part Number", style="cyan")
        table.add_column("Occurrences", justify="center")
        table.add_column("Avg Price", justify="right")
        table.add_column("Price Range", justify="right")
        table.add_column("Description", max_width=30)
        
        for part_data in unknown_parts_data:
            part_number = part_data['part_number']
            occurrences = str(part_data['occurrences'])
            avg_price = f"${part_data['avg_price']:.2f}"
            
            if part_data['min_price'] == part_data['max_price']:
                price_range = f"${part_data['min_price']:.2f}"
            else:
                price_range = f"${part_data['min_price']:.2f} - ${part_data['max_price']:.2f}"
            
            description = part_data.get('description', 'N/A')
            if len(description) > 30:
                description = description[:27] + "..."
            
            table.add_row(part_number, occurrences, avg_price, price_range, description)
        
        self.console.print(table)
        self.console.print()
        
        return Confirm.ask(
            "Would you like to review and add these parts to the database?",
            default=True
        )
    
    def confirm_part_addition(self, part_details: Dict[str, Any]) -> bool:
        """
        Confirm part addition with user.
        
        Args:
            part_details: Dictionary with part details to be added
            
        Returns:
            True if user confirms, False otherwise
        """
        self.console.print("\n[bold]Confirm part addition:[/bold]")
        
        # Display part details
        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan", width=20)
        table.add_column("Value", style="white")
        
        for key, value in part_details.items():
            if value is not None:
                display_key = key.replace('_', ' ').title()
                if key == 'authorized_price':
                    display_value = f"${value:.2f}"
                else:
                    display_value = str(value)
                table.add_row(display_key, display_value)
        
        self.console.print(table)
        self.console.print()
        
        return Confirm.ask("Add this part to the database?", default=True)
    
    def display_error(self, error_message: str, error_type: str = "Error"):
        """Display an error message to the user."""
        self.console.print(f"[red]{error_type}: {error_message}[/red]")
    
    def display_success(self, message: str):
        """Display a success message to the user."""
        self.console.print(f"[green]✓ {message}[/green]")
    
    def display_warning(self, message: str):
        """Display a warning message to the user."""
        self.console.print(f"[yellow]⚠ {message}[/yellow]")
    
    def display_info(self, message: str):
        """Display an info message to the user."""
        self.console.print(f"[blue]ℹ {message}[/blue]")


class BatchDiscoveryPrompt:
    """
    Prompt handler for batch discovery operations.
    
    This class provides prompts for reviewing and processing
    multiple unknown parts that were collected during batch processing.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the batch prompt handler.
        
        Args:
            console: Rich console instance for formatted output
        """
        self.console = console or Console()
        self.part_prompt = PartDiscoveryPrompt(console)
    
    def review_unknown_parts_batch(self, unknown_parts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Review unknown parts in batch mode.
        
        Args:
            unknown_parts_data: List of unknown parts with aggregated information
            
        Returns:
            List of user decisions for each part
        """
        if not self.part_prompt.display_batch_review_prompt(unknown_parts_data):
            return []
        
        results = []
        
        for i, part_data in enumerate(unknown_parts_data, 1):
            self.console.print(f"\n[bold]Reviewing part {i} of {len(unknown_parts_data)}:[/bold]")
            
            # Create context from aggregated data
            context = UnknownPartContext(
                part_number=part_data['part_number'],
                description=part_data.get('description'),
                discovered_price=Decimal(str(part_data['avg_price']))
            )
            
            try:
                decision = self.part_prompt.prompt_for_unknown_part(
                    context, 
                    part_data['occurrences']
                )
                decision['part_number'] = part_data['part_number']
                results.append(decision)
                
                # Check if user wants to stop processing
                if decision['action'] in ['stop_processing', 'skip_all_remaining']:
                    break
                    
            except UserCancelledError:
                break
        
        return results