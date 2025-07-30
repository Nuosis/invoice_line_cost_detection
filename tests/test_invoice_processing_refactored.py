"""
Tests for refactored invoice processing functions with minimal mocking.

This test suite focuses on testing the business logic of the refactored helper functions
with real data and minimal mocking, following the requirement to minimize mocking as much as possible.
"""

import pytest
import tempfile
import uuid
import sys
from pathlib import Path
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# Import the functions directly to avoid circular import issues
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the functions directly to avoid circular import issues
from cli.commands.invoice_commands import (
    _discover_pdf_files, _create_validation_config, _execute_validation_workflow,
    _generate_processing_results, _process_invoices
)

from cli.exceptions import ProcessingError
from processing.validation_models import ValidationConfiguration
from processing.validation_integration import ValidationWorkflowManager


class TestDiscoverPdfFiles:
    """Test PDF file discovery functionality with real file system operations."""
    
    def test_discover_single_pdf_file(self):
        """Test discovering a single PDF file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test PDF file
            pdf_path = Path(temp_dir) / "test_invoice.pdf"
            pdf_path.write_text("dummy pdf content")
            
            result = _discover_pdf_files(pdf_path)
            
            assert len(result) == 1
            assert result[0] == pdf_path
    
    def test_discover_multiple_pdf_files_in_directory(self):
        """Test discovering multiple PDF files in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple PDF files
            pdf_files = []
            for i in range(3):
                pdf_path = temp_path / f"invoice_{i}.pdf"
                pdf_path.write_text(f"dummy pdf content {i}")
                pdf_files.append(pdf_path)
            
            # Create a non-PDF file (should be ignored)
            (temp_path / "readme.txt").write_text("not a pdf")
            
            result = _discover_pdf_files(temp_path)
            
            assert len(result) == 3
            # Results should contain all PDF files
            result_names = {f.name for f in result}
            expected_names = {f.name for f in pdf_files}
            assert result_names == expected_names
    
    def test_discover_no_pdf_files_raises_error(self):
        """Test that ProcessingError is raised when no PDF files are found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create only non-PDF files
            (temp_path / "readme.txt").write_text("not a pdf")
            (temp_path / "data.json").write_text("{}")
            
            with pytest.raises(ProcessingError, match="No PDF files found"):
                _discover_pdf_files(temp_path)
    
    def test_discover_single_non_pdf_file_raises_error(self):
        """Test that ProcessingError is raised for single non-PDF file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            txt_path = Path(temp_dir) / "not_a_pdf.txt"
            txt_path.write_text("not a pdf")
            
            with pytest.raises(ProcessingError, match="No PDF files found"):
                _discover_pdf_files(txt_path)
    
    def test_discover_empty_directory_raises_error(self):
        """Test that ProcessingError is raised for empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with pytest.raises(ProcessingError, match="No PDF files found"):
                _discover_pdf_files(temp_path)


class TestCreateValidationConfig:
    """Test validation configuration creation with real ValidationConfiguration objects."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock database manager with realistic behavior
        self.mock_db_manager = Mock()
        self.mock_db_manager.get_config_value.side_effect = lambda key, default: default
    
    def test_create_threshold_based_config(self):
        """Test creating threshold-based validation configuration."""
        threshold = Decimal('0.50')
        
        config = _create_validation_config(
            validation_mode='threshold_based',
            threshold=threshold,
            interactive=True,
            collect_unknown=False,
            db_manager=self.mock_db_manager
        )
        
        assert isinstance(config, ValidationConfiguration)
        assert config.price_discrepancy_warning_threshold == threshold
        assert config.price_discrepancy_critical_threshold == threshold * 2
        assert config.interactive_discovery is True
        assert config.batch_collect_unknown_parts is False
    
    def test_create_parts_based_config(self):
        """Test creating parts-based validation configuration."""
        config = _create_validation_config(
            validation_mode='parts_based',
            threshold=Decimal('0.30'),  # Should be ignored for parts-based mode
            interactive=False,
            collect_unknown=True,
            db_manager=self.mock_db_manager
        )
        
        assert isinstance(config, ValidationConfiguration)
        assert config.interactive_discovery is False
        assert config.batch_collect_unknown_parts is True
        # Should use database configuration, not threshold
        self.mock_db_manager.get_config_value.assert_called()
    
    def test_config_applies_common_settings(self):
        """Test that common settings are applied regardless of mode."""
        for mode in ['threshold_based', 'parts_based']:
            config = _create_validation_config(
                validation_mode=mode,
                threshold=Decimal('0.25'),
                interactive=True,
                collect_unknown=True,
                db_manager=self.mock_db_manager
            )
            
            assert config.interactive_discovery is True
            assert config.batch_collect_unknown_parts is True


class TestGenerateProcessingResults:
    """Test processing results generation with real data structures."""
    
    def test_generate_results_from_validation_summary(self):
        """Test generating results from validation workflow summary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.csv"
            
            # Create realistic validation results
            validation_results = {
                'successful_validations': 5,
                'failed_validations': 1,
                'total_anomalies': 3,
                'unknown_parts_discovered': 2,
                'critical_anomalies': 1,
                'warning_anomalies': 2,
                'total_processing_time': 15.5
            }
            
            result = _generate_processing_results(validation_results, output_path)
            
            assert result['files_processed'] == 5
            assert result['files_failed'] == 1
            assert result['anomalies_found'] == 3
            assert result['unknown_parts'] == 2
            assert result['critical_anomalies'] == 1
            assert result['warning_anomalies'] == 2
            assert result['processing_time'] == 15.5
            assert result['report_file'] == str(output_path)
            assert result['total_overcharge'] == Decimal('0.00')
    
    def test_generate_results_from_batch_processing_stats(self):
        """Test generating results from batch processing statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "batch_report.csv"
            
            # Create realistic batch processing results
            batch_results = {
                'successfully_processed': 10,
                'failed_processing': 2,
                'total_anomalies': 8,
                'unknown_parts_discovered': 5,
                'critical_anomalies': 3,
                'warning_anomalies': 5,
                'average_processing_time': 2.3
            }
            
            result = _generate_processing_results(batch_results, output_path)
            
            assert result['files_processed'] == 10
            assert result['files_failed'] == 2
            assert result['anomalies_found'] == 8
            assert result['unknown_parts'] == 5
            assert result['critical_anomalies'] == 3
            assert result['warning_anomalies'] == 5
            assert result['processing_time'] == 2.3
    
    def test_generate_results_handles_missing_fields(self):
        """Test that missing fields are handled gracefully with defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "minimal_report.csv"
            
            # Minimal validation results
            minimal_results = {
                'successful_validations': 1
            }
            
            result = _generate_processing_results(minimal_results, output_path)
            
            assert result['files_processed'] == 1
            assert result['files_failed'] == 0
            assert result['anomalies_found'] == 0
            assert result['unknown_parts'] == 0
            assert result['critical_anomalies'] == 0
            assert result['warning_anomalies'] == 0
            assert result['processing_time'] == 0.0


class TestExecuteValidationWorkflow:
    """Test validation workflow execution with minimal mocking."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_manager = Mock()
        self.mock_config = ValidationConfiguration()
        
        # Create mock workflow with realistic behavior
        self.mock_workflow = Mock(spec=ValidationWorkflowManager)
        self.mock_workflow.report_generator = Mock()
        
    def test_execute_single_file_workflow(self):
        """Test executing workflow for single PDF file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("dummy pdf")
            output_path = Path(temp_dir) / "report.csv"
            
            # Mock single file processing
            mock_validation_result = Mock()
            mock_discovery_results = []
            self.mock_workflow.process_single_invoice.return_value = (
                mock_validation_result, mock_discovery_results
            )
            
            # Mock report generation
            self.mock_workflow.report_generator.generate_anomaly_report.return_value = {
                'total_anomalies': 2
            }
            
            # Mock validation summary
            expected_summary = {
                'successful_validations': 1,
                'failed_validations': 0,
                'total_anomalies': 2,
                'unknown_parts_discovered': 0,
                'critical_anomalies': 1,
                'warning_anomalies': 1,
                'total_processing_time': 1.5
            }
            self.mock_workflow.get_validation_summary.return_value = expected_summary
            
            with patch('cli.commands.invoice_commands.create_validation_workflow', 
                      return_value=self.mock_workflow):
                with patch('cli.commands.invoice_commands.format_validation_summary', 
                          return_value="Summary"):
                    result = _execute_validation_workflow(
                        pdf_files=[pdf_path],
                        config=self.mock_config,
                        db_manager=self.mock_db_manager,
                        interactive=False,
                        output_path=output_path,
                        output_format='csv'
                    )
            
            # Verify workflow was called correctly
            self.mock_workflow.process_single_invoice.assert_called_once_with(
                pdf_path, interactive_discovery=False
            )
            self.mock_workflow.report_generator.generate_anomaly_report.assert_called_once()
            self.mock_workflow.get_validation_summary.assert_called_once()
            
            assert result == expected_summary
    
    def test_execute_batch_workflow(self):
        """Test executing workflow for multiple PDF files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            pdf_files = []
            for i in range(3):
                pdf_path = Path(temp_dir) / f"test_{i}.pdf"
                pdf_path.write_text(f"dummy pdf {i}")
                pdf_files.append(pdf_path)
            
            output_path = Path(temp_dir) / "batch_report.csv"
            
            # Mock batch processing
            expected_stats = {
                'total_invoices': 3,
                'successfully_processed': 3,
                'failed_processing': 0,
                'total_anomalies': 5,
                'unknown_parts_discovered': 2
            }
            self.mock_workflow.process_invoices_batch.return_value = expected_stats
            
            with patch('cli.commands.invoice_commands.create_validation_workflow', 
                      return_value=self.mock_workflow):
                result = _execute_validation_workflow(
                    pdf_files=pdf_files,
                    config=self.mock_config,
                    db_manager=self.mock_db_manager,
                    interactive=True,
                    output_path=output_path,
                    output_format='csv'
                )
            
            # Verify batch processing was called correctly
            self.mock_workflow.process_invoices_batch.assert_called_once_with(
                invoice_paths=pdf_files,
                output_path=output_path,
                report_format='csv',
                interactive_discovery=True
            )
            
            assert result == expected_stats


class TestProcessInvoicesIntegration:
    """Integration tests for the refactored _process_invoices function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_manager = Mock()
        self.mock_db_manager.get_config_value.side_effect = lambda key, default: default
        
        # Create mock workflow
        self.mock_workflow = Mock(spec=ValidationWorkflowManager)
        self.mock_workflow.report_generator = Mock()
    
    def test_process_invoices_single_file_integration(self):
        """Test complete processing workflow for single file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test PDF file
            pdf_path = Path(temp_dir) / "invoice.pdf"
            pdf_path.write_text("dummy pdf content")
            output_path = Path(temp_dir) / "report.csv"
            
            # Mock workflow responses
            mock_validation_result = Mock()
            self.mock_workflow.process_single_invoice.return_value = (
                mock_validation_result, []
            )
            self.mock_workflow.report_generator.generate_anomaly_report.return_value = {}
            
            validation_summary = {
                'successful_validations': 1,
                'failed_validations': 0,
                'total_anomalies': 1,
                'unknown_parts_discovered': 0,
                'critical_anomalies': 0,
                'warning_anomalies': 1,
                'total_processing_time': 2.1
            }
            self.mock_workflow.get_validation_summary.return_value = validation_summary
            
            with patch('cli.commands.invoice_commands.create_validation_workflow', 
                      return_value=self.mock_workflow):
                with patch('cli.commands.invoice_commands.format_validation_summary', 
                          return_value="Summary"):
                    result = _process_invoices(
                        input_path=pdf_path,
                        output_path=output_path,
                        output_format='csv',
                        validation_mode='parts_based',
                        threshold=Decimal('0.30'),
                        interactive=False,
                        collect_unknown=True,
                        session_id=str(uuid.uuid4()),
                        db_manager=self.mock_db_manager
                    )
            
            # Verify result structure
            assert isinstance(result, dict)
            assert 'files_processed' in result
            assert 'files_failed' in result
            assert 'anomalies_found' in result
            assert 'report_file' in result
            assert result['files_processed'] == 1
            assert result['anomalies_found'] == 1
    
    def test_process_invoices_batch_integration(self):
        """Test complete processing workflow for multiple files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test directory with PDF files
            input_dir = Path(temp_dir) / "invoices"
            input_dir.mkdir()
            
            for i in range(2):
                pdf_path = input_dir / f"invoice_{i}.pdf"
                pdf_path.write_text(f"dummy pdf content {i}")
            
            output_path = Path(temp_dir) / "batch_report.csv"
            
            # Mock batch processing response
            batch_stats = {
                'successfully_processed': 2,
                'failed_processing': 0,
                'total_anomalies': 3,
                'unknown_parts_discovered': 1,
                'critical_anomalies': 1,
                'warning_anomalies': 2,
                'average_processing_time': 1.8
            }
            self.mock_workflow.process_invoices_batch.return_value = batch_stats
            
            with patch('cli.commands.invoice_commands.create_validation_workflow', 
                      return_value=self.mock_workflow):
                result = _process_invoices(
                    input_path=input_dir,
                    output_path=output_path,
                    output_format='csv',
                    validation_mode='threshold_based',
                    threshold=Decimal('0.25'),
                    interactive=True,
                    collect_unknown=False,
                    session_id=str(uuid.uuid4()),
                    db_manager=self.mock_db_manager
                )
            
            # Verify result structure
            assert isinstance(result, dict)
            assert result['files_processed'] == 2
            assert result['anomalies_found'] == 3
            assert result['unknown_parts'] == 1
    
    def test_process_invoices_handles_processing_error(self):
        """Test that ProcessingError is properly raised and handled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty directory (no PDFs)
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()
            output_path = Path(temp_dir) / "report.csv"
            
            with pytest.raises(ProcessingError, match="Invoice processing failed"):
                _process_invoices(
                    input_path=empty_dir,
                    output_path=output_path,
                    output_format='csv',
                    validation_mode='parts_based',
                    threshold=Decimal('0.30'),
                    interactive=False,
                    collect_unknown=False,
                    session_id=str(uuid.uuid4()),
                    db_manager=self.mock_db_manager
                )


class TestRefactoredFunctionBehavior:
    """Test that refactored functions maintain expected behavior patterns."""
    
    def test_functions_follow_single_responsibility_principle(self):
        """Test that each function has a single, well-defined responsibility."""
        # _discover_pdf_files should only handle file discovery
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("dummy")
            
            result = _discover_pdf_files(pdf_path)
            assert isinstance(result, list)
            assert all(isinstance(p, Path) for p in result)
        
        # _create_validation_config should only handle configuration creation
        mock_db = Mock()
        mock_db.get_config_value.side_effect = lambda k, d: d
        
        config = _create_validation_config('parts_based', Decimal('0.30'), True, False, mock_db)
        assert isinstance(config, ValidationConfiguration)
        
        # _generate_processing_results should only handle result formatting
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.csv"
            test_data = {'successful_validations': 1, 'total_anomalies': 0}
            
            result = _generate_processing_results(test_data, output_path)
            assert isinstance(result, dict)
            assert 'files_processed' in result
    
    def test_functions_have_clear_input_output_contracts(self):
        """Test that functions have well-defined input/output contracts."""
        # Test input validation and output consistency
        with tempfile.TemporaryDirectory() as temp_dir:
            # _discover_pdf_files: Path -> List[Path]
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("dummy")
            
            result = _discover_pdf_files(pdf_path)
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], Path)
            
            # _generate_processing_results: Dict, Path -> Dict
            test_data = {'successful_validations': 2}
            output_path = Path(temp_dir) / "report.csv"
            
            result = _generate_processing_results(test_data, output_path)
            assert isinstance(result, dict)
            assert 'files_processed' in result
            assert 'report_file' in result
            assert result['report_file'] == str(output_path)
    
    def test_error_handling_is_consistent(self):
        """Test that error handling is consistent across functions."""
        # _discover_pdf_files should raise ProcessingError for no files
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir)
            
            with pytest.raises(ProcessingError):
                _discover_pdf_files(empty_dir)
        
        # Functions should handle None/invalid inputs gracefully
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.csv"
            
            # Empty validation results should not crash
            result = _generate_processing_results({}, output_path)
            assert isinstance(result, dict)
            assert result['files_processed'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])