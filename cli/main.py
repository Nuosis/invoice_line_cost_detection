"""
Main CLI entry point for the Invoice Rate Detection System.

This module provides the main command-line interface with command groups
and global options for the invoice rate detection system.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import click

from database.database import DatabaseManager
from database.models import DatabaseError
from cli.commands import (
    invoice_commands,
    parts_commands,
    database_commands,
    config_commands,
    discovery_commands,
    utils_commands
)
from cli.exceptions import CLIError
from cli.formatters import setup_logging


# Global context class to share state between commands
class CLIContext:
    """Context object to share state between CLI commands."""
    
    def __init__(self):
        self.verbose = False
        self.quiet = False
        self.database_path = "invoice_detection.db"
        self.config_file = None
        self.db_manager = None
    
    def get_db_manager(self) -> DatabaseManager:
        """Get or create database manager instance."""
        if self.db_manager is None:
            self.db_manager = DatabaseManager(self.database_path)
        return self.db_manager


# Pass context between commands
pass_context = click.make_pass_decorator(CLIContext, ensure=True)


@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-essential output')
@click.option('--config-file', type=click.Path(exists=True), 
              help='Specify custom configuration file path')
@click.option('--database', type=click.Path(), default="invoice_detection.db",
              help='Specify custom database path')
@click.version_option(version="1.0.0", prog_name="invoice-checker")
@click.pass_context
def cli(ctx, verbose, quiet, config_file, database):
    """
    Invoice Rate Detection System - CLI Tool
    
    A comprehensive tool for processing invoices, managing parts database,
    and detecting pricing anomalies.
    
    Examples:
        # Process invoices with interactive discovery
        invoice-checker process ./invoices --interactive
        
        # Add a new part to the database
        invoice-checker parts add GP0171NAVY 15.50 --description "Navy Work Pants"
        
        # Get system status
        invoice-checker status
    """
    # Initialize context
    cli_ctx = CLIContext()
    cli_ctx.verbose = verbose
    cli_ctx.quiet = quiet
    cli_ctx.database_path = database
    cli_ctx.config_file = config_file
    ctx.obj = cli_ctx
    
    # Setup logging
    setup_logging(verbose, quiet)
    
    # If no command is provided, show help or run interactive mode
    if ctx.invoked_subcommand is None:
        # Check if we should run in simple mode (for non-technical users)
        if len(sys.argv) == 1:  # No arguments provided
            # Run interactive processing mode
            ctx.invoke(interactive_process)
        else:
            click.echo(ctx.get_help())


@cli.command()
@pass_context
def interactive_process(ctx):
    """
    Interactive processing mode for non-technical users.
    
    This is the default mode when no arguments are provided.
    Guides users through the invoice processing workflow.
    """
    try:
        from cli.commands.invoice_commands import run_interactive_processing
        run_interactive_processing(ctx)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Interactive processing failed: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Add command groups
cli.add_command(invoice_commands.invoice_group)
cli.add_command(parts_commands.parts_group)
cli.add_command(database_commands.database_group)
cli.add_command(config_commands.config_group)
cli.add_command(discovery_commands.discovery_group)
cli.add_command(utils_commands.utils_group)


def main():
    """Main entry point for the CLI application."""
    try:
        cli()
    except CLIError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Database Error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Unexpected error occurred")
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()