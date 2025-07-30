"""
End-to-End Tests for Database Management Commands

This test suite validates all database management functionality without using any mocking.
All tests create real database files, backup files, and system resources, then clean up completely.

Test Coverage:
- Database backup command (standard and compressed backups)
- Database restore command (with verification and force options)
- Database migrate command (version upgrades and dry-run)
- Database maintenance command (vacuum, cleanup, integrity checks)
- Backup verification and integrity testing
- Error handling for corrupted backups and invalid operations
- Cross-platform file handling and permissions
"""

import gzip
import os
import shutil
import sqlite3
import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any
import time

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part, Configuration, PartDiscoveryLog, DatabaseError
from database.db_migration import DatabaseMigrator
from database.db_utils import DatabaseBackupManager


class TestDatabaseManagement(unittest.TestCase):
    """
    Comprehensive e2e tests for database management functionality.
    
    These tests validate that all database management commands work correctly
    in real-world conditions without any mocking.
    """
    
    def setUp(self):
        """
        Set up test environment for each test.
        
        Creates a unique temporary directory and database file for each test
        to ensure complete isolation.
        """
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_db_mgmt_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_db_mgmt_{self.test_id}.db"
        
        # Create directories for backups and test files
        self.backup_dir = self.temp_dir / "backups"
        self.backup_dir.mkdir()
        
        # Track created resources for cleanup
        self.created_files = [self.db_path]
        self.created_dirs = [self.temp_dir, self.backup_dir]
        self.db_manager = None
        self.backup_manager = None
        
    def tearDown(self):
        """
        Clean up all resources created during the test.
        
        Ensures no test artifacts are left behind, following the strict
        cleanup requirements for e2e tests.
        """
        # Close database manager if it exists
        if self.db_manager:
            try:
                self.db_manager.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Close backup manager if it exists
        if self.backup_manager:
            try:
                self.backup_manager.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove all created files
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove backup files
        try:
            for backup_file in self.backup_dir.glob("*"):
                if backup_file.is_file():
                    backup_file.unlink()
        except Exception:
            pass
        
        # Remove all created directories
        for dir_path in reversed(self.created_dirs):  # Remove in reverse order
            try:
                if dir_path.exists():
                    dir_path.rmdir()
            except Exception:
                pass  # Ignore errors during cleanup
    
    def _setup_test_data(self):
        """Set up test data in the database for backup/restore testing."""
        # Add test parts
        test_parts = [
            Part(
                part_number="BACKUP001",
                authorized_price=Decimal("15.50"),
                description="Backup Test Part 1",
                category="Test"
            ),
            Part(
                part_number="BACKUP002",
                authorized_price=Decimal("25.75"),
                description="Backup Test Part 2",
                category="Test"
            ),
            Part(
                part_number="BACKUP003",
                authorized_price=Decimal("35.00"),
                description="Backup Test Part 3",
                category="Tools"
            )
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
        
        # Add test discovery logs
        test_logs = [
            PartDiscoveryLog(
                part_number="BACKUP001",
                action_taken="discovered",
                invoice_number="INV001",
                discovered_price=Decimal("15.50")
            ),
            PartDiscoveryLog(
                part_number="BACKUP002",
                action_taken="added",
                invoice_number="INV002",
                discovered_price=Decimal("25.75")
            )
        ]
        
        for log in test_logs:
            self.db_manager.create_discovery_log(log)
        
        # Update a configuration value
        self.db_manager.set_config_value("test_backup_config", "test_value")
    
    def test_database_backup_basic_functionality(self):
        """
        Test basic database backup functionality.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Create backup manager
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        
        # Create backup (simulates: database backup)
        backup_path = self.backup_dir / f"backup_{self.test_id}.db"
        self.created_files.append(backup_path)
        
        backup_result = self.backup_manager.create_backup(str(backup_path))
        
        # Verify backup was created successfully
        self.assertTrue(backup_result['success'])
        self.assertTrue(backup_path.exists())
        self.assertGreater(backup_path.stat().st_size, 0)
        
        # Verify backup contains expected data
        backup_db = DatabaseManager(str(backup_path))
        try:
            backup_parts = backup_db.list_parts()
            self.assertEqual(len(backup_parts), 3)
            
            backup_logs = backup_db.list_discovery_logs()
            self.assertEqual(len(backup_logs), 2)
            
            backup_config = backup_db.get_config_value("test_backup_config")
            self.assertEqual(backup_config, "test_value")
        finally:
            backup_db.close()
    
    def test_database_backup_with_custom_location(self):
        """
        Test database backup with custom location and filename.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Create backup manager
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        
        # Create backup with custom location (simulates: database backup ./backups/custom_backup.db)
        custom_backup_path = self.backup_dir / "custom_backup_name.db"
        self.created_files.append(custom_backup_path)
        
        backup_result = self.backup_manager.create_backup(str(custom_backup_path))
        
        # Verify custom backup was created
        self.assertTrue(backup_result['success'])
        self.assertTrue(custom_backup_path.exists())
        self.assertEqual(custom_backup_path.name, "custom_backup_name.db")
        
        # Verify backup metadata
        self.assertIn('backup_size', backup_result)
        self.assertIn('backup_time', backup_result)
        self.assertGreater(backup_result['backup_size'], 0)
    
    def test_database_backup_compressed(self):
        """
        Test database backup with compression.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Create backup manager
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        
        # Create compressed backup (simulates: database backup --compress)
        compressed_backup_path = self.backup_dir / f"compressed_backup_{self.test_id}.db.gz"
        self.created_files.append(compressed_backup_path)
        
        backup_result = self.backup_manager.create_backup(
            str(compressed_backup_path),
            compress=True
        )
        
        # Verify compressed backup was created
        self.assertTrue(backup_result['success'])
        self.assertTrue(compressed_backup_path.exists())
        self.assertTrue(compressed_backup_path.name.endswith('.gz'))
        
        # Verify compressed file is smaller than uncompressed
        uncompressed_backup_path = self.backup_dir / f"uncompressed_backup_{self.test_id}.db"
        self.created_files.append(uncompressed_backup_path)
        
        uncompressed_result = self.backup_manager.create_backup(str(uncompressed_backup_path))
        
        compressed_size = compressed_backup_path.stat().st_size
        uncompressed_size = uncompressed_backup_path.stat().st_size
        
        self.assertLess(compressed_size, uncompressed_size, "Compressed backup should be smaller")
        
        # Verify compressed backup can be decompressed and contains correct data
        decompressed_path = self.backup_dir / f"decompressed_{self.test_id}.db"
        self.created_files.append(decompressed_path)
        
        with gzip.open(compressed_backup_path, 'rb') as compressed_file:
            with open(decompressed_path, 'wb') as decompressed_file:
                shutil.copyfileobj(compressed_file, decompressed_file)
        
        # Verify decompressed backup contains expected data
        decompressed_db = DatabaseManager(str(decompressed_path))
        try:
            decompressed_parts = decompressed_db.list_parts()
            self.assertEqual(len(decompressed_parts), 3)
        finally:
            decompressed_db.close()
    
    def test_database_backup_with_logs_inclusion(self):
        """
        Test database backup with discovery logs inclusion.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Create backup manager
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        
        # Create backup including logs (simulates: database backup --include-logs)
        backup_with_logs_path = self.backup_dir / f"backup_with_logs_{self.test_id}.db"
        self.created_files.append(backup_with_logs_path)
        
        backup_result = self.backup_manager.create_backup(
            str(backup_with_logs_path),
            include_logs=True
        )
        
        # Verify backup was created with logs
        self.assertTrue(backup_result['success'])
        
        # Verify backup contains discovery logs
        backup_db = DatabaseManager(str(backup_with_logs_path))
        try:
            backup_logs = backup_db.list_discovery_logs()
            self.assertEqual(len(backup_logs), 2)
            
            # Verify specific log data
            log1 = next(log for log in backup_logs if log.part_number == "BACKUP001")
            self.assertEqual(log1.action_taken, "discovered")
            self.assertEqual(log1.invoice_number, "INV001")
        finally:
            backup_db.close()
        
        # Create backup without logs for comparison
        backup_no_logs_path = self.backup_dir / f"backup_no_logs_{self.test_id}.db"
        self.created_files.append(backup_no_logs_path)
        
        backup_no_logs_result = self.backup_manager.create_backup(
            str(backup_no_logs_path),
            include_logs=False
        )
        
        # Verify backup without logs is smaller
        with_logs_size = backup_with_logs_path.stat().st_size
        no_logs_size = backup_no_logs_path.stat().st_size
        
        self.assertGreaterEqual(with_logs_size, no_logs_size, 
                               "Backup with logs should be same size or larger")
    
    def test_database_restore_basic_functionality(self):
        """
        Test basic database restore functionality.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Create backup
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        backup_path = self.backup_dir / f"restore_test_backup_{self.test_id}.db"
        self.created_files.append(backup_path)
        
        backup_result = self.backup_manager.create_backup(str(backup_path))
        self.assertTrue(backup_result['success'])
        
        # Modify original database
        self.db_manager.create_part(Part(
            part_number="MODIFIED001",
            authorized_price=Decimal("99.99"),
            description="Modified Part"
        ))
        
        # Verify modification
        modified_parts = self.db_manager.list_parts()
        self.assertEqual(len(modified_parts), 4)  # 3 original + 1 modified
        
        # Close original database
        self.db_manager.close()
        
        # Restore from backup (simulates: database restore backup_file.db)
        restore_result = self.backup_manager.restore_backup(
            str(backup_path),
            str(self.db_path)
        )
        
        # Verify restore was successful
        self.assertTrue(restore_result['success'])
        
        # Reopen database and verify restoration
        self.db_manager = DatabaseManager(str(self.db_path))
        restored_parts = self.db_manager.list_parts()
        
        # Should have original 3 parts, not the modified 4
        self.assertEqual(len(restored_parts), 3)
        
        # Verify specific restored data
        restored_part_numbers = {part.part_number for part in restored_parts}
        expected_part_numbers = {"BACKUP001", "BACKUP002", "BACKUP003"}
        self.assertEqual(restored_part_numbers, expected_part_numbers)
        
        # Verify modified part is gone
        self.assertNotIn("MODIFIED001", restored_part_numbers)
    
    def test_database_restore_with_verification(self):
        """
        Test database restore with backup verification.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Create backup
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        backup_path = self.backup_dir / f"verify_restore_backup_{self.test_id}.db"
        self.created_files.append(backup_path)
        
        backup_result = self.backup_manager.create_backup(str(backup_path))
        self.assertTrue(backup_result['success'])
        
        # Close original database
        self.db_manager.close()
        
        # Restore with verification (simulates: database restore backup_file.db --verify)
        restore_result = self.backup_manager.restore_backup(
            str(backup_path),
            str(self.db_path),
            verify_backup=True
        )
        
        # Verify restore was successful with verification
        self.assertTrue(restore_result['success'])
        self.assertTrue(restore_result['backup_verified'])
        
        # Verify database integrity after restore
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test database functionality
        parts = self.db_manager.list_parts()
        self.assertEqual(len(parts), 3)
        
        # Test that we can add new data (database is functional)
        new_part = Part(
            part_number="POST_RESTORE001",
            authorized_price=Decimal("50.00"),
            description="Post Restore Test"
        )
        self.db_manager.create_part(new_part)
        
        updated_parts = self.db_manager.list_parts()
        self.assertEqual(len(updated_parts), 4)
    
    def test_database_restore_force_without_confirmation(self):
        """
        Test database restore with force option (no confirmation).
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Create backup
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        backup_path = self.backup_dir / f"force_restore_backup_{self.test_id}.db"
        self.created_files.append(backup_path)
        
        backup_result = self.backup_manager.create_backup(str(backup_path))
        self.assertTrue(backup_result['success'])
        
        # Modify database significantly
        for i in range(10):
            self.db_manager.create_part(Part(
                part_number=f"BULK{i:03d}",
                authorized_price=Decimal(f"{i * 10}.00"),
                description=f"Bulk Part {i}"
            ))
        
        # Verify significant changes
        modified_parts = self.db_manager.list_parts()
        self.assertEqual(len(modified_parts), 13)  # 3 original + 10 bulk
        
        # Close database
        self.db_manager.close()
        
        # Force restore without confirmation (simulates: database restore backup_file.db --force)
        restore_result = self.backup_manager.restore_backup(
            str(backup_path),
            str(self.db_path),
            force=True
        )
        
        # Verify force restore was successful
        self.assertTrue(restore_result['success'])
        self.assertTrue(restore_result['forced'])
        
        # Verify restoration overwrote all changes
        self.db_manager = DatabaseManager(str(self.db_path))
        restored_parts = self.db_manager.list_parts()
        self.assertEqual(len(restored_parts), 3)  # Back to original 3 parts
    
    def test_database_migrate_dry_run(self):
        """
        Test database migration dry-run functionality.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create database migrator
        migrator = DatabaseMigrator(self.db_manager)
        
        # Test dry-run migration (simulates: database migrate --dry-run)
        dry_run_result = migrator.migrate_database(dry_run=True)
        
        # Verify dry-run results
        self.assertIsInstance(dry_run_result, dict)
        self.assertIn('current_version', dry_run_result)
        self.assertIn('target_version', dry_run_result)
        self.assertIn('migrations_needed', dry_run_result)
        self.assertIn('dry_run', dry_run_result)
        self.assertTrue(dry_run_result['dry_run'])
        
        # Verify database was not actually modified
        original_stats = self.db_manager.get_database_stats()
        self.assertEqual(original_stats['database_version'], '1.0')
    
    def test_database_migrate_to_specific_version(self):
        """
        Test database migration to a specific version.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Get current version
        current_version = self.db_manager.get_config_value('database_version')
        self.assertEqual(current_version, '1.0')
        
        # Create database migrator
        migrator = DatabaseMigrator(self.db_manager)
        
        # Test migration to specific version (simulates: database migrate --to-version 1.1)
        # Note: This test assumes migration logic exists for version 1.1
        migration_result = migrator.migrate_database(target_version='1.1')
        
        # Verify migration results
        if migration_result['migrations_applied'] > 0:
            # If migrations were applied, verify version was updated
            updated_version = self.db_manager.get_config_value('database_version')
            self.assertEqual(updated_version, '1.1')
        else:
            # If no migrations needed, version should remain the same
            self.assertEqual(migration_result['current_version'], '1.0')
    
    def test_database_migrate_with_backup_first(self):
        """
        Test database migration with automatic backup creation.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Create database migrator
        migrator = DatabaseMigrator(self.db_manager)
        
        # Test migration with backup (simulates: database migrate --backup-first)
        migration_result = migrator.migrate_database(
            backup_first=True,
            backup_dir=str(self.backup_dir)
        )
        
        # Verify migration results
        self.assertIsInstance(migration_result, dict)
        self.assertIn('backup_created', migration_result)
        
        if migration_result['backup_created']:
            # Verify backup file was created
            backup_files = list(self.backup_dir.glob("pre_migration_backup_*.db"))
            self.assertGreater(len(backup_files), 0, "Pre-migration backup should be created")
            
            # Add backup file to cleanup list
            for backup_file in backup_files:
                self.created_files.append(backup_file)
            
            # Verify backup contains original data
            backup_db = DatabaseManager(str(backup_files[0]))
            try:
                backup_parts = backup_db.list_parts()
                self.assertEqual(len(backup_parts), 3)
            finally:
                backup_db.close()
    
    def test_database_maintenance_basic_functionality(self):
        """
        Test basic database maintenance functionality.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Get initial database size
        initial_stats = self.db_manager.get_database_stats()
        initial_size = initial_stats['database_size_bytes']
        
        # Run basic maintenance (simulates: database maintenance)
        maintenance_result = self.db_manager.run_maintenance()
        
        # Verify maintenance results
        self.assertTrue(maintenance_result['success'])
        self.assertIn('operations_performed', maintenance_result)
        self.assertIn('vacuum_performed', maintenance_result)
        self.assertIn('integrity_check_passed', maintenance_result)
        
        # Verify database is still functional after maintenance
        post_maintenance_parts = self.db_manager.list_parts()
        self.assertEqual(len(post_maintenance_parts), 3)
        
        # Verify database integrity
        self.assertTrue(maintenance_result['integrity_check_passed'])
    
    def test_database_maintenance_vacuum_operation(self):
        """
        Test database maintenance vacuum operation.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Add and then delete many parts to create fragmentation
        bulk_parts = []
        for i in range(50):
            part = Part(
                part_number=f"TEMP{i:03d}",
                authorized_price=Decimal(f"{i}.00"),
                description=f"Temporary Part {i}"
            )
            self.db_manager.create_part(part)
            bulk_parts.append(part.part_number)
        
        # Delete all temporary parts to create fragmentation
        for part_number in bulk_parts:
            self.db_manager.delete_part(part_number, soft_delete=False)
        
        # Get database size before vacuum
        pre_vacuum_stats = self.db_manager.get_database_stats()
        pre_vacuum_size = pre_vacuum_stats['database_size_bytes']
        
        # Run maintenance with vacuum (simulates: database maintenance --vacuum)
        maintenance_result = self.db_manager.run_maintenance(vacuum=True)
        
        # Verify vacuum was performed
        self.assertTrue(maintenance_result['success'])
        self.assertTrue(maintenance_result['vacuum_performed'])
        
        # Get database size after vacuum
        post_vacuum_stats = self.db_manager.get_database_stats()
        post_vacuum_size = post_vacuum_stats['database_size_bytes']
        
        # Vacuum should reduce database size due to removed fragmentation
        self.assertLessEqual(post_vacuum_size, pre_vacuum_size, 
                            "Database size should not increase after vacuum")
        
        # Verify database functionality after vacuum
        remaining_parts = self.db_manager.list_parts()
        self.assertEqual(len(remaining_parts), 3)  # Only original test parts should remain
    
    def test_database_maintenance_cleanup_logs(self):
        """
        Test database maintenance log cleanup operation.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Add many old discovery logs
        import datetime
        old_date = datetime.datetime.now() - datetime.timedelta(days=400)  # Older than retention
        
        old_logs = []
        for i in range(20):
            log = PartDiscoveryLog(
                part_number=f"OLD{i:03d}",
                action_taken="discovered",
                invoice_number=f"OLD_INV{i:03d}",
                discovered_price=Decimal(f"{i}.00"),
                discovery_date=old_date
            )
            self.db_manager.create_discovery_log(log)
            old_logs.append(log)
        
        # Verify old logs were added
        all_logs_before = self.db_manager.list_discovery_logs()
        self.assertEqual(len(all_logs_before), 22)  # 2 original + 20 old
        
        # Run maintenance with log cleanup (simulates: database maintenance --cleanup-logs)
        maintenance_result = self.db_manager.run_maintenance(cleanup_logs=True)
        
        # Verify cleanup was performed
        self.assertTrue(maintenance_result['success'])
        self.assertIn('logs_cleaned', maintenance_result)
        
        # Verify old logs were removed (based on retention policy)
        all_logs_after = self.db_manager.list_discovery_logs()
        self.assertLess(len(all_logs_after), len(all_logs_before), 
                       "Some logs should have been cleaned up")
        
        # Verify recent logs are still present
        recent_logs = [log for log in all_logs_after 
                      if log.part_number in ["BACKUP001", "BACKUP002"]]
        self.assertEqual(len(recent_logs), 2, "Recent logs should be preserved")
    
    def test_database_maintenance_integrity_verification(self):
        """
        Test database maintenance integrity verification.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Run maintenance with integrity check (simulates: database maintenance --verify-integrity)
        maintenance_result = self.db_manager.run_maintenance(verify_integrity=True)
        
        # Verify integrity check was performed
        self.assertTrue(maintenance_result['success'])
        self.assertTrue(maintenance_result['integrity_check_passed'])
        self.assertIn('integrity_issues', maintenance_result)
        
        # For a healthy database, there should be no integrity issues
        self.assertEqual(len(maintenance_result['integrity_issues']), 0)
        
        # Verify database is still functional after integrity check
        parts_after_check = self.db_manager.list_parts()
        self.assertEqual(len(parts_after_check), 3)
    
    def test_database_maintenance_with_auto_backup(self):
        """
        Test database maintenance with automatic backup creation.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Run maintenance with auto backup (simulates: database maintenance --auto-backup)
        maintenance_result = self.db_manager.run_maintenance(
            auto_backup=True,
            backup_dir=str(self.backup_dir)
        )
        
        # Verify maintenance was successful
        self.assertTrue(maintenance_result['success'])
        self.assertIn('backup_created', maintenance_result)
        
        if maintenance_result['backup_created']:
            # Verify backup file was created
            backup_files = list(self.backup_dir.glob("pre_maintenance_backup_*.db"))
            self.assertGreater(len(backup_files), 0, "Pre-maintenance backup should be created")
            
            # Add backup file to cleanup list
            for backup_file in backup_files:
                self.created_files.append(backup_file)
            
            # Verify backup contains original data
            backup_db = DatabaseManager(str(backup_files[0]))
            try:
                backup_parts = backup_db.list_parts()
                self.assertEqual(len(backup_parts), 3)
            finally:
                backup_db.close()
    
    def test_database_error_handling_corrupted_backup(self):
        """
        Test error handling when attempting to restore from corrupted backup.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create a corrupted backup file
        corrupted_backup_path = self.backup_dir / f"corrupted_backup_{self.test_id}.db"
        self.created_files.append(corrupted_backup_path)
        
        # Write invalid data to simulate corruption
        with open(corrupted_backup_path, 'wb') as f:
            f.write(b"This is not a valid SQLite database file")
        
        # Create backup manager
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        
        # Attempt to restore from corrupted backup
        restore_result = self.backup_manager.restore_backup(
            str(corrupted_backup_path),
            str(self.db_path)
        )
        
        # Verify restore failed gracefully
        self.assertFalse(restore_result['success'])
        self.assertIn('error', restore_result)
        self.assertIn('corrupt', restore_result['error'].lower())
        
        # Verify original database is still intact
        original_stats = self.db_manager.get_database_stats()
        self.assertIsInstance(original_stats, dict)
    
    def test_database_error_handling_invalid_backup_path(self):
        """
        Test error handling for invalid backup paths.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create backup manager
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        
        # Test backup to invalid path
        invalid_backup_path = "/invalid/path/that/does/not/exist/backup.db"
        
        backup_result = self.backup_manager.create_backup(invalid_backup_path)
        
        # Verify backup failed gracefully
        self.assertFalse(backup_result['success'])
        self.assertIn('error', backup_result)
        
        # Test restore from non-existent backup
        non_existent_backup = "/path/that/does/not/exist/backup.db"
        
        restore_result = self.backup_manager.restore_backup(
            non_existent_backup,
            str(self.db_path)
        )
        
        # Verify restore failed gracefully
        self.assertFalse(restore_result['success'])
        self.assertIn('error', restore_result)
    
    def test_database_cross_platform_compatibility(self):
        """
        Test database management functionality across different platforms.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_data()
        
        # Test backup with platform-specific paths
        backup_path = self.backup_dir / f"cross_platform_backup_{self.test_id}.db"
        self.created_files.append(backup_path)
        
        # Create backup manager
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        
        # Create backup
        backup_result = self.backup_manager.create_backup(str(backup_path))
        
        # Verify backup works across platforms
        self.assertTrue(backup_result['success'])
        self.assertTrue(backup_path.exists())
        
        # Test file permissions
        self.assertTrue(os.access(backup_path, os.R_OK), "Backup should be readable")
        
        # Test backup file can be opened by another database manager
        backup_db = DatabaseManager(str(backup_path))
        try:
            backup_parts = backup_db.list_parts()
            self.assertEqual(len(backup_parts), 3)
        finally:
            backup_db.close()
    
    def test_database_performance_large_backup_restore(self):
        """
        Test database backup and restore performance with larger datasets.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create a larger dataset for performance testing
        import time
        start_time = time.time()
        
        # Add 100 parts
        for i in range(100):
            part = Part(
                part_number=f"PERF{i:04d}",
                authorized_price=Decimal(f"{10 + (i % 50)}.{i % 100:02d}"),
                description=f"Performance Test Part {i}",
                category=f"Category{i % 10}"
            )
            self.db_manager.create_part(part)
        
        # Add 200 discovery logs
        for i in range(200):
            log = PartDiscoveryLog(
                part_number=f"PERF{i % 100:04d}",
                action_taken="discovered",
                invoice_number=f"PERF_INV{i:04d}",
                discovered_price=Decimal(f"{5 + (i % 25)}.{i % 100:02d}")
            )
            self.db_manager.create_discovery_log(log)
        
        data_creation_time = time.time() - start_time
        
        # Test backup performance
        backup_path = self.backup_dir / f"performance_backup_{self.test_id}.db"
        self.created_files.append(backup_path)
        
        self.backup_manager = DatabaseBackupManager(self.db_manager)
        
        backup_start_time = time.time()
        backup_result = self.backup_manager.create_backup(str(backup_path))
        backup_time = time.time() - backup_start_time
        
        # Verify backup was successful
        self.assertTrue(backup_result['success'])
        
        # Test restore performance
        # Close original database
        self.db_manager.close()
        
        restore_start_time = time.time()
        restore_result = self.backup_manager.restore_backup(
            str(backup_path),
            str(self.db_path)
        )
        restore_time = time.time() - restore_start_time
        
        # Verify restore was successful
        self.assertTrue(restore_result['success'])
        
        # Verify performance is reasonable
        self.assertLess(backup_time, 10.0, "Backup should complete within 10 seconds")
        self.assertLess(restore_time, 10.0, "Restore should complete within 10 seconds")
        
        # Verify data integrity after restore
        self.db_manager = DatabaseManager(str(self.db_path))
        restored_parts = self.db_manager.list_parts()
        restored_logs = self.db_manager.list_discovery_logs()
        
        self.assertEqual(len(restored_parts), 100)
        self.assertEqual(len(restored_logs), 200)


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)