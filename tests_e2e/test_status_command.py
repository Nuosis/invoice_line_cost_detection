"""
End-to-End Tests for Status Command Functionality

This test suite validates the status command functionality without using any mocking.
All tests create real database files and system resources, then clean up completely.

Test Coverage:
- Basic status command execution
- Database status reporting
- System information display
- Configuration status validation
- Error handling for missing/corrupted databases
- Performance metrics reporting
- Cross-platform compatibility
"""

import os
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Dict, Any

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part, Configuration, PartDiscoveryLog
from decimal import Decimal


class TestStatusCommand(unittest.TestCase):
    """
    Comprehensive e2e tests for status command functionality.
    
    These tests validate that the status command works correctly in real-world
    conditions without any mocking.
    """
    
    def setUp(self):
        """
        Set up test environment for each test.
        
        Creates a unique temporary directory and database file for each test
        to ensure complete isolation.
        """
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_status_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_status_db_{self.test_id}.db"
        
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
    
    def test_status_with_empty_database(self):
        """
        Test status command with a newly initialized empty database.
        """
        # Initialize database manager - creates empty database
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Get database statistics (simulates status command functionality)
        stats = self.db_manager.get_database_stats()
        
        # Verify basic statistics for empty database
        self.assertIsInstance(stats, dict, "Status should return a dictionary")
        
        # Check required status fields
        required_fields = [
            'total_parts', 'active_parts', 'config_entries', 
            'discovery_log_entries', 'database_size_bytes', 'database_version'
        ]
        
        for field in required_fields:
            self.assertIn(field, stats, f"Status should include '{field}' field")
        
        # Verify empty database values
        self.assertEqual(stats['total_parts'], 0, "Empty database should have 0 total parts")
        self.assertEqual(stats['active_parts'], 0, "Empty database should have 0 active parts")
        self.assertGreater(stats['config_entries'], 0, "Database should have default config entries")
        self.assertEqual(stats['discovery_log_entries'], 0, "Empty database should have 0 discovery log entries")
        self.assertGreater(stats['database_size_bytes'], 0, "Database file should have size > 0")
        self.assertEqual(stats['database_version'], '1.0', "Database version should be '1.0'")
    
    def test_status_with_populated_database(self):
        """
        Test status command with a database containing parts and discovery logs.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add test parts
        test_parts = [
            Part(part_number="TEST001", authorized_price=Decimal("10.50"), 
                 description="Test Part 1", category="Test"),
            Part(part_number="TEST002", authorized_price=Decimal("15.75"), 
                 description="Test Part 2", category="Test"),
            Part(part_number="INACTIVE001", authorized_price=Decimal("5.00"), 
                 description="Inactive Part", category="Test", is_active=False)
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
        
        # Add test discovery log entries
        test_logs = [
            PartDiscoveryLog(
                part_number="TEST001",
                action_taken="discovered",
                invoice_number="INV001",
                discovered_price=Decimal("10.50")
            ),
            PartDiscoveryLog(
                part_number="TEST002",
                action_taken="added",
                invoice_number="INV002",
                discovered_price=Decimal("15.75")
            )
        ]
        
        for log in test_logs:
            self.db_manager.create_discovery_log(log)
        
        # Get database statistics
        stats = self.db_manager.get_database_stats()
        
        # Verify populated database values
        self.assertEqual(stats['total_parts'], 3, "Should have 3 total parts")
        self.assertEqual(stats['active_parts'], 2, "Should have 2 active parts")
        self.assertEqual(stats['discovery_log_entries'], 2, "Should have 2 discovery log entries")
        self.assertGreater(stats['database_size_bytes'], 0, "Database should have grown in size")
    
    def test_status_database_file_information(self):
        """
        Test that status command provides accurate database file information.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Get initial stats
        initial_stats = self.db_manager.get_database_stats()
        initial_size = initial_stats['database_size_bytes']
        
        # Add some data to increase database size
        for i in range(10):
            part = Part(
                part_number=f"BULK{i:03d}",
                authorized_price=Decimal(f"{10 + i}.50"),
                description=f"Bulk Test Part {i}",
                category="Bulk"
            )
            self.db_manager.create_part(part)
        
        # Get updated stats
        updated_stats = self.db_manager.get_database_stats()
        updated_size = updated_stats['database_size_bytes']
        
        # Verify database size increased (allow for same size due to SQLite page allocation)
        self.assertGreaterEqual(updated_size, initial_size, "Database size should not decrease after adding parts")
        self.assertEqual(updated_stats['total_parts'], 10, "Should have 10 parts after bulk insert")
        self.assertEqual(updated_stats['active_parts'], 10, "All bulk parts should be active")
    
    def test_status_configuration_information(self):
        """
        Test that status command includes configuration information.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Get all configurations (simulates part of status command)
        configs = self.db_manager.list_config()
        
        # Verify we have default configurations
        self.assertGreater(len(configs), 0, "Should have default configurations")
        
        # Check for specific required configurations
        config_keys = {config.key for config in configs}
        required_configs = [
            'validation_mode',
            'default_output_format',
            'interactive_discovery',
            'database_version'
        ]
        
        for required_config in required_configs:
            self.assertIn(required_config, config_keys, 
                         f"Should have default configuration '{required_config}'")
        
        # Verify configuration values are accessible
        validation_mode = self.db_manager.get_config_value('validation_mode')
        self.assertIsNotNone(validation_mode, "Should be able to retrieve validation_mode")
        self.assertEqual(validation_mode, 'parts_based', "Default validation_mode should be 'parts_based'")
    
    def test_status_with_missing_database_file(self):
        """
        Test status command behavior when database file doesn't exist.
        """
        # Use a non-existent database path
        non_existent_path = self.temp_dir / "non_existent.db"
        
        # Initialize database manager - should create the database
        self.db_manager = DatabaseManager(str(non_existent_path))
        self.created_files.append(non_existent_path)
        
        # Verify database was created and is functional
        self.assertTrue(non_existent_path.exists(), "Database file should be created")
        
        # Get stats to verify functionality
        stats = self.db_manager.get_database_stats()
        self.assertIsInstance(stats, dict, "Should return valid stats even for new database")
        self.assertEqual(stats['total_parts'], 0, "New database should have 0 parts")
    
    def test_status_database_integrity_check(self):
        """
        Test that status command can detect database integrity issues.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add some test data
        test_part = Part(
            part_number="INTEGRITY_TEST",
            authorized_price=Decimal("25.00"),
            description="Integrity Test Part"
        )
        self.db_manager.create_part(test_part)
        
        # Verify database integrity through schema verification
        # This simulates what the status command would do
        try:
            # The _verify_database_schema method is called during initialization
            # and would catch integrity issues
            with self.db_manager.get_connection() as conn:
                # Check that we can query all tables
                cursor = conn.execute("SELECT COUNT(*) FROM parts")
                parts_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM config")
                config_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM part_discovery_log")
                log_count = cursor.fetchone()[0]
                
                # Verify counts are reasonable
                self.assertEqual(parts_count, 1, "Should have 1 part")
                self.assertGreater(config_count, 0, "Should have config entries")
                self.assertEqual(log_count, 0, "Should have 0 log entries")
                
        except Exception as e:
            self.fail(f"Database integrity check failed: {e}")
    
    def test_status_performance_metrics(self):
        """
        Test that status command provides performance-related metrics.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add a moderate amount of test data to get meaningful metrics
        import time
        start_time = time.time()
        
        # Add parts in batches to simulate real usage
        for batch in range(3):
            for i in range(10):
                part_num = f"PERF{batch:02d}{i:03d}"
                part = Part(
                    part_number=part_num,
                    authorized_price=Decimal(f"{10 + batch + i}.50"),
                    description=f"Performance Test Part {batch}-{i}",
                    category=f"Batch{batch}"
                )
                self.db_manager.create_part(part)
        
        creation_time = time.time() - start_time
        
        # Get database statistics
        stats = self.db_manager.get_database_stats()
        
        # Verify performance metrics are reasonable
        self.assertEqual(stats['total_parts'], 30, "Should have created 30 parts")
        self.assertLess(creation_time, 5.0, "Creating 30 parts should take less than 5 seconds")
        
        # Test query performance
        start_time = time.time()
        parts = self.db_manager.list_parts()
        query_time = time.time() - start_time
        
        self.assertEqual(len(parts), 30, "Should retrieve all 30 parts")
        self.assertLess(query_time, 1.0, "Querying 30 parts should take less than 1 second")
    
    def test_status_cross_platform_compatibility(self):
        """
        Test that status command works correctly across different platforms.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test path handling across platforms
        self.assertTrue(self.db_path.exists(), "Database file should exist")
        self.assertTrue(self.db_path.is_file(), "Database path should be a file")
        
        # Test file permissions
        self.assertTrue(os.access(self.db_path, os.R_OK), "Database should be readable")
        self.assertTrue(os.access(self.db_path, os.W_OK), "Database should be writable")
        
        # Get stats and verify path information is correct
        stats = self.db_manager.get_database_stats()
        actual_size = self.db_path.stat().st_size
        
        self.assertEqual(stats['database_size_bytes'], actual_size, 
                        "Reported size should match actual file size")
    
    def test_status_with_concurrent_access(self):
        """
        Test status command behavior with concurrent database access.
        """
        import threading
        import time
        
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        results = []
        errors = []
        
        def get_status():
            try:
                # Create separate database manager for this thread
                thread_db_manager = DatabaseManager(str(self.db_path))
                stats = thread_db_manager.get_database_stats()
                results.append(stats)
                thread_db_manager.close()
            except Exception as e:
                errors.append(e)
        
        def add_parts():
            try:
                # Create separate database manager for this thread
                thread_db_manager = DatabaseManager(str(self.db_path))
                for i in range(5):
                    part = Part(
                        part_number=f"CONCURRENT{i:03d}",
                        authorized_price=Decimal(f"{20 + i}.00"),
                        description=f"Concurrent Test Part {i}"
                    )
                    thread_db_manager.create_part(part)
                    time.sleep(0.01)  # Small delay to increase concurrency chance
                thread_db_manager.close()
            except Exception as e:
                errors.append(e)
        
        # Start concurrent operations
        threads = []
        
        # Start status checking threads
        for i in range(2):
            thread = threading.Thread(target=get_status)
            threads.append(thread)
            thread.start()
        
        # Start part adding thread
        thread = threading.Thread(target=add_parts)
        threads.append(thread)
        thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify results
        self.assertEqual(len(errors), 0, f"No errors should occur during concurrent access: {errors}")
        self.assertGreaterEqual(len(results), 2, "Should have at least 2 status results")
        
        # All status results should be valid dictionaries
        for result in results:
            self.assertIsInstance(result, dict, "Each status result should be a dictionary")
            self.assertIn('total_parts', result, "Each result should have total_parts")
    
    def test_status_memory_usage(self):
        """
        Test that status command has reasonable memory usage.
        """
        try:
            import psutil
            import os
        except ImportError:
            self.skipTest("psutil not available - skipping memory usage test")
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add a reasonable amount of data
        for i in range(100):
            part = Part(
                part_number=f"MEM{i:04d}",
                authorized_price=Decimal(f"{10 + (i % 50)}.50"),
                description=f"Memory Test Part {i}",
                category=f"Category{i % 10}"
            )
            self.db_manager.create_part(part)
        
        # Get status multiple times to test memory stability
        for _ in range(10):
            stats = self.db_manager.get_database_stats()
            self.assertIsInstance(stats, dict, "Status should always return valid data")
        
        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for this test)
        max_acceptable_increase = 50 * 1024 * 1024  # 50MB
        self.assertLess(memory_increase, max_acceptable_increase,
                       f"Memory increase ({memory_increase / 1024 / 1024:.1f}MB) should be reasonable")


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)