"""
Parts management commands for the CLI interface.

This module implements all parts-related commands including:
- add: Add new part to database
- list: List parts with filtering
- get: Get single part details
- update: Update existing part
- delete: Delete/deactivate part
- import: Import parts from CSV
- export: Export parts to CSV
- stats: Parts statistics
"""

import csv
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from decimal import Decimal

import click

from cli.context import pass_context
from cli.validators import PART_NUMBER, PRICE, OUTPUT_FORMAT
from cli.formatters import (
    print_success, print_warning, print_error, print_info,
    format_table, write_csv, format_json, display_summary
)
from cli.progress import show_import_progress
from cli.prompts import prompt_for_part_details, prompt_for_confirmation
from cli.exceptions import CLIError, ValidationError
from cli.error_handlers import error_handler
from cli.validation_helpers import ValidationHelper
from database.models import Part, PartNotFoundError, DatabaseError


logger = logging.getLogger(__name__)


# Create parts command group
@click.group(name='parts')
def parts_group():
    """Parts management commands."""
    pass


@parts_group.command()
@click.argument('part_number', type=PART_NUMBER, required=False)
@click.argument('price', type=PRICE, required=False)
@click.option('--description', '-d', type=str, help='Part description')
@click.option('--category', '-c', type=str, help='Part category')
@click.option('--source', type=click.Choice(['manual', 'discovered', 'imported']),
              default='manual', help='Source of part data')
@click.option('--notes', type=str, help='Additional notes')
@pass_context
@error_handler({'operation': 'part_creation', 'command': 'parts add'})
def add(ctx, part_number, price, description, category, source, notes):
    """
    Add a new part to the master parts database.
    
    Examples:
        # Add a basic part
        invoice-checker parts add GP0171NAVY 15.50
        
        # Add a part with full details
        invoice-checker parts add GP0171NAVY 15.50 \\
            --description "Navy Work Pants" \\
            --category "Clothing" \\
            --notes "Standard work uniform item"
    """
    # Get part details interactively if not provided
    if not part_number or not price:
        if part_number and not price:
            # Part number provided but not price
            details = prompt_for_part_details(part_number)
        else:
            # Neither provided
            details = prompt_for_part_details()
        
        part_number = details['part_number']
        price = details['authorized_price']
        description = details.get('description') or description
        category = details.get('category') or category
        notes = details.get('notes') or notes
    
    # Create part object
    part = Part(
        part_number=part_number,
        authorized_price=price,
        description=description,
        category=category,
        source=source,
        notes=notes
    )
    
    # Show confirmation
    part_details = {
        'part_number': part.part_number,
        'authorized_price': part.authorized_price,
        'description': part.description,
        'category': part.category,
        'source': part.source,
        'notes': part.notes
    }
    
    if not prompt_for_confirmation("Add this part to the database?",
                                 default=True, show_details=part_details):
        print_info("Part addition cancelled.")
        return
    
    # Add to database
    db_manager = ctx.get_db_manager()
    created_part = db_manager.create_part(part)
    
    print_success(f"Part {created_part.part_number} added successfully!")


@parts_group.command()
@click.option('--category', '-c', type=str, help='Filter by category')
@click.option('--active-only', is_flag=True, default=True, help='Show only active parts')
@click.option('--include-inactive', is_flag=True, help='Include inactive parts')
@click.option('--format', '-f', type=OUTPUT_FORMAT, default='table',
              help='Output format (table, csv, json)')
@click.option('--limit', '-l', type=int, help='Maximum number of results')
@click.option('--offset', type=int, default=0, help='Skip number of results')
@click.option('--sort-by', type=click.Choice(['part_number', 'price', 'created_date']),
              default='part_number', help='Sort by field')
@click.option('--order', type=click.Choice(['asc', 'desc']), default='asc',
              help='Sort order')
@pass_context
def list(ctx, category, active_only, include_inactive, format, limit, offset, sort_by, order):
    """
    List parts with filtering and sorting options.
    
    Examples:
        # List all active parts
        invoice-checker parts list
        
        # List parts in a specific category
        invoice-checker parts list --category "Clothing"
        
        # Export parts to CSV
        invoice-checker parts list --format csv > parts.csv
    """
    try:
        db_manager = ctx.get_db_manager()
        
        # Determine active filter
        show_active_only = active_only and not include_inactive
        
        # Get parts from database
        parts = db_manager.list_parts(
            active_only=show_active_only,
            category=category,
            limit=limit,
            offset=offset
        )
        
        if not parts:
            print_info("No parts found matching the criteria.")
            return
        
        # Convert to display format
        parts_data = []
        for part in parts:
            parts_data.append({
                'Part Number': part.part_number,
                'Price': part.authorized_price,
                'Description': part.description or '',
                'Category': part.category or '',
                'Source': part.source,
                'Active': 'Yes' if part.is_active else 'No',
                'Created': part.created_date.strftime('%Y-%m-%d') if part.created_date else ''
            })
        
        # Sort results
        reverse = (order == 'desc')
        if sort_by == 'part_number':
            parts_data.sort(key=lambda x: x['Part Number'], reverse=reverse)
        elif sort_by == 'price':
            parts_data.sort(key=lambda x: float(x['Price']), reverse=reverse)
        elif sort_by == 'created_date':
            parts_data.sort(key=lambda x: x['Created'], reverse=reverse)
        
        # Display results
        if format == 'table':
            click.echo(format_table(parts_data))
        elif format == 'csv':
            import sys
            write_csv(parts_data, sys.stdout)
        elif format == 'json':
            click.echo(format_json(parts_data))
        
        # Show summary
        print_info(f"Found {len(parts)} parts")
        
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to list parts")
        raise CLIError(f"Failed to list parts: {e}")


@parts_group.command()
@click.argument('part_number', type=PART_NUMBER)
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.option('--include-history', is_flag=True, help='Include discovery log history')
@pass_context
@error_handler({'operation': 'part_retrieval', 'command': 'parts get'})
def get(ctx, part_number, format, include_history):
    """
    Retrieve detailed information about a specific part.
    
    Examples:
        # Get part details
        invoice-checker parts get GP0171NAVY
        
        # Get part with discovery history
        invoice-checker parts get GP0171NAVY --include-history
    """
    db_manager = ctx.get_db_manager()
    
    # Get part from database
    part = db_manager.get_part(part_number)
    
    # Prepare part data
    part_data = {
        'Part Number': part.part_number,
        'Authorized Price': f"{part.authorized_price:.2f}",
        'Description': part.description or 'N/A',
        'Category': part.category or 'N/A',
        'Source': part.source,
        'First Seen Invoice': part.first_seen_invoice or 'N/A',
        'Active': 'Yes' if part.is_active else 'No',
        'Created Date': part.created_date.strftime('%Y-%m-%d %H:%M:%S') if part.created_date else 'N/A',
        'Last Updated': part.last_updated.strftime('%Y-%m-%d %H:%M:%S') if part.last_updated else 'N/A',
        'Notes': part.notes or 'N/A'
    }
    
    # Display part information
    if format == 'table':
        click.echo(f"\nPart Details: {part_number}")
        click.echo("=" * 40)
        for key, value in part_data.items():
            click.echo(f"{key:20}: {value}")
    elif format == 'json':
        click.echo(format_json(part_data))
    
    # Include discovery history if requested
    if include_history:
        discovery_logs = db_manager.get_discovery_logs(part_number=part_number)
        if discovery_logs:
            click.echo(f"\nDiscovery History ({len(discovery_logs)} entries):")
            click.echo("-" * 40)
            
            history_data = []
            for log in discovery_logs:
                history_data.append({
                    'Date': log.discovery_date.strftime('%Y-%m-%d %H:%M:%S') if log.discovery_date else 'N/A',
                    'Invoice': log.invoice_number or 'N/A',
                    'Action': log.action_taken,
                    'Discovered Price': log.discovered_price or 'N/A',
                    'Notes': log.notes or ''
                })
            
            if format == 'table':
                click.echo(format_table(history_data))
            elif format == 'json':
                click.echo(format_json(history_data))
        else:
            print_info("No discovery history found for this part.")


@parts_group.command()
@click.argument('part_number', type=PART_NUMBER)
@click.option('--price', '-p', type=PRICE, help='New authorized price')
@click.option('--description', '-d', type=str, help='New description')
@click.option('--category', '-c', type=str, help='New category')
@click.option('--notes', type=str, help='New notes')
@click.option('--activate', is_flag=True, help='Activate part')
@click.option('--deactivate', is_flag=True, help='Deactivate part')
@pass_context
def update(ctx, part_number, price, description, category, notes, activate, deactivate):
    """
    Update an existing part's information.
    
    Examples:
        # Update part price
        invoice-checker parts update GP0171NAVY --price 16.00
        
        # Update multiple fields
        invoice-checker parts update GP0171NAVY \\
            --price 16.00 \\
            --description "Updated Navy Work Pants" \\
            --category "Workwear"
        
        # Deactivate a part
        invoice-checker parts update GP0171NAVY --deactivate
    """
    try:
        db_manager = ctx.get_db_manager()
        
        # Get existing part
        part = db_manager.get_part(part_number)
        
        # Track what's being updated
        updates = {}
        
        # Update fields if provided
        if price is not None:
            part.authorized_price = price
            updates['price'] = price
        
        if description is not None:
            part.description = description
            updates['description'] = description
        
        if category is not None:
            part.category = category
            updates['category'] = category
        
        if notes is not None:
            part.notes = notes
            updates['notes'] = notes
        
        if activate and deactivate:
            raise CLIError("Cannot both activate and deactivate a part")
        
        if activate:
            part.is_active = True
            updates['status'] = 'activated'
        elif deactivate:
            part.is_active = False
            updates['status'] = 'deactivated'
        
        if not updates:
            print_info("No updates specified. Use --help to see available options.")
            return
        
        # Show confirmation
        if not prompt_for_confirmation(
            f"Update part {part_number} with the following changes?",
            default=True,
            show_details=updates
        ):
            print_info("Update cancelled.")
            return
        
        # Update in database
        updated_part = db_manager.update_part(part)
        
        print_success(f"Part {updated_part.part_number} updated successfully!")
        
        # Show updated details
        update_summary = []
        for field, value in updates.items():
            update_summary.append(f"  {field.title()}: {value}")
        
        if update_summary:
            click.echo("Updated fields:")
            click.echo("\n".join(update_summary))
        
    except PartNotFoundError:
        raise CLIError(f"Part '{part_number}' not found")
    except ValidationError as e:
        raise CLIError(f"Validation error: {e}")
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to update part")
        raise CLIError(f"Failed to update part: {e}")


@parts_group.command()
@click.argument('part_number', type=PART_NUMBER)
@click.option('--soft', is_flag=True, default=True, help='Soft delete (deactivate)')
@click.option('--hard', is_flag=True, help='Permanently delete from database')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@pass_context
def delete(ctx, part_number, soft, hard, force):
    """
    Delete or deactivate a part.
    
    Examples:
        # Soft delete (deactivate) a part
        invoice-checker parts delete GP0171NAVY
        
        # Permanently delete a part
        invoice-checker parts delete GP0171NAVY --hard
        
        # Force delete without confirmation
        invoice-checker parts delete GP0171NAVY --force
    """
    try:
        if soft and hard:
            raise CLIError("Cannot specify both --soft and --hard options")
        
        # Default to soft delete
        soft_delete = not hard
        
        db_manager = ctx.get_db_manager()
        
        # Check if part exists
        try:
            part = db_manager.get_part(part_number)
        except PartNotFoundError:
            raise CLIError(f"Part '{part_number}' not found")
        
        # Confirm deletion
        if not force:
            action = "deactivate" if soft_delete else "permanently delete"
            if not prompt_for_confirmation(
                f"Are you sure you want to {action} part '{part_number}'?",
                default=False
            ):
                print_info("Deletion cancelled.")
                return
        
        # Delete part
        db_manager.delete_part(part_number, soft_delete=soft_delete)
        
        action = "deactivated" if soft_delete else "permanently deleted"
        print_success(f"Part {part_number} {action} successfully!")
        
        if soft_delete:
            print_info("Part is now inactive but remains in the database.")
        else:
            print_warning("Part has been permanently removed from the database.")
        
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to delete part")
        raise CLIError(f"Failed to delete part: {e}")


@parts_group.command(name='import')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--update-existing', is_flag=True, help='Update existing parts')
@click.option('--dry-run', is_flag=True, help='Validate data without making changes')
@click.option('--batch-size', type=int, default=100, help='Process in batches')
@click.option('--skip-duplicates', is_flag=True, help='Skip duplicate parts without error')
@click.option('--transform-data', is_flag=True, help='Apply data transformations during import')
@click.option('--mapping-file', type=click.Path(exists=True), help='CSV column mapping file')
@pass_context
def import_parts(ctx, input_file, update_existing, dry_run, batch_size, skip_duplicates, transform_data, mapping_file):
    """
    Import parts from a CSV file.
    
    The CSV file should have columns: part_number, authorized_price, description, category, notes
    
    Examples:
        # Import parts from CSV
        invoice-checker parts import parts.csv
        
        # Dry run to validate data
        invoice-checker parts import parts.csv --dry-run
        
        # Import and update existing parts
        invoice-checker parts import parts.csv --update-existing
    """
    try:
        input_path = Path(input_file)
        
        # Load column mapping if provided
        column_mapping = None
        if mapping_file:
            column_mapping = _load_column_mapping(Path(mapping_file))
            print_info(f"Loaded column mapping from {mapping_file}")
        
        # Read and validate CSV file
        parts_data = _read_parts_csv(input_path, column_mapping, transform_data)
        
        if not parts_data:
            raise CLIError("No valid parts found in CSV file")
        
        print_info(f"Found {len(parts_data)} parts in CSV file")
        
        if dry_run:
            print_info("Dry run mode - no changes will be made")
            _validate_parts_data(parts_data)
            print_success("All parts data is valid!")
            return
        
        # Confirm import
        if not prompt_for_confirmation(
            f"Import {len(parts_data)} parts from {input_path}?",
            default=True
        ):
            print_info("Import cancelled.")
            return
        
        # Import parts
        db_manager = ctx.get_db_manager()
        results = _import_parts_batch(
            parts_data, db_manager, update_existing, batch_size, skip_duplicates
        )
        
        # Display results
        display_summary("Import Results", results)
        print_success("Parts import completed!")
        
    except Exception as e:
        logger.exception("Failed to import parts")
        raise CLIError(f"Failed to import parts: {e}")


@parts_group.command()
@click.argument('output_file', type=click.Path())
@click.option('--category', '-c', type=str, help='Filter by category')
@click.option('--active-only', is_flag=True, default=True, help='Export only active parts')
@click.option('--include-inactive', is_flag=True, help='Include inactive parts')
@click.option('--format', '-f', type=click.Choice(['csv', 'json']), default='csv', help='Export format')
@pass_context
def export(ctx, output_file, category, active_only, include_inactive, format):
    """
    Export parts to a CSV or JSON file.

    Examples:
        # Export all active parts
        invoice-checker parts export parts.csv

        # Export parts in a specific category
        invoice-checker parts export clothing_parts.csv --category "Clothing"

        # Export all parts including inactive
        invoice-checker parts export all_parts.csv --include-inactive

        # Export as JSON
        invoice-checker parts export parts.json --format json
    """
    try:
        db_manager = ctx.get_db_manager()
        output_path = Path(output_file)

        # Determine active filter
        show_active_only = active_only and not include_inactive

        # Get parts from database
        parts = db_manager.list_parts(
            active_only=show_active_only,
            category=category
        )

        if not parts:
            print_info("No parts found matching the criteria.")
            return

        # Convert to export format
        export_data = []
        for part in parts:
            export_data.append({
                'part_number': part.part_number,
                'authorized_price': float(part.authorized_price),
                'description': part.description or '',
                'category': part.category or '',
                'source': part.source,
                'first_seen_invoice': part.first_seen_invoice or '',
                'is_active': part.is_active,
                'notes': part.notes or ''
            })

        if format == 'csv':
            write_csv(export_data, output_path)
        elif format == 'json':
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)

        print_success(f"Exported {len(export_data)} parts to {output_path}")

    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to export parts")
        raise CLIError(f"Failed to export parts: {e}")


@parts_group.command()
@click.option('--category', '-c', type=str, help='Filter by category')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@pass_context
def stats(ctx, category, format):
    """
    Display statistical information about parts.
    
    Examples:
        # Show overall parts statistics
        invoice-checker parts stats
        
        # Show statistics for a specific category
        invoice-checker parts stats --category "Clothing"
    """
    try:
        db_manager = ctx.get_db_manager()
        
        # Get database statistics
        db_stats = db_manager.get_database_stats()
        
        # Calculate parts statistics
        all_parts = db_manager.list_parts(active_only=False, category=category)
        active_parts = [p for p in all_parts if p.is_active]
        inactive_parts = [p for p in all_parts if not p.is_active]
        
        # Calculate price statistics
        if active_parts:
            prices = [float(p.authorized_price) for p in active_parts]
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
        else:
            avg_price = min_price = max_price = 0
        
        # Get category breakdown
        categories = {}
        for part in active_parts:
            cat = part.category or 'Uncategorized'
            categories[cat] = categories.get(cat, 0) + 1
        
        # Prepare statistics
        stats_data = {
            'total_parts': len(all_parts),
            'active_parts': len(active_parts),
            'inactive_parts': len(inactive_parts),
            'average_price': round(avg_price, 2),
            'min_price': min_price,
            'max_price': max_price,
            'categories': len(categories),
            'top_category': max(categories.items(), key=lambda x: x[1])[0] if categories else 'None'
        }
        
        # Display statistics
        if format == 'table':
            title = f"Parts Statistics{' - ' + category if category else ''}"
            display_summary(title, stats_data)
            
            if categories:
                click.echo("\nCategory Breakdown:")
                click.echo("-" * 30)
                for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                    click.echo(f"  {cat}: {count} parts")
        
        elif format == 'json':
            stats_data['category_breakdown'] = categories
            click.echo(format_json(stats_data))
        
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to get parts statistics")
        raise CLIError(f"Failed to get parts statistics: {e}")


# Import bulk operations from separate module
from cli.commands.bulk_operations import bulk_update, bulk_delete, bulk_activate


# Add bulk operations to the parts group
parts_group.add_command(bulk_update)
parts_group.add_command(bulk_delete)
parts_group.add_command(bulk_activate)


def _load_column_mapping(mapping_file: Path) -> Dict[str, str]:
    """
    Load column mapping from CSV file.
    
    Expected format: source_column,target_column
    Example: item_code,part_number
    """
    mapping = {}
    try:
        with open(mapping_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if 'source_column' not in reader.fieldnames or 'target_column' not in reader.fieldnames:
                raise CLIError("Mapping file must have 'source_column' and 'target_column' columns")
            
            for row in reader:
                source = row['source_column'].strip()
                target = row['target_column'].strip()
                if source and target:
                    mapping[source] = target
        
        logger.info(f"Loaded {len(mapping)} column mappings")
        return mapping
    except Exception as e:
        raise CLIError(f"Failed to load column mapping: {e}")


def _apply_data_transformations(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply common data transformations to imported data."""
    transformed = data.copy()
    
    # Transform part number to uppercase
    if 'part_number' in transformed and transformed['part_number']:
        transformed['part_number'] = str(transformed['part_number']).strip().upper()
    
    # Clean and normalize price
    if 'authorized_price' in transformed and transformed['authorized_price']:
        price_str = str(transformed['authorized_price']).strip()
        # Remove currency symbols
        price_str = price_str.replace('$', '').replace(',', '')
        try:
            transformed['authorized_price'] = Decimal(price_str)
        except (ValueError, TypeError):
            pass  # Keep original value if transformation fails
    
    # Clean text fields
    for field in ['description', 'category', 'notes']:
        if field in transformed and transformed[field]:
            transformed[field] = str(transformed[field]).strip() or None
    
    return transformed


def _read_parts_csv(file_path: Path, column_mapping: Optional[Dict[str, str]] = None,
                   transform_data: bool = False) -> List[Dict[str, Any]]:
    """Read and parse parts data from CSV file with optional mapping and transformations."""
    parts_data = []
    
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Apply column mapping if provided
        if column_mapping:
            # Remap column names
            mapped_fieldnames = []
            for field in reader.fieldnames:
                mapped_field = column_mapping.get(field, field)
                mapped_fieldnames.append(mapped_field)
            
            # Create new reader with mapped columns
            f.seek(0)  # Reset file position
            raw_reader = csv.reader(f)
            next(raw_reader)  # Skip header
            reader = csv.DictReader(f, fieldnames=mapped_fieldnames)
        
        required_columns = ['part_number', 'authorized_price']
        available_columns = reader.fieldnames or []
        
        if not all(col in available_columns for col in required_columns):
            missing = [col for col in required_columns if col not in available_columns]
            raise CLIError(f"CSV file must contain columns: {', '.join(missing)}")
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
            try:
                part_data = {
                    'part_number': row['part_number'].strip().upper() if row.get('part_number') else '',
                    'authorized_price': Decimal(row['authorized_price'].strip()) if row.get('authorized_price') else Decimal('0'),
                    'description': row.get('description', '').strip() or None,
                    'category': row.get('category', '').strip() or None,
                    'notes': row.get('notes', '').strip() or None
                }
                
                # Apply transformations if requested
                if transform_data:
                    part_data = _apply_data_transformations(part_data)
                
                # Basic data validation
                if not part_data['part_number']:
                    print_warning(f"Row {row_num}: Empty part number, skipping")
                    continue
                
                if part_data['authorized_price'] <= 0:
                    print_warning(f"Row {row_num}: Invalid price, skipping")
                    continue
                
                parts_data.append(part_data)
                
            except (ValueError, KeyError) as e:
                print_warning(f"Row {row_num}: Invalid data ({e}), skipping")
                continue
    
    return parts_data


def _validate_parts_data(parts_data: List[Dict[str, Any]]) -> None:
    """Validate parts data before import using centralized validation helpers."""
    # Use the new validation helper for batch validation
    validation_result = ValidationHelper.validate_parts_data_batch(parts_data)
    
    if validation_result.has_errors:
        # Print detailed validation summary
        ValidationHelper.print_validation_summary(validation_result, "Parts Data Validation")
        
        # Format and display errors
        error_message = ValidationHelper.format_validation_errors(
            validation_result.invalid_items,
            show_suggestions=True,
            max_errors_displayed=5
        )
        raise CLIError(f"Parts data validation failed:\n{error_message}")
    
    if validation_result.has_warnings:
        print_warning("Parts data validation completed with warnings:")
        for warning in validation_result.warnings:
            print_warning(f"  • {warning}")


def _import_parts_batch(parts_data: List[Dict[str, Any]], db_manager,
                       update_existing: bool, batch_size: int, skip_duplicates: bool = False) -> Dict[str, Any]:
    """Import parts in batches with progress tracking."""
    results = {
        'total_parts': len(parts_data),
        'imported': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    for i, part_data, progress in show_import_progress(parts_data, "Importing parts"):
        try:
            # Create part object
            part = Part(
                part_number=part_data['part_number'],
                authorized_price=part_data['authorized_price'],
                description=part_data['description'],
                category=part_data['category'],
                source='imported',
                notes=part_data['notes']
            )
            
            # Try to create or update part
            try:
                db_manager.create_part(part)
                results['imported'] += 1
            except DatabaseError as e:
                if "already exists" in str(e):
                    if update_existing:
                        # Update existing part
                        existing_part = db_manager.get_part(part.part_number)
                        existing_part.authorized_price = part.authorized_price
                        existing_part.description = part.description
                        existing_part.category = part.category
                        existing_part.notes = part.notes
                        db_manager.update_part(existing_part)
                        results['updated'] += 1
                    elif skip_duplicates:
                        # Skip without error
                        results['skipped'] += 1
                    else:
                        # Default behavior - count as skipped but log warning
                        print_warning(f"Part {part.part_number} already exists, skipping")
                        results['skipped'] += 1
                else:
                    raise
            
        except Exception as e:
            logger.warning(f"Failed to import part {part_data['part_number']}: {e}")
            results['errors'] += 1
    
    return results