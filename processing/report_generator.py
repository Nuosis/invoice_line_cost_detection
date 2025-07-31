"""
Comprehensive report generation system for the Invoice Rate Detection System.

This module implements the complete report format specification including:
- Primary CSV Anomaly Report
- Detailed Validation Report (TXT)
- Summary Report (TXT)
- Unknown Parts Report (CSV)
- Processing Statistics Report (JSON)
- Error Report (TXT)

All reports follow the exact format specification with proper file naming,
directory organization, and template-based rendering.
"""

import json
import csv
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal
from dataclasses import dataclass, field

from processing.validation_models import (
    InvoiceValidationResult, ValidationAnomaly, SeverityLevel, AnomalyType
)
from database.database import DatabaseManager


logger = logging.getLogger(__name__)


@dataclass
class ReportOptions:
    """Configuration options for report generation."""
    session_id: str
    output_directory: Path = Path("./reports")
    include_bom: bool = True  # UTF-8 BOM for Excel compatibility
    max_line_width: int = 80
    currency_precision: int = 2
    rate_precision: int = 3
    date_format: str = "%m/%d/%Y"
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"
    
    def __post_init__(self):
        """Ensure output directory exists."""
        self.output_directory.mkdir(parents=True, exist_ok=True)


@dataclass
class ReportMetadata:
    """Metadata for generated reports."""
    report_type: str
    file_path: Path
    generation_time: datetime = field(default_factory=datetime.now)
    file_size_bytes: int = 0
    record_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'report_type': self.report_type,
            'file_path': str(self.file_path),
            'generation_time': self.generation_time.isoformat(),
            'file_size_bytes': self.file_size_bytes,
            'record_count': self.record_count
        }


class ReportTemplate:
    """Base class for all report templates."""
    
    def __init__(self, format_type: str, template_name: str):
        """
        Initialize report template.
        
        Args:
            format_type: Format type (csv, txt, json)
            template_name: Name of the template
        """
        self.format_type = format_type
        self.template_name = template_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def render(self, data: Dict[str, Any], options: ReportOptions) -> str:
        """
        Render template with data.
        
        Args:
            data: Data to render
            options: Report options
            
        Returns:
            Rendered content as string
        """
        raise NotImplementedError("Subclasses must implement render method")
    
    def generate_filename(self, report_type: str, options: ReportOptions) -> str:
        """
        Generate filename according to specification.
        
        Format: [report_type]_YYYYMMDD_HHMMSS_[session_short].extension
        
        Args:
            report_type: Type of report
            options: Report options containing session_id
            
        Returns:
            Generated filename
        """
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        session_short = options.session_id[:6] if len(options.session_id) >= 6 else options.session_id
        
        return f"{report_type}_{date_str}_{time_str}_{session_short}.{self.format_type}"


class CSVAnomalyReportTemplate(ReportTemplate):
    """CSV template for primary anomaly report with Excel optimization."""
    
    def __init__(self):
        super().__init__("csv", "anomaly_report")
    
    def render(self, data: Dict[str, Any], options: ReportOptions) -> str:
        """Render CSV anomaly report according to specification."""
        results = data.get('validation_results', [])
        
        # Define columns according to specification
        fieldnames = [
            'Invoice Number', 'Invoice Date', 'Invoice File', 'Line Number',
            'Part Number', 'Part Description', 'Quantity', 'Invoice Price',
            'Authorized Price', 'Price Difference', 'Percentage Difference',
            'Anomaly Type', 'Severity', 'Financial Impact', 'Processing Session', 'Notes'
        ]
        
        # Collect and sort anomaly rows
        anomaly_rows = []
        
        for result in results:
            for anomaly in result.get_all_anomalies():
                row = self._create_anomaly_row(result, anomaly, options)
                anomaly_rows.append(row)
        
        # Sort according to specification rules
        anomaly_rows.sort(key=self._sort_key)
        
        # Generate CSV content
        import io
        output = io.StringIO()
        
        # Add UTF-8 BOM for Excel compatibility if requested
        if options.include_bom:
            output.write('\ufeff')
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(anomaly_rows)
        
        return output.getvalue()
    
    def _create_anomaly_row(self, result: InvoiceValidationResult, 
                           anomaly: ValidationAnomaly, options: ReportOptions) -> Dict[str, str]:
        """Create a single anomaly row for CSV output."""
        details = anomaly.details or {}
        
        # Extract line item details
        line_number = details.get('line_number', '')
        quantity = details.get('quantity', '')
        invoice_price = details.get('invoice_price', details.get('price'))
        authorized_price = details.get('authorized_price', details.get('expected_price'))
        
        # Calculate price difference and percentage
        price_diff = ""
        percentage_diff = ""
        if invoice_price is not None and authorized_price is not None:
            try:
                inv_price = Decimal(str(invoice_price))
                auth_price = Decimal(str(authorized_price))
                diff = inv_price - auth_price
                price_diff = self._format_currency(diff, options)
                
                if auth_price != 0:
                    pct = (diff / auth_price) * 100
                    percentage_diff = f"{pct:.1f}%"
            except (ValueError, TypeError, ZeroDivisionError):
                pass
        
        # Calculate financial impact
        financial_impact = ""
        if quantity and price_diff:
            try:
                qty = int(quantity)
                diff_amount = Decimal(str(price_diff.replace('$', '').replace(',', '')))
                impact = qty * diff_amount
                financial_impact = self._format_currency(impact, options)
            except (ValueError, TypeError):
                financial_impact = details.get('total_impact', '')
                if financial_impact:
                    financial_impact = self._format_currency(financial_impact, options)
        
        return {
            'Invoice Number': result.invoice_number or '',
            'Invoice Date': self._format_date(result.invoice_date, options),
            'Invoice File': Path(result.invoice_path).name if result.invoice_path else '',
            'Line Number': str(line_number) if line_number else '',
            'Part Number': anomaly.part_number or '',
            'Part Description': details.get('description', ''),
            'Quantity': str(quantity) if quantity else '',
            'Invoice Price': self._format_currency(invoice_price, options) if invoice_price else '',
            'Authorized Price': self._format_currency(authorized_price, options) if authorized_price else 'N/A',
            'Price Difference': price_diff,
            'Percentage Difference': percentage_diff,
            'Anomaly Type': anomaly.anomaly_type.value,
            'Severity': anomaly.severity.value,
            'Financial Impact': financial_impact,
            'Processing Session': options.session_id,
            'Notes': anomaly.description or ''
        }
    
    def _sort_key(self, row: Dict[str, str]) -> tuple:
        """Generate sort key according to specification rules."""
        # Primary: Severity (CRITICAL first, then WARNING, then INFORMATIONAL)
        severity_order = {'CRITICAL': 0, 'WARNING': 1, 'INFORMATIONAL': 2}
        severity_rank = severity_order.get(row['Severity'], 3)
        
        # Secondary: Financial Impact (highest first)
        try:
            financial_impact = float(row['Financial Impact'].replace('$', '').replace(',', ''))
        except (ValueError, AttributeError):
            financial_impact = 0.0
        
        # Tertiary: Invoice Date (newest first)
        try:
            invoice_date = datetime.strptime(row['Invoice Date'], "%m/%d/%Y")
        except (ValueError, TypeError):
            invoice_date = datetime.min
        
        return (severity_rank, -financial_impact, -invoice_date.timestamp())
    
    def _format_currency(self, amount: Union[Decimal, float, int, str], 
                        options: ReportOptions) -> str:
        """Format currency according to specification."""
        if amount is None or amount == '':
            return ''
        
        try:
            value = float(amount)
            return f"${value:,.{options.currency_precision}f}"
        except (ValueError, TypeError):
            return str(amount)
    
    def _format_date(self, date_str: str, options: ReportOptions) -> str:
        """Format date according to specification (MM/DD/YYYY for Excel)."""
        if not date_str:
            return ''
        
        try:
            # Try to parse various date formats and convert to MM/DD/YYYY
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime(options.date_format)
                except ValueError:
                    continue
            return date_str  # Return as-is if can't parse
        except (ValueError, TypeError):
            return str(date_str)


class DetailedValidationReportTemplate(ReportTemplate):
    """Text template for detailed validation report."""
    
    def __init__(self):
        super().__init__("txt", "detailed_validation_report")
    
    def render(self, data: Dict[str, Any], options: ReportOptions) -> str:
        """Render detailed validation report according to specification."""
        results = data.get('validation_results', [])
        processing_stats = data.get('processing_stats', {})
        
        lines = []
        
        # Header
        lines.extend([
            "Invoice Rate Detection System - Detailed Validation Report",
            "=" * 60,
            f"Generated: {datetime.now().strftime(options.timestamp_format)}",
            f"Validation Mode: Parts-based validation",
            ""
        ])
        
        # Process each invoice
        for result in results:
            if result.get_all_anomalies():
                lines.extend(self._render_invoice_section(result, options))
        
        # Processing summary
        lines.extend(self._render_processing_summary(results, processing_stats, options))
        
        lines.extend([
            "=" * 60,
            "END OF REPORT",
            "=" * 60
        ])
        
        return "\n".join(lines)
    
    def _render_invoice_section(self, result: InvoiceValidationResult, 
                               options: ReportOptions) -> List[str]:
        """Render individual invoice section."""
        lines = [
            "=" * 60,
            f"INVOICE: {result.invoice_number}",
            "=" * 60,
            f"Invoice Date: {self._format_date(result.invoice_date, options)}",
            f"Lines Processed: {len(result.get_all_anomalies())}",
            "",
            "RATE VALIDATION ERRORS:",
            "-" * 24,
            ""
        ]
        
        # Add each anomaly
        for i, anomaly in enumerate(result.get_all_anomalies(), 1):
            lines.extend(self._render_anomaly_detail(i, anomaly, options))
        
        # Invoice totals validation (placeholder - would need actual totals data)
        lines.extend([
            "INVOICE TOTALS VALIDATION:",
            "-" * 26,
            "Subtotal: [Validation needed]",
            "Freight: [Validation needed]",
            "Tax: [Validation needed]",
            "Total: [Validation needed]",
            "Validation: [PASSED/FAILED]",
            "",
            f"Invoice {result.invoice_number} Summary:",
            f"  Error Lines: {len(result.get_all_anomalies())} of [total] lines",
            f"  Invoice Adjustment: {self._calculate_invoice_adjustment(result, options)}",
            ""
        ])
        
        return lines
    
    def _render_anomaly_detail(self, line_num: int, anomaly: ValidationAnomaly, 
                              options: ReportOptions) -> List[str]:
        """Render individual anomaly detail."""
        details = anomaly.details or {}
        
        lines = [
            f"Line {line_num}: [Employee] - {anomaly.part_number} {details.get('description', '')}",
        ]
        
        # Rate comparison
        invoice_price = details.get('invoice_price', details.get('price'))
        authorized_price = details.get('authorized_price', details.get('expected_price'))
        
        if invoice_price is not None and authorized_price is not None:
            try:
                inv_price = Decimal(str(invoice_price))
                auth_price = Decimal(str(authorized_price))
                diff = inv_price - auth_price
                
                lines.append(
                    f"  Actual Rate: ${inv_price:.{options.rate_precision}f}  |  "
                    f"Expected Rate: ${auth_price:.{options.rate_precision}f}  |  "
                    f"Difference: {'+' if diff >= 0 else ''}${diff:.{options.rate_precision}f}"
                )
                
                quantity = details.get('quantity', 1)
                if quantity:
                    line_adjustment = diff * int(quantity)
                    lines.append(
                        f"  Quantity: {quantity}  |  "
                        f"Line Adjustment: {'+' if line_adjustment >= 0 else ''}${line_adjustment:.{options.currency_precision}f}"
                    )
            except (ValueError, TypeError):
                pass
        
        lines.append("")
        return lines
    
    def _render_processing_summary(self, results: List[InvoiceValidationResult], 
                                  processing_stats: Dict[str, Any], 
                                  options: ReportOptions) -> List[str]:
        """Render processing summary section."""
        total_invoices = len(results)
        total_anomalies = sum(len(r.get_all_anomalies()) for r in results)
        critical_anomalies = sum(len(r.critical_anomalies) for r in results)
        warning_anomalies = sum(len(r.warning_anomalies) for r in results)
        
        # Calculate financial impact
        total_adjustment = Decimal('0.00')
        overcharges = Decimal('0.00')
        undercharges = Decimal('0.00')
        
        for result in results:
            adjustment = self._calculate_invoice_adjustment_decimal(result)
            total_adjustment += adjustment
            if adjustment > 0:
                overcharges += adjustment
            else:
                undercharges += abs(adjustment)
        
        lines = [
            "=" * 60,
            "PROCESSING SUMMARY",
            "=" * 60,
            "",
            f"Total Invoices Processed: {total_invoices}",
            "",
            "Line Error Analysis:",
            f"  Total Error Lines: {total_anomalies}",
            f"  Errored Invoices: {[r.invoice_number for r in results if r.get_all_anomalies()]}",
            "",
            "Rate Validation Issues:",
            f"  Lines with critical issues: {critical_anomalies}",
            f"  Lines with warnings: {warning_anomalies}",
            f"  Lines with zero rates: 0",  # Would need actual data
            "",
            "Financial Impact:",
            f"  Total Adjustment Required: {'+' if total_adjustment >= 0 else ''}${total_adjustment:.{options.currency_precision}f}",
            f"  Overcharges: ${overcharges:.{options.currency_precision}f}",
            f"  Undercharges: -${undercharges:.{options.currency_precision}f}",
            f"  Net Adjustment: {'+' if total_adjustment >= 0 else ''}${total_adjustment:.{options.currency_precision}f}",
            "",
            "Processing Performance:",
            f"  Average Processing Time: {processing_stats.get('average_processing_time', 0):.2f}s per invoice",
            f"  Total Processing Time: {processing_stats.get('total_processing_time', 0):.2f}s",
            f"  Lines Processed per Second: {processing_stats.get('lines_per_second', 0):.0f}",
            ""
        ]
        
        return lines
    
    def _calculate_invoice_adjustment(self, result: InvoiceValidationResult, 
                                    options: ReportOptions) -> str:
        """Calculate total adjustment for an invoice."""
        adjustment = self._calculate_invoice_adjustment_decimal(result)
        return f"{'+' if adjustment >= 0 else ''}${adjustment:.{options.currency_precision}f}"
    
    def _calculate_invoice_adjustment_decimal(self, result: InvoiceValidationResult) -> Decimal:
        """Calculate total adjustment as Decimal."""
        total = Decimal('0.00')
        
        for anomaly in result.get_all_anomalies():
            details = anomaly.details or {}
            
            try:
                invoice_price = details.get('invoice_price', details.get('price'))
                authorized_price = details.get('authorized_price', details.get('expected_price'))
                quantity = details.get('quantity', 1)
                
                if invoice_price is not None and authorized_price is not None and quantity:
                    inv_price = Decimal(str(invoice_price))
                    auth_price = Decimal(str(authorized_price))
                    qty = int(quantity)
                    
                    line_adjustment = (inv_price - auth_price) * qty
                    total += line_adjustment
            except (ValueError, TypeError):
                continue
        
        return total
    
    def _format_date(self, date_str: str, options: ReportOptions) -> str:
        """Format date for display."""
        if not date_str:
            return ''
        
        try:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime(options.date_format)
                except ValueError:
                    continue
            return date_str
        except (ValueError, TypeError):
            return str(date_str)


class SummaryReportTemplate(ReportTemplate):
    """Text template for processing summary report."""
    
    def __init__(self):
        super().__init__("txt", "processing_summary")
    
    def render(self, data: Dict[str, Any], options: ReportOptions) -> str:
        """Render processing summary report according to specification."""
        results = data.get('validation_results', [])
        processing_stats = data.get('processing_stats', {})
        input_path = data.get('input_path', 'Unknown')
        
        lines = [
            "INVOICE RATE DETECTION SYSTEM - PROCESSING SUMMARY",
            "=" * 50,
            "",
            f"Processing Session: {options.session_id}",
            f"Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}",
            f"Input Folder: {input_path}",
            f"Processing Duration: {self._format_duration(processing_stats.get('total_processing_time', 0))}",
            "",
            "PROCESSING STATISTICS",
            "-" * 20,
            f"Total Invoices Processed: {len(results)}",
            f"Successfully Processed: {len([r for r in results if r.processing_successful])}",
            f"Failed to Process: {len([r for r in results if not r.processing_successful])}",
            f"Total Line Items Validated: {sum(len(r.get_all_anomalies()) for r in results)}",
            "",
            "ANOMALY SUMMARY",
            "-" * 14,
            f"Total Anomalies Found: {sum(len(r.get_all_anomalies()) for r in results)}",
            f"├─ Critical Issues: {sum(len(r.critical_anomalies) for r in results)}",
            f"├─ Warnings: {sum(len(r.warning_anomalies) for r in results)}",
            f"└─ Informational: {sum(len(r.informational_anomalies) for r in results)}",
            "",
            "FINANCIAL IMPACT",
            "-" * 15,
        ]
        
        # Calculate financial metrics
        total_overcharges, avg_overcharge, largest_overcharge = self._calculate_financial_metrics(results)
        
        lines.extend([
            f"Total Potential Overcharges: ${total_overcharges:,.2f}",
            f"Average Overcharge per Invoice: ${avg_overcharge:.2f}",
            f"Largest Single Overcharge: ${largest_overcharge['amount']:.2f} (Invoice: {largest_overcharge['invoice']}, Part: {largest_overcharge['part']})",
            "",
            "PARTS DISCOVERY",
            "-" * 14,
            f"Unknown Parts Discovered: {processing_stats.get('unknown_parts_discovered', 0)}",
            f"Parts Added to Database: {processing_stats.get('parts_added_during_discovery', 0)}",
            f"Parts Skipped by User: {processing_stats.get('parts_skipped', 0)}",
            "",
            "TOP ISSUES BY FREQUENCY",
            "-" * 22,
        ])
        
        # Add top issues
        issue_counts = self._calculate_issue_frequency(results)
        for i, (issue_type, count) in enumerate(issue_counts[:3], 1):
            lines.append(f"{i}. {issue_type}: {count} occurrences")
        
        lines.extend([
            "",
            "RECOMMENDATIONS",
            "-" * 14,
            f"• Review {sum(len(r.critical_anomalies) for r in results)} critical price discrepancies immediately",
            f"• Add {processing_stats.get('unknown_parts_discovered', 0)} unknown parts to master database",
            "• Investigate recurring issues with price discrepancies",
            "",
            "FILES GENERATED",
            "-" * 14,
            f"• Main Report: invoice_anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            f"• Unknown Parts: unknown_parts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            f"• Error Log: processing_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        ])
        
        return "\n".join(lines)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes} minutes {remaining_seconds} seconds"
    
    def _calculate_financial_metrics(self, results: List[InvoiceValidationResult]) -> tuple:
        """Calculate financial impact metrics."""
        total_overcharges = 0.0
        overcharge_amounts = []
        largest_overcharge = {'amount': 0.0, 'invoice': '', 'part': ''}
        
        for result in results:
            for anomaly in result.get_all_anomalies():
                if anomaly.anomaly_type == AnomalyType.PRICE_DISCREPANCY:
                    details = anomaly.details or {}
                    
                    try:
                        invoice_price = details.get('invoice_price', details.get('price'))
                        authorized_price = details.get('authorized_price', details.get('expected_price'))
                        quantity = details.get('quantity', 1)
                        
                        if invoice_price and authorized_price and quantity:
                            diff = (float(invoice_price) - float(authorized_price)) * int(quantity)
                            if diff > 0:  # Only count overcharges
                                total_overcharges += diff
                                overcharge_amounts.append(diff)
                                
                                if diff > largest_overcharge['amount']:
                                    largest_overcharge = {
                                        'amount': diff,
                                        'invoice': result.invoice_number or 'Unknown',
                                        'part': anomaly.part_number or 'Unknown'
                                    }
                    except (ValueError, TypeError):
                        continue
        
        avg_overcharge = total_overcharges / len(results) if results else 0.0
        
        return total_overcharges, avg_overcharge, largest_overcharge
    
    def _calculate_issue_frequency(self, results: List[InvoiceValidationResult]) -> List[tuple]:
        """Calculate frequency of different issue types."""
        issue_counts = {}
        
        for result in results:
            for anomaly in result.get_all_anomalies():
                issue_type = anomaly.anomaly_type.value
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        return sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)


class UnknownPartsReportTemplate(ReportTemplate):
    """CSV template for unknown parts report."""
    
    def __init__(self):
        super().__init__("csv", "unknown_parts")
    
    def render(self, data: Dict[str, Any], options: ReportOptions) -> str:
        """Render unknown parts report according to specification."""
        unknown_parts = data.get('unknown_parts', [])
        
        fieldnames = [
            'Part Number', 'Description', 'First Seen Invoice', 'Invoice Date',
            'Discovered Price', 'Quantity', 'Suggested Authorized Price',
            'Confidence Level', 'Similar Parts Found', 'Recommended Action',
            'Discovery Session', 'User Decision'
        ]
        
        import io
        output = io.StringIO()
        
        if options.include_bom:
            output.write('\ufeff')
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for part in unknown_parts:
            row = {
                'Part Number': part.get('part_number', ''),
                'Description': part.get('description', ''),
                'First Seen Invoice': part.get('first_seen_invoice', ''),
                'Invoice Date': self._format_date(part.get('invoice_date', ''), options),
                'Discovered Price': self._format_currency(part.get('discovered_price'), options),
                'Quantity': str(part.get('quantity', '')) if part.get('quantity') else '',
                'Suggested Authorized Price': self._format_currency(part.get('suggested_price'), options),
                'Confidence Level': f"{part.get('confidence', 0):.1f}%" if part.get('confidence') else '',
                'Similar Parts Found': str(part.get('similar_parts_count', 0)),
                'Recommended Action': part.get('recommended_action', 'Review and add to database'),
                'Discovery Session': options.session_id,
                'User Decision': part.get('user_decision', '')
            }
            writer.writerow(row)
        
        return output.getvalue()
    
    def _format_currency(self, amount: Union[Decimal, float, int, str], options: ReportOptions) -> str:
        """Format currency value."""
        if amount is None or amount == '':
            return ''
        
        try:
            value = float(amount)
            return f"${value:.{options.currency_precision}f}"
        except (ValueError, TypeError):
            return str(amount)
    
    def _format_date(self, date_str: str, options: ReportOptions) -> str:
        """Format date for display."""
        if not date_str:
            return ''
        
        try:
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime(options.date_format)
                except ValueError:
                    continue
            return date_str
        except (ValueError, TypeError):
            return str(date_str)


class ProcessingStatsReportTemplate(ReportTemplate):
    """JSON template for processing statistics report."""
    
    def __init__(self):
        super().__init__("json", "processing_stats")
    
    def render(self, data: Dict[str, Any], options: ReportOptions) -> str:
        """Render processing statistics report according to specification."""
        results = data.get('validation_results', [])
        processing_stats = data.get('processing_stats', {})
        
        start_time = processing_stats.get('processing_start', datetime.now())
        end_time = processing_stats.get('processing_end', datetime.now())
        
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        total_files = len(results)
        successful_extractions = len([r for r in results if r.processing_successful])
        failed_extractions = total_files - successful_extractions
        total_line_items = sum(len(r.get_all_anomalies()) for r in results)
        
        # Calculate anomaly statistics
        anomaly_stats = {}
        for result in results:
            for anomaly in result.get_all_anomalies():
                anomaly_type = anomaly.anomaly_type.value
                anomaly_stats[anomaly_type] = anomaly_stats.get(anomaly_type, 0) + 1
        
        stats_data = {
            "session_id": options.session_id,
            "processing_start": start_time.isoformat(),
            "processing_end": end_time.isoformat(),
            "duration_seconds": duration,
            "performance_metrics": {
                "files_per_second": total_files / duration if duration > 0 else 0,
                "validation_operations_per_second": total_line_items / duration if duration > 0 else 0,
                "database_queries_executed": processing_stats.get('database_queries', 0),
                "cache_hit_rate": processing_stats.get('cache_hit_rate', 0.0)
            },
            "file_statistics": {
                "total_files": total_files,
                "successful_extractions": successful_extractions,
                "failed_extractions": failed_extractions,
                "average_file_size_mb": processing_stats.get('average_file_size_mb', 0.0),
                "total_pages_processed": processing_stats.get('total_pages_processed', 0)
            },
            "validation_statistics": {
                "total_line_items": total_line_items,
                "parts_validated": processing_stats.get('parts_validated', 0),
                "unknown_parts": processing_stats.get('unknown_parts_discovered', 0),
                "price_comparisons": processing_stats.get('price_comparisons', 0),
                "format_validations": total_files
            },
            "anomaly_statistics": {
                "total_anomalies": sum(len(r.get_all_anomalies()) for r in results),
                "critical_anomalies": sum(len(r.critical_anomalies) for r in results),
                "warning_anomalies": sum(len(r.warning_anomalies) for r in results),
                "informational_anomalies": sum(len(r.informational_anomalies) for r in results),
                "anomalies_by_type": anomaly_stats
            }
        }
        
        return json.dumps(stats_data, indent=2, ensure_ascii=False)


class ErrorReportTemplate(ReportTemplate):
    """Text template for error report."""
    
    def __init__(self):
        super().__init__("txt", "processing_errors")
    
    def render(self, data: Dict[str, Any], options: ReportOptions) -> str:
        """Render error report according to specification."""
        errors = data.get('errors', [])
        warnings = data.get('warnings', [])
        failed_files = data.get('failed_files', [])
        skipped_items = data.get('skipped_items', [])
        system_info = data.get('system_info', {})
        
        lines = [
            "INVOICE RATE DETECTION SYSTEM - ERROR REPORT",
            "=" * 44,
            "",
            f"Processing Session: {options.session_id}",
            f"Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}",
            ""
        ]
        
        # Critical errors
        if errors:
            lines.extend([
                "CRITICAL ERRORS",
                "-" * 14,
            ])
            
            for error in errors:
                lines.extend([
                    f"{error.get('timestamp', datetime.now().strftime('%H:%M:%S'))} ERROR: {error.get('type', 'Unknown')} - {error.get('message', '')}",
                    f"  File: {error.get('file', 'Unknown')}",
                    f"  Details: {error.get('details', 'No additional details')}",
                    f"  Recovery Action: {error.get('recovery_action', 'None attempted')}",
                    f"  User Action Required: {error.get('user_action', 'Contact support')}",
                    ""
                ])
        
        # Warnings
        if warnings:
            lines.extend([
                "WARNINGS",
                "-" * 8,
            ])
            
            for warning in warnings:
                lines.extend([
                    f"{warning.get('timestamp', datetime.now().strftime('%H:%M:%S'))} WARNING: {warning.get('type', 'Unknown')} - {warning.get('message', '')}",
                    f"  Context: {warning.get('context', 'No additional context')}",
                    f"  Impact: {warning.get('impact', 'Unknown impact')}",
                    ""
                ])
        
        # Processing failures
        if failed_files or skipped_items:
            lines.extend([
                "PROCESSING FAILURES",
                "-" * 18,
            ])
            
            if failed_files:
                lines.append("Failed Files:")
                for failed_file in failed_files:
                    lines.append(f"• {failed_file.get('filename', 'Unknown')} - {failed_file.get('reason', 'Unknown reason')}")
                lines.append("")
            
            if skipped_items:
                lines.append("Skipped Line Items:")
                for skipped in skipped_items:
                    lines.append(f"• Invoice {skipped.get('invoice', 'Unknown')}, Line {skipped.get('line', 'Unknown')} - {skipped.get('reason', 'Unknown reason')}")
                lines.append("")
        
        # System information
        lines.extend([
            "SYSTEM INFORMATION",
            "-" * 17,
            f"Application Version: {system_info.get('app_version', 'Unknown')}",
            f"Database Version: {system_info.get('db_version', 'Unknown')}",
            f"Python Version: {system_info.get('python_version', 'Unknown')}",
            f"Available Memory: {system_info.get('available_memory_mb', 'Unknown')} MB",
            f"Disk Space: {system_info.get('disk_space_gb', 'Unknown')} GB free"
        ])
        
        return "\n".join(lines)


class ComprehensiveReportGenerator:
    """
    Main report generator that orchestrates all report types according to specification.
    
    This class manages the complete report generation workflow including:
    - Template selection and rendering
    - File naming according to specification
    - Directory organization
    - Multiple report type generation
    - Error handling and logging
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize comprehensive report generator.
        
        Args:
            db_manager: Database manager for configuration access
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize templates
        self.templates = {
            'csv_anomaly': CSVAnomalyReportTemplate(),
            'detailed_validation': DetailedValidationReportTemplate(),
            'summary': SummaryReportTemplate(),
            'unknown_parts': UnknownPartsReportTemplate(),
            'processing_stats': ProcessingStatsReportTemplate(),
            'error_report': ErrorReportTemplate()
        }
    
    def generate_all_reports(self,
                           validation_results: List[InvoiceValidationResult],
                           processing_stats: Dict[str, Any],
                           session_id: str,
                           output_directory: Path = None,
                           input_path: str = None,
                           unknown_parts: List[Dict[str, Any]] = None,
                           errors: List[Dict[str, Any]] = None,
                           warnings: List[Dict[str, Any]] = None) -> Dict[str, ReportMetadata]:
        """
        Generate all reports according to specification.
        
        Args:
            validation_results: List of validation results
            processing_stats: Processing statistics
            session_id: Processing session ID
            output_directory: Output directory (defaults to ./reports)
            input_path: Input path for processing
            unknown_parts: List of unknown parts discovered
            errors: List of errors encountered
            warnings: List of warnings encountered
            
        Returns:
            Dictionary mapping report type to metadata
        """
        if output_directory is None:
            output_directory = Path("./reports")
        
        # Create report options
        options = ReportOptions(
            session_id=session_id,
            output_directory=output_directory
        )
        
        # Ensure directory structure exists
        self._create_directory_structure(options)
        
        # Prepare data for all reports
        report_data = {
            'validation_results': validation_results,
            'processing_stats': processing_stats,
            'input_path': input_path or 'Unknown',
            'unknown_parts': unknown_parts or [],
            'errors': errors or [],
            'warnings': warnings or [],
            'failed_files': processing_stats.get('failed_files', []),
            'skipped_items': processing_stats.get('skipped_items', []),
            'system_info': self._get_system_info()
        }
        
        generated_reports = {}
        
        try:
            # Generate primary CSV anomaly report
            if validation_results:
                metadata = self._generate_single_report(
                    'csv_anomaly', 'invoice_anomalies', report_data, options
                )
                generated_reports['anomaly_report'] = metadata
            
            # Generate detailed validation report
            if validation_results:
                metadata = self._generate_single_report(
                    'detailed_validation', 'invoice_validation_report', report_data, options
                )
                generated_reports['validation_report'] = metadata
            
            # Generate summary report
            metadata = self._generate_single_report(
                'summary', 'processing_summary', report_data, options
            )
            generated_reports['summary_report'] = metadata
            
            # Generate unknown parts report if there are unknown parts
            if unknown_parts:
                metadata = self._generate_single_report(
                    'unknown_parts', 'unknown_parts', report_data, options
                )
                generated_reports['unknown_parts_report'] = metadata
            
            # Generate processing statistics report
            metadata = self._generate_single_report(
                'processing_stats', 'processing_stats', report_data, options
            )
            generated_reports['stats_report'] = metadata
            
            # Generate error report if there are errors or warnings
            if errors or warnings:
                metadata = self._generate_single_report(
                    'error_report', 'processing_errors', report_data, options
                )
                generated_reports['error_report'] = metadata
            
            self.logger.info(f"Generated {len(generated_reports)} reports for session {session_id}")
            
        except Exception as e:
            self.logger.exception(f"Failed to generate reports: {e}")
            raise
        
        return generated_reports
    
    def _generate_single_report(self, template_key: str, report_type: str,
                               data: Dict[str, Any], options: ReportOptions) -> ReportMetadata:
        """Generate a single report using the specified template."""
        template = self.templates[template_key]
        
        try:
            # Render content
            content = template.render(data, options)
            
            # Generate filename
            filename = template.generate_filename(report_type, options)
            
            # Determine output path (current session directory)
            session_dir = self._get_session_directory(options)
            file_path = session_dir / filename
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Create metadata
            file_size = file_path.stat().st_size
            record_count = self._estimate_record_count(content, template.format_type)
            
            metadata = ReportMetadata(
                report_type=report_type,
                file_path=file_path,
                file_size_bytes=file_size,
                record_count=record_count
            )
            
            self.logger.info(f"Generated {report_type} report: {file_path}")
            return metadata
            
        except Exception as e:
            self.logger.exception(f"Failed to generate {report_type} report: {e}")
            raise
    
    def _create_directory_structure(self, options: ReportOptions) -> None:
        """Create directory structure according to specification."""
        base_dir = options.output_directory
        
        # Create main directories
        current_dir = base_dir / "current"
        archive_dir = base_dir / "archive"
        templates_dir = base_dir / "templates"
        
        for directory in [current_dir, archive_dir, templates_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create date-specific directory
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = current_dir / today
        date_dir.mkdir(exist_ok=True)
        
        # Create session directory
        session_dir = self._get_session_directory(options)
        session_dir.mkdir(exist_ok=True)
    
    def _get_session_directory(self, options: ReportOptions) -> Path:
        """Get the session-specific directory path."""
        base_dir = options.output_directory
        today = datetime.now().strftime("%Y-%m-%d")
        session_short = options.session_id[:6] if len(options.session_id) >= 6 else options.session_id
        time_str = datetime.now().strftime("%H%M%S")
        
        session_dir_name = f"session_{session_short}_{time_str}"
        return base_dir / "current" / today / session_dir_name
    
    def _estimate_record_count(self, content: str, format_type: str) -> int:
        """Estimate the number of records in the content."""
        if format_type == 'csv':
            lines = content.strip().split('\n')
            return max(0, len(lines) - 1)  # Subtract header
        elif format_type == 'json':
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return len(data)
                elif isinstance(data, dict):
                    return 1
            except json.JSONDecodeError:
                pass
        
        # For text files, count meaningful lines (non-empty, non-separator)
        lines = content.strip().split('\n')
        meaningful_lines = [
            line for line in lines
            if line.strip() and not line.strip().startswith('=') and not line.strip().startswith('-')
        ]
        return len(meaningful_lines)
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for error reporting."""
        import sys
        import platform
        import psutil
        import shutil
        
        try:
            return {
                'app_version': '1.0.0',  # Would be read from config
                'db_version': '1.0',     # Would be read from database
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'platform': platform.system(),
                'available_memory_mb': round(psutil.virtual_memory().available / (1024 * 1024)),
                'disk_space_gb': round(shutil.disk_usage('.').free / (1024 * 1024 * 1024))
            }
        except Exception as e:
            self.logger.warning(f"Could not gather system info: {e}")
            return {
                'app_version': '1.0.0',
                'db_version': '1.0',
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
                'platform': 'Unknown',
                'available_memory_mb': 'Unknown',
                'disk_space_gb': 'Unknown'
            }


# Factory function for creating report generator
def create_report_generator(db_manager: DatabaseManager) -> ComprehensiveReportGenerator:
    """
    Factory function to create a comprehensive report generator.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        Configured ComprehensiveReportGenerator instance
    """
    return ComprehensiveReportGenerator(db_manager)