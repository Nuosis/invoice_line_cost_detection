"""
Expectation document generator tests for the Invoice Rate Detection System.

This module creates and manages expectation documents that define the expected
validation results for test invoices. It generates templates and compares
actual results against expected outcomes.
"""

import unittest
import tempfile
import shutil
import uuid
import json
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List

from processing.pdf_processor import PDFProcessor
from processing.validation_engine import ValidationEngine
from database.database import DatabaseManager
from database.models import Part


class ExpectationDocumentGenerator:
    """
    Generates and manages expectation documents for validation testing.
    
    This class creates template expectation documents based on actual
    validation results and provides methods to compare results against
    expectations.
    """
    
    def __init__(self, temp_dir: Path):
        """Initialize the expectation generator."""
        self.temp_dir = temp_dir
        self.expectations_dir = temp_dir / "expectations"
        self.expectations_dir.mkdir(exist_ok=True)
    
    def generate_expectation_template(self, invoice_path: Path, 
                                    validation_engine: ValidationEngine) -> Dict[str, Any]:
        """
        Generate an expectation template based on actual validation results.
        
        Args:
            invoice_path: Path to the invoice PDF
            validation_engine: Validation engine to use for processing
            
        Returns:
            Dictionary containing expectation template
        """
        # Process the invoice
        validation_result = validation_engine.validate_invoice(invoice_path)
        
        # Extract key metrics and results
        template = {
            "invoice_metadata": {
                "invoice_number": validation_result.invoice_number,
                "invoice_date": validation_result.invoice_date,
                "invoice_path": str(invoice_path.name)
            },
            "processing_expectations": {
                "should_process_successfully": validation_result.processing_successful,
                "should_be_valid": validation_result.is_valid,
                "expected_processing_time_max_seconds": 30.0
            },
            "line_items_expectations": {
                "expected_total_line_items_min": max(1, len(validation_result.parts_lookup_results) - 5),
                "expected_total_line_items_max": len(validation_result.parts_lookup_results) + 5,
                "expected_valid_line_items_min": max(0, len([r for r in validation_result.parts_lookup_results if r.is_valid]) - 2),
                "expected_format_sections_count": 4
            },
            "validation_expectations": {
                "expected_critical_anomalies_max": len(validation_result.critical_anomalies) + 2,
                "expected_warning_anomalies_max": len(validation_result.warning_anomalies) + 5,
                "expected_unknown_parts_max": len([r for r in validation_result.parts_lookup_results 
                                                 if not r.is_valid and "unknown" in r.message.lower()]) + 3
            },
            "format_sections_expectations": {
                "should_have_subtotal": True,
                "should_have_freight": True,
                "should_have_tax": True,
                "should_have_total": True,
                "sections_should_be_in_order": True
            },
            "specific_validations": {
                "invoice_number_should_be_numeric": True,
                "invoice_date_should_be_present": True,
                "total_amount_should_be_positive": True
            },
            "template_metadata": {
                "generated_at": datetime.now().isoformat(),
                "generated_from_actual_results": True,
                "template_version": "1.0",
                "notes": "Auto-generated template - manually review and adjust expected values"
            }
        }
        
        return template
    
    def save_expectation_template(self, invoice_name: str, template: Dict[str, Any]) -> Path:
        """
        Save expectation template to file.
        
        Args:
            invoice_name: Name of the invoice (without extension)
            template: Template dictionary to save
            
        Returns:
            Path to saved template file
        """
        template_file = self.expectations_dir / f"{invoice_name}_expectations.json"
        
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, default=str)
        
        return template_file
    
    def load_expectation_template(self, invoice_name: str) -> Dict[str, Any]:
        """
        Load expectation template from file.
        
        Args:
            invoice_name: Name of the invoice (without extension)
            
        Returns:
            Template dictionary
        """
        template_file = self.expectations_dir / f"{invoice_name}_expectations.json"
        
        if not template_file.exists():
            raise FileNotFoundError(f"Expectation template not found: {template_file}")
        
        with open(template_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def compare_results_to_expectations(self, validation_result, expectations: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare actual validation results to expectations.
        
        Args:
            validation_result: Actual validation result
            expectations: Expected results dictionary
            
        Returns:
            Comparison results dictionary
        """
        comparison = {
            "overall_match": True,
            "mismatches": [],
            "metadata_comparison": {},
            "processing_comparison": {},
            "line_items_comparison": {},
            "validation_comparison": {},
            "format_sections_comparison": {}
        }
        
        # Compare metadata
        meta_exp = expectations.get("invoice_metadata", {})
        if meta_exp.get("invoice_number") != validation_result.invoice_number:
            comparison["mismatches"].append({
                "category": "metadata",
                "field": "invoice_number",
                "expected": meta_exp.get("invoice_number"),
                "actual": validation_result.invoice_number
            })
            comparison["overall_match"] = False
        
        # Compare processing expectations
        proc_exp = expectations.get("processing_expectations", {})
        if proc_exp.get("should_process_successfully") != validation_result.processing_successful:
            comparison["mismatches"].append({
                "category": "processing",
                "field": "processing_successful",
                "expected": proc_exp.get("should_process_successfully"),
                "actual": validation_result.processing_successful
            })
            comparison["overall_match"] = False
        
        # Compare line items expectations
        line_exp = expectations.get("line_items_expectations", {})
        actual_line_items = len(validation_result.parts_lookup_results)
        min_expected = line_exp.get("expected_total_line_items_min", 0)
        max_expected = line_exp.get("expected_total_line_items_max", 999)
        
        if not (min_expected <= actual_line_items <= max_expected):
            comparison["mismatches"].append({
                "category": "line_items",
                "field": "total_line_items_count",
                "expected_range": f"{min_expected}-{max_expected}",
                "actual": actual_line_items
            })
            comparison["overall_match"] = False
        
        # Compare validation expectations
        val_exp = expectations.get("validation_expectations", {})
        actual_critical = len(validation_result.critical_anomalies)
        max_critical = val_exp.get("expected_critical_anomalies_max", 999)
        
        if actual_critical > max_critical:
            comparison["mismatches"].append({
                "category": "validation",
                "field": "critical_anomalies_count",
                "expected_max": max_critical,
                "actual": actual_critical
            })
            comparison["overall_match"] = False
        
        return comparison


class ExpectationGeneratorTests(unittest.TestCase):
    """
    Test suite for expectation document generation and comparison.
    """
    
    def setUp(self):
        """Set up test environment."""
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"expectation_test_{self.test_id}_"))
        
        # Initialize components
        self.db_path = self.temp_dir / f"test_db_{self.test_id}.db"
        self.db_manager = DatabaseManager(str(self.db_path))
        self.validation_engine = ValidationEngine(self.db_manager)
        self.expectation_generator = ExpectationDocumentGenerator(self.temp_dir)
        
        # Setup test parts
        self._setup_test_parts()
        
        # Test invoice
        self.test_invoice_pdf = Path("docs/invoices/5790265785.pdf")
        if not self.test_invoice_pdf.exists():
            self.skipTest("Required PDF file not found")
    
    def tearDown(self):
        """Clean up test resources."""
        try:
            if hasattr(self.db_manager, 'close'):
                self.db_manager.close()
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Cleanup error in {self.__class__.__name__}: {e}")
    
    def _setup_test_parts(self):
        """Set up test parts in database."""
        test_parts = [
            Part(
                part_number="GOS218NVOT",
                authorized_price=Decimal("0.750"),
                description="JACKET HIP EVIS 65/35",
                source="test"
            ),
            Part(
                part_number="GP0002CHAR",
                authorized_price=Decimal("0.300"),
                description="PANT WORK TWILL 65/35",
                source="test"
            )
        ]
        
        for part in test_parts:
            try:
                self.db_manager.create_part(part)
            except Exception:
                pass
    
    def test_generate_expectation_template(self):
        """Test generating an expectation template from actual results."""
        # Generate template
        template = self.expectation_generator.generate_expectation_template(
            self.test_invoice_pdf, self.validation_engine
        )
        
        # Verify template structure
        self.assertIn("invoice_metadata", template)
        self.assertIn("processing_expectations", template)
        self.assertIn("line_items_expectations", template)
        self.assertIn("validation_expectations", template)
        self.assertIn("template_metadata", template)
        
        # Verify metadata
        metadata = template["invoice_metadata"]
        self.assertEqual(metadata["invoice_number"], "5790265785")
        self.assertEqual(metadata["invoice_date"], "07/17/2025")
        
        # Verify processing expectations
        proc_exp = template["processing_expectations"]
        self.assertIn("should_process_successfully", proc_exp)
        self.assertIn("should_be_valid", proc_exp)
        
        # Verify line items expectations
        line_exp = template["line_items_expectations"]
        self.assertIn("expected_total_line_items_min", line_exp)
        self.assertIn("expected_total_line_items_max", line_exp)
        self.assertEqual(line_exp["expected_format_sections_count"], 4)
    
    def test_save_and_load_expectation_template(self):
        """Test saving and loading expectation templates."""
        # Generate template
        template = self.expectation_generator.generate_expectation_template(
            self.test_invoice_pdf, self.validation_engine
        )
        
        # Save template
        template_file = self.expectation_generator.save_expectation_template(
            "5790265785", template
        )
        
        # Verify file was created
        self.assertTrue(template_file.exists())
        
        # Load template
        loaded_template = self.expectation_generator.load_expectation_template("5790265785")
        
        # Verify loaded template matches original
        self.assertEqual(loaded_template["invoice_metadata"]["invoice_number"], 
                        template["invoice_metadata"]["invoice_number"])
        self.assertEqual(loaded_template["processing_expectations"]["should_process_successfully"],
                        template["processing_expectations"]["should_process_successfully"])
    
    def test_compare_results_to_expectations(self):
        """Test comparing actual results to expectations."""
        # Generate template from actual results
        template = self.expectation_generator.generate_expectation_template(
            self.test_invoice_pdf, self.validation_engine
        )
        
        # Run validation again to get results
        validation_result = self.validation_engine.validate_invoice(self.test_invoice_pdf)
        
        # Compare results to expectations
        comparison = self.expectation_generator.compare_results_to_expectations(
            validation_result, template
        )
        
        # Should match since template was generated from same results
        self.assertTrue(comparison["overall_match"], 
                       f"Results should match template: {comparison['mismatches']}")
        self.assertEqual(len(comparison["mismatches"]), 0)
    
    def test_expectation_template_with_modified_expectations(self):
        """Test comparison with modified expectations to verify mismatch detection."""
        # Generate template
        template = self.expectation_generator.generate_expectation_template(
            self.test_invoice_pdf, self.validation_engine
        )
        
        # Modify expectations to create mismatches
        template["invoice_metadata"]["invoice_number"] = "WRONG_NUMBER"
        template["processing_expectations"]["should_process_successfully"] = False
        
        # Run validation
        validation_result = self.validation_engine.validate_invoice(self.test_invoice_pdf)
        
        # Compare results
        comparison = self.expectation_generator.compare_results_to_expectations(
            validation_result, template
        )
        
        # Should detect mismatches
        self.assertFalse(comparison["overall_match"])
        self.assertGreater(len(comparison["mismatches"]), 0)
        
        # Verify specific mismatches
        mismatch_fields = [m["field"] for m in comparison["mismatches"]]
        self.assertIn("invoice_number", mismatch_fields)
        self.assertIn("processing_successful", mismatch_fields)
    
    def test_expectation_template_file_not_found(self):
        """Test handling of missing expectation template files."""
        with self.assertRaises(FileNotFoundError):
            self.expectation_generator.load_expectation_template("nonexistent_invoice")


class ExpectationTemplateValidationTests(unittest.TestCase):
    """
    Test suite for validating expectation template structure and content.
    """
    
    def setUp(self):
        """Set up test environment."""
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"template_validation_test_{self.test_id}_"))
        self.expectation_generator = ExpectationDocumentGenerator(self.temp_dir)
    
    def tearDown(self):
        """Clean up test resources."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Cleanup error in {self.__class__.__name__}: {e}")
    
    def test_expectation_template_required_fields(self):
        """Test that expectation templates contain all required fields."""
        # Create a sample template
        template = {
            "invoice_metadata": {
                "invoice_number": "TEST123",
                "invoice_date": "01/01/2025",
                "invoice_path": "test.pdf"
            },
            "processing_expectations": {
                "should_process_successfully": True,
                "should_be_valid": True
            },
            "line_items_expectations": {
                "expected_total_line_items_min": 10,
                "expected_total_line_items_max": 50,
                "expected_format_sections_count": 4
            },
            "validation_expectations": {
                "expected_critical_anomalies_max": 0,
                "expected_warning_anomalies_max": 5
            },
            "template_metadata": {
                "generated_at": datetime.now().isoformat(),
                "template_version": "1.0"
            }
        }
        
        # Verify required sections exist
        required_sections = [
            "invoice_metadata",
            "processing_expectations", 
            "line_items_expectations",
            "validation_expectations",
            "template_metadata"
        ]
        
        for section in required_sections:
            self.assertIn(section, template, f"Required section '{section}' missing")
        
        # Verify required fields in each section
        self.assertIn("invoice_number", template["invoice_metadata"])
        self.assertIn("should_process_successfully", template["processing_expectations"])
        self.assertIn("expected_total_line_items_min", template["line_items_expectations"])
        self.assertIn("expected_critical_anomalies_max", template["validation_expectations"])
        self.assertIn("template_version", template["template_metadata"])


if __name__ == '__main__':
    unittest.main()