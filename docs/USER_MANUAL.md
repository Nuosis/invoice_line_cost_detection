# Invoice Rate Detection System - User Manual

**Version 2.0.0**
**Last Updated:** January 8, 2025

---

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Getting Started](#getting-started)
3. [Processing Invoices](#processing-invoices)
4. [Parts Database Management](#parts-database-management)
5. [Database Operations](#database-operations)
6. [Discovery Management](#discovery-management)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)
9. [Command Reference](#command-reference)

---

## Installation and Setup

### System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Memory**: Minimum 512MB RAM
- **Storage**: 100MB free disk space
- **Permissions**: Read access to invoice files, write access for reports and database
- **Internet Connection**: Required for initial setup (downloads Python dependencies automatically)

### Quick Start Installation (Recommended)

The Clarity Invoice Validator includes bootstrap scripts that automatically handle all installation requirements. This is the easiest way to get started.

#### For Windows Users

1. **Download and extract** the Clarity Invoice Validator application
2. **Double-click** [`Clarity Invoice Validator.bat`](Clarity%20Invoice%20Validator.bat) to launch
3. **Follow the on-screen prompts** - the system will automatically:
   - Check for existing installations
   - Download and install required components
   - Set up the application in the appropriate location
   - Launch the invoice validator

#### For macOS and Linux Users

1. **Download and extract** the Clarity Invoice Validator application
2. **Double-click** [`Clarity Invoice Validator.command`](Clarity%20Invoice%20Validator.command) to launch
   - On macOS, you may need to right-click and select "Open" the first time
   - On Linux, ensure the file has execute permissions: `chmod +x "Clarity Invoice Validator.command"`
3. **Follow the on-screen prompts** - the system will automatically:
   - Check for existing installations
   - Download and install required components
   - Set up the application in the appropriate location
   - Launch the invoice validator

### What the Bootstrap Scripts Do

The bootstrap scripts handle all the technical setup automatically:

- **Dependency Management**: Automatically installs Python, UV package manager, and all required libraries
- **Location Management**: Installs the application in the standard location for your operating system:
  - **Windows**: `%LOCALAPPDATA%\Programs\InvoiceRateDetector`
  - **macOS**: `~/Applications/InvoiceRateDetector`
  - **Linux**: `~/.local/bin/InvoiceRateDetector`
- **Update Handling**: Checks for and downloads the latest launcher scripts
- **Error Recovery**: Provides fallback options if network downloads fail

### Manual Installation (Advanced Users)

If you prefer to install manually or need custom configuration:

#### Prerequisites

1. **Install Python 3.8+** from [python.org](https://python.org)
2. **Install UV Package Manager**:
   ```bash
   pip install uv
   ```

#### Setup Steps

1. **Download and extract the application**
2. **Navigate to the application directory**
3. **Install dependencies**:
   ```bash
   uv sync
   ```
4. **Test installation**:
   ```bash
   uv run invoice-checker --help
   ```

### Initial Configuration

After installation (whether using bootstrap scripts or manual installation), verify the system is working:

```bash
# Check system status and database connectivity
uv run invoice-checker status

# View available commands
uv run invoice-checker --help
```

The system automatically creates a SQLite database (`invoice_detection.db`) on first run.

### Installation Locations

The bootstrap scripts install the application in standard locations:

| Operating System | Installation Path |
|------------------|-------------------|
| **Windows** | `%LOCALAPPDATA%\Programs\InvoiceRateDetector` |
| **macOS** | `~/Applications/InvoiceRateDetector` |
| **Linux** | `~/.local/bin/InvoiceRateDetector` |

### Troubleshooting Installation

If the bootstrap scripts encounter issues:

1. **Check Internet Connection**: The scripts download components from GitHub
2. **Antivirus Software**: Some antivirus programs may block the downloads
3. **Permissions**: Ensure you have write permissions to the installation directory
4. **Manual Download**: If automatic download fails, the scripts provide manual download URLs

For detailed troubleshooting, see the [Troubleshooting](#troubleshooting) section.

---

## Getting Started

### First Time Setup

If you used the bootstrap scripts ([`Clarity Invoice Validator.command`](Clarity%20Invoice%20Validator.command) for macOS/Linux or [`Clarity Invoice Validator.bat`](Clarity%20Invoice%20Validator.bat) for Windows), the system is already set up and ready to use. Simply run the bootstrap script again to launch the application.

### Quick Start Workflow

1. **Launch the application**:
   - **Windows**: Double-click [`Clarity Invoice Validator.bat`](Clarity%20Invoice%20Validator.bat)
   - **macOS/Linux**: Double-click [`Clarity Invoice Validator.command`](Clarity%20Invoice%20Validator.command)
   - **Manual**: Navigate to installation directory and run `uv run invoice-checker`

2. **Check system status** (first time):
   ```bash
   uv run invoice-checker status
   ```

3. **Add some parts to the database**:
   ```bash
   uv run invoice-checker parts add GP0171NAVY 15.50 --description "Navy Work Pants"
   ```

4. **Process invoices**:
   ```bash
   uv run invoice-checker invoice process ./invoices --output report.csv
   ```

5. **Review the generated report** in Excel or a text editor

### Interactive Mode (Recommended for New Users)

The easiest way to get started is with interactive mode. This provides a guided experience:

```bash
uv run invoice-checker
```

The interactive workflow guides you through:
- Selecting invoice files or folders
- Configuring output options
- Processing with automatic parts discovery
- Adding new parts to your database as they're discovered

### Bootstrap Script Features

The bootstrap scripts provide additional convenience:

- **Automatic Updates**: Check for and download the latest version
- **Environment Detection**: Automatically configure for your operating system
- **Error Recovery**: Provide fallback options if issues occur
- **User-Friendly Interface**: Colored output and clear progress indicators
- **Installation Management**: Handle all technical setup automatically

### Next Steps

After your first successful run:

1. **Build your parts database** by processing existing invoices with discovery mode
2. **Configure validation settings** to match your business requirements
3. **Set up regular processing workflows** for ongoing invoice validation
4. **Review the generated reports** to identify pricing anomalies

For detailed instructions on each of these steps, see the relevant sections in this manual.

---

## Processing Invoices

This section covers the core functionality of processing PDF invoices to detect pricing anomalies.

### Basic Invoice Processing

#### Interactive Mode (Recommended for beginners)

Run without arguments for guided processing:

```bash
uv run invoice-checker
```

This launches an interactive workflow that guides you through:
- Selecting invoice files or folders
- Configuring output options
- Processing with automatic parts discovery

#### Command-Line Processing

For direct processing:

```bash
# Process a single PDF file (saves to documents/ directory and auto-opens)
uv run invoice-checker invoice process invoice.pdf

# Process a folder of PDFs (saves to documents/ directory and auto-opens)
uv run invoice-checker invoice process ./invoices

# Process with interactive discovery enabled
uv run invoice-checker invoice process ./invoices --interactive

# Process with different output formats
uv run invoice-checker invoice process ./invoices --format json
uv run invoice-checker invoice process ./invoices --format txt

# Process without auto-opening reports
uv run invoice-checker invoice process ./invoices --no-auto-open

# Process with custom output location (overrides documents/ directory)
uv run invoice-checker invoice process ./invoices --output custom_report.csv
```

#### Batch Processing

Process multiple folders simultaneously:

```bash
# Process multiple folders
uv run invoice-checker invoice batch ./invoice_folders --output-dir ./reports

# Enable parallel processing for faster results
uv run invoice-checker invoice batch ./invoice_folders --parallel --max-workers 4

# Continue processing even if some folders fail
uv run invoice-checker invoice batch ./invoice_folders --continue-on-error
```

### Unknown Parts Discovery

When processing invoices, you may encounter parts not in your database:

#### Collect Unknown Parts

```bash
# Collect unknown parts from a single file
uv run invoice-checker invoice collect-unknowns invoice.pdf --output unknowns.csv

# Collect unknown parts from a folder
uv run invoice-checker invoice collect-unknowns ./invoices --output unknowns.csv

# Include price suggestions
uv run invoice-checker invoice collect-unknowns ./invoices --suggest-prices --output unknowns.csv
```

#### Review Discovered Parts

```bash
# Review unknown parts from recent processing
uv run invoice-checker discovery review

# Review specific discovery session
uv run invoice-checker discovery review --session-id abc123

# Export discovery data
uv run invoice-checker discovery export --output discovery_data.csv
```

### Understanding Reports

The system generates comprehensive reports in CSV or TXT format and automatically saves them to the `documents/` directory for easy access.

#### Report Location and Auto-Opening

**📁 Default Location**: All reports are automatically saved to the `documents/` directory in your current working directory.

**🚀 Auto-Opening**: Reports are automatically opened in your default application:
- **CSV files** open in Excel (or your default spreadsheet application)
- **TXT files** open in Notepad (or your default text editor)
- **JSON files** open in your default JSON viewer

**🔧 Control Options**:
- Use `--no-auto-open` to disable automatic opening
- Use `--output` to specify a custom location (overrides documents/ directory)

#### CSV Report Columns

| Column | Description |
|--------|-------------|
| Invoice # | Invoice number from the PDF |
| Date | Invoice date |
| Line Item | Part number/item code |
| Rate | Price per unit from invoice |
| Qty | Quantity ordered |
| Validation Result | Pass/Fail status |
| Issue Type | Type of validation issue found |
| Description | Item description |
| PDF File | Source PDF filename |

#### Report Analysis

```bash
# View processing results
uv run invoice-checker status

# Review discovery sessions
uv run invoice-checker discovery sessions

# Get discovery statistics
uv run invoice-checker discovery stats --days 7
```

#### Finding Your Reports

Reports are saved with timestamps for easy identification:
- **Location**: `./documents/`
- **Naming**: `{invoice_number}_{report_type}_{timestamp}.{format}`
- **Example**: `INV001_analysis_20250108_143022.csv`

You can always find your reports in the documents directory, even if auto-opening fails.

---

## Parts Database Management

The system uses a SQLite database to store parts information for validation. This section covers managing your parts database.

### Understanding the Parts Database

The system stores parts with the following information:
- **Part Number**: Unique identifier (can be composite key)
- **Authorized Price**: Expected price for validation
- **Description**: Human-readable description
- **Category**: Optional grouping
- **Source**: How the part was added (manual, discovered, imported)
- **Active Status**: Whether the part is currently active

### Adding Parts

#### Manual Addition

```bash
# Add a basic part
uv run invoice-checker parts add GP0171NAVY 15.50

# Add with full details
uv run invoice-checker parts add GP0171NAVY 15.50 \
  --description "Navy Work Pants" \
  --category "Clothing" \
  --notes "Standard work uniform item"
```

#### Bulk Import from CSV

1. **Create a CSV file** with required columns:
   ```csv
   part_number,authorized_price,description,category,notes
   GP0171NAVY,15.50,Navy Work Pants,Clothing,Standard uniform
   GP0171KHAKI,16.00,Khaki Work Pants,Clothing,Standard uniform
   TOOL001,25.00,Hammer,Tools,16oz claw hammer
   ```

2. **Import the CSV**:
   ```bash
   uv run invoice-checker parts import parts.csv
   
   # Update existing parts during import
   uv run invoice-checker parts import parts.csv --update-existing
   
   # Preview import without making changes
   uv run invoice-checker parts import parts.csv --dry-run
   ```

### Viewing and Searching Parts

```bash
# List all active parts
uv run invoice-checker parts list

# List parts in a specific category
uv run invoice-checker parts list --category "Clothing"

# Include inactive parts
uv run invoice-checker parts list --include-inactive

# Get detailed information about a specific part
uv run invoice-checker parts get GP0171NAVY

# Show part history
uv run invoice-checker parts get GP0171NAVY --include-history
```

### Updating Parts

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

# Reactivate a part
uv run invoice-checker parts update GP0171NAVY --activate
```

### Bulk Operations

#### Bulk Updates

```bash
# Update multiple parts from CSV
uv run invoice-checker parts bulk-update price_updates.csv --field price

# Update multiple fields
uv run invoice-checker parts bulk-update updates.csv --field price --field description

# Preview changes before applying
uv run invoice-checker parts bulk-update updates.csv --field price --dry-run
```

#### Bulk Deletion

```bash
# Soft delete multiple parts
uv run invoice-checker parts bulk-delete parts_to_remove.csv

# Permanently delete parts
uv run invoice-checker parts bulk-delete parts_to_remove.csv --hard

# Force deletion without confirmation
uv run invoice-checker parts bulk-delete parts_to_remove.csv --force
```

### Export and Backup

```bash
# Export all active parts to CSV
uv run invoice-checker parts export all_parts.csv

# Export all parts including inactive
uv run invoice-checker parts export all_parts.csv --include-inactive

# Export specific category
uv run invoice-checker parts export clothing_parts.csv --category "Clothing"
```

### Database Statistics

```bash
# Show overall statistics
uv run invoice-checker parts stats

# Show statistics for a specific category
uv run invoice-checker parts stats --category "Clothing"
```

---

## Database Operations

The system provides comprehensive database management capabilities through both interactive menus and command-line interface.

### Interactive Database Management

When you run the application without arguments, you'll see the main menu. Select option 3 to access the database management menu:

```
╔═════════════════════════════════════════════════════════════════════════════════╗
║                                   MAIN MENU                                     ║
╚═════════════════════════════════════════════════════════════════════════════════╝

1) Process Invoices    - Run interactive invoice processing with discovery
2) Manage Parts        - Add, update, import/export parts database
3) Manage Database     - Backup, restore, and maintain database
4) Setup               - Install, update, and configure system
5) Help                - Show help and documentation
6) Exit                - Exit the application
```

The database management menu provides these options:

```
Database Management Options:
1) Create backup
2) Restore from backup
3) Database maintenance
4) Database migration
5) View backup history
6) Reset database
7) Return to main menu
```

#### Interactive Features

- **Guided Workflows**: Step-by-step prompts for each operation
- **Safety Confirmations**: Multiple confirmation steps for destructive operations
- **Automatic Backups**: Pre-operation backups created automatically
- **Progress Indicators**: Real-time feedback during long operations
- **Error Recovery**: Clear guidance when issues occur

### Backup and Restore

#### Creating Backups

**Interactive Mode**: Select "Create backup" from the database management menu for guided backup creation.

**Command Line**:
```bash
# Create a standard backup
uv run invoice-checker database backup

# Create a backup with custom location
uv run invoice-checker database backup ./backups/backup_2025_01_08.db

# Create a compressed backup
uv run invoice-checker database backup --compress

# Include discovery logs in backup
uv run invoice-checker database backup --include-logs
```

#### Viewing Backup History

**Interactive Mode**: Select "View backup history" from the database management menu to see available backups with details.

**Command Line**:
```bash
# View recent backups
uv run invoice-checker database view-backup-history

# View more backups
uv run invoice-checker database view-backup-history --limit 20

# View backups in specific directory
uv run invoice-checker database view-backup-history --backup-dir ./backups
```

The backup history shows:
- File name and creation date
- File size in MB
- Full file path for easy access

#### Restoring from Backup

**Interactive Mode**: Select "Restore from backup" from the database management menu for guided restoration with backup selection.

**Command Line**:
```bash
# Restore from a backup file
uv run invoice-checker database restore backup_2025_01_08.db

# Force restore without confirmation
uv run invoice-checker database restore backup_2025_01_08.db --force

# Skip backup verification
uv run invoice-checker database restore backup_2025_01_08.db --no-verify
```

**⚠️ Important**: Restoring replaces your current database. The system automatically creates a pre-restore backup for safety.

### Database Maintenance

**Interactive Mode**: Select "Database maintenance" from the database management menu for guided maintenance with customizable options.

**Command Line**:
```bash
# Run all maintenance tasks
uv run invoice-checker database maintenance

# Run specific maintenance tasks
uv run invoice-checker database maintenance --vacuum --cleanup-logs

# Verify database integrity
uv run invoice-checker database maintenance --verify-integrity

# Skip automatic backup during maintenance
uv run invoice-checker database maintenance --no-auto-backup
```

Maintenance operations include:
- **Vacuum**: Reclaims unused space and optimizes database structure
- **Log Cleanup**: Removes old discovery log entries based on retention policy
- **Integrity Check**: Verifies database structure and data consistency
- **Statistics**: Shows space savings and maintenance results

### Database Migration

**Interactive Mode**: Select "Database migration" from the database management menu for guided schema updates.

**Command Line**:
```bash
# Check current database version
uv run invoice-checker database migrate --dry-run

# Migrate to latest version
uv run invoice-checker database migrate

# Create backup before migration
uv run invoice-checker database migrate --backup-first
```

### Database Reset

**⚠️ WARNING: Database reset permanently deletes all data!**

**Interactive Mode**: Select "Reset database" from the database management menu for guided reset with multiple safety confirmations.

The interactive reset process:
1. Choose whether to keep configuration settings
2. Review what will be deleted (parts data, discovery logs, optionally configs)
3. Type "RESET" to confirm (case-sensitive)
4. Automatic backup is created before reset

**Command Line**:
```bash
# Reset database (with confirmation)
uv run invoice-checker database reset

# Force reset without confirmation
uv run invoice-checker database reset --force

# Keep configuration settings
uv run invoice-checker database reset --keep-config
```

### Best Practices for Database Management

1. **Regular Backups**: Create backups before major operations or data imports
2. **Use Interactive Mode**: For safety, use the interactive interface for destructive operations
3. **Monitor Database Size**: Use maintenance to track database growth and optimize performance
4. **Test Restores**: Periodically test backup restoration to ensure backups are valid
5. **Keep Multiple Backups**: Maintain several backup versions for different time periods
6. **Review Backup History**: Use the backup history feature to manage and organize backups

### Troubleshooting Database Issues

If you encounter database problems:

1. **Use Interactive Mode**: The guided interface provides step-by-step troubleshooting
2. **Check Integrity**: Run database maintenance with integrity check
3. **View Backup History**: Identify the most recent good backup
4. **Create Safety Backup**: Always backup before attempting repairs
5. **Reset as Last Resort**: Use database reset only if other methods fail

---

## Discovery Management

The system tracks unknown parts discovered during processing for later review.

### Reviewing Discovered Parts

```bash
# Review unknown parts from recent processing
uv run invoice-checker discovery review

# Review specific discovery session
uv run invoice-checker discovery review --session-id abc123

# Interactive review with prompts to add parts
uv run invoice-checker discovery review --interactive

# Export unknown parts to file
uv run invoice-checker discovery review --output unknowns.csv
```

### Discovery Sessions

```bash
# List recent discovery sessions
uv run invoice-checker discovery sessions

# Show detailed session information
uv run invoice-checker discovery sessions --detailed

# Limit number of sessions shown
uv run invoice-checker discovery sessions --limit 10
```

### Discovery Statistics

```bash
# Show overall discovery statistics
uv run invoice-checker discovery stats

# Show statistics for specific time period
uv run invoice-checker discovery stats --days 30

# Show statistics for specific session
uv run invoice-checker discovery stats --session-id abc123
```

### Export Discovery Data

```bash
# Export all discovery data
uv run invoice-checker discovery export --output discovery_data.csv

# Export specific session
uv run invoice-checker discovery export --session-id abc123 --output session_data.csv

# Include parts that were added to database
uv run invoice-checker discovery export --include-added --output complete_data.csv
```

---

## Configuration

The system stores configuration settings in the database for persistence.

### Viewing Configuration

```bash
# List all configuration settings
uv run invoice-checker config list

# List settings in a specific category
uv run invoice-checker config list --category "validation"

# Get specific configuration value
uv run invoice-checker config get validation_mode

# Show configuration in JSON format
uv run invoice-checker config list --format json
```

### Setting Configuration

```bash
# Set a configuration value
uv run invoice-checker config set interactive_discovery true

# Set with specific data type
uv run invoice-checker config set price_tolerance 0.001 --type float

# Set with description and category
uv run invoice-checker config set validation_mode parts_based \
  --description "Default validation mode" \
  --category "validation"
```

### Resetting Configuration

```bash
# Reset specific setting to default
uv run invoice-checker config reset validation_mode

# Reset all settings (with confirmation)
uv run invoice-checker config reset --force
```

### Interactive Setup

```bash
# Run interactive configuration setup
uv run invoice-checker config setup

# Run setup in interactive mode
uv run invoice-checker config setup --interactive
```

### Common Configuration Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `validation_mode` | `parts_based` | Default validation mode |
| `interactive_discovery` | `true` | Enable interactive part discovery |
| `price_tolerance` | `0.001` | Price comparison tolerance |
| `log_retention_days` | `365` | Days to keep discovery logs |

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

#### Issue: Bootstrap Script Won't Run
**Problem**: Double-clicking the bootstrap script doesn't work or shows permission errors.

**Solutions**:

**For macOS Users**:
1. **Right-click and select "Open"** the first time to bypass security restrictions
2. **Check file permissions**:
   ```bash
   chmod +x "Clarity Invoice Validator.command"
   ```
3. **Run from Terminal** if double-clicking fails:
   ```bash
   ./Clarity\ Invoice\ Validator.command
   ```

**For Windows Users**:
1. **Run as Administrator** if you get permission errors
2. **Check antivirus software** - some programs block script execution
3. **Enable script execution** in PowerShell if needed:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

**For Linux Users**:
1. **Make the script executable**:
   ```bash
   chmod +x "Clarity Invoice Validator.command"
   ```
2. **Run from terminal**:
   ```bash
   ./Clarity\ Invoice\ Validator.command
   ```

#### Issue: Download Failures During Bootstrap
**Problem**: Bootstrap script fails to download required components.

**Solutions**:
1. **Check Internet Connection**: Ensure you have a stable internet connection
2. **Check Firewall/Proxy Settings**: Corporate firewalls may block downloads
3. **Manual Download**: Use the URLs provided by the script to download manually
4. **Antivirus Interference**: Temporarily disable antivirus during installation
5. **Use Local Installation**: If you have the full package, place `invoice-launcher.sh` or `invoice-launcher.bat` in the same directory as the bootstrap script

#### Issue: "Command not found" Error
**Problem**: Getting "command not found" when trying to run the application manually.

**Solutions**:
1. **Use Bootstrap Scripts First**: Try the bootstrap scripts before manual installation
2. **Check Python Installation**:
   ```bash
   python3 --version
   # Should show Python 3.8 or higher
   ```

3. **Check UV Installation**:
   ```bash
   uv --version
   # Should show UV version
   ```

4. **Ensure you're in the correct directory**:
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