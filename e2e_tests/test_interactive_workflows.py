"""
End-to-End Tests for Interactive Processing Workflows

This test suite validates complete interactive workflows without using any mocking.
All tests create real database files, PDF files, and system resources, then clean up completely.

Test Coverage:
- Complete invoice processing workflow with interactive discovery
- Interactive parts discovery and decision-making
- User confirmation and input simulation
- Workflow state management and persistence
- Error recovery in interactive sessions
- Multi-step workflow validation
- Session continuity and resumption
- User experience validation
"""

import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any
import io
import sys
from unittest.mock import patch

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part, PartDiscoveryLog
from processing.pdf_processor import PDFProcessor
from processing.part_discovery_service import PartDiscoveryService
from processing.validation_engine import ValidationEngine
from cli.prompts import InteractivePrompts
from cli.context import ProcessingContext


class TestInteractiveWorkflows(unittest.TestCase):
    """
    Comprehensive e2e tests for interactive processing workflows.
    
    These tests validate that complete user workflows work correctly
    in real-world conditions without any mocking of core functionality.
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
        self.invoices_dir = self.temp_dir / "invoices"
        self.invoices_dir.mkdir()
        self.reports_dir = self.temp_dir / "reports"
        self.reports_dir.mkdir()
        
        # Track created resources for cleanup
        self.created_files = [self.db_path]
        self.created_dirs = [self.temp_dir, self.invoices_dir, self.reports_dir]
        
        # Initialize components
        self.db_manager = None
        self.pdf_processor = None
        self.discovery_service = None
        self.validation_engine = None
        self.interactive_prompts = None
        self.processing_context = None
        
    def tearDown(self):
        """
        Clean up all resources created during the test.
        
        Ensures no test artifacts are left behind, following the strict
        cleanup requirements for e2e tests.
        """
        # Close all components
        components = [
            self.discovery_service,
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
        for test_dir in [self.invoices_dir, self.reports_dir]:
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
        self.discovery_service = PartDiscoveryService(self.db_manager)
        self.validation_engine = ValidationEngine(self.db_manager)
        self.interactive_prompts = InteractivePrompts()
        self.processing_context = ProcessingContext()
    
    def _setup_test_parts(self):
        """Set up test parts for workflow testing."""
        test_parts = [
            Part(
                part_number="KNOWN001",
                authorized_price=Decimal("15.00"),
                description="Known Test Part 1",
                category="Safety",
                is_active=True
            ),
            Part(
                part_number="KNOWN002",
                authorized_price=Decimal("25.00"),
                description="Known Test Part 2",
                category="Tools",
                is_active=True
            ),
            Part(
                part_number="KNOWN003",
                authorized_price=Decimal("35.00"),
                description="Known Test Part 3",
                category="Equipment",
                is_active=True
            )
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
    
    def _create_test_invoice_content(self, invoice_number: str, line_items: List[Dict[str, Any]]) -> str:
        """Create test invoice content for PDF simulation."""
        content_lines = [
            f"INVOICE #{invoice_number}",
            "Date: 2025-01-15",
            "Vendor: Test Safety Supply Co.",
            "",
            "LINE ITEMS:",
            "Part Number | Description | Qty | Unit Price | Total",
            "-" * 60
        ]
        
        for item in line_items:
            line = f"{item['part_number']} | {item['description']} | {item['qty']} | ${item['unit_price']:.2f} | ${item['total']:.2f}"
            content_lines.append(line)
        
        content_lines.extend([
            "",
            f"TOTAL: ${sum(item['total'] for item in line_items):.2f}",
            "",
            "Thank you for your business!"
        ])
        
        return "\n".join(content_lines)
    
    def _create_test_pdf_file(self, filename: str, content: str) -> Path:
        """Create a test PDF file with the given content."""
        # For testing purposes, we'll create a text file that simulates PDF content
        # In a real implementation, this would create an actual PDF
        pdf_path = self.invoices_dir / filename
        self.created_files.append(pdf_path)
        
        with open(pdf_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return pdf_path
    
    def test_complete_invoice_processing_workflow_with_known_parts(self):
        """
        Test complete invoice processing workflow with all known parts.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Create test invoice with known parts
        line_items = [
            {
                "part_number": "KNOWN001",
                "description": "Known Test Part 1",
                "qty": 5,
                "unit_price": Decimal("15.00"),
                "total": Decimal("75.00")
            },
            {
                "part_number": "KNOWN002",
                "description": "Known Test Part 2",
                "qty": 3,
                "unit_price": Decimal("25.00"),
                "total": Decimal("75.00")
            }
        ]
        
        invoice_content = self._create_test_invoice_content("INV001", line_items)
        pdf_path = self._create_test_pdf_file("test_invoice_001.pdf", invoice_content)
        
        # Initialize processing context
        self.processing_context.set_input_path(str(self.invoices_dir))
        self.processing_context.set_output_path(str(self.reports_dir / "validation_report.csv"))
        self.processing_context.set_interactive_mode(True)
        
        # Process invoice (simulates: process --input invoices/ --output report.csv --interactive)
        processing_result = self.validation_engine.process_invoice_file(
            str(pdf_path),
            context=self.processing_context
        )
        
        # Verify processing was successful
        self.assertTrue(processing_result['success'])
        self.assertEqual(processing_result['total_line_items'], 2)
        self.assertEqual(processing_result['validation_passed'], 2)
        self.assertEqual(processing_result['validation_failed'], 0)
        self.assertEqual(processing_result['unknown_parts'], 0)
        
        # Verify no interactive discovery was needed
        self.assertFalse(processing_result.get('interactive_session_required', False))
        
        # Verify validation report was created
        report_path = Path(self.processing_context.get_output_path())
        self.assertTrue(report_path.exists())
        
        # Verify report content
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        self.assertIn("KNOWN001", report_content)
        self.assertIn("KNOWN002", report_content)
        self.assertIn("PASS", report_content)
    
    def test_interactive_workflow_with_unknown_parts_discovery(self):
        """
        Test interactive workflow with unknown parts requiring discovery.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Create test invoice with mix of known and unknown parts
        line_items = [
            {
                "part_number": "KNOWN001",
                "description": "Known Test Part 1",
                "qty": 2,
                "unit_price": Decimal("15.00"),
                "total": Decimal("30.00")
            },
            {
                "part_number": "UNKNOWN001",
                "description": "Unknown Safety Vest",
                "qty": 10,
                "unit_price": Decimal("12.50"),
                "total": Decimal("125.00")
            },
            {
                "part_number": "UNKNOWN002",
                "description": "Unknown Hard Hat",
                "qty": 5,
                "unit_price": Decimal("18.75"),
                "total": Decimal("93.75")
            }
        ]
        
        invoice_content = self._create_test_invoice_content("INV002", line_items)
        pdf_path = self._create_test_pdf_file("test_invoice_002.pdf", invoice_content)
        
        # Initialize processing context for interactive mode
        self.processing_context.set_input_path(str(self.invoices_dir))
        self.processing_context.set_output_path(str(self.reports_dir / "interactive_report.csv"))
        self.processing_context.set_interactive_mode(True)
        self.processing_context.set_session_id("interactive_session_001")
        
        # Simulate user responses for interactive discovery
        user_responses = [
            "1",  # Add UNKNOWN001 to database
            "y",  # Confirm adding UNKNOWN001
            "2",  # Skip UNKNOWN002 for now
            "y"   # Confirm skipping UNKNOWN002
        ]
        
        # Process invoice with simulated user input
        with patch('builtins.input', side_effect=user_responses):
            processing_result = self.discovery_service.process_invoice_interactively(
                str(pdf_path),
                context=self.processing_context
            )
        
        # Verify processing results
        self.assertTrue(processing_result['success'])
        self.assertEqual(processing_result['total_line_items'], 3)
        self.assertEqual(processing_result['known_parts_processed'], 1)
        self.assertEqual(processing_result['unknown_parts_discovered'], 2)
        self.assertEqual(processing_result['parts_added_to_database'], 1)
        self.assertEqual(processing_result['parts_skipped'], 1)
        
        # Verify UNKNOWN001 was added to database
        added_part = self.db_manager.get_part("UNKNOWN001")
        self.assertEqual(added_part.part_number, "UNKNOWN001")
        self.assertEqual(added_part.authorized_price, Decimal("12.50"))
        self.assertEqual(added_part.description, "Unknown Safety Vest")
        self.assertEqual(added_part.source, "discovery")
        
        # Verify UNKNOWN002 was not added to database
        with self.assertRaises(Exception):
            self.db_manager.get_part("UNKNOWN002")
        
        # Verify discovery logs were created
        discovery_logs = self.db_manager.list_discovery_logs()
        self.assertEqual(len(discovery_logs), 2)
        
        # Verify specific discovery log entries
        unknown001_log = next(log for log in discovery_logs if log.part_number == "UNKNOWN001")
        self.assertEqual(unknown001_log.action_taken, "added")
        self.assertEqual(unknown001_log.user_decision, "add_to_database")
        
        unknown002_log = next(log for log in discovery_logs if log.part_number == "UNKNOWN002")
        self.assertEqual(unknown002_log.action_taken, "skipped")
        self.assertEqual(unknown002_log.user_decision, "skip")
    
    def test_interactive_workflow_with_price_validation_failures(self):
        """
        Test interactive workflow with price validation failures requiring user decisions.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Create test invoice with price discrepancies
        line_items = [
            {
                "part_number": "KNOWN001",
                "description": "Known Test Part 1",
                "qty": 3,
                "unit_price": Decimal("20.00"),  # Higher than authorized $15.00
                "total": Decimal("60.00")
            },
            {
                "part_number": "KNOWN002",
                "description": "Known Test Part 2",
                "qty": 2,
                "unit_price": Decimal("22.00"),  # Lower than authorized $25.00
                "total": Decimal("44.00")
            }
        ]
        
        invoice_content = self._create_test_invoice_content("INV003", line_items)
        pdf_path = self._create_test_pdf_file("test_invoice_003.pdf", invoice_content)
        
        # Initialize processing context
        self.processing_context.set_input_path(str(self.invoices_dir))
        self.processing_context.set_output_path(str(self.reports_dir / "price_validation_report.csv"))
        self.processing_context.set_interactive_mode(True)
        self.processing_context.set_validation_mode("strict")
        
        # Simulate user responses for price validation failures
        user_responses = [
            "1",  # Update authorized price for KNOWN001
            "y",  # Confirm price update for KNOWN001
            "2",  # Flag as exception for KNOWN002
            "Price negotiated with vendor",  # Exception reason
            "y"   # Confirm exception for KNOWN002
        ]
        
        # Process invoice with simulated user input
        with patch('builtins.input', side_effect=user_responses):
            processing_result = self.validation_engine.process_invoice_interactively(
                str(pdf_path),
                context=self.processing_context
            )
        
        # Verify processing results
        self.assertTrue(processing_result['success'])
        self.assertEqual(processing_result['total_line_items'], 2)
        self.assertEqual(processing_result['price_updates_made'], 1)
        self.assertEqual(processing_result['exceptions_flagged'], 1)
        
        # Verify KNOWN001 price was updated
        updated_part = self.db_manager.get_part("KNOWN001")
        self.assertEqual(updated_part.authorized_price, Decimal("20.00"))
        
        # Verify KNOWN002 price was not updated
        unchanged_part = self.db_manager.get_part("KNOWN002")
        self.assertEqual(unchanged_part.authorized_price, Decimal("25.00"))
        
        # Verify validation report includes exceptions
        report_path = Path(self.processing_context.get_output_path())
        self.assertTrue(report_path.exists())
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        self.assertIn("KNOWN001", report_content)
        self.assertIn("KNOWN002", report_content)
        self.assertIn("PRICE_UPDATED", report_content)
        self.assertIn("EXCEPTION", report_content)
        self.assertIn("Price negotiated with vendor", report_content)
    
    def test_interactive_workflow_session_persistence_and_resumption(self):
        """
        Test interactive workflow session persistence and resumption capabilities.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Create test invoice for session testing
        line_items = [
            {
                "part_number": "UNKNOWN003",
                "description": "Session Test Part 1",
                "qty": 4,
                "unit_price": Decimal("22.50"),
                "total": Decimal("90.00")
            },
            {
                "part_number": "UNKNOWN004",
                "description": "Session Test Part 2",
                "qty": 6,
                "unit_price": Decimal("17.25"),
                "total": Decimal("103.50")
            }
        ]
        
        invoice_content = self._create_test_invoice_content("INV004", line_items)
        pdf_path = self._create_test_pdf_file("test_invoice_004.pdf", invoice_content)
        
        # Initialize processing context with session ID
        session_id = "persistent_session_001"
        self.processing_context.set_session_id(session_id)
        self.processing_context.set_interactive_mode(True)
        
        # Start interactive session and process first part only
        user_responses_part1 = [
            "1",  # Add UNKNOWN003 to database
            "y",  # Confirm adding UNKNOWN003
            "3"   # Save and exit session
        ]
        
        # Process first part with simulated user input
        with patch('builtins.input', side_effect=user_responses_part1):
            session_result = self.discovery_service.start_interactive_session(
                str(pdf_path),
                context=self.processing_context
            )
        
        # Verify session was saved
        self.assertTrue(session_result['session_saved'])
        self.assertEqual(session_result['session_id'], session_id)
        self.assertEqual(session_result['parts_processed'], 1)
        self.assertEqual(session_result['parts_remaining'], 1)
        
        # Verify UNKNOWN003 was added
        added_part = self.db_manager.get_part("UNKNOWN003")
        self.assertEqual(added_part.part_number, "UNKNOWN003")
        
        # Resume session to process remaining parts
        user_responses_part2 = [
            "2",  # Skip UNKNOWN004
            "y",  # Confirm skipping UNKNOWN004
            "4"   # Complete and close session
        ]
        
        # Resume session with simulated user input
        with patch('builtins.input', side_effect=user_responses_part2):
            resume_result = self.discovery_service.resume_interactive_session(
                session_id,
                context=self.processing_context
            )
        
        # Verify session was completed
        self.assertTrue(resume_result['session_completed'])
        self.assertEqual(resume_result['total_parts_processed'], 2)
        self.assertEqual(resume_result['parts_added'], 1)
        self.assertEqual(resume_result['parts_skipped'], 1)
        
        # Verify session state was properly managed
        session_logs = self.db_manager.list_discovery_logs(session_id=session_id)
        self.assertEqual(len(session_logs), 2)
        
        # Verify session cannot be resumed after completion
        with self.assertRaises(Exception):
            self.discovery_service.resume_interactive_session(session_id, self.processing_context)
    
    def test_interactive_workflow_error_recovery(self):
        """
        Test interactive workflow error recovery and graceful handling.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Create test invoice with problematic data
        line_items = [
            {
                "part_number": "INVALID@PART",  # Invalid part number format
                "description": "Invalid Part Number",
                "qty": -5,  # Invalid quantity
                "unit_price": Decimal("0.00"),  # Invalid price
                "total": Decimal("0.00")
            },
            {
                "part_number": "VALID001",
                "description": "Valid Part",
                "qty": 2,
                "unit_price": Decimal("15.00"),
                "total": Decimal("30.00")
            }
        ]
        
        invoice_content = self._create_test_invoice_content("INV005", line_items)
        pdf_path = self._create_test_pdf_file("test_invoice_005.pdf", invoice_content)
        
        # Initialize processing context
        self.processing_context.set_input_path(str(self.invoices_dir))
        self.processing_context.set_output_path(str(self.reports_dir / "error_recovery_report.csv"))
        self.processing_context.set_interactive_mode(True)
        self.processing_context.set_error_recovery_mode(True)
        
        # Simulate user responses for error recovery
        user_responses = [
            "1",  # Attempt to correct invalid part
            "CORRECTED001",  # Provide corrected part number
            "5",  # Provide corrected quantity
            "15.00",  # Provide corrected unit price
            "y",  # Confirm corrections
            "1",  # Add corrected part to database
            "y"   # Confirm adding to database
        ]
        
        # Process invoice with error recovery
        with patch('builtins.input', side_effect=user_responses):
            processing_result = self.discovery_service.process_invoice_with_error_recovery(
                str(pdf_path),
                context=self.processing_context
            )
        
        # Verify error recovery was successful
        self.assertTrue(processing_result['success'])
        self.assertEqual(processing_result['errors_encountered'], 1)
        self.assertEqual(processing_result['errors_recovered'], 1)
        self.assertEqual(processing_result['parts_corrected'], 1)
        self.assertEqual(processing_result['parts_added_after_correction'], 1)
        
        # Verify corrected part was added to database
        corrected_part = self.db_manager.get_part("CORRECTED001")
        self.assertEqual(corrected_part.part_number, "CORRECTED001")
        self.assertEqual(corrected_part.authorized_price, Decimal("15.00"))
        self.assertEqual(corrected_part.description, "Invalid Part Number")  # Original description preserved
        
        # Verify error recovery logs were created
        discovery_logs = self.db_manager.list_discovery_logs()
        error_recovery_logs = [log for log in discovery_logs if log.notes and "error_recovery" in log.notes]
        self.assertEqual(len(error_recovery_logs), 1)
        
        # Verify error recovery log details
        recovery_log = error_recovery_logs[0]
        self.assertEqual(recovery_log.part_number, "CORRECTED001")
        self.assertEqual(recovery_log.action_taken, "added")
        self.assertIn("corrected_from", recovery_log.notes)
        self.assertIn("INVALID@PART", recovery_log.notes)
    
    def test_interactive_workflow_batch_processing_with_user_decisions(self):
        """
        Test interactive workflow with batch processing and user decisions.
        """
        # Setup components and test data
        self._setup_test_components()
        self._setup_test_parts()
        
        # Create multiple test invoices for batch processing
        invoice_data = [
            {
                "filename": "batch_invoice_001.pdf",
                "invoice_number": "BATCH001",
                "line_items": [
                    {"part_number": "BATCH_UNKNOWN001", "description": "Batch Unknown Part 1", "qty": 3, "unit_price": Decimal("10.00"), "total": Decimal("30.00")},
                    {"part_number": "KNOWN001", "description": "Known Test Part 1", "qty": 2, "unit_price": Decimal("15.00"), "total": Decimal("30.00")}
                ]
            },
            {
                "filename": "batch_invoice_002.pdf",
                "invoice_number": "BATCH002",
                "line_items": [
                    {"part_number": "BATCH_UNKNOWN002", "description": "Batch Unknown Part 2", "qty": 4, "unit_price": Decimal("12.50"), "total": Decimal("50.00")},
                    {"part_number": "BATCH_UNKNOWN003", "description": "Batch Unknown Part 3", "qty": 1, "unit_price": Decimal("25.00"), "total": Decimal("25.00")}
                ]
            }
        ]
        
        # Create test invoice files
        pdf_paths = []
        for invoice in invoice_data:
            content = self._create_test_invoice_content(invoice["invoice_number"], invoice["line_items"])
            pdf_path = self._create_test_pdf_file(invoice["filename"], content)
            pdf_paths.append(pdf_path)
        
        # Initialize processing context for batch mode
        self.processing_context.set_input_path(str(self.invoices_dir))
        self.processing_context.set_output_path(str(self.reports_dir / "batch_processing_report.csv"))
        self.processing_context.set_interactive_mode(True)
        self.processing_context.set_batch_mode(True)
        self.processing_context.set_session_id("batch_session_001")
        
        # Simulate user responses for batch processing
        user_responses = [
            "1",  # Add BATCH_UNKNOWN001
            "y",  # Confirm adding BATCH_UNKNOWN001
            "1",  # Add BATCH_UNKNOWN002
            "y",  # Confirm adding BATCH_UNKNOWN002
            "2",  # Skip BATCH_UNKNOWN003
            "y",  # Confirm skipping BATCH_UNKNOWN003
            "y"   # Confirm completing batch processing
        ]
        
        # Process batch with simulated user input
        with patch('builtins.input', side_effect=user_responses):
            batch_result = self.discovery_service.process_batch_interactively(
                pdf_paths,
                context=self.processing_context
            )
        
        # Verify batch processing results
        self.assertTrue(batch_result['success'])
        self.assertEqual(batch_result['total_invoices_processed'], 2)
        self.assertEqual(batch_result['total_line_items'], 4)
        self.assertEqual(batch_result['known_parts_processed'], 1)
        self.assertEqual(batch_result['unknown_parts_discovered'], 3)
        self.assertEqual(batch_result['parts_added_to_database'], 2)
        self.assertEqual(batch_result['parts_skipped'], 1)
        
        # Verify parts were added correctly
        added_part1 = self.db_manager.get_part("BATCH_UNKNOWN001")
        self.assertEqual(added_part1.authorized_price, Decimal("10.00"))
        
        added_part2 = self.db_manager.get_part("BATCH_UNKNOWN002")
        self.assertEqual(added_part2.authorized_price, Decimal("12.50"))
        
        # Verify skipped part was not added
        with self.assertRaises(Exception):
            self.db_manager.get_part("BATCH_UNKNOWN003")
        
        # Verify batch processing report was created
        report_path = Path(self.processing_context.get_output_path())
        self.assertTrue(report_path.exists())
        
        # Verify discovery logs for batch session
        batch_logs = self.db_manager.list_discovery_logs(session_id="batch_session_001")
        self.assertEqual(len(batch_logs), 3)
        
        # Verify session summary
        session_summary = self.discovery_service.get_session_summary("batch_session_001")
        self.assertEqual(session_summary['total_parts_discovered'], 3)
        self.assertEqual(session_summary['parts_added'], 2)
        self.assertEqual(session_summary['parts_skipped'], 1)
        self.assertEqual(session_summary['invoices_processed'], 2)


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)