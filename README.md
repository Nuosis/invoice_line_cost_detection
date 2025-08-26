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

### 🚀 One-Click Setup (Recommended)

The easiest way to get started is with the **Clarity Invoice Validator** bootstrap file:

#### **🎯 Super Simple Setup**
1. **Download the bootstrap file for your platform**:
   - **🪟 Windows**: [`Clarity Invoice Validator.bat`](https://raw.githubusercontent.com/your-repo/invoice_line_cost_detection/main/Clarity%20Invoice%20Validator.bat)
   - **🍎 macOS**: [`Clarity Invoice Validator.command`](https://raw.githubusercontent.com/your-repo/invoice_line_cost_detection/main/Clarity%20Invoice%20Validator.command)
   - **🐧 Linux**: [`Clarity Invoice Validator.command`](https://raw.githubusercontent.com/your-repo/invoice_line_cost_detection/main/Clarity%20Invoice%20Validator.command)

2. **Double-click the file** - That's it! 🎉

#### **✨ What happens automatically:**
- 🔍 **Smart Detection**: Checks if the system is already installed
- 📥 **Auto-Download**: Downloads and sets up everything if needed
- 🏠 **Standard Location**: Installs to the recommended system location
- ✅ **Requirements Check**: Verifies Python 3.8+, UV, Git
- 🔧 **Auto-Install**: Installs missing dependencies (UV on Linux/macOS)
- 🗂️ **Project Setup**: Clones and configures the complete system
- 🔄 **Auto-Backup**: Sets up automatic database backups (Linux/macOS)
- 🎛️ **Launch Interface**: Opens the user-friendly menu system

### 🛠️ Advanced Setup (Alternative)

For users who prefer manual control, you can use the launcher scripts directly:

#### **🐧 Linux / 🍎 macOS**
```bash
# Choose installation location (recommended)
mkdir -p ~/Applications && cd ~/Applications  # macOS
# OR
mkdir -p ~/.local/bin && cd ~/.local/bin      # Linux

# Download and run launcher
curl -O https://raw.githubusercontent.com/your-repo/invoice_line_cost_detection/main/invoice-launcher.sh
chmod +x invoice-launcher.sh
./invoice-launcher.sh
```

#### **🪟 Windows**
```cmd
# Choose installation location (recommended)
mkdir "%LOCALAPPDATA%\Programs" && cd /d "%LOCALAPPDATA%\Programs"

# Download and run launcher
curl -O https://raw.githubusercontent.com/your-repo/invoice_line_cost_detection/main/invoice-launcher.bat
invoice-launcher.bat
```

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
   source .venv/bin/activate
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
# Process invoices with parts-based validation (saves to documents/ and auto-opens)
uv run invoice-checker invoice process /path/to/invoices

# Process with interactive discovery
uv run invoice-checker invoice process /path/to/invoices --interactive

# Process without auto-opening reports
uv run invoice-checker invoice process /path/to/invoices --no-auto-open

# Batch processing multiple folders
uv run invoice-checker invoice batch /path/to/invoice_folders --output-dir ./reports
```

#### Manage Parts Database
```bash
# List all parts
uv run invoice-checker parts list

# Add a new part
uv run invoice-checker parts add GP0171NAVY 15.50 --description "Navy Work Pants"

# Import parts from CSV
uv run invoice-checker parts import parts.csv

# Export parts to CSV
uv run invoice-checker parts export all_parts.csv
```

#### Discovery Management
```bash
# Review discovered parts from recent processing
uv run invoice-checker discovery review

# View discovery statistics
uv run invoice-checker discovery stats --days 7

# Export discovery data
uv run invoice-checker discovery export --output discovery_data.csv
```

#### Configuration Management

The system supports flexible configuration of validation, reporting, and workflow options. You can view, set, and reset configuration values directly from the CLI, or use an interactive setup wizard for guided configuration.

```bash
# List all configuration options and their current values
uv run invoice-checker config list

# List configuration options in a specific category (e.g., validation)
uv run invoice-checker config list --category validation

# Show the value of a specific configuration key
uv run invoice-checker config get validation_mode

# Set a configuration value (auto-detects type)
uv run invoice-checker config set validation_mode parts_based

# Set a configuration value with explicit type and description
uv run invoice-checker config set price_tolerance 0.001 --type number --description "Price comparison tolerance"

# Reset a specific configuration to its default value
uv run invoice-checker config reset validation_mode

# Reset all configurations to defaults (with confirmation)
uv run invoice-checker config reset

# Run the interactive setup wizard (recommended for new users)
uv run invoice-checker config setup
```

**Common configuration keys:**
- `validation_mode`: How invoices are validated (`parts_based` or `threshold_based`)
- `default_output_format`: Default report format (`txt`, `csv`, or `json`)
- `interactive_discovery`: Prompt user to add unknown parts interactively
- `price_tolerance`: Tolerance for price comparisons (e.g., `0.001`)

For a full list of available options and their descriptions, use `uv run invoice-checker config list --format table` or `--format json`.

The interactive setup wizard (`uv run invoice-checker config setup`) will guide you through the most important configuration steps.

### Example Usage

```bash
# Check system status and database connectivity
uv run invoice-checker status

# Process all PDFs in the 'invoices' folder (saves to documents/ and auto-opens)
uv run invoice-checker invoice process ./docs/invoices

# Process with interactive parts discovery
uv run invoice-checker invoice process ./invoices --interactive

# Process without auto-opening reports
uv run invoice-checker invoice process ./invoices --no-auto-open

# List all parts in database
uv run invoice-checker parts list

# Review unknown parts from recent processing
uv run invoice-checker discovery review

# Get help for any command
uv run invoice-checker --help
uv run invoice-checker invoice --help
uv run invoice-checker parts --help
```

### 📁 Report Location & Auto-Opening

**New in this version**: Reports are automatically saved to the `documents/` directory and opened in your default application!

- **📍 Location**: All reports are saved to `./documents/` directory
- **🚀 Auto-Open**: Reports automatically open in Excel (CSV), Notepad (TXT), or your default viewer (JSON)
- **🔧 Control**: Use `--no-auto-open` to disable automatic opening
- **📝 Custom Path**: Use `--output` to specify a different location

**Report Files**:
- `{invoice_number}_analysis_{timestamp}.csv` - Main validation report
- `{invoice_number}_report_{timestamp}.txt` - Human-readable summary
- `{invoice_number}_validation_{timestamp}.json` - Complete validation data

**Example**: After processing, you'll see files like:
- `documents/INV001_analysis_20250108_143022.csv` (opens in Excel)
- `documents/INV001_report_20250108_143022.txt` (opens in Notepad)

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
- **Database Location**: `invoice_detection.db` (created automatically)
- **Parts Management**: Add, update, and list parts via CLI commands
- **Validation**: Compare invoice items against database entries

### Supported File Formats
- **Input**: PDF files only
- **Output**: CSV (.csv), JSON (.json), or Text (.txt) files
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

## Deployment

### For Developers: Creating Deployment Packages

The `deploy.sh` script provides several options for managing deployments:

#### **📦 Deployment Script Options**

```bash
# Standard deployment (recommended for development)
./deploy.sh
```
**What it does:**
- Creates a summary of changes since last commit
- Updates CHANGELOG.md with date and version
- Commits changes to git with unique timestamp
- Pushes to origin repository

```bash
# Create deployment package only
./deploy.sh --package-only
```
**What it does:**
- Creates a deployment-ready ZIP package
- Includes static version file (no git dependency)
- Adds deployment marker files
- **Does NOT** commit or push to git
- **Use when:** You want to create a user-ready package without affecting git

```bash
# Deploy AND create package
./deploy.sh --with-package
```
**What it does:**
- Performs standard deployment (commit + push)
- **ALSO** creates deployment package
- **Use when:** You want to both deploy to git AND create user package

```bash
# Preview what would be deployed
./deploy.sh --dry-run
```
**What it does:**
- Shows what changes would be deployed
- Shows version information
- **Does NOT** make any changes
- **Use when:** You want to preview before deploying

#### **🎯 When to Use Each Option**

| Scenario | Command | Purpose |
|----------|---------|---------|
| **Regular development** | `./deploy.sh` | Commit and push changes to git |
| **Create user package** | `./deploy.sh --package-only` | Generate ZIP for end users |
| **Release version** | `./deploy.sh --with-package` | Deploy to git AND create user package |
| **Preview changes** | `./deploy.sh --dry-run` | Check what would be deployed |

#### **📁 Deployment Package Contents**

When using `--package-only` or `--with-package`, the script creates:
- `invoice-rate-detection-{version}.zip` - Complete user package
- `invoice-rate-detection-{version}/` - Extracted package directory

**Package includes:**
- All application files (cli/, database/, processing/)
- Documentation (docs/, README.md, CHANGELOG.md)
- Launcher scripts (*.sh, *.bat, *.command)
- **Static version file** (`.version`) - No git dependency
- **Deployment marker** (`.deployed`) - Indicates deployed mode
- **Deployment info** (`.deployment_info`) - Build metadata

#### **🔄 Version Handling**

The system automatically handles versioning differently for development vs deployment:

**Development Mode** (git repository):
- Version: `1.0.14+dirty` (dynamic, git-based)
- Uses commit count and dirty status
- Requires git to be available

**Deployment Mode** (user package):
- Version: `1.0.14` (static, from `.version` file)
- No git dependency required
- Clean version number for end users

#### **🔗 Integration with Clarity Invoice Validator Bootstrap**

The deployment packages work seamlessly with the Clarity Invoice Validator bootstrap scripts:

**Bootstrap Script Workflow:**
1. **Clarity Invoice Validator.bat/.command** (bootstrap) →
2. **invoice-launcher.sh/.bat** (launcher) →
3. **invoice_line_cost_detection/** (git-based installation)

**How Deployment Packages Fit:**

```bash
# For git-based installations (current system)
./deploy.sh                    # Standard development deployment
./deploy.sh --with-package     # Deploy to git AND create user package

# For direct user distribution (alternative)
./deploy.sh --package-only     # Create standalone package
```

**Two Distribution Methods:**

| Method | Bootstrap Required | Git Required | Updates |
|--------|-------------------|--------------|---------|
| **Git-based** (current) | ✅ Yes | ✅ Yes | Automatic via git |
| **Package-based** (new) | ❌ No | ❌ No | Manual package replacement |

**Git-based Distribution** (recommended):
- Users download `Clarity Invoice Validator.bat/.command`
- Bootstrap script downloads launcher from GitHub
- Launcher clones git repository and manages updates
- **Advantages**: Automatic updates, always latest version
- **Requirements**: Git, internet connection

**Package-based Distribution** (alternative):
- Users download `invoice-rate-detection-{version}.zip`
- Extract and run directly, no git required
- **Advantages**: No git dependency, works offline
- **Disadvantages**: Manual updates required

**Hybrid Approach** (best of both):
- Primary: Git-based with bootstrap scripts (automatic updates)
- Fallback: Package-based for users without git
- Use `./deploy.sh --with-package` to create both

## Development

### Project Structure
```
invoice_line_cost_detection/
├── Clarity Invoice Validator.bat     # 🎯 One-click bootstrap (Windows)
├── Clarity Invoice Validator.command # 🎯 One-click bootstrap (macOS/Linux)
├── invoice-launcher.sh               # 🚀 Advanced launcher script (Linux/macOS)
├── invoice-launcher.bat              # 🚀 Advanced launcher script (Windows)
├── cli/                              # CLI command modules
│   ├── main.py                      # Main CLI entry point
│   ├── commands/                    # Individual command implementations
│   └── ...                          # CLI utilities and helpers
├── processing/                       # PDF processing and validation
│   ├── pdf_processor.py             # PDF text extraction
│   ├── validation_engine.py         # Validation logic
│   └── ...                          # Processing utilities
├── database/                         # Database operations
│   ├── models.py                    # Database models
│   └── database.py                  # Database connection and operations
├── tests_unit/                       # Unit tests
├── tests_e2e/                        # End-to-end tests
├── tests_journey/                    # Journey tests
├── test_validation/                  # Validation tests
├── docs/                            # Documentation and sample files
├── pyproject.toml                   # Project configuration
└── README.md                        # This file
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

### Testing

The project implements a comprehensive 4-layer testing strategy designed to ensure reliability, maintainability, and excellent user experience across all system components.

#### Test Architecture Overview

```
Testing Layers (Run from most fundamental to most complex):
├── Unit Tests (tests_unit/)           # Business logic validation
├── End-to-End Tests (tests_e2e/)      # System integration workflows
├── Journey Tests (tests_journey/)     # CLI user experience flows
└── Validation Tests (test_validation/) # Real-world data validation
```

#### Prerequisites

```bash
# Install test dependencies
uv sync --group dev
```

#### Running Tests

**Quick Start - Run All Tests:**
```bash
# Run complete test suite (recommended order)
PYTHONPATH=. uv run python -m pytest tests_unit/ -v
PYTHONPATH=. uv run python -m pytest tests_e2e/ -v
PYTHONPATH=. uv run python -m pytest tests_journey/ -v
```

**Individual Test Layers:**
```bash
# Unit Tests - Business logic validation (>80% coverage)
PYTHONPATH=. uv run python -m pytest tests_unit/ -v

# End-to-End Tests - Complete system workflows (no mocking)
PYTHONPATH=. uv run python -m pytest tests_e2e/ -v

# Journey Tests - CLI user experience flows (strategic mocking)
PYTHONPATH=. uv run python -m pytest tests_journey/ -v

# Validation Tests - Real invoice processing validation
uv run python test_validation/extract_invoice_text.py --invoicePath docs/invoices/5790265776.pdf
uv run python test_validation/extract_parts.py --invoicePath docs/invoices/5790265776.pdf
```

**Advanced Testing Options:**
```bash
# Run with coverage reporting
PYTHONPATH=. uv run python -m pytest tests_unit/ --cov=. --cov-report=term-missing

# Run specific test file
PYTHONPATH=. uv run python -m pytest tests_unit/test_database.py -v

# Run specific test method
PYTHONPATH=. uv run python -m pytest tests_unit/test_database.py::TestDatabaseManager::test_database_initialization -v

# Stop on first failure
PYTHONPATH=. uv run python -m pytest -x tests_unit/

# Generate HTML coverage report
PYTHONPATH=. uv run python -m pytest tests_unit/ --cov=. --cov-report=html
```

#### Test Layer Details

##### 1. Unit Tests (`tests_unit/`)
**Purpose**: Validate business logic and individual component functionality
- **Coverage**: >80% overall, 99% on critical paths
- **Approach**: Comprehensive unit testing with minimal mocking
- **Focus**: Database operations, CLI commands, PDF processing, validation logic
- **Status**: 282/282 tests passing ✅

**Key Test Files:**
- `test_database.py` - Database operations and models (99% coverage)
- `test_cli.py` - Command-line interface (99% coverage)
- `test_pdf_processing.py` - PDF text extraction (99% coverage)
- `test_validation_helpers.py` - Input validation (100% coverage)
- `test_invoice_processing_refactored.py` - Invoice processing (99% coverage)

##### 2. End-to-End Tests (`tests_e2e/`)
**Purpose**: Validate complete system workflows in real-world conditions
- **Policy**: **NO MOCKING** - uses real databases, files, and system components
- **Focus**: System integration, database setup, cross-platform compatibility
- **Isolation**: Each test creates unique resources and cleans up completely

**Key Test Areas:**
- Initial database setup and schema validation
- Invoice processing workflows with real PDFs
- Parts management and discovery operations
- Error handling and edge cases
- Cross-platform compatibility testing

##### 3. Journey Tests (`tests_journey/`)
**Purpose**: Validate CLI user experience and interaction flows
- **Policy**: **Strategic mocking** - mock only user input, test real system responses
- **Focus**: User interface flows, prompt handling, error recovery
- **Critical**: Prevents UI bugs that other test layers miss

**Key Test Categories:**
- Interactive prompt testing (path input, choice selection)
- Command workflow testing (complete CLI command execution)
- Error recovery testing (invalid input, retry mechanisms)
- Multi-step workflow testing (state preservation, data consistency)

**Important Note**: Exit code 0 with no output indicates tests are hanging and waiting for user input - all user interactions must be automated.

##### 4. Validation Tests (`test_validation/`)
**Purpose**: Validate real-world invoice processing with actual PDF files
- **Approach**: Uses real invoice PDFs from `docs/invoices/`
- **Focus**: Text extraction accuracy, parts detection, validation engine output
- **Tools**: Individual extraction scripts for targeted validation

**Available Validation Scripts:**
```bash
# Extract raw text from PDF
uv run python test_validation/extract_invoice_text.py --invoicePath docs/invoices/5790265776.pdf

# Extract detected parts with item codes
uv run python test_validation/extract_parts.py --invoicePath docs/invoices/5790265776.pdf

# Extract all line items for parsing validation
uv run python test_validation/extract_lines.py --invoicePath docs/invoices/5790265776.pdf

# Generate validation engine output
uv run python test_validation/extract_validation_output.py --invoicePath docs/invoices/5790265776.pdf --format txt

# CLI-based parts database review and regression testing
uv run python test_validation/database_parts_review.py --invoicePath docs/invoices/5790265776.pdf
```

#### Test Execution Guidelines

**Development Workflow:**
1. **Unit Tests First**: Validate business logic changes
2. **E2E Tests**: Verify system integration
3. **Journey Tests**: Ensure UI/UX remains functional
4. **Validation Tests**: Confirm real-world data processing

**Continuous Integration:**
- All test layers must pass before deployment
- Tests run in isolation with proper cleanup
- Cross-platform compatibility verified
- Performance benchmarks maintained

**Debugging Failed Tests:**
```bash
# Run with detailed failure information
PYTHONPATH=. uv run python -m pytest tests_unit/test_database.py --tb=long -v

# Run with debugger on failure
PYTHONPATH=. uv run python -m pytest tests_unit/test_database.py --pdb

# Run journey tests with output capture disabled
PYTHONPATH=. uv run python -m pytest tests_journey/ -v -s
```

#### Coverage and Quality Metrics

**Current Status:**
- **Unit Tests**: 282/282 passing, 66% overall coverage
- **Critical Modules**: >95% coverage on essential business logic
- **Performance**: Full test suite completes in ~8.5 seconds
- **Architecture**: Modern, clean, no legacy dependencies

**Well-Tested Modules (>80% coverage):**
- `cli/validation_helpers.py`: 94%
- `database/database.py`: 83%
- `processing/part_discovery_service.py`: 88%
- `processing/validation_models.py`: 92%

**Areas for Future Improvement (<50% coverage):**
- Interactive CLI features (tested via journey tests)
- Extended validation strategies (less critical paths)
- Utility modules (minimal business impact)

#### Best Practices for Test Development

**Writing New Tests:**
- Use descriptive names: `test_create_part_with_valid_data_success`
- Test both success and failure cases
- Ensure proper resource cleanup
- Keep tests fast (<1 second each)
- Use realistic test data that matches actual system requirements

**Test Data Management:**
- Use programmatic test data generation
- Include edge cases and boundary conditions
- Validate with real invoice PDFs when possible
- Ensure test databases contain complete parts data

**Error Testing:**
- Test all error conditions and exception paths
- Verify proper error messages and logging
- Test recovery from various failure scenarios
- Validate graceful degradation when possible

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