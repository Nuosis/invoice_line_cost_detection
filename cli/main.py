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

from database.models import DatabaseError
from cli.context import CLIContext, pass_context
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

# Add top-level commands for convenience (these are also available under utils)
@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed version and dependency information')
@pass_context
def version(ctx, detailed):
    """Display version and system information."""
    try:
        # Basic version info
        app_version = "1.0.0"
        click.echo(f"Invoice Rate Detection System v{app_version}")
        
        if detailed:
            # Get system information
            import platform
            system_info = {
                'Application Version': app_version,
                'Python Version': sys.version.split()[0],
                'Platform': platform.platform(),
                'Architecture': platform.architecture()[0],
                'Python Executable': sys.executable
            }
            
            # Get database information
            try:
                db_manager = ctx.get_db_manager()
                db_stats = db_manager.get_database_stats()
                system_info.update({
                    'Database Version': db_stats.get('database_version', 'Unknown'),
                    'Database Size': f"{db_stats.get('database_size_bytes', 0) / (1024*1024):.2f} MB",
                    'Total Parts': db_stats.get('total_parts', 0),
                    'Active Parts': db_stats.get('active_parts', 0)
                })
            except Exception as e:
                system_info['Database Status'] = f"Error: {e}"
            
            # Display detailed information
            click.echo("\nDetailed System Information:")
            click.echo("=" * 40)
            for key, value in system_info.items():
                click.echo(f"{key:20}: {value}")
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Failed to show version")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@pass_context
def status(ctx, format):
    """Display system status and health information."""
    try:
        from cli.formatters import display_summary, format_json, print_success, print_warning, print_error
        import platform
        
        db_manager = ctx.get_db_manager()
        
        # Collect system status information
        status_info = {}
        
        # Database status
        try:
            db_stats = db_manager.get_database_stats()
            status_info.update({
                'Database Status': 'Connected',
                'Database Version': db_stats.get('database_version', 'Unknown'),
                'Database Size (MB)': round(db_stats.get('database_size_bytes', 0) / (1024*1024), 2),
                'Total Parts': db_stats.get('total_parts', 0),
                'Active Parts': db_stats.get('active_parts', 0),
                'Configuration Entries': db_stats.get('config_entries', 0),
                'Discovery Log Entries': db_stats.get('discovery_log_entries', 0)
            })
        except Exception as e:
            status_info['Database Status'] = f'Error: {e}'
        
        # System information
        status_info.update({
            'Python Version': sys.version.split()[0],
            'Platform': platform.system(),
        })
        
        # Display status
        if format == 'table':
            display_summary("System Status", status_info)
        elif format == 'json':
            click.echo(format_json(status_info))
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Failed to get system status")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


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