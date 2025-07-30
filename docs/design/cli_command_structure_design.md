# CLI Command Structure Design
## Invoice Rate Detection System

**Document Version**: 1.0  
**Date**: July 29, 2025  
**Author**: System Architect  

---

## Table of Contents

1. [Overview](#overview)
2. [Command Architecture](#command-architecture)
3. [Global Parameters](#global-parameters)
4. [Invoice Processing Commands](#invoice-processing-commands)
5. [Parts Management Commands](#parts-management-commands)
6. [Database Management Commands](#database-management-commands)
7. [Configuration Management Commands](#configuration-management-commands)
8. [Discovery Log Management Commands](#discovery-log-management-commands)
9. [Utility Commands](#utility-commands)
10. [Parameter Validation](#parameter-validation)
11. [Interactive Prompt Flows](#interactive-prompt-flows)
12. [Help System](#help-system)
13. [Progress Indicators](#progress-indicators)
14. [Error Handling](#error-handling)
15. [Implementation Guidelines](#implementation-guidelines)

---

## Overview

The Invoice Rate Detection System CLI provides a comprehensive command-line interface designed for both non-technical business users and advanced users. The CLI supports the complete workflow from invoice processing to parts management, database operations, and system maintenance.

### Design Principles

- **User-Friendly**: Simple commands with intuitive naming
- **Consistent**: Uniform parameter naming and behavior across commands
- **Discoverable**: Comprehensive help system and logical command grouping
- **Flexible**: Support for both command-line arguments and interactive prompts
- **Robust**: Comprehensive error handling and validation
- **Extensible**: Modular design for future enhancements

---

## Command Architecture

The CLI is organized into logical command groups with a hierarchical structure:

```
invoice-checker
├── Main Processing Commands
│   ├── process          # Primary invoice processing
│   ├── batch            # Batch processing multiple folders
│   ├── interactive      # Guided interactive processing
│   └── collect-unknowns # Collect unknown parts
├── Parts Management
│   ├── parts add        # Add new part
│   ├── parts list       # List parts with filtering
│   ├── parts get        # Get single part details
│   ├── parts update     # Update existing part
│   ├── parts delete     # Delete/deactivate part
│   ├── parts import     # Import parts from CSV
│   ├── parts export     # Export parts to CSV
│   └── parts stats      # Parts statistics
├── Database Operations
│   ├── backup           # Create database backup
│   ├── restore          # Restore from backup
│   ├── migrate          # Database schema migration
│   └── maintenance      # Database maintenance tasks
├── Configuration
│   ├── config get       # Get configuration value
│   ├── config set       # Set configuration value
│   ├── config list      # List all configurations
│   └── config reset     # Reset configuration
├── Discovery Log
│   ├── discovery list   # List discovery log entries
│   ├── discovery export # Export discovery logs
│   └── discovery cleanup # Clean up old logs
└── Utilities
    ├── help             # Show help information
    ├── version          # Show version information
    └── status           # Show system status
```

---

## Global Parameters

These parameters are available for all commands:

| Parameter | Short | Description | Default |
|-----------|-------|-------------|---------|
| `--verbose` | `-v` | Enable verbose logging | False |
| `--quiet` | `-q` | Suppress non-essential output | False |
| `--config-file` | | Specify custom configuration file path | auto-detect |
| `--database` | | Specify custom database path | invoice_detection.db |
| `--help` | `-h` | Show help information | |

---

## Invoice Processing Commands

### 1. `process` - Main Processing Command

**Purpose**: Process invoices with parts-based validation (primary command)

**Syntax**:
```bash
invoice-checker process [OPTIONS] INPUT_PATH
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `INPUT_PATH` | | Path | Path to folder containing PDFs or single PDF file | Required |
| `--output` | `-o` | Path | Output report file | report.csv |
| `--format` | `-f` | Choice | Output format (csv, txt) | csv |
| `--interactive` | `-i` | Flag | Enable interactive part discovery | False |
| `--collect-unknown` | | Flag | Collect unknown parts for later review | False |
| `--session-id` | | String | Custom processing session ID | auto-generated |
| `--validation-mode` | | Choice | Validation mode (parts_based, threshold_based) | parts_based |
| `--threshold` | `-t` | Float | Threshold for threshold-based mode | 0.30 |

**Examples**:
```bash
# Basic processing with interactive discovery
invoice-checker process ./invoices --output report.csv --interactive

# Collect unknown parts without validation
invoice-checker process ./invoices --collect-unknown --format txt

# Threshold-based processing (alternative validation mode)
uv run invoice-checker process single_invoice.pdf --threshold 0.25 --validation-mode threshold_based
```

### 2. `batch` - Batch Processing

**Purpose**: Process multiple invoice folders in batch mode

**Syntax**:
```bash
invoice-checker batch [OPTIONS] INPUT_PATH
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `INPUT_PATH` | | Path | Path containing multiple invoice folders | Required |
| `--output-dir` | `-o` | Path | Output directory for reports | ./reports |
| `--parallel` | `-p` | Flag | Enable parallel processing | False |
| `--max-workers` | | Integer | Maximum worker threads | 4 |
| `--continue-on-error` | | Flag | Continue processing if individual folders fail | False |

### 3. `interactive` - Interactive Processing

**Purpose**: Guided interactive processing with prompts

**Syntax**:
```bash
invoice-checker interactive [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--preset` | | String | Use predefined settings preset | |
| `--save-preset` | | String | Save current settings as preset | |

### 4. `collect-unknowns` - Unknown Parts Collection

**Purpose**: Process invoices and collect unknown parts without validation

**Syntax**:
```bash
invoice-checker collect-unknowns [OPTIONS] INPUT_PATH
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `INPUT_PATH` | | Path | Path to invoices | Required |
| `--output` | `-o` | Path | Output file for unknown parts | unknown_parts.csv |
| `--suggest-prices` | | Flag | Include price suggestions based on invoice data | False |

---

## Parts Management Commands

### 1. `parts add` - Add New Part

**Purpose**: Add a new part to the master parts database

**Syntax**:
```bash
invoice-checker parts add [OPTIONS] PART_NUMBER PRICE
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `PART_NUMBER` | | String | Unique part identifier | Required |
| `PRICE` | | Decimal | Authorized price | Required |
| `--description` | `-d` | String | Part description | |
| `--category` | `-c` | String | Part category | |
| `--source` | | Choice | Source (manual, discovered, imported) | manual |
| `--notes` | | String | Additional notes | |

**Example**:
```bash
invoice-checker parts add GP0171NAVY 15.50 --description "Navy Work Pants" --category "Clothing"
```

### 2. `parts list` - List Parts

**Purpose**: List parts with filtering and sorting options

**Syntax**:
```bash
invoice-checker parts list [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--category` | `-c` | String | Filter by category | |
| `--active-only` | | Flag | Show only active parts | True |
| `--include-inactive` | | Flag | Include inactive parts | False |
| `--format` | `-f` | Choice | Output format (table, csv, json) | table |
| `--limit` | `-l` | Integer | Maximum number of results | |
| `--offset` | | Integer | Skip number of results | 0 |
| `--sort-by` | | Choice | Sort by field (part_number, price, created_date) | part_number |
| `--order` | | Choice | Sort order (asc, desc) | asc |

### 3. `parts get` - Get Single Part

**Purpose**: Retrieve detailed information about a specific part

**Syntax**:
```bash
invoice-checker parts get [OPTIONS] PART_NUMBER
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `PART_NUMBER` | | String | Part number to retrieve | Required |
| `--format` | `-f` | Choice | Output format (table, json) | table |
| `--include-history` | | Flag | Include discovery log history | False |

### 4. `parts update` - Update Part

**Purpose**: Update an existing part's information

**Syntax**:
```bash
invoice-checker parts update [OPTIONS] PART_NUMBER
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `PART_NUMBER` | | String | Part number to update | Required |
| `--price` | `-p` | Decimal | New authorized price | |
| `--description` | `-d` | String | New description | |
| `--category` | `-c` | String | New category | |
| `--notes` | | String | New notes | |
| `--activate` | | Flag | Activate part | |
| `--deactivate` | | Flag | Deactivate part | |

### 5. `parts delete` - Delete Part

**Purpose**: Delete or deactivate a part

**Syntax**:
```bash
invoice-checker parts delete [OPTIONS] PART_NUMBER
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `PART_NUMBER` | | String | Part number to delete | Required |
| `--soft` | | Flag | Soft delete (deactivate) | True |
| `--hard` | | Flag | Permanently delete from database | False |
| `--force` | | Flag | Skip confirmation prompt | False |

### 6. `parts import` - Import Parts

**Purpose**: Import parts from a CSV file

**Syntax**:
```bash
invoice-checker parts import [OPTIONS] INPUT_FILE
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `INPUT_FILE` | | Path | CSV file containing parts data | Required |
| `--update-existing` | | Flag | Update existing parts | False (skip) |
| `--dry-run` | | Flag | Validate data without making changes | False |
| `--batch-size` | | Integer | Process in batches | 100 |

### 7. `parts export` - Export Parts

**Purpose**: Export parts to a CSV file

**Syntax**:
```bash
invoice-checker parts export [OPTIONS] OUTPUT_FILE
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `OUTPUT_FILE` | | Path | Output CSV file path | Required |
| `--category` | `-c` | String | Filter by category | |
| `--active-only` | | Flag | Export only active parts | True |
| `--include-inactive` | | Flag | Include inactive parts | False |

### 8. `parts stats` - Parts Statistics

**Purpose**: Display statistical information about parts

**Syntax**:
```bash
invoice-checker parts stats [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--category` | `-c` | String | Filter by category | |
| `--format` | `-f` | Choice | Output format (table, json) | table |

---

## Database Management Commands

### 1. `backup` - Create Database Backup

**Purpose**: Create a backup of the database

**Syntax**:
```bash
invoice-checker backup [OPTIONS] [OUTPUT_PATH]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `OUTPUT_PATH` | | Path | Backup file path | auto-generated |
| `--compress` | | Flag | Compress backup file | False |
| `--include-logs` | | Flag | Include discovery logs in backup | True |

### 2. `restore` - Restore Database

**Purpose**: Restore database from a backup file

**Syntax**:
```bash
invoice-checker restore [OPTIONS] BACKUP_PATH
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `BACKUP_PATH` | | Path | Path to backup file | Required |
| `--force` | | Flag | Skip confirmation prompt | False |
| `--verify` | | Flag | Verify backup integrity before restore | True |

### 3. `migrate` - Database Migration

**Purpose**: Perform database schema migration

**Syntax**:
```bash
invoice-checker migrate [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--to-version` | | String | Target schema version | latest |
| `--dry-run` | | Flag | Show migration plan without executing | False |
| `--backup-first` | | Flag | Create backup before migration | True |

### 4. `maintenance` - Database Maintenance

**Purpose**: Perform database maintenance tasks

**Syntax**:
```bash
invoice-checker maintenance [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--vacuum` | | Flag | Vacuum database to reclaim space | True |
| `--cleanup-logs` | | Flag | Clean up old discovery logs | True |
| `--verify-integrity` | | Flag | Verify data integrity | True |
| `--auto-backup` | | Flag | Create backup before maintenance | True |

---

## Configuration Management Commands

### 1. `config get` - Get Configuration Value

**Purpose**: Retrieve a configuration value

**Syntax**:
```bash
invoice-checker config get [OPTIONS] KEY
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `KEY` | | String | Configuration key | Required |
| `--format` | `-f` | Choice | Output format (value, json) | value |

### 2. `config set` - Set Configuration Value

**Purpose**: Set a configuration value

**Syntax**:
```bash
invoice-checker config set [OPTIONS] KEY VALUE
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `KEY` | | String | Configuration key | Required |
| `VALUE` | | String | Configuration value | Required |
| `--type` | `-t` | Choice | Value type (string, number, boolean, json) | auto-detect |
| `--description` | `-d` | String | Configuration description | |
| `--category` | `-c` | String | Configuration category | general |

### 3. `config list` - List Configurations

**Purpose**: List all configuration settings

**Syntax**:
```bash
invoice-checker config list [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--category` | `-c` | String | Filter by category | |
| `--format` | `-f` | Choice | Output format (table, json) | table |

### 4. `config reset` - Reset Configuration

**Purpose**: Reset configuration to default values

**Syntax**:
```bash
invoice-checker config reset [OPTIONS] [KEY]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `KEY` | | String | Specific key to reset (optional) | |
| `--force` | | Flag | Skip confirmation prompt | False |

---

## Discovery Log Management Commands

### 1. `discovery list` - List Discovery Logs

**Purpose**: List discovery log entries with filtering

**Syntax**:
```bash
invoice-checker discovery list [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--part-number` | `-p` | String | Filter by part number | |
| `--invoice-number` | `-i` | String | Filter by invoice number | |
| `--session-id` | `-s` | String | Filter by session ID | |
| `--days-back` | `-d` | Integer | Show entries from last N days | 30 |
| `--action` | `-a` | Choice | Filter by action type | |
| `--limit` | `-l` | Integer | Maximum number of results | |
| `--format` | `-f` | Choice | Output format (table, csv, json) | table |

### 2. `discovery export` - Export Discovery Logs

**Purpose**: Export discovery logs to CSV file

**Syntax**:
```bash
invoice-checker discovery export [OPTIONS] OUTPUT_FILE
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `OUTPUT_FILE` | | Path | Output CSV file path | Required |
| `--days-back` | `-d` | Integer | Export entries from last N days | |
| `--session-id` | `-s` | String | Export specific session | |

### 3. `discovery cleanup` - Clean Up Old Logs

**Purpose**: Clean up old discovery log entries

**Syntax**:
```bash
invoice-checker discovery cleanup [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--retention-days` | `-r` | Integer | Keep logs newer than N days | 365 |
| `--dry-run` | | Flag | Show what would be deleted without deleting | False |
| `--force` | | Flag | Skip confirmation prompt | False |

---

## Utility Commands

### 1. `help` - Show Help Information

**Purpose**: Display help information for commands

**Syntax**:
```bash
invoice-checker help [COMMAND]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `COMMAND` | | String | Show help for specific command | |

### 2. `version` - Show Version Information

**Purpose**: Display version and system information

**Syntax**:
```bash
invoice-checker version [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--detailed` | | Flag | Show detailed version and dependency information | False |

### 3. `status` - Show System Status

**Purpose**: Display system status and health information

**Syntax**:
```bash
invoice-checker status [OPTIONS]
```

**Parameters**:
| Parameter | Short | Type | Description | Default |
|-----------|-------|------|-------------|---------|
| `--format` | `-f` | Choice | Output format (table, json) | table |

---

## Parameter Validation

### Validation Rules

| Data Type | Validation Rules | Examples |
|-----------|------------------|----------|
| **Part Numbers** | Alphanumeric with underscores, hyphens, periods (2-20 chars) | `GP0171NAVY`, `GS-0448`, `ABC_123` |
| **Prices** | Positive decimal values with up to 4 decimal places | `15.50`, `0.3000`, `125.99` |
| **File Paths** | Must exist and be accessible for input; parent directory must exist for output | `./invoices`, `/path/to/file.pdf` |
| **Dates** | ISO format or common date formats | `2025-07-29`, `07/29/2025` |
| **Enum Values** | Must match predefined choices | `csv`, `json`, `parts_based` |

### Error Messages

- **Input Validation Errors**: Clear message with valid options and examples
- **File Access Errors**: Specific error with suggested solutions
- **Database Errors**: User-friendly message with recovery options
- **Network/Permission Errors**: Actionable error messages with troubleshooting steps

---

## Interactive Prompt Flows

When required arguments are missing, the CLI provides guided prompts:

### Example: `process` Command Flow

```
Invoice Rate Detection System
=============================

Input folder not specified.
Enter path to folder containing PDF invoices: /path/to/invoices

✓ Found 15 PDF files in /path/to/invoices

Output file not specified.
Enter output file path [report.csv]: custom_report.csv

Validation mode not specified.
Select validation mode:
  1) Parts-based validation (recommended)
  2) Threshold-based validation
Enter choice [1]: 1

Enable interactive part discovery? [Y/n]: y

Processing invoices...
[████████████████████████████████████████] 100% (15/15 files)

✓ Processing complete!
  - Files processed: 15
  - Anomalies found: 23
  - Unknown parts: 5
  - Report saved: custom_report.csv

Would you like to review unknown parts now? [y/N]: y
```

### Example: `parts add` Command Flow

```
Adding new part to database...

Part number: GP0171NAVY
Authorized price: 15.50
Description [optional]: Navy Work Pants
Category [optional]: Clothing
Notes [optional]: Standard work uniform item

✓ Part GP0171NAVY added successfully!

Would you like to add another part? [y/N]: n
```

---

## Help System

### Command Help Structure

Each command includes comprehensive help with:

1. **Purpose**: Clear description of what the command does
2. **Usage**: Syntax with required and optional parameters
3. **Parameters**: Detailed parameter descriptions with types and defaults
4. **Examples**: Common use cases with sample commands
5. **Related Commands**: Links to related functionality
6. **Troubleshooting**: Common issues and solutions

### Example Help Output

```
invoice-checker parts add --help

PURPOSE:
    Add a new part to the master parts database

USAGE:
    invoice-checker parts add [OPTIONS] PART_NUMBER PRICE

PARAMETERS:
    PART_NUMBER         Unique part identifier (required)
    PRICE              Authorized price in dollars (required)
    
    -d, --description   Part description
    -c, --category      Part category for organization
    --source           Source of part data (manual, discovered, imported)
    --notes            Additional notes about the part

EXAMPLES:
    # Add a basic part
    invoice-checker parts add GP0171NAVY 15.50
    
    # Add a part with full details
    invoice-checker parts add GP0171NAVY 15.50 \
        --description "Navy Work Pants" \
        --category "Clothing" \
        --notes "Standard work uniform item"

RELATED COMMANDS:
    parts list         List all parts
    parts update       Update existing part
    parts get          Get part details

TROUBLESHOOTING:
    - Part already exists: Use 'parts update' to modify existing parts
    - Invalid price format: Use decimal format (e.g., 15.50, not $15.50)
    - Permission denied: Check database file permissions
```

---

## Progress Indicators

### Progress Bar Types

1. **File Processing**: Progress bar with current file and percentage
   ```
   Processing invoices... [████████████████████████████████████████] 85% (17/20 files)
   Current: invoice_5790265785.pdf
   ```

2. **Database Operations**: Spinner with operation description
   ```
   Creating database backup... ⠋ (15.2 MB written)
   ```

3. **Batch Operations**: Overall progress with ETA
   ```
   Batch processing folders... [██████████████████████████              ] 67% (4/6 folders)
   ETA: 2 minutes remaining
   ```

4. **Import/Export**: Records processed with rate information
   ```
   Importing parts... [████████████████████████████████████████] 100% (1,250/1,250 records)
   Rate: 125 records/second
   ```

### User Feedback Messages

- **Success Messages**: Clear confirmation with key details
  ```
  ✓ Processing complete!
    - Files processed: 15
    - Anomalies found: 23
    - Total overcharge: $145.67
    - Report saved: report.csv
  ```

- **Warning Messages**: Non-fatal issues with suggested actions
  ```
  ⚠ Warning: 3 PDF files could not be processed
    - invoice_corrupted.pdf: File appears to be corrupted
    - invoice_empty.pdf: No text content found
    - invoice_locked.pdf: File is password protected
    
  Suggestion: Check file integrity and try again
  ```

- **Error Messages**: Specific errors with recovery guidance
  ```
  ✗ Error: Database connection failed
    
  Possible causes:
    - Database file is locked by another process
    - Insufficient disk space
    - File permissions issue
    
  Solutions:
    1. Close other instances of the application
    2. Check available disk space (need at least 100MB)
    3. Run with administrator privileges
  ```

---

## Error Handling

### Error Categories

1. **User Input Errors**
   - Invalid parameters or arguments
   - Missing required information
   - Malformed data

2. **System Errors**
   - File system access issues
   - Database connection problems
   - Network connectivity issues

3. **Data Errors**
   - Corrupted files
   - Invalid data formats
   - Constraint violations

4. **Business Logic Errors**
   - Validation failures
   - Workflow violations
   - State inconsistencies

### Error Response Format

```json
{
  "error": {
    "code": "PART_NOT_FOUND",
    "message": "Part 'GP0171NAVY' not found in database",
    "details": {
      "part_number": "GP0171NAVY",
      "suggestion": "Use 'parts list' to see available parts"
    },
    "recovery_actions": [
      "Check part number spelling",
      "Add the part using 'parts add' command",
      "Import parts from CSV file"
    ]
  }
}
```

---

## Implementation Guidelines

### Command-Line Parsing Strategy

1. **Framework**: Use `click` library for robust CLI framework
2. **Command Groups**: Organize commands into logical groups
3. **Parameter Types**: Define custom parameter types for validation
4. **Context Passing**: Use click context for sharing state between commands

### Code Organization

```
cli/
├── __init__.py
├── main.py              # Main entry point and command groups
├── commands/
│   ├── __init__.py
│   ├── process.py       # Invoice processing commands
│   ├── parts.py         # Parts management commands
│   ├── database.py      # Database management commands
│   ├── config.py        # Configuration commands
│   ├── discovery.py     # Discovery log commands
│   └── utils.py         # Utility commands
├── validators.py        # Parameter validation functions
├── prompts.py          # Interactive prompt handlers
├── formatters.py       # Output formatting utilities
├── progress.py         # Progress indicator implementations
└── exceptions.py       # Custom exception classes
```

### Testing Strategy

1. **Unit Tests**: Test individual command functions
2. **Integration Tests**: Test command interactions with database
3. **CLI Tests**: Test command-line interface using click testing utilities
4. **User Acceptance Tests**: Test complete user workflows

### Documentation Requirements

1. **Inline Documentation**: Comprehensive docstrings for all functions
2. **Command Help**: Built-in help for all commands and parameters
3. **User Guide**: Step-by-step user documentation
4. **API Reference**: Technical reference for developers

---

## Conclusion

This CLI design provides a comprehensive, user-friendly interface that supports the complete Invoice Rate Detection System workflow. The hierarchical command structure, consistent parameter naming, and extensive help system make it accessible to both novice and expert users while maintaining the flexibility needed for advanced use cases.

The design emphasizes usability, discoverability, and robustness, ensuring that users can efficiently accomplish their tasks while receiving clear feedback and guidance throughout the process.