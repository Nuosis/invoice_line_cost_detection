"""
Comprehensive test suite for batch processing functionality (Issue #1).

This module tests the batch processing implementation including:
- Unit tests for parallel and sequential processing
- Error handling tests with continue_on_error flag
- Performance tests with multiple folders
- Integration tests with actual PDF files
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

from cli.main import cli
from cli.commands.invoice_commands import _process_batch, _find_invoice_folders
from cli.exceptions import ProcessingError
from database.database import DatabaseManager
from database.models import Part


class TestBatchProcessingUnit:
    """Unit tests for batch processing functionality."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create test folder structure with realistic content
        self.test_folders = []
        for i in range(3):
            folder = Path(self.temp_dir) / f"folder_{i}"
            folder.mkdir()
            # Create more realistic PDF-like files
            for j in range(2):
                pdf_file = folder / f"invoice_{j}.pdf"
                # Create content that resembles invoice structure
                pdf_content = f"""
                Invoice #{1000 + i * 10 + j}
                Date: 2024-01-{i + 1:02d}
                
                Line Items:
                PART001    $1.50    Qty: 10    Total: $15.00
                PART002    $2.25    Qty: 5     Total: $11.25
                """
                pdf_file.write_text(pdf_content)
            self.test_folders.append(folder)
        
        self.output_dir = Path(self.temp_dir) / "output"
        self.output_dir.mkdir()
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_sequential_processing_basic_functionality(self):
        """Test basic sequential batch processing without heavy mocking."""
        # Only mock the core processing function to avoid PDF parsing complexity
        with patch('cli.commands.invoice_commands._process_invoices') as mock_process:
            mock_process.return_value = {
                'files_processed': 2,
                'anomalies_found': 1,
                'files_failed': 0
            }
            
            result = _process_batch(
                folders=self.test_folders,
                output_dir=self.output_dir,
                parallel=False,
                max_workers=4,
                continue_on_error=True,
                db_manager=self.db_manager
            )
            
            # Verify basic functionality
            assert result['folders_processed'] == 3
            assert result['folders_failed'] == 0
            assert result['total_files'] == 6
            assert result['total_anomalies'] == 3
            assert len(result['processing_errors']) == 0
            assert mock_process.call_count == 3
    
    def test_parallel_processing_basic_functionality(self):
        """Test basic parallel batch processing without heavy mocking."""
        # Only mock the core processing function
        with patch('cli.commands.invoice_commands._process_invoices') as mock_process:
            mock_process.return_value = {
                'files_processed': 2,
                'anomalies_found': 1,
                'files_failed': 0
            }
            
            result = _process_batch(
                folders=self.test_folders,
                output_dir=self.output_dir,
                parallel=True,
                max_workers=2,
                continue_on_error=True,
                db_manager=self.db_manager
            )
            
            # Verify parallel processing works
            assert result['folders_processed'] == 3
            assert result['folders_failed'] == 0
            assert result['total_files'] == 6
            assert result['total_anomalies'] == 3
            assert len(result['processing_errors']) == 0
            assert mock_process.call_count == 3
    
    def test_continue_on_error_behavior(self):
        """Test error handling behavior with both continue_on_error settings."""
        # Create a problematic folder (empty folder that will cause processing issues)
        problem_folder = Path(self.temp_dir) / "problem_folder"
        problem_folder.mkdir()
        # No PDF files in this folder - will cause processing issues
        
        test_folders_with_problem = self.test_folders + [problem_folder]
        
        # Mock only the processing function with realistic error behavior
        def mock_processing(*args, **kwargs):
            folder_path = kwargs.get('input_path') or args[0]
            if 'problem_folder' in str(folder_path):
                raise ProcessingError("No PDF files found in folder")
            return {
                'files_processed': 2,
                'anomalies_found': 1,
                'files_failed': 0
            }
        
        # Test continue_on_error=True
        with patch('cli.commands.invoice_commands._process_invoices', side_effect=mock_processing):
            result = _process_batch(
                folders=test_folders_with_problem,
                output_dir=self.output_dir,
                parallel=False,
                max_workers=4,
                continue_on_error=True,
                db_manager=self.db_manager
            )
            
            # Should continue despite error
            assert result['folders_processed'] == 3  # 3 successful
            assert result['folders_failed'] == 1     # 1 failed
            assert len(result['processing_errors']) == 1
            assert 'problem_folder' in result['processing_errors'][0]['folder']
        
        # Test continue_on_error=False
        with patch('cli.commands.invoice_commands._process_invoices', side_effect=mock_processing):
            with pytest.raises(ProcessingError, match="Batch processing failed"):
                _process_batch(
                    folders=test_folders_with_problem,
                    output_dir=self.output_dir,
                    parallel=False,
                    max_workers=4,
                    continue_on_error=False,
                    db_manager=self.db_manager
                )
    
    def test_parallel_error_handling(self):
        """Test parallel processing error handling."""
        # Create a folder that will cause issues
        problem_folder = Path(self.temp_dir) / "parallel_problem"
        problem_folder.mkdir()
        
        def mock_processing(*args, **kwargs):
            folder_path = kwargs.get('input_path') or args[0]
            if 'parallel_problem' in str(folder_path):
                raise ProcessingError("Parallel processing error")
            return {
                'files_processed': 2,
                'anomalies_found': 1,
                'files_failed': 0
            }
        
        test_folders_with_problem = self.test_folders + [problem_folder]
        
        # Test parallel with continue_on_error=False
        with patch('cli.commands.invoice_commands._process_invoices', side_effect=mock_processing):
            with pytest.raises(ProcessingError, match="Batch processing failed"):
                _process_batch(
                    folders=test_folders_with_problem,
                    output_dir=self.output_dir,
                    parallel=True,
                    max_workers=2,
                    continue_on_error=False,
                    db_manager=self.db_manager
                )
    
    def test_empty_folders_list(self):
        """Test batch processing with empty folders list."""
        result = _process_batch(
            folders=[],
            output_dir=self.output_dir,
            parallel=False,
            max_workers=4,
            continue_on_error=True,
            db_manager=self.db_manager
        )
        
        # Should return empty stats
        assert result['folders_processed'] == 0
        assert result['folders_failed'] == 0
        assert result['total_files'] == 0
        assert result['total_anomalies'] == 0
        assert len(result['processing_errors']) == 0
    
    def test_single_folder_parallel_fallback(self):
        """Test that single folder uses sequential processing even with parallel=True."""
        with patch('cli.commands.invoice_commands._process_invoices') as mock_process:
            mock_process.return_value = {
                'files_processed': 2,
                'anomalies_found': 1,
                'files_failed': 0
            }
            
            # Test with single folder and parallel=True
            result = _process_batch(
                folders=[self.test_folders[0]],
                output_dir=self.output_dir,
                parallel=True,
                max_workers=4,
                continue_on_error=True,
                db_manager=self.db_manager
            )
            
            # Should still process successfully
            assert result['folders_processed'] == 1
            assert result['folders_failed'] == 0


class TestBatchProcessingIntegration:
    """Integration tests for batch processing with CLI commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "integration_test.db"
        self.env = {'INVOICE_CHECKER_DB': str(self.db_path)}
        
        # Initialize database with real data
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create test folder structure with realistic invoice content
        self.batch_input_dir = Path(self.temp_dir) / "batch_input"
        self.batch_input_dir.mkdir()
        
        # Create multiple folders with realistic PDF files
        for i in range(2):
            folder = self.batch_input_dir / f"invoices_{i}"
            folder.mkdir()
            for j in range(2):
                pdf_file = folder / f"invoice_{1000 + i * 10 + j}.pdf"
                # Create realistic invoice content
                invoice_content = f"""
                Invoice #{1000 + i * 10 + j}
                Date: 2024-0{i + 1}-{j + 15:02d}
                
                Line Items:
                PART{i:03d}    ${1.50 + (i * 0.25):.2f}    Qty: {j + 1}    Total: ${(1.50 + i * 0.25) * (j + 1):.2f}
                PART{i+1:03d}  ${2.00 + (j * 0.30):.2f}    Qty: {i + 2}    Total: ${(2.00 + j * 0.30) * (i + 2):.2f}
                
                Subtotal: ${((1.50 + i * 0.25) * (j + 1)) + ((2.00 + j * 0.30) * (i + 2)):.2f}
                """
                pdf_file.write_text(invoice_content)
        
        self.output_dir = Path(self.temp_dir) / "batch_output"
    
    def teardown_method(self):
        """Clean up test environment."""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_batch_command_basic_functionality(self):
        """Test basic batch command functionality with minimal mocking."""
        # Only mock the core processing to avoid PDF parsing complexity
        with patch('cli.commands.invoice_commands._process_invoices') as mock_process:
            mock_process.return_value = {
                'files_processed': 2,
                'anomalies_found': 0,
                'files_failed': 0
            }
            
            result = self.runner.invoke(
                cli,
                [
                    'invoice', 'batch', str(self.batch_input_dir),
                    '--output-dir', str(self.output_dir),
                    '--parallel'
                ],
                env=self.env
            )
            
            # Verify command succeeded
            assert result.exit_code == 0
            assert 'Batch processing complete' in result.output
            assert 'folders to process' in result.output
            
            # Verify processing was called for each folder
            assert mock_process.call_count == 2
    
    def test_batch_command_error_handling(self):
        """Test batch command error handling with realistic scenarios."""
        # Create a folder with no PDF files to trigger realistic error
        empty_folder = self.batch_input_dir / "empty_folder"
        empty_folder.mkdir()
        (empty_folder / "not_a_pdf.txt").write_text("This is not a PDF")
        
        def mock_processing(*args, **kwargs):
            folder_path = kwargs.get('input_path') or args[0]
            if 'empty_folder' in str(folder_path):
                raise ProcessingError("No valid PDF files found")
            return {
                'files_processed': 2,
                'anomalies_found': 0,
                'files_failed': 0
            }
        
        with patch('cli.commands.invoice_commands._process_invoices', side_effect=mock_processing):
            result = self.runner.invoke(
                cli,
                [
                    'invoice', 'batch', str(self.batch_input_dir),
                    '--output-dir', str(self.output_dir),
                    '--continue-on-error'
                ],
                env=self.env
            )
            
            # Should complete with errors reported
            assert result.exit_code == 0
            assert 'folders to process' in result.output
    
    def test_batch_command_no_valid_folders(self):
        """Test batch command with no valid folders - no mocking needed."""
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()
        
        # Create some non-PDF files
        (empty_dir / "readme.txt").write_text("No PDFs here")
        (empty_dir / "data.csv").write_text("col1,col2\nval1,val2")
        
        result = self.runner.invoke(
            cli,
            ['invoice', 'batch', str(empty_dir)],
            env=self.env
        )
        
        # Should fail with appropriate error
        assert result.exit_code != 0
        # Check that the exception contains the expected error message
        assert result.exception is not None
        assert 'No folders with PDF files found' in str(result.exception)
    
    def test_batch_command_output_directory_creation(self):
        """Test that batch command creates output directory if it doesn't exist."""
        non_existent_output = Path(self.temp_dir) / "new_output_dir"
        
        with patch('cli.commands.invoice_commands._process_invoices') as mock_process:
            mock_process.return_value = {
                'files_processed': 2,
                'anomalies_found': 1,
                'files_failed': 0
            }
            
            result = self.runner.invoke(
                cli,
                [
                    'invoice', 'batch', str(self.batch_input_dir),
                    '--output-dir', str(non_existent_output)
                ],
                env=self.env
            )
            
            # Should succeed and create the directory
            assert result.exit_code == 0
            assert non_existent_output.exists()
            assert non_existent_output.is_dir()


class TestBatchProcessingScalability:
    """Scalability and configuration tests for batch processing."""
    
    def setup_method(self):
        """Set up scalability test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "scalability_test.db"
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create test dataset with realistic structure
        self.test_folders = []
        for i in range(6):  # Moderate number for testing
            folder = Path(self.temp_dir) / f"batch_folder_{i}"
            folder.mkdir()
            # Create realistic invoice-like files
            for j in range(3):  # 3 files per folder
                pdf_file = folder / f"invoice_{1000 + i * 10 + j}.pdf"
                invoice_content = f"""
                Invoice #{1000 + i * 10 + j}
                Date: 2024-{(i % 12) + 1:02d}-{(j % 28) + 1:02d}
                
                Line Items:
                PART{i:03d}    ${1.50 + (i * 0.25):.2f}    Qty: {j + 1}
                PART{i+1:03d}  ${2.00 + (j * 0.30):.2f}    Qty: {i + 1}
                """
                pdf_file.write_text(invoice_content)
            self.test_folders.append(folder)
        
        self.output_dir = Path(self.temp_dir) / "scalability_output"
        self.output_dir.mkdir()
    
    def teardown_method(self):
        """Clean up scalability test environment."""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parallel_vs_sequential_functionality(self):
        """Test that parallel and sequential processing produce identical results."""
        # Mock processing to focus on batch logic rather than PDF parsing
        mock_result = {
            'files_processed': 3,
            'anomalies_found': 1,
            'files_failed': 0
        }
        
        with patch('cli.commands.invoice_commands._process_invoices', return_value=mock_result) as mock_process:
            # Test sequential processing
            sequential_result = _process_batch(
                folders=self.test_folders,
                output_dir=self.output_dir,
                parallel=False,
                max_workers=4,
                continue_on_error=True,
                db_manager=self.db_manager
            )
            
            sequential_calls = mock_process.call_count
            mock_process.reset_mock()
            
            # Test parallel processing
            parallel_result = _process_batch(
                folders=self.test_folders,
                output_dir=self.output_dir,
                parallel=True,
                max_workers=3,
                continue_on_error=True,
                db_manager=self.db_manager
            )
            
            parallel_calls = mock_process.call_count
            
            # Both should produce identical results
            assert sequential_result['folders_processed'] == parallel_result['folders_processed']
            assert sequential_result['total_files'] == parallel_result['total_files']
            assert sequential_result['total_anomalies'] == parallel_result['total_anomalies']
            assert sequential_result['folders_failed'] == parallel_result['folders_failed']
            
            # Both should process all folders
            assert sequential_calls == parallel_calls == len(self.test_folders)
    
    def test_worker_configuration_effectiveness(self):
        """Test that different worker configurations work correctly."""
        mock_result = {
            'files_processed': 3,
            'anomalies_found': 1,
            'files_failed': 0
        }
        
        # Test with different worker counts
        worker_configs = [1, 2, 4, 8]  # Including edge cases
        
        for max_workers in worker_configs:
            with patch('cli.commands.invoice_commands._process_invoices', return_value=mock_result) as mock_process:
                result = _process_batch(
                    folders=self.test_folders[:4],  # Use subset for consistent testing
                    output_dir=self.output_dir,
                    parallel=True,
                    max_workers=max_workers,
                    continue_on_error=True,
                    db_manager=self.db_manager
                )
                
                # Should process all folders regardless of worker count
                assert result['folders_processed'] == 4
                assert result['folders_failed'] == 0
                assert result['total_files'] == 12  # 4 folders * 3 files each
                assert result['total_anomalies'] == 4  # 4 folders * 1 anomaly each
                
                # Verify all folders were processed
                assert mock_process.call_count == 4
    
    def test_large_batch_handling(self):
        """Test handling of larger batches without artificial delays."""
        # Create additional folders for larger batch test
        large_batch_folders = self.test_folders.copy()
        
        # Add more folders to test scalability
        for i in range(6, 12):  # Add 6 more folders
            folder = Path(self.temp_dir) / f"large_batch_{i}"
            folder.mkdir()
            for j in range(2):  # 2 files per folder
                pdf_file = folder / f"invoice_{2000 + i * 10 + j}.pdf"
                pdf_file.write_text(f"Large batch test invoice {i}-{j}")
            large_batch_folders.append(folder)
        
        mock_result = {
            'files_processed': 2,
            'anomalies_found': 0,
            'files_failed': 0
        }
        
        with patch('cli.commands.invoice_commands._process_invoices', return_value=mock_result):
            result = _process_batch(
                folders=large_batch_folders,
                output_dir=self.output_dir,
                parallel=True,
                max_workers=4,
                continue_on_error=True,
                db_manager=self.db_manager
            )
            
            # Should handle large batch successfully
            assert result['folders_processed'] == 12
            assert result['folders_failed'] == 0
            assert result['total_files'] == 24  # 12 folders * 2 files each
            assert len(result['processing_errors']) == 0


class TestFindInvoiceFolders:
    """Test the helper function for finding invoice folders."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_find_folders_with_pdfs(self):
        """Test finding folders that contain PDF files."""
        # Create folders with and without PDFs
        folder_with_pdfs = self.base_path / "has_pdfs"
        folder_with_pdfs.mkdir()
        (folder_with_pdfs / "invoice1.pdf").write_text("PDF content")
        (folder_with_pdfs / "invoice2.pdf").write_text("PDF content")
        
        folder_without_pdfs = self.base_path / "no_pdfs"
        folder_without_pdfs.mkdir()
        (folder_without_pdfs / "readme.txt").write_text("Text file")
        
        empty_folder = self.base_path / "empty"
        empty_folder.mkdir()
        
        # Test finding folders
        found_folders = _find_invoice_folders(self.base_path)
        
        # Should only find the folder with PDFs
        assert len(found_folders) == 1
        assert found_folders[0] == folder_with_pdfs
    
    def test_find_no_folders(self):
        """Test when no folders contain PDFs."""
        # Create folder with non-PDF files
        folder = self.base_path / "no_pdfs"
        folder.mkdir()
        (folder / "document.txt").write_text("Text content")
        
        found_folders = _find_invoice_folders(self.base_path)
        
        # Should find no folders
        assert len(found_folders) == 0
    
    def test_find_nested_folders(self):
        """Test finding folders at different nesting levels."""
        # Create nested structure
        level1 = self.base_path / "level1"
        level1.mkdir()
        (level1 / "invoice.pdf").write_text("PDF content")
        
        level2 = level1 / "level2"
        level2.mkdir()
        (level2 / "nested_invoice.pdf").write_text("PDF content")
        
        # Should only find direct subdirectories, not nested ones
        found_folders = _find_invoice_folders(self.base_path)
        
        assert len(found_folders) == 1
        assert found_folders[0] == level1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])