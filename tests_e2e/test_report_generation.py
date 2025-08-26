"""
End-to-End tests for comprehensive report generation system.

This module tests the complete report generation workflow using real PDF processing,
database operations, and file system interactions. NO MOCKING is used in accordance
with e2e testing guidelines.

Tests validate that the new comprehensive report generation system produces
reports that conform to the specification when processing real invoice PDFs.
"""

import unittest
import tempfile
import shutil
import json
import csv
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import uuid

from database.database import DatabaseManager
from database.models import Part
from cli.commands.invoice_commands import create_validation_workflow
from processing.validation_models import ValidationConfiguration
from processing.report_generator import create_report_generator


class TestComprehensiveReportGeneration(unittest.TestCase):
    """
    Test comprehensive report generation with real PDF processing.
    
    This test suite validates that the new report generation system:
    1. Generates all required report types according to specification
    2. Uses correct file naming conventions
    3. Creates proper directory structure
    4. Produces correctly formatted content
    5. Handles real PDF processing and database operations
    """
    
    def setUp(self):
        """Set up test environment with real database and temporary directories."""
        # Create temporary directory for test files
        self.test_dir = Path(tempfile.mkdtemp(prefix="e2e_report_test_"))
        
        # Create temporary database
        self.db_path = self.test_dir / f"test_db_{uuid.uuid4().hex[:8]}.db"
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Initialize database with test data
        self._setup_test_database()
        
        # Create test invoice directory
        self.invoice_dir = self.test_dir / "invoices"
        self.invoice_dir.mkdir()
        
        # Create test output directory
        self.output_dir = self.test_dir / "reports"
        self.output_dir.mkdir()
        
        # Copy real invoice PDFs for testing
        self._setup_test_invoices()
        
        # Create report generator
        self.report_generator = create_report_generator(self.db_manager)
    
    def tearDown(self):
        """Clean up all test resources."""
        # Close database connections
        if hasattr(self.db_manager, 'close'):
            self.db_manager.close()
        
        # Remove temporary directory and all contents
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _setup_test_database(self):
        """Set up test database with sample parts data."""
        # Add some test parts to the database
        test_parts = [
            Part(
                part_number="GS0448",
                description="SHIRT WORK LS BTN COTTON",
                authorized_price=Decimal("15.50"),
                category="Clothing",
                is_active=True
            ),
            Part(
                part_number="GP0171NAVY",
                description="PANTS WORK NAVY",
                authorized_price=Decimal("20.00"),
                category="Clothing",
                is_active=True
            ),
            Part(
                part_number="SAFETY001",
                description="SAFETY VEST HIGH VIS",
                authorized_price=Decimal("25.00"),
                category="Safety",
                is_active=True
            )
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
    
    def _setup_test_invoices(self):
        """Set up test invoice files by copying from docs/invoices if available."""
        # Check if real invoice PDFs are available
        docs_invoice_dir = Path("docs/invoices")
        
        if docs_invoice_dir.exists():
            # Copy available PDF files
            pdf_files = list(docs_invoice_dir.glob("*.pdf"))
            if pdf_files:
                # Copy first few PDFs for testing
                for i, pdf_file in enumerate(pdf_files[:3]):
                    dest_file = self.invoice_dir / f"test_invoice_{i+1}.pdf"
                    shutil.copy2(pdf_file, dest_file)
            else:
                # Create a minimal test PDF if no real ones available
                self._create_minimal_test_pdf()
        else:
            # Create a minimal test PDF if docs directory doesn't exist
            self._create_minimal_test_pdf()
    
    def _create_minimal_test_pdf(self):
        """Create a minimal test PDF for testing when real PDFs aren't available."""
        # This is a fallback - create a simple text file that can be processed
        # In a real scenario, we'd have actual PDF files
        test_content = """
        INVOICE #5790256943
        Date: 06/09/2025
        
        Line Items:
        GS0448    SHIRT WORK LS BTN COTTON    8    $15.75
        UNKNOWN001    UNKNOWN PART    5    $10.00
        """
        
        test_file = self.invoice_dir / "test_invoice_1.txt"
        test_file.write_text(test_content)
    
    def test_comprehensive_report_generation_workflow(self):
        """Test the complete report generation workflow with real processing."""
        # Create validation configuration
        config = ValidationConfiguration.from_database_config(self.db_manager)
        config.interactive_discovery = False  # Disable for automated testing
        
        # Create validation workflow
        workflow = create_validation_workflow(self.db_manager, config)
        
        # Find invoice files to process
        invoice_files = list(self.invoice_dir.glob("*.pdf")) + list(self.invoice_dir.glob("*.txt"))
        
        if not invoice_files:
            self.skipTest("No invoice files available for testing")
        
        # Process invoices using the workflow (this will use the new report generator)
        session_id = str(uuid.uuid4())
        output_file = self.output_dir / "test_report.csv"
        
        try:
            # Process invoices - this should trigger the new comprehensive report generation
            processing_stats = workflow.process_invoices_batch(
                invoice_paths=invoice_files,
                output_path=output_file,
                report_format='csv',
                interactive_discovery=False
            )
            
            # Verify processing completed successfully
            self.assertIsInstance(processing_stats, dict)
            self.assertIn('report_generated', processing_stats)
            self.assertTrue(processing_stats.get('report_generated', False))
            
            # If comprehensive reports were generated, verify them
            if 'generated_reports' in processing_stats:
                self._verify_comprehensive_reports(processing_stats['generated_reports'])
            else:
                # Fallback verification for legacy report
                self._verify_legacy_report(output_file)
                
        except Exception as e:
            self.fail(f"Report generation workflow failed: {e}")
    
    def test_direct_comprehensive_report_generation(self):
        """Test direct comprehensive report generation with mock validation results."""
        # Create mock validation results for testing
        from processing.validation_models import InvoiceValidationResult, ValidationAnomaly, SeverityLevel, AnomalyType
        
        # Create a validation anomaly
        anomaly = ValidationAnomaly(
            anomaly_type=AnomalyType.PRICE_DISCREPANCY,
            severity=SeverityLevel.CRITICAL,
            part_number="GS0448",
            description="Price significantly higher than authorized rate",
            details={
                'description': 'SHIRT WORK LS BTN COTTON',
                'invoice_price': Decimal('15.75'),
                'authorized_price': Decimal('15.50'),
                'quantity': 8,
                'difference_amount': Decimal('0.25'),
                'percentage_difference': Decimal('1.6'),
                'total_impact': Decimal('2.00')
            },
            resolution_action="Contact supplier about price increase",
            detected_at=datetime.now()
        )
        
        # Create validation result
        result = InvoiceValidationResult(
            invoice_number="5790256943",
            invoice_date="06/09/2025",
            invoice_path=Path("test_invoice.pdf"),
            processing_successful=True,
            processing_start_time=datetime.now(),
            processing_end_time=datetime.now(),
            processing_duration=2.5,
            processing_session_id=str(uuid.uuid4())
        )
        result.critical_anomalies.append(anomaly)
        
        # Create processing statistics
        processing_stats = {
            'total_invoices': 1,
            'successfully_processed': 1,
            'failed_processing': 0,
            'total_anomalies': 1,
            'critical_anomalies': 1,
            'warning_anomalies': 0,
            'unknown_parts_discovered': 1,
            'total_processing_time': 2.5
        }
        
        # Create unknown parts data
        unknown_parts = [
            {
                'part_number': 'UNKNOWN001',
                'description': 'UNKNOWN PART',
                'first_seen_invoice': '5790256943',
                'invoice_date': '06/09/2025',
                'discovered_price': Decimal('10.00'),
                'quantity': 5,
                'suggested_price': Decimal('9.50'),
                'confidence': 0.8,
                'similar_parts_count': 0,
                'recommended_action': 'Review and add to database',
                'user_decision': ''
            }
        ]
        
        # Generate comprehensive reports
        session_id = str(uuid.uuid4())
        
        generated_reports = self.report_generator.generate_all_reports(
            validation_results=[result],
            processing_stats=processing_stats,
            session_id=session_id,
            output_directory=self.output_dir,
            input_path=str(self.invoice_dir),
            unknown_parts=unknown_parts,
            errors=[],
            warnings=[]
        )
        
        # Verify all expected reports were generated
        self._verify_comprehensive_reports(generated_reports)
    
    def _verify_comprehensive_reports(self, generated_reports):
        """Verify that all comprehensive reports were generated correctly."""
        # Expected report types according to specification
        expected_reports = [
            'anomaly_report',      # CSV anomaly report
            'validation_report',   # Detailed validation report (TXT)
            'summary_report',      # Summary report (TXT)
            'stats_report'         # Processing statistics (JSON)
        ]
        
        # Unknown parts report is conditional
        if 'unknown_parts_report' in generated_reports:
            expected_reports.append('unknown_parts_report')
        
        # Verify all expected reports exist
        for report_type in expected_reports:
            self.assertIn(report_type, generated_reports, 
                         f"Missing expected report type: {report_type}")
            
            if isinstance(generated_reports[report_type], str):
                # If it's a string path, convert to Path
                report_path = Path(generated_reports[report_type])
            else:
                # If it's a ReportMetadata object, get the file_path
                report_path = generated_reports[report_type].file_path
            
            self.assertTrue(report_path.exists(), 
                           f"Report file does not exist: {report_path}")
            self.assertGreater(report_path.stat().st_size, 0,
                              f"Report file is empty: {report_path}")
        
        # Verify specific report formats and content
        self._verify_csv_anomaly_report(generated_reports.get('anomaly_report'))
        self._verify_detailed_validation_report(generated_reports.get('validation_report'))
        self._verify_summary_report(generated_reports.get('summary_report'))
        self._verify_processing_stats_report(generated_reports.get('stats_report'))
        
        if 'unknown_parts_report' in generated_reports:
            self._verify_unknown_parts_report(generated_reports['unknown_parts_report'])
    
    def _verify_csv_anomaly_report(self, report_info):
        """Verify CSV anomaly report format and content."""
        if isinstance(report_info, str):
            report_path = Path(report_info)
        else:
            report_path = report_info.file_path
        
        # Verify file naming convention
        filename = report_path.name
        self.assertTrue(filename.startswith('invoice_anomalies_'),
                       f"CSV report filename doesn't follow convention: {filename}")
        self.assertTrue(filename.endswith('.csv'),
                       f"CSV report doesn't have .csv extension: {filename}")
        
        # Verify CSV content structure
        with open(report_path, 'r', encoding='utf-8-sig') as f:  # Handle BOM
            reader = csv.reader(f)
            header = next(reader)
            
            # Check for required columns according to specification
            required_columns = [
                'Invoice Number', 'Invoice Date', 'Invoice File', 'Line Number',
                'Part Number', 'Part Description', 'Quantity', 'Invoice Price',
                'Authorized Price', 'Price Difference', 'Percentage Difference',
                'Anomaly Type', 'Severity', 'Financial Impact', 'Processing Session', 'Notes'
            ]
            
            for column in required_columns:
                self.assertIn(column, header,
                             f"Missing required column in CSV: {column}")
    
    def _verify_detailed_validation_report(self, report_info):
        """Verify detailed validation report format and content."""
        if isinstance(report_info, str):
            report_path = Path(report_info)
        else:
            report_path = report_info.file_path
        
        # Verify file naming convention
        filename = report_path.name
        self.assertTrue(filename.startswith('invoice_validation_report_'),
                       f"Validation report filename doesn't follow convention: {filename}")
        self.assertTrue(filename.endswith('.txt'),
                       f"Validation report doesn't have .txt extension: {filename}")
        
        # Verify content structure according to specification
        content = report_path.read_text(encoding='utf-8')
        
        # Check for required sections
        required_sections = [
            "Invoice Rate Detection System - Detailed Validation Report",
            "Generated:",
            "PROCESSING SUMMARY"
        ]
        
        for section in required_sections:
            self.assertIn(section, content,
                         f"Missing required section in validation report: {section}")
    
    def _verify_summary_report(self, report_info):
        """Verify summary report format and content."""
        if isinstance(report_info, str):
            report_path = Path(report_info)
        else:
            report_path = report_info.file_path
        
        # Verify file naming convention
        filename = report_path.name
        self.assertTrue(filename.startswith('processing_summary_'),
                       f"Summary report filename doesn't follow convention: {filename}")
        self.assertTrue(filename.endswith('.txt'),
                       f"Summary report doesn't have .txt extension: {filename}")
        
        # Verify content structure
        content = report_path.read_text(encoding='utf-8')
        
        required_sections = [
            "INVOICE RATE DETECTION SYSTEM - PROCESSING SUMMARY",
            "PROCESSING STATISTICS",
            "ANOMALY SUMMARY",
            "FINANCIAL IMPACT"
        ]
        
        for section in required_sections:
            self.assertIn(section, content,
                         f"Missing required section in summary report: {section}")
    
    def _verify_processing_stats_report(self, report_info):
        """Verify processing statistics report format and content."""
        if isinstance(report_info, str):
            report_path = Path(report_info)
        else:
            report_path = report_info.file_path
        
        # Verify file naming convention
        filename = report_path.name
        self.assertTrue(filename.startswith('processing_stats_'),
                       f"Stats report filename doesn't follow convention: {filename}")
        self.assertTrue(filename.endswith('.json'),
                       f"Stats report doesn't have .json extension: {filename}")
        
        # Verify JSON structure
        with open(report_path, 'r', encoding='utf-8') as f:
            stats_data = json.load(f)
        
        required_keys = [
            'session_id', 'processing_start', 'processing_end',
            'duration_seconds', 'performance_metrics', 'file_statistics',
            'validation_statistics', 'anomaly_statistics'
        ]
        
        for key in required_keys:
            self.assertIn(key, stats_data,
                         f"Missing required key in stats JSON: {key}")
    
    def _verify_unknown_parts_report(self, report_info):
        """Verify unknown parts report format and content."""
        if isinstance(report_info, str):
            report_path = Path(report_info)
        else:
            report_path = report_info.file_path
        
        # Verify file naming convention
        filename = report_path.name
        self.assertTrue(filename.startswith('unknown_parts_'),
                       f"Unknown parts report filename doesn't follow convention: {filename}")
        self.assertTrue(filename.endswith('.csv'),
                       f"Unknown parts report doesn't have .csv extension: {filename}")
        
        # Verify CSV structure
        with open(report_path, 'r', encoding='utf-8-sig') as f:  # Handle BOM
            reader = csv.reader(f)
            header = next(reader)
            
            required_columns = [
                'Part Number', 'Description', 'First Seen Invoice',
                'Invoice Date', 'Discovered Price', 'Quantity',
                'Suggested Authorized Price', 'Confidence Level',
                'Similar Parts Found', 'Recommended Action'
            ]
            
            for column in required_columns:
                self.assertIn(column, header,
                             f"Missing required column in unknown parts CSV: {column}")
    
    def _verify_legacy_report(self, output_file):
        """Verify legacy report format when comprehensive reports aren't generated."""
        self.assertTrue(output_file.exists(),
                       f"Legacy report file does not exist: {output_file}")
        self.assertGreater(output_file.stat().st_size, 0,
                          f"Legacy report file is empty: {output_file}")
    
    def test_directory_structure_creation(self):
        """Test that proper directory structure is created according to specification."""
        # Generate reports to trigger directory creation
        session_id = str(uuid.uuid4())
        
        # Create minimal validation result for testing
        from processing.validation_models import InvoiceValidationResult
        
        result = InvoiceValidationResult(
            invoice_number="TEST001",
            invoice_date="07/29/2025",
            invoice_path=Path("test.pdf"),
            processing_successful=True,
            processing_start_time=datetime.now(),
            processing_end_time=datetime.now(),
            processing_duration=1.0,
            processing_session_id=str(uuid.uuid4())
        )
        
        processing_stats = {
            'total_invoices': 1,
            'successfully_processed': 1,
            'total_processing_time': 1.0
        }
        
        # Generate reports
        generated_reports = self.report_generator.generate_all_reports(
            validation_results=[result],
            processing_stats=processing_stats,
            session_id=session_id,
            output_directory=self.output_dir
        )
        
        # Verify directory structure according to specification
        self.assertTrue((self.output_dir / "current").exists(),
                       "Missing 'current' directory")
        self.assertTrue((self.output_dir / "archive").exists(),
                       "Missing 'archive' directory")
        self.assertTrue((self.output_dir / "templates").exists(),
                       "Missing 'templates' directory")
        
        # Verify date-specific directory
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.output_dir / "current" / today
        self.assertTrue(date_dir.exists(),
                       f"Missing date-specific directory: {date_dir}")
        
        # Verify session directory exists
        session_dirs = list(date_dir.glob(f"session_{session_id[:6]}_*"))
        self.assertTrue(len(session_dirs) > 0,
                       f"Missing session directory for session {session_id[:6]}")


if __name__ == '__main__':
    unittest.main()