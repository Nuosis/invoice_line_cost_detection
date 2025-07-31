"""
Unit tests for the comprehensive report generation system.

This module tests all report templates and the comprehensive report generator
according to the report format specification. Tests use mocking where appropriate
to isolate the report generation logic from external dependencies.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
import csv
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from processing.report_generator import (
    ReportTemplate, ReportOptions, ReportMetadata,
    CSVAnomalyReportTemplate, DetailedValidationReportTemplate,
    SummaryReportTemplate, UnknownPartsReportTemplate,
    ProcessingStatsReportTemplate, ErrorReportTemplate,
    ComprehensiveReportGenerator, create_report_generator
)
from processing.validation_models import (
    InvoiceValidationResult, ValidationAnomaly, SeverityLevel, AnomalyType
)
from database.database import DatabaseManager


class TestReportOptions(unittest.TestCase):
    """Test ReportOptions data class."""
    
    def test_report_options_creation(self):
        """Test creating ReportOptions with required parameters."""
        session_id = "test-session-123"
        output_dir = Path("/tmp/reports")
        
        options = ReportOptions(
            session_id=session_id,
            output_directory=output_dir
        )
        
        self.assertEqual(options.session_id, session_id)
        self.assertEqual(options.output_directory, output_dir)


class TestReportMetadata(unittest.TestCase):
    """Test ReportMetadata data class."""
    
    def test_report_metadata_creation(self):
        """Test creating ReportMetadata with all parameters."""
        metadata = ReportMetadata(
            report_type="test_report",
            file_path=Path("/tmp/test.csv"),
            file_size_bytes=1024,
            record_count=10
        )
        
        self.assertEqual(metadata.report_type, "test_report")
        self.assertEqual(metadata.file_path, Path("/tmp/test.csv"))
        self.assertEqual(metadata.file_size_bytes, 1024)
        self.assertEqual(metadata.record_count, 10)


class TestReportTemplate(unittest.TestCase):
    """Test base ReportTemplate class."""
    
    def test_base_template_creation(self):
        """Test creating base template."""
        template = ReportTemplate("csv", "test_template")
        
        self.assertEqual(template.format_type, "csv")
        self.assertEqual(template.template_name, "test_template")
    
    def test_generate_filename(self):
        """Test filename generation according to specification."""
        template = ReportTemplate("csv", "test_template")
        options = ReportOptions(
            session_id="abc123-def456-ghi789",
            output_directory=Path("/tmp")
        )
        
        filename = template.generate_filename("invoice_anomalies", options)
        
        # Should follow format: [report_type]_YYYYMMDD_HHMMSS_[session_short].extension
        self.assertTrue(filename.startswith("invoice_anomalies_"))
        self.assertTrue(filename.endswith("_abc123.csv"))
        
        # Check date format (YYYYMMDD)
        parts = filename.split("_")
        date_part = parts[2]
        self.assertEqual(len(date_part), 8)
        self.assertTrue(date_part.isdigit())
        
        # Check time format (HHMMSS)
        time_part = parts[3]
        self.assertEqual(len(time_part), 6)
        self.assertTrue(time_part.isdigit())


class TestCSVAnomalyReportTemplate(unittest.TestCase):
    """Test CSV anomaly report template."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.template = CSVAnomalyReportTemplate()
        self.options = ReportOptions(
            session_id="test-session",
            output_directory=Path("/tmp")
        )
    
    def test_template_initialization(self):
        """Test template is properly initialized."""
        self.assertEqual(self.template.format_type, "csv")
        self.assertEqual(self.template.template_name, "anomaly_report")
    
    def test_render_with_anomalies(self):
        """Test rendering CSV with anomalies."""
        # Create mock validation results with anomalies
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
            detected_at=datetime(2025, 7, 29, 13, 45, 0)
        )
        
        result = Mock(spec=InvoiceValidationResult)
        result.invoice_number = "5790256943"
        result.invoice_date = "06/09/2025"
        result.invoice_file_path = Path("invoice_5790256943.pdf")
        result.invoice_path = Path("invoice_5790256943.pdf")  # Add this for compatibility
        result.get_all_anomalies.return_value = [anomaly]
        
        data = {'validation_results': [result]}
        
        content = self.template.render(data, self.options)
        
        # Verify CSV structure
        lines = content.strip().split('\n')
        self.assertTrue(len(lines) >= 2)  # Header + at least one data row
        
        # Check header according to specification
        header = lines[0]
        expected_columns = [
            'Invoice Number', 'Invoice Date', 'Invoice File', 'Line Number',
            'Part Number', 'Part Description', 'Quantity', 'Invoice Price',
            'Authorized Price', 'Price Difference', 'Percentage Difference',
            'Anomaly Type', 'Severity', 'Financial Impact', 'Processing Session', 'Notes'
        ]
        
        for column in expected_columns:
            self.assertIn(column, header)
        
        # Check data row
        data_row = lines[1]
        self.assertIn("5790256943", data_row)
        self.assertIn("GS0448", data_row)
        self.assertIn("CRITICAL", data_row)
    
    def test_render_empty_results(self):
        """Test rendering CSV with no anomalies."""
        data = {'validation_results': []}
        
        content = self.template.render(data, self.options)
        
        # Should still have header
        lines = content.strip().split('\n')
        self.assertEqual(len(lines), 1)  # Only header
        
        header = lines[0]
        self.assertIn('Invoice Number', header)


class TestDetailedValidationReportTemplate(unittest.TestCase):
    """Test detailed validation report template."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.template = DetailedValidationReportTemplate()
        self.options = ReportOptions(
            session_id="test-session",
            output_directory=Path("/tmp")
        )
    
    def test_template_initialization(self):
        """Test template is properly initialized."""
        self.assertEqual(self.template.format_type, "txt")
        self.assertEqual(self.template.template_name, "detailed_validation_report")
    
    def test_render_with_results(self):
        """Test rendering detailed validation report."""
        # Create mock validation result
        anomaly = ValidationAnomaly(
            anomaly_type=AnomalyType.PRICE_DISCREPANCY,
            severity=SeverityLevel.WARNING,
            part_number="GS0448",
            description="Minor price discrepancy",
            details={
                'description': 'SHIRT WORK LS BTN COTTON',
                'invoice_price': Decimal('15.75'),
                'authorized_price': Decimal('15.50'),
                'quantity': 8,
                'difference_amount': Decimal('0.25'),
                'total_impact': Decimal('2.00')
            },
            detected_at=datetime(2025, 7, 29, 13, 45, 0)
        )
        
        result = Mock(spec=InvoiceValidationResult)
        result.invoice_number = "5790256943"
        result.invoice_date = "06/09/2025"
        result.processing_successful = True
        result.get_all_anomalies.return_value = [anomaly]
        result.critical_anomalies = []
        result.warning_anomalies = [anomaly]
        result.informational_anomalies = []
        
        data = {
            'validation_results': [result],
            'processing_stats': {
                'total_invoices': 1,
                'successfully_processed': 1,
                'total_processing_time': 2.5
            }
        }
        
        content = self.template.render(data, self.options)
        
        # Verify report structure according to specification
        self.assertIn("Invoice Rate Detection System - Detailed Validation Report", content)
        self.assertIn("=" * 60, content)
        self.assertIn("INVOICE: 5790256943", content)
        self.assertIn("RATE VALIDATION ERRORS:", content)
        self.assertIn("GS0448", content)
        self.assertIn("PROCESSING SUMMARY", content)
        self.assertIn("Total Invoices Processed: 1", content)


class TestSummaryReportTemplate(unittest.TestCase):
    """Test summary report template."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.template = SummaryReportTemplate()
        self.options = ReportOptions(
            session_id="test-session",
            output_directory=Path("/tmp")
        )
    
    def test_render_summary_report(self):
        """Test rendering summary report."""
        # Create mock validation results to match the processing stats
        mock_results = []
        for i in range(5):
            mock_result = Mock(spec=InvoiceValidationResult)
            mock_result.invoice_number = f"TEST{i+1}"
            mock_result.processing_successful = i < 4  # 4 successful, 1 failed
            mock_result.get_all_anomalies.return_value = []
            mock_result.critical_anomalies = []  # Add missing attribute
            mock_result.warning_anomalies = []   # Add missing attribute
            mock_result.informational_anomalies = []  # Add missing attribute
            mock_results.append(mock_result)
        
        data = {
            'validation_results': mock_results,
            'processing_stats': {
                'total_invoices': 5,
                'successfully_processed': 4,
                'failed_processing': 1,
                'total_anomalies': 10,
                'critical_anomalies': 2,
                'warning_anomalies': 6,
                'informational_anomalies': 2,
                'unknown_parts_discovered': 3,
                'parts_added_during_discovery': 1,
                'total_processing_time': 15.5
            },
            'input_path': '/test/invoices',
            'unknown_parts': [{'part_number': 'TEST123'}]
        }
        
        content = self.template.render(data, self.options)
        
        # Verify summary report structure
        self.assertIn("INVOICE RATE DETECTION SYSTEM - PROCESSING SUMMARY", content)
        self.assertIn("PROCESSING STATISTICS", content)
        self.assertIn("Total Invoices Processed: 5", content)
        self.assertIn("ANOMALY SUMMARY", content)
        self.assertIn("Critical Issues: 0", content)  # Template calculates from actual results, not stats
        self.assertIn("FINANCIAL IMPACT", content)
        self.assertIn("PARTS DISCOVERY", content)
        self.assertIn("Unknown Parts Discovered: 3", content)


class TestUnknownPartsReportTemplate(unittest.TestCase):
    """Test unknown parts report template."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.template = UnknownPartsReportTemplate()
        self.options = ReportOptions(
            session_id="test-session",
            output_directory=Path("/tmp")
        )
    
    def test_render_unknown_parts_csv(self):
        """Test rendering unknown parts CSV."""
        unknown_parts = [
            {
                'part_number': 'XYZ999',
                'description': 'UNKNOWN SAFETY VEST',
                'first_seen_invoice': '5790256943',
                'invoice_date': '06/09/2025',
                'discovered_price': Decimal('45.00'),
                'quantity': 3,
                'suggested_price': Decimal('42.00'),
                'confidence': 0.85,
                'similar_parts_count': 2,
                'recommended_action': 'Review and add to database',
                'user_decision': ''
            }
        ]
        
        data = {'unknown_parts': unknown_parts}
        
        content = self.template.render(data, self.options)
        
        # Verify CSV structure
        lines = content.strip().split('\n')
        self.assertTrue(len(lines) >= 2)  # Header + data
        
        header = lines[0]
        expected_columns = [
            'Part Number', 'Description', 'First Seen Invoice',
            'Invoice Date', 'Discovered Price', 'Quantity',
            'Suggested Authorized Price', 'Confidence Level',
            'Similar Parts Found', 'Recommended Action'
        ]
        
        for column in expected_columns:
            self.assertIn(column, header)
        
        data_row = lines[1]
        self.assertIn('XYZ999', data_row)
        self.assertIn('UNKNOWN SAFETY VEST', data_row)


class TestProcessingStatsReportTemplate(unittest.TestCase):
    """Test processing statistics report template."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.template = ProcessingStatsReportTemplate()
        self.options = ReportOptions(
            session_id="test-session",
            output_directory=Path("/tmp")
        )
    
    def test_render_processing_stats_json(self):
        """Test rendering processing statistics JSON."""
        validation_results = []
        processing_stats = {
            'total_invoices': 5,
            'successfully_processed': 4,
            'total_processing_time': 15.5,
            'database_queries': 150,
            'cache_hit_rate': 0.85
        }
        
        data = {
            'validation_results': validation_results,
            'processing_stats': processing_stats
        }
        
        content = self.template.render(data, self.options)
        
        # Verify JSON structure
        stats_data = json.loads(content)
        
        self.assertIn('session_id', stats_data)
        self.assertIn('processing_start', stats_data)
        self.assertIn('processing_end', stats_data)
        self.assertIn('duration_seconds', stats_data)
        self.assertIn('performance_metrics', stats_data)
        self.assertIn('file_statistics', stats_data)
        self.assertIn('validation_statistics', stats_data)
        self.assertIn('anomaly_statistics', stats_data)
        
        # Check performance metrics
        perf_metrics = stats_data['performance_metrics']
        self.assertIn('files_per_second', perf_metrics)
        self.assertIn('validation_operations_per_second', perf_metrics)


class TestErrorReportTemplate(unittest.TestCase):
    """Test error report template."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.template = ErrorReportTemplate()
        self.options = ReportOptions(
            session_id="test-session",
            output_directory=Path("/tmp")
        )
    
    def test_render_error_report(self):
        """Test rendering error report."""
        errors = [
            {
                'timestamp': '13:45:00',
                'type': 'ProcessingError',
                'message': 'Failed to process invoice',
                'file': 'invoice_123.pdf',
                'details': 'PDF corruption detected',
                'recovery_action': 'Skipped file',
                'user_action': 'Check PDF file integrity'
            }
        ]
        
        warnings = [
            {
                'timestamp': '13:46:00',
                'type': 'ValidationWarning',
                'message': 'Unknown part detected',
                'context': 'Part XYZ999 not in database',
                'impact': 'Validation skipped for this part'
            }
        ]
        
        data = {
            'errors': errors,
            'warnings': warnings,
            'failed_files': [{'filename': 'invoice_123.pdf', 'reason': 'PDF corruption'}],
            'system_info': {
                'app_version': '1.0.0',
                'python_version': '3.11.0'
            }
        }
        
        content = self.template.render(data, self.options)
        
        # Verify error report structure
        self.assertIn("INVOICE RATE DETECTION SYSTEM - ERROR REPORT", content)
        self.assertIn("CRITICAL ERRORS", content)
        self.assertIn("ProcessingError", content)
        self.assertIn("WARNINGS", content)
        self.assertIn("ValidationWarning", content)
        self.assertIn("PROCESSING FAILURES", content)
        self.assertIn("SYSTEM INFORMATION", content)


class TestComprehensiveReportGenerator(unittest.TestCase):
    """Test the comprehensive report generator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.generator = ComprehensiveReportGenerator(self.mock_db_manager)
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_generator_initialization(self):
        """Test generator is properly initialized."""
        self.assertEqual(self.generator.db_manager, self.mock_db_manager)
        self.assertIn('csv_anomaly', self.generator.templates)
        self.assertIn('detailed_validation', self.generator.templates)
        self.assertIn('summary', self.generator.templates)
        self.assertIn('unknown_parts', self.generator.templates)
        self.assertIn('processing_stats', self.generator.templates)
        self.assertIn('error_report', self.generator.templates)
    
    @patch('processing.report_generator.datetime')
    def test_generate_all_reports(self, mock_datetime):
        """Test generating all reports."""
        # Mock datetime for consistent testing
        mock_datetime.now.return_value = datetime(2025, 7, 29, 13, 45, 0)
        mock_datetime.strftime = datetime.strftime
        
        # Create mock validation results
        anomaly = ValidationAnomaly(
            anomaly_type=AnomalyType.PRICE_DISCREPANCY,
            severity=SeverityLevel.CRITICAL,
            part_number="GS0448",
            description="Test anomaly",
            details={'total_impact': Decimal('10.00')},
            detected_at=datetime(2025, 7, 29, 13, 45, 0)
        )
        
        result = Mock(spec=InvoiceValidationResult)
        result.invoice_number = "5790256943"
        result.invoice_date = "06/09/2025"
        result.invoice_file_path = Path("test_invoice.pdf")
        result.invoice_path = Path("test_invoice.pdf")  # Add this for compatibility
        result.processing_successful = True
        result.processing_start_time = datetime.now()
        result.processing_end_time = datetime.now()
        result.processing_duration = 2.5
        result.get_all_anomalies.return_value = [anomaly]
        result.critical_anomalies = [anomaly]
        result.warning_anomalies = []
        result.informational_anomalies = []
        
        validation_results = [result]
        processing_stats = {
            'total_invoices': 1,
            'successfully_processed': 1,
            'total_processing_time': 2.5
        }
        
        unknown_parts = [
            {
                'part_number': 'XYZ999',
                'description': 'Test part',
                'discovered_price': Decimal('45.00')
            }
        ]
        
        generated_reports = self.generator.generate_all_reports(
            validation_results=validation_results,
            processing_stats=processing_stats,
            session_id="test-session-123",
            output_directory=self.temp_dir,
            unknown_parts=unknown_parts
        )
        
        # Verify all expected reports were generated
        expected_reports = ['anomaly_report', 'validation_report', 'summary_report', 
                          'unknown_parts_report', 'stats_report']
        
        for report_type in expected_reports:
            self.assertIn(report_type, generated_reports)
            metadata = generated_reports[report_type]
            self.assertIsInstance(metadata, ReportMetadata)
            self.assertTrue(metadata.file_path.exists())
    
    def test_create_directory_structure(self):
        """Test directory structure creation."""
        options = ReportOptions(
            session_id="test-session-123",
            output_directory=self.temp_dir
        )
        
        self.generator._create_directory_structure(options)
        
        # Verify directory structure
        self.assertTrue((self.temp_dir / "current").exists())
        self.assertTrue((self.temp_dir / "archive").exists())
        self.assertTrue((self.temp_dir / "templates").exists())
        
        # Verify date-specific directory
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertTrue((self.temp_dir / "current" / today).exists())


class TestCreateReportGenerator(unittest.TestCase):
    """Test the factory function for creating report generators."""
    
    def test_create_report_generator(self):
        """Test factory function creates proper generator."""
        mock_db_manager = Mock(spec=DatabaseManager)
        
        generator = create_report_generator(mock_db_manager)
        
        self.assertIsInstance(generator, ComprehensiveReportGenerator)
        self.assertEqual(generator.db_manager, mock_db_manager)


if __name__ == '__main__':
    unittest.main()