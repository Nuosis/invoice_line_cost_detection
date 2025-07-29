"""
Database utilities and helper functions for the Invoice Rate Detection System.

This module provides additional utility functions for database operations,
maintenance tasks, and data import/export functionality.
"""

import csv
import json
import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

from database import DatabaseManager
from database.models import Part, Configuration, PartDiscoveryLog, ValidationError, DatabaseError

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseUtils:
    """
    Utility class providing additional database operations and maintenance functions.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize database utilities.
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
    
    # Data Import/Export Functions
    
    def export_parts_to_csv(self, output_path: str, active_only: bool = True) -> int:
        """
        Export parts data to CSV file.
        
        Args:
            output_path: Path to output CSV file
            active_only: If True, only export active parts
            
        Returns:
            int: Number of parts exported
            
        Raises:
            DatabaseError: If export operation fails
        """
        try:
            parts = self.db_manager.list_parts(active_only=active_only)
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'part_number', 'authorized_price', 'description', 'category',
                    'source', 'first_seen_invoice', 'created_date', 'last_updated',
                    'is_active', 'notes'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for part in parts:
                    part_dict = part.to_dict()
                    writer.writerow(part_dict)
            
            logger.info(f"Exported {len(parts)} parts to {output_path}")
            return len(parts)
            
        except Exception as e:
            logger.error(f"Failed to export parts to CSV: {e}")
            raise DatabaseError(f"Failed to export parts: {e}")
    
    def import_parts_from_csv(self, input_path: str, update_existing: bool = False,
                             dry_run: bool = False) -> Tuple[int, int, List[str]]:
        """
        Import parts data from CSV file.
        
        Args:
            input_path: Path to input CSV file
            update_existing: If True, update existing parts; if False, skip duplicates
            dry_run: If True, validate data but don't make changes
            
        Returns:
            Tuple[int, int, List[str]]: (created_count, updated_count, errors)
            
        Raises:
            DatabaseError: If import operation fails
        """
        try:
            if not Path(input_path).exists():
                raise DatabaseError(f"Input file not found: {input_path}")
            
            created_count = 0
            updated_count = 0
            errors = []
            
            with open(input_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                    try:
                        # Convert string values to appropriate types
                        part_data = {
                            'part_number': row['part_number'].strip(),
                            'authorized_price': Decimal(row['authorized_price']),
                            'description': row.get('description', '').strip() or None,
                            'category': row.get('category', '').strip() or None,
                            'source': row.get('source', 'imported').strip(),
                            'first_seen_invoice': row.get('first_seen_invoice', '').strip() or None,
                            'is_active': row.get('is_active', 'True').lower() in ('true', '1', 'yes'),
                            'notes': row.get('notes', '').strip() or None
                        }
                        
                        # Create Part instance for validation
                        part = Part(**part_data)
                        
                        if dry_run:
                            # Just validate, don't create
                            part.validate()
                            created_count += 1
                            continue
                        
                        # Try to create or update part
                        try:
                            self.db_manager.create_part(part)
                            created_count += 1
                            logger.debug(f"Created part: {part.part_number}")
                            
                        except ValidationError as e:
                            if "already exists" in str(e) and update_existing:
                                # Update existing part
                                existing_part = self.db_manager.get_part(part.part_number)
                                
                                # Update fields
                                existing_part.authorized_price = part.authorized_price
                                existing_part.description = part.description
                                existing_part.category = part.category
                                existing_part.notes = part.notes
                                
                                self.db_manager.update_part(existing_part)
                                updated_count += 1
                                logger.debug(f"Updated part: {part.part_number}")
                            else:
                                errors.append(f"Row {row_num}: {e}")
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {e}")
            
            if not dry_run:
                logger.info(f"Import completed: {created_count} created, {updated_count} updated, {len(errors)} errors")
            else:
                logger.info(f"Dry run completed: {created_count} valid rows, {len(errors)} errors")
            
            return created_count, updated_count, errors
            
        except Exception as e:
            logger.error(f"Failed to import parts from CSV: {e}")
            raise DatabaseError(f"Failed to import parts: {e}")
    
    def export_config_to_json(self, output_path: str, category: Optional[str] = None) -> int:
        """
        Export configuration settings to JSON file.
        
        Args:
            output_path: Path to output JSON file
            category: Optional category filter
            
        Returns:
            int: Number of configurations exported
            
        Raises:
            DatabaseError: If export operation fails
        """
        try:
            configs = self.db_manager.list_config(category=category)
            
            # Convert to dictionary with typed values
            config_dict = {}
            for config in configs:
                config_dict[config.key] = {
                    'value': config.get_typed_value(),
                    'data_type': config.data_type,
                    'description': config.description,
                    'category': config.category
                }
            
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(config_dict, jsonfile, indent=2, default=str)
            
            logger.info(f"Exported {len(configs)} configurations to {output_path}")
            return len(configs)
            
        except Exception as e:
            logger.error(f"Failed to export config to JSON: {e}")
            raise DatabaseError(f"Failed to export config: {e}")
    
    def import_config_from_json(self, input_path: str, update_existing: bool = True,
                               dry_run: bool = False) -> Tuple[int, int, List[str]]:
        """
        Import configuration settings from JSON file.
        
        Args:
            input_path: Path to input JSON file
            update_existing: If True, update existing configs; if False, skip duplicates
            dry_run: If True, validate data but don't make changes
            
        Returns:
            Tuple[int, int, List[str]]: (created_count, updated_count, errors)
            
        Raises:
            DatabaseError: If import operation fails
        """
        try:
            if not Path(input_path).exists():
                raise DatabaseError(f"Input file not found: {input_path}")
            
            created_count = 0
            updated_count = 0
            errors = []
            
            with open(input_path, 'r', encoding='utf-8') as jsonfile:
                config_data = json.load(jsonfile)
            
            for key, data in config_data.items():
                try:
                    if isinstance(data, dict):
                        # New format with metadata
                        value = data['value']
                        data_type = data.get('data_type', 'string')
                        description = data.get('description')
                        category = data.get('category', 'general')
                    else:
                        # Simple format - just value
                        value = data
                        data_type = 'string'
                        description = None
                        category = 'general'
                    
                    if dry_run:
                        # Just validate
                        config = Configuration(
                            key=key,
                            value=str(value),
                            data_type=data_type,
                            description=description,
                            category=category
                        )
                        config.validate()
                        created_count += 1
                        continue
                    
                    # Set configuration value
                    self.db_manager.set_config_value(
                        key=key,
                        value=value,
                        data_type=data_type,
                        description=description,
                        category=category
                    )
                    
                    # Check if it was created or updated
                    try:
                        existing_config = self.db_manager.get_config(key)
                        if existing_config.created_date == existing_config.last_updated:
                            created_count += 1
                        else:
                            updated_count += 1
                    except:
                        created_count += 1
                    
                except Exception as e:
                    errors.append(f"Key '{key}': {e}")
            
            if not dry_run:
                logger.info(f"Config import completed: {created_count} created, {updated_count} updated, {len(errors)} errors")
            else:
                logger.info(f"Config dry run completed: {created_count} valid entries, {len(errors)} errors")
            
            return created_count, updated_count, errors
            
        except Exception as e:
            logger.error(f"Failed to import config from JSON: {e}")
            raise DatabaseError(f"Failed to import config: {e}")
    
    # Data Analysis Functions
    
    def get_parts_by_price_range(self, min_price: Optional[Decimal] = None,
                                 max_price: Optional[Decimal] = None,
                                 active_only: bool = True) -> List[Part]:
        """
        Get parts within a specific price range.
        
        Args:
            min_price: Minimum authorized price (inclusive)
            max_price: Maximum authorized price (inclusive)
            active_only: If True, only return active parts
            
        Returns:
            List[Part]: Parts within the specified price range
        """
        try:
            all_parts = self.db_manager.list_parts(active_only=active_only)
            
            filtered_parts = []
            for part in all_parts:
                if min_price is not None and part.authorized_price < min_price:
                    continue
                if max_price is not None and part.authorized_price > max_price:
                    continue
                filtered_parts.append(part)
            
            return filtered_parts
            
        except Exception as e:
            logger.error(f"Failed to get parts by price range: {e}")
            raise DatabaseError(f"Failed to get parts by price range: {e}")
    
    def get_parts_statistics(self) -> Dict[str, Any]:
        """
        Get statistical information about parts data.
        
        Returns:
            Dict[str, Any]: Statistics about parts
        """
        try:
            all_parts = self.db_manager.list_parts(active_only=False)
            active_parts = self.db_manager.list_parts(active_only=True)
            
            if not all_parts:
                return {
                    'total_parts': 0,
                    'active_parts': 0,
                    'inactive_parts': 0,
                    'price_statistics': {},
                    'categories': {},
                    'sources': {}
                }
            
            # Price statistics
            active_prices = [part.authorized_price for part in active_parts]
            price_stats = {}
            
            if active_prices:
                price_stats = {
                    'min_price': float(min(active_prices)),
                    'max_price': float(max(active_prices)),
                    'avg_price': float(sum(active_prices) / len(active_prices)),
                    'median_price': float(sorted(active_prices)[len(active_prices) // 2])
                }
            
            # Category distribution
            categories = {}
            for part in active_parts:
                category = part.category or 'Uncategorized'
                categories[category] = categories.get(category, 0) + 1
            
            # Source distribution
            sources = {}
            for part in all_parts:
                sources[part.source] = sources.get(part.source, 0) + 1
            
            return {
                'total_parts': len(all_parts),
                'active_parts': len(active_parts),
                'inactive_parts': len(all_parts) - len(active_parts),
                'price_statistics': price_stats,
                'categories': categories,
                'sources': sources
            }
            
        except Exception as e:
            logger.error(f"Failed to get parts statistics: {e}")
            raise DatabaseError(f"Failed to get parts statistics: {e}")
    
    def get_discovery_log_summary(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Get summary of discovery log activity.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Dict[str, Any]: Summary of discovery log activity
        """
        try:
            logs = self.db_manager.get_discovery_logs(days_back=days_back)
            
            if not logs:
                return {
                    'total_entries': 0,
                    'actions': {},
                    'sessions': 0,
                    'parts_discovered': 0,
                    'price_mismatches': 0
                }
            
            # Action distribution
            actions = {}
            for log in logs:
                actions[log.action_taken] = actions.get(log.action_taken, 0) + 1
            
            # Unique sessions
            sessions = len(set(log.processing_session_id for log in logs if log.processing_session_id))
            
            # Unique parts discovered
            parts_discovered = len(set(log.part_number for log in logs))
            
            # Price mismatches
            price_mismatches = sum(1 for log in logs if log.action_taken == 'price_mismatch')
            
            return {
                'total_entries': len(logs),
                'actions': actions,
                'sessions': sessions,
                'parts_discovered': parts_discovered,
                'price_mismatches': price_mismatches
            }
            
        except Exception as e:
            logger.error(f"Failed to get discovery log summary: {e}")
            raise DatabaseError(f"Failed to get discovery log summary: {e}")
    
    # Maintenance Functions
    
    def perform_maintenance(self, cleanup_logs: bool = True, vacuum: bool = True,
                           backup: bool = True) -> Dict[str, Any]:
        """
        Perform routine database maintenance tasks.
        
        Args:
            cleanup_logs: If True, cleanup old discovery logs
            vacuum: If True, vacuum the database
            backup: If True, create a backup
            
        Returns:
            Dict[str, Any]: Results of maintenance operations
        """
        results = {}
        
        try:
            # Cleanup old discovery logs
            if cleanup_logs:
                retention_days = int(self.db_manager.get_config_value('log_retention_days', 365))
                deleted_logs = self.db_manager.cleanup_old_discovery_logs(retention_days)
                results['logs_cleaned'] = deleted_logs
                logger.info(f"Cleaned up {deleted_logs} old discovery log entries")
            
            # Vacuum database
            if vacuum:
                self.db_manager.vacuum_database()
                results['vacuum_completed'] = True
                logger.info("Database vacuum completed")
            
            # Create backup
            if backup:
                backup_path = self.db_manager.create_backup()
                results['backup_created'] = backup_path
                logger.info(f"Backup created: {backup_path}")
            
            results['maintenance_completed'] = datetime.now().isoformat()
            return results
            
        except Exception as e:
            logger.error(f"Maintenance operation failed: {e}")
            results['error'] = str(e)
            return results
    
    def validate_data_integrity(self) -> Tuple[bool, List[str]]:
        """
        Validate data integrity across all tables.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Check for orphaned discovery log entries
            logs = self.db_manager.get_discovery_logs()
            part_numbers = {part.part_number for part in self.db_manager.list_parts(active_only=False)}
            
            orphaned_logs = []
            for log in logs:
                if log.part_number and log.part_number not in part_numbers:
                    orphaned_logs.append(log.part_number)
            
            if orphaned_logs:
                issues.append(f"Found {len(orphaned_logs)} discovery log entries with non-existent part numbers")
            
            # Check for parts with invalid prices
            invalid_price_parts = []
            for part in self.db_manager.list_parts(active_only=False):
                if part.authorized_price <= 0:
                    invalid_price_parts.append(part.part_number)
            
            if invalid_price_parts:
                issues.append(f"Found {len(invalid_price_parts)} parts with invalid prices")
            
            # Check configuration data types
            invalid_configs = []
            for config in self.db_manager.list_config():
                try:
                    config.get_typed_value()
                except Exception:
                    invalid_configs.append(config.key)
            
            if invalid_configs:
                issues.append(f"Found {len(invalid_configs)} configurations with invalid values")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Data integrity check failed: {e}")
            return False, issues
    
    # Batch Operations
    
    def batch_update_parts_category(self, part_numbers: List[str], new_category: str) -> Tuple[int, List[str]]:
        """
        Update category for multiple parts in a batch operation.
        
        Args:
            part_numbers: List of part numbers to update
            new_category: New category to assign
            
        Returns:
            Tuple[int, List[str]]: (updated_count, errors)
        """
        updated_count = 0
        errors = []
        
        try:
            for part_number in part_numbers:
                try:
                    part = self.db_manager.get_part(part_number)
                    part.category = new_category
                    self.db_manager.update_part(part)
                    updated_count += 1
                    
                except Exception as e:
                    errors.append(f"Part {part_number}: {e}")
            
            logger.info(f"Batch category update completed: {updated_count} updated, {len(errors)} errors")
            return updated_count, errors
            
        except Exception as e:
            logger.error(f"Batch category update failed: {e}")
            raise DatabaseError(f"Batch category update failed: {e}")
    
    def batch_create_discovery_logs(self, session_id: str, logs_data: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """
        Create multiple discovery log entries in a batch operation.
        
        Args:
            session_id: Processing session ID for all logs
            logs_data: List of dictionaries containing log data
            
        Returns:
            Tuple[int, List[str]]: (created_count, errors)
        """
        created_count = 0
        errors = []
        
        try:
            for i, log_data in enumerate(logs_data):
                try:
                    log_data['processing_session_id'] = session_id
                    log_entry = PartDiscoveryLog(**log_data)
                    self.db_manager.create_discovery_log(log_entry)
                    created_count += 1
                    
                except Exception as e:
                    errors.append(f"Log entry {i}: {e}")
            
            logger.info(f"Batch discovery log creation completed: {created_count} created, {len(errors)} errors")
            return created_count, errors
            
        except Exception as e:
            logger.error(f"Batch discovery log creation failed: {e}")
            raise DatabaseError(f"Batch discovery log creation failed: {e}")


# Convenience functions for common operations

def create_processing_session() -> str:
    """
    Create a new processing session ID.
    
    Returns:
        str: Unique session ID
    """
    return str(uuid.uuid4())


def format_price(price: Union[Decimal, float]) -> str:
    """
    Format a price value for display.
    
    Args:
        price: Price value to format
        
    Returns:
        str: Formatted price string
    """
    return f"${float(price):.4f}"


def validate_part_number(part_number: str) -> bool:
    """
    Validate a part number format.
    
    Args:
        part_number: Part number to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    import re
    return bool(re.match(r'^[A-Za-z0-9_\-\.]+$', part_number))


def calculate_price_difference(discovered_price: Decimal, authorized_price: Decimal) -> Decimal:
    """
    Calculate the price difference between discovered and authorized prices.
    
    Args:
        discovered_price: Price found in invoice
        authorized_price: Authorized price from database
        
    Returns:
        Decimal: Price difference (positive if overcharge)
    """
    return discovered_price - authorized_price


def is_price_mismatch(discovered_price: Decimal, authorized_price: Decimal, tolerance: float = 0.001) -> bool:
    """
    Check if there's a significant price mismatch.
    
    Args:
        discovered_price: Price found in invoice
        authorized_price: Authorized price from database
        tolerance: Tolerance for floating point comparison
        
    Returns:
        bool: True if prices don't match within tolerance
    """
    return abs(float(discovered_price - authorized_price)) > tolerance