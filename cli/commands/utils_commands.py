"""
Utility commands for the CLI interface.

This module implements utility commands including:
- help: Show help information
- version: Show version information
- status: Show system status
"""

import logging
import sys
import platform
from pathlib import Path

import click

from cli.main import pass_context
from cli.formatters import (
    print_success, print_warning, print_error, print_info,
    format_table, format_json, display_summary
)
from cli.exceptions import CLIError
from database.models import DatabaseError


logger = logging.getLogger(__name__)


# Create utils command group
@click.group(name='utils')
def utils_group():
    """Utility commands."""
    pass


@utils_group.command()
@click.argument('command', type=str, required=False)
@click.pass_context
def help(ctx, command):
    """
    Show help information for commands.
    
    Examples:
        # Show general help
        invoice-checker help
        
        # Show help for a specific command
        invoice-checker help process
        
        # Show help for a command group
        invoice-checker help parts
    """
    try:
        if command:
            # Show help for specific command
            if command in ['process', 'batch', 'interactive', 'collect-unknowns']:
                click.echo(ctx.parent.parent.get_command(ctx, 'invoice').get_command(ctx, command).get_help(ctx))
            elif command in ['add', 'list', 'get', 'update', 'delete', 'import', 'export', 'stats']:
                click.echo(ctx.parent.parent.get_command(ctx, 'parts').get_command(ctx, command).get_help(ctx))
            elif command in ['backup', 'restore', 'migrate', 'maintenance']:
                click.echo(ctx.parent.parent.get_command(ctx, 'database').get_command(ctx, command).get_help(ctx))
            elif command in ['get', 'set', 'list', 'reset']:
                click.echo(ctx.parent.parent.get_command(ctx, 'config').get_command(ctx, command).get_help(ctx))
            elif command in ['discovery']:
                click.echo(ctx.parent.parent.get_command(ctx, 'discovery').get_help(ctx))
            elif command in ['parts', 'invoice', 'database', 'config', 'utils']:
                click.echo(ctx.parent.parent.get_command(ctx, command).get_help(ctx))
            else:
                print_error(f"Unknown command: {command}")
                _show_available_commands()
        else:
            # Show general help
            click.echo(ctx.parent.parent.get_help(ctx))
            _show_quick_start_guide()
        
    except Exception as e:
        logger.exception("Failed to show help")
        raise CLIError(f"Failed to show help: {e}")


@utils_group.command()
@click.option('--detailed', is_flag=True, help='Show detailed version and dependency information')
@pass_context
def version(ctx, detailed):
    """
    Display version and system information.
    
    Examples:
        # Show basic version
        invoice-checker version
        
        # Show detailed version info
        invoice-checker version --detailed
    """
    try:
        # Basic version info
        app_version = "1.0.0"  # This would normally come from package metadata
        click.echo(f"Invoice Rate Detection System v{app_version}")
        
        if detailed:
            # Get system information
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
            
            # Get dependency versions
            try:
                import click as click_module
                system_info['Click Version'] = click_module.__version__
            except:
                system_info['Click Version'] = 'Unknown'
            
            try:
                import tabulate
                system_info['Tabulate Version'] = tabulate.__version__
            except:
                system_info['Tabulate Version'] = 'Not installed'
            
            # Display detailed information
            click.echo("\nDetailed System Information:")
            click.echo("=" * 40)
            for key, value in system_info.items():
                click.echo(f"{key:20}: {value}")
        
    except Exception as e:
        logger.exception("Failed to show version")
        raise CLIError(f"Failed to show version: {e}")


@utils_group.command()
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@pass_context
def status(ctx, format):
    """
    Display system status and health information.
    
    Examples:
        # Show system status
        invoice-checker status
        
        # Show status in JSON format
        invoice-checker status --format json
    """
    try:
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
            'Available Memory (MB)': _get_available_memory_mb()
        })
        
        # Configuration status
        try:
            validation_mode = db_manager.get_config_value('validation_mode', 'unknown')
            interactive_discovery = db_manager.get_config_value('interactive_discovery', False)
            status_info.update({
                'Validation Mode': validation_mode,
                'Interactive Discovery': 'Enabled' if interactive_discovery else 'Disabled'
            })
        except Exception as e:
            status_info['Configuration Status'] = f'Error: {e}'
        
        # Recent activity
        try:
            recent_logs = db_manager.get_discovery_logs(days_back=7, limit=10)
            status_info['Recent Activity (7 days)'] = len(recent_logs)
        except Exception as e:
            status_info['Recent Activity'] = f'Error: {e}'
        
        # Display status
        if format == 'table':
            display_summary("System Status", status_info)
            
            # Show health indicators
            click.echo("\nHealth Indicators:")
            click.echo("-" * 20)
            
            # Database health
            if 'Error' not in str(status_info.get('Database Status', '')):
                print_success("✓ Database connection healthy")
            else:
                print_error("✗ Database connection issues")
            
            # Parts database health
            active_parts = status_info.get('Active Parts', 0)
            if active_parts > 0:
                print_success(f"✓ Parts database populated ({active_parts} active parts)")
            else:
                print_warning("⚠ Parts database is empty")
            
            # Configuration health
            if 'Error' not in str(status_info.get('Configuration Status', '')):
                print_success("✓ Configuration loaded successfully")
            else:
                print_error("✗ Configuration issues detected")
            
        elif format == 'json':
            click.echo(format_json(status_info))
        
    except Exception as e:
        logger.exception("Failed to get system status")
        raise CLIError(f"Failed to get system status: {e}")


def _show_available_commands():
    """Show available commands organized by category."""
    click.echo("\nAvailable Commands:")
    click.echo("=" * 30)
    
    commands = {
        "Invoice Processing": [
            "process - Process invoices with parts-based validation",
            "batch - Batch processing of multiple folders", 
            "interactive - Guided interactive processing",
            "collect-unknowns - Collect unknown parts without validation"
        ],
        "Parts Management": [
            "parts add - Add new part to database",
            "parts list - List parts with filtering",
            "parts get - Get single part details",
            "parts update - Update existing part",
            "parts delete - Delete/deactivate part",
            "parts import - Import parts from CSV",
            "parts export - Export parts to CSV",
            "parts stats - Parts statistics"
        ],
        "Database Operations": [
            "database backup - Create database backup",
            "database restore - Restore from backup",
            "database migrate - Database schema migration",
            "database maintenance - Database maintenance tasks"
        ],
        "Configuration": [
            "config get - Get configuration value",
            "config set - Set configuration value", 
            "config list - List all configurations",
            "config reset - Reset configuration"
        ],
        "Discovery Logs": [
            "discovery list - List discovery log entries",
            "discovery export - Export discovery logs",
            "discovery cleanup - Clean up old logs"
        ],
        "Utilities": [
            "help - Show help information",
            "version - Show version information",
            "status - Show system status"
        ]
    }
    
    for category, command_list in commands.items():
        click.echo(f"\n{category}:")
        for command in command_list:
            click.echo(f"  {command}")


def _show_quick_start_guide():
    """Show a quick start guide for new users."""
    click.echo("\nQuick Start Guide:")
    click.echo("=" * 30)
    click.echo("1. Check system status:")
    click.echo("   invoice-checker status")
    click.echo()
    click.echo("2. Add parts to database:")
    click.echo("   invoice-checker parts add PART123 15.50 --description 'Sample Part'")
    click.echo()
    click.echo("3. Process invoices:")
    click.echo("   invoice-checker process ./invoices --interactive")
    click.echo()
    click.echo("4. View results and manage parts as needed")
    click.echo()
    click.echo("For detailed help on any command, use:")
    click.echo("   invoice-checker help <command>")


def _get_available_memory_mb():
    """Get available system memory in MB."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return round(memory.available / (1024 * 1024), 2)
    except ImportError:
        # psutil not available, try alternative methods
        try:
            import os
            # This is a rough estimate and may not be accurate
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemAvailable:'):
                        return round(int(line.split()[1]) / 1024, 2)
        except:
            pass
        return "Unknown"


# Add commands to the group (help, version, status are added automatically)
# We don't need to explicitly add them since they're defined as commands above

# However, we need to make these commands available at the top level too
# This will be handled in the main CLI module