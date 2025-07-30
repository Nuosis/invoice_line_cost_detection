# Invoice Rate Detection System

A modern, user-friendly CLI tool for detecting overcharges in PDF invoices using advanced parts database validation and generating detailed reports.

## Features

- **Parts Database Integration**: Validate invoice line items against known parts database
- **Interactive Parts Discovery**: Discover and add new parts interactively
- **Batch Processing**: Process entire folders of PDF invoices at once
- **Advanced Validation**: Multiple validation strategies beyond simple threshold checking
- **Multiple Output Formats**: Generate reports in CSV or TXT format
- **Robust PDF Parsing**: Uses pdfplumber for reliable text extraction
- **Database Management**: Built-in SQLite database for parts management
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Quick Start

### 🚀 Automated Setup (Recommended)

The easiest way to get started is using the automated launcher script for your platform:

#### **🐧 Linux / 🍎 macOS**
1. **Download the launcher script**:
   ```bash
   curl -O https://raw.githubusercontent.com/your-repo/invoice_line_cost_detection/main/invoice-launcher.sh
   chmod +x invoice-launcher.sh
   ```

2. **Run the launcher**:
   ```bash
   ./invoice-launcher.sh
   ```

#### **🪟 Windows**
1. **Download the launcher script**:
   ```cmd
   curl -O https://raw.githubusercontent.com/your-repo/invoice_line_cost_detection/main/invoice-launcher.bat
   ```
   *Or download manually from the repository*

2. **Run the launcher**:
   ```cmd
   invoice-launcher.bat
   ```

#### **✨ What the launcher does:**
- ✅ Check system requirements (Python 3.8+, UV, Git)
- ✅ Automatically install missing dependencies (UV on Linux/macOS)
- ✅ Clone and set up the project
- ✅ Configure automatic database backups (Linux/macOS)
- ✅ Provide a user-friendly menu interface

### 📋 Manual Installation

If you prefer manual setup:

#### Prerequisites
- Python 3.8 or higher
- UV (modern Python package installer) - [Install UV](https://docs.astral.sh/uv/getting-started/installation/)
- Git

#### Steps
1. **Download or clone the project**:
   ```bash
   git clone <repository-url>
   cd invoice_line_cost_detection
   ```

2. **Install dependencies using UV**:
   ```bash
   uv sync
   ```

3. **Install the package**:
   ```bash
   uv pip install -e .
   ```

### Basic Usage

#### 🚀 Using the Launcher (Recommended)
```bash
# Run the interactive launcher
./invoice-launcher.sh
```

The launcher provides a user-friendly menu with options for:
- **Process Invoices**: Interactive workflow with automatic discovery
- **Manage Parts**: Add, update, import/export parts with guided prompts
- **Manage Database**: Backup, restore, and maintenance operations
- **Setup**: System installation, updates, and configuration

#### 💻 Direct CLI Commands

#### Check System Status
```bash
uv run invoice-checker status
```

#### Process Invoices
```bash
uv run invoice-checker process --input /path/to/invoices --output report.csv
```

#### Manage Parts Database
```bash
# List all parts
uv run invoice-checker parts list

# Add a new part
uv run invoice-checker parts add --code "GS0448" --description "SHIRT WORK LS BTN COTTON" --rate 0.30

# Interactive parts discovery
uv run invoice-checker discover --input /path/to/invoices
```

### Example Usage

```bash
# Check system status and database connectivity
uv run invoice-checker status

# Process all PDFs in the 'invoices' folder
uv run invoice-checker process --input docs/invoices --output overcharges.csv

# Interactive discovery of new parts from invoices
uv run invoice-checker discover --input ./invoices

# List all parts in database
uv run invoice-checker parts list

# Get help for any command
uv run invoice-checker --help
uv run invoice-checker process --help
```

## Output Format

### CSV Report
The CSV report includes the following columns:
- **Invoice #**: Invoice number
- **Date**: Invoice date
- **Line Item**: Item code/SKU
- **Rate**: Item rate per unit
- **Qty**: Quantity
- **Validation Result**: Pass/Fail status
- **Issue Type**: Type of validation issue found
- **Description**: Item description
- **PDF File**: Source PDF filename

### Text Report
The text report provides:
- Summary statistics (total issues found, validation results)
- Detailed breakdown by invoice
- Parts database status and coverage
- Easy-to-read format for manual review

## Configuration

### Parts Database
The system uses a SQLite database to store known parts and their expected rates:
- **Database Location**: `invoice_data.db` (created automatically)
- **Parts Management**: Add, update, and list parts via CLI commands
- **Validation**: Compare invoice items against database entries

### Supported File Formats
- **Input**: PDF files only
- **Output**: CSV (.csv) or Text (.txt) files
- **Database**: SQLite (.db) files

## Troubleshooting

### Common Issues

#### "No PDF files found"
- Ensure the input path contains PDF files
- Check file permissions
- Verify the path is correct

#### "Could not extract text from PDF"
- PDF may be image-based (scanned) - text extraction not possible
- PDF may be corrupted or password-protected
- Try with a different PDF to test the tool

#### "Database connection failed"
- Check if database file exists and is accessible
- Verify write permissions in the current directory
- Try running `uv run invoice-checker status` to check system health

#### "Module not found" errors
- Install the package: `uv pip install -e .`
- Ensure you're using the correct Python environment
- Try: `uv sync` to install all dependencies from pyproject.toml

### Getting Help

Run with `--help` to see all available options:
```bash
uv run invoice-checker --help
uv run invoice-checker process --help
uv run invoice-checker parts --help
```

Check system status:
```bash
uv run invoice-checker status
```

## Development

### Project Structure
```
invoice_line_cost_detection/
├── invoice-launcher.sh    # 🚀 Automated setup and launcher script (Linux/macOS)
├── invoice-launcher.bat   # 🚀 Automated setup and launcher script (Windows)
├── cli/                   # CLI command modules
│   ├── main.py           # Main CLI entry point
│   ├── commands/         # Individual command implementations
│   └── ...               # CLI utilities and helpers
├── processing/           # PDF processing and validation
│   ├── pdf_processor.py  # PDF text extraction
│   ├── validation_engine.py # Validation logic
│   └── ...               # Processing utilities
├── database/             # Database operations
│   ├── models.py         # Database models
│   └── database.py       # Database connection and operations
├── unit_tests/           # Test suite
├── docs/                 # Documentation and sample files
├── pyproject.toml        # Project configuration
└── README.md            # This file
```

### 🎯 Launcher Script Features

The `invoice-launcher.sh` script provides:

#### **🔧 Automated Setup**
- System requirements checking (Python 3.8+, UV, Git)
- Automatic UV installation if missing
- Repository cloning and dependency installation
- Package installation and configuration

#### **🔄 Smart Updates**
- Automatic version checking against Git repository
- Safe updates with database backup before changes
- Rollback capability if updates fail
- Preserves existing database and configuration

#### **💾 Backup Management**
- Automatic daily database backups (2 AM via cron)
- Manual backup and restore options
- Backup history management (keeps last 30 backups)
- Pre-update safety backups

#### **🎨 User Interface**
- Beautiful ASCII art banner
- Color-coded status messages
- Interactive menu system with 4 main options:
  1. **Process Invoices** - Interactive workflow with discovery
  2. **Manage Parts** - Add, update, import/export parts
  3. **Manage Database** - Backup, restore, maintenance
  4. **Setup** - Install, update, configure system

#### **🔍 Interactive Workflows**
- **Invoice Processing**: Automatic discovery → processing → reporting → backup
- **Parts Management**: List, add, update, import/export with guided prompts
- **Database Operations**: Backup, restore, maintenance with safety checks
- **System Setup**: Complete installation and configuration wizard

### Running Tests

```bash
# Run all tests
uv run python -m pytest unit_tests/

# Run with coverage
uv run python -m pytest unit_tests/ --cov=.

# Run specific test
uv run python -m pytest unit_tests/test_cli.py
```

### Code Quality

The project follows strict coding standards:
- **PEP 8** compliance
- **Type hints** for better code documentation
- **Comprehensive error handling**
- **Modular design** with clear separation of concerns
- **Extensive test coverage** (>80%)

## Architecture

### Core Components

1. **CLI Module**: Command-line interface with multiple subcommands
2. **Processing Module**: PDF text extraction and validation logic
3. **Database Module**: Parts database management and queries
4. **Validation Engine**: Multiple validation strategies and rules

### Design Patterns Used

- **Command Pattern**: CLI command structure
- **Strategy Pattern**: Multiple validation strategies
- **Repository Pattern**: Database access abstraction
- **Factory Pattern**: Validation strategy selection
- **Single Responsibility**: Each module has one clear purpose

## Performance

### Typical Performance
- **Small PDFs** (1-5 pages): ~1-2 seconds per file
- **Large PDFs** (10+ pages): ~3-5 seconds per file
- **Database queries**: Sub-millisecond for parts lookups
- **Batch processing**: Optimized for large invoice sets

### Memory Usage
- **Low memory footprint**: Processes one PDF at a time
- **Efficient database queries**: Uses indexed lookups
- **Resource management**: Properly releases file handles and connections

## Security

### Data Handling
- **Local database**: All data stored locally in SQLite
- **No data transmission**: Tool operates entirely offline
- **File permissions**: Respects system file permissions
- **Input validation**: Validates all user inputs and file paths

### Privacy
- **No telemetry**: Tool doesn't send usage data
- **No network access**: Operates entirely offline
- **Secure defaults**: Uses safe default configurations

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions:

1. **Check the troubleshooting section** above
2. **Run system status check**: `uv run invoice-checker status`
3. **Review the test files** for usage examples
4. **Create an issue** with detailed error information

## Changelog

### Version 2.1.0 (Current)
- 🚀 **Automated launcher script** with beautiful ASCII art interface
- 🔧 **Smart setup and updates** with automatic dependency management
- 💾 **Automatic backup system** with daily cron jobs and retention management
- 🎨 **Interactive menu system** for all major operations
- 🔄 **Safe update mechanism** with database backup before changes
- 📋 **Guided workflows** for invoice processing, parts management, and database operations

### Version 2.0.0
- Modern CLI architecture with subcommands
- Parts database integration with SQLite
- Interactive parts discovery system
- Advanced validation strategies
- Comprehensive error handling and logging
- Modular, maintainable codebase

### Version 1.0.0 (Legacy - Removed)
- ~~Basic threshold-based validation~~ (replaced with parts database)
- ~~Monolithic script architecture~~ (replaced with modular CLI)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd invoice_line_cost_detection

# Install all dependencies (UV automatically manages virtual environments)
uv sync

# Install the package in development mode
uv pip install -e .

# Install development dependencies
uv add --dev pytest pytest-cov pytest-mock black flake8 mypy

# Run tests
uv run python -m pytest unit_tests/

# Check system status
uv run invoice-checker status
```

## Acknowledgments

- **pdfplumber**: Excellent PDF text extraction library
- **SQLite**: Reliable embedded database for parts management
- **Click**: Modern CLI framework for Python
- **Python community**: For excellent documentation and tools