"""
Discovery log management commands for the CLI interface.

This module implements discovery log-related commands including:
- list: List discovery log entries
- export: Export discovery logs
- cleanup: Clean up old logs
"""

import logging
from pathlib import Path
from typing import Optional

import click

from cli.main import pass_context
from cli.validators import validate_positive_integer, validate_session_id
from cli.formatters import (
    print_success, print_warning, print_error, print_info,
    format_table, write_csv, format_json, display_summary
)
from cli.prompts import prompt_for_confirmation
from cli.exceptions import CLIError, ValidationError
from database.models import DatabaseError


logger = logging.getLogger(__name__)


# Create discovery command group
@click.group(name='discovery')
def discovery_group():
    """Discovery log management commands."""
    pass


@discovery_group.command()
@click.option('--part-number', '-p', type=str, help='Filter by part number')
@click.option('--invoice-number', '-i', type=str, help='Filter by invoice number')
@click.option('--session-id', '-s', type=str, help='Filter by session ID')
@click.option('--days-back', '-d', type=int, default=30, help='Show entries from last N days')
@click.option('--action', '-a', type=click.Choice(['discovered', 'added', 'updated', 'skipped', 'price_mismatch']),
              help='Filter by action type')
@click.option('--limit', '-l', type=int, help='Maximum number of results')
@click.option('--format', '-f', type=click.Choice(['table', 'csv', 'json']), default='table',
              help='Output format')
@pass_context
def list(ctx, part_number, invoice_number, session_id, days_back, action, limit, format):
    """
    List discovery log entries with filtering.
    
    Examples:
        # List recent discoveries
        invoice-checker discovery list
        
        # List discoveries for a specific part
        invoice-checker discovery list --part-number GP0171NAVY
        
        # List discoveries from a specific session
        invoice-checker discovery list --session-id abc123
        
        # Export discoveries to CSV
        invoice-checker discovery list --format csv > discoveries.csv
    """
    try:
        db_manager = ctx.get_db_manager()
        
        # Validate session ID if provided
        if session_id:
            session_id = validate_session_id(session_id)
        
        # Get discovery logs
        logs = db_manager.get_discovery_logs(
            part_number=part_number,
            invoice_number=invoice_number,
            session_id=session_id,
            days_back=days_back,
            limit=limit
        )
        
        # Filter by action if specified
        if action:
            logs = [log for log in logs if log.action_taken == action]
        
        if not logs:
            print_info("No discovery log entries found matching the criteria.")
            return
        
        # Convert to display format
        log_data = []
        for log in logs:
            log_data.append({
                'ID': log.id,
                'Part Number': log.part_number,
                'Invoice': log.invoice_number or 'N/A',
                'Invoice Date': log.invoice_date or 'N/A',
                'Discovered Price': f"${float(log.discovered_price):.4f}" if log.discovered_price else 'N/A',
                'Authorized Price': f"${float(log.authorized_price):.4f}" if log.authorized_price else 'N/A',
                'Action': log.action_taken,
                'User Decision': log.user_decision or 'N/A',
                'Discovery Date': log.discovery_date.strftime('%Y-%m-%d %H:%M:%S') if log.discovery_date else 'N/A',
                'Session ID': log.processing_session_id or 'N/A',
                'Notes': log.notes or ''
            })
        
        # Display results
        if format == 'table':
            # For table format, show a subset of columns for readability
            table_data = []
            for item in log_data:
                table_data.append({
                    'Part Number': item['Part Number'],
                    'Action': item['Action'],
                    'Discovered Price': item['Discovered Price'],
                    'Invoice': item['Invoice'],
                    'Discovery Date': item['Discovery Date'][:10]  # Just the date part
                })
            click.echo(format_table(table_data))
        elif format == 'csv':
            import sys
            write_csv(log_data, sys.stdout)
        elif format == 'json':
            click.echo(format_json(log_data))
        
        # Show summary
        print_info(f"Found {len(logs)} discovery log entries")
        
        # Show action breakdown
        if len(logs) > 1:
            actions = {}
            for log in logs:
                actions[log.action_taken] = actions.get(log.action_taken, 0) + 1
            
            print_info("Action breakdown:")
            for action_type, count in sorted(actions.items()):
                print_info(f"  {action_type}: {count}")
        
    except ValidationError as e:
        raise CLIError(f"Validation error: {e}")
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to list discovery logs")
        raise CLIError(f"Failed to list discovery logs: {e}")


@discovery_group.command()
@click.argument('output_file', type=click.Path())
@click.option('--days-back', '-d', type=int, help='Export entries from last N days')
@click.option('--session-id', '-s', type=str, help='Export specific session')
@click.option('--part-number', '-p', type=str, help='Export entries for specific part')
@click.option('--action', '-a', type=click.Choice(['discovered', 'added', 'updated', 'skipped', 'price_mismatch']),
              help='Export entries with specific action')
@pass_context
def export(ctx, output_file, days_back, session_id, part_number, action):
    """
    Export discovery logs to CSV file.
    
    Examples:
        # Export all recent discoveries
        invoice-checker discovery export discoveries.csv
        
        # Export discoveries from last 7 days
        invoice-checker discovery export recent.csv --days-back 7
        
        # Export specific session
        invoice-checker discovery export session.csv --session-id abc123
    """
    try:
        db_manager = ctx.get_db_manager()
        output_path = Path(output_file)
        
        # Validate session ID if provided
        if session_id:
            session_id = validate_session_id(session_id)
        
        # Get discovery logs
        logs = db_manager.get_discovery_logs(
            part_number=part_number,
            session_id=session_id,
            days_back=days_back
        )
        
        # Filter by action if specified
        if action:
            logs = [log for log in logs if log.action_taken == action]
        
        if not logs:
            print_info("No discovery log entries found matching the criteria.")
            return
        
        # Convert to export format
        export_data = []
        for log in logs:
            export_data.append({
                'id': log.id,
                'part_number': log.part_number,
                'invoice_number': log.invoice_number or '',
                'invoice_date': log.invoice_date or '',
                'discovered_price': float(log.discovered_price) if log.discovered_price else '',
                'authorized_price': float(log.authorized_price) if log.authorized_price else '',
                'action_taken': log.action_taken,
                'user_decision': log.user_decision or '',
                'discovery_date': log.discovery_date.isoformat() if log.discovery_date else '',
                'processing_session_id': log.processing_session_id or '',
                'notes': log.notes or ''
            })
        
        # Write to CSV
        write_csv(export_data, output_path)
        
        print_success(f"Exported {len(export_data)} discovery log entries to {output_path}")
        
        # Show export summary
        export_summary = {
            'total_entries': len(export_data),
            'date_range': f"Last {days_back} days" if days_back else "All time",
            'output_file': str(output_path)
        }
        
        if session_id:
            export_summary['session_id'] = session_id
        if part_number:
            export_summary['part_number'] = part_number
        if action:
            export_summary['action_filter'] = action
        
        display_summary("Export Summary", export_summary)
        
    except ValidationError as e:
        raise CLIError(f"Validation error: {e}")
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to export discovery logs")
        raise CLIError(f"Failed to export discovery logs: {e}")


@discovery_group.command()
@click.option('--retention-days', '-r', type=int, default=365,
              help='Keep logs newer than N days')
@click.option('--dry-run', is_flag=True,
              help='Show what would be deleted without deleting')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@pass_context
def cleanup(ctx, retention_days, dry_run, force):
    """
    Clean up old discovery log entries.
    
    Examples:
        # Clean up logs older than 1 year (default)
        invoice-checker discovery cleanup
        
        # Clean up logs older than 90 days
        invoice-checker discovery cleanup --retention-days 90
        
        # Dry run to see what would be deleted
        invoice-checker discovery cleanup --dry-run
    """
    try:
        # Validate retention days
        retention_days = validate_positive_integer(retention_days, min_value=1, max_value=3650)
        
        db_manager = ctx.get_db_manager()
        
        # Get count of logs that would be deleted
        all_logs = db_manager.get_discovery_logs()
        
        # Calculate cutoff date
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        old_logs = [log for log in all_logs 
                   if log.discovery_date and log.discovery_date < cutoff_date]
        
        if not old_logs:
            print_info(f"No discovery logs older than {retention_days} days found.")
            return
        
        print_info(f"Found {len(old_logs)} discovery log entries older than {retention_days} days")
        print_info(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if dry_run:
            print_info("Dry run mode - no entries will be deleted")
            
            # Show breakdown by action type
            actions = {}
            for log in old_logs:
                actions[log.action_taken] = actions.get(log.action_taken, 0) + 1
            
            print_info("Entries that would be deleted by action type:")
            for action_type, count in sorted(actions.items()):
                print_info(f"  {action_type}: {count}")
            
            return
        
        # Confirm cleanup
        if not force:
            print_warning(f"This will permanently delete {len(old_logs)} discovery log entries.")
            print_warning("This action cannot be undone!")
            
            if not prompt_for_confirmation(
                f"Delete discovery logs older than {retention_days} days?",
                default=False
            ):
                print_info("Cleanup cancelled.")
                return
        
        # Perform cleanup
        deleted_count = db_manager.cleanup_old_discovery_logs(retention_days)
        
        print_success(f"Cleaned up {deleted_count} old discovery log entries!")
        
        # Show cleanup summary
        cleanup_summary = {
            'entries_deleted': deleted_count,
            'retention_days': retention_days,
            'cutoff_date': cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        display_summary("Cleanup Summary", cleanup_summary)
        
        # Show remaining log count
        remaining_logs = db_manager.get_discovery_logs()
        print_info(f"Remaining discovery log entries: {len(remaining_logs)}")
        
    except ValidationError as e:
        raise CLIError(f"Validation error: {e}")
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to cleanup discovery logs")
        raise CLIError(f"Failed to cleanup discovery logs: {e}")


# Add commands to the group
discovery_group.add_command(list)
discovery_group.add_command(export)
discovery_group.add_command(cleanup)