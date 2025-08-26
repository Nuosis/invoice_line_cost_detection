"""
End-to-End Tests for Configuration Management Commands

This test suite validates all configuration management functionality without using any mocking.
All tests create real database files and system resources, then clean up completely.

Test Coverage:
- Config get command (retrieving individual configuration values)
- Config set command (setting configuration values with type validation)
- Config list command (listing all configurations with filtering)
- Config reset command (resetting to default values)
- Configuration data type handling (string, boolean, number)
- Configuration categories and organization
- Error handling for invalid configurations
- Configuration persistence and retrieval
"""

import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Configuration, DatabaseError, ValidationError


class TestConfigurationManagement(unittest.TestCase):
    """
    Comprehensive e2e tests for configuration management functionality.
    
    These tests validate that all configuration management commands work correctly
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
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_config_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_config_db_{self.test_id}.db"
        
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
    
    def test_config_get_default_values(self):
        """
        Test config get command with default configuration values.
        """
        # Initialize database manager (creates default configurations)
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test getting default validation mode (simulates: config get validation_mode)
        validation_mode = self.db_manager.get_config_value('validation_mode')
        self.assertEqual(validation_mode, 'parts_based')
        
        # Test getting default output format (simulates: config get default_output_format)
        output_format = self.db_manager.get_config_value('default_output_format')
        self.assertEqual(output_format, 'txt')
        
        # Test getting default interactive discovery (simulates: config get interactive_discovery)
        interactive_discovery = self.db_manager.get_config_value('interactive_discovery')
        self.assertTrue(interactive_discovery)
        
        # Test getting default database version (simulates: config get database_version)
        database_version = self.db_manager.get_config_value('database_version')
        self.assertEqual(database_version, '1.0')
    
    def test_config_get_with_detailed_information(self):
        """
        Test config get command with detailed configuration information.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test getting detailed configuration object (simulates: config get validation_mode --format detailed)
        validation_mode_config = self.db_manager.get_config('validation_mode')
        
        # Verify configuration object structure
        self.assertIsInstance(validation_mode_config, Configuration)
        self.assertEqual(validation_mode_config.key, 'validation_mode')
        self.assertEqual(validation_mode_config.value, 'parts_based')
        self.assertEqual(validation_mode_config.data_type, 'string')
        self.assertIsNotNone(validation_mode_config.description)
        self.assertIsNotNone(validation_mode_config.category)
        self.assertIsNotNone(validation_mode_config.created_date)
        
        # Test getting boolean configuration with details
        interactive_config = self.db_manager.get_config('interactive_discovery')
        self.assertEqual(interactive_config.data_type, 'boolean')
        self.assertEqual(interactive_config.get_typed_value(), True)
        
        # Test getting number configuration with details
        price_tolerance_config = self.db_manager.get_config('price_tolerance')
        self.assertEqual(price_tolerance_config.data_type, 'number')
        self.assertIsInstance(price_tolerance_config.get_typed_value(), float)
    
    def test_config_set_string_values(self):
        """
        Test config set command with string values.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test setting validation mode (simulates: config set validation_mode threshold_based)
        self.db_manager.set_config_value('validation_mode', 'threshold_based')
        
        # Verify the value was set
        updated_value = self.db_manager.get_config_value('validation_mode')
        self.assertEqual(updated_value, 'threshold_based')
        
        # Test setting output format (simulates: config set default_output_format json)
        self.db_manager.set_config_value('default_output_format', 'json')
        
        # Verify the value was set
        updated_format = self.db_manager.get_config_value('default_output_format')
        self.assertEqual(updated_format, 'json')
        
        # Verify last_updated timestamp was updated
        updated_config = self.db_manager.get_config('validation_mode')
        self.assertIsNotNone(updated_config.last_updated)
    
    def test_config_set_boolean_values(self):
        """
        Test config set command with boolean values.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test setting boolean to false (simulates: config set interactive_discovery false)
        self.db_manager.set_config_value('interactive_discovery', False)
        
        # Verify the boolean value was set correctly
        updated_value = self.db_manager.get_config_value('interactive_discovery')
        self.assertFalse(updated_value)
        
    
    def test_config_set_number_values(self):
        """
        Test config set command with number values.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test setting price tolerance (simulates: config set price_tolerance 0.05)
        self.db_manager.set_config_value('price_tolerance', 0.05)
        
        # Verify the number value was set correctly
        updated_tolerance = self.db_manager.get_config_value('price_tolerance')
        self.assertEqual(updated_tolerance, 0.05)
        
        # Test setting retention days (simulates: config set log_retention_days 180)
        self.db_manager.set_config_value('log_retention_days', 180)
        
        # Verify the integer value was set correctly
        retention_days = self.db_manager.get_config_value('log_retention_days')
        self.assertEqual(retention_days, 180)
        
        # Verify data type is preserved
        tolerance_config = self.db_manager.get_config('price_tolerance')
        self.assertEqual(tolerance_config.data_type, 'number')
        self.assertIsInstance(tolerance_config.get_typed_value(), float)
    
    def test_config_set_new_configuration(self):
        """
        Test config set command for creating new configuration entries.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test setting a new custom configuration (simulates: config set custom_setting "custom_value")
        self.db_manager.set_config_value(
            'custom_test_setting', 
            'custom_test_value',
            data_type='string',
            description='Test custom configuration',
            category='test'
        )
        
        # Verify the new configuration was created
        custom_value = self.db_manager.get_config_value('custom_test_setting')
        self.assertEqual(custom_value, 'custom_test_value')
        
        # Verify the configuration details
        custom_config = self.db_manager.get_config('custom_test_setting')
        self.assertEqual(custom_config.key, 'custom_test_setting')
        self.assertEqual(custom_config.value, 'custom_test_value')
        self.assertEqual(custom_config.data_type, 'string')
        self.assertEqual(custom_config.description, 'Test custom configuration')
        self.assertEqual(custom_config.category, 'test')
        self.assertIsNotNone(custom_config.created_date)
        
        # Test setting a new number configuration
        self.db_manager.set_config_value(
            'custom_number_setting',
            42.5,
            data_type='number',
            description='Test custom number',
            category='test'
        )
        
        # Verify the new number configuration
        custom_number = self.db_manager.get_config_value('custom_number_setting')
        self.assertEqual(custom_number, 42.5)
    
    def test_config_list_all_configurations(self):
        """
        Test config list command for all configurations.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Get all configurations (simulates: config list)
        all_configs = self.db_manager.list_config()
        
        # Verify we have default configurations
        self.assertGreater(len(all_configs), 0)
        
        # Verify required default configurations exist
        config_keys = {config.key for config in all_configs}
        required_configs = {
            'validation_mode',
            'default_output_format',
            'interactive_discovery',
            'database_version',
            'price_tolerance',
            'log_retention_days'
        }
        
        for required_config in required_configs:
            self.assertIn(required_config, config_keys, 
                         f"Required configuration '{required_config}' should exist")
        
        # Verify configuration objects have required fields
        for config in all_configs:
            self.assertIsInstance(config, Configuration)
            self.assertIsNotNone(config.key)
            self.assertIsNotNone(config.value)
            self.assertIsNotNone(config.data_type)
            self.assertIsNotNone(config.created_date)
    
    def test_config_list_with_category_filter(self):
        """
        Test config list command with category filtering.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add configurations in different categories
        self.db_manager.set_config_value(
            'test_category_1', 'value1', 
            data_type='string', category='test_category'
        )
        self.db_manager.set_config_value(
            'test_category_2', 'value2', 
            data_type='string', category='test_category'
        )
        self.db_manager.set_config_value(
            'other_category_1', 'value3', 
            data_type='string', category='other_category'
        )
        
        # Test filtering by category (simulates: config list --category test_category)
        test_category_configs = self.db_manager.list_config(category='test_category')
        
        # Verify filtering worked
        self.assertEqual(len(test_category_configs), 2)
        for config in test_category_configs:
            self.assertEqual(config.category, 'test_category')
        
        # Verify specific configurations are present
        test_config_keys = {config.key for config in test_category_configs}
        self.assertIn('test_category_1', test_config_keys)
        self.assertIn('test_category_2', test_config_keys)
        self.assertNotIn('other_category_1', test_config_keys)
        
        # Test filtering by different category
        other_category_configs = self.db_manager.list_config(category='other_category')
        self.assertEqual(len(other_category_configs), 1)
        self.assertEqual(other_category_configs[0].key, 'other_category_1')
    
    def test_config_list_with_format_options(self):
        """
        Test config list command with different output formats.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Get configurations in table format (default)
        all_configs = self.db_manager.list_config()
        
        # Verify we can access all configuration details
        for config in all_configs:
            # Test that we can access all fields (simulates table format display)
            self.assertIsNotNone(config.key)
            self.assertIsNotNone(config.value)
            self.assertIsNotNone(config.data_type)
            self.assertIsNotNone(config.category)
            
            # Test typed value conversion
            typed_value = config.get_typed_value()
            if config.data_type == 'boolean':
                self.assertIsInstance(typed_value, bool)
            elif config.data_type == 'number':
                self.assertIsInstance(typed_value, (int, float))
            elif config.data_type == 'string':
                self.assertIsInstance(typed_value, str)
        
        # Test getting configurations as dictionary (simulates JSON format)
        config_dict = {}
        for config in all_configs:
            config_dict[config.key] = {
                'value': config.get_typed_value(),
                'data_type': config.data_type,
                'category': config.category,
                'description': config.description
            }
        
        # Verify dictionary format contains expected data
        self.assertIn('validation_mode', config_dict)
        self.assertEqual(config_dict['validation_mode']['value'], 'parts_based')
        self.assertEqual(config_dict['validation_mode']['data_type'], 'string')
    
    def test_config_reset_single_configuration(self):
        """
        Test config reset command for individual configurations.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Modify a default configuration
        original_value = self.db_manager.get_config_value('validation_mode')
        self.assertEqual(original_value, 'parts_based')
        
        # Change the value
        self.db_manager.set_config_value('validation_mode', 'threshold_based')
        modified_value = self.db_manager.get_config_value('validation_mode')
        self.assertEqual(modified_value, 'threshold_based')
        
        # Reset to default (simulates: config reset validation_mode)
        self.db_manager.reset_config_to_default('validation_mode')
        
        # Verify value was reset to default
        reset_value = self.db_manager.get_config_value('validation_mode')
        self.assertEqual(reset_value, 'parts_based')
        
        # Test resetting a boolean configuration
        self.db_manager.set_config_value('interactive_discovery', False)
        self.assertFalse(self.db_manager.get_config_value('interactive_discovery'))
        
        self.db_manager.reset_config_to_default('interactive_discovery')
        reset_boolean = self.db_manager.get_config_value('interactive_discovery')
        self.assertTrue(reset_boolean)  # Default should be True
    
    def test_config_reset_multiple_configurations(self):
        """
        Test config reset command for multiple configurations.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Modify multiple configurations
        self.db_manager.set_config_value('validation_mode', 'threshold_based')
        self.db_manager.set_config_value('default_output_format', 'json')
        self.db_manager.set_config_value('interactive_discovery', False)
        self.db_manager.set_config_value('price_tolerance', 0.10)
        
        # Verify modifications
        self.assertEqual(self.db_manager.get_config_value('validation_mode'), 'threshold_based')
        self.assertEqual(self.db_manager.get_config_value('default_output_format'), 'json')
        self.assertFalse(self.db_manager.get_config_value('interactive_discovery'))
        self.assertEqual(self.db_manager.get_config_value('price_tolerance'), 0.10)
        
        # Reset multiple configurations (simulates: config reset validation_mode default_output_format)
        configs_to_reset = ['validation_mode', 'default_output_format', 'interactive_discovery']
        for config_key in configs_to_reset:
            self.db_manager.reset_config_to_default(config_key)
        
        # Verify all were reset to defaults
        self.assertEqual(self.db_manager.get_config_value('validation_mode'), 'parts_based')
        self.assertEqual(self.db_manager.get_config_value('default_output_format'), 'csv')
        self.assertTrue(self.db_manager.get_config_value('interactive_discovery'))
        
        # Verify unmodified configuration remains changed
        self.assertEqual(self.db_manager.get_config_value('price_tolerance'), 0.10)
    
    def test_config_reset_all_configurations(self):
        """
        Test config reset command for all configurations.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Get original default values
        original_configs = {}
        for config in self.db_manager.list_config():
            original_configs[config.key] = config.get_typed_value()
        
        # Modify several configurations
        modifications = {
            'validation_mode': 'threshold_based',
            'default_output_format': 'json',
            'interactive_discovery': False,
            'price_tolerance': 0.15,
            'log_retention_days': 180
        }
        
        for key, value in modifications.items():
            self.db_manager.set_config_value(key, value)
        
        # Verify modifications were applied
        for key, expected_value in modifications.items():
            actual_value = self.db_manager.get_config_value(key)
            self.assertEqual(actual_value, expected_value)
        
        # Reset all configurations (simulates: config reset --all)
        all_configs = self.db_manager.list_config()
        for config in all_configs:
            if config.key in modifications:  # Only reset the ones we modified
                self.db_manager.reset_config_to_default(config.key)
        
        # Verify all configurations were reset to defaults
        for key in modifications.keys():
            if key in original_configs:
                reset_value = self.db_manager.get_config_value(key)
                original_value = original_configs[key]
                self.assertEqual(reset_value, original_value, 
                               f"Configuration '{key}' should be reset to original value")
    
    def test_config_error_handling_invalid_keys(self):
        """
        Test error handling for invalid configuration keys.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test getting non-existent configuration (simulates: config get nonexistent_key)
        with self.assertRaises(DatabaseError):
            self.db_manager.get_config_value('nonexistent_configuration_key')
        
        # Test getting non-existent configuration object
        with self.assertRaises(DatabaseError):
            self.db_manager.get_config('nonexistent_configuration_key')
        
        # Test resetting non-existent configuration
        with self.assertRaises(DatabaseError):
            self.db_manager.reset_config_to_default('nonexistent_configuration_key')
    
    def test_config_error_handling_invalid_values(self):
        """
        Test error handling for invalid configuration values.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test setting invalid boolean value
        with self.assertRaises(ValidationError):
            self.db_manager.set_config_value('interactive_discovery', 'invalid_boolean')
        
        # Test setting invalid number value
        with self.assertRaises(ValidationError):
            self.db_manager.set_config_value('price_tolerance', 'not_a_number')
        
        # Test setting negative value for positive-only configuration
        with self.assertRaises(ValidationError):
            self.db_manager.set_config_value('log_retention_days', -30)
        
        # Test setting invalid validation mode
        with self.assertRaises(ValidationError):
            self.db_manager.set_config_value('validation_mode', 'invalid_mode')
    
    def test_config_data_type_conversion(self):
        """
        Test configuration data type conversion and validation.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test string to boolean conversion
        self.db_manager.set_config_value('interactive_discovery', 'true')
        boolean_value = self.db_manager.get_config_value('interactive_discovery')
        self.assertTrue(boolean_value)
        self.assertIsInstance(boolean_value, bool)
        
        self.db_manager.set_config_value('interactive_discovery', 'false')
        boolean_value = self.db_manager.get_config_value('interactive_discovery')
        self.assertFalse(boolean_value)
        self.assertIsInstance(boolean_value, bool)
        
        # Test string to number conversion
        self.db_manager.set_config_value('price_tolerance', '0.025')
        number_value = self.db_manager.get_config_value('price_tolerance')
        self.assertEqual(number_value, 0.025)
        self.assertIsInstance(number_value, float)
        
        # Test integer to float conversion
        self.db_manager.set_config_value('price_tolerance', 1)
        number_value = self.db_manager.get_config_value('price_tolerance')
        self.assertEqual(number_value, 1.0)
        self.assertIsInstance(number_value, float)
    
    def test_config_persistence_across_sessions(self):
        """
        Test that configuration changes persist across database sessions.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Set some configuration values
        test_configs = {
            'validation_mode': 'threshold_based',
            'interactive_discovery': False,
            'price_tolerance': 0.075,
            'custom_persistent_test': 'persistent_value'
        }
        
        for key, value in test_configs.items():
            if key == 'custom_persistent_test':
                self.db_manager.set_config_value(key, value, data_type='string', category='test')
            else:
                self.db_manager.set_config_value(key, value)
        
        # Close database connection
        self.db_manager.close()
        
        # Reopen database with new manager instance
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Verify all configurations persisted
        for key, expected_value in test_configs.items():
            actual_value = self.db_manager.get_config_value(key)
            self.assertEqual(actual_value, expected_value, 
                           f"Configuration '{key}' should persist across sessions")
        
        # Verify data types are preserved
        validation_config = self.db_manager.get_config('validation_mode')
        self.assertEqual(validation_config.data_type, 'string')
        
        discovery_config = self.db_manager.get_config('interactive_discovery')
        self.assertEqual(discovery_config.data_type, 'boolean')
        
        tolerance_config = self.db_manager.get_config('price_tolerance')
        self.assertEqual(tolerance_config.data_type, 'number')
    
    def test_config_concurrent_access(self):
        """
        Test configuration management with concurrent database access.
        """
        import threading
        import time
        
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        results = []
        errors = []
        
        def config_operations():
            try:
                # Create separate database manager for this thread
                thread_db_manager = DatabaseManager(str(self.db_path))
                
                # Perform configuration operations
                thread_db_manager.set_config_value('concurrent_test', f'thread_value_{threading.current_thread().ident}')
                value = thread_db_manager.get_config_value('concurrent_test')
                results.append(value)
                
                # List configurations
                configs = thread_db_manager.list_config()
                results.append(len(configs))
                
                thread_db_manager.close()
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads performing configuration operations
        threads = []
        for i in range(3):
            thread = threading.Thread(target=config_operations)
            threads.append(thread)
            thread.start()
            time.sleep(0.01)  # Small delay to increase concurrency chance
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify results
        self.assertEqual(len(errors), 0, f"No errors should occur during concurrent access: {errors}")
        self.assertGreater(len(results), 0, "Should have results from concurrent operations")
        
        # Verify final configuration state is consistent
        final_configs = self.db_manager.list_config()
        self.assertGreater(len(final_configs), 0)


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)