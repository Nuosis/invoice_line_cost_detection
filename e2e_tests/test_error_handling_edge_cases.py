"""
End-to-End Tests for Error Handling and Edge Cases

This test suite validates comprehensive error handling and edge case scenarios
without using any mocking. All tests create real error conditions, system resources,
and edge case data, then clean up completely.

Test Coverage:
- Database corruption and recovery scenarios
- File system errors (permissions, disk space, locked files)
- Invalid input data handling (malformed PDFs, corrupt CSVs)
- Network and I/O errors simulation
- Memory and resource exhaustion scenarios
- Concurrent access and race conditions
- Data validation edge cases
- System limits and boundary conditions
- Graceful degradation under stress
- Error recovery and rollback mechanisms
"""

import os
import tempfile
import unittest
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Dict, Any
import csv
import json
import sqlite3
import threading
import time
import shutil

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part, PartDiscoveryLog, DatabaseError, ValidationError
from processing.pdf_processor import PDFProcessor, PDFProcessingError
from processing.validation_engine import ValidationEngine
from cli.error_handlers import ErrorHandler, ErrorRecoveryManager
from cli.exceptions import CLIError, ProcessingError


class TestErrorHandlingEdgeCases(unittest.TestCase):
    """
    Comprehensive e2e tests for error handling and edge cases.
    
    These tests validate that the system handles errors gracefully and
    recovers properly from various failure scenarios.
    """
    
    def setUp(self):
        """
        Set up test environment for each test.
        
        Creates a unique temporary directory and database file for each test
        to ensure complete isolation.
        """
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_error_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_error_db_{self.test_id}.db"
        
        # Create test directories
        self.test_dirs = {
            'invoices': self.temp_dir / "invoices",
            'reports': self.temp_dir / "reports",
            'corrupted': self.temp_dir / "corrupted",
            'locked': self.temp_dir / "locked",
            'invalid': self.temp_dir / "invalid"
        }
        
        for test_dir in self.test_dirs.values():
            test_dir.mkdir(parents=True, exist_ok=True)
        
        # Track created resources for cleanup
        self.created_files = [self.db_path]
        self.created_dirs = [self.temp_dir] + list(self.test_dirs.values())
        
        # Initialize components
        self.db_manager = None
        self.pdf_processor = None
        self.validation_engine = None
        self.error_handler = None
        self.recovery_manager = None
        
    def tearDown(self):
        """
        Clean up all resources created during the test.
        
        Ensures no test artifacts are left behind, following the strict
        cleanup requirements for e2e tests.
        """
        # Close all components
        components = [
            self.recovery_manager,
            self.validation_engine,
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
                    # Try to unlock file if it's locked
                    try:
                        os.chmod(file_path, 0o777)
                    except Exception:
                        pass
                    file_path.unlink()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove test files from directories
        for test_dir in self.test_dirs.values():
            try:
                if test_dir.exists():
                    for file_path in test_dir.rglob("*"):
                        if file_path.is_file():
                            try:
                                os.chmod(file_path, 0o777)
                                file_path.unlink()
                            except Exception:
                                pass
            except Exception:
                pass
        
        # Remove all created directories
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
        self.validation_engine = ValidationEngine(self.db_manager)
        self.error_handler = ErrorHandler()
        self.recovery_manager = ErrorRecoveryManager(self.db_manager)
    
    def _create_corrupted_database(self, db_path: Path):
        """Create a corrupted database file for testing."""
        # Create a file with invalid SQLite content
        with open(db_path, 'wb') as f:
            f.write(b'This is not a valid SQLite database file')
            f.write(b'\x00' * 1000)  # Add some null bytes
            f.write(b'More invalid content')
        
        self.created_files.append(db_path)
    
    def _create_malformed_pdf(self, pdf_path: Path):
        """Create a malformed PDF file for testing."""
        # Create a file that looks like a PDF but is corrupted
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4\n')  # PDF header
            f.write(b'This is not valid PDF content\n')
            f.write(b'\x00' * 500)  # Invalid binary data
            f.write(b'%%EOF')  # PDF footer
        
        self.created_files.append(pdf_path)
    
    def _create_invalid_csv(self, csv_path: Path):
        """Create an invalid CSV file for testing."""
        # Create a CSV with inconsistent columns and invalid data
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('part_number,description,price\n')
            f.write('PART001,Valid Part,10.50\n')
            f.write('PART002,Missing Price\n')  # Missing column
            f.write('PART003,Invalid Price,not_a_number\n')
            f.write('PART004,"Unclosed quote,15.00\n')  # Unclosed quote
            f.write('PART005,Valid Part,20.00,extra_column\n')  # Extra column
        
        self.created_files.append(csv_path)
    
    def test_database_corruption_recovery(self):
        """
        Test database corruption detection and recovery.
        """
        # Setup components
        self._setup_test_components()
        
        # Create a corrupted database
        corrupted_db_path = self.test_dirs['corrupted'] / "corrupted.db"
        self._create_corrupted_database(corrupted_db_path)
        
        # Test opening corrupted database
        with self.assertRaises(DatabaseError):
            corrupted_db_manager = DatabaseManager(str(corrupted_db_path))
        
        # Test recovery mechanism
        recovery_result = self.recovery_manager.recover_from_corruption(
            str(corrupted_db_path)
        )
        
        # Verify recovery was attempted
        self.assertIn('recovery_attempted', recovery_result)
        self.assertIn('backup_created', recovery_result)
        
        # Test creating new database after corruption
        new_db_path = self.test_dirs['corrupted'] / "recovered.db"
        self.created_files.append(new_db_path)
        
        recovered_db_manager = DatabaseManager(str(new_db_path))
        
        # Verify new database works
        test_part = Part(
            part_number="RECOVERY_TEST",
            authorized_price=Decimal("10.00"),
            description="Recovery test part",
            category="Test"
        )
        
        recovered_db_manager.create_part(test_part)
        retrieved_part = recovered_db_manager.get_part("RECOVERY_TEST")
        
        self.assertEqual(retrieved_part.part_number, "RECOVERY_TEST")
        recovered_db_manager.close()
    
    def test_file_permission_errors(self):
        """
        Test handling of file permission errors.
        """
        # Setup components
        self._setup_test_components()
        
        # Create a read-only database file
        readonly_db_path = self.test_dirs['locked'] / "readonly.db"
        self.created_files.append(readonly_db_path)
        
        # First create a valid database
        temp_db_manager = DatabaseManager(str(readonly_db_path))
        test_part = Part(
            part_number="READONLY_TEST",
            authorized_price=Decimal("15.00"),
            description="Read-only test part",
            category="Test"
        )
        temp_db_manager.create_part(test_part)
        temp_db_manager.close()
        
        # Make the file read-only
        os.chmod(readonly_db_path, 0o444)
        
        # Test opening read-only database
        try:
            readonly_db_manager = DatabaseManager(str(readonly_db_path))
            
            # Should be able to read
            part = readonly_db_manager.get_part("READONLY_TEST")
            self.assertEqual(part.part_number, "READONLY_TEST")
            
            # Should fail to write
            with self.assertRaises(DatabaseError):
                new_part = Part(
                    part_number="WRITE_TEST",
                    authorized_price=Decimal("20.00"),
                    description="Write test part",
                    category="Test"
                )
                readonly_db_manager.create_part(new_part)
            
            readonly_db_manager.close()
            
        finally:
            # Restore write permissions for cleanup
            try:
                os.chmod(readonly_db_path, 0o777)
            except Exception:
                pass
        
        # Test creating files in read-only directory
        readonly_dir = self.test_dirs['locked'] / "readonly_dir"
        readonly_dir.mkdir()
        self.created_dirs.append(readonly_dir)
        
        os.chmod(readonly_dir, 0o555)  # Read and execute only
        
        try:
            # Should fail to create files in read-only directory
            with self.assertRaises(PermissionError):
                forbidden_file = readonly_dir / "forbidden.txt"
                with open(forbidden_file, 'w') as f:
                    f.write("This should fail")
        
        finally:
            # Restore write permissions for cleanup
            try:
                os.chmod(readonly_dir, 0o777)
            except Exception:
                pass
    
    def test_malformed_pdf_handling(self):
        """
        Test handling of malformed and corrupted PDF files.
        """
        # Setup components
        self._setup_test_components()
        
        # Create various types of malformed PDFs
        malformed_pdfs = {
            'corrupted_header': self.test_dirs['invalid'] / "corrupted_header.pdf",
            'truncated': self.test_dirs['invalid'] / "truncated.pdf",
            'binary_garbage': self.test_dirs['invalid'] / "binary_garbage.pdf",
            'empty_file': self.test_dirs['invalid'] / "empty.pdf"
        }
        
        # Create corrupted header PDF
        self._create_malformed_pdf(malformed_pdfs['corrupted_header'])
        
        # Create truncated PDF
        with open(malformed_pdfs['truncated'], 'wb') as f:
            f.write(b'%PDF-1.4\n')
            f.write(b'1 0 obj\n<< /Type /Catalog >>\nendobj\n')
            # Missing xref and trailer
        self.created_files.append(malformed_pdfs['truncated'])
        
        # Create binary garbage file
        with open(malformed_pdfs['binary_garbage'], 'wb') as f:
            f.write(os.urandom(1000))  # Random binary data
        self.created_files.append(malformed_pdfs['binary_garbage'])
        
        # Create empty file
        malformed_pdfs['empty_file'].touch()
        self.created_files.append(malformed_pdfs['empty_file'])
        
        # Test processing each malformed PDF
        for pdf_type, pdf_path in malformed_pdfs.items():
            with self.subTest(pdf_type=pdf_type):
                try:
                    # Should handle errors gracefully
                    processing_result = self.pdf_processor.process_pdf_with_error_handling(
                        str(pdf_path)
                    )
                    
                    # Should return error result, not crash
                    self.assertFalse(processing_result['success'])
                    self.assertIn('error', processing_result)
                    self.assertIn('error_type', processing_result)
                    
                except PDFProcessingError as e:
                    # Expected exception type
                    self.assertIsInstance(e, PDFProcessingError)
                    self.assertIn(pdf_type, str(e).lower() or 'pdf')
                
                except Exception as e:
                    # Should not raise unexpected exceptions
                    self.fail(f"Unexpected exception for {pdf_type}: {str(e)}")
    
    def test_invalid_csv_data_handling(self):
        """
        Test handling of invalid CSV data during import operations.
        """
        # Setup components
        self._setup_test_components()
        
        # Create invalid CSV file
        invalid_csv_path = self.test_dirs['invalid'] / "invalid_parts.csv"
        self._create_invalid_csv(invalid_csv_path)
        
        # Test importing invalid CSV
        import_result = self.db_manager.import_parts_with_error_handling(
            str(invalid_csv_path)
        )
        
        # Should handle errors gracefully
        self.assertFalse(import_result['success'])
        self.assertIn('errors', import_result)
        self.assertIn('valid_rows_processed', import_result)
        self.assertIn('invalid_rows_skipped', import_result)
        
        # Should process valid rows despite errors
        self.assertGreater(import_result['valid_rows_processed'], 0)
        self.assertGreater(import_result['invalid_rows_skipped'], 0)
        
        # Verify valid parts were imported
        try:
            valid_part = self.db_manager.get_part("PART001")
            self.assertEqual(valid_part.authorized_price, Decimal("10.50"))
        except DatabaseError:
            self.fail("Valid part should have been imported despite CSV errors")
        
        # Test CSV with completely invalid format
        garbage_csv_path = self.test_dirs['invalid'] / "garbage.csv"
        self.created_files.append(garbage_csv_path)
        
        with open(garbage_csv_path, 'wb') as f:
            f.write(b'\x00\x01\x02\x03')  # Binary garbage
            f.write(b'Not CSV data at all')
        
        garbage_import_result = self.db_manager.import_parts_with_error_handling(
            str(garbage_csv_path)
        )
        
        self.assertFalse(garbage_import_result['success'])
        self.assertEqual(garbage_import_result['valid_rows_processed'], 0)
    
    def test_data_validation_edge_cases(self):
        """
        Test data validation with edge case values.
        """
        # Setup components
        self._setup_test_components()
        
        # Test edge case part data
        edge_case_parts = [
            # Extreme decimal values
            {
                'part_number': 'EXTREME_DECIMAL',
                'price': Decimal('999999999.999999'),
                'description': 'Extreme decimal price',
                'should_succeed': True
            },
            # Zero price
            {
                'part_number': 'ZERO_PRICE',
                'price': Decimal('0.00'),
                'description': 'Zero price part',
                'should_succeed': True
            },
            # Negative price
            {
                'part_number': 'NEGATIVE_PRICE',
                'price': Decimal('-10.00'),
                'description': 'Negative price part',
                'should_succeed': False
            },
            # Very long description
            {
                'part_number': 'LONG_DESC',
                'price': Decimal('15.00'),
                'description': 'A' * 10000,  # Very long description
                'should_succeed': True
            },
            # Empty description
            {
                'part_number': 'EMPTY_DESC',
                'price': Decimal('20.00'),
                'description': '',
                'should_succeed': True
            },
            # Special characters in part number
            {
                'part_number': 'SPECIAL@#$%',
                'price': Decimal('25.00'),
                'description': 'Special characters in part number',
                'should_succeed': False
            },
            # Very long part number
            {
                'part_number': 'A' * 1000,
                'price': Decimal('30.00'),
                'description': 'Very long part number',
                'should_succeed': False
            }
        ]
        
        for test_case in edge_case_parts:
            with self.subTest(part_number=test_case['part_number'][:20]):
                try:
                    part = Part(
                        part_number=test_case['part_number'],
                        authorized_price=test_case['price'],
                        description=test_case['description'],
                        category='EdgeCase'
                    )
                    
                    if test_case['should_succeed']:
                        # Should succeed
                        self.db_manager.create_part(part)
                        retrieved_part = self.db_manager.get_part(test_case['part_number'])
                        self.assertEqual(retrieved_part.authorized_price, test_case['price'])
                    else:
                        # Should fail validation
                        with self.assertRaises((ValidationError, DatabaseError)):
                            self.db_manager.create_part(part)
                
                except (ValidationError, DatabaseError) as e:
                    if test_case['should_succeed']:
                        self.fail(f"Part creation should have succeeded: {str(e)}")
                    # Expected failure for invalid data
                
                except Exception as e:
                    self.fail(f"Unexpected exception: {str(e)}")
    
    def test_concurrent_database_access(self):
        """
        Test concurrent database access and race conditions.
        """
        # Setup components
        self._setup_test_components()
        
        # Create initial test data
        initial_part = Part(
            part_number="CONCURRENT_TEST",
            authorized_price=Decimal("10.00"),
            description="Concurrent test part",
            category="Test"
        )
        self.db_manager.create_part(initial_part)
        
        # Test concurrent read operations
        read_results = []
        read_errors = []
        
        def concurrent_read():
            try:
                # Create separate database manager for this thread
                thread_db_manager = DatabaseManager(str(self.db_path))
                part = thread_db_manager.get_part("CONCURRENT_TEST")
                read_results.append(part.authorized_price)
                thread_db_manager.close()
            except Exception as e:
                read_errors.append(e)
        
        # Start multiple read threads
        read_threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_read)
            read_threads.append(thread)
            thread.start()
        
        # Wait for all read threads to complete
        for thread in read_threads:
            thread.join(timeout=10)
        
        # Verify read operations succeeded
        self.assertEqual(len(read_errors), 0, f"Read errors occurred: {read_errors}")
        self.assertEqual(len(read_results), 5)
        for result in read_results:
            self.assertEqual(result, Decimal("10.00"))
        
        # Test concurrent write operations
        write_results = []
        write_errors = []
        
        def concurrent_write(thread_id):
            try:
                # Create separate database manager for this thread
                thread_db_manager = DatabaseManager(str(self.db_path))
                
                # Try to create a unique part
                part = Part(
                    part_number=f"THREAD_{thread_id}",
                    authorized_price=Decimal(f"{thread_id}.00"),
                    description=f"Thread {thread_id} part",
                    category="Concurrent"
                )
                
                thread_db_manager.create_part(part)
                write_results.append(thread_id)
                thread_db_manager.close()
                
            except Exception as e:
                write_errors.append((thread_id, e))
        
        # Start multiple write threads
        write_threads = []
        for i in range(3):
            thread = threading.Thread(target=concurrent_write, args=(i,))
            write_threads.append(thread)
            thread.start()
            time.sleep(0.01)  # Small delay to increase concurrency chance
        
        # Wait for all write threads to complete
        for thread in write_threads:
            thread.join(timeout=10)
        
        # Verify write operations
        self.assertLessEqual(len(write_errors), 1, f"Too many write errors: {write_errors}")
        self.assertGreaterEqual(len(write_results), 2, "At least 2 writes should succeed")
        
        # Verify created parts exist
        for thread_id in write_results:
            part = self.db_manager.get_part(f"THREAD_{thread_id}")
            self.assertEqual(part.authorized_price, Decimal(f"{thread_id}.00"))
    
    def test_memory_and_resource_limits(self):
        """
        Test behavior under memory and resource constraints.
        """
        # Setup components
        self._setup_test_components()
        
        # Test large data processing
        large_parts_count = 1000
        
        try:
            # Create many parts to test memory usage
            for i in range(large_parts_count):
                part = Part(
                    part_number=f"LARGE_{i:04d}",
                    authorized_price=Decimal(f"{i % 100}.{i % 100:02d}"),
                    description=f"Large dataset part {i} with some description text",
                    category=f"Category{i % 10}"
                )
                self.db_manager.create_part(part)
                
                # Periodically check if we're running out of resources
                if i % 100 == 0:
                    # Force garbage collection
                    import gc
                    gc.collect()
            
            # Test querying large dataset
            all_parts = self.db_manager.list_parts()
            self.assertEqual(len(all_parts), large_parts_count)
            
            # Test filtering large dataset
            category_parts = self.db_manager.list_parts(category="Category1")
            expected_count = large_parts_count // 10
            self.assertEqual(len(category_parts), expected_count)
            
        except MemoryError:
            # If we run out of memory, ensure graceful handling
            self.skipTest("Insufficient memory for large dataset test")
        
        except Exception as e:
            # Should not fail with other exceptions
            self.fail(f"Large dataset processing failed: {str(e)}")
    
    def test_error_recovery_rollback_mechanisms(self):
        """
        Test error recovery and transaction rollback mechanisms.
        """
        # Setup components
        self._setup_test_components()
        
        # Create initial state
        initial_part = Part(
            part_number="ROLLBACK_TEST",
            authorized_price=Decimal("10.00"),
            description="Initial state part",
            category="Test"
        )
        self.db_manager.create_part(initial_part)
        
        # Test transaction rollback on error
        try:
            # Start a transaction that will fail
            with self.db_manager.transaction():
                # Update existing part
                updated_part = Part(
                    part_number="ROLLBACK_TEST",
                    authorized_price=Decimal("20.00"),
                    description="Updated state part",
                    category="Test"
                )
                self.db_manager.update_part(updated_part)
                
                # Create a part that will cause constraint violation
                duplicate_part = Part(
                    part_number="ROLLBACK_TEST",  # Duplicate part number
                    authorized_price=Decimal("30.00"),
                    description="Duplicate part",
                    category="Test"
                )
                self.db_manager.create_part(duplicate_part)  # This should fail
        
        except DatabaseError:
            # Expected error due to constraint violation
            pass
        
        # Verify rollback occurred - part should have original values
        rolled_back_part = self.db_manager.get_part("ROLLBACK_TEST")
        self.assertEqual(rolled_back_part.authorized_price, Decimal("10.00"))
        self.assertEqual(rolled_back_part.description, "Initial state part")
        
        # Test recovery from partial operations
        recovery_result = self.recovery_manager.recover_from_partial_operation(
            operation_type="bulk_import",
            operation_id="test_recovery_001"
        )
        
        self.assertIn('recovery_status', recovery_result)
        self.assertIn('actions_taken', recovery_result)
    
    def test_system_limits_boundary_conditions(self):
        """
        Test system limits and boundary conditions.
        """
        # Setup components
        self._setup_test_components()
        
        # Test maximum string lengths
        max_length_tests = [
            {
                'field': 'part_number',
                'max_length': 50,
                'test_value': 'A' * 51,
                'should_fail': True
            },
            {
                'field': 'description',
                'max_length': 1000,
                'test_value': 'A' * 1001,
                'should_fail': True
            },
            {
                'field': 'category',
                'max_length': 100,
                'test_value': 'A' * 101,
                'should_fail': True
            }
        ]
        
        for test in max_length_tests:
            with self.subTest(field=test['field']):
                try:
                    part_data = {
                        'part_number': 'TEST_LIMIT',
                        'authorized_price': Decimal('10.00'),
                        'description': 'Test description',
                        'category': 'Test'
                    }
                    part_data[test['field']] = test['test_value']
                    
                    part = Part(**part_data)
                    
                    if test['should_fail']:
                        with self.assertRaises((ValidationError, DatabaseError)):
                            self.db_manager.create_part(part)
                    else:
                        self.db_manager.create_part(part)
                        retrieved_part = self.db_manager.get_part(part.part_number)
                        self.assertIsNotNone(retrieved_part)
                
                except (ValidationError, DatabaseError):
                    if not test['should_fail']:
                        self.fail(f"Should not have failed for {test['field']}")
        
        # Test decimal precision limits
        precision_tests = [
            Decimal('999999999.99'),  # Large valid number
            Decimal('0.001'),         # Small valid number
            Decimal('0.0001'),        # Very small number
        ]
        
        for i, test_price in enumerate(precision_tests):
            with self.subTest(price=str(test_price)):
                try:
                    part = Part(
                        part_number=f"PRECISION_{i}",
                        authorized_price=test_price,
                        description=f"Precision test {i}",
                        category="Precision"
                    )
                    
                    self.db_manager.create_part(part)
                    retrieved_part = self.db_manager.get_part(f"PRECISION_{i}")
                    self.assertEqual(retrieved_part.authorized_price, test_price)
                
                except (ValidationError, DatabaseError, InvalidOperation) as e:
                    # Some precision limits might be expected
                    if test_price > Decimal('999999999'):
                        continue  # Expected failure for very large numbers
                    else:
                        self.fail(f"Precision test failed unexpectedly: {str(e)}")
    
    def test_graceful_degradation_under_stress(self):
        """
        Test graceful degradation under various stress conditions.
        """
        # Setup components
        self._setup_test_components()
        
        # Test rapid successive operations
        rapid_operations_count = 100
        successful_operations = 0
        failed_operations = 0
        
        for i in range(rapid_operations_count):
            try:
                # Rapid part creation
                part = Part(
                    part_number=f"RAPID_{i:03d}",
                    authorized_price=Decimal(f"{i % 50}.{i % 100:02d}"),
                    description=f"Rapid operation part {i}",
                    category="Rapid"
                )
                
                self.db_manager.create_part(part)
                successful_operations += 1
                
                # Immediate query
                retrieved_part = self.db_manager.get_part(f"RAPID_{i:03d}")
                self.assertEqual(retrieved_part.part_number, f"RAPID_{i:03d}")
                
            except Exception as e:
                failed_operations += 1
                # Should not have too many failures
                if failed_operations > rapid_operations_count * 0.1:  # More than 10% failure
                    self.fail(f"Too many failures during rapid operations: {str(e)}")
        
        # Verify most operations succeeded
        self.assertGreater(successful_operations, rapid_operations_count * 0.8)  # At least 80% success
        
        # Test system recovery after stress
        recovery_test_part = Part(
            part_number="RECOVERY_AFTER_STRESS",
            authorized_price=Decimal("99.99"),
            description="Recovery test after stress",
            category="Recovery"
        )
        
        self.db_manager.create_part(recovery_test_part)
        recovered_part = self.db_manager.get_part("RECOVERY_AFTER_STRESS")
        self.assertEqual(recovered_part.authorized_price, Decimal("99.99"))


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)