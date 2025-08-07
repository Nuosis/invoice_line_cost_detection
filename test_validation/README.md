# Validation Test Suite

This directory contains comprehensive validation tests for the Invoice Rate Detection System. The validation test suite verifies the accuracy and reliability of the entire invoice processing pipeline, from PDF text extraction to final validation reports.

## Overview

The validation test suite consists of three main components:

1. **Text Extraction Validation** - Verifies PDF text extraction accuracy
2. **CLI Validation Output** - Tests the CLI validation process and output generation
3. **Expectation Document Management** - Creates and manages expected validation results

## Test Structure

```
test_validation/
├── __init__.py                           # Package initialization
├── README.md                            # This documentation
├── run_validation_tests.py              # Main test runner
├── test_text_extraction_validation.py   # Text extraction tests
├── test_cli_validation_output.py        # CLI validation tests
├── test_expectation_generator.py        # Expectation management tests
└── expectations/                        # Expected results templates
    └── 5790265785_expectations.json     # Sample expectation template
```

## Running Tests

### Quick Start

Run all validation tests:

```bash
# From project root
PYTHONPATH=. python test_validation/run_validation_tests.py
```

### Individual Test Suites

Run specific test categories:

```bash
# Text extraction validation only
PYTHONPATH=. python -m pytest test_validation/test_text_extraction_validation.py -v

# CLI validation output only
PYTHONPATH=. python -m pytest test_validation/test_cli_validation_output.py -v

# Expectation generator only
PYTHONPATH=. python -m pytest test_validation/test_expectation_generator.py -v
```

### Integration with Existing Test Framework

The validation tests integrate with the existing test framework:

```bash
# Run with other unit tests
PYTHONPATH=. python -m pytest tests_unit/ test_validation/ -v

# Run with e2e tests
PYTHONPATH=. python -m pytest tests_e2e/ test_validation/ -v
```

## Test Categories

### 1. Text Extraction Validation Tests

**Purpose**: Verify that PDF text extraction produces accurate and consistent results.

**What it tests**:
- PDF text extraction accuracy against known extracted text files
- Invoice metadata extraction (invoice number, date, customer info)
- Line item extraction count and quality
- Format section extraction (SUBTOTAL, FREIGHT, TAX, TOTAL)
- Specific line item validation for known parts

**Key test files**:
- `test_text_extraction_validation.py`
- Uses `docs/invoices/5790265785.pdf` and `docs/invoices/output/5790265785_extracted_text.txt`
- run `extract_invoice_text.py` to generate text if does not exist 

**Example test**:
```python
def test_text_extraction_basic_accuracy(self):
    """Test that PDF text extraction produces reasonable output."""
    invoice_data = self.pdf_processor.process_pdf(self.test_invoice_pdf)
    
    # Verify basic extraction
    self.assertGreater(len(invoice_data.raw_text), 1000)
    self.assertIn("5790265785", invoice_data.raw_text)
    self.assertEqual(invoice_data.invoice_number, "5790265785")
```

### 2. CLI Validation Output Tests

**Purpose**: Verify that the CLI validation process generates correct output in various formats.

**What it tests**:
- CLI command execution and success
- Output file generation (CSV, JSON, TXT formats)
- Parts-based vs threshold-based validation modes
- Database integration during CLI processing
- Error handling with empty databases

**Key test files**:
- `test_cli_validation_output.py`
- Uses actual CLI commands via subprocess

**Example test**:
```python
def test_cli_validation_csv_output(self):
    """Test CLI validation process generates valid CSV output."""
    result = self._run_cli_validation('csv')
    
    # Verify command succeeded and output exists
    self.assertEqual(result.returncode, 0)
    self.assertTrue(self.output_csv.exists())
    self._verify_csv_output()
```

### 3. Expectation Document Management Tests

**Purpose**: Create and manage expectation templates that define expected validation results.

**What it tests**:
- Expectation template generation from actual results
- Template saving and loading
- Result comparison against expectations
- Mismatch detection and reporting
- Template structure validation

**Key test files**:
- `test_expectation_generator.py`
- `expectations/5790265785_expectations.json`

**Example expectation template**:
```json
{
  "invoice_metadata": {
    "invoice_number": "5790265785",
    "invoice_date": "07/17/2025"
  },
  "processing_expectations": {
    "should_process_successfully": true,
    "should_be_valid": true
  },
  "line_items_expectations": {
    "expected_total_line_items_min": 80,
    "expected_total_line_items_max": 120
  }
}
```

## Expectation Templates

Expectation templates define the expected behavior and results for validation tests. They serve as:

1. **Test Oracles** - Define what correct behavior looks like
2. **Regression Detection** - Catch when behavior changes unexpectedly
3. **Documentation** - Record expected system behavior
4. **Baseline Management** - Provide reference points for validation

### Template Structure

Each expectation template contains:

- **Invoice Metadata**: Expected invoice number, date, customer info
- **Processing Expectations**: Should processing succeed, validation pass
- **Line Items Expectations**: Expected counts and ranges
- **Validation Expectations**: Expected anomaly counts
- **Format Sections**: Expected SUBTOTAL, FREIGHT, TAX, TOTAL values
- **Specific Validations**: Detailed checks for known data points

### Creating New Templates

To create expectation templates for new invoices:

1. **Generate from actual results**:
```python
from test_validation.test_expectation_generator import ExpectationDocumentGenerator

generator = ExpectationDocumentGenerator(temp_dir)
template = generator.generate_expectation_template(invoice_path, validation_engine)
generator.save_expectation_template("invoice_name", template)
```

2. **Manually create** based on known invoice characteristics
3. **Review and adjust** generated templates for accuracy

### Template Maintenance

- **Review regularly** - Ensure templates reflect current expected behavior
- **Update when system changes** - Modify templates when validation logic changes
- **Version control** - Track template changes alongside code changes
- **Document changes** - Record why template values were modified

## Test Data Requirements

### Required Files

The validation tests require these files to be present:

1. **Test Invoice PDF**: `docs/invoices/5790265785.pdf`
2. **Expected Text Output**: `docs/invoices/output/5790265785_extracted_text.txt`
3. **Expectation Template**: `test_validation/expectations/5790265785_expectations.json`

### Test Database

Tests create temporary SQLite databases with test parts:
- GOS218NVOT (Jacket) - $0.750
- GP0002CHAR (Pants) - $0.300
- GS0007LGOT (Long Sleeve Shirt) - $0.300
- GS0019LGOT (Short Sleeve Shirt) - $0.300

## Integration Points

### With Existing Test Framework

The validation tests integrate with the existing test structure:

- **Follow same patterns** as `tests_unit/` and `tests_e2e/`
- **Use same cleanup strategies** with temporary files and databases
- **Compatible with pytest** and unittest frameworks
- **Respect existing test isolation** principles

### With CI/CD Pipeline

The validation tests are designed for CI/CD integration:

- **Exit codes** indicate pass/fail status
- **Detailed reporting** for debugging failures
- **Resource cleanup** prevents test pollution
- **Configurable verbosity** for different environments

## Troubleshooting

### Common Issues

1. **Missing test files**:
   ```
   FileNotFoundError: Required PDF file docs/invoices/5790265785.pdf not found
   ```
   **Solution**: Ensure test invoice files are present in the docs/invoices directory

2. **CLI command failures**:
   ```
   CLI command failed: ModuleNotFoundError: No module named 'cli'
   ```
   **Solution**: Ensure PYTHONPATH=. is set when running tests

3. **Database connection errors**:
   ```
   DatabaseError: Unable to connect to database
   ```
   **Solution**: Check that temporary directories are writable

4. **Expectation mismatches**:
   ```
   AssertionError: Results should match template: [{'category': 'metadata', ...}]
   ```
   **Solution**: Review and update expectation templates if system behavior has legitimately changed

### Debug Mode

Run tests with additional debugging:

```bash
# Verbose output
PYTHONPATH=. python -m pytest test_validation/ -v -s

# Stop on first failure
PYTHONPATH=. python -m pytest test_validation/ -x

# Show full diff on failures
PYTHONPATH=. python -m pytest test_validation/ --tb=long
```

### Log Analysis

Tests generate detailed logs for debugging:

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

### Adding New Validation Tests

1. **Follow existing patterns** in test file structure
2. **Create expectation templates** for new test scenarios
3. **Use real data** - avoid mocking when possible
4. **Clean up resources** in tearDown methods
5. **Document test purpose** and expected behavior

### Updating Expectation Templates

1. **Verify changes are intentional** - not regressions
2. **Update template metadata** with change reasons
3. **Test with multiple invoices** if possible
4. **Review with team** before committing changes

### Best Practices

- **Test real scenarios** - use actual invoice files
- **Validate end-to-end** - test complete workflows
- **Expect reasonable ranges** - not exact values
- **Handle edge cases** - test error conditions
- **Document assumptions** - explain test logic

## Performance Considerations

### Test Execution Time

- **Text extraction tests**: ~5-10 seconds per invoice
- **CLI validation tests**: ~10-15 seconds per test (includes subprocess overhead)
- **Expectation tests**: ~2-5 seconds per test
- **Total suite**: ~2-3 minutes for complete run

### Resource Usage

- **Memory**: ~50-100MB during test execution
- **Disk**: ~10-20MB for temporary files and databases
- **CPU**: Moderate usage during PDF processing

### Optimization Tips

- **Run in parallel** where possible (pytest -n auto)
- **Skip slow tests** during development (pytest -m "not slow")
- **Use test fixtures** to share expensive setup
- **Clean up aggressively** to prevent resource leaks

## Future Enhancements

### Planned Improvements

1. **Multi-invoice validation** - Test with multiple invoice formats
2. **Performance benchmarking** - Track processing speed over time
3. **Visual diff reporting** - Show differences in validation results
4. **Automated template updates** - Generate templates from CI runs
5. **Cross-platform testing** - Verify behavior on Windows/Mac/Linux

### Extension Points

- **Custom validation strategies** - Test new validation approaches
- **Report format validation** - Verify output format compliance
- **Database migration testing** - Test schema changes
- **Configuration validation** - Test different system configurations

---

For questions or issues with the validation test suite, please refer to the main project documentation or create an issue in the project repository.