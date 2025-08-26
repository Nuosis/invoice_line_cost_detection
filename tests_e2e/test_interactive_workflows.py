"""
End-to-End Tests for Interactive Processing Workflows

This test suite validates complete interactive workflows without using any mocking.
All tests use REAL invoice PDFs, REAL database operations, and REAL system components.

Test Coverage:
- Complete invoice processing workflow with real PDFs
- Real parts discovery from actual invoice data
- Real database operations and validation
- Real file system operations
- Real PDF processing with actual invoice files
"""

import tempfile
import unittest
import uuid
import shutil
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part
from processing.pdf_processor import PDFProcessor
from processing.validation_engine import ValidationEngine


class TestInteractiveWorkflows(unittest.TestCase):
    """
    Comprehensive e2e tests for interactive processing workflows.
    
    These tests validate that complete user workflows work correctly
    with real invoice PDFs and real system components.
    """
    
    def setUp(self):
        """
        Set up test environment for each test.
        
        Creates a unique temporary directory and database file for each test
        to ensure complete isolation.
        """
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_interactive_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_interactive_db_{self.test_id}.db"
        
        # Create directories for test files
        self.reports_dir = self.temp_dir / "reports"
        self.reports_dir.mkdir()
        
        # Track created resources for cleanup
        self.created_files = [self.db_path]
        self.created_dirs = [self.temp_dir, self.reports_dir]
        
        # Initialize components
        self.db_manager = None
        self.pdf_processor = None
        self.validation_engine = None
        
        # Get path to real invoice PDFs
        self.invoice_dir = Path(__file__).parent.parent / "docs" / "invoices"
        self.assertTrue(self.invoice_dir.exists(), f"Invoice directory not found: {self.invoice_dir}")
        
        # Verify we have real invoice PDFs to test with
        self.invoice_files = list(self.invoice_dir.glob("*.pdf"))
        self.assertGreater(len(self.invoice_files), 0, "No invoice PDF files found for testing")
        
    def tearDown(self):
        """
        Clean up all resources created during the test.
        
        Ensures no test artifacts are left behind, following the strict
        cleanup requirements for e2e tests.
        """
        # Close all components
        components = [
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
                    file_path.unlink()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove test files from directories
        for test_dir in [self.reports_dir]:
            try:
                if test_dir.exists():
                    for file_path in test_dir.glob("*"):
                        if file_path.is_file():
                            file_path.unlink()
            except Exception:
                pass
        
        # Remove all created directories
        for dir_path in reversed(self.created_dirs):  # Remove in reverse order
            try:
                if dir_path.exists():
                    dir_path.rmdir()
            except Exception:
                pass  # Ignore errors during cleanup
    
    def _setup_test_components(self):
        """Initialize all test components."""
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Initialize processing components
        self.pdf_processor = PDFProcessor()
        self.validation_engine = ValidationEngine(self.db_manager)
    
    def _setup_test_parts(self):
        """Set up test parts for workflow testing."""
        test_parts = [
            Part(
                part_number="GP0171NAVY",
                authorized_price=Decimal("0.300"),
                description="PANT WORK DURAPRES COTTON",
                category="Garments",
                is_active=True
            ),
            Part(
                part_number="GS0448",
                authorized_price=Decimal("0.300"),
                description="SHIRT WORK LS BTN COTTON",
                category="Garments",
                is_active=True
            ),
            Part(
                part_number="TEST_KNOWN_PART",
                authorized_price=Decimal("15.00"),
                description="Test Known Part",
                category="Test",
                is_active=True
            )
        ]
        
        for part in test_parts:
            try:
                self.db_manager.create_part(part)
            except Exception:
                # Part might already exist, continue
                pass
    
    def test_complete_invoice_processing_workflow_with_real_pdfs(self):
        """
        Test complete invoice processing workflow with real PDF files.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Use the first available real invoice PDF
        test_invoice = self.invoice_files[0]
        self.assertTrue(test_invoice.exists(), f"Test invoice not found: {test_invoice}")
        
        # Process the real invoice
        try:
            invoice_data = self.pdf_processor.process_pdf(test_invoice)
            self.assertIsNotNone(invoice_data, "Failed to extract data from real invoice PDF")
            
            # Verify we extracted line items
            line_items = invoice_data.get_valid_line_items()
            self.assertGreater(len(line_items), 0, "No line items extracted from real invoice")
            
            # Validate the invoice using the validation engine
            validation_result = self.validation_engine.validate_invoice(test_invoice)
            self.assertIsNotNone(validation_result, "Validation result should not be None")
            self.assertTrue(validation_result.processing_successful, "Invoice processing should succeed")
            
            # Verify we have validation results
            total_results = (
                len(validation_result.pre_validation_results) +
                len(validation_result.data_quality_results) +
                len(validation_result.format_validation_results) +
                len(validation_result.parts_lookup_results) +
                len(validation_result.price_validation_results) +
                len(validation_result.business_rules_results)
            )
            self.assertGreater(total_results, 0, "Should have validation results")
            
        except Exception as e:
            self.fail(f"Failed to process real invoice {test_invoice}: {e}")
    
    def test_batch_processing_with_real_invoices(self):
        """
        Test batch processing with multiple real invoice files.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Use up to 3 real invoice files for batch testing
        test_invoices = self.invoice_files[:3]
        self.assertGreater(len(test_invoices), 0, "Need at least one invoice for batch testing")
        
        # Process batch of real invoices
        try:
            validation_results = self.validation_engine.validate_batch(test_invoices)
            
            # Verify we got results for each invoice
            self.assertEqual(len(validation_results), len(test_invoices), 
                           "Should get validation result for each invoice")
            
            # Verify at least some processing was successful
            successful_count = sum(1 for r in validation_results if r.processing_successful)
            self.assertGreater(successful_count, 0, "At least some invoices should process successfully")
            
            # Verify each result has basic required fields
            for result in validation_results:
                self.assertIsNotNone(result.invoice_path, "Invoice path should be set")
                self.assertIsNotNone(result.processing_session_id, "Session ID should be set")
                self.assertIsNotNone(result.processing_start_time, "Start time should be set")
                self.assertIsNotNone(result.processing_end_time, "End time should be set")
                
        except Exception as e:
            self.fail(f"Failed to process batch of real invoices: {e}")
    
    def test_parts_discovery_with_real_invoice_data(self):
        """
        Test parts discovery functionality with real invoice data.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Use a real invoice for discovery testing
        test_invoice = self.invoice_files[0]
        
        try:
            # Extract data from real invoice
            invoice_data = self.pdf_processor.process_pdf(test_invoice)
            self.assertIsNotNone(invoice_data, "Should extract data from real invoice")
            
            line_items = invoice_data.get_valid_line_items()
            self.assertGreater(len(line_items), 0, "Should have line items from real invoice")
            
            # Check which parts are unknown (not in our test database)
            unknown_parts = []
            known_parts = []
            
            for line_item in line_items:
                if line_item.item_code:
                    try:
                        self.db_manager.get_part(line_item.item_code)
                        known_parts.append(line_item.item_code)
                    except Exception:
                        unknown_parts.append(line_item.item_code)
            
            # We should have some parts (either known or unknown)
            total_parts = len(known_parts) + len(unknown_parts)
            self.assertGreater(total_parts, 0, "Should find parts in real invoice data")
            
            # If we have unknown parts, verify we can add them to database
            if unknown_parts:
                # Take the first unknown part and add it to database
                unknown_part_code = unknown_parts[0]
                
                # Find the line item for this part
                unknown_line_item = next(
                    (item for item in line_items if item.item_code == unknown_part_code),
                    None
                )
                self.assertIsNotNone(unknown_line_item, "Should find line item for unknown part")
                
                # Create a new part from the discovered data
                new_part = Part(
                    part_number=unknown_part_code,
                    authorized_price=unknown_line_item.rate or Decimal("1.00"),
                    description=unknown_line_item.description or "Discovered from invoice",
                    category="Discovered",
                    source="discovered",
                    is_active=True
                )
                
                # Add to database
                created_part = self.db_manager.create_part(new_part)
                self.assertEqual(created_part.part_number, unknown_part_code)
                
                # Verify we can retrieve it
                retrieved_part = self.db_manager.get_part(unknown_part_code)
                self.assertEqual(retrieved_part.part_number, unknown_part_code)
                
        except Exception as e:
            self.fail(f"Failed parts discovery test with real invoice: {e}")
    
    def test_validation_with_real_invoice_data(self):
        """
        Test validation functionality with real invoice data and known parts.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Use a real invoice for validation testing
        test_invoice = self.invoice_files[0]
        
        try:
            # Process the invoice and get validation results
            validation_result = self.validation_engine.validate_invoice(test_invoice)
            self.assertIsNotNone(validation_result, "Should get validation result")
            
            # Verify basic validation structure
            self.assertIsNotNone(validation_result.invoice_path, "Invoice path should be set")
            self.assertTrue(validation_result.processing_successful, "Processing should succeed")
            
            # Check that we have some validation results
            has_results = (
                len(validation_result.pre_validation_results) > 0 or
                len(validation_result.data_quality_results) > 0 or
                len(validation_result.format_validation_results) > 0 or
                len(validation_result.parts_lookup_results) > 0 or
                len(validation_result.price_validation_results) > 0 or
                len(validation_result.business_rules_results) > 0
            )
            self.assertTrue(has_results, "Should have some validation results")
            
            # Test validation error categorization (v2.0 streamlined)
            total_errors = (
                len(validation_result.critical_anomalies) +
                len(validation_result.warning_anomalies) +
                len(validation_result.informational_anomalies)
            )
            
            # We might have anomalies (unknown parts, price discrepancies, etc.)
            # This is normal for real invoice data
            
            # Verify timing information
            self.assertIsNotNone(validation_result.processing_start_time)
            self.assertIsNotNone(validation_result.processing_end_time)
            self.assertGreater(validation_result.processing_duration, 0)
            
        except Exception as e:
            self.fail(f"Failed validation test with real invoice: {e}")
    
    def test_report_generation_with_real_data(self):
        """
        Test report generation with real invoice processing results.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Use a real invoice for report testing
        test_invoice = self.invoice_files[0]
        report_path = self.reports_dir / "test_validation_report.csv"
        
        try:
            # Process the invoice
            validation_result = self.validation_engine.validate_invoice(test_invoice)
            self.assertTrue(validation_result.processing_successful, "Processing should succeed")
            
            # For this test, we'll verify that the validation result contains
            # the data needed for report generation
            
            # Verify we have invoice metadata
            self.assertIsNotNone(validation_result.invoice_path)
            
            # Verify we have timing information
            self.assertIsNotNone(validation_result.processing_start_time)
            self.assertIsNotNone(validation_result.processing_end_time)
            
            # Verify we can get summary statistics
            summary = validation_result.get_summary_statistics()
            self.assertIsInstance(summary, dict, "Should get summary statistics")
            
            # The actual report generation would be handled by the CLI layer
            # Here we just verify the data is available for reporting
            
        except Exception as e:
            self.fail(f"Failed report generation test with real invoice: {e}")


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)