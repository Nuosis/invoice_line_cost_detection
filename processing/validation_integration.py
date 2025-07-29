"""
Integration utilities for connecting the validation engine with CLI commands.

This module provides utilities and helper functions to integrate the validation
engine with the existing CLI command structure.
"""

import logging
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from processing.validation_engine import ValidationEngine
from processing.validation_models import (
    InvoiceValidationResult, ValidationConfiguration, ValidationAnomaly,
    PartDiscoveryResult, PriceSuggestion, SeverityLevel, AnomalyType
)
from processing.validation_strategies_extended import suggest_authorized_price
from database.database import DatabaseManager
from database.models import Part, PartDiscoveryLog
from cli.progress import ProgressTracker
from cli.prompts import PartDiscoveryPrompt
from cli.formatters import format_currency, format_table


logger = logging.getLogger(__name__)


class ValidationReportGenerator:
    """Generates reports from validation results."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize report generator.
        
        Args:
            db_manager: Database manager for configuration access
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def generate_anomaly_report(self, results: List[InvoiceValidationResult], 
                               output_path: Path, format_type: str = 'csv') -> Dict[str, Any]:
        """
        Generate anomaly report from validation results.
        
        Args:
            results: List of validation results
            output_path: Path to write report
            format_type: Report format ('csv' or 'txt')
            
        Returns:
            Report generation statistics
        """
        if format_type.lower() == 'csv':
            return self._generate_csv_report(results, output_path)
        else:
            return self._generate_txt_report(results, output_path)
    
    def _generate_csv_report(self, results: List[InvoiceValidationResult], 
                           output_path: Path) -> Dict[str, Any]:
        """Generate CSV format report."""
        anomaly_rows = []
        
        for result in results:
            for anomaly in result.get_all_anomalies():
                # Extract line item details if available
                line_item_details = self._extract_line_item_details(anomaly)
                
                row = {
                    'Invoice Number': result.invoice_number,
                    'Invoice Date': result.invoice_date,
                    'Part Number': anomaly.part_number or '',
                    'Description': line_item_details.get('description', ''),
                    'Rate': line_item_details.get('rate', ''),
                    'Quantity': line_item_details.get('quantity', ''),
                    'Anomaly Type': anomaly.anomaly_type.value,
                    'Severity': anomaly.severity.value,
                    'Issue Description': anomaly.description,
                    'Overcharge Amount': self._calculate_overcharge_amount(anomaly),
                    'Total Impact': self._calculate_total_impact(anomaly),
                    'Resolution Action': anomaly.resolution_action or '',
                    'Detected At': anomaly.detected_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                anomaly_rows.append(row)
        
        # Write CSV file
        if anomaly_rows:
            fieldnames = list(anomaly_rows[0].keys())
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(anomaly_rows)
        else:
            # Write empty CSV with headers
            fieldnames = ['Invoice Number', 'Invoice Date', 'Part Number', 'Description', 
                         'Rate', 'Quantity', 'Anomaly Type', 'Severity', 'Issue Description',
                         'Overcharge Amount', 'Total Impact', 'Resolution Action', 'Detected At']
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
        
        return {
            'total_anomalies': len(anomaly_rows),
            'critical_anomalies': len([r for r in anomaly_rows if r['Severity'] == 'CRITICAL']),
            'warning_anomalies': len([r for r in anomaly_rows if r['Severity'] == 'WARNING']),
            'invoices_processed': len(results),
            'output_path': str(output_path)
        }
    
    def _generate_txt_report(self, results: List[InvoiceValidationResult], 
                           output_path: Path) -> Dict[str, Any]:
        """Generate text format report."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Invoice Rate Detection System - Validation Report\n")
            f.write("=" * 60 + "\n\n")
            
            # Summary statistics
            total_invoices = len(results)
            successful_validations = len([r for r in results if r.processing_successful])
            total_anomalies = sum(len(r.get_all_anomalies()) for r in results)
            critical_anomalies = sum(len(r.critical_anomalies) for r in results)
            
            f.write(f"Processing Summary:\n")
            f.write(f"  Total Invoices: {total_invoices}\n")
            f.write(f"  Successfully Processed: {successful_validations}\n")
            f.write(f"  Total Anomalies Found: {total_anomalies}\n")
            f.write(f"  Critical Issues: {critical_anomalies}\n\n")
            
            # Detailed anomalies by invoice
            for result in results:
                if result.get_all_anomalies():
                    f.write(f"Invoice: {result.invoice_number} ({result.invoice_date})\n")
                    f.write("-" * 40 + "\n")
                    
                    for anomaly in result.get_all_anomalies():
                        f.write(f"  [{anomaly.severity.value}] {anomaly.anomaly_type.value}\n")
                        f.write(f"    Part: {anomaly.part_number or 'N/A'}\n")
                        f.write(f"    Issue: {anomaly.description}\n")
                        
                        overcharge = self._calculate_overcharge_amount(anomaly)
                        if overcharge:
                            f.write(f"    Overcharge: {overcharge}\n")
                        
                        f.write("\n")
                    
                    f.write("\n")
        
        return {
            'total_anomalies': total_anomalies,
            'critical_anomalies': critical_anomalies,
            'warning_anomalies': total_anomalies - critical_anomalies,
            'invoices_processed': total_invoices,
            'output_path': str(output_path)
        }
    
    def _extract_line_item_details(self, anomaly: ValidationAnomaly) -> Dict[str, str]:
        """Extract line item details from anomaly."""
        details = anomaly.details or {}
        return {
            'description': details.get('description', ''),
            'rate': format_currency(details.get('price', details.get('invoice_price', ''))) if details.get('price') or details.get('invoice_price') else '',
            'quantity': str(details.get('quantity', '')) if details.get('quantity') else ''
        }
    
    def _calculate_overcharge_amount(self, anomaly: ValidationAnomaly) -> str:
        """Calculate overcharge amount from anomaly details."""
        if anomaly.anomaly_type != AnomalyType.PRICE_DISCREPANCY:
            return ''
        
        details = anomaly.details or {}
        difference = details.get('difference_amount')
        if difference:
            return format_currency(difference)
        return ''
    
    def _calculate_total_impact(self, anomaly: ValidationAnomaly) -> str:
        """Calculate total financial impact from anomaly details."""
        details = anomaly.details or {}
        total_impact = details.get('total_impact')
        if total_impact:
            return format_currency(total_impact)
        return ''


class InteractivePartDiscovery:
    """Handles interactive part discovery workflow."""
    
    def __init__(self, db_manager: DatabaseManager, validation_config: ValidationConfiguration):
        """
        Initialize interactive part discovery.
        
        Args:
            db_manager: Database manager for part operations
            validation_config: Validation configuration
        """
        self.db_manager = db_manager
        self.config = validation_config
        self.prompt = PartDiscoveryPrompt()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def handle_unknown_parts(self, unknown_parts: List[Dict[str, Any]]) -> List[PartDiscoveryResult]:
        """
        Handle unknown parts through interactive discovery.
        
        Args:
            unknown_parts: List of unknown part information
            
        Returns:
            List of discovery results
        """
        results = []
        
        if not unknown_parts:
            return results
        
        self.logger.info(f"Starting interactive discovery for {len(unknown_parts)} unknown parts")
        
        # Group parts by part number to avoid duplicates
        unique_parts = {}
        for part_info in unknown_parts:
            part_number = part_info['part_number']
            if part_number not in unique_parts:
                unique_parts[part_number] = part_info
        
        for part_number, part_info in unique_parts.items():
            try:
                result = self._discover_single_part(part_info)
                results.append(result)
                
                # Check if user wants to stop discovery
                if not result.continue_processing:
                    self.logger.info("User requested to stop part discovery")
                    break
                    
            except Exception as e:
                self.logger.exception(f"Error during discovery of part {part_number}: {e}")
                results.append(PartDiscoveryResult(
                    action='error',
                    continue_processing=True
                ))
        
        return results
    
    def _discover_single_part(self, part_info: Dict[str, Any]) -> PartDiscoveryResult:
        """
        Discover a single unknown part interactively.
        
        Args:
            part_info: Information about the unknown part
            
        Returns:
            Discovery result
        """
        part_number = part_info['part_number']
        discovered_price = part_info.get('discovered_price')
        
        # Generate price suggestions
        price_suggestions = []
        if discovered_price:
            price_suggestions = suggest_authorized_price(
                part_number, Decimal(str(discovered_price)), self.db_manager
            )
        
        # Present part information and get user decision
        decision = self.prompt.prompt_for_unknown_part(
            part_number=part_number,
            description=part_info.get('description', ''),
            discovered_price=discovered_price,
            invoice_number=part_info.get('invoice_number', ''),
            price_suggestions=price_suggestions
        )
        
        if decision['action'] == 'add':
            # Add the part to database
            new_part = Part(
                part_number=part_number,
                description=decision.get('description', part_info.get('description', '')),
                authorized_price=Decimal(str(decision['price'])),
                size=part_info.get('size', ''),
                item_type=part_info.get('item_type', ''),
                active=True
            )
            
            try:
                self.db_manager.add_part(new_part)
                
                # Log the discovery
                discovery_log = PartDiscoveryLog(
                    part_number=part_number,
                    discovered_in_invoice=part_info.get('invoice_number', ''),
                    discovered_price=Decimal(str(discovered_price)) if discovered_price else None,
                    authorized_price=new_part.authorized_price,
                    action_taken='added',
                    user_decision=decision.get('reason', ''),
                    discovery_date=part_info.get('first_seen', '')
                )
                self.db_manager.log_part_discovery(discovery_log)
                
                self.logger.info(f"Added new part: {part_number} at ${new_part.authorized_price}")
                
                return PartDiscoveryResult(
                    action='added',
                    part=new_part,
                    continue_processing=True,
                    user_decision=decision.get('reason', ''),
                    discovery_log=discovery_log
                )
                
            except Exception as e:
                self.logger.error(f"Failed to add part {part_number}: {e}")
                return PartDiscoveryResult(
                    action='error',
                    continue_processing=True
                )
        
        elif decision['action'] == 'skip':
            # Log the skip decision
            discovery_log = PartDiscoveryLog(
                part_number=part_number,
                discovered_in_invoice=part_info.get('invoice_number', ''),
                discovered_price=Decimal(str(discovered_price)) if discovered_price else None,
                action_taken='skipped',
                user_decision=decision.get('reason', ''),
                discovery_date=part_info.get('first_seen', '')
            )
            self.db_manager.log_part_discovery(discovery_log)
            
            return PartDiscoveryResult(
                action='skipped',
                continue_processing=True,
                user_decision=decision.get('reason', ''),
                discovery_log=discovery_log
            )
        
        elif decision['action'] == 'skip_all':
            return PartDiscoveryResult(
                action='skip_all',
                continue_processing=False,
                user_decision='User chose to skip all remaining parts'
            )
        
        else:
            return PartDiscoveryResult(
                action='error',
                continue_processing=True
            )


class ValidationWorkflowManager:
    """Manages the complete validation workflow for CLI integration."""
    
    def __init__(self, db_manager: DatabaseManager, 
                 validation_config: Optional[ValidationConfiguration] = None):
        """
        Initialize workflow manager.
        
        Args:
            db_manager: Database manager
            validation_config: Optional validation configuration
        """
        self.db_manager = db_manager
        self.config = validation_config or ValidationConfiguration.from_database_config(db_manager)
        self.validation_engine = ValidationEngine(db_manager, self.config)
        self.report_generator = ValidationReportGenerator(db_manager)
        self.part_discovery = InteractivePartDiscovery(db_manager, self.config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def process_invoices_batch(self, invoice_paths: List[Path], 
                             output_path: Path, 
                             report_format: str = 'csv',
                             interactive_discovery: bool = None) -> Dict[str, Any]:
        """
        Process multiple invoices in batch mode.
        
        Args:
            invoice_paths: List of PDF file paths
            output_path: Path for output report
            report_format: Report format ('csv' or 'txt')
            interactive_discovery: Override for interactive discovery setting
            
        Returns:
            Processing results and statistics
        """
        # Override interactive discovery if specified
        if interactive_discovery is not None:
            self.config.interactive_discovery = interactive_discovery
        
        self.logger.info(f"Starting batch processing of {len(invoice_paths)} invoices")
        
        # Initialize progress tracking
        progress = ProgressTracker(total=len(invoice_paths), description="Processing invoices")
        
        # Process all invoices
        validation_results = []
        unknown_parts_collection = []
        
        for i, invoice_path in enumerate(invoice_paths):
            try:
                progress.update(i, f"Processing {invoice_path.name}")
                
                # Validate single invoice
                result = self.validation_engine.validate_invoice(invoice_path)
                validation_results.append(result)
                
                # Collect unknown parts for batch processing
                if not self.config.interactive_discovery:
                    unknown_parts_collection.extend(result.unknown_parts_discovered)
                
            except Exception as e:
                self.logger.exception(f"Failed to process {invoice_path}: {e}")
                # Continue with next invoice
                continue
        
        progress.finish("Invoice processing completed")
        
        # Handle unknown parts if in interactive mode
        discovery_results = []
        if self.config.interactive_discovery and unknown_parts_collection:
            self.logger.info(f"Starting interactive discovery for {len(unknown_parts_collection)} unknown parts")
            discovery_results = self.part_discovery.handle_unknown_parts(unknown_parts_collection)
        
        # Generate report
        report_stats = self.report_generator.generate_anomaly_report(
            validation_results, output_path, report_format
        )
        
        # Compile final statistics
        processing_stats = {
            'total_invoices': len(invoice_paths),
            'successfully_processed': len([r for r in validation_results if r.processing_successful]),
            'failed_processing': len([r for r in validation_results if not r.processing_successful]),
            'total_anomalies': sum(len(r.get_all_anomalies()) for r in validation_results),
            'critical_anomalies': sum(len(r.critical_anomalies) for r in validation_results),
            'warning_anomalies': sum(len(r.warning_anomalies) for r in validation_results),
            'unknown_parts_discovered': len(unknown_parts_collection),
            'parts_added_during_discovery': len([r for r in discovery_results if r.action == 'added']),
            'average_processing_time': sum(r.processing_duration for r in validation_results) / len(validation_results) if validation_results else 0,
            'report_generated': True,
            'report_path': str(output_path),
            'report_format': report_format
        }
        
        processing_stats.update(report_stats)
        
        self.logger.info(f"Batch processing completed: {processing_stats['successfully_processed']}/{processing_stats['total_invoices']} successful")
        
        return processing_stats
    
    def process_single_invoice(self, invoice_path: Path, 
                             interactive_discovery: bool = None) -> Tuple[InvoiceValidationResult, List[PartDiscoveryResult]]:
        """
        Process a single invoice with optional interactive discovery.
        
        Args:
            invoice_path: Path to PDF file
            interactive_discovery: Override for interactive discovery setting
            
        Returns:
            Tuple of (validation_result, discovery_results)
        """
        # Override interactive discovery if specified
        if interactive_discovery is not None:
            self.config.interactive_discovery = interactive_discovery
        
        self.logger.info(f"Processing single invoice: {invoice_path}")
        
        # Validate invoice
        validation_result = self.validation_engine.validate_invoice(invoice_path)
        
        # Handle unknown parts if needed
        discovery_results = []
        if self.config.interactive_discovery and validation_result.unknown_parts_discovered:
            discovery_results = self.part_discovery.handle_unknown_parts(
                validation_result.unknown_parts_discovered
            )
        
        return validation_result, discovery_results
    
    def get_validation_summary(self, results: List[InvoiceValidationResult]) -> Dict[str, Any]:
        """
        Generate summary statistics from validation results.
        
        Args:
            results: List of validation results
            
        Returns:
            Summary statistics dictionary
        """
        if not results:
            return {'total_invoices': 0}
        
        return {
            'total_invoices': len(results),
            'successful_validations': len([r for r in results if r.processing_successful]),
            'failed_validations': len([r for r in results if not r.processing_successful]),
            'invoices_with_anomalies': len([r for r in results if r.get_all_anomalies()]),
            'invoices_with_critical_issues': len([r for r in results if r.critical_anomalies]),
            'total_anomalies': sum(len(r.get_all_anomalies()) for r in results),
            'critical_anomalies': sum(len(r.critical_anomalies) for r in results),
            'warning_anomalies': sum(len(r.warning_anomalies) for r in results),
            'informational_anomalies': sum(len(r.informational_anomalies) for r in results),
            'unknown_parts_discovered': sum(len(r.unknown_parts_discovered) for r in results),
            'average_processing_time': sum(r.processing_duration for r in results) / len(results),
            'total_processing_time': sum(r.processing_duration for r in results)
        }


def create_validation_workflow(db_manager: DatabaseManager, 
                             config: Optional[ValidationConfiguration] = None) -> ValidationWorkflowManager:
    """
    Factory function to create a validation workflow manager.
    
    Args:
        db_manager: Database manager instance
        config: Optional validation configuration
        
    Returns:
        Configured ValidationWorkflowManager instance
    """
    return ValidationWorkflowManager(db_manager, config)


def format_validation_summary(summary: Dict[str, Any]) -> str:
    """
    Format validation summary for display.
    
    Args:
        summary: Summary statistics dictionary
        
    Returns:
        Formatted summary string
    """
    if summary.get('total_invoices', 0) == 0:
        return "No invoices processed."
    
    lines = [
        f"Validation Summary:",
        f"  Total Invoices: {summary['total_invoices']}",
        f"  Successfully Processed: {summary['successful_validations']}",
        f"  Failed Processing: {summary['failed_validations']}",
        f"",
        f"Anomaly Detection:",
        f"  Invoices with Issues: {summary['invoices_with_anomalies']}",
        f"  Critical Issues: {summary['critical_anomalies']}",
        f"  Warnings: {summary['warning_anomalies']}",
        f"  Informational: {summary['informational_anomalies']}",
        f"",
        f"Part Discovery:",
        f"  Unknown Parts Found: {summary['unknown_parts_discovered']}",
        f"",
        f"Performance:",
        f"  Average Processing Time: {summary['average_processing_time']:.2f}s per invoice",
        f"  Total Processing Time: {summary['total_processing_time']:.2f}s"
    ]
    
    return "\n".join(lines)