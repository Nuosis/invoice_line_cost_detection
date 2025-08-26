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
from cli.version import get_version, get_version_info
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
@click.version_option(version=get_version(), prog_name="invoice-checker")
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
            click.get_current_context().invoke(interactive_process)
        else:
            click.echo(ctx.get_help())


@cli.command()
@pass_context
def interactive_process(ctx):
    """
    Interactive processing mode for non-technical users.
    
    This is the default mode when no arguments are provided.
    Provides a main menu with all system functions.
    """
    try:
        run_main_interactive_menu(ctx)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Interactive mode failed: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def run_main_interactive_menu(ctx):
    """
    Run the main interactive menu system.
    
    This function provides a comprehensive menu-driven interface for all
    system operations, making it easy for non-technical users to access
    all functionality.
    
    Args:
        ctx: CLI context containing database manager and other resources
    """
    from cli.formatters import print_success, print_warning, print_error, print_info
    from cli.prompts import prompt_for_choice
    from cli.exceptions import UserCancelledError
    
    # Ensure database is initialized before showing menu
    ctx.get_db_manager()

    # Show welcome message
    click.echo("\n" + "="*75)
    click.echo("           INVOICE RATE DETECTION SYSTEM - MAIN MENU")
    click.echo("="*75)
    click.echo("Welcome to the Invoice Rate Detection System!")
    click.echo("This tool helps you manage parts databases and validate invoice pricing.")
    click.echo("")
    
    while True:
        try:
            # Display main menu
            click.echo("╔═════════════════════════════════════════════════════════════════════════════════╗")
            click.echo("║                                   MAIN MENU                                     ║")
            click.echo("╚═════════════════════════════════════════════════════════════════════════════════╝")
            click.echo("")
            
            menu_options = [
                "Configure and Process - Run interactive invoice processing with discovery",
                "Manage Parts        - Add, update, import/export parts database",
                "Manage Database     - Backup, restore, and maintain database",
                "Setup / Configuration - System setup and configuration options",
                "Help                - Show help and documentation",
                "Exit                - Exit the application"
            ]

            click.echo("")
            choice = prompt_for_choice("Enter choice", menu_options)
            
            if choice == menu_options[0]:
                # Process Invoices
                print_info("[INFO] Starting invoice processing...")
                from cli.commands.invoice_commands import run_interactive_processing
                run_interactive_processing(ctx)
                
            elif choice == menu_options[1]:
                # Manage Parts
                print_info("[INFO] Starting parts management...")
                _run_interactive_parts_management(ctx)
                
            elif choice == menu_options[2]:
                # Manage Database
                print_info("[INFO] Starting database management...")
                from cli.commands.database_commands import run_interactive_database_management
                run_interactive_database_management(ctx)

            elif choice == menu_options[3]:
                # Setup / Configuration
                print_info("[INFO] Starting setup and configuration management...")
                from cli.commands.config_commands import run_interactive_config_management
                run_interactive_config_management(ctx)

            elif choice == menu_options[4]:
                # Help
                _show_help_menu(ctx)
                
            elif choice == menu_options[5]:
                # Exit
                print_info("Thank you for using the Invoice Rate Detection System!")
                break
            else:
                print_error("Invalid option. Please select a valid menu option.")
                continue
                
        except UserCancelledError:
            print_info("Operation cancelled by user.")
            if click.confirm("Return to main menu?", default=True):
                continue
            else:
                break
        except KeyboardInterrupt:
            print_info("\nOperation cancelled by user.")
            if click.confirm("Return to main menu?", default=True):
                continue
            else:
                break
        except Exception as e:
            print_error(f"An error occurred: {e}")
            if not click.confirm("Continue to main menu?", default=True):
                break


def _run_interactive_parts_management(ctx):
    """Interactive parts management workflow."""
    from cli.prompts import prompt_for_choice
    from cli.exceptions import UserCancelledError
    from cli.formatters import print_info, print_error
    
    while True:
        try:
            click.echo("\n" + "="*75)
            click.echo("                           PARTS MANAGEMENT")
            click.echo("="*75)
            
            parts_options = [
                "List parts",
                "Add new part",
                "Update existing part",
                "Import parts from CSV",
                "Export parts to CSV",
                "Search parts",
                "Return to main menu"
            ]

            print_info("Parts Management Options:")
            choice = prompt_for_choice("Enter choice", parts_options)

            if choice == parts_options[0]:
                from cli.commands.parts_commands import _interactive_list_parts
                _interactive_list_parts(ctx)
            elif choice == parts_options[1]:
                from cli.commands.parts_commands import _interactive_add_part
                _interactive_add_part(ctx)
            elif choice == parts_options[2]:
                from cli.commands.parts_commands import _interactive_update_part
                _interactive_update_part(ctx)
            elif choice == parts_options[3]:
                from cli.commands.parts_commands import _interactive_import_parts
                _interactive_import_parts(ctx)
            elif choice == parts_options[4]:
                from cli.commands.parts_commands import _interactive_export_parts
                _interactive_export_parts(ctx)
            elif choice == parts_options[5]:
                from cli.commands.parts_commands import _interactive_search_parts
                _interactive_search_parts(ctx)
            elif choice == parts_options[6]:
                print_info("Returning to main menu...")
                break
            else:
                print_error("Invalid option. Please select a valid menu option.")
                continue
                
        except UserCancelledError:
            print_info("Parts management cancelled by user.")
            break
        except Exception as e:
            print_error(f"An error occurred: {e}")
            if not click.confirm("Continue with parts management?", default=True):
                break




def _show_help_menu(ctx):
    """Show help and documentation menu."""
    from cli.formatters import print_info
    
    click.echo("\n" + "="*75)
    click.echo("                           HELP & DOCUMENTATION")
    click.echo("="*75)
    
    print_info("Available Help Topics:")
    click.echo("")
    click.echo("1. Getting Started Guide")
    click.echo("   - How to set up and use the system")
    click.echo("   - Basic workflow for processing invoices")
    click.echo("")
    click.echo("2. Parts Management")
    click.echo("   - Adding and managing parts in the database")
    click.echo("   - Importing/exporting parts data")
    click.echo("")
    click.echo("3. Database Management")
    click.echo("   - Creating backups and restoring data")
    click.echo("   - Database maintenance and optimization")
    click.echo("")
    click.echo("4. Troubleshooting")
    click.echo("   - Common issues and solutions")
    click.echo("   - Error messages and their meanings")
    click.echo("")
    click.echo("5. Command Reference")
    click.echo("   - Complete list of CLI commands")
    click.echo("   - Command options and examples")
    click.echo("")
    
    help_choice = click.prompt(
        "Select help topic (1-5) or press Enter to return",
        default="",
        type=str
    )
    
    if help_choice == "1":
        _show_getting_started_guide()
    elif help_choice == "2":
        _show_parts_management_help()
    elif help_choice == "3":
        _show_database_management_help()
    elif help_choice == "4":
        _show_troubleshooting_help()
    elif help_choice == "5":
        _show_command_reference()
    else:
        print_info("Returning to main menu...")


def _check_system_dependencies():
    """Check system dependencies and requirements."""
    from cli.formatters import print_success, print_warning, print_error, print_info
    import sys
    import platform
    
    print_info("Checking system dependencies...")
    click.echo("")
    
    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 8):
        print_success(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro} (OK)")
    else:
        print_error(f"✗ Python {python_version.major}.{python_version.minor}.{python_version.micro} (Requires 3.8+)")
    
    # Check platform
    system = platform.system()
    print_info(f"Platform: {system} {platform.release()}")
    
    # Check required packages
    required_packages = [
        'click', 'pdfplumber', 'pathlib', 'sqlite3', 'decimal'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"✓ {package} (Available)")
        except ImportError:
            print_error(f"✗ {package} (Missing)")
    
    click.echo("")
    print_info("Dependency check complete.")


def _show_recent_logs(ctx):
    """Show recent system logs and activity."""
    from cli.formatters import print_info, format_table
    
    try:
        db_manager = ctx.get_db_manager()
        
        # Get recent discovery logs
        recent_logs = db_manager.get_discovery_logs(limit=10)
        
        if recent_logs:
            print_info("Recent Discovery Activity:")
            log_data = []
            for log in recent_logs:
                log_data.append({
                    'Date': log.discovery_date.strftime('%Y-%m-%d %H:%M') if log.discovery_date else 'Unknown',
                    'Part': log.part_number,
                    'Action': log.action_taken,
                    'Invoice': log.invoice_number or 'N/A'
                })
            
            click.echo(format_table(log_data))
        else:
            print_info("No recent activity found.")
            
    except Exception as e:
        print_info(f"Could not retrieve logs: {e}")


def _show_getting_started_guide():
    """Show getting started guide."""
    click.echo("\n" + "="*75)
    click.echo("                           GETTING STARTED GUIDE")
    click.echo("="*75)
    click.echo("""
WELCOME TO THE INVOICE RATE DETECTION SYSTEM

This system helps you validate invoice pricing by comparing line items
against your master parts database.

BASIC WORKFLOW:
1. Set up your parts database with expected prices
2. Process invoices to detect pricing anomalies
3. Review generated reports for overcharges
4. Add new parts discovered during processing

FIRST TIME SETUP:
1. Go to 'Manage Parts' to add your initial parts
2. Or import parts from a CSV file
3. Process a test invoice to verify everything works
4. Review the generated report

TIPS:
- Keep your parts database up to date
- Create regular backups of your database
- Use interactive discovery to learn about new parts
- Check the troubleshooting section if you encounter issues

Press Enter to continue...
""")
    input()


def _show_parts_management_help():
    """Show parts management help."""
    click.echo("\n" + "="*75)
    click.echo("                           PARTS MANAGEMENT HELP")
    click.echo("="*75)
    click.echo("""
MANAGING YOUR PARTS DATABASE

The parts database is the heart of the system. It contains:
- Part numbers and descriptions
- Authorized/expected prices
- Categories and other metadata

ADDING PARTS:
- Use 'Add new part' for individual parts
- Use 'Import from CSV' for bulk additions
- Parts are automatically discovered during invoice processing

CSV IMPORT FORMAT:
part_number,authorized_price,description,category
GP0171NAVY,15.50,"Navy Work Pants",Clothing
GS0448,12.75,"Work Shirt Long Sleeve",Clothing

BEST PRACTICES:
- Keep part numbers consistent
- Update prices regularly
- Use meaningful descriptions
- Organize with categories
- Export backups regularly

Press Enter to continue...
""")
    input()


def _show_database_management_help():
    """Show database management help."""
    click.echo("\n" + "="*75)
    click.echo("                           DATABASE MANAGEMENT HELP")
    click.echo("="*75)
    click.echo("""
DATABASE BACKUP AND MAINTENANCE

Regular maintenance keeps your system running smoothly:

BACKUP OPERATIONS:
- Create backup: Save current database state
- Restore from backup: Replace database with backup
- View backup history: See available backups

MAINTENANCE TASKS:
- Vacuum database: Reclaim unused space
- Clean up logs: Remove old discovery entries
- Verify integrity: Check for database corruption

RESET DATABASE:
- Completely erases all data
- Creates backup before reset
- Option to keep configuration settings
- Cannot be undone - use with caution!

RECOMMENDED SCHEDULE:
- Daily: Automatic backups during processing
- Weekly: Manual backup before major changes
- Monthly: Database maintenance and cleanup
- As needed: Restore from backup if issues occur

Press Enter to continue...
""")
    input()


def _show_troubleshooting_help():
    """Show troubleshooting help."""
    click.echo("\n" + "="*75)
    click.echo("                           TROUBLESHOOTING HELP")
    click.echo("="*75)
    click.echo("""
COMMON ISSUES AND SOLUTIONS

PROBLEM: "Database locked" error
SOLUTION: Close other instances of the application

PROBLEM: "No PDF files found"
SOLUTION: Check file path and ensure PDFs are in the directory

PROBLEM: "Part not found" during processing
SOLUTION: Add the part to your database or use discovery mode

PROBLEM: Reports show no anomalies when expected
SOLUTION: Check part prices in database, verify validation mode

PROBLEM: Cannot import CSV file
SOLUTION: Check CSV format, ensure required columns exist

PROBLEM: Application crashes or freezes
SOLUTION: Check system requirements, restart application

GETTING HELP:
- Check the logs for detailed error messages
- Use 'View system status' to check system health
- Ensure all dependencies are installed
- Try processing a simple test file first
- email marcus@claritybusinesssolutions.ca

If problems persist, check the documentation or contact support.

Press Enter to continue...
""")
    input()


def _show_command_reference():
    """Show command reference."""
    click.echo("\n" + "="*75)
    click.echo("                           COMMAND REFERENCE")
    click.echo("="*75)
    click.echo("""
COMMAND LINE INTERFACE REFERENCE

INVOICE PROCESSING:
  invoice-checker process <path>           Process invoices
  invoice-checker process --interactive    Interactive processing
  invoice-checker collect-unknowns <path> Collect unknown parts

PARTS MANAGEMENT:
  invoice-checker parts list               List all parts
  invoice-checker parts add <part> <price> Add new part
  invoice-checker parts import <csv>       Import from CSV
  invoice-checker parts export <csv>       Export to CSV

DATABASE MANAGEMENT:
  invoice-checker database backup          Create backup
  invoice-checker database restore <file>  Restore from backup
  invoice-checker database maintenance     Run maintenance
  invoice-checker database reset           Reset database
  invoice-checker database interactive     Interactive management

SYSTEM COMMANDS:
  invoice-checker status                   Show system status
  invoice-checker version                  Show version info
  invoice-checker --help                   Show help

INTERACTIVE MODE:
  invoice-checker                          Start interactive mode
  
For detailed help on any command, use:
  invoice-checker <command> --help

Press Enter to continue...
""")
    input()


# Add command groups
cli.add_command(invoice_commands.invoice_group)
cli.add_command(parts_commands.parts_group)
cli.add_command(database_commands.database_group)
cli.add_command(config_commands.config_group)
cli.add_command(discovery_commands.discovery_group)
cli.add_command(utils_commands.utils_group)

# Add top-level commands for convenience (these are also available under utils)
@cli.command()
@click.argument('input_path', type=click.Path(exists=True), required=False)
@click.option('--no-auto-open', is_flag=True,
              help='Disable automatic opening of generated reports')
@pass_context
def quick(ctx, input_path, no_auto_open):
    """
    Quick processing with all defaults but discovery enabled.
    
    This command processes invoices using all configured defaults:
    - Uses default invoice location if no input provided
    - Uses default output format and location
    - Uses default validation mode
    - Enables part discovery (records unknown parts; no prompts)
    - Auto-opens reports unless --no-auto-open is specified
    
    Perfect for streamlined processing when you want discovery
    but don't want to answer prompts.
    
    Examples:
        # Quick process with defaults
        invoice-checker quick
        
        # Quick process specific folder
        invoice-checker quick /path/to/invoices
        
        # Quick process without auto-opening reports
        invoice-checker quick --no-auto-open
    """
    try:
        from cli.commands.invoice_commands import run_quick_processing
        from cli.exceptions import UserCancelledError, CLIError
        run_quick_processing(ctx, input_path, not no_auto_open)
    except UserCancelledError:
        click.echo("Quick processing cancelled by user.")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Quick processing failed")
        click.echo(f"Quick processing failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed version and dependency information')
@pass_context
def version(ctx, detailed):
    """Display version and system information."""
    try:
        # Get comprehensive version info
        version_info = get_version_info()
        app_version = version_info['version']
        click.echo(f"Invoice Rate Detection System v{app_version}")
        
        if detailed:
            # Get system information
            import platform
            system_info = {
                'Application Version': app_version,
                'Base Version': version_info['base_version'],
                'Python Version': sys.version.split()[0],
                'Platform': platform.platform(),
                'Architecture': platform.architecture()[0],
                'Python Executable': sys.executable
            }
            
            # Add git information if available
            if version_info['git_available']:
                system_info.update({
                    'Git Commit': version_info['commit_hash'],
                    'Git Branch': version_info['branch'],
                    'Repository Status': 'Clean' if not version_info['dirty'] else 'Modified'
                })
            else:
                system_info['Git Status'] = 'Not available'
            
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