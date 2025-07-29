# Invoice Rate Detection System - Development Guide

## Solution Overview

- **User**: Single, non-technical user (business owner) on a desktop (Windows/Mac/Linux).
- **Interface**: Simple command-line (CLI) tool, run by double-clicking or from terminal.
- **Workflow**: User selects a folder of PDF invoices, runs the tool, and receives a clear, easy-to-read report of all overcharges by invoice/date/amount.
- **Configuration**: The overcharge threshold (default $0.30) is user-configurable (via prompt or config file).
- **No post-processing**: The report is for manual use; no integration with accounting/email/etc.
- **No security or multi-user concerns.**

---

## Minimal User Flow

```mermaid
flowchart TD
    A[User downloads/extracts app] --> B[User double-clicks or runs CLI tool]
    B --> C[Tool prompts for folder of PDFs]
    C --> D[User selects folder]
    D --> E[Tool processes all PDFs in folder]
    E --> F[Tool outputs a single report file (CSV or TXT)]
    F --> G[User opens report in Excel or Notepad]
```

---

## CLI Example

```sh
python invoice_checker.py --input /path/to/invoices --threshold 0.30 --output report.csv
```
- If run without arguments, prompt user for folder and threshold.

---

## Report Example

| Invoice #   | Date       | Line Item | Rate | Qty | Overcharge | Description                |
|-------------|------------|-----------|------|-----|------------|----------------------------|
| 5790256943  | 06/09/2025 | GS0448    | 0.345| 8   | $0.36      | SHIRT WORK LS BTN COTTON   |
| ...         | ...        | ...       | ...  | ... | ...        | ...                        |

---

## Key Features

- **Batch Processing**: Accepts a folder of PDFs, processes all at once.
- **Configurable Threshold**: User can set/change the overcharge threshold.
- **Simple Output**: One CSV or TXT report, easy to open in Excel/Notepad.
- **No Duplicates**: Each invoice is listed by number/date; user can re-run as needed.
- **No GUI, No Web, No Docker required**: Just Python and dependencies.

---

## Implementation Steps

1. **PDF Text Extraction**: Use a library like `pdfplumber` or `PyPDF2`.
2. **Line Item Parsing**: Regex or simple pattern matching to extract line items and rates.
3. **Threshold Comparison**: Flag any line item with rate > threshold.
4. **Report Generation**: Write flagged items to a CSV or TXT file.
5. **User Prompts**: If no arguments, prompt for folder and threshold.
6. **Error Handling**: Print clear errors for unreadable PDFs, missing data, etc.

---

## Deployment

- User downloads a ZIP or folder with the script and a README.
- User double-clicks or runs the script, follows prompts, and gets a report.
- No installation or admin rights required (except Python and dependencies).

---

## Notes

- **Cost, ease of use, and clarity are prioritized.**
- **No unnecessary complexity.**
- **No post-processing or automation beyond the report.**