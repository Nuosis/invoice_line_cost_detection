# End-to-End Test Suite

This directory contains comprehensive end-to-end (e2e) tests for the Invoice Rate Detection System. These tests validate the entire system functionality in real-world conditions without using any mocking.

## Overview

The e2e test suite follows strict principles:
- **NO MOCKING**: All tests use real database connections, file systems, and system components
- **Complete Isolation**: Each test creates its own resources and cleans up completely
- **Real-World Validation**: Tests simulate actual user scenarios and system behavior

## Test Structure

```
e2e_tests/
├── README.md                           # This file
├── roo.md                             # Testing rules and guidelines
├── __init__.py                        # Package initialization
├── run_tests.py                       # Enhanced test runner script
├── test_initial_database_setup.py     # Database initialization tests
├── test_status_command.py             # System status validation tests
├── test_parts_management.py           # Parts CRUD operations tests
├── test_invoice_processing.py         # Invoice processing workflow tests
├── test_database_management.py        # Database backup/restore tests
├── test_configuration_management.py   # Configuration management tests
├── test_discovery_management.py       # Part discovery workflow tests
├── test_bulk_operations.py            # Bulk operations tests
├── test_interactive_workflows.py      # Interactive user workflow tests
├── test_cross_platform_compatibility.py # Cross-platform compatibility tests
└── test_error_handling_edge_cases.py  # Error handling and edge case tests
```

## Test Suites

### Core System Tests

#### Initial Database Setup Tests (`test_initial_database_setup.py`)

Comprehensive smoke tests for database initialization functionality:

- **Database File Creation**: Tests database file creation and directory structure
- **Schema Validation**: Verifies all tables, indexes, triggers, and views are created correctly
- **Default Configuration**: Validates default configuration values are inserted properly
- **Connection Management**: Tests database connection properties and settings
- **Error Handling**: Tests various error conditions and edge cases
- **Cross-Platform Compatibility**: Ensures tests work on Windows, macOS, and Linux
- **Concurrent Access**: Tests concurrent database initialization scenarios

#### System Status Tests (`test_status_command.py`)

Validates system status reporting and health checks:

- **Database Status Validation**: Tests database connectivity and health reporting
- **Configuration Status**: Validates configuration loading and status reporting
- **System Dependencies**: Tests dependency checking and version validation
- **Performance Metrics**: Validates system performance reporting
- **Error Condition Reporting**: Tests status reporting under various error conditions

### Feature-Specific Test Suites

#### Parts Management Tests (`test_parts_management.py`)

Comprehensive testing of parts database operations:

- **CRUD Operations**: Create, read, update, delete operations for parts
- **Data Validation**: Input validation and constraint checking
- **Import/Export Operations**: CSV import/export functionality
- **Search and Filtering**: Parts search and filtering capabilities
- **Statistics and Reporting**: Parts statistics and summary reporting
- **Batch Operations**: Bulk parts operations and performance testing

#### Invoice Processing Tests (`test_invoice_processing.py`)

End-to-end invoice processing workflow validation:

- **PDF Processing**: PDF text extraction and parsing
- **Line Item Detection**: Invoice line item identification and extraction
- **Validation Engine**: Rate validation and business rule application
- **Report Generation**: CSV and text report generation
- **Batch Processing**: Multiple invoice processing workflows
- **Error Recovery**: Processing error handling and recovery

#### Database Management Tests (`test_database_management.py`)

Database administration and maintenance operations:

- **Backup Operations**: Database backup creation and validation
- **Restore Operations**: Database restore and integrity verification
- **Migration Testing**: Schema migration and data preservation
- **Maintenance Operations**: Database optimization and cleanup
- **Integrity Checks**: Data integrity validation and repair
- **Performance Testing**: Database performance under load

#### Configuration Management Tests (`test_configuration_management.py`)

System configuration management validation:

- **Configuration CRUD**: Configuration setting management
- **Type Validation**: Configuration value type checking and conversion
- **Default Handling**: Default configuration value management
- **Persistence Testing**: Configuration persistence and retrieval
- **Validation Rules**: Configuration validation rule enforcement
- **Reset Operations**: Configuration reset and factory defaults

#### Discovery Management Tests (`test_discovery_management.py`)

Interactive part discovery workflow testing:

- **Discovery Sessions**: Part discovery session management
- **Interactive Workflows**: User interaction simulation and validation
- **Session Persistence**: Discovery session state management
- **Statistics Tracking**: Discovery statistics and reporting
- **Export Operations**: Discovery results export functionality
- **Error Handling**: Discovery workflow error scenarios

#### Bulk Operations Tests (`test_bulk_operations.py`)

Large-scale operations and performance testing:

- **Bulk Updates**: Mass part updates and validation
- **Bulk Deletions**: Mass deletion operations with safety checks
- **Bulk Activation**: Mass part activation/deactivation
- **Performance Validation**: Large dataset processing performance
- **Transaction Management**: Bulk operation transaction handling
- **Error Recovery**: Bulk operation failure recovery

#### Interactive Workflows Tests (`test_interactive_workflows.py`)

User interaction and workflow simulation:

- **User Input Simulation**: Interactive command simulation
- **Workflow State Management**: Multi-step workflow state handling
- **Progress Reporting**: User progress feedback validation
- **Error Recovery**: Interactive error handling and recovery
- **Session Management**: User session state management
- **Help System**: Interactive help and guidance testing

### System Quality Tests

#### Cross-Platform Compatibility Tests (`test_cross_platform_compatibility.py`)

Platform-specific behavior validation:

- **File System Operations**: Cross-platform file handling
- **Path Handling**: Platform-specific path normalization
- **Unicode Support**: Unicode handling across platforms
- **Encoding Compatibility**: File encoding handling
- **Permission Management**: Platform-specific permission handling
- **Temporary Resources**: Platform-specific temporary file management

#### Error Handling and Edge Cases Tests (`test_error_handling_edge_cases.py`)

Comprehensive error scenario and edge case validation:

- **Database Corruption**: Corruption detection and recovery
- **File System Errors**: Permission and access error handling
- **Invalid Input Handling**: Malformed data processing
- **Resource Exhaustion**: Memory and resource limit testing
- **Concurrent Access**: Race condition and locking scenarios
- **System Limits**: Boundary condition and limit testing

### Key Test Cases (Examples)

1. **Database File Creation**
   - Creates database file when it doesn't exist
   - Creates parent directories if needed
   - Handles existing database files correctly

2. **Schema Verification**
   - Validates all required tables exist with correct structure
   - Verifies indexes, triggers, and views are created
   - Tests foreign key constraints and data integrity

3. **Parts Management**
   - CRUD operations with validation
   - Import/export with error handling
   - Search and filtering accuracy

4. **Invoice Processing**
   - PDF parsing and text extraction
   - Line item detection and validation
   - Report generation and formatting

5. **Error Handling**
   - Graceful degradation under failure
   - Recovery mechanisms and rollback
   - User-friendly error reporting

## Running Tests

### Using the Enhanced Test Runner (Recommended)

The enhanced test runner provides comprehensive test execution with detailed reporting:

```bash
# Run all e2e tests with enhanced reporting
python e2e_tests/run_tests.py

# Run with verbose output and detailed error reporting
python e2e_tests/run_tests.py --verbose

# List all available test suites
python e2e_tests/run_tests.py --list-suites

# Run specific test pattern
python e2e_tests/run_tests.py --test-pattern "test_parts*"

# Run specific test categories
python e2e_tests/run_tests.py --test-pattern "test_*management*"
```

The enhanced test runner provides:
- **Organized Test Categories**: Tests are organized into logical categories
- **Detailed Progress Reporting**: Real-time test execution progress
- **Comprehensive Summary**: Success rates, execution times, and detailed results
- **Enhanced Error Reporting**: Clear error messages and failure analysis
- **Test Suite Listing**: Easy discovery of available test suites

### Using Python's unittest Module

```bash
# Run all tests in the directory
python -m unittest discover e2e_tests

# Run specific test file
python -m unittest e2e_tests.test_initial_database_setup

# Run specific test class
python -m unittest e2e_tests.test_initial_database_setup.TestInitialDatabaseSetup

# Run specific test method
python -m unittest e2e_tests.test_initial_database_setup.TestInitialDatabaseSetup.test_database_file_creation_on_initialization
```

### Using pytest (if available)

```bash
# Run all e2e tests
pytest e2e_tests/

# Run with verbose output
pytest e2e_tests/ -v

# Run specific test file
pytest e2e_tests/test_initial_database_setup.py
```

## Test Output

The test runner provides detailed output including:
- Test execution progress
- Pass/fail status for each test
- Detailed error messages and tracebacks for failures
- Summary statistics (tests run, failures, errors, skipped)

Example output:
```
Running e2e tests from /path/to/e2e_tests
Test pattern: test_*.py
----------------------------------------------------------------------
test_database_file_creation_on_initialization ... ok
test_required_tables_creation ... ok
test_default_configuration_insertion ... ok
...
----------------------------------------------------------------------
Tests run: 20, Failures: 0, Errors: 0, Skipped: 0
```

## Test Environment

### Requirements

- Python 3.8+
- All project dependencies (see `pyproject.toml`)
- Write access to temporary directories
- Sufficient disk space for test databases

### Temporary Resources

Tests create temporary resources in system temp directories:
- Database files with unique names
- Temporary directories for test isolation
- All resources are automatically cleaned up after each test

### Cross-Platform Support

Tests are designed to work on:
- **Windows**: Uses Windows-compatible file paths and operations
- **macOS**: Handles macOS-specific file system behaviors
- **Linux**: Works with various Linux distributions

## Test Guidelines

### Adding New Tests

When adding new e2e tests:

1. **Follow the NO MOCKING rule** - Use real system components
2. **Ensure complete cleanup** - Clean up all created resources
3. **Use unique identifiers** - Avoid conflicts with parallel tests
4. **Test real scenarios** - Simulate actual user workflows
5. **Handle cross-platform differences** - Test on multiple platforms

### Test Naming Convention

- Test files: `test_<functionality>.py`
- Test classes: `Test<Functionality>`
- Test methods: `test_<specific_behavior>`

### Resource Management

Each test must:
- Create unique temporary directories and files
- Track all created resources for cleanup
- Implement robust cleanup in `tearDown()` methods
- Handle cleanup errors gracefully

## Debugging Tests

### Verbose Output

Use the `--verbose` flag to see detailed test execution:
```bash
python e2e_tests/run_tests.py --verbose
```

### Debug Logging

Enable debug logging by setting the logging level:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Manual Test Execution

Run individual tests for debugging:
```bash
python -m unittest e2e_tests.test_initial_database_setup.TestInitialDatabaseSetup.test_specific_method -v
```

## Continuous Integration

These tests are designed to run in CI/CD environments:
- No external dependencies beyond the project requirements
- Deterministic and repeatable results
- Proper exit codes for CI systems
- Comprehensive error reporting

### CI Configuration Example

```yaml
# Example GitHub Actions configuration
- name: Run E2E Tests
  run: |
    python e2e_tests/run_tests.py --verbose
```

## Performance Considerations

E2E tests may take longer than unit tests because they:
- Create real database files and perform actual database operations
- Perform actual file system operations across platforms
- Test complete system workflows end-to-end
- Process real PDF files and generate reports
- Test error conditions and recovery scenarios
- Validate cross-platform compatibility

Typical execution times:
- Individual test: 0.1-5 seconds
- Test category (e.g., Parts Management): 5-15 seconds
- Full comprehensive test suite: 60-180 seconds
- Cross-platform and error handling tests: 10-30 seconds each

Performance varies based on:
- System specifications (CPU, disk I/O)
- Platform (Windows, macOS, Linux)
- Available system resources
- Concurrent system activity

## Troubleshooting

### Common Issues

1. **Permission Errors**
   - Ensure write access to temp directories
   - Check file system permissions

2. **Database Lock Errors**
   - Verify all database connections are properly closed
   - Check for concurrent test execution conflicts

3. **Platform-Specific Failures**
   - Test on the target platform
   - Check file path handling for platform differences

### Getting Help

If tests fail:
1. Run with `--verbose` flag for detailed output
2. Check the specific error messages and tracebacks
3. Verify system requirements and dependencies
4. Test on a clean environment

## Contributing

When contributing to the e2e test suite:
1. Read the testing guidelines in `roo.md`
2. Follow the established patterns and conventions
3. Ensure all tests pass on multiple platforms
4. Add appropriate documentation for new test suites
5. Update this README if adding new functionality

---

**Remember**: These tests validate real system behavior. No shortcuts, no mocking, no compromises on cleanup.