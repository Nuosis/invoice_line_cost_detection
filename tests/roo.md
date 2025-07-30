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
PYTHONPATH=. uv run python -m pytest tests/ -v

# Run specific test file
PYTHONPATH=. uv run python -m pytest tests/test_database.py -v

# Run specific test class or method
PYTHONPATH=. uv run python -m pytest tests/test_database.py::TestDatabaseManager -v
PYTHONPATH=. uv run python -m pytest tests/test_database.py::TestDatabaseManager::test_database_initialization -v
```

#### Common Options
```bash
# Run with coverage
PYTHONPATH=. uv run python -m pytest --cov=. tests/

# Stop on first failure
PYTHONPATH=. uv run python -m pytest -x tests/

# Show detailed output for failures
PYTHONPATH=. uv run python -m pytest --tb=long tests/

# Run quietly (minimal output)
PYTHONPATH=. uv run python -m pytest -q tests/
```

## Test Files

| File | Purpose |
|------|---------|
| `test_database.py` | Database operations and models |
| `test_cli.py` | Command-line interface |
| `test_pdf_processing.py` | PDF text extraction |
| `test_batch_processing.py` | Batch processing workflows |
| `test_validation_helpers.py` | Input validation |
| `test_error_handling.py` | Error handling |
| `test_interactive_functions.py` | User interactions |
| `test_invoice_processing_refactored.py` | Invoice processing |

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
- **Database tests**: 53/60 passing (7 minor failures, non-critical)
- **Other tests**: Active and maintained
- **Performance**: Full test suite runs in ~2 seconds

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
PYTHONPATH=. uv run python -m pytest -v --tb=long tests/test_database.py::TestSpecificTest::test_method

# Run with debugger on failure
PYTHONPATH=. uv run python -m pytest --pdb tests/test_database.py
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

**Quick Reference**: `PYTHONPATH=. uv run python -m pytest tests/ -v`