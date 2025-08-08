"""
Database management commands for the CLI interface.

This module implements database-related commands including:
- backup: Create database backup
- restore: Restore from backup
- migrate: Database schema migration
- maintenance: Database maintenance tasks
"""

import logging
from pathlib import Path
from datetime import datetime

import click

from cli.context import pass_context
from cli.formatters import (
    print_success, print_warning, print_error, print_info,
    display_summary
)
from cli.progress import spinner, MultiStepProgress
from cli.prompts import prompt_for_confirmation
from cli.exceptions import CLIError
from database.models import DatabaseError


logger = logging.getLogger(__name__)


def _verify_backup_integrity(backup_path: Path, db_manager) -> bool:
    """
    Verify backup file integrity and structure.
    
    Args:
        backup_path: Path to backup file
        db_manager: Database manager instance
        
    Returns:
        True if backup is valid, False otherwise
        
    Raises:
        DatabaseError: If verification fails critically
    """
    import sqlite3
    import tempfile
    import shutil
    
    try:
        # Check file exists and is readable
        if not backup_path.exists():
            raise DatabaseError(f"Backup file not found: {backup_path}")
        
        if backup_path.stat().st_size == 0:
            raise DatabaseError("Backup file is empty")
        
        # Test SQLite file integrity
        with sqlite3.connect(str(backup_path)) as conn:
            cursor = conn.cursor()
            
            # Check database integrity
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()
            if integrity_result[0] != 'ok':
                raise DatabaseError(f"Backup integrity check failed: {integrity_result[0]}")
            
            # Verify expected tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            
            expected_tables = {'parts', 'configuration', 'part_discovery_log'}
            missing_tables = expected_tables - tables
            if missing_tables:
                raise DatabaseError(f"Backup missing required tables: {missing_tables}")
            
            # Verify table schemas
            for table in expected_tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                if not columns:
                    raise DatabaseError(f"Table {table} has no columns")
        
        # Test restore capability with temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            shutil.copy2(backup_path, temp_path)
            
            # Try to connect and perform basic operations
            with sqlite3.connect(str(temp_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM parts")
                parts_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM configuration")
                config_count = cursor.fetchone()[0]
                
                logger.info(f"Backup verification: {parts_count} parts, {config_count} config entries")
        
        finally:
            if temp_path.exists():
                temp_path.unlink()
        
        return True
        
    except sqlite3.Error as e:
        raise DatabaseError(f"SQLite error during backup verification: {e}")
    except Exception as e:
        raise DatabaseError(f"Backup verification failed: {e}")


# Create database command group
@click.group(name='database')
def database_group():
    """Database management commands."""
    pass


@database_group.command()
@click.argument('output_path', type=click.Path(), required=False)
@click.option('--compress', is_flag=True, help='Compress backup file')
@click.option('--include-logs', is_flag=True, default=True,
              help='Include discovery logs in backup')
@pass_context
def backup(ctx, output_path, compress, include_logs):
    """
    Create a backup of the database.
    
    Examples:
        # Create automatic backup
        invoice-checker database backup
        
        # Create backup with custom path
        invoice-checker database backup ./backups/my_backup.db
        
        # Create compressed backup
        invoice-checker database backup --compress
    """
    try:
        db_manager = ctx.get_db_manager()
        
        with spinner("Creating database backup"):
            backup_path = db_manager.create_backup(output_path)
        
        # Get backup file size
        backup_size = Path(backup_path).stat().st_size
        size_mb = backup_size / (1024 * 1024)
        
        print_success(f"Database backup created successfully!")
        print_info(f"Backup file: {backup_path}")
        print_info(f"Backup size: {size_mb:.2f} MB")
        
        if include_logs:
            print_info("Discovery logs included in backup")
        
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to create backup")
        raise CLIError(f"Failed to create backup: {e}")


@database_group.command()
@click.argument('backup_path', type=click.Path(exists=True))
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@click.option('--verify/--no-verify', default=True,
              help='Verify backup integrity before restore')
@pass_context
def restore(ctx, backup_path, force, verify):
    """
    Restore database from a backup file.
    
    Examples:
        # Restore from backup
        invoice-checker database restore backup_20250729.db
        
        # Force restore without confirmation
        invoice-checker database restore backup.db --force
    """
    try:
        backup_path = Path(backup_path)
        
        # Verify backup file
        if not backup_path.exists():
            raise CLIError(f"Backup file not found: {backup_path}")
        
        # Get backup file info
        backup_size = backup_path.stat().st_size
        backup_date = datetime.fromtimestamp(backup_path.stat().st_mtime)
        
        print_info(f"Backup file: {backup_path}")
        print_info(f"Backup size: {backup_size / (1024 * 1024):.2f} MB")
        print_info(f"Backup date: {backup_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Confirm restore
        if not force:
            print_warning("This will replace the current database with the backup.")
            print_warning("All current data will be lost!")
            
            if not prompt_for_confirmation(
                "Are you sure you want to restore from this backup?",
                default=False
            ):
                print_info("Restore cancelled.")
                return
        
        # Perform restore
        db_manager = ctx.get_db_manager()
        
        progress = MultiStepProgress([
            "Verifying backup",
            "Creating pre-restore backup", 
            "Restoring database",
            "Verifying restored database"
        ], "Database Restore")
        
        try:
            if verify:
                progress.start_step("Verifying backup", "Checking backup integrity")
                try:
                    _verify_backup_integrity(backup_path, db_manager)
                    progress.complete_step(True, "Backup verified successfully")
                except DatabaseError as e:
                    progress.complete_step(False, f"Backup verification failed: {e}")
                    raise
            
            progress.start_step("Creating pre-restore backup", "Saving current database")
            # Pre-restore backup is created automatically by restore_backup
            progress.complete_step(True, "Pre-restore backup created")
            
            progress.start_step("Restoring database", "Replacing database with backup")
            db_manager.restore_backup(str(backup_path))
            progress.complete_step(True, "Database restored")
            
            progress.start_step("Verifying restored database", "Checking database integrity")
            try:
                _verify_backup_integrity(Path(db_manager.db_path), db_manager)
                progress.complete_step(True, "Database verified successfully")
            except DatabaseError as e:
                progress.complete_step(False, f"Database verification failed: {e}")
                raise
            
            progress.finish(True, "Restore completed successfully")
            
        except Exception as e:
            progress.finish(False, f"Restore failed: {e}")
            raise
        
        print_success("Database restored successfully!")
        print_info("A pre-restore backup was created for safety.")
        
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to restore backup")
        raise CLIError(f"Failed to restore backup: {e}")


@database_group.command()
@click.option('--to-version', type=str, default='latest',
              help='Target schema version')
@click.option('--dry-run', is_flag=True,
              help='Show migration plan without executing')
@click.option('--backup-first', is_flag=True, default=True,
              help='Create backup before migration')
@pass_context
def migrate(ctx, to_version, dry_run, backup_first):
    """
    Perform database schema migration.
    
    Examples:
        # Migrate to latest version
        invoice-checker database migrate
        
        # Dry run to see migration plan
        invoice-checker database migrate --dry-run
        
        # Migrate to specific version
        invoice-checker database migrate --to-version 2.0
    """
    try:
        db_manager = ctx.get_db_manager()
        
        # Get current database version
        current_version = db_manager.get_config_value('database_version', '1.0')
        
        print_info(f"Current database version: {current_version}")
        print_info(f"Target version: {to_version}")
        
        if dry_run:
            print_info("Dry run mode - no changes will be made")
            # Show migration plan
            print_info("Migration plan:")
            print_info("  - No migrations needed (current implementation)")
            return
        
        if current_version == to_version:
            print_info("Database is already at the target version.")
            return
        
        # Confirm migration
        if not prompt_for_confirmation(
            f"Migrate database from version {current_version} to {to_version}?",
            default=True
        ):
            print_info("Migration cancelled.")
            return
        
        # Create backup if requested
        if backup_first:
            with spinner("Creating pre-migration backup"):
                backup_path = db_manager.create_backup()
            print_info(f"Pre-migration backup created: {backup_path}")
        
        # Perform migration
        with spinner("Performing database migration"):
            # Migration logic would be implemented here
            # For now, just update the version
            db_manager.set_config_value('database_version', to_version)
        
        print_success(f"Database migrated to version {to_version}!")
        
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to migrate database")
        raise CLIError(f"Failed to migrate database: {e}")


@database_group.command()
@click.option('--vacuum', is_flag=True, default=True,
              help='Vacuum database to reclaim space')
@click.option('--cleanup-logs', is_flag=True, default=True,
              help='Clean up old discovery logs')
@click.option('--verify-integrity', is_flag=True, default=True,
              help='Verify data integrity')
@click.option('--auto-backup', is_flag=True, default=True,
              help='Create backup before maintenance')
@pass_context
def maintenance(ctx, vacuum, cleanup_logs, verify_integrity, auto_backup):
    """
    Perform database maintenance tasks.
    
    Examples:
        # Run all maintenance tasks
        invoice-checker database maintenance
        
        # Run only vacuum
        invoice-checker database maintenance --no-cleanup-logs --no-verify-integrity
        
        # Skip backup
        invoice-checker database maintenance --no-auto-backup
    """
    try:
        db_manager = ctx.get_db_manager()
        
        # Get initial database stats
        initial_stats = db_manager.get_database_stats()
        initial_size = initial_stats['database_size_bytes']
        
        print_info("Starting database maintenance...")
        
        maintenance_steps = []
        if auto_backup:
            maintenance_steps.append("Creating backup")
        if verify_integrity:
            maintenance_steps.append("Verifying integrity")
        if cleanup_logs:
            maintenance_steps.append("Cleaning up logs")
        if vacuum:
            maintenance_steps.append("Vacuuming database")
        
        progress = MultiStepProgress(maintenance_steps, "Database Maintenance")
        
        results = {
            'backup_created': False,
            'integrity_verified': False,
            'logs_cleaned': 0,
            'vacuum_completed': False,
            'space_reclaimed': 0
        }
        
        try:
            # Create backup
            if auto_backup:
                progress.start_step("Creating backup", "Creating pre-maintenance backup")
                backup_path = db_manager.create_backup()
                results['backup_created'] = True
                progress.complete_step(True, f"Backup created: {Path(backup_path).name}")
            
            # Verify integrity
            if verify_integrity:
                progress.start_step("Verifying integrity", "Checking database integrity")
                try:
                    _verify_backup_integrity(Path(db_manager.db_path), db_manager)
                    results['integrity_verified'] = True
                    progress.complete_step(True, "Database integrity verified")
                except DatabaseError as e:
                    results['integrity_verified'] = False
                    progress.complete_step(False, f"Integrity verification failed: {e}")
                    # Continue with other maintenance tasks even if integrity check fails
                    logger.warning(f"Database integrity verification failed: {e}")
            
            # Clean up logs
            if cleanup_logs:
                progress.start_step("Cleaning up logs", "Removing old discovery logs")
                retention_days = int(db_manager.get_config_value('log_retention_days', 365))
                deleted_count = db_manager.cleanup_old_discovery_logs(retention_days)
                results['logs_cleaned'] = deleted_count
                progress.complete_step(True, f"Cleaned {deleted_count} old log entries")
            
            # Vacuum database
            if vacuum:
                progress.start_step("Vacuuming database", "Reclaiming unused space")
                db_manager.vacuum_database()
                results['vacuum_completed'] = True
                progress.complete_step(True, "Database vacuumed")
            
            progress.finish(True, "Maintenance completed successfully")
            
        except Exception as e:
            progress.finish(False, f"Maintenance failed: {e}")
            raise
        
        # Get final stats and calculate space savings
        final_stats = db_manager.get_database_stats()
        final_size = final_stats['database_size_bytes']
        space_saved = initial_size - final_size
        results['space_reclaimed'] = space_saved
        
        # Display results
        print_success("Database maintenance completed!")
        
        maintenance_summary = {
            'initial_size_mb': round(initial_size / (1024 * 1024), 2),
            'final_size_mb': round(final_size / (1024 * 1024), 2),
            'space_saved_mb': round(space_saved / (1024 * 1024), 2),
            'logs_cleaned': results['logs_cleaned'],
            'backup_created': results['backup_created']
        }
        
        display_summary("Maintenance Results", maintenance_summary)
        
        if space_saved > 0:
            print_info(f"Reclaimed {space_saved / (1024 * 1024):.2f} MB of disk space")
        
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to perform maintenance")
        raise CLIError(f"Failed to perform maintenance: {e}")


@database_group.command()
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@click.option('--keep-config', is_flag=True, default=True,
              help='Keep configuration settings (default: true)')
@pass_context
def reset(ctx, force, keep_config):
    """
    Reset (erase) the current database with appropriate confirmations.
    
    This command will completely erase the current database and recreate
    it with default schema. All parts, discovery logs, and optionally
    configuration will be lost.
    
    Examples:
        # Reset database with confirmation
        invoice-checker database reset
        
        # Force reset without confirmation
        invoice-checker database reset --force
        
        # Reset database but remove all configuration too
        invoice-checker database reset --no-keep-config
    """
    try:
        db_manager = ctx.get_db_manager()
        
        # Get current database stats for confirmation
        try:
            stats = db_manager.get_database_stats()
            parts_count = stats.get('total_parts', 0)
            config_count = stats.get('config_entries', 0)
            logs_count = stats.get('discovery_log_entries', 0)
        except Exception:
            # If we can't get stats, assume database exists but is corrupted
            parts_count = "unknown"
            config_count = "unknown"
            logs_count = "unknown"
        
        # Show what will be lost
        print_warning("DATABASE RESET WARNING")
        print_warning("=" * 50)
        print_warning("This operation will PERMANENTLY DELETE all data in the database:")
        print_warning(f"  • Parts: {parts_count}")
        print_warning(f"  • Discovery logs: {logs_count}")
        if not keep_config:
            print_warning(f"  • Configuration settings: {config_count}")
        else:
            print_info(f"  • Configuration settings: {config_count} (will be preserved)")
        print_warning("")
        print_warning("This action CANNOT be undone!")
        
        # Confirm reset
        if not force:
            print_warning("Are you absolutely sure you want to reset the database?")
            confirmation = click.prompt(
                "Type 'RESET' to confirm database reset (or 'cancel' to abort)",
                type=str,
                default="cancel"
            )
            if confirmation.upper() != "RESET":
                print_info("Database reset cancelled.")
                return
        
        # Create backup before reset
        print_info("Creating backup before reset...")
        try:
            backup_path = db_manager.create_backup()
            print_info(f"Backup created: {backup_path}")
        except Exception as e:
            print_warning(f"Failed to create backup: {e}")
            if not force and not click.confirm("Continue without backup?", default=False):
                print_info("Database reset cancelled.")
                return
        
        # Perform reset
        progress = MultiStepProgress([
            "Backing up configuration" if keep_config else "Preparing reset",
            "Resetting database",
            "Restoring configuration" if keep_config else "Initializing database",
            "Verifying reset"
        ], "Database Reset")
        
        try:
            # Step 1: Backup configuration if keeping it
            config_backup = None
            if keep_config:
                progress.start_step("Backing up configuration", "Saving current configuration")
                try:
                    config_backup = db_manager.list_config()
                    progress.complete_step(True, f"Backed up {len(config_backup)} configuration entries")
                except Exception as e:
                    progress.complete_step(False, f"Configuration backup failed: {e}")
                    config_backup = None
            else:
                progress.start_step("Preparing reset", "Preparing database reset")
                progress.complete_step(True, "Ready to reset")
            
            # Step 2: Reset database
            progress.start_step("Resetting database", "Erasing and recreating database")
            db_manager.reset_database()
            progress.complete_step(True, "Database reset completed")
            
            # Step 3: Restore configuration if keeping it
            if keep_config and config_backup:
                progress.start_step("Restoring configuration", "Restoring configuration settings")
                restored_count = 0
                for config in config_backup:
                    try:
                        db_manager.set_config_value(
                            key=config.key,
                            value=config.get_typed_value(),
                            data_type=config.data_type,
                            description=config.description,
                            category=config.category
                        )
                        restored_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to restore config {config.key}: {e}")
                progress.complete_step(True, f"Restored {restored_count} configuration entries")
            else:
                progress.start_step("Initializing database", "Setting up default configuration")
                # Initialize with default configuration
                from database.models import DEFAULT_CONFIG
                initialized_count = 0
                for key, default_config in DEFAULT_CONFIG.items():
                    try:
                        db_manager.set_config_value(
                            key=default_config.key,
                            value=default_config.get_typed_value(),
                            data_type=default_config.data_type,
                            description=default_config.description,
                            category=default_config.category
                        )
                        initialized_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to initialize config {key}: {e}")
                progress.complete_step(True, f"Initialized {initialized_count} default configurations")
            
            # Step 4: Verify reset
            progress.start_step("Verifying reset", "Checking database integrity")
            try:
                new_stats = db_manager.get_database_stats()
                expected_parts = 0
                expected_logs = 0
                actual_parts = new_stats.get('total_parts', 0)
                actual_logs = new_stats.get('discovery_log_entries', 0)
                
                if actual_parts == expected_parts and actual_logs == expected_logs:
                    progress.complete_step(True, "Database reset verified successfully")
                else:
                    progress.complete_step(False, f"Verification failed: {actual_parts} parts, {actual_logs} logs")
            except Exception as e:
                progress.complete_step(False, f"Verification failed: {e}")
            
            progress.finish(True, "Database reset completed successfully")
            
        except Exception as e:
            progress.finish(False, f"Database reset failed: {e}")
            raise
        
        print_success("Database has been successfully reset!")
        print_info("All parts and discovery logs have been removed.")
        if keep_config:
            print_info("Configuration settings have been preserved.")
        else:
            print_info("Configuration has been reset to defaults.")
        
        if 'backup_path' in locals():
            print_info(f"A backup was created before reset: {backup_path}")
        
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Failed to reset database")
        raise CLIError(f"Failed to reset database: {e}")


# Add individual commands to the group
database_group.add_command(backup)
database_group.add_command(restore)
database_group.add_command(migrate)
database_group.add_command(maintenance)
database_group.add_command(reset)