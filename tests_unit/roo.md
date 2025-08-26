# Testing Guide

## Quick Start

### Prerequisites
```bash
# Install test dependencies
uv sync --group dev
```

### Running Tests

#### Basic Commands
```bash
# Run all tests
PYTHONPATH=. uv run python -m pytest tests_unit/ -v

# Run specific test file
PYTHONPATH=. uv run python -m pytest tests_unit/test_database.py -v

# Run specific test class or method
PYTHONPATH=. uv run python -m pytest tests_unit/test_database.py::TestDatabaseManager -v
PYTHONPATH=. uv run python -m pytest tests_unit/test_database.py::TestDatabaseManager::test_database_initialization -v
```

#### Common Options
```bash
# Run with coverage
PYTHONPATH=. uv run python -m pytest --cov=. --cov-report=term-missing tests_unit/

# Stop on first failure
PYTHONPATH=. uv run python -m pytest -x tests_unit/

# Show detailed output for failures
PYTHONPATH=. uv run python -m pytest --tb=long tests_unit/

# Run quietly (minimal output)
PYTHONPATH=. uv run python -m pytest -q tests_unit/
```

## Test Files

| File | Purpose | Coverage |
|------|---------|----------|
| `test_database.py` | Database operations and models | 99% |
| `test_cli.py` | Command-line interface | 99% |
| `test_pdf_processing.py` | PDF text extraction | 99% |
| `test_batch_processing.py` | Batch processing workflows | 99% |
| `test_validation_helpers.py` | Input validation | 100% |
| `test_error_handling.py` | Error handling | 99% |
| `test_interactive_functions.py` | User interactions | 99% |
| `test_invoice_processing_refactored.py` | Invoice processing | 99% |
| `test_part_discovery.py` | Part discovery service | 99% |
| `test_bulk_operations.py` | Bulk operations | 97% |
| `test_backup_verification.py` | Backup verification | 98% |
| `test_cleanup_utils.py` | Test utilities | 98% |

## Important Notes

### Environment Setup
- **Always use `PYTHONPATH=.`** to ensure proper module imports
- Tests use temporary databases and files (auto-cleanup)
- Dev dependencies must be installed with `uv sync --group dev`

### Test Framework
- Uses **pytest** with configuration in `pyproject.toml`
- Test files follow pattern: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Current Status
- **All tests**: 282/282 passing ✅
- **Overall coverage**: 66% (acceptable for current scope)
- **Critical paths**: Well tested (>95% coverage)
- **Performance**: Full test suite runs in ~8.5 seconds
- **Test architecture**: Modern, clean, no legacy dependencies

## Troubleshooting

### Common Issues
```bash
# Import errors - ensure PYTHONPATH is set
export PYTHONPATH=.

# Missing pytest - install dev dependencies
uv sync --group dev

# Database locks - clean up test files
rm -f test_*.db
```

### Debugging Failed Tests
```bash
# Run single failing test with full details
PYTHONPATH=. uv run python -m pytest -v --tb=long tests_unit/test_database.py::TestSpecificTest::test_method

# Run with debugger on failure
PYTHONPATH=. uv run python -m pytest --pdb tests_unit/test_database.py

# Generate coverage report
PYTHONPATH=. uv run python -m pytest --cov=. --cov-report=html tests_unit/
```

## Writing New Tests

### Basic Structure
```python
import unittest
from database.database import DatabaseManager

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        # Setup test data
        pass
    
    def test_feature_success(self):
        # Arrange, Act, Assert
        pass
    
    def tearDown(self):
        # Cleanup
        pass
```

### Best Practices
- Use descriptive test names: `test_create_part_with_valid_data_success`
- Test both success and failure cases
- Use temporary files/databases
- Clean up resources in tearDown
- Keep tests fast (< 1 second each)

---

**Quick Reference**: `PYTHONPATH=. uv run python -m pytest tests_unit/ -v`

## Coverage Summary

**Overall: 66%** (9,278 statements, 3,155 missed)

### Well-Tested Modules (>80%)
- [`cli/validation_helpers.py`](../cli/validation_helpers.py): 94%
- [`database/database.py`](../database/database.py): 83%
- [`processing/part_discovery_service.py`](../processing/part_discovery_service.py): 88%
- [`processing/validation_models.py`](../processing/validation_models.py): 92%

### Areas for Future Improvement (<50%)
- [`database/db_utils.py`](../database/db_utils.py): 0% (unused utilities)
- [`cli/commands/discovery_commands.py`](../cli/commands/discovery_commands.py): 20%
- [`processing/validation_integration.py`](../processing/validation_integration.py): 17%
- [`processing/validation_strategies_extended.py`](../processing/validation_strategies_extended.py): 13%

**Note**: Low coverage areas are primarily interactive features and extended validation strategies that are less critical for automated testing.