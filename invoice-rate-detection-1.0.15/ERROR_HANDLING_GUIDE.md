# Error Handling Guidelines

**Document Version:** 1.0  
**Date:** 2025-07-29  
**Author:** Program Manager  
**Status:** Active  

---

## Overview

This document provides comprehensive guidelines for implementing consistent, user-friendly error handling across the Invoice Rate Detection System CLI. The centralized error handling system provides specific recovery suggestions for different error types and ensures a consistent user experience.

---

## Architecture

### Centralized Error Handler

The error handling system is built around the [`ErrorHandler`](../cli/error_handlers.py) class, which provides:

- **Specific Error Handlers**: Tailored handling for different error types
- **Recovery Suggestions**: Actionable guidance for users to resolve issues
- **Consistent Formatting**: Standardized error message presentation
- **Decorator Pattern**: Easy application across CLI commands

### Error Handler Decorator

The `@error_handler` decorator provides automatic error catching and handling:

```python
from cli.error_handlers import error_handler

@error_handler({'operation': 'part_creation', 'command': 'parts add'})
def add_part_command(ctx, part_number, price, ...):
    # Command implementation
    pass
```

---

## Error Types and Handling

### Database Errors

**Error Type:** [`DatabaseError`](../database/models.py)

**Common Scenarios:**
- Database locked by another process
- Missing or corrupted tables
- Insufficient disk space
- Permission denied
- Database corruption

**Recovery Suggestions:**
- Close other application instances
- Run database migration
- Free up disk space
- Check file permissions
- Restore from backup

**Example:**
```python
# Automatic handling via decorator
@error_handler({'operation': 'database_query'})
def query_parts():
    # If DatabaseError occurs, user gets specific recovery suggestions
    pass
```

### Processing Errors

**Error Type:** [`ProcessingError`](../cli/exceptions.py)

**Common Scenarios:**
- PDF file corruption or password protection
- Validation failures
- Memory exhaustion
- File access issues

**Recovery Suggestions:**
- Verify PDF file integrity
- Try threshold-based validation mode
- Process files in smaller batches
- Check file permissions

**Example:**
```python
@error_handler({'operation': 'pdf_processing', 'file_path': pdf_path})
def process_pdf(pdf_path):
    # Context provides file path for specific error messages
    pass
```

### Validation Errors

**Error Type:** [`ValidationError`](../database/models.py)

**Common Scenarios:**
- Invalid part number format
- Negative or invalid prices
- Invalid email addresses
- Missing required fields

**Recovery Suggestions:**
- Format requirements for specific fields
- Examples of valid input
- Reference to command help

**Example:**
```python
@error_handler({'field_name': 'part_number', 'value': part_number})
def validate_part_number(part_number):
    # Provides field-specific validation guidance
    pass
```

### Part Not Found Errors

**Error Type:** [`PartNotFoundError`](../database/models.py)

**Common Scenarios:**
- Misspelled part numbers
- Parts not yet added to database
- Case sensitivity issues

**Recovery Suggestions:**
- Check spelling
- List available parts
- Search for similar parts
- Add missing parts

### Configuration Errors

**Error Type:** [`ConfigurationError`](../database/models.py)

**Common Scenarios:**
- Invalid configuration values
- Missing configuration keys
- Type conversion errors

**Recovery Suggestions:**
- Check current configuration
- Reset to defaults
- Set specific values
- Restore from backup

---

## Implementation Guidelines

### Using the Error Handler Decorator

#### Basic Usage

```python
from cli.error_handlers import error_handler

@error_handler()
def simple_command():
    # Basic error handling with default context
    pass
```

#### With Context

```python
@error_handler({
    'operation': 'part_creation',
    'command': 'parts add',
    'part_number': part_number
})
def add_part_command(part_number, price):
    # Rich context for specific error messages
    pass
```

#### Context Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `operation` | Type of operation being performed | `'part_creation'`, `'pdf_processing'` |
| `command` | CLI command being executed | `'parts add'`, `'invoice process'` |
| `file_path` | File being processed | `'/path/to/invoice.pdf'` |
| `part_number` | Part number involved | `'GP0171NAVY'` |
| `config_key` | Configuration key | `'validation_mode'` |
| `field_name` | Input field name | `'price'`, `'part_number'` |
| `value` | Input value that failed | `'invalid@part'` |

### Removing Old Error Handling

When updating existing commands, remove manual try/catch blocks:

#### Before (Manual Error Handling)
```python
def old_command():
    try:
        # Command logic
        pass
    except DatabaseError as e:
        raise CLIError(f"Database error: {e}")
    except Exception as e:
        logger.exception("Command failed")
        raise CLIError(f"Command failed: {e}")
```

#### After (Centralized Error Handling)
```python
@error_handler({'operation': 'command_operation'})
def new_command():
    # Command logic - errors handled automatically
    pass
```

### Convenience Functions

For common error handling patterns outside of CLI commands:

#### File Operations
```python
from cli.error_handlers import handle_file_operation_error

try:
    process_file(file_path)
except Exception as e:
    handle_file_operation_error(e, file_path, "processing")
```

#### Database Operations
```python
from cli.error_handlers import handle_database_operation_error

try:
    db_operation()
except Exception as e:
    handle_database_operation_error(e, "database_query", part_number="TEST123")
```

---

## Error Message Format

### Standard Format

All error messages follow a consistent format:

1. **Error Type**: Clear identification of the error category
2. **Specific Message**: Detailed description of what went wrong
3. **Recovery Suggestions**: Numbered list of actionable steps
4. **Command Examples**: Specific commands to resolve the issue

### Example Output

```
Error: Database is currently locked by another process
Recovery suggestions:
  1. Close any other instances of the application
  2. Wait a few seconds and try again
  3. Restart the application if the problem persists
  4. Check if another user is accessing the database
```

---

## Testing Error Handling

### Unit Tests

Test error handlers with specific error scenarios:

```python
def test_database_locked_error():
    error = DatabaseError("database is locked")
    context = {'operation': 'test_operation'}
    
    with patch('cli.error_handlers.print_error') as mock_error:
        ErrorHandler.handle_database_error(error, context)
        mock_error.assert_called_once_with("Database is currently locked by another process")
```

### Integration Tests

Test decorator functionality with realistic scenarios:

```python
@error_handler({'operation': 'test_command'})
def test_command():
    raise DatabaseError("test error")

def test_decorator_integration():
    with pytest.raises(CLIError):
        test_command()
```

### Test Coverage Requirements

- **Error Handler Methods**: 100% coverage of all error handling methods
- **Decorator Functionality**: Test all error types and context propagation
- **Recovery Suggestions**: Verify appropriate suggestions are provided
- **Integration**: Test with actual CLI command patterns

---

## Best Practices

### Do's

✅ **Use the decorator on all CLI commands**
```python
@error_handler({'operation': 'command_name'})
def command_function():
    pass
```

✅ **Provide rich context for better error messages**
```python
@error_handler({
    'operation': 'file_processing',
    'file_path': file_path,
    'command': 'process'
})
```

✅ **Use specific error types instead of generic Exception**
```python
# Good
raise ProcessingError("PDF processing failed")

# Avoid
raise Exception("Something went wrong")
```

✅ **Test error handling scenarios**
```python
def test_error_scenario():
    with pytest.raises(CLIError):
        command_with_error()
```

### Don'ts

❌ **Don't use manual try/catch in decorated functions**
```python
@error_handler()
def bad_command():
    try:  # Unnecessary - decorator handles this
        risky_operation()
    except Exception as e:
        raise CLIError(str(e))
```

❌ **Don't catch and re-raise without adding value**
```python
# Bad
try:
    operation()
except DatabaseError as e:
    raise DatabaseError(str(e))  # No added value
```

❌ **Don't provide generic error messages**
```python
# Bad
raise CLIError("Error occurred")

# Good
raise ProcessingError("PDF file appears to be corrupted")
```

❌ **Don't forget to provide context**
```python
# Bad
@error_handler()

# Good
@error_handler({'operation': 'specific_operation'})
```

---

## Migration Guide

### Step 1: Import Error Handler

```python
from cli.error_handlers import error_handler
```

### Step 2: Apply Decorator

```python
@error_handler({'operation': 'command_operation', 'command': 'command_name'})
def existing_command():
    # Existing logic
```

### Step 3: Remove Manual Error Handling

Remove existing try/catch blocks that are now handled by the decorator.

### Step 4: Update Tests

Update tests to expect CLIError instead of specific error types:

```python
# Before
with pytest.raises(DatabaseError):
    command()

# After
with pytest.raises(CLIError):
    command()
```

### Step 5: Verify Error Messages

Test that appropriate recovery suggestions are provided for different error scenarios.

---

## Troubleshooting

### Common Issues

#### Error Handler Not Working

**Problem**: Errors not being caught by decorator
**Solution**: Ensure decorator is applied correctly and imported properly

#### Missing Recovery Suggestions

**Problem**: Generic error messages without specific guidance
**Solution**: Provide appropriate context in decorator parameters

#### Test Failures

**Problem**: Tests expecting specific error types
**Solution**: Update tests to expect CLIError wrapper

### Debugging

Enable debug logging to see error handling flow:

```python
import logging
logging.getLogger('cli.error_handlers').setLevel(logging.DEBUG)
```

---

## Future Enhancements

### Planned Improvements

1. **Error Analytics**: Track common error patterns for system improvements
2. **Contextual Help**: Dynamic help suggestions based on error context
3. **Error Recovery**: Automatic retry mechanisms for transient errors
4. **User Feedback**: Collect user feedback on error message effectiveness

### Extension Points

The error handling system is designed for easy extension:

- Add new error types by implementing specific handler methods
- Extend context parameters for richer error messages
- Add new convenience functions for common patterns
- Integrate with external error reporting systems

---

## References

- [CLI Error Handlers Implementation](../cli/error_handlers.py)
- [Database Models and Exceptions](../database/models.py)
- [CLI Exceptions](../cli/exceptions.py)
- [Error Handling Tests](../tests/test_error_handling.py)
- [CLI Remediation Plan](CLI_REMEDIATION_PLAN.md#issue-5-error-handling-improvements)

---

*This document is part of the Invoice Rate Detection System documentation suite and should be updated as the error handling system evolves.*