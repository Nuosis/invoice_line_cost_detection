"""
Simple report generator that accepts validation JSON and produces three outputs:
1. JSON - returns the input object unchanged
2. TXT - human-readable summary for manual review
3. CSV - meaningful representation for Excel analysis

Reports are automatically saved to the documents/ directory and opened in the default application.
"""

import json
import csv
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from .report_utils import (
    get_documents_directory,
    get_default_report_path,
    auto_open_reports,
    get_report_summary_message
)


class SimpleReportGenerator:
    """Simple report generator for validation JSON objects."""
    
    def generate_reports(self, validation_data: Dict[str, Any], output_base_path: str = None,
                        auto_open: bool = True, preferred_format: str = "csv",
                        generate_all_formats: bool = True) -> Dict[str, str]:
        """
        Generate report formats from validation JSON.
        
        Args:
            validation_data: The validation JSON object
            output_base_path: Base path for output files (optional, defaults to documents/ directory)
            auto_open: Whether to automatically open the generated reports (default: True)
            preferred_format: Preferred format for auto-opening (default: "csv")
            generate_all_formats: Whether to generate all formats or just the preferred one (default: True)
            
        Returns:
            Dict with format keys containing the generated content
        """
        reports = {}
        
        # Generate requested formats
        if generate_all_formats:
            reports = {
                'json': self.generate_json_report(validation_data),
                'txt': self.generate_txt_report(validation_data),
                'csv': self.generate_csv_report(validation_data)
            }
        else:
            # Generate only the preferred format
            if preferred_format == 'json':
                reports['json'] = self.generate_json_report(validation_data)
            elif preferred_format == 'txt':
                reports['txt'] = self.generate_txt_report(validation_data)
            else:  # default to csv
                reports['csv'] = self.generate_csv_report(validation_data)
        
        # CRITICAL: Do NOT fallback to documents directory - use the provided path
        if output_base_path is None:
            raise ValueError("output_base_path must be provided - no default fallback allowed")
        
        report_files = self._write_reports_to_files(reports, output_base_path, validation_data, preferred_format)
        
        # Auto-open only the preferred format if requested
        if auto_open and report_files:
            auto_open_reports(report_files, primary_format=preferred_format)
        
        return reports
    
    def generate_json_report(self, validation_data: Dict[str, Any]) -> str:
        """Return the validation JSON object unchanged."""
        return json.dumps(validation_data, indent=2, ensure_ascii=False)
    
    def generate_txt_report(self, validation_data: Dict[str, Any]) -> str:
        """Generate human-readable text summary."""
        lines = []
        
        # Header
        invoice_num = validation_data.get('invoice_metadata', {}).get('invoice_number', 'Unknown')
        invoice_date = validation_data.get('invoice_metadata', {}).get('invoice_date', 'Unknown')
        
        lines.extend([
            "INVOICE VALIDATION REPORT",
            "=" * 50,
            f"Invoice: {invoice_num}",
            f"Date: {invoice_date}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ])
        
        # Invoice totals validation
        lines.extend(self._generate_format_section(validation_data))
        
        # Line items with errors
        lines.extend(self._generate_error_lines_section(validation_data))
        
        # Summary
        lines.extend(self._generate_summary_section(validation_data))
        
        return "\n".join(lines)
    
    def generate_csv_report(self, validation_data: Dict[str, Any]) -> str:
        """Generate CSV representation of validation data with enhanced error reporting."""
        output = io.StringIO()
        
        # Add UTF-8 BOM for Excel compatibility
        output.write('\ufeff')
        
        fieldnames = [
            'Invoice Number', 'Invoice Date', 'Line Number', 'Part Number',
            'Description', 'Item Type', 'Quantity', 'Actual Rate', 'Actual Total',
            'Expected Rate', 'Expected Total', 'Delta', 'Status', 'Raw Text'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Check if this is batch processing (has 'invoices' array)
        if 'invoices' in validation_data:
            return self._generate_batch_csv(validation_data, writer, output)
        else:
            return self._generate_single_csv(validation_data, writer, output)
    
    def _generate_single_csv(self, validation_data: Dict[str, Any], writer, output) -> str:
        """Generate CSV for single invoice."""
        invoice_metadata = validation_data.get('invoice_metadata', {})
        invoice_num = invoice_metadata.get('invoice_number', '')
        invoice_date = invoice_metadata.get('invoice_date', '')
        
        # Create a lookup for error lines by line number
        error_lines = validation_data.get('error_lines', [])
        error_lookup = {error.get('line_number'): error for error in error_lines}
        
        # Process all parts and merge with error data
        parts = validation_data.get('parts', [])
        actual_grand_total = 0.0
        expected_grand_total = 0.0
        total_delta = 0.0
        
        for part in parts:
            line_number = part.get('lineitem_fields', {}).get('line_number')
            error_data = error_lookup.get(line_number)
            
            if error_data:
                # This line has validation errors
                row = self._create_enhanced_csv_row(part, error_data, invoice_num, invoice_date, 'ERROR')
                actual_grand_total += error_data.get('actual_total', 0)
                expected_grand_total += error_data.get('expected_total', 0)
                total_delta += (error_data.get('expected_total', 0) - error_data.get('actual_total', 0))
            else:
                # This line passed validation
                row = self._create_enhanced_csv_row(part, None, invoice_num, invoice_date, 'VALID')
                # For valid lines, actual = expected
                line_total = part.get('lineitem_fields', {}).get('total', 0)
                actual_grand_total += line_total
                expected_grand_total += line_total
            
            writer.writerow(row)
        
        # Add invoice summary row
        summary_row = {
            'Invoice Number': invoice_num,
            'Invoice Date': invoice_date,
            'Line Number': 'SUMMARY',
            'Part Number': '',
            'Description': 'Invoice Totals',
            'Item Type': '',
            'Quantity': '',
            'Actual Rate': '',
            'Actual Total': f"${actual_grand_total:.2f}",
            'Expected Rate': '',
            'Expected Total': f"${expected_grand_total:.2f}",
            'Delta': f"${total_delta:.2f}",
            'Status': 'SUMMARY',
            'Raw Text': f"Total Delta: ${total_delta:.2f}"
        }
        writer.writerow(summary_row)
        
        return output.getvalue()
    
    def _generate_batch_csv(self, validation_data: Dict[str, Any], writer, output) -> str:
        """Generate CSV for batch processing with individual invoice sections."""
        invoices = validation_data.get('invoices', [])
        batch_actual_total = 0.0
        batch_expected_total = 0.0
        batch_delta = 0.0
        
        for invoice_data in invoices:
            invoice_metadata = invoice_data.get('invoice_metadata', {})
            invoice_num = invoice_metadata.get('invoice_number', '')
            invoice_date = invoice_metadata.get('invoice_date', '')
            
            # Create a lookup for error lines by line number for this invoice
            error_lines = invoice_data.get('error_lines', [])
            error_lookup = {error.get('line_number'): error for error in error_lines}
            
            # Process all parts for this invoice
            parts = invoice_data.get('parts', [])
            invoice_actual_total = 0.0
            invoice_expected_total = 0.0
            invoice_delta = 0.0
            
            for part in parts:
                line_number = part.get('lineitem_fields', {}).get('line_number')
                error_data = error_lookup.get(line_number)
                
                if error_data:
                    # This line has validation errors
                    row = self._create_enhanced_csv_row(part, error_data, invoice_num, invoice_date, 'ERROR')
                    invoice_actual_total += error_data.get('actual_total', 0)
                    invoice_expected_total += error_data.get('expected_total', 0)
                    invoice_delta += (error_data.get('expected_total', 0) - error_data.get('actual_total', 0))
                else:
                    # This line passed validation
                    row = self._create_enhanced_csv_row(part, None, invoice_num, invoice_date, 'VALID')
                    # For valid lines, actual = expected
                    line_total = part.get('lineitem_fields', {}).get('total', 0)
                    invoice_actual_total += line_total
                    invoice_expected_total += line_total
                
                writer.writerow(row)
            
            # Add invoice sub-summary row
            sub_summary_row = {
                'Invoice Number': invoice_num,
                'Invoice Date': invoice_date,
                'Line Number': 'SUB-TOTAL',
                'Part Number': '',
                'Description': f'Invoice {invoice_num} Totals',
                'Item Type': '',
                'Quantity': '',
                'Actual Rate': '',
                'Actual Total': f"${invoice_actual_total:.2f}",
                'Expected Rate': '',
                'Expected Total': f"${invoice_expected_total:.2f}",
                'Delta': f"${invoice_delta:.2f}",
                'Status': 'SUB-TOTAL',
                'Raw Text': f"Invoice Delta: ${invoice_delta:.2f}"
            }
            writer.writerow(sub_summary_row)
            
            # Add empty row for separation
            writer.writerow({field: '' for field in writer.fieldnames})
            
            # Add to batch totals
            batch_actual_total += invoice_actual_total
            batch_expected_total += invoice_expected_total
            batch_delta += invoice_delta
        
        # Add final batch summary row
        batch_summary_row = {
            'Invoice Number': 'BATCH',
            'Invoice Date': '',
            'Line Number': 'GRAND TOTAL',
            'Part Number': '',
            'Description': 'Batch Grand Totals',
            'Item Type': '',
            'Quantity': '',
            'Actual Rate': '',
            'Actual Total': f"${batch_actual_total:.2f}",
            'Expected Rate': '',
            'Expected Total': f"${batch_expected_total:.2f}",
            'Delta': f"${batch_delta:.2f}",
            'Status': 'GRAND TOTAL',
            'Raw Text': f"Batch Total Delta: ${batch_delta:.2f}"
        }
        writer.writerow(batch_summary_row)
        
        return output.getvalue()
    
    def _generate_format_section(self, validation_data: Dict[str, Any]) -> List[str]:
        """Generate format sections validation text."""
        lines = [
            "INVOICE TOTALS VALIDATION:",
            "-" * 26,
        ]
        
        format_sections = validation_data.get('format_sections', [])
        if format_sections:
            validation_status = "PASSED"
            
            for section in format_sections:
                section_type = section.get('section_type', 'Unknown')
                amount = section.get('amount')
                
                if amount is not None:
                    lines.append(f"{section_type.title()}: ${amount:.2f}")
                else:
                    lines.append(f"{section_type.title()}: [Not found]")
                    validation_status = "FAILED"
            
            lines.extend([
                f"Validation: {validation_status}",
                ""
            ])
        else:
            lines.extend([
                "No format validation data available",
                "Validation: [SKIPPED]",
                ""
            ])
        
        return lines
    
    def _generate_error_lines_section(self, validation_data: Dict[str, Any]) -> List[str]:
        """Generate error lines section using enhanced error_lines data."""
        error_lines = validation_data.get('error_lines', [])
        
        if not error_lines:
            return [
                "RATE VALIDATION ERRORS:",
                "-" * 24,
                "No validation errors found - all rates match authorized prices.",
                ""
            ]
        
        lines = [
            "RATE VALIDATION ERRORS:",
            "-" * 24,
            ""
        ]
        
        total_delta = 0.0
        actual_grand_total = 0.0
        expected_grand_total = 0.0
        
        for error in error_lines:
            line_number = error.get('line_number', 'Unknown')
            part_number = error.get('part_number', 'Unknown')
            description = error.get('description', 'No description')
            qty = error.get('qty', 1)
            expected_price = error.get('expected_price', 0)
            actual_price = error.get('actual_price', 0)
            expected_total = error.get('expected_total', 0)
            actual_total = error.get('actual_total', 0)
            raw_text = error.get('raw_text', '')
            
            # Calculate delta for this line (negative = overcharge)
            line_delta = expected_total - actual_total
            total_delta += line_delta
            actual_grand_total += actual_total
            expected_grand_total += expected_total
            
            # Handle None values safely
            expected_price_str = f"${expected_price:.2f}" if expected_price is not None else "N/A"
            actual_price_str = f"${actual_price:.2f}" if actual_price is not None else "N/A"
            expected_total_str = f"${expected_total:.2f}" if expected_total is not None else "N/A"
            actual_total_str = f"${actual_total:.2f}" if actual_total is not None else "N/A"
            line_delta_str = f"{'+' if line_delta >= 0 else ''}${line_delta:.2f}" if line_delta is not None else "N/A"
            
            lines.extend([
                f"Line {line_number}: {part_number} - {description}",
                f"  Expected: {qty} × {expected_price_str} = {expected_total_str}",
                f"  Actual:   {qty} × {actual_price_str} = {actual_total_str}",
                f"  Delta:    {line_delta_str}",
                f"  Raw: {raw_text}",
                ""
            ])
        
        lines.extend([
            "INVOICE SUMMARY:",
            "-" * 16,
            f"Invoice Grand Total:   ${actual_grand_total:.2f}",
            f"Total Delta:           {'+' if total_delta >= 0 else ''}${total_delta:.2f}",
            f"Correct Grand Total:   ${expected_grand_total:.2f}",
            ""
        ])
        
        return lines
    
    def _generate_summary_section(self, validation_data: Dict[str, Any]) -> List[str]:
        """Generate summary section."""
        invoice_metadata = validation_data.get('invoice_metadata', {})
        validation_summary = validation_data.get('validation_summary', {})
        
        total_parts = validation_summary.get('total_parts', 0)
        failed_parts = validation_summary.get('failed_parts', 0)
        passed_parts = validation_summary.get('passed_parts', 0)
        
        lines = [
            "SUMMARY:",
            "-" * 8,
            f"Total Line Items: {total_parts}",
            f"Passed Validation: {passed_parts}",
            f"Failed Validation: {failed_parts}",
            f"Error Rate: {(failed_parts/total_parts*100):.1f}%" if total_parts > 0 else "Error Rate: 0.0%",
            ""
        ]
        
        # Remove recommendations section as requested
        
        return lines
    
    def _parse_rate_and_quantity(self, raw_text: str) -> tuple:
        """Parse rate and quantity from raw text line."""
        if not raw_text:
            return None, None
        
        # Format: "employee | part | description | size | type | quantity | rate | total"
        # Example: "1 | Anthony Carson | GP1212NAVY | PANT FR CARGO DRIFIRE |  | 38X34 | Rent |  | 11 | 1.150 | 12.65"
        parts = [p.strip() for p in raw_text.split('|')]
        
        try:
            if len(parts) >= 3:
                # The last 3 parts should be: quantity, rate, total
                # Work backwards from the end
                total_str = parts[-1]  # line total (not needed)
                rate_str = parts[-2]   # individual rate
                qty_str = parts[-3]    # quantity
                
                rate = None
                quantity = None
                
                # Parse rate
                if rate_str and rate_str.replace('.', '').replace('-', '').isdigit():
                    rate = float(rate_str)
                
                # Parse quantity
                if qty_str and qty_str.isdigit():
                    quantity = int(qty_str)
                
                return rate, quantity
        except (ValueError, IndexError):
            pass
        
        return None, None
    
    def _create_enhanced_csv_row(self, part: Dict[str, Any], error_data: Optional[Dict[str, Any]],
                                invoice_num: str, invoice_date: str, status: str) -> Dict[str, str]:
        """Create an enhanced CSV row with proper validation data."""
        db_fields = part.get('database_fields', {})
        line_fields = part.get('lineitem_fields', {})
        
        part_number = db_fields.get('part_number', '')
        description = db_fields.get('description', '')
        item_type = db_fields.get('item_type', '')
        line_number = line_fields.get('line_number', '')
        raw_text = line_fields.get('raw_text', '')
        
        if error_data:
            # Use enhanced error data
            quantity = error_data.get('qty', 1)
            actual_rate = error_data.get('actual_price', 0)
            expected_rate = error_data.get('expected_price', 0)
            actual_total = error_data.get('actual_total', 0)
            expected_total = error_data.get('expected_total', 0)
            delta = expected_total - actual_total
        else:
            # Valid line - extract from part data with proper defaults
            quantity = line_fields.get('quantity', 1) or 1
            actual_rate = db_fields.get('authorized_price', 0) or 0
            expected_rate = actual_rate  # Same for valid lines
            
            # Calculate totals if not provided
            line_total = line_fields.get('total', 0) or 0
            if line_total > 0:
                actual_total = line_total
            else:
                actual_total = actual_rate * quantity
            
            expected_total = actual_total  # Same for valid lines
            delta = 0.0
        
        return {
            'Invoice Number': invoice_num,
            'Invoice Date': invoice_date,
            'Line Number': str(line_number) if line_number else '',
            'Part Number': part_number,
            'Description': description,
            'Item Type': item_type,
            'Quantity': str(quantity) if quantity else '',
            'Actual Rate': f"${actual_rate:.2f}" if actual_rate is not None else '$0.00',
            'Actual Total': f"${actual_total:.2f}" if actual_total is not None else '$0.00',
            'Expected Rate': f"${expected_rate:.2f}" if expected_rate is not None else '$0.00',
            'Expected Total': f"${expected_total:.2f}" if expected_total is not None else '$0.00',
            'Delta': f"${delta:.2f}" if delta is not None else '$0.00',
            'Status': status,
            'Raw Text': raw_text
        }
    
    def _write_reports_to_files(self, reports: Dict[str, str], base_path: str, validation_data: Dict[str, Any], preferred_format: str = "csv") -> Dict[str, Path]:
        """
        Write reports to files with proper naming and date folder structure.
        
        Args:
            reports: Dictionary of report content by format
            base_path: Base path for output files
            validation_data: Validation data containing invoice metadata
            preferred_format: Preferred format for naming consistency
            
        Returns:
            Dictionary mapping format to file path for auto-opening
        """
        base_path = Path(base_path)
        
        # Create date-based subdirectory: selected_destination/YYYYMMDD/
        date_folder = datetime.now().strftime('%Y%m%d')
        output_dir = base_path / date_folder
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get invoice number, handle "unknown" case
        invoice_num = validation_data.get('invoice_metadata', {}).get('invoice_number')
        if not invoice_num or invoice_num.lower() == 'unknown':
            # When no specific invoice selected, drop "unknown" from title
            base_name = "report"
        else:
            base_name = invoice_num
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report_files = {}
        
        # Write only the formats that were generated
        if 'json' in reports:
            json_path = output_dir / f"{base_name}_validation_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(reports['json'])
            report_files['json'] = json_path
        
        if 'txt' in reports:
            txt_path = output_dir / f"{base_name}_report_{timestamp}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(reports['txt'])
            report_files['txt'] = txt_path
        
        if 'csv' in reports:
            csv_path = output_dir / f"{base_name}_analysis_{timestamp}.csv"
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                f.write(reports['csv'])
            report_files['csv'] = csv_path
        
        return report_files


def generate_reports(validation_data: Dict[str, Any], output_path: str = None) -> Dict[str, str]:
    """
    Convenience function to generate all reports from validation JSON.
    
    Args:
        validation_data: The validation JSON object
        output_path: Optional path to write files
        
    Returns:
        Dict with 'json', 'txt', and 'csv' content
    """
    generator = SimpleReportGenerator()
    return generator.generate_reports(validation_data, output_path)