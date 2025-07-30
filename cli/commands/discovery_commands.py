"""
CLI commands for interactive part discovery management.

This module provides commands for managing the part discovery system,
including reviewing unknown parts, managing discovery sessions, and
configuring discovery behavior.
"""

import logging
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cli.context import get_context
from cli.formatters import format_success, format_error, format_warning, format_info
from cli.exceptions import CLIError, UserCancelledError
from processing.part_discovery_service import InteractivePartDiscoveryService
from processing.part_discovery_prompts import BatchDiscoveryPrompt
from database.models import DatabaseError


logger = logging.getLogger(__name__)
console = Console()


@click.group(name='discovery')
@click.pass_context
def discovery_group(ctx):
    """
    Part discovery management commands.
    
    These commands help manage the interactive part discovery system,
    including reviewing unknown parts and managing discovery sessions.
    """
    pass


@discovery_group.command('review')
@click.option('--session-id', '-s', help='Discovery session ID to review')
@click.option('--interactive/--no-interactive', default=True, 
              help='Enable interactive review and addition of parts')
@click.option('--output', '-o', type=click.Path(), 
              help='Output file for unknown parts report (CSV format)')
@click.pass_context
def review_unknown_parts(ctx, session_id: Optional[str], interactive: bool, output: Optional[str]):
    """
    Review unknown parts discovered during invoice processing.
    
    This command allows you to review parts that were discovered but not
    added to the database during invoice processing. You can choose to
    add them interactively or export them for later review.
    
    Examples:
        invoice-checker discovery review
        invoice-checker discovery review --session-id abc123
        invoice-checker discovery review --no-interactive --output unknown_parts.csv
    """
    try:
        app_context = get_context()
        discovery_service = InteractivePartDiscoveryService(app_context.db_manager)
        
        if not session_id:
            # Get the most recent session with unknown parts
            session_id = _get_most_recent_discovery_session(discovery_service)
            if not session_id:
                console.print(format_info("No discovery sessions with unknown parts found."))
                return
        
        # Get unknown parts for review
        unknown_parts_data = discovery_service.get_unknown_parts_for_review(session_id)
        
        if not unknown_parts_data:
            console.print(format_info(f"No unknown parts found in session {session_id}."))
            return
        
        console.print(format_info(f"Found {len(unknown_parts_data)} unknown parts in session {session_id}"))
        
        if output:
            # Export to CSV
            _export_unknown_parts_csv(unknown_parts_data, output)
            console.print(format_success(f"Unknown parts exported to {output}"))
            return
        
        if interactive:
            # Interactive review and addition
            batch_prompt = BatchDiscoveryPrompt(console)
            decisions = batch_prompt.review_unknown_parts_batch(unknown_parts_data)
            
            if decisions:
                # Process the decisions
                results = _process_batch_decisions(discovery_service, decisions, session_id)
                _display_batch_results(results)
            else:
                console.print(format_info("No parts were processed."))
        else:
            # Just display the unknown parts
            _display_unknown_parts_table(unknown_parts_data)
    
    except (DatabaseError, CLIError) as e:
        console.print(format_error(f"Error reviewing unknown parts: {e}"))
        ctx.exit(1)
    except UserCancelledError:
        console.print(format_warning("Review cancelled by user."))
    except Exception as e:
        logger.exception("Unexpected error in discovery review")
        console.print(format_error(f"Unexpected error: {e}"))
        ctx.exit(1)


@discovery_group.command('sessions')
@click.option('--limit', '-l', default=10, help='Number of recent sessions to show')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed session information')
@click.pass_context
def list_sessions(ctx, limit: int, detailed: bool):
    """
    List recent discovery sessions.
    
    Shows information about recent part discovery sessions, including
    the number of parts discovered and processed.
    
    Examples:
        invoice-checker discovery sessions
        invoice-checker discovery sessions --limit 20 --detailed
    """
    try:
        app_context = get_context()
        
        # Check if database manager is available
        if not app_context.db_manager:
            console.print(format_info("No discovery sessions found."))
            return
        
        # Get recent discovery sessions from database logs
        logs = app_context.db_manager.get_discovery_logs(limit=limit * 10)  # Get more to group by session
        
        if not logs:
            console.print(format_info("No discovery sessions found."))
            return
        
        # Group logs by session
        sessions = {}
        for log in logs:
            session_id = log.processing_session_id
            if session_id not in sessions:
                sessions[session_id] = {
                    'session_id': session_id,
                    'parts_discovered': set(),
                    'parts_added': 0,
                    'first_seen': log.created_at,
                    'last_seen': log.created_at
                }
            
            sessions[session_id]['parts_discovered'].add(log.part_number)
            if log.action_taken == 'added':
                sessions[session_id]['parts_added'] += 1
            
            # Update time range
            if log.created_at < sessions[session_id]['first_seen']:
                sessions[session_id]['first_seen'] = log.created_at
            if log.created_at > sessions[session_id]['last_seen']:
                sessions[session_id]['last_seen'] = log.created_at
        
        # Convert to list and sort by most recent
        session_list = list(sessions.values())
        session_list.sort(key=lambda x: x['last_seen'], reverse=True)
        session_list = session_list[:limit]
        
        if detailed:
            _display_detailed_sessions(session_list)
        else:
            _display_sessions_table(session_list)
    
    except DatabaseError as e:
        console.print(format_error(f"Database error: {e}"))
        ctx.exit(1)
    except Exception as e:
        logger.exception("Unexpected error listing sessions")
        console.print(format_error(f"Unexpected error: {e}"))
        ctx.exit(1)


@discovery_group.command('stats')
@click.option('--session-id', '-s', help='Show stats for specific session')
@click.option('--days', '-d', default=30, help='Number of days to include in stats')
@click.pass_context
def discovery_stats(ctx, session_id: Optional[str], days: int):
    """
    Show discovery statistics.
    
    Displays statistics about part discovery activities, including
    discovery rates, success rates, and trending information.
    
    Examples:
        invoice-checker discovery stats
        invoice-checker discovery stats --session-id abc123
        invoice-checker discovery stats --days 7
    """
    try:
        app_context = get_context()
        
        if session_id:
            # Show stats for specific session
            discovery_service = InteractivePartDiscoveryService(app_context.db_manager)
            summary = discovery_service.get_session_summary(session_id)
            _display_session_stats(summary)
        else:
            # Show overall stats
            logs = app_context.db_manager.get_discovery_logs(days=days)
            stats = _calculate_discovery_stats(logs)
            _display_overall_stats(stats, days)
    
    except DatabaseError as e:
        console.print(format_error(f"Database error: {e}"))
        ctx.exit(1)
    except Exception as e:
        logger.exception("Unexpected error getting discovery stats")
        console.print(format_error(f"Unexpected error: {e}"))
        ctx.exit(1)


@discovery_group.command('export')
@click.option('--session-id', '-s', help='Session ID to export')
@click.option('--output', '-o', required=True, type=click.Path(), 
              help='Output file path (CSV format)')
@click.option('--include-added', is_flag=True, 
              help='Include parts that were already added to database')
@click.pass_context
def export_discoveries(ctx, session_id: Optional[str], output: str, include_added: bool):
    """
    Export discovery data to CSV file.
    
    Exports part discovery information to a CSV file for external analysis
    or bulk processing in spreadsheet applications.
    
    Examples:
        invoice-checker discovery export --output discoveries.csv
        invoice-checker discovery export --session-id abc123 --output session_abc123.csv
        invoice-checker discovery export --output all_discoveries.csv --include-added
    """
    try:
        app_context = get_context()
        
        # Get discovery logs
        if session_id:
            logs = app_context.db_manager.get_discovery_logs(session_id=session_id)
        else:
            logs = app_context.db_manager.get_discovery_logs()
        
        if not logs:
            console.print(format_info("No discovery data found to export."))
            return
        
        # Filter logs if needed
        if not include_added:
            logs = [log for log in logs if log.action_taken != 'added']
        
        # Export to CSV
        _export_discovery_logs_csv(logs, output)
        console.print(format_success(f"Exported {len(logs)} discovery records to {output}"))
    
    except DatabaseError as e:
        console.print(format_error(f"Database error: {e}"))
        ctx.exit(1)
    except Exception as e:
        logger.exception("Unexpected error exporting discoveries")
        console.print(format_error(f"Unexpected error: {e}"))
        ctx.exit(1)


def _get_most_recent_discovery_session(discovery_service: InteractivePartDiscoveryService) -> Optional[str]:
    """Get the most recent discovery session with unknown parts."""
    try:
        # This would need to be implemented in the database manager
        # For now, return None to indicate no session found
        return None
    except Exception:
        return None


def _export_unknown_parts_csv(unknown_parts_data: List[dict], output_path: str):
    """Export unknown parts data to CSV file."""
    import csv
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'part_number', 'occurrences', 'unique_invoices', 'avg_price', 
            'min_price', 'max_price', 'price_variance', 'descriptions'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for part_data in unknown_parts_data:
            row = part_data.copy()
            # Convert descriptions list to string
            if 'descriptions' in row and isinstance(row['descriptions'], list):
                row['descriptions'] = '; '.join(row['descriptions'])
            writer.writerow(row)


def _export_discovery_logs_csv(logs: List, output_path: str):
    """Export discovery logs to CSV file."""
    import csv
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'part_number', 'invoice_number', 'invoice_date', 'discovered_price',
            'authorized_price', 'action_taken', 'user_decision', 'processing_session_id',
            'notes', 'created_at'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for log in logs:
            writer.writerow({
                'part_number': log.part_number,
                'invoice_number': log.invoice_number,
                'invoice_date': log.invoice_date,
                'discovered_price': float(log.discovered_price) if log.discovered_price else None,
                'authorized_price': float(log.authorized_price) if log.authorized_price else None,
                'action_taken': log.action_taken,
                'user_decision': log.user_decision,
                'processing_session_id': log.processing_session_id,
                'notes': log.notes,
                'created_at': log.created_at.isoformat() if log.created_at else None
            })


def _process_batch_decisions(discovery_service: InteractivePartDiscoveryService, 
                           decisions: List[dict], session_id: str) -> List[dict]:
    """Process batch decisions and return results."""
    results = []
    
    for decision in decisions:
        if decision['action'] == 'add_to_database_now':
            try:
                # Create part from decision
                part_details = decision['part_details']
                from database.models import Part
                
                part = Part(
                    part_number=decision['part_number'],
                    authorized_price=part_details['authorized_price'],
                    description=part_details.get('description'),
                    category=part_details.get('category'),
                    source='batch_discovery',
                    notes=part_details.get('notes')
                )
                
                created_part = discovery_service.db_manager.create_part(part)
                
                results.append({
                    'part_number': decision['part_number'],
                    'action': 'added',
                    'success': True,
                    'part': created_part
                })
                
            except Exception as e:
                results.append({
                    'part_number': decision['part_number'],
                    'action': 'failed',
                    'success': False,
                    'error': str(e)
                })
        else:
            results.append({
                'part_number': decision['part_number'],
                'action': decision['action'],
                'success': True
            })
    
    return results


def _display_batch_results(results: List[dict]):
    """Display results of batch processing."""
    table = Table(title="Batch Processing Results", show_header=True, header_style="bold magenta")
    table.add_column("Part Number", style="cyan")
    table.add_column("Action", style="white")
    table.add_column("Status", style="white")
    table.add_column("Details", style="white")
    
    for result in results:
        status = "✓ Success" if result['success'] else "✗ Failed"
        status_style = "green" if result['success'] else "red"
        
        details = ""
        if not result['success'] and 'error' in result:
            details = result['error']
        elif result['action'] == 'added':
            details = "Added to database"
        elif result['action'] == 'skipped':
            details = "Skipped by user"
        
        table.add_row(
            result['part_number'],
            result['action'].replace('_', ' ').title(),
            f"[{status_style}]{status}[/{status_style}]",
            details
        )
    
    console.print(table)


def _display_unknown_parts_table(unknown_parts_data: List[dict]):
    """Display unknown parts in a table format."""
    table = Table(title="Unknown Parts", show_header=True, header_style="bold magenta")
    table.add_column("Part Number", style="cyan")
    table.add_column("Occurrences", justify="center")
    table.add_column("Avg Price", justify="right")
    table.add_column("Price Range", justify="right")
    table.add_column("Description", max_width=30)
    
    for part_data in unknown_parts_data:
        part_number = part_data['part_number']
        occurrences = str(part_data['occurrences'])
        
        if 'avg_price' in part_data:
            avg_price = f"${part_data['avg_price']:.2f}"
            if part_data['min_price'] == part_data['max_price']:
                price_range = f"${part_data['min_price']:.2f}"
            else:
                price_range = f"${part_data['min_price']:.2f} - ${part_data['max_price']:.2f}"
        else:
            avg_price = "N/A"
            price_range = "N/A"
        
        descriptions = part_data.get('descriptions', [])
        description = descriptions[0] if descriptions else "N/A"
        if len(description) > 30:
            description = description[:27] + "..."
        
        table.add_row(part_number, occurrences, avg_price, price_range, description)
    
    console.print(table)


def _display_sessions_table(sessions: List[dict]):
    """Display sessions in a table format."""
    table = Table(title="Discovery Sessions", show_header=True, header_style="bold magenta")
    table.add_column("Session ID", style="cyan", max_width=20)
    table.add_column("Parts Discovered", justify="center")
    table.add_column("Parts Added", justify="center")
    table.add_column("First Seen", style="white")
    table.add_column("Last Seen", style="white")
    
    for session in sessions:
        session_id = session['session_id'][:18] + "..." if len(session['session_id']) > 20 else session['session_id']
        parts_discovered = str(len(session['parts_discovered']))
        parts_added = str(session['parts_added'])
        first_seen = session['first_seen'].strftime('%Y-%m-%d %H:%M') if session['first_seen'] else "N/A"
        last_seen = session['last_seen'].strftime('%Y-%m-%d %H:%M') if session['last_seen'] else "N/A"
        
        table.add_row(session_id, parts_discovered, parts_added, first_seen, last_seen)
    
    console.print(table)


def _display_detailed_sessions(sessions: List[dict]):
    """Display detailed session information."""
    for session in sessions:
        panel_content = []
        panel_content.append(f"Session ID: {session['session_id']}")
        panel_content.append(f"Parts Discovered: {len(session['parts_discovered'])}")
        panel_content.append(f"Parts Added: {session['parts_added']}")
        panel_content.append(f"First Seen: {session['first_seen'].strftime('%Y-%m-%d %H:%M:%S') if session['first_seen'] else 'N/A'}")
        panel_content.append(f"Last Seen: {session['last_seen'].strftime('%Y-%m-%d %H:%M:%S') if session['last_seen'] else 'N/A'}")
        
        if session['parts_discovered']:
            panel_content.append(f"Discovered Parts: {', '.join(list(session['parts_discovered'])[:5])}")
            if len(session['parts_discovered']) > 5:
                panel_content.append(f"... and {len(session['parts_discovered']) - 5} more")
        
        panel = Panel(
            "\n".join(panel_content),
            title=f"Session {session['session_id'][:8]}...",
            title_align="left",
            border_style="blue"
        )
        console.print(panel)
        console.print()


def _display_session_stats(summary: dict):
    """Display statistics for a specific session."""
    panel_content = []
    panel_content.append(f"Session ID: {summary.get('session_id', 'N/A')}")
    panel_content.append(f"Unique Parts Discovered: {summary.get('unique_parts_discovered', 0)}")
    panel_content.append(f"Total Occurrences: {summary.get('total_occurrences', 0)}")
    panel_content.append(f"Parts Added: {summary.get('parts_added', 0)}")
    panel_content.append(f"Processing Mode: {summary.get('processing_mode', 'N/A')}")
    
    if 'duration_minutes' in summary:
        panel_content.append(f"Duration: {summary['duration_minutes']:.1f} minutes")
    
    panel = Panel(
        "\n".join(panel_content),
        title="Session Statistics",
        title_align="left",
        border_style="green"
    )
    console.print(panel)


def _display_overall_stats(stats: dict, days: int):
    """Display overall discovery statistics."""
    panel_content = []
    panel_content.append(f"Time Period: Last {days} days")
    panel_content.append(f"Total Discoveries: {stats.get('total_discoveries', 0)}")
    panel_content.append(f"Unique Parts: {stats.get('unique_parts', 0)}")
    panel_content.append(f"Parts Added: {stats.get('parts_added', 0)}")
    panel_content.append(f"Parts Skipped: {stats.get('parts_skipped', 0)}")
    panel_content.append(f"Success Rate: {stats.get('success_rate', 0):.1f}%")
    panel_content.append(f"Active Sessions: {stats.get('active_sessions', 0)}")
    
    panel = Panel(
        "\n".join(panel_content),
        title="Discovery Statistics",
        title_align="left",
        border_style="green"
    )
    console.print(panel)


def _calculate_discovery_stats(logs: List) -> dict:
    """Calculate overall discovery statistics from logs."""
    if not logs:
        return {
            'total_discoveries': 0,
            'unique_parts': 0,
            'parts_added': 0,
            'parts_skipped': 0,
            'success_rate': 0.0,
            'active_sessions': 0
        }
    
    unique_parts = set()
    parts_added = 0
    parts_skipped = 0
    sessions = set()
    
    for log in logs:
        unique_parts.add(log.part_number)
        sessions.add(log.processing_session_id)
        
        if log.action_taken == 'added':
            parts_added += 1
        elif log.action_taken == 'skipped':
            parts_skipped += 1
    
    total_processed = parts_added + parts_skipped
    success_rate = (parts_added / total_processed * 100) if total_processed > 0 else 0
    
    return {
        'total_discoveries': len(logs),
        'unique_parts': len(unique_parts),
        'parts_added': parts_added,
        'parts_skipped': parts_skipped,
        'success_rate': success_rate,
        'active_sessions': len(sessions)
    }