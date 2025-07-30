"""
Bulk operations for parts management.

This module provides comprehensive bulk operations for parts including:
- Bulk update operations
- Bulk delete/deactivate operations  
- Bulk activate operations
- Advanced CSV processing with transformations
"""

import csv
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from decimal import Decimal

import click

from cli.context import pass_context
from cli.validators import PART_NUMBER, PRICE
from cli.formatters import (
    print_success, print_warning, print_error, print_info,
    display_summary
)
from cli.progress import show_import_progress
from cli.prompts import prompt_for_confirmation
from cli.exceptions import CLIError
from cli.error_handlers import error_handler
from database.models import Part, PartNotFoundError, DatabaseError


logger = logging.getLogger(__name__)


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
        if field in transformed:
            if transformed[field]:
                cleaned = str(transformed[field]).strip()
                transformed[field] = cleaned if cleaned else None
            else:
                transformed[field] = None
    
    return transformed


def _read_bulk_update_csv(file_path: Path, fields: List[str]) -> List[Dict[str, Any]]:
    """Read bulk update data from CSV file."""
    update_data = []
    
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        if 'part_number' not in reader.fieldnames:
            raise CLIError("CSV file must contain 'part_number' column")
        
        # Check that at least one update field is present
        available_fields = [field for field in fields if field in reader.fieldnames]
        if not available_fields:
            raise CLIError(f"CSV file must contain at least one of: {', '.join(fields)}")
        
        for row_num, row in enumerate(reader, start=2):
            try:
                part_number = row['part_number'].strip().upper()
                if not part_number:
                    print_warning(f"Row {row_num}: Empty part number, skipping")
                    continue
                
                update_item = {'part_number': part_number}
                
                # Extract update fields
                for field in available_fields:
                    value = row.get(field, '').strip()
                    if value:  # Only include non-empty values
                        if field == 'price':
                            try:
                                update_item['authorized_price'] = Decimal(value)
                            except ValueError:
                                print_warning(f"Row {row_num}: Invalid price '{value}', skipping field")
                        else:
                            update_item[field] = value
                
                if len(update_item) > 1:  # Has fields beyond part_number
                    update_data.append(update_item)
                
            except Exception as e:
                print_warning(f"Row {row_num}: Error processing row ({e}), skipping")
                continue
    
    return update_data


def _read_part_numbers_csv(file_path: Path) -> List[str]:
    """Read part numbers from CSV file."""
    part_numbers = []
    
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        if 'part_number' not in reader.fieldnames:
            raise CLIError("CSV file must contain 'part_number' column")
        
        for row_num, row in enumerate(reader, start=2):
            try:
                part_number = row['part_number'].strip().upper()
                if part_number:
                    part_numbers.append(part_number)
                else:
                    print_warning(f"Row {row_num}: Empty part number, skipping")
                    
            except Exception as e:
                print_warning(f"Row {row_num}: Error processing row ({e}), skipping")
                continue
    
    return part_numbers


def _preview_bulk_updates(update_data: List[Dict[str, Any]], fields: List[str]) -> None:
    """Preview what would be updated in bulk update operation."""
    print_info("Preview of bulk updates:")
    
    # Show first few items as examples
    preview_count = min(5, len(update_data))
    for i, item in enumerate(update_data[:preview_count]):
        print_info(f"  {item['part_number']}: {', '.join(f'{k}={v}' for k, v in item.items() if k != 'part_number')}")
    
    if len(update_data) > preview_count:
        print_info(f"  ... and {len(update_data) - preview_count} more parts")


def _preview_bulk_delete(part_numbers: List[str], soft_delete: bool) -> None:
    """Preview what would be deleted in bulk delete operation."""
    action = "deactivated" if soft_delete else "permanently deleted"
    print_info(f"Preview of parts to be {action}:")
    
    # Show first few items as examples
    preview_count = min(10, len(part_numbers))
    for part_number in part_numbers[:preview_count]:
        print_info(f"  {part_number}")
    
    if len(part_numbers) > preview_count:
        print_info(f"  ... and {len(part_numbers) - preview_count} more parts")


def _preview_bulk_activate(part_numbers: List[str]) -> None:
    """Preview what would be activated in bulk activate operation."""
    print_info("Preview of parts to be activated:")
    
    # Show first few items as examples
    preview_count = min(10, len(part_numbers))
    for part_number in part_numbers[:preview_count]:
        print_info(f"  {part_number}")
    
    if len(part_numbers) > preview_count:
        print_info(f"  ... and {len(part_numbers) - preview_count} more parts")


def _perform_bulk_update(update_data: List[Dict[str, Any]], db_manager, fields: List[str],
                        filter_category: Optional[str], batch_size: int) -> Dict[str, Any]:
    """Perform bulk update operation."""
    results = {
        'total_parts': len(update_data),
        'updated': 0,
        'not_found': 0,
        'errors': 0,
        'filtered_out': 0
    }
    
    for i, update_item, progress in show_import_progress(update_data, "Updating parts"):
        try:
            part_number = update_item['part_number']
            
            # Get existing part
            try:
                part = db_manager.get_part(part_number)
            except PartNotFoundError:
                results['not_found'] += 1
                print_warning(f"Part {part_number} not found, skipping")
                continue
            
            # Apply category filter if specified
            if filter_category and part.category != filter_category:
                results['filtered_out'] += 1
                continue
            
            # Update fields
            updated = False
            for field, value in update_item.items():
                if field == 'part_number':
                    continue
                
                if field == 'authorized_price':
                    part.authorized_price = value
                    updated = True
                elif field == 'description':
                    part.description = value
                    updated = True
                elif field == 'category':
                    part.category = value
                    updated = True
                elif field == 'notes':
                    part.notes = value
                    updated = True
                elif field == 'status':
                    part.is_active = value.lower() in ('true', '1', 'active', 'yes')
                    updated = True
            
            if updated:
                db_manager.update_part(part)
                results['updated'] += 1
            
        except Exception as e:
            logger.warning(f"Failed to update part {update_item['part_number']}: {e}")
            results['errors'] += 1
    
    return results


def _perform_bulk_delete(part_numbers: List[str], db_manager, soft_delete: bool,
                        filter_category: Optional[str], batch_size: int) -> Dict[str, Any]:
    """Perform bulk delete operation."""
    results = {
        'total_parts': len(part_numbers),
        'deleted': 0,
        'not_found': 0,
        'errors': 0,
        'filtered_out': 0
    }
    
    for i, part_number, progress in show_import_progress(part_numbers, "Deleting parts"):
        try:
            # Check if part exists and apply filter
            if filter_category:
                try:
                    part = db_manager.get_part(part_number)
                    if part.category != filter_category:
                        results['filtered_out'] += 1
                        continue
                except PartNotFoundError:
                    results['not_found'] += 1
                    continue
            
            # Delete part
            try:
                db_manager.delete_part(part_number, soft_delete=soft_delete)
                results['deleted'] += 1
            except PartNotFoundError:
                results['not_found'] += 1
                print_warning(f"Part {part_number} not found, skipping")
            
        except Exception as e:
            logger.warning(f"Failed to delete part {part_number}: {e}")
            results['errors'] += 1
    
    return results


def _perform_bulk_activate(part_numbers: List[str], db_manager, filter_category: Optional[str],
                          batch_size: int) -> Dict[str, Any]:
    """Perform bulk activate operation."""
    results = {
        'total_parts': len(part_numbers),
        'activated': 0,
        'not_found': 0,
        'errors': 0,
        'filtered_out': 0,
        'already_active': 0
    }
    
    for i, part_number, progress in show_import_progress(part_numbers, "Activating parts"):
        try:
            # Get existing part
            try:
                part = db_manager.get_part(part_number)
            except PartNotFoundError:
                results['not_found'] += 1
                print_warning(f"Part {part_number} not found, skipping")
                continue
            
            # Apply category filter if specified
            if filter_category and part.category != filter_category:
                results['filtered_out'] += 1
                continue
            
            # Check if already active
            if part.is_active:
                results['already_active'] += 1
                continue
            
            # Activate part
            part.is_active = True
            db_manager.update_part(part)
            results['activated'] += 1
            
        except Exception as e:
            logger.warning(f"Failed to activate part {part_number}: {e}")
            results['errors'] += 1
    
    return results


# Command definitions
@click.command(name='bulk-update')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--field', '-f', type=click.Choice(['price', 'description', 'category', 'notes', 'status']),
              multiple=True, help='Fields to update (can specify multiple)')
@click.option('--filter-category', type=str, help='Only update parts in this category')
@click.option('--dry-run', is_flag=True, help='Show what would be updated without making changes')
@click.option('--batch-size', type=int, default=50, help='Process in batches')
@pass_context
@error_handler({'operation': 'bulk_update', 'command': 'parts bulk-update'})
def bulk_update(ctx, input_file, field, filter_category, dry_run, batch_size):
    """
    Bulk update parts from a CSV file.
    
    CSV should contain part_number column and columns for fields to update.
    Only specified fields will be updated.
    
    Examples:
        # Update prices only
        invoice-checker parts bulk-update updates.csv --field price
        
        # Update multiple fields
        invoice-checker parts bulk-update updates.csv --field price --field description
        
        # Dry run to see what would be updated
        invoice-checker parts bulk-update updates.csv --field price --dry-run
    """
    try:
        input_path = Path(input_file)
        
        if not field:
            raise CLIError("At least one field must be specified with --field option")
        
        # Read update data
        update_data = _read_bulk_update_csv(input_path, list(field))
        
        if not update_data:
            raise CLIError("No valid update data found in CSV file")
        
        print_info(f"Found {len(update_data)} parts to update")
        
        if dry_run:
            print_info("Dry run mode - no changes will be made")
            _preview_bulk_updates(update_data, list(field))
            return
        
        # Confirm bulk update
        if not prompt_for_confirmation(
            f"Update {len(update_data)} parts with fields: {', '.join(field)}?",
            default=True
        ):
            print_info("Bulk update cancelled.")
            return
        
        # Perform bulk update
        db_manager = ctx.get_db_manager()
        results = _perform_bulk_update(
            update_data, db_manager, list(field), filter_category, batch_size
        )
        
        # Display results
        display_summary("Bulk Update Results", results)
        print_success("Bulk update completed!")
        
    except Exception as e:
        logger.exception("Failed to perform bulk update")
        raise CLIError(f"Failed to perform bulk update: {e}")


@click.command(name='bulk-delete')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--soft', is_flag=True, default=True, help='Soft delete (deactivate)')
@click.option('--hard', is_flag=True, help='Permanently delete from database')
@click.option('--filter-category', type=str, help='Only delete parts in this category')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without making changes')
@click.option('--batch-size', type=int, default=50, help='Process in batches')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@pass_context
@error_handler({'operation': 'bulk_delete', 'command': 'parts bulk-delete'})
def bulk_delete(ctx, input_file, soft, hard, filter_category, dry_run, batch_size, force):
    """
    Bulk delete or deactivate parts from a CSV file.
    
    CSV should contain a part_number column with parts to delete.
    
    Examples:
        # Soft delete (deactivate) parts
        invoice-checker parts bulk-delete parts_to_delete.csv
        
        # Permanently delete parts
        invoice-checker parts bulk-delete parts_to_delete.csv --hard
        
        # Dry run to see what would be deleted
        invoice-checker parts bulk-delete parts_to_delete.csv --dry-run
    """
    try:
        if soft and hard:
            raise CLIError("Cannot specify both --soft and --hard options")
        
        # Default to soft delete
        soft_delete = not hard
        
        input_path = Path(input_file)
        
        # Read part numbers to delete
        part_numbers = _read_part_numbers_csv(input_path)
        
        if not part_numbers:
            raise CLIError("No valid part numbers found in CSV file")
        
        print_info(f"Found {len(part_numbers)} parts to {'deactivate' if soft_delete else 'delete'}")
        
        if dry_run:
            print_info("Dry run mode - no changes will be made")
            _preview_bulk_delete(part_numbers, soft_delete)
            return
        
        # Confirm bulk delete
        if not force:
            action = "deactivate" if soft_delete else "permanently delete"
            if not prompt_for_confirmation(
                f"Are you sure you want to {action} {len(part_numbers)} parts?",
                default=False
            ):
                print_info("Bulk delete cancelled.")
                return
        
        # Perform bulk delete
        db_manager = ctx.get_db_manager()
        results = _perform_bulk_delete(
            part_numbers, db_manager, soft_delete, filter_category, batch_size
        )
        
        # Display results
        display_summary("Bulk Delete Results", results)
        action = "deactivated" if soft_delete else "deleted"
        print_success(f"Bulk {action} completed!")
        
    except Exception as e:
        logger.exception("Failed to perform bulk delete")
        raise CLIError(f"Failed to perform bulk delete: {e}")


@click.command(name='bulk-activate')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--filter-category', type=str, help='Only activate parts in this category')
@click.option('--dry-run', is_flag=True, help='Show what would be activated without making changes')
@click.option('--batch-size', type=int, default=50, help='Process in batches')
@pass_context
@error_handler({'operation': 'bulk_activate', 'command': 'parts bulk-activate'})
def bulk_activate(ctx, input_file, filter_category, dry_run, batch_size):
    """
    Bulk activate (reactivate) parts from a CSV file.
    
    CSV should contain a part_number column with parts to activate.
    
    Examples:
        # Activate parts
        invoice-checker parts bulk-activate parts_to_activate.csv
        
        # Dry run to see what would be activated
        invoice-checker parts bulk-activate parts_to_activate.csv --dry-run
    """
    try:
        input_path = Path(input_file)
        
        # Read part numbers to activate
        part_numbers = _read_part_numbers_csv(input_path)
        
        if not part_numbers:
            raise CLIError("No valid part numbers found in CSV file")
        
        print_info(f"Found {len(part_numbers)} parts to activate")
        
        if dry_run:
            print_info("Dry run mode - no changes will be made")
            _preview_bulk_activate(part_numbers)
            return
        
        # Confirm bulk activate
        if not prompt_for_confirmation(
            f"Activate {len(part_numbers)} parts?",
            default=True
        ):
            print_info("Bulk activate cancelled.")
            return
        
        # Perform bulk activate
        db_manager = ctx.get_db_manager()
        results = _perform_bulk_activate(
            part_numbers, db_manager, filter_category, batch_size
        )
        
        # Display results
        display_summary("Bulk Activate Results", results)
        print_success("Bulk activate completed!")
        
    except Exception as e:
        logger.exception("Failed to perform bulk activate")
        raise CLIError(f"Failed to perform bulk activate: {e}")