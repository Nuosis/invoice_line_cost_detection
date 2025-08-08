# Example of how to run

## Invoice Text
uv run '/Users/marc
usswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/test_validation/extract_
invoice_text.py' --invoicePath '/Users/marcusswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/docs/invoices/5790265776.pdf'

## Parts
uv run '/Users/marc
usswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/test_validation/extract_
parts.py' --invoicePath '/Users/marcusswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/docs/invoices/5790265776.pdf'

## Lines (All Line Items)
uv run '/Users/marc
usswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/test_validation/extract_
lines.py' --invoicePath '/Users/marcusswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/docs/invoices/5790265776.pdf'

## Validate Output
uv run '/Users/marc
usswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/test_validation/extract_
validation_output.py' --invoicePath '/Users/marcusswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/docs/invoices/5790265776.pdf --format txt'

# Suites
the extract suite consist of
`/Users/marcusswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/test_validation/extract_invoice_text.py`
`/Users/marcusswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/test_validation/extract_validation_output.py`
`/Users/marcusswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/test_validation/extract_parts.py`
`/Users/marcusswift/Documents/fileMakerDevelopment/Phil Doublet/invoice_line_cost_detection/test_validation/extract_lines.py`

All require --invoicePath (full path) and extract_validation_output accepts --format of (csv, txt)

## Script Purposes:
- **extract_invoice_text.py**: Extracts raw text from PDF for text validation
- **extract_parts.py**: Extracts only valid parts (with item codes) for parts database validation
- **extract_lines.py**: Extracts ALL detected line items for line parsing validation
- **extract_validation_output.py**: Extracts validation engine output for validation logic testing

---

## database_parts_review.py: CLI-based Parts Database Review

This script exercises the *real* CLI for parts management, simulating add/update/pass logic and exporting the database state for regression testing.

### Basic Usage

```sh
uv run python test_validation/database_parts_review.py --invoicePath docs/invoices/5790265776.pdf
```

- Extracts text, lines, and parts from the given invoice PDF.
- Adds or updates discovered parts using the CLI (`parts add`/`parts update`).
- Exports the current parts database to `test_validation/expectations/5790265785_parts_db.csv`.

### Custom Database Path

```sh
uv run python test_validation/database_parts_review.py --invoicePath docs/invoices/5790265785.pdf --dbPath test_validation/my_test.db
```

- Uses a custom SQLite database file for isolation.

### Custom Output Directory

```sh
python test_validation/database_parts_review.py --invoicePath docs/invoices/5790265785.pdf --outputDir test_validation/expectations/
```

- Stores all output and exported database files in the specified directory.

### Export as JSON

```sh
python test_validation/database_parts_review.py --invoicePath docs/invoices/5790265785.pdf --exportFormat json
```

### Full example
```sh
uv run python test_validation/database_parts_review.py --invoicePath docs/invoices/5790265785.pdf --dbPath test_validation/my_test.db --outputDir test_validation/expectations/ --exportFormat json
```

- Exports the parts database as JSON instead of CSV.

### What does this test?

- The script **calls the actual CLI** for all parts management operations.
- It is suitable for verifying CLI-based add/update/pass logic and for regression testing the CLI interface and its integration with the database.
- All actions are performed through the CLI, providing true end-to-end coverage of the CLI functions.
