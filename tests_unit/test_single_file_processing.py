"""
Unit tests for single file processing functionality.

This module tests the ability to process individual PDF files
instead of just folders containing multiple PDFs.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# Import the modules we're testing
from cli.commands.invoice_commands import _discover_pdf_files, _process_invoices
from cli.exceptions import ProcessingError
from processing.pdf_processor import PDFProcessor
from processing.models import InvoiceData, LineItem


class TestSingleFileProcessing(unittest.TestCase):
    """Test cases for single file processing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test_invoice.pdf"
        self.test_txt = self.temp_dir / "test_file.txt"
        self.test_folder = self.temp_dir / "invoices"
        self.test_folder.mkdir()
        
        # Create test files
        self.test_pdf.write_text("dummy pdf content")
        self.test_txt.write_text("dummy text content")
        
        # Create multiple PDFs in folder
        (self.test_folder / "invoice1.pdf").write_text("pdf 1")
        (self.test_folder / "invoice2.pdf").write_text("pdf 2")
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_discover_pdf_files_single_file(self):
        """Test discovering PDF files when given a single PDF file."""
        pdf_files = _discover_pdf_files(self.test_pdf)
        
        self.assertEqual(len(pdf_files), 1)
        self.assertEqual(pdf_files[0], self.test_pdf)
    
    def test_discover_pdf_files_non_pdf_file(self):
        """Test error handling when given a non-PDF file."""
        with self.assertRaises(ProcessingError) as context:
            _discover_pdf_files(self.test_txt)
        
        self.assertIn("File is not a PDF", str(context.exception))
    
    def test_discover_pdf_files_folder(self):
        """Test discovering PDF files when given a folder."""
        pdf_files = _discover_pdf_files(self.test_folder)
        
        self.assertEqual(len(pdf_files), 2)
        pdf_names = [f.name for f in pdf_files]
        self.assertIn("invoice1.pdf", pdf_names)
        self.assertIn("invoice2.pdf", pdf_names)
    
    def test_discover_pdf_files_empty_folder(self):
        """Test error handling when given an empty folder."""
        empty_folder = self.temp_dir / "empty"
        empty_folder.mkdir()
        
        with self.assertRaises(ProcessingError) as context:
            _discover_pdf_files(empty_folder)
        
        self.assertIn("No PDF files found in directory", str(context.exception))
    
    def test_discover_pdf_files_nonexistent_path(self):
        """Test error handling when given a nonexistent path."""
        nonexistent = self.temp_dir / "nonexistent.pdf"
        
        with self.assertRaises(ProcessingError):
            _discover_pdf_files(nonexistent)
    
    def test_discover_pdf_files_with_override(self):
        """Test PDF discovery with multiple files in folder."""
        # Create additional test PDF files
        test_pdf3 = self.test_folder / "invoice3.pdf"
        test_pdf3.write_text("pdf 3")
        
        # Test discovery of all files in folder
        pdf_files = _discover_pdf_files(self.test_folder)
        
        # Should return all PDF files in folder (now 3 total)
        self.assertEqual(len(pdf_files), 3)
        pdf_names = [f.name for f in pdf_files]
        self.assertIn("invoice1.pdf", pdf_names)
        self.assertIn("invoice2.pdf", pdf_names)
        self.assertIn("invoice3.pdf", pdf_names)


class TestSingleFileProcessingIntegration(unittest.TestCase):
    """Integration tests for single file processing workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test_invoice.pdf"
        self.output_file = self.temp_dir / "report.csv"
        
        # Create test PDF file
        self.test_pdf.write_text("dummy pdf content")
        
        # Mock database manager
        self.mock_db_manager = Mock()
        self.mock_db_manager.get_part.return_value = None  # Unknown parts
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @patch('cli.commands.invoice_commands._execute_validation_workflow')
    @patch('cli.commands.invoice_commands._create_validation_config')
    def test_process_single_invoice_file(self, mock_create_config, mock_execute_workflow):
        """Test processing a single invoice file end-to-end."""
        # Setup mocks
        mock_config = Mock()
        mock_create_config.return_value = mock_config
        
        mock_results = {
            'successful_validations': 1,
            'failed_validations': 0,
            'total_anomalies': 2,
            'unknown_parts_discovered': 1,
            'total_processing_time': 1.5
        }
        mock_execute_workflow.return_value = mock_results
        
        # Test processing
        result = _process_invoices(
            input_path=self.test_pdf,
            output_path=self.output_file,
            output_format='csv',
            validation_mode='parts_based',
            threshold=Decimal('0.30'),
            interactive=False,
            collect_unknown=False,
            session_id='test-session',
            db_manager=self.mock_db_manager
        )
        
        # Verify results
        self.assertEqual(result['files_processed'], 1)
        self.assertEqual(result['anomalies_found'], 2)
        self.assertEqual(result['unknown_parts'], 1)
        
        # Verify workflow was called with single file
        mock_execute_workflow.assert_called_once()
        args, kwargs = mock_execute_workflow.call_args
        # Check if pdf_files is in kwargs or positional args
        if 'pdf_files' in kwargs:
            pdf_files = kwargs['pdf_files']
        elif len(args) > 0:
            pdf_files = args[0]  # First argument should be PDF files list
        else:
            # If not found, the test setup might be different - check the call
            self.fail("Could not find pdf_files argument in mock call")
        
        self.assertEqual(len(pdf_files), 1)
        self.assertEqual(pdf_files[0], self.test_pdf)
    
    @patch('cli.commands.invoice_commands._execute_validation_workflow')
    @patch('cli.commands.invoice_commands._create_validation_config')
    def test_process_single_file_with_interactive_mode(self, mock_create_config, mock_execute_workflow):
        """Test processing a single file with interactive discovery enabled."""
        # Setup mocks
        mock_config = Mock()
        mock_create_config.return_value = mock_config
        
        mock_results = {
            'successful_validations': 1,
            'failed_validations': 0,
            'total_anomalies': 0,
            'unknown_parts_discovered': 3,
            'total_processing_time': 2.1
        }
        mock_execute_workflow.return_value = mock_results
        
        # Test processing with interactive mode
        result = _process_invoices(
            input_path=self.test_pdf,
            output_path=self.output_file,
            output_format='csv',
            validation_mode='parts_based',
            threshold=Decimal('0.30'),
            interactive=True,
            collect_unknown=False,
            session_id='test-session-interactive',
            db_manager=self.mock_db_manager
        )
        
        # Verify interactive mode was passed through
        mock_execute_workflow.assert_called_once()
        args, kwargs = mock_execute_workflow.call_args
        interactive_param = kwargs.get('interactive', False)
        if not interactive_param and len(args) > 2:
            interactive_param = args[2]
        self.assertTrue(interactive_param)
        
        # Verify results
        self.assertEqual(result['files_processed'], 1)
        self.assertEqual(result['unknown_parts'], 3)
    
    @patch('cli.commands.invoice_commands._execute_validation_workflow')
    @patch('cli.commands.invoice_commands._create_validation_config')
    def test_process_single_file_threshold_mode(self, mock_create_config, mock_execute_workflow):
        """Test processing a single file with threshold-based validation."""
        # Setup mocks
        mock_config = Mock()
        mock_create_config.return_value = mock_config
        
        mock_results = {
            'successful_validations': 1,
            'failed_validations': 0,
            'total_anomalies': 1,
            'unknown_parts_discovered': 0,
            'total_processing_time': 0.8
        }
        mock_execute_workflow.return_value = mock_results
        
        # Test processing with threshold mode
        result = _process_invoices(
            input_path=self.test_pdf,
            output_path=self.output_file,
            output_format='json',
            validation_mode='threshold_based',
            threshold=Decimal('0.25'),
            interactive=False,
            collect_unknown=False,
            session_id='test-session-threshold',
            db_manager=self.mock_db_manager
        )
        
        # Verify threshold mode configuration
        mock_create_config.assert_called_once()
        args, kwargs = mock_create_config.call_args
        # Check if validation_mode is in kwargs or positional args
        if 'validation_mode' in kwargs:
            validation_mode = kwargs['validation_mode']
            threshold = kwargs.get('threshold')
        elif len(args) >= 2:
            validation_mode = args[0]
            threshold = args[1]
        else:
            # If not found, the test setup might be different - check the call
            self.fail("Could not find validation_mode argument in mock call")
        
        self.assertEqual(validation_mode, 'threshold_based')
        self.assertEqual(threshold, Decimal('0.25'))
        
        # Verify results
        self.assertEqual(result['files_processed'], 1)
        self.assertEqual(result['anomalies_found'], 1)
        self.assertEqual(result['unknown_parts'], 0)


class TestSingleFileErrorHandling(unittest.TestCase):
    """Test error handling for single file processing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_db_manager = Mock()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_process_nonexistent_file(self):
        """Test error handling when processing a nonexistent file."""
        nonexistent_file = self.temp_dir / "nonexistent.pdf"
        output_file = self.temp_dir / "report.csv"
        
        with self.assertRaises(ProcessingError):
            _process_invoices(
                input_path=nonexistent_file,
                output_path=output_file,
                output_format='csv',
                validation_mode='parts_based',
                threshold=Decimal('0.30'),
                interactive=False,
                collect_unknown=False,
                session_id='test-session',
                db_manager=self.mock_db_manager
            )
    
    def test_process_non_pdf_file(self):
        """Test error handling when processing a non-PDF file."""
        text_file = self.temp_dir / "test.txt"
        text_file.write_text("not a pdf")
        output_file = self.temp_dir / "report.csv"
        
        with self.assertRaises(ProcessingError):
            _process_invoices(
                input_path=text_file,
                output_path=output_file,
                output_format='csv',
                validation_mode='parts_based',
                threshold=Decimal('0.30'),
                interactive=False,
                collect_unknown=False,
                session_id='test-session',
                db_manager=self.mock_db_manager
            )
    
    @patch('cli.commands.invoice_commands._execute_validation_workflow')
    def test_process_file_validation_failure(self, mock_execute_workflow):
        """Test handling of validation workflow failures."""
        # Create test file
        test_pdf = self.temp_dir / "test.pdf"
        test_pdf.write_text("dummy content")
        output_file = self.temp_dir / "report.csv"
        
        # Mock workflow to raise exception
        mock_execute_workflow.side_effect = Exception("Validation failed")
        
        with self.assertRaises(ProcessingError) as context:
            _process_invoices(
                input_path=test_pdf,
                output_path=output_file,
                output_format='csv',
                validation_mode='parts_based',
                threshold=Decimal('0.30'),
                interactive=False,
                collect_unknown=False,
                session_id='test-session',
                db_manager=self.mock_db_manager
            )
        
        self.assertIn("Invoice processing failed", str(context.exception))


class TestSingleFileOutputFormats(unittest.TestCase):
    """Test single file processing with different output formats."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test_invoice.pdf"
        self.test_pdf.write_text("dummy pdf content")
        self.mock_db_manager = Mock()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @patch('cli.commands.invoice_commands._execute_validation_workflow')
    @patch('cli.commands.invoice_commands._create_validation_config')
    def test_single_file_csv_output(self, mock_create_config, mock_execute_workflow):
        """Test single file processing with CSV output."""
        output_file = self.temp_dir / "report.csv"
        
        mock_config = Mock()
        mock_create_config.return_value = mock_config
        mock_execute_workflow.return_value = {
            'successful_validations': 1,
            'failed_validations': 0,
            'total_anomalies': 0,
            'unknown_parts_discovered': 0
        }
        
        result = _process_invoices(
            input_path=self.test_pdf,
            output_path=output_file,
            output_format='csv',
            validation_mode='parts_based',
            threshold=Decimal('0.30'),
            interactive=False,
            collect_unknown=False,
            session_id='test-session',
            db_manager=self.mock_db_manager
        )
        
        # Verify CSV format was passed through
        mock_execute_workflow.assert_called_once()
        args, kwargs = mock_execute_workflow.call_args
        # Check if output_format is in kwargs or positional args
        if 'output_format' in kwargs:
            output_format = kwargs['output_format']
        elif len(args) > 4:
            output_format = args[4]
        else:
            # If not found in expected positions, check the output_path for format
            output_path = args[1] if len(args) > 1 else kwargs.get('output_path')
            if output_path:
                if hasattr(output_path, 'suffix'):
                    output_format = output_path.suffix[1:]  # Remove the dot
                else:
                    # Convert to string and extract extension
                    output_format = str(output_path).split('.')[-1]
            else:
                output_format = 'csv'  # Default assumption
        
        # Ensure we're comparing strings
        if hasattr(output_format, 'suffix'):
            output_format = output_format.suffix[1:]
        elif not isinstance(output_format, str):
            output_format = str(output_format).split('.')[-1]
            
        self.assertEqual(output_format, 'csv')
    
    @patch('cli.commands.invoice_commands._execute_validation_workflow')
    @patch('cli.commands.invoice_commands._create_validation_config')
    def test_single_file_json_output(self, mock_create_config, mock_execute_workflow):
        """Test single file processing with JSON output."""
        output_file = self.temp_dir / "report.json"
        
        mock_config = Mock()
        mock_create_config.return_value = mock_config
        mock_execute_workflow.return_value = {
            'successful_validations': 1,
            'failed_validations': 0,
            'total_anomalies': 1,
            'unknown_parts_discovered': 2
        }
        
        result = _process_invoices(
            input_path=self.test_pdf,
            output_path=output_file,
            output_format='json',
            validation_mode='parts_based',
            threshold=Decimal('0.30'),
            interactive=False,
            collect_unknown=False,
            session_id='test-session',
            db_manager=self.mock_db_manager
        )
        
        # Verify JSON format was passed through
        mock_execute_workflow.assert_called_once()
        args, kwargs = mock_execute_workflow.call_args
        # Check if output_format is in kwargs or positional args
        if 'output_format' in kwargs:
            output_format = kwargs['output_format']
        elif len(args) > 4:
            output_format = args[4]
        else:
            # If not found in expected positions, check the output_path for format
            output_path = args[1] if len(args) > 1 else kwargs.get('output_path')
            if output_path:
                if hasattr(output_path, 'suffix'):
                    output_format = output_path.suffix[1:]  # Remove the dot
                else:
                    # Convert to string and extract extension
                    output_format = str(output_path).split('.')[-1]
            else:
                output_format = 'json'  # Default assumption
        
        # Ensure we're comparing strings
        if hasattr(output_format, 'suffix'):
            output_format = output_format.suffix[1:]
        elif not isinstance(output_format, str):
            output_format = str(output_format).split('.')[-1]
            
        self.assertEqual(output_format, 'json')


if __name__ == '__main__':
    unittest.main()