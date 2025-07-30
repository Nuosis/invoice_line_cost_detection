# Invoice Rate Detection System - User Manual

**Version 1.0.0**  
**Last Updated:** July 30, 2025

---

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Parts Discovery and Database Setup](#parts-discovery-and-database-setup)
3. [Processing Invoices](#processing-invoices)
4. [Backing Up and Restoring](#backing-up-and-restoring)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)
7. [Command Reference](#command-reference)

---

## Installation and Setup

### System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 512MB RAM
- **Storage**: 100MB free disk space
- **Permissions**: Read access to invoice files, write access for reports and database

### Installation Instructions

#### Windows Installation

1. **Install Python** (if not already installed):
   - Download Python from [python.org](https://python.org)
   - During installation, check "Add Python to PATH"
   - Verify installation: Open Command Prompt and run `python --version`

2. **Install UV Package Manager**:
   ```cmd
   pip install uv
   ```

3. **Download and Setup the Application**:
   ```cmd
   # Download the application (replace with actual download location)
   cd C:\Users\YourName\Downloads
   unzip invoice-rate-detection.zip
   cd invoice-rate-detection
   
   # Install dependencies
   uv sync
   ```

4. **Test Installation**:
   ```cmd
   uv run invoice-checker --help
   ```

#### macOS Installation

1. **Install Python** (using Homebrew - recommended):
   ```bash
   # Install Homebrew if not already installed
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # Install Python
   brew install python
   ```

2. **Install UV Package Manager**:
   ```bash
   pip3 install uv
   ```

3. **Download and Setup the Application**:
   ```bash
   # Download and extract the application
   cd ~/Downloads
   unzip invoice-rate-detection.zip
   cd invoice-rate-detection
   
   # Install dependencies
   uv sync
   ```

4. **Test Installation**:
   ```bash
   uv run invoice-checker --help
   ```

#### Linux Installation (Ubuntu/Debian)

1. **Install Python and Dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   ```

2. **Install UV Package Manager**:
   ```bash
   pip3 install uv
   ```

3. **Download and Setup the Application**:
   ```bash
   # Download and extract the application
   cd ~/Downloads
   unzip invoice-rate-detection.zip
   cd invoice-rate-detection
   
   # Install dependencies
   uv sync
   ```

4. **Test Installation**:
   ```bash
   uv run invoice-checker --help
   ```

### Initial Configuration

After installation, test the basic functionality:

```bash
# Test the modern CLI system
uv run invoice-checker --help

# Check system status
uv run invoice-checker status
```

The modern CLI system provides comprehensive parts-based validation, interactive discovery, and advanced reporting features.

---

## Parts Discovery and Database Setup

The Invoice Rate Detection System uses a master parts database to validate invoice line items against authorized prices. This section covers setting up and managing your parts database.

### Understanding the Parts Database

The system stores parts information in a local SQLite database with the following key data:
- **Part Number**: Unique identifier for each part
- **Authorized Price**: The approved price for the part
- **Description**: Human-readable description
- **Category**: Optional grouping (e.g., "Clothing", "Tools")
- **Source**: How the part was added (manual, discovered, imported)

### Initial Database Setup

When you first run the system, it automatically creates an empty database. You can populate it in several ways:

#### Method 1: Interactive Part Discovery (Recommended)

This is the easiest way to build your database while processing invoices:

1. **Start Processing with Discovery Enabled**:
   ```bash
   uv run invoice-checker process ./invoices --interactive
   ```

2. **When Unknown Parts are Found**, you'll see prompts like:
   ```
   ┌─ Unknown Part Discovered ─────────────────────────────────────┐
   │ Part Number    │ GS0448                                       │
   │ Description    │ SHIRT WORK LS BTN COTTON                     │
   │ Discovered Price│ $15.50                                      │
   │ Quantity       │ 2                                            │
   │ Invoice Number │ 5790256943                                   │
   └────────────────┴──────────────────────────────────────────────┘
   
   What would you like to do with this unknown part?
   1. Add to database now (with full details)
   2. Mark for later review (collect for batch processing)
   3. Skip this part (don't add to database)
   ```

3. **Choose Option 1** to add parts immediately, or **Option 2** to review later

#### Method 2: Manual Part Addition

Add individual parts manually:

```bash
# Add a basic part
uv run invoice-checker parts add GP0171NAVY 15.50

# Add a part with full details
uv run invoice-checker parts add GP0171NAVY 15.50 \
  --description "Navy Work Pants" \
  --category "Clothing" \
  --notes "Standard work uniform item"
```

#### Method 3: Bulk Import from CSV

If you have existing parts data in a spreadsheet:

1. **Create a CSV file** with the following columns:
   ```csv
   part_number,authorized_price,description,category,notes
   GP0171NAVY,15.50,Navy Work Pants,Clothing,Standard uniform
   GP0171KHAKI,16.00,Khaki Work Pants,Clothing,Standard uniform
   TOOL001,25.00,Hammer,Tools,16oz claw hammer
   ```

2. **Import the CSV**:
   ```bash
   uv run invoice-checker parts import parts.csv
   ```

3. **Verify the import**:
   ```bash
   uv run invoice-checker parts list
   ```

### Managing Your Parts Database

#### Viewing Parts

```bash
# List all active parts
uv run invoice-checker parts list

# List parts in a specific category
uv run invoice-checker parts list --category "Clothing"

# Get detailed information about a specific part
uv run invoice-checker parts get GP0171NAVY

# Export parts to CSV for backup or editing
uv run invoice-checker parts export my_parts.csv
```

#### Updating Parts

```bash
# Update a part's price
uv run invoice-checker parts update GP0171NAVY --price 16.00

# Update multiple fields
uv run invoice-checker parts update GP0171NAVY \
  --price 16.00 \
  --description "Updated Navy Work Pants" \
  --category "Workwear"

# Deactivate a part (soft delete)
uv run invoice-checker parts update GP0171NAVY --deactivate
```

#### Database Statistics

Monitor your database growth:

```bash
# Show overall statistics
uv run invoice-checker parts stats

# Show statistics for a specific category
uv run invoice-checker parts stats --category "Clothing"
```

---

## Processing Invoices

This section covers the core functionality of processing PDF invoices to detect pricing anomalies.

### Basic Invoice Processing

#### Simple Processing (Interactive Mode)

For first-time users or occasional processing:

1. **Start Interactive Mode**:
   ```bash
   uv run invoice-checker
   ```

2. **Follow the Prompts**:
   - **Step 1**: Select your invoice folder
   - **Step 2**: Configure output format and location
   - **Step 3**: Choose validation mode (parts-based recommended)
   - **Step 4**: Enable/disable interactive part discovery
   - **Step 5**: Processing begins automatically

3. **Review Results**: The system will show a summary and offer next actions

#### Command-Line Processing

For regular use or automation:

```bash
# Basic processing with parts-based validation
uv run invoice-checker process ./invoices --output report.csv

# Process with interactive discovery enabled
uv run invoice-checker process ./invoices --interactive --output report.csv

# Process a single invoice file
uv run invoice-checker process invoice.pdf --output single_report.csv

# Process a single file with interactive discovery
uv run invoice-checker process invoice.pdf --interactive --output report.csv

# Process a single file with custom threshold
uv run invoice-checker process invoice.pdf --threshold 0.20 --output report.csv
```

### Single File Processing

The system supports processing individual PDF invoice files, which is particularly useful for:
- **Urgent invoice validation**: Quick processing of time-sensitive invoices
- **Problem file troubleshooting**: Isolating and debugging specific invoice issues
- **New supplier testing**: Testing invoices from new suppliers before batch processing
- **Interactive part discovery**: Adding new parts with immediate feedback

#### Single File Examples

```bash
# Basic single file processing
uv run invoice-checker process invoice_001.pdf --output report.csv

# Single file with JSON output
uv run invoice-checker process invoice_001.pdf --format json --output report.json

# Single file with threshold validation
uv run invoice-checker process invoice_001.pdf --validation-mode threshold_based --threshold 0.15

# Collect unknown parts from single file
uv run invoice-checker collect-unknowns problem_invoice.pdf --suggest-prices --output unknowns.csv
```

### Advanced Processing Options

#### Batch Processing Multiple Folders

Process multiple folders of invoices simultaneously:

```bash
# Process all folders in a directory (sequential)
uv run invoice-checker batch ./invoice_folders --output-dir ./reports

# Process with parallel processing (faster)
uv run invoice-checker batch ./invoice_folders --parallel --max-workers 4

# Continue processing even if some folders fail
uv run invoice-checker batch ./invoice_folders --continue-on-error
```

#### Validation Modes

The system supports two validation modes:

1. **Parts-Based Validation** (Recommended):
   - Compares invoice prices against your parts database
   - Identifies unknown parts for addition to database
   - Provides precise anomaly detection

   ```bash
   uv run invoice-checker process ./invoices --validation-mode parts_based
   ```

2. **Threshold-Based Validation** (Legacy):
   - Flags any line item above a specified threshold
   - Simpler but less precise
   - Useful for initial screening

   ```bash
   uv run invoice-checker process ./invoices --validation-mode threshold_based --threshold 0.30
   ```

#### Unknown Parts Handling

When processing invoices, you may encounter parts not in your database:

1. **Interactive Mode**: Prompts you to add parts immediately
2. **Batch Collection Mode**: Collects unknown parts for later review
3. **Collection Only Mode**: Just identifies unknown parts without validation

```bash
# Collect unknown parts from single file
uv run invoice-checker collect-unknowns invoice.pdf --output single_unknowns.csv

# Collect unknown parts from folder
uv run invoice-checker collect-unknowns ./invoices --output unknown_parts.csv

# Include price suggestions for single file
uv run invoice-checker collect-unknowns invoice.pdf --suggest-prices --output unknowns_with_prices.csv

# Include price suggestions for folder
uv run invoice-checker collect-unknowns ./invoices --suggest-prices --output unknown_parts.csv
```

### Understanding Reports

#### CSV Report Format

The CSV report includes these columns:

| Column | Description |
|--------|-------------|
| Invoice # | Invoice number from the PDF |
| Date | Invoice date |
| Line Item | Part number/item code |
| Rate | Price per unit from invoice |
| Qty | Quantity ordered |
| Overcharge | Calculated overcharge amount |
| Description | Item description |
| PDF File | Source PDF filename |

#### Report Analysis

```bash
# View processing results
uv run invoice-checker status

# Review recent discovery sessions
uv run invoice-checker discovery sessions

# Get statistics on discovered parts
uv run invoice-checker discovery stats --days 7
```

### Processing Workflows

#### Daily Processing Workflow

1. **Place new invoices** in your designated folder
2. **Run processing**:
   ```bash
   uv run invoice-checker process ./daily_invoices --interactive
   ```
3. **Review and add unknown parts** as prompted
4. **Check the generated report** for anomalies
5. **Archive processed invoices** to avoid reprocessing

#### Single File Processing Workflow

1. **Identify the specific invoice** that needs processing
2. **Process the individual file**:
   ```bash
   uv run invoice-checker process urgent_invoice.pdf --interactive --output urgent_report.csv
   ```
3. **Review results immediately** for quick decision making
4. **Add any unknown parts** discovered during processing
5. **Move processed file** to appropriate folder

#### Weekly Review Workflow

1. **Review discovery statistics**:
   ```bash
   uv run invoice-checker discovery stats --days 7
   ```
2. **Export parts database** for backup:
   ```bash
   uv run invoice-checker parts export weekly_backup.csv
   ```
3. **Review and clean up** old discovery sessions:
   ```bash
   uv run invoice-checker discovery sessions --limit 20
   ```

---

## Backing Up and Restoring

Regular backups protect your parts database and configuration settings.

### Database Backup

#### Creating Backups

```bash
# Create a standard backup
uv run invoice-checker database backup

# Create a backup with custom name and location
uv run invoice-checker database backup ./backups/backup_2025_07_30.db

# Create a compressed backup (smaller file size)
uv run invoice-checker database backup --compress

# Create backup including discovery logs
uv run invoice-checker database backup --include-logs
```

#### Automatic Backup Scheduling

**Windows (Task Scheduler)**:
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily/weekly)
4. Set action to run:
   ```cmd
   uv run invoice-checker database backup
   ```

**macOS/Linux (Cron)**:
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/invoice-rate-detection && uv run invoice-checker database backup
```

### Database Restore

#### Restoring from Backup

```bash
# Restore from a backup file
uv run invoice-checker database restore backup_2025_07_30.db

# Force restore without confirmation
uv run invoice-checker database restore backup_2025_07_30.db --force

# Skip backup verification (faster but less safe)
uv run invoice-checker database restore backup_2025_07_30.db --no-verify
```

**⚠️ Important**: Restoring replaces your current database. The system automatically creates a pre-restore backup for safety.

### Parts Data Backup

#### Export Parts to CSV

```bash
# Export all active parts
uv run invoice-checker parts export all_parts.csv

# Export all parts including inactive
uv run invoice-checker parts export all_parts.csv --include-inactive

# Export specific category
uv run invoice-checker parts export clothing_parts.csv --category "Clothing"
```

#### Import Parts from CSV

```bash
# Import new parts
uv run invoice-checker parts import new_parts.csv

# Import and update existing parts
uv run invoice-checker parts import updated_parts.csv --update-existing

# Test import without making changes
uv run invoice-checker parts import test_parts.csv --dry-run
```

### Database Maintenance

#### Regular Maintenance

```bash
# Run all maintenance tasks
uv run invoice-checker database maintenance

# Run specific maintenance tasks
uv run invoice-checker database maintenance --no-cleanup-logs --no-verify-integrity

# Skip automatic backup during maintenance
uv run invoice-checker database maintenance --no-auto-backup
```

#### Database Migration

When updating to newer versions:

```bash
# Check current database version
uv run invoice-checker database migrate --dry-run

# Migrate to latest version
uv run invoice-checker database migrate

# Migrate to specific version
uv run invoice-checker database migrate --to-version 2.0
```

---

## Advanced Features

### Bulk Operations

For managing large numbers of parts efficiently:

#### Bulk Updates

```bash
# Update prices for multiple parts from CSV
uv run invoice-checker parts bulk-update price_updates.csv --field price

# Update multiple fields
uv run invoice-checker parts bulk-update updates.csv --field price --field description

# Preview changes before applying
uv run invoice-checker parts bulk-update updates.csv --field price --dry-run

# Filter updates by category
uv run invoice-checker parts bulk-update updates.csv --field price --filter-category "Clothing"
```

#### Bulk Deletion

```bash
# Soft delete (deactivate) multiple parts
uv run invoice-checker parts bulk-delete parts_to_remove.csv

# Permanently delete parts
uv run invoice-checker parts bulk-delete parts_to_remove.csv --hard

# Force deletion without confirmation
uv run invoice-checker parts bulk-delete parts_to_remove.csv --force
```

#### Bulk Activation

```bash
# Reactivate multiple deactivated parts
uv run invoice-checker parts bulk-activate parts_to_activate.csv

# Preview activations
uv run invoice-checker parts bulk-activate parts_to_activate.csv --dry-run
```

### Discovery Management

#### Session Management

```bash
# List recent discovery sessions
uv run invoice-checker discovery sessions

# Show detailed session information
uv run invoice-checker discovery sessions --detailed

# Review specific session
uv run invoice-checker discovery review --session-id abc123
```

#### Discovery Analytics

```bash
# Show overall discovery statistics
uv run invoice-checker discovery stats

# Show statistics for specific time period
uv run invoice-checker discovery stats --days 30

# Export discovery data for analysis
uv run invoice-checker discovery export --output discovery_data.csv
```

### Configuration Management

#### System Configuration

```bash
# List all configuration settings
uv run invoice-checker config list

# Get specific configuration value
uv run invoice-checker config get validation_mode

# Set configuration value
uv run invoice-checker config set interactive_discovery true

# Reset configuration to defaults
uv run invoice-checker config reset validation_mode
```

#### Common Configuration Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `validation_mode` | `parts_based` | Default validation mode |
| `interactive_discovery` | `true` | Enable interactive part discovery |
| `discovery_batch_mode` | `false` | Collect unknown parts for batch review |
| `price_tolerance` | `0.001` | Price comparison tolerance |
| `log_retention_days` | `365` | Days to keep discovery logs |

### Automation and Scripting

#### Batch Scripts

**Windows Batch File** (`process_daily.bat`):
```batch
@echo off
cd /d "C:\path\to\invoice-rate-detection"
uv run invoice-checker process "C:\invoices\daily" --output "C:\reports\daily_report_%date:~-4,4%_%date:~-10,2%_%date:~-7,2%.csv"
echo Processing complete. Report saved.
pause
```

**Linux/macOS Shell Script** (`process_daily.sh`):
```bash
#!/bin/bash
cd /path/to/invoice-rate-detection
DATE=$(date +%Y_%m_%d)
uv run invoice-checker process ./invoices/daily --output "./reports/daily_report_${DATE}.csv"
echo "Processing complete. Report saved."
```

#### Integration with Other Systems

**PowerShell Integration** (Windows):
```powershell
# Process invoices and email report
$reportPath = "C:\reports\daily_report.csv"
& uv run invoice-checker process "C:\invoices" --output $reportPath

if (Test-Path $reportPath) {
    Send-MailMessage -To "manager@company.com" -From "system@company.com" `
                     -Subject "Daily Invoice Report" -Body "Report attached" `
                     -Attachments $reportPath -SmtpServer "smtp.company.com"
}
```

### Performance Optimization

#### Large Dataset Processing

```bash
# Process large batches with parallel processing
uv run invoice-checker batch ./large_invoice_folders --parallel --max-workers 8

# Use batch processing for better memory management
uv run invoice-checker parts bulk-update large_update.csv --batch-size 100

# Enable progress tracking for long operations
uv run invoice-checker process ./large_folder --verbose
```

#### Database Optimization

```bash
# Regular database maintenance
uv run invoice-checker database maintenance

# Vacuum database to reclaim space
uv run invoice-checker database maintenance --vacuum

# Clean up old discovery logs
uv run invoice-checker database maintenance --cleanup-logs
```

---

## Troubleshooting

### Common Issues

#### Issue: "Command not found" Error
**Problem**: Getting "command not found" when trying to run the application.

**Solutions**:
1. **Check Python Installation**:
   ```bash
   python3 --version
   # Should show Python 3.8 or higher
   ```

2. **Check UV Installation**:
   ```bash
   uv --version
   # Should show UV version
   ```

3. **Ensure you're in the correct directory**:
   ```bash
   ls -la
   # Should see pyproject.toml and other project files
   ```

#### Issue: "No module named 'pdfplumber'" Error
**Problem**: Missing dependencies when running the script.

**Solution**:
```bash
# Reinstall dependencies
uv sync
```

#### Issue: "Permission denied" Error
**Problem**: Cannot access files or directories.

**Solutions**:
1. **Check file permissions**:
   ```bash
   ls -la pyproject.toml
   # Ensure you have read access to project files
   ```

2. **Run with proper permissions**:
   ```bash
   # The modern CLI should not require special permissions
   uv run invoice-checker --help
   ```

#### Issue: PDF Processing Errors
**Problem**: Cannot read or process PDF files.

**Solutions**:
1. **Check PDF file integrity**:
   - Try opening the PDF in a PDF viewer
   - Ensure the PDF is not password-protected
   - Verify the PDF contains text (not just images)

2. **Check file paths**:
   ```bash
   # Use absolute paths if relative paths don't work
   uv run invoice-checker process --input /full/path/to/invoices --output report.csv
   ```

#### Issue: Empty or Incorrect Reports
**Problem**: Generated reports are empty or contain wrong data.

**Solutions**:
1. **Check validation settings**:
   ```bash
   # Use parts-based validation (recommended)
   uv run invoice-checker process --input ./invoices --output report.csv
   ```

2. **Enable verbose logging**:
   ```bash
   uv run invoice-checker process --input ./invoices --output report.csv --verbose
   ```

3. **Verify PDF content**:
   - Ensure PDFs contain the expected invoice format
   - Check that line items and rates are clearly visible in the PDF

#### Issue: Database Connection Errors
**Problem**: Cannot connect to or create the database.

**Solutions**:
1. **Check database file permissions**:
   ```bash
   ls -la *.db
   # Ensure you have read/write permissions
   ```

2. **Reset database**:
   ```bash
   # Backup existing database first
   cp invoice_data.db invoice_data.db.backup
   
   # Remove and recreate
   rm invoice_data.db
   uv run invoice-checker status  # Will recreate database
   ```

### Modern CLI System

The modern CLI system provides comprehensive functionality through the `uv run invoice-checker` command with various subcommands for different operations.

**For Developers**: To fix this issue:
1. Check the `pyproject.toml` configuration
2. Verify the package structure and import paths
3. Ensure all modules are properly installed in the virtual environment

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Enable verbose logging
uv run invoice-checker process --input ./invoices --output report.csv --verbose

# Check system status for diagnostic information
uv run invoice-checker status --verbose
```

### Getting Help

1. **Check the documentation**: Review this manual and the README.md file
2. **Verify system requirements**: Ensure Python 3.8+ and all dependencies are installed
3. **Test with sample data**: Use the provided sample invoices in `docs/invoices/`
4. **Check log files**: Look for any error messages in the console output
5. **Contact support**: If issues persist, provide:
   - Your operating system and version
   - Python version (`python3 --version`)
   - UV version (`uv --version`)
   - Complete error message
   - Steps to reproduce the issue

---

## Command Reference

### Main Commands

| Command | Description |
|---------|-------------|
| `invoice-checker` | Interactive processing mode |
| `invoice-checker process` | Process invoices |
| `invoice-checker parts` | Parts management |
| `invoice-checker database` | Database operations |
| `invoice-checker config` | Configuration management |
| `invoice-checker discovery` | Discovery management |
| `invoice-checker status` | System status |
| `invoice-checker version` | Version information |

### Invoice Processing Commands

```bash
# Process invoices (single file or folder)
invoice-checker process <input_path> [options]
  --output, -o          Output file path
  --format, -f          Output format (csv, txt, json)
  --interactive, -i     Enable interactive discovery
  --collect-unknown     Collect unknown parts
  --validation-mode     Validation mode (parts_based, threshold_based)
  --threshold, -t       Threshold for threshold-based mode

# Examples:
# Single file: invoice-checker process invoice.pdf --output report.csv
# Folder:      invoice-checker process ./invoices --output report.csv

# Batch processing
invoice-checker batch <input_path> [options]
  --output-dir, -o      Output directory
  --parallel, -p        Enable parallel processing
  --max-workers         Maximum worker threads
  --continue-on-error   Continue if folders fail

# Collect unknown parts (single file or folder)
invoice-checker collect-unknowns <input_path> [options]
  --output, -o          Output file
  --suggest-prices      Include price suggestions

# Examples:
# Single file: invoice-checker collect-unknowns invoice.pdf --output unknowns.csv
# Folder:      invoice-checker collect-unknowns ./invoices --output unknowns.csv
```

### Parts Management Commands

```bash
# Add part
invoice-checker parts add <part_number> <price> [options]
  --description, -d     Part description
  --category, -c        Part category
  --notes               Additional notes

# List parts
invoice-checker parts list [options]
  --category, -c        Filter by category
  --active-only         Show only active parts
  --format, -f          Output format (table, csv, json)
  --limit, -l           Maximum results
  --sort-by             Sort field

# Get part details
invoice-checker parts get <part_number> [options]
  --format, -f          Output format
  --include-history     Include discovery history

# Update part
invoice-checker parts update <part_number> [options]
  --price, -p           New price
  --description, -d     New description
  --category, -c        New category
  --activate            Activate part
  --deactivate          Deactivate part

# Delete part
invoice-checker parts delete <part_number> [options]
  --soft                Soft delete (default)
  --hard                Permanent delete
  --force               Skip confirmation

# Import/Export
invoice-checker parts import <file> [options]
  --update-existing     Update existing parts
  --dry-run             Preview without changes
  --batch-size          Process batch size

invoice-checker parts export <file> [options]
  --category, -c        Filter by category
  --include-inactive    Include inactive parts

# Statistics
invoice-checker parts stats [options]
  --category, -c        Filter by category
  --format, -f          Output format
```

### Bulk Operations Commands

```bash
# Bulk update
invoice-checker parts bulk-update <file> [options]
  --field               Fields to update
  --filter-category     Filter by category
  --dry-run             Preview changes
  --batch-size          Process batch size

# Bulk delete
invoice-checker parts bulk-delete <file> [options]
  --soft                Soft delete (default)
  --hard                Permanent delete
  --force               Skip confirmation
  --dry-run             Preview deletions

# Bulk activate
invoice-checker parts bulk-activate <file> [options]
  --filter-category     Filter by category
  --dry-run             Preview activations
```

### Database Commands

```bash
# Backup
invoice-checker database backup [output_path] [options]
  --compress            Compress backup
  --include-logs        Include discovery logs

# Restore
invoice-checker database restore <backup_path> [options]
  --force               Skip confirmation
  --verify/--no-verify  Verify backup integrity

# Migrate
invoice-checker database migrate [options]
  --to-version          Target version
  --dry-run             Show migration plan
  --backup-first        Create backup first

# Maintenance
invoice-checker database maintenance [options]
  --vacuum              Vacuum database
  --cleanup-logs        Clean old logs
  --verify-integrity    Verify integrity
  --auto-backup         Create backup first
```

### Configuration Commands

```bash
# Get configuration
invoice-checker config get <key> [options]
  --format, -f          Output format

# Set configuration
invoice-checker config set <key> <value> [options]
  --type, -t            Value type
  --description, -d     Description
  --category, -c        Category

# List configurations
invoice-checker config list [options]
  --category, -c        Filter by category
  --format, -f          Output format

# Reset configuration
invoice-checker config reset [key] [options]
  --force               Skip confirmation
```

### Discovery Commands

```bash
# Review unknown parts
invoice-checker discovery review [options]
  --session-id, -s      Session ID
  --interactive         Enable interactive review
  --output, -o          Output file

# List sessions
invoice-checker discovery sessions [options]
  --limit, -l           Number of sessions
  --detailed, -d        Detailed information

# Discovery statistics
invoice-checker discovery stats [options]
  --session-id, -s      Specific session
  --days, -d            Time period

# Export discoveries
invoice-checker discovery export [options]
  --session-id, -s      Session ID
  --output, -o          Output file
  --include-added       Include added parts
```

### Global Options

All commands support these global options:

```bash
--verbose, -v         Enable verbose logging
--quiet, -q           Suppress non-essential output
--config-file         Custom configuration file
--database            Custom database path
--help                Show help message
--version             Show version information
```

---

## Appendix

### File Formats

#### CSV Import Format for Parts

```csv
part_number,authorized_price,description,category,notes
GP0171NAVY,15.50,Navy Work Pants,Clothing,Standard uniform
GP0171KHAKI,16.00,Khaki Work Pants,Clothing,Standard uniform
TOOL001,25.00,Hammer,Tools,16oz claw hammer
```

#### CSV Import Format for Bulk Updates

```csv
part_number,price,description,category,notes
GP0171NAVY,15.75,Updated Navy Work Pants,Workwear,Price increase
GP0171KHAKI,16.25,Updated Khaki Work Pants,Workwear,Price increase
```

#### CSV Import Format for Bulk Operations

```csv
part_number
GP0171NAVY
GP0171KHAKI
TOOL001
```

### Default Configuration Values

| Setting | Default Value | Description |
|---------|---------------|-------------|
| `validation_mode` | `parts_based` | Default validation mode |
| `interactive_discovery` | `true` | Enable interactive part discovery |
| `discovery_batch_mode` | `false` | Collect unknown parts for batch review |
| `auto_add_discovered_parts` | `false` | Automatically add parts without confirmation |
| `discovery_auto_skip_duplicates` | `true` | Skip parts already discovered in session |
| `discovery_prompt_timeout` | `300` | Timeout for interactive prompts (seconds) |
| `discovery_require_description` | `false` | Require description when adding parts |
| `discovery_default_category` | `discovered` | Default category for new parts |
| `discovery_max_price_variance` | `0.10` | Flag parts with high price variance |
| `discovery_session_cleanup_days` | `7` | Days to keep inactive sessions |
| `price_tolerance` | `0.001` | Price comparison tolerance |
| `log_retention_days` | `365` | Days to keep discovery logs |

---

**End of User Manual**

For additional support or questions, please refer to the troubleshooting section or check the system status using `invoice-checker status`.