# Bulk Operations Guide

This guide covers the comprehensive bulk operations functionality implemented for the Invoice Rate Detection System's parts management.

## Overview

The bulk operations module provides efficient batch processing capabilities for parts management, including:

- **Bulk Update**: Update multiple parts from CSV data
- **Bulk Delete/Deactivate**: Remove or deactivate multiple parts
- **Bulk Activate**: Reactivate multiple deactivated parts
- **Advanced CSV Processing**: Column mapping and data transformations
- **Progress Tracking**: Real-time progress indicators for large operations
- **Dry Run Mode**: Preview changes before execution

## Features

### 1. Bulk Update Operations

Update multiple parts simultaneously from CSV data with selective field updates.

#### Command Usage
```bash
# Update prices only
uv run invoice-checker parts bulk-update updates.csv --field price

# Update multiple fields
uv run invoice-checker parts bulk-update updates.csv --field price --field description

# Dry run to preview changes
uv run invoice-checker parts bulk-update updates.csv --field price --dry-run

# Filter by category
uv run invoice-checker parts bulk-update updates.csv --field price --filter-category "Clothing"
```

#### CSV Format
```csv
part_number,price,description,category,notes
GP0171NAVY,15.50,Navy Work Pants,Clothing,Updated pricing
GP0171KHAKI,16.00,Khaki Work Pants,Clothing,New description
```

#### Options
- `--field`: Specify which fields to update (price, description, category, notes, status)
- `--filter-category`: Only update parts in specified category
- `--dry-run`: Preview changes without making them
- `--batch-size`: Process in batches (default: 50)

### 2. Bulk Delete/Deactivate Operations

Remove or deactivate multiple parts from the database.

#### Command Usage
```bash
# Soft delete (deactivate) parts
uv run invoice-checker parts bulk-delete parts_to_delete.csv

# Permanently delete parts
uv run invoice-checker parts bulk-delete parts_to_delete.csv --hard

# Dry run to preview deletions
uv run invoice-checker parts bulk-delete parts_to_delete.csv --dry-run

# Skip confirmation prompt
uv run invoice-checker parts bulk-delete parts_to_delete.csv --force
```

#### CSV Format
```csv
part_number
GP0171NAVY
GP0171KHAKI
GP0171BLACK
```

#### Options
- `--soft`: Soft delete (deactivate) - default behavior
- `--hard`: Permanently delete from database
- `--filter-category`: Only delete parts in specified category
- `--dry-run`: Preview deletions without making them
- `--force`: Skip confirmation prompt
- `--batch-size`: Process in batches (default: 50)

### 3. Bulk Activate Operations

Reactivate multiple deactivated parts.

#### Command Usage
```bash
# Activate parts
invoice-checker parts bulk-activate parts_to_activate.csv

# Dry run to preview activations
invoice-checker parts bulk-activate parts_to_activate.csv --dry-run

# Filter by category
invoice-checker parts bulk-activate parts_to_activate.csv --filter-category "Tools"
```

#### CSV Format
```csv
part_number
GP0171NAVY
GP0171KHAKI
```

#### Options
- `--filter-category`: Only activate parts in specified category
- `--dry-run`: Preview activations without making them
- `--batch-size`: Process in batches (default: 50)

## Advanced Features

### Column Mapping

Use column mapping files to handle CSV files with different column names:

#### Mapping File Format
```csv
source_column,target_column
item_code,part_number
price,authorized_price
desc,description
```

#### Usage
```bash
invoice-checker parts import data.csv --mapping-file mapping.csv
```

### Data Transformations

Automatic data transformations include:

- **Part Numbers**: Converted to uppercase
- **Prices**: Currency symbols removed, decimal formatting normalized
- **Text Fields**: Trimmed whitespace, empty strings converted to NULL

#### Enable Transformations
```bash
invoice-checker parts import data.csv --transform-data
```

### Progress Tracking

All bulk operations include real-time progress indicators:

```
Importing parts: 100%|████████████| 1000/1000 [00:30<00:00, 33.33it/s]
```

### Error Handling

Comprehensive error handling with detailed reporting:

- **Validation Errors**: Clear messages for invalid data
- **Database Errors**: Graceful handling of constraint violations
- **File Errors**: Helpful messages for file access issues
- **Network Errors**: Retry logic for temporary failures

## Integration with Existing Systems

### Database Integration

- **Full CRUD Support**: Create, Read, Update, Delete operations
- **Transaction Safety**: All operations are atomic
- **Audit Trail**: Complete logging of all changes
- **Backup Integration**: Works with existing backup/restore functionality

### Validation Integration

- **Centralized Validation**: Uses existing ValidationHelper system
- **Business Rules**: Enforces all existing business logic
- **Data Integrity**: Maintains referential integrity
- **Error Reporting**: Consistent error formatting

### CLI Integration

- **Consistent Interface**: Follows existing CLI patterns
- **Error Handling**: Uses centralized error handling system
- **Progress Reporting**: Consistent progress indicators
- **Help System**: Integrated help and documentation

## Performance Considerations

### Batch Processing

- **Configurable Batch Size**: Optimize for memory usage
- **Progress Tracking**: Real-time feedback for long operations
- **Memory Management**: Efficient processing of large datasets
- **Error Recovery**: Continue processing after individual failures

### Optimization Tips

1. **Use Appropriate Batch Sizes**: 50-100 for most operations
2. **Enable Transformations**: Only when needed to improve performance
3. **Use Dry Run**: Always test with large datasets first
4. **Monitor Memory**: Watch memory usage with very large files

## Security Considerations

### Input Validation

- **CSV Injection Prevention**: Sanitizes all input data
- **Path Traversal Protection**: Validates file paths
- **Data Type Validation**: Enforces correct data types
- **Size Limits**: Prevents memory exhaustion attacks

### Access Control

- **File Permissions**: Respects system file permissions
- **Database Permissions**: Uses existing database access controls
- **Audit Logging**: Logs all operations for security review

## Troubleshooting

### Common Issues

#### CSV Format Errors
```
Error: CSV file must contain 'part_number' column
Solution: Ensure your CSV has the required columns
```

#### Memory Issues
```
Error: Out of memory processing large file
Solution: Reduce batch size or process file in chunks
```

#### Permission Errors
```
Error: Permission denied accessing file
Solution: Check file permissions and user access rights
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export LOG_LEVEL=DEBUG
invoice-checker parts bulk-update data.csv --field price
```

## Examples

### Complete Workflow Example

1. **Prepare Data**
```csv
part_number,price,description,category
GP0171NAVY,15.50,Navy Work Pants,Clothing
GP0171KHAKI,16.00,Khaki Work Pants,Clothing
TOOL001,25.00,Hammer,Tools
```

2. **Dry Run Test**
```bash
invoice-checker parts bulk-update updates.csv --field price --dry-run
```

3. **Execute Update**
```bash
invoice-checker parts bulk-update updates.csv --field price
```

4. **Verify Results**
```bash
invoice-checker parts list --category Clothing
```

### Batch Import/Export Workflow

1. **Export Current Data**
```bash
invoice-checker parts export current_parts.csv
```

2. **Modify Data** (edit CSV file)

3. **Import Updates**
```bash
invoice-checker parts import updated_parts.csv --update-existing
```

## Best Practices

### Data Preparation

1. **Validate Data**: Always use dry-run mode first
2. **Backup Database**: Create backups before large operations
3. **Test with Small Datasets**: Verify logic with small samples
4. **Use Consistent Formats**: Maintain consistent CSV formatting

### Operation Execution

1. **Monitor Progress**: Watch progress indicators for issues
2. **Check Results**: Verify operations completed successfully
3. **Review Logs**: Check logs for warnings or errors
4. **Validate Data**: Confirm data integrity after operations

### Error Recovery

1. **Use Transactions**: Operations are atomic by default
2. **Restore from Backup**: If major issues occur
3. **Partial Recovery**: Re-run operations with corrected data
4. **Audit Trail**: Use logs to understand what happened

## API Reference

### Bulk Operations Module

The bulk operations are implemented in `cli/commands/bulk_operations.py` and provide the following functions:

- `bulk_update()`: Update multiple parts from CSV
- `bulk_delete()`: Delete/deactivate multiple parts
- `bulk_activate()`: Activate multiple parts
- `_read_bulk_update_csv()`: Parse update CSV files
- `_read_part_numbers_csv()`: Parse part number lists
- `_perform_bulk_update()`: Execute bulk updates
- `_perform_bulk_delete()`: Execute bulk deletions
- `_perform_bulk_activate()`: Execute bulk activations

### Integration Points

- **Database Layer**: `database/models.py` - Part model and database operations
- **Validation Layer**: `cli/validation_helpers.py` - Data validation
- **Progress Tracking**: `cli/progress.py` - Progress indicators
- **Error Handling**: `cli/error_handlers.py` - Centralized error handling
- **CLI Framework**: `cli/commands/parts_commands.py` - Command integration

## Conclusion

The bulk operations functionality provides a comprehensive, efficient, and safe way to manage large numbers of parts in the Invoice Rate Detection System. With features like dry-run mode, progress tracking, and comprehensive error handling, users can confidently perform bulk operations while maintaining data integrity and system performance.

For additional support or questions, refer to the main documentation or contact the development team.