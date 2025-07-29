#!/usr/bin/env python3
"""
Invoice Rate Detection System
A simple CLI tool to detect overcharges in PDF invoices by comparing line item rates
to a configurable threshold and generating a report.

Usage:
    python invoice_checker.py --input /path/to/invoices --threshold 0.30 --output report.csv
    python invoice_checker.py  # Interactive mode with prompts
"""

import argparse
import csv
import logging
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import pdfplumber
import pypdf


@dataclass
class LineItem:
    """Represents a line item found in an invoice."""
    invoice_number: str
    invoice_date: str
    item_code: str
    description: str
    rate: float
    quantity: int
    overcharge_amount: float
    pdf_filename: str


@dataclass
class ProcessingResult:
    """Results from processing a single PDF."""
    filename: str
    success: bool
    error_message: Optional[str] = None
    line_items: List[LineItem] = None
    
    def __post_init__(self):
        if self.line_items is None:
            self.line_items = []


class InvoiceParser:
    """Handles parsing of invoice text to extract line items and rates."""
    
    def __init__(self, threshold: float = 0.30):
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)
        
        # Regex patterns for extracting invoice data
        self.patterns = {
            'invoice_number': [
                r'INVOICE\s+NUMBER\s+(\d+)',
                r'Invoice\s*#?\s*:?\s*(\d+)',
                r'Invoice\s*Number\s*:?\s*(\d+)',
                r'INV\s*#?\s*:?\s*(\d+)',
                r'#\s*(\d{8,})',  # Long number sequences
            ],
            'invoice_date': [
                r'INVOICE\s+DATE\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'Date\s*:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'Invoice\s*Date\s*:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            # Pattern for line items matching the actual invoice format:
            # WEARER# WEARER NAME ITEM ITEM DESCRIPTION SIZE TYPE BILL QTY RATE TOTAL
            'line_item': [
                # Match the actual format: wearer# wearer_name item_code description size type bill_type qty rate total
                r'\d+\s+.+?\s+([A-Z]{2}\d{4}[A-Z]*)\s+(.+?)\s+[A-Z0-9]+\s+[A-Z]+\s+(\d+\.\d{3})\s+(\d+)\s+\d+\.\d{2}',
                # Fallback patterns for other formats
                r'([A-Z]{2}\d{4}[A-Z]*)\s+(.+?)\s+(\d+\.\d{3})\s+(\d+)',
                r'([A-Z]+\d+[A-Z]*)\s+(.+?)\s+(\d+\.\d{2,3})\s+(\d+)',
            ]
        }
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """Extract text from PDF using pdfplumber with PyPDF2 fallback."""
        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                if text.strip():
                    return text
            
            # Fallback to pypdf
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                return text if text.strip() else None
                
        except Exception as e:
            self.logger.error(f"Error extracting text from {pdf_path}: {e}")
            return None
    
    def extract_invoice_number(self, text: str) -> str:
        """Extract invoice number from text."""
        for pattern in self.patterns['invoice_number']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return "Unknown"
    
    def extract_invoice_date(self, text: str) -> str:
        """Extract invoice date from text."""
        for pattern in self.patterns['invoice_date']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Normalize date format
                try:
                    # Try different date formats
                    for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            return parsed_date.strftime('%m/%d/%Y')
                        except ValueError:
                            continue
                    return date_str  # Return as-is if parsing fails
                except:
                    return date_str
        return "Unknown"
    
    def extract_line_items(self, text: str, invoice_number: str, invoice_date: str, pdf_filename: str) -> List[LineItem]:
        """Extract line items from invoice text."""
        line_items = []
        seen_items = set()  # Track seen items to avoid duplicates
        
        for pattern in self.patterns['line_item']:
            matches = re.findall(pattern, text, re.MULTILINE)
            
            for match in matches:
                try:
                    item_code = match[0].strip()
                    description = match[1].strip()
                    rate = float(match[2])
                    quantity = int(match[3])
                    
                    # Create a unique key for this item to avoid duplicates
                    item_key = (item_code, description, rate, quantity)
                    if item_key in seen_items:
                        continue
                    seen_items.add(item_key)
                    
                    # Validate item code (should be reasonable length and format)
                    if len(item_code) < 2 or len(item_code) > 20:
                        continue
                    
                    # Check if rate exceeds threshold
                    if rate > self.threshold:
                        overcharge = (rate - self.threshold) * quantity
                        
                        line_item = LineItem(
                            invoice_number=invoice_number,
                            invoice_date=invoice_date,
                            item_code=item_code,
                            description=description,
                            rate=rate,
                            quantity=quantity,
                            overcharge_amount=overcharge,
                            pdf_filename=pdf_filename
                        )
                        line_items.append(line_item)
                        
                except (ValueError, IndexError) as e:
                    self.logger.debug(f"Error parsing line item {match}: {e}")
                    continue
        
        return line_items
    
    def parse_invoice(self, pdf_path: Path) -> ProcessingResult:
        """Parse a single invoice PDF and return processing results."""
        filename = pdf_path.name
        
        try:
            # Extract text from PDF
            text = self.extract_text_from_pdf(pdf_path)
            if not text:
                return ProcessingResult(
                    filename=filename,
                    success=False,
                    error_message="Could not extract text from PDF"
                )
            
            # Extract invoice metadata
            invoice_number = self.extract_invoice_number(text)
            invoice_date = self.extract_invoice_date(text)
            
            # Extract line items that exceed threshold
            line_items = self.extract_line_items(text, invoice_number, invoice_date, filename)
            
            return ProcessingResult(
                filename=filename,
                success=True,
                line_items=line_items
            )
            
        except Exception as e:
            return ProcessingResult(
                filename=filename,
                success=False,
                error_message=str(e)
            )


class ReportGenerator:
    """Handles generation of output reports."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_csv_report(self, line_items: List[LineItem], output_path: Path) -> bool:
        """Generate CSV report of overcharge line items."""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Invoice #', 'Date', 'Line Item', 'Rate', 'Qty', 
                    'Overcharge', 'Description', 'PDF File'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for item in line_items:
                    writer.writerow({
                        'Invoice #': item.invoice_number,
                        'Date': item.invoice_date,
                        'Line Item': item.item_code,
                        'Rate': f"${item.rate:.3f}",
                        'Qty': item.quantity,
                        'Overcharge': f"${item.overcharge_amount:.2f}",
                        'Description': item.description,
                        'PDF File': item.pdf_filename
                    })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating CSV report: {e}")
            return False
    
    def generate_text_report(self, line_items: List[LineItem], output_path: Path) -> bool:
        """Generate text report of overcharge line items grouped by invoice."""
        try:
            with open(output_path, 'w', encoding='utf-8') as txtfile:
                txtfile.write("Invoice Rate Detection Report\n")
                txtfile.write("=" * 50 + "\n\n")
                
                if not line_items:
                    txtfile.write("No overcharges found.\n")
                    return True
                
                # Group items by invoice number and file
                from collections import defaultdict
                grouped_items = defaultdict(list)
                for item in line_items:
                    key = (item.invoice_number, item.invoice_date, item.pdf_filename)
                    grouped_items[key].append(item)
                
                # Process each invoice group
                for (invoice_number, invoice_date, pdf_filename), items in grouped_items.items():
                    invoice_total = sum(item.overcharge_amount for item in items)
                    
                    txtfile.write(f"Invoice: {invoice_number} ({invoice_date})\n")
                    txtfile.write(f"File: {pdf_filename}\n")
                    txtfile.write(f"Total Overcharges Found: {len(items)}\n")
                    txtfile.write(f"Total Overcharge Amount: ${invoice_total:.2f}\n\n")
                    
                    for item in items:
                        txtfile.write(f"Item: {item.item_code} - {item.description}\n")
                        txtfile.write(f"  Rate: ${item.rate:.3f} x {item.quantity} = Overcharge: ${item.overcharge_amount:.2f}\n\n")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating text report: {e}")
            return False


class InvoiceChecker:
    """Main application class for invoice rate detection."""
    
    def __init__(self, threshold: float = 0.30):
        self.threshold = threshold
        self.parser = InvoiceParser(threshold)
        self.report_generator = ReportGenerator()
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)
    
    def get_pdf_files(self, input_path: Path) -> List[Path]:
        """Get all PDF files from the input directory."""
        if not input_path.exists():
            raise FileNotFoundError(f"Input path does not exist: {input_path}")
        
        if input_path.is_file():
            if input_path.suffix.lower() == '.pdf':
                return [input_path]
            else:
                raise ValueError(f"File is not a PDF: {input_path}")
        
        pdf_files = list(input_path.glob("*.pdf"))
        if not pdf_files:
            raise ValueError(f"No PDF files found in directory: {input_path}")
        
        return sorted(pdf_files)
    
    def process_invoices(self, input_path: Path) -> Tuple[List[LineItem], List[ProcessingResult]]:
        """Process all PDF invoices in the input path."""
        pdf_files = self.get_pdf_files(input_path)
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        all_line_items = []
        processing_results = []
        
        for pdf_file in pdf_files:
            self.logger.info(f"Processing: {pdf_file.name}")
            
            result = self.parser.parse_invoice(pdf_file)
            processing_results.append(result)
            
            if result.success:
                all_line_items.extend(result.line_items)
                if result.line_items:
                    self.logger.info(f"  Found {len(result.line_items)} overcharge(s)")
                else:
                    self.logger.info("  No overcharges found")
            else:
                self.logger.error(f"  Error: {result.error_message}")
        
        return all_line_items, processing_results
    
    def generate_report(self, line_items: List[LineItem], output_path: Path) -> bool:
        """Generate the output report."""
        if output_path.suffix.lower() == '.csv':
            return self.report_generator.generate_csv_report(line_items, output_path)
        else:
            return self.report_generator.generate_text_report(line_items, output_path)
    
    def run(self, input_path: Path, output_path: Path) -> bool:
        """Run the complete invoice checking process."""
        try:
            self.logger.info("Starting invoice rate detection...")
            self.logger.info(f"Threshold: ${self.threshold:.2f}")
            self.logger.info(f"Input: {input_path}")
            self.logger.info(f"Output: {output_path}")
            
            # Process all invoices
            line_items, results = self.process_invoices(input_path)
            
            # Generate summary
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful
            total_overcharge = sum(item.overcharge_amount for item in line_items)
            
            self.logger.info(f"\nProcessing Summary:")
            self.logger.info(f"  Files processed: {len(results)}")
            self.logger.info(f"  Successful: {successful}")
            self.logger.info(f"  Failed: {failed}")
            self.logger.info(f"  Overcharges found: {len(line_items)}")
            self.logger.info(f"  Total overcharge amount: ${total_overcharge:.2f}")
            
            # Generate report
            if self.generate_report(line_items, output_path):
                self.logger.info(f"\nReport generated: {output_path}")
                return True
            else:
                self.logger.error("Failed to generate report")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during processing: {e}")
            return False


def get_user_input() -> Tuple[Path, float, Path]:
    """Get input parameters from user interactively."""
    print("Invoice Rate Detection System")
    print("=" * 40)
    
    # Get input folder
    while True:
        input_str = input("Enter path to folder containing PDF invoices: ").strip()
        if not input_str:
            print("Please enter a valid path.")
            continue
        
        # Remove surrounding quotes if present
        input_str = input_str.strip('\'"')
        
        input_path = Path(input_str)
        if not input_path.exists():
            print(f"Path does not exist: {input_path}")
            continue
        
        try:
            # Test if we can find PDF files
            if input_path.is_file():
                if input_path.suffix.lower() != '.pdf':
                    print("File must be a PDF.")
                    continue
            else:
                pdf_files = list(input_path.glob("*.pdf"))
                if not pdf_files:
                    print(f"No PDF files found in: {input_path}")
                    continue
            break
        except Exception as e:
            print(f"Error accessing path: {e}")
            continue
    
    # Get threshold
    while True:
        threshold_str = input("Enter overcharge threshold (default $0.30): ").strip()
        if not threshold_str:
            threshold = 0.30
            break
        
        try:
            threshold = float(threshold_str.replace('$', ''))
            if threshold < 0:
                print("Threshold must be positive.")
                continue
            break
        except ValueError:
            print("Please enter a valid number.")
            continue
    
    # Get output file
    while True:
        output_str = input("Enter output file path (default: report.csv): ").strip()
        if not output_str:
            output_path = Path("report.csv")
            break
        
        output_path = Path(output_str)
        
        # Add extension if missing
        if not output_path.suffix:
            output_path = output_path.with_suffix('.csv')
        
        # Validate extension
        if output_path.suffix.lower() not in ['.csv', '.txt']:
            print("Output file must be .csv or .txt")
            continue
        
        break
    
    return input_path, threshold, output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Invoice Rate Detection System - Detect overcharges in PDF invoices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input /path/to/invoices --threshold 0.30 --output report.csv
  %(prog)s  # Interactive mode with prompts
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=Path,
        help='Path to folder containing PDF invoices or single PDF file'
    )
    
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=0.30,
        help='Overcharge threshold in dollars (default: 0.30)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output report file path (.csv or .txt, default: report.csv)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Get parameters from command line or user input
        if args.input and args.output:
            input_path = args.input
            threshold = args.threshold
            output_path = args.output
        else:
            input_path, threshold, output_path = get_user_input()
        
        # Validate threshold
        if threshold < 0:
            print("Error: Threshold must be positive")
            sys.exit(1)
        
        # Add default extension to output if missing
        if not output_path.suffix:
            output_path = output_path.with_suffix('.csv')
        
        # Create invoice checker and run
        checker = InvoiceChecker(threshold)
        success = checker.run(input_path, output_path)
        
        if success:
            print(f"\nSuccess! Report saved to: {output_path}")
            sys.exit(0)
        else:
            print("\nProcessing failed. Check the log messages above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()