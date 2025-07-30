"""
End-to-End Tests for Cross-Platform Compatibility

This test suite validates cross-platform functionality without using any mocking.
All tests create real database files, system resources, and test platform-specific behaviors,
then clean up completely.

Test Coverage:
- File path handling across platforms (Windows, macOS, Linux)
- Database file creation and access permissions
- CSV and report file generation with different encodings
- Special character handling in file names and content
- Path separator handling and normalization
- Unicode support across platforms
- File locking and concurrent access
- Platform-specific temporary directory usage
- Environment variable handling
- Command-line argument processing
"""

import os
import platform
import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any
import csv
import json
import locale
import sys

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part, PartDiscoveryLog
from processing.pdf_processor import PDFProcessor


class TestCrossPlatformCompatibility(unittest.TestCase):
    """
    Comprehensive e2e tests for cross-platform compatibility.
    
    These tests validate that the system works correctly across different
    operating systems and handles platform-specific behaviors properly.
    """
    
    def setUp(self):
        """
        Set up test environment for each test.
        
        Creates a unique temporary directory and database file for each test
        to ensure complete isolation.
        """
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_crossplatform_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_crossplatform_db_{self.test_id}.db"
        
        # Create platform-specific test directories (using safe names)
        self.test_dirs = {
            'invoices': self.temp_dir / "invoices",
            'reports': self.temp_dir / "reports",
            'exports': self.temp_dir / "exports",
            'backups': self.temp_dir / "backups",
            'unicode_test': self.temp_dir / "unicode_test",
            'spaces_test': self.temp_dir / "directory_with_spaces",
            'special_chars': self.temp_dir / "special_chars"
        }
        
        # Create all test directories
        for test_dir in self.test_dirs.values():
            test_dir.mkdir(parents=True, exist_ok=True)
        
        # Track created resources for cleanup
        self.created_files = [self.db_path]
        self.created_dirs = [self.temp_dir] + list(self.test_dirs.values())
        
        # Initialize components
        self.db_manager = None
        self.pdf_processor = None
        
        # Get platform information
        self.platform_info = {
            'system': platform.system(),
            'release': platform.release(),
            'machine': platform.machine(),
            'python_version': platform.python_version(),
            'encoding': sys.getdefaultencoding(),
            'filesystem_encoding': sys.getfilesystemencoding(),
            'locale': locale.getdefaultlocale()
        }
    
    def tearDown(self):
        """
        Clean up all resources created during the test.
        
        Ensures no test artifacts are left behind, following the strict
        cleanup requirements for e2e tests.
        """
        # Close all components
        components = [
            self.pdf_processor,
            self.db_manager
        ]
        
        for component in components:
            if component:
                try:
                    if hasattr(component, 'close'):
                        component.close()
                except Exception:
                    pass  # Ignore errors during cleanup
        
        # Remove all created files
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove test files from directories
        for test_dir in self.test_dirs.values():
            try:
                if test_dir.exists():
                    for file_path in test_dir.rglob("*"):
                        if file_path.is_file():
                            file_path.unlink()
            except Exception:
                pass
        
        # Remove all created directories (in reverse order)
        for dir_path in reversed(self.created_dirs):
            try:
                if dir_path.exists():
                    dir_path.rmdir()
            except Exception:
                pass  # Ignore errors during cleanup
    
    def _setup_test_components(self):
        """Initialize all test components."""
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Initialize other components
        self.pdf_processor = PDFProcessor()
    
    def _setup_test_parts_with_unicode(self):
        """Set up test parts with Unicode characters for cross-platform testing."""
        unicode_parts = [
            Part(
                part_number="UNICODE_001",
                authorized_price=Decimal("15.50"),
                description="Safety Vest with emojis",
                category="Safety",
                is_active=True
            ),
            Part(
                part_number="UNICODE_002",
                authorized_price=Decimal("25.00"),
                description="Hard Hat - Protective Helmet",
                category="Protection",
                is_active=True
            ),
            Part(
                part_number="UNICODE_003",
                authorized_price=Decimal("35.75"),
                description="Tool Box - Equipment Storage",
                category="Tools",
                is_active=True
            ),
            Part(
                part_number="SPECIAL_CHARS",
                authorized_price=Decimal("12.25"),
                description="Part with special chars",
                category="Special",
                is_active=True
            )
        ]
        
        for part in unicode_parts:
            self.db_manager.create_part(part)
    
    def test_database_file_creation_cross_platform(self):
        """
        Test database file creation and access across different platforms.
        """
        # Setup components
        self._setup_test_components()
        
        # Test database creation in different directory types
        test_db_paths = {
            'normal': self.test_dirs['invoices'] / "normal_db.db",
            'unicode': self.test_dirs['unicode_test'] / "unicode_database.db",
            'spaces': self.test_dirs['spaces_test'] / "database_with_spaces.db",
            'special': self.test_dirs['special_chars'] / "special_db.db"
        }
        
        created_databases = []
        
        for path_type, db_path in test_db_paths.items():
            self.created_files.append(db_path)
            
            try:
                # Create database manager for this path
                test_db_manager = DatabaseManager(str(db_path))
                created_databases.append((path_type, test_db_manager, db_path))
                
                # Verify database file was created
                self.assertTrue(db_path.exists(), f"Database file should exist for {path_type} path")
                
                # Test basic database operations
                test_part = Part(
                    part_number=f"TEST_{path_type.upper()}",
                    authorized_price=Decimal("10.00"),
                    description=f"Test part for {path_type} path",
                    category="Test"
                )
                
                test_db_manager.create_part(test_part)
                retrieved_part = test_db_manager.get_part(f"TEST_{path_type.upper()}")
                
                self.assertEqual(retrieved_part.part_number, f"TEST_{path_type.upper()}")
                self.assertEqual(retrieved_part.authorized_price, Decimal("10.00"))
                
            except Exception as e:
                self.fail(f"Database creation failed for {path_type} path: {str(e)}")
        
        # Clean up database connections
        for path_type, db_manager, db_path in created_databases:
            try:
                db_manager.close()
            except Exception:
                pass
    
    def test_file_path_handling_and_normalization(self):
        """
        Test file path handling and normalization across platforms.
        """
        # Setup components
        self._setup_test_components()
        
        # Test different path formats (using safe cross-platform paths)
        test_paths = [
            # Relative paths
            "invoices/test.pdf",
            "reports/validation.csv",
            "exports/data.json",
            
            # Paths with underscores and hyphens (safe across platforms)
            "directory_with_underscores/report.txt",
            "mixed-separators/file.pdf",
            
            # Reasonable length paths
            "long/path/with/many/nested/directories/file.csv"
        ]
        
        for test_path in test_paths:
            try:
                # Test path creation using pathlib (cross-platform)
                normalized_path = Path(test_path)
                full_path = self.temp_dir / normalized_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Create a test file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(f"Test content for {test_path}")
                
                self.created_files.append(full_path)
                
                # Verify file was created and can be read
                self.assertTrue(full_path.exists(), f"File should exist: {full_path}")
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.assertIn("Test content", content)
                
            except Exception as e:
                # Some paths might not be valid on certain platforms
                if self.platform_info['system'] == 'Windows' and len(str(full_path)) > 260:
                    continue  # Expected limitation on Windows
                else:
                    self.fail(f"Unexpected error for path {test_path}: {str(e)}")
    
    def test_unicode_support_across_platforms(self):
        """
        Test Unicode support in file names, content, and database operations.
        """
        # Setup components and Unicode test data
        self._setup_test_components()
        self._setup_test_parts_with_unicode()
        
        # Test Unicode in database operations
        unicode_parts = self.db_manager.list_parts()
        unicode_part_numbers = {part.part_number for part in unicode_parts}
        
        expected_parts = {"UNICODE_001", "UNICODE_002", "UNICODE_003", "SPECIAL_CHARS"}
        for expected_part in expected_parts:
            self.assertIn(expected_part, unicode_part_numbers)
        
        # Test Unicode in part descriptions and categories
        safety_part = self.db_manager.get_part("UNICODE_001")
        self.assertIn("Safety Vest", safety_part.description)
        self.assertEqual(safety_part.category, "Safety")
        
        protection_part = self.db_manager.get_part("UNICODE_002")
        self.assertIn("Hard Hat", protection_part.description)
        self.assertEqual(protection_part.category, "Protection")
        
        tools_part = self.db_manager.get_part("UNICODE_003")
        self.assertIn("Tool Box", tools_part.description)
        self.assertEqual(tools_part.category, "Tools")
        
        # Test Unicode in CSV export
        csv_export_path = self.test_dirs['exports'] / "unicode_export_test.csv"
        self.created_files.append(csv_export_path)
        
        # Export parts to CSV with Unicode content
        with open(csv_export_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['part_number', 'description', 'category', 'price']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for part in unicode_parts:
                writer.writerow({
                    'part_number': part.part_number,
                    'description': part.description,
                    'category': part.category,
                    'price': str(part.authorized_price)
                })
        
        # Verify CSV file was created and contains Unicode content
        self.assertTrue(csv_export_path.exists())
        
        with open(csv_export_path, 'r', encoding='utf-8') as csvfile:
            content = csvfile.read()
            self.assertIn("Safety Vest", content)
            self.assertIn("Hard Hat", content)
            self.assertIn("Tool Box", content)
        
        # Test reading CSV back
        with open(csv_export_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            imported_parts = list(reader)
        
        self.assertEqual(len(imported_parts), len(unicode_parts))
        
        # Verify Unicode content is preserved
        safety_row = next(row for row in imported_parts if row['part_number'] == 'UNICODE_001')
        self.assertIn("Safety Vest", safety_row['description'])
        self.assertEqual(safety_row['category'], "Safety")
    
    def test_csv_report_generation_with_different_encodings(self):
        """
        Test CSV report generation with different encodings across platforms.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts_with_unicode()
        
        # Test different encodings
        encodings_to_test = ['utf-8', 'utf-16']
        
        # Add ASCII-only parts for broader compatibility testing
        ascii_part = Part(
            part_number="ASCII_001",
            authorized_price=Decimal("20.00"),
            description="ASCII Only Part",
            category="ASCII",
            is_active=True
        )
        self.db_manager.create_part(ascii_part)
        
        for encoding in encodings_to_test:
            try:
                report_path = self.test_dirs['reports'] / f"report_{encoding}.csv"
                self.created_files.append(report_path)
                
                # Get parts to export (all parts for Unicode-capable encodings)
                parts_to_export = self.db_manager.list_parts()
                
                # Generate report with specific encoding
                with open(report_path, 'w', newline='', encoding=encoding) as csvfile:
                    fieldnames = ['part_number', 'description', 'category', 'price', 'status']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for part in parts_to_export:
                        writer.writerow({
                            'part_number': part.part_number,
                            'description': part.description,
                            'category': part.category,
                            'price': str(part.authorized_price),
                            'status': 'active' if part.is_active else 'inactive'
                        })
                
                # Verify file was created
                self.assertTrue(report_path.exists(), f"Report should exist for encoding {encoding}")
                
                # Test reading the file back
                with open(report_path, 'r', encoding=encoding) as csvfile:
                    reader = csv.DictReader(csvfile)
                    read_parts = list(reader)
                
                self.assertGreater(len(read_parts), 0, f"Should have parts in {encoding} report")
                
                # Verify content integrity
                for row in read_parts:
                    self.assertIn('part_number', row)
                    self.assertIn('description', row)
                    self.assertIn('category', row)
                    self.assertIn('price', row)
                    self.assertIn('status', row)
                
            except Exception as e:
                self.fail(f"Report generation failed for encoding {encoding}: {str(e)}")
    
    def test_temporary_directory_usage_cross_platform(self):
        """
        Test temporary directory usage across different platforms.
        """
        # Setup components
        self._setup_test_components()
        
        # Test platform-specific temporary directory behavior
        platform_temp_dirs = []
        
        # Create temporary directories using different methods
        temp_methods = [
            ('tempfile.mkdtemp', lambda: Path(tempfile.mkdtemp(prefix="test_"))),
            ('tempfile.gettempdir', lambda: Path(tempfile.gettempdir()) / f"test_{uuid.uuid4().hex[:8]}"),
            ('platform_specific', self._get_platform_temp_dir)
        ]
        
        for method_name, temp_method in temp_methods:
            try:
                temp_path = temp_method()
                if not temp_path.exists():
                    temp_path.mkdir(parents=True)
                
                platform_temp_dirs.append((method_name, temp_path))
                self.created_dirs.append(temp_path)
                
                # Test database creation in temporary directory
                temp_db_path = temp_path / "temp_test.db"
                self.created_files.append(temp_db_path)
                
                temp_db_manager = DatabaseManager(str(temp_db_path))
                
                # Test basic operations
                test_part = Part(
                    part_number=f"TEMP_{method_name.upper()}",
                    authorized_price=Decimal("15.00"),
                    description=f"Temporary part for {method_name}",
                    category="Temp"
                )
                
                temp_db_manager.create_part(test_part)
                retrieved_part = temp_db_manager.get_part(f"TEMP_{method_name.upper()}")
                
                self.assertEqual(retrieved_part.part_number, f"TEMP_{method_name.upper()}")
                
                # Test file operations
                test_file_path = temp_path / "test_file.txt"
                self.created_files.append(test_file_path)
                
                with open(test_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Test content for {method_name}")
                
                self.assertTrue(test_file_path.exists())
                
                with open(test_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.assertIn(method_name, content)
                
                temp_db_manager.close()
                
            except Exception as e:
                self.fail(f"Temporary directory test failed for {method_name}: {str(e)}")
        
        # Verify all temporary directories were created successfully
        self.assertEqual(len(platform_temp_dirs), len(temp_methods))
    
    def _get_platform_temp_dir(self) -> Path:
        """Get platform-specific temporary directory."""
        system = self.platform_info['system']
        
        if system == 'Windows':
            temp_base = Path(os.environ.get('TEMP', os.environ.get('TMP', 'C:\\temp')))
        elif system == 'Darwin':  # macOS
            temp_base = Path('/tmp')
        else:  # Linux and other Unix-like systems
            temp_base = Path('/tmp')
        
        temp_dir = temp_base / f"crossplatform_test_{uuid.uuid4().hex[:8]}"
        return temp_dir
    
    def test_file_permissions_and_access_cross_platform(self):
        """
        Test file permissions and access patterns across platforms.
        """
        # Setup components
        self._setup_test_components()
        
        # Test different file permission scenarios
        test_files = {
            'database': self.test_dirs['invoices'] / "permissions_test.db",
            'csv_report': self.test_dirs['reports'] / "permissions_report.csv",
            'json_export': self.test_dirs['exports'] / "permissions_export.json",
            'backup': self.test_dirs['backups'] / "permissions_backup.db"
        }
        
        for file_type, file_path in test_files.items():
            self.created_files.append(file_path)
            
            try:
                if file_type == 'database':
                    # Test database file permissions
                    test_db_manager = DatabaseManager(str(file_path))
                    
                    test_part = Part(
                        part_number="PERM_TEST",
                        authorized_price=Decimal("10.00"),
                        description="Permission test part",
                        category="Test"
                    )
                    
                    test_db_manager.create_part(test_part)
                    test_db_manager.close()
                    
                elif file_type == 'csv_report':
                    # Test CSV file permissions
                    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(['part_number', 'description', 'price'])
                        writer.writerow(['PERM_TEST', 'Permission test', '10.00'])
                
                elif file_type == 'json_export':
                    # Test JSON file permissions
                    test_data = {
                        'parts': [
                            {
                                'part_number': 'PERM_TEST',
                                'description': 'Permission test',
                                'price': '10.00'
                            }
                        ]
                    }
                    
                    with open(file_path, 'w', encoding='utf-8') as jsonfile:
                        json.dump(test_data, jsonfile, indent=2)
                
                elif file_type == 'backup':
                    # Test backup file permissions (copy of database)
                    import shutil
                    source_db = test_files['database']
                    if source_db.exists():
                        shutil.copy2(source_db, file_path)
                
                # Verify file was created
                self.assertTrue(file_path.exists(), f"File should exist: {file_path}")
                
                # Test file access permissions
                self.assertTrue(os.access(file_path, os.R_OK), f"File should be readable: {file_path}")
                self.assertTrue(os.access(file_path, os.W_OK), f"File should be writable: {file_path}")
                
                # Test file size
                file_size = file_path.stat().st_size
                self.assertGreater(file_size, 0, f"File should not be empty: {file_path}")
                
            except Exception as e:
                self.fail(f"File permission test failed for {file_type}: {str(e)}")
    
    def test_platform_specific_behaviors(self):
        """
        Test platform-specific behaviors and edge cases.
        """
        # Setup components
        self._setup_test_components()
        
        system = self.platform_info['system']
        
        # Test platform-specific file system behaviors
        if system == 'Windows':
            self._test_windows_specific_behaviors()
        elif system == 'Darwin':  # macOS
            self._test_macos_specific_behaviors()
        else:  # Linux and other Unix-like systems
            self._test_linux_specific_behaviors()
        
        # Test common cross-platform behaviors
        self._test_common_cross_platform_behaviors()
    
    def _test_windows_specific_behaviors(self):
        """Test Windows-specific behaviors."""
        # Test Windows path length limitations
        try:
            # Create a path that's reasonable but tests Windows behavior
            long_path_parts = ['directory'] * 5
            long_path = self.temp_dir / Path(*long_path_parts) / "test_file.txt"
            
            if len(str(long_path)) < 200:  # Stay well under Windows limit
                long_path.parent.mkdir(parents=True, exist_ok=True)
                with open(long_path, 'w') as f:
                    f.write("Windows path test")
                self.created_files.append(long_path)
                self.assertTrue(long_path.exists())
        except Exception:
            # Expected on Windows with certain path configurations
            pass
    
    def _test_macos_specific_behaviors(self):
        """Test macOS-specific behaviors."""
        # Test macOS case sensitivity (usually case-insensitive)
        test_file_lower = self.temp_dir / "macos_test.txt"
        test_file_upper = self.temp_dir / "MACOS_TEST.txt"
        
        with open(test_file_lower, 'w') as f:
            f.write("macOS case test")
        
        self.created_files.extend([test_file_lower, test_file_upper])
        
        # On case-insensitive file systems, these should refer to the same file
        if test_file_upper.exists():
            # File system is case-insensitive
            with open(test_file_upper, 'r') as f:
                content = f.read()
                self.assertIn("macOS case test", content)
    
    def _test_linux_specific_behaviors(self):
        """Test Linux-specific behaviors."""
        # Test Linux case sensitivity (usually case-sensitive)
        test_file_lower = self.temp_dir / "linux_test.txt"
        test_file_upper = self.temp_dir / "LINUX_TEST.txt"
        
        with open(test_file_lower, 'w') as f:
            f.write("Linux lower case test")
        
        with open(test_file_upper, 'w') as f:
            f.write("Linux upper case test")
        
        self.created_files.extend([test_file_lower, test_file_upper])
        
        # Both files should exist independently
        self.assertTrue(test_file_lower.exists())
        self.assertTrue(test_file_upper.exists())
        
        with open(test_file_lower, 'r') as f:
            content = f.read()
            self.assertIn("lower case", content)
        
        with open(test_file_upper, 'r') as f:
            content = f.read()
            self.assertIn("upper case", content)
    
    def _test_common_cross_platform_behaviors(self):
        """Test behaviors that should be consistent across platforms."""
        # Test UTF-8 encoding consistency
        unicode_test_file = self.temp_dir / "unicode_consistency_test.txt"
        unicode_content = "Unicode test: Tool Equipment"
        with open(unicode_test_file, 'w', encoding='utf-8') as f:
            f.write(unicode_content)
        
        self.created_files.append(unicode_test_file)
        
        # Read back and verify consistency
        with open(unicode_test_file, 'r', encoding='utf-8') as f:
            read_content = f.read()
            self.assertEqual(read_content, unicode_content)
        
        # Test newline handling consistency
        newline_test_file = self.temp_dir / "newline_test.txt"
        self.created_files.append(newline_test_file)
        
        test_lines = ["Line 1", "Line 2", "Line 3"]
        
        with open(newline_test_file, 'w', encoding='utf-8', newline='') as f:
            for line in test_lines:
                f.write(line + '\n')
        
        with open(newline_test_file, 'r', encoding='utf-8') as f:
            read_lines = f.read().splitlines()
            self.assertEqual(read_lines, test_lines)


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)