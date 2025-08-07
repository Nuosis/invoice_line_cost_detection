"""
CLI validation output tests for the Invoice Rate Detection System.

This module tests the CLI validation process by running actual CLI commands
and verifying the generated output matches expected patterns and contains
required validation information.
"""

import unittest
import tempfile
import shutil
import uuid
import subprocess
import sys
from pathlib import Path
from decimal import Decimal
import csv
import json

from database.database import DatabaseManager
from database.models import Part


class CLIValidationOutputTests(unittest.TestCase):
    """
    Test suite for validating CLI validation process output.
    
    These tests run the actual CLI validation process and verify
    that the generated reports contain expected validation results.
    """
    
    def setUp(self):
        """Set up test environment with real resources."""
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"cli_validation_test_{self.test_id}_"))
        
        # Create unique database file
        self.db_path = self.temp_dir / f"test_database_{self.test_id}.db"
        
        # Initialize database manager and add test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Define test invoice
        self.test_invoice_pdf = Path("docs/invoices/5790265785.pdf")
        
        # Skip test if required files are not available
        if not self.test_invoice_pdf.exists():
            self.skipTest(f"Required PDF file {self.test_invoice_pdf} not found")
        
        # Copy test invoice to temp directory
        self.test_invoice_copy = self.temp_dir / "test_invoice.pdf"
        shutil.copy2(self.test_invoice_pdf, self.test_invoice_copy)
        
        # Define output files
        self.output_csv = self.temp_dir / "validation_report.csv"
        self.output_json = self.temp_dir / "validation_report.json"
        self.output_txt = self.temp_dir / "validation_report.txt"
    
    def tearDown(self):
        """Clean up test resources."""
        try:
            # Close database connections
            if hasattr(self.db_manager, 'close'):
                self.db_manager.close()
            
            # Remove temporary directory
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Cleanup error in {self.__class__.__name__}: {e}")
    
    def _setup_test_parts(self):
        """Set up test parts in the database."""
        test_parts = [
            Part(
                part_number="GOS218NVOT",
                authorized_price=Decimal("0.750"),
                description="JACKET HIP EVIS 65/35",
                category="Outerwear",
                source="test"
            ),
            Part(
                part_number="GP0002CHAR",
                authorized_price=Decimal("0.300"),
                description="PANT WORK TWILL 65/35",
                category="Pants",
                source="test"
            ),
            Part(
                part_number="GS0007LGOT",
                authorized_price=Decimal("0.300"),
                description="SHIRT WORK LS 65/35",
                category="Shirts",
                source="test"
            ),
            Part(
                part_number="GS0019LGOT",
                authorized_price=Decimal("0.300"),
                description="SHIRT WORK SS 65/35",
                category="Shirts",
                source="test"
            )
        ]
        
        for part in test_parts:
            try:
                self.db_manager.create_part(part)
            except Exception:
                # Part might already exist, continue
                pass
    
    def test_cli_validation_csv_output(self):
        """Test CLI validation process generates valid CSV output."""
        # Run CLI validation command
        result = self._run_cli_validation('csv')
        
        # Verify command succeeded
        self.assertEqual(result.returncode, 0, f"CLI command failed: {result.stderr}")
        
        # Verify output file was created
        self.assertTrue(self.output_csv.exists(), "CSV output file should be created")
        
        # Verify CSV content
        self._verify_csv_output()
    
    def test_cli_validation_json_output(self):
        """Test CLI validation process generates valid JSON output."""
        # Run CLI validation command
        result = self._run_cli_validation('json')
        
        # Verify command succeeded
        self.assertEqual(result.returncode, 0, f"CLI command failed: {result.stderr}")
        
        # Verify output file was created
        self.assertTrue(self.output_json.exists(), "JSON output file should be created")
        
        # Verify JSON content
        self._verify_json_output()
    
    def test_cli_validation_txt_output(self):
        """Test CLI validation process generates valid TXT output."""
        # Run CLI validation command
        result = self._run_cli_validation('txt')
        
        # Verify command succeeded
        self.assertEqual(result.returncode, 0, f"CLI command failed: {result.stderr}")
        
        # Verify output file was created
        self.assertTrue(self.output_txt.exists(), "TXT output file should be created")
        
        # Verify TXT content
        self._verify_txt_output()
    
    def test_cli_validation_parts_based_mode(self):
        """Test CLI validation in parts-based mode."""
        # Run CLI validation with parts-based mode
        result = self._run_cli_validation('csv', validation_mode='parts_based')
        
        # Verify command succeeded
        self.assertEqual(result.returncode, 0, f"CLI command failed: {result.stderr}")
        
        # Verify output contains parts-based validation results
        self.assertTrue(self.output_csv.exists())
        
        # Read and verify CSV content
        with open(self.output_csv, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Should have validation results
        self.assertGreater(len(rows), 0, "Should have validation results")
        
        # Check for expected columns
        if rows:
            expected_columns = ['invoice_number', 'part_number', 'validation_status']
            for col in expected_columns:
                self.assertIn(col, rows[0].keys(), f"Column '{col}' should be present")
    
    def test_cli_validation_threshold_based_mode(self):
        """Test CLI validation in threshold-based mode."""
        # Run CLI validation with threshold-based mode
        result = self._run_cli_validation('csv', validation_mode='threshold_based', threshold='0.50')
        
        # Verify command succeeded
        self.assertEqual(result.returncode, 0, f"CLI command failed: {result.stderr}")
        
        # Verify output file was created
        self.assertTrue(self.output_csv.exists())
    
    def _run_cli_validation(self, output_format, validation_mode='parts_based', threshold='0.30'):
        """Run CLI validation command and return result."""
        output_file = getattr(self, f'output_{output_format}')
        
        cmd = [
            sys.executable, '-m', 'cli.main',
            'invoice', 'process',
            str(self.test_invoice_copy),
            '--output', str(output_file),
            '--format', output_format,
            '--validation-mode', validation_mode,
            '--threshold', threshold
        ]
        
        # Set environment variables
        env = {
            'PYTHONPATH': '.',
            'INVOICE_CHECKER_DB_PATH': str(self.db_path)
        }
        
        # Run command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            env={**dict(os.environ), **env} if 'os' in globals() else env
        )
        
        return result
    
    def _verify_csv_output(self):
        """Verify CSV output contains expected validation data."""
        with open(self.output_csv, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Should have some validation results
        self.assertGreater(len(rows), 0, "CSV should contain validation results")
        
        # Check for required columns
        if rows:
            first_row = rows[0]
            required_columns = ['invoice_number', 'invoice_date']
            for col in required_columns:
                self.assertIn(col, first_row.keys(), f"Required column '{col}' missing")
            
            # Verify invoice number is correct
            self.assertEqual(first_row['invoice_number'], '5790265785')
    
    def _verify_json_output(self):
        """Verify JSON output contains expected validation data."""
        with open(self.output_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Should be a valid JSON structure
        self.assertIsInstance(data, (dict, list), "JSON should contain dict or list")
        
        # If it's a dict, check for expected keys
        if isinstance(data, dict):
            expected_keys = ['validation_results', 'summary']
            for key in expected_keys:
                if key in data:
                    self.assertIsNotNone(data[key], f"Key '{key}' should have value")
    
    def _verify_txt_output(self):
        """Verify TXT output contains expected validation data."""
        content = self.output_txt.read_text(encoding='utf-8')
        
        # Should have substantial content
        self.assertGreater(len(content), 100, "TXT output should have substantial content")
        
        # Should contain invoice information
        self.assertIn('5790265785', content, "Should contain invoice number")
        self.assertIn('validation', content.lower(), "Should contain validation information")


class CLIValidationIntegrationTests(unittest.TestCase):
    """
    Integration tests for CLI validation with different scenarios.
    """
    
    def setUp(self):
        """Set up test environment."""
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"cli_integration_test_{self.test_id}_"))
        
        # Create database
        self.db_path = self.temp_dir / f"integration_test_{self.test_id}.db"
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test invoice
        self.test_invoice_pdf = Path("docs/invoices/5790265785.pdf")
        if not self.test_invoice_pdf.exists():
            self.skipTest("Required PDF file not found")
        
        self.test_invoice_copy = self.temp_dir / "test_invoice.pdf"
        shutil.copy2(self.test_invoice_pdf, self.test_invoice_copy)
    
    def tearDown(self):
        """Clean up test resources."""
        try:
            if hasattr(self.db_manager, 'close'):
                self.db_manager.close()
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Cleanup error in {self.__class__.__name__}: {e}")
    
    def test_cli_validation_with_empty_database(self):
        """Test CLI validation with empty parts database."""
        output_file = self.temp_dir / "empty_db_report.csv"
        
        cmd = [
            sys.executable, '-m', 'cli.main',
            'invoice', 'process',
            str(self.test_invoice_copy),
            '--output', str(output_file),
            '--format', 'csv',
            '--validation-mode', 'parts_based'
        ]
        
        env = {
            'PYTHONPATH': '.',
            'INVOICE_CHECKER_DB_PATH': str(self.db_path)
        }
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            env={**dict(os.environ), **env} if 'os' in globals() else env
        )
        
        # Should complete successfully even with empty database
        self.assertEqual(result.returncode, 0, f"CLI should handle empty database: {result.stderr}")
        self.assertTrue(output_file.exists(), "Output file should be created")


if __name__ == '__main__':
    import os
    unittest.main()