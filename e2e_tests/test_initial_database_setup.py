"""
End-to-End Smoke Tests for Initial Database Setup

This test suite comprehensively validates the initial database setup functionality
without using any mocking. All tests create real database files and clean up
after themselves.

Test Coverage:
- Database file creation and initialization
- Schema validation (tables, indexes, triggers, views)
- Default configuration insertion and validation
- Error handling during initialization
- Database connection management
- Cross-platform compatibility
"""

import os
import sqlite3
import tempfile
import unittest
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part, Configuration, PartDiscoveryLog, DatabaseError, ValidationError


class TestInitialDatabaseSetup(unittest.TestCase):
    """
    Comprehensive smoke tests for initial database setup functionality.
    
    These tests validate that the database initialization process works correctly
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
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_db_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_database_{self.test_id}.db"
        
        # Track created resources for cleanup
        self.created_files = [self.db_path]
        self.created_dirs = [self.temp_dir]
        self.db_manager = None
        
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
        
        # Remove all created files
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove all created directories
        for dir_path in reversed(self.created_dirs):  # Remove in reverse order
            try:
                if dir_path.exists():
                    dir_path.rmdir()
            except Exception:
                pass  # Ignore errors during cleanup
    
    def test_database_file_creation_on_initialization(self):
        """
        Test that database file is created when DatabaseManager is initialized
        with a non-existent database path.
        """
        # Verify database file doesn't exist initially
        self.assertFalse(self.db_path.exists(), "Database file should not exist initially")
        
        # Initialize DatabaseManager - should create the database file
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Verify database file was created
        self.assertTrue(self.db_path.exists(), "Database file should be created during initialization")
        self.assertGreater(self.db_path.stat().st_size, 0, "Database file should not be empty")
    
    def test_database_directory_creation(self):
        """
        Test that parent directories are created if they don't exist.
        """
        # Create a nested directory path that doesn't exist
        nested_dir = self.temp_dir / "nested" / "subdirectory"
        nested_db_path = nested_dir / f"nested_test_{self.test_id}.db"
        self.created_files.append(nested_db_path)
        self.created_dirs.extend([nested_dir, nested_dir.parent])
        
        # Verify nested directory doesn't exist
        self.assertFalse(nested_dir.exists(), "Nested directory should not exist initially")
        
        # Initialize DatabaseManager - should create directories and database
        self.db_manager = DatabaseManager(str(nested_db_path))
        
        # Verify directory and database were created
        self.assertTrue(nested_dir.exists(), "Nested directory should be created")
        self.assertTrue(nested_db_path.exists(), "Database file should be created in nested directory")
    
    def test_required_tables_creation(self):
        """
        Test that all required tables are created during initialization.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Get list of created tables
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
        
        # Verify all required tables exist
        required_tables = ['parts', 'config', 'part_discovery_log']
        for table in required_tables:
            self.assertIn(table, tables, f"Required table '{table}' should be created")
        
        # Verify we have exactly the expected tables (no extras)
        self.assertEqual(set(tables), set(required_tables), "Should have exactly the required tables")
    
    def test_parts_table_schema(self):
        """
        Test that the parts table has the correct schema structure.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        with self.db_manager.get_connection() as conn:
            # Get parts table schema
            cursor = conn.execute("PRAGMA table_info(parts)")
            columns = {row[1]: {'type': row[2], 'notnull': row[3], 'pk': row[5]} 
                      for row in cursor.fetchall()}
        
        # Verify required columns exist with correct properties
        expected_columns = {
            'part_number': {'type': 'TEXT', 'notnull': 0, 'pk': 1},
            'authorized_price': {'type': 'DECIMAL(10,4)', 'notnull': 1, 'pk': 0},
            'description': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'category': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'source': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'first_seen_invoice': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'created_date': {'type': 'TIMESTAMP', 'notnull': 0, 'pk': 0},
            'last_updated': {'type': 'TIMESTAMP', 'notnull': 0, 'pk': 0},
            'is_active': {'type': 'BOOLEAN', 'notnull': 0, 'pk': 0},
            'notes': {'type': 'TEXT', 'notnull': 0, 'pk': 0}
        }
        
        for col_name, expected_props in expected_columns.items():
            self.assertIn(col_name, columns, f"Column '{col_name}' should exist in parts table")
            actual_props = columns[col_name]
            self.assertEqual(actual_props['pk'], expected_props['pk'], 
                           f"Column '{col_name}' primary key property mismatch")
    
    def test_config_table_schema(self):
        """
        Test that the config table has the correct schema structure.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        with self.db_manager.get_connection() as conn:
            # Get config table schema
            cursor = conn.execute("PRAGMA table_info(config)")
            columns = {row[1]: {'type': row[2], 'notnull': row[3], 'pk': row[5]} 
                      for row in cursor.fetchall()}
        
        # Verify required columns exist
        expected_columns = {
            'key': {'type': 'TEXT', 'notnull': 0, 'pk': 1},
            'value': {'type': 'TEXT', 'notnull': 1, 'pk': 0},
            'data_type': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'description': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'category': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'created_date': {'type': 'TIMESTAMP', 'notnull': 0, 'pk': 0},
            'last_updated': {'type': 'TIMESTAMP', 'notnull': 0, 'pk': 0}
        }
        
        for col_name, expected_props in expected_columns.items():
            self.assertIn(col_name, columns, f"Column '{col_name}' should exist in config table")
            actual_props = columns[col_name]
            self.assertEqual(actual_props['pk'], expected_props['pk'], 
                           f"Column '{col_name}' primary key property mismatch")
    
    def test_part_discovery_log_table_schema(self):
        """
        Test that the part_discovery_log table has the correct schema structure.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        with self.db_manager.get_connection() as conn:
            # Get part_discovery_log table schema
            cursor = conn.execute("PRAGMA table_info(part_discovery_log)")
            columns = {row[1]: {'type': row[2], 'notnull': row[3], 'pk': row[5]} 
                      for row in cursor.fetchall()}
        
        # Verify required columns exist
        expected_columns = {
            'id': {'type': 'INTEGER', 'notnull': 0, 'pk': 1},
            'part_number': {'type': 'TEXT', 'notnull': 1, 'pk': 0},
            'invoice_number': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'invoice_date': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'discovered_price': {'type': 'DECIMAL(10,4)', 'notnull': 0, 'pk': 0},
            'authorized_price': {'type': 'DECIMAL(10,4)', 'notnull': 0, 'pk': 0},
            'action_taken': {'type': 'TEXT', 'notnull': 1, 'pk': 0},
            'user_decision': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'discovery_date': {'type': 'TIMESTAMP', 'notnull': 0, 'pk': 0},
            'processing_session_id': {'type': 'TEXT', 'notnull': 0, 'pk': 0},
            'notes': {'type': 'TEXT', 'notnull': 0, 'pk': 0}
        }
        
        for col_name, expected_props in expected_columns.items():
            self.assertIn(col_name, columns, f"Column '{col_name}' should exist in part_discovery_log table")
    
    def test_indexes_creation(self):
        """
        Test that all required indexes are created during initialization.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        with self.db_manager.get_connection() as conn:
            # Get list of created indexes
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            indexes = [row[0] for row in cursor.fetchall()]
        
        # Verify required indexes exist
        expected_indexes = [
            'idx_parts_number',
            'idx_parts_active',
            'idx_parts_category',
            'idx_config_category',
            'idx_discovery_part',
            'idx_discovery_invoice',
            'idx_discovery_date',
            'idx_discovery_session'
        ]
        
        for index in expected_indexes:
            self.assertIn(index, indexes, f"Required index '{index}' should be created")
    
    def test_triggers_creation(self):
        """
        Test that all required triggers are created during initialization.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        with self.db_manager.get_connection() as conn:
            # Get list of created triggers
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='trigger'
                ORDER BY name
            """)
            triggers = [row[0] for row in cursor.fetchall()]
        
        # Verify required triggers exist
        expected_triggers = [
            'update_parts_timestamp',
            'update_config_timestamp'
        ]
        
        for trigger in expected_triggers:
            self.assertIn(trigger, triggers, f"Required trigger '{trigger}' should be created")
    
    def test_views_creation(self):
        """
        Test that all required views are created during initialization.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        with self.db_manager.get_connection() as conn:
            # Get list of created views
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='view'
                ORDER BY name
            """)
            views = [row[0] for row in cursor.fetchall()]
        
        # Verify required views exist
        expected_views = [
            'active_parts',
            'recent_discoveries'
        ]
        
        for view in expected_views:
            self.assertIn(view, views, f"Required view '{view}' should be created")
    
    def test_default_configuration_insertion(self):
        """
        Test that default configuration values are inserted during initialization.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Get all configuration entries
        configs = self.db_manager.list_config()
        config_keys = {config.key for config in configs}
        
        # Verify required default configurations exist
        expected_config_keys = {
            'validation_mode',
            'default_output_format',
            'interactive_discovery',
            'auto_add_discovered_parts',
            'price_tolerance',
            'backup_retention_days',
            'log_retention_days',
            'database_version'
        }
        
        for key in expected_config_keys:
            self.assertIn(key, config_keys, f"Default configuration '{key}' should be inserted")
        
        # Verify specific configuration values
        validation_mode = self.db_manager.get_config_value('validation_mode')
        self.assertEqual(validation_mode, 'parts_based', "Default validation_mode should be 'parts_based'")
        
        output_format = self.db_manager.get_config_value('default_output_format')
        self.assertEqual(output_format, 'csv', "Default output_format should be 'csv'")
        
        interactive_discovery = self.db_manager.get_config_value('interactive_discovery')
        self.assertTrue(interactive_discovery, "Default interactive_discovery should be True")
        
        database_version = self.db_manager.get_config_value('database_version')
        self.assertEqual(database_version, '1.0', "Default database_version should be '1.0'")
    
    def test_configuration_data_types(self):
        """
        Test that configuration values have correct data types.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test string configurations
        validation_mode = self.db_manager.get_config('validation_mode')
        self.assertEqual(validation_mode.data_type, 'string')
        self.assertIsInstance(validation_mode.get_typed_value(), str)
        
        # Test boolean configurations
        interactive_discovery = self.db_manager.get_config('interactive_discovery')
        self.assertEqual(interactive_discovery.data_type, 'boolean')
        self.assertIsInstance(interactive_discovery.get_typed_value(), bool)
        
        # Test number configurations
        price_tolerance = self.db_manager.get_config('price_tolerance')
        self.assertEqual(price_tolerance.data_type, 'number')
        self.assertIsInstance(price_tolerance.get_typed_value(), float)
    
    def test_database_connection_properties(self):
        """
        Test that database connections have correct properties set.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        with self.db_manager.get_connection() as conn:
            # Test foreign key constraints are enabled
            cursor = conn.execute("PRAGMA foreign_keys")
            foreign_keys_enabled = cursor.fetchone()[0]
            self.assertEqual(foreign_keys_enabled, 1, "Foreign key constraints should be enabled")
            
            # Test WAL mode is enabled
            cursor = conn.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            self.assertEqual(journal_mode.upper(), 'WAL', "WAL journal mode should be enabled")
            
            # Test busy timeout is set
            cursor = conn.execute("PRAGMA busy_timeout")
            busy_timeout = cursor.fetchone()[0]
            self.assertEqual(busy_timeout, 30000, "Busy timeout should be set to 30 seconds")
    
    def test_existing_database_initialization(self):
        """
        Test that initializing with an existing database doesn't recreate it.
        """
        # Create initial database
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add a test part to verify data persistence
        test_part = Part(
            part_number="TEST001",
            authorized_price=Decimal("10.50"),
            description="Test Part"
        )
        self.db_manager.create_part(test_part)
        
        # Get initial stats
        initial_stats = self.db_manager.get_database_stats()
        initial_size = self.db_path.stat().st_size
        
        # Close and reinitialize with same path
        self.db_manager.close()
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Verify database wasn't recreated
        final_stats = self.db_manager.get_database_stats()
        final_size = self.db_path.stat().st_size
        
        self.assertEqual(initial_stats['total_parts'], final_stats['total_parts'], 
                        "Part count should be preserved")
        self.assertEqual(initial_size, final_size, "Database file size should be unchanged")
        
        # Verify test part still exists
        retrieved_part = self.db_manager.get_part("TEST001")
        self.assertEqual(retrieved_part.part_number, "TEST001")
        self.assertEqual(retrieved_part.authorized_price, Decimal("10.50"))
    
    def test_schema_verification_on_existing_database(self):
        """
        Test that schema verification works correctly on existing databases.
        """
        # Create initial database
        self.db_manager = DatabaseManager(str(self.db_path))
        self.db_manager.close()
        
        # Reinitialize - should verify schema without errors
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Verify database is functional
        stats = self.db_manager.get_database_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_parts', stats)
        self.assertIn('database_version', stats)
    
    def test_database_stats_after_initialization(self):
        """
        Test that database statistics are available after initialization.
        """
        self.db_manager = DatabaseManager(str(self.db_path))
        
        stats = self.db_manager.get_database_stats()
        
        # Verify stats structure
        expected_keys = [
            'total_parts', 'active_parts', 'config_entries', 
            'discovery_log_entries', 'database_size_bytes', 'database_version'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats, f"Stats should include '{key}'")
        
        # Verify initial values
        self.assertEqual(stats['total_parts'], 0, "Should start with 0 parts")
        self.assertEqual(stats['active_parts'], 0, "Should start with 0 active parts")
        self.assertGreater(stats['config_entries'], 0, "Should have default config entries")
        self.assertEqual(stats['discovery_log_entries'], 0, "Should start with 0 discovery log entries")
        self.assertGreater(stats['database_size_bytes'], 0, "Database file should have size")
        self.assertEqual(stats['database_version'], '1.0', "Should have correct database version")
    
    def test_error_handling_invalid_database_path(self):
        """
        Test error handling when database path is invalid or inaccessible.
        """
        # Test with invalid path (contains null character on most systems)
        invalid_path = str(self.temp_dir / "invalid\x00path.db")
        
        with self.assertRaises(DatabaseError):
            DatabaseManager(invalid_path)
    
    def test_error_handling_permission_denied(self):
        """
        Test error handling when database directory is not writable.
        
        Note: This test may be skipped on systems where permission manipulation
        is not possible or reliable.
        """
        # Create a directory and make it read-only
        readonly_dir = self.temp_dir / "readonly"
        readonly_dir.mkdir()
        self.created_dirs.append(readonly_dir)
        
        try:
            # Make directory read-only
            readonly_dir.chmod(0o444)
            
            # Try to create database in read-only directory
            readonly_db_path = readonly_dir / "test.db"
            self.created_files.append(readonly_db_path)
            
            with self.assertRaises(DatabaseError):
                DatabaseManager(str(readonly_db_path))
                
        except (OSError, PermissionError):
            # Skip test if we can't manipulate permissions
            self.skipTest("Cannot test permission denied scenario on this system")
        finally:
            # Restore permissions for cleanup
            try:
                readonly_dir.chmod(0o755)
            except (OSError, PermissionError):
                pass
    
    def test_concurrent_initialization(self):
        """
        Test that concurrent database initialization is handled correctly.
        """
        import threading
        import time
        
        results = []
        errors = []
        
        def init_database():
            try:
                db_manager = DatabaseManager(str(self.db_path))
                stats = db_manager.get_database_stats()
                results.append(stats)
                db_manager.close()
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads trying to initialize the same database
        threads = []
        for i in range(3):
            thread = threading.Thread(target=init_database)
            threads.append(thread)
            thread.start()
            time.sleep(0.01)  # Small delay to increase chance of concurrency
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify results
        self.assertEqual(len(errors), 0, f"No errors should occur during concurrent initialization: {errors}")
        self.assertEqual(len(results), 3, "All threads should complete successfully")
        
        # Verify all threads see the same database state
        for result in results[1:]:
            self.assertEqual(result['database_version'], results[0]['database_version'])
            self.assertEqual(result['config_entries'], results[0]['config_entries'])


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)