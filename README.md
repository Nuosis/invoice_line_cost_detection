# Invoice Rate Detection System

A simple, user-friendly CLI tool for detecting overcharges in PDF invoices by comparing line item rates to a configurable threshold and generating detailed reports.

## Features

- **Batch Processing**: Process entire folders of PDF invoices at once
- **Configurable Threshold**: Set custom overcharge detection threshold (default: $0.30)
- **Multiple Output Formats**: Generate reports in CSV or TXT format
- **Robust PDF Parsing**: Uses both pdfplumber and pypdf for maximum compatibility
- **Interactive Mode**: User-friendly prompts when run without arguments
- **Comprehensive Logging**: Clear progress updates and error reporting
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Quick Start

### Prerequisites

- Python 3.8 or higher
- UV (modern Python package installer) - [Install UV](https://docs.astral.sh/uv/getting-started/installation/)

### Installation

1. **Download or clone the project**:
   ```bash
   git clone <repository-url>
   cd phil_doublet
   ```

2. **Install dependencies using UV**:
   ```bash
   uv sync
   ```
   
   Or install individually:
   ```bash
   uv add pdfplumber pypdf
   ```

3. **Make the script executable** (optional):
   ```bash
   chmod +x invoice_checker.py
   ```

### Basic Usage

#### Interactive Mode (Recommended for beginners)
Simply run the script without arguments and follow the prompts:

```bash
uv run invoice_checker.py
```

The tool will ask you for:
- Path to folder containing PDF invoices
- Overcharge threshold (default: $0.30)
- Output report file path (default: report.csv)

#### Command Line Mode
For advanced users or automation:

```bash
uv run invoice_checker.py --input /path/to/invoices --threshold 0.30 --output report.csv
```

### Example Usage

```bash
# Process all PDFs in the 'invoices' folder with default threshold
uv run invoice_checker.py --input docs --output overcharges.csv

# Use custom threshold of $0.50
uv run invoice_checker.py --input ./invoices --threshold 0.50 --output report.txt

# Process a single PDF file
uv run invoice_checker.py --input invoice.pdf --output results.csv

# Enable verbose logging
uv run invoice_checker.py --input ./invoices --output report.csv --verbose
```

## Output Format

### CSV Report
The CSV report includes the following columns:
- **Invoice #**: Invoice number
- **Date**: Invoice date
- **Line Item**: Item code/SKU
- **Rate**: Item rate per unit
- **Qty**: Quantity
- **Overcharge**: Calculated overcharge amount
- **Description**: Item description
- **PDF File**: Source PDF filename

### Text Report
The text report provides:
- Summary statistics (total overcharges, total amount)
- Detailed breakdown by invoice
- Easy-to-read format for manual review

## Configuration

### Threshold Settings
The overcharge threshold determines which line items are flagged:
- **Default**: $0.30
- **Range**: Any positive decimal value
- **Examples**: 0.25, 0.50, 1.00

### Supported File Formats
- **Input**: PDF files only
- **Output**: CSV (.csv) or Text (.txt) files

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

#### "Permission denied" errors
- Ensure you have read access to input files
- Ensure you have write access to output directory
- On Unix systems, check file permissions with `ls -la`

#### "Module not found" errors
- Install required dependencies: `uv add pdfplumber PyPDF2`
- Ensure you're using the correct Python environment
- Try: `uv sync` to install all dependencies from pyproject.toml

### Getting Help

Run with `--help` to see all available options:
```bash
uv run invoice_checker.py --help
```

Enable verbose logging for detailed troubleshooting:
```bash
uv run invoice_checker.py --verbose
```

## Development

### Project Structure
```
phil_doublet/
├── invoice_checker.py      # Main application
├── scripts/
│   └── pdf_extractor.py   # PDF extraction utilities
├── tests/
│   ├── __init__.py
│   └── test_invoice_checker.py  # Test suite
├── docs/                   # Documentation and sample files
├── pyproject.toml         # Project configuration
├── requirements.txt       # Dependencies
└── README.md             # This file
```

### Running Tests

```bash
# Run all tests
uv run python -m pytest tests/

# Run with coverage
uv run python -m pytest tests/ --cov=invoice_checker

# Run specific test
uv run python -m pytest tests/test_invoice_checker.py::TestInvoiceParser
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

1. **InvoiceParser**: Handles PDF text extraction and line item parsing
2. **ReportGenerator**: Creates output reports in various formats
3. **InvoiceChecker**: Main orchestrator class
4. **CLI Interface**: Command-line argument parsing and user interaction

### Design Patterns Used

- **Strategy Pattern**: Multiple PDF extraction methods
- **Factory Pattern**: Report generation based on file type
- **Command Pattern**: CLI command processing
- **Single Responsibility**: Each class has one clear purpose

## Performance

### Typical Performance
- **Small PDFs** (1-5 pages): ~1-2 seconds per file
- **Large PDFs** (10+ pages): ~3-5 seconds per file
- **Batch processing**: Processes files sequentially for reliability

### Memory Usage
- **Low memory footprint**: Processes one PDF at a time
- **Efficient text extraction**: Uses streaming where possible
- **Garbage collection**: Properly releases resources

## Security

### Data Handling
- **No data retention**: Tool doesn't store or transmit data
- **Local processing**: All operations performed locally
- **File permissions**: Respects system file permissions
- **Input validation**: Validates all user inputs

### Privacy
- **No telemetry**: Tool doesn't send usage data
- **No network access**: Operates entirely offline
- **Secure defaults**: Uses safe default configurations

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions:

1. **Check the troubleshooting section** above
2. **Review the test files** for usage examples
3. **Run with verbose logging** to diagnose issues
4. **Create an issue** with detailed error information

## Changelog

### Version 1.0.0
- Initial release
- Basic PDF text extraction
- Line item parsing with regex patterns
- CSV and TXT report generation
- Interactive and CLI modes
- Comprehensive test suite
- Cross-platform compatibility

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
cd phil_doublet

# Install all dependencies (UV automatically manages virtual environments)
uv sync

# Install development dependencies
uv add --dev pytest pytest-cov pytest-mock black flake8 mypy

# Run tests
uv run python -m pytest tests/
```

## Acknowledgments

- **pdfplumber**: Excellent PDF text extraction library
- **PyPDF2**: Reliable PDF processing fallback
- **Python community**: For excellent documentation and tools