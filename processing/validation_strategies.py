"""
Validation strategies for the Invoice Rate Detection System.

This module implements the Strategy pattern for different validation approaches,
allowing for flexible and extensible validation logic.
"""

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Dict, Any, Optional

from processing.models import InvoiceData, LineItem, FormatSection
from processing.validation_models import (
    ValidationResult, ValidationConfiguration, AnomalyType, SeverityLevel
)
from database.models import Part, PartNotFoundError
from database.database import DatabaseManager


logger = logging.getLogger(__name__)


class ValidationStrategy(ABC):
    """
    Abstract base class for validation strategies.
    
    This class defines the interface that all validation strategies must implement,
    following the Strategy pattern for flexible validation approaches.
    """
    
    def __init__(self, config: ValidationConfiguration, db_manager: DatabaseManager):
        """
        Initialize the validation strategy.
        
        Args:
            config: Validation configuration parameters
            db_manager: Database manager for data access
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """
        Perform validation using this strategy.
        
        Args:
            context: Validation context containing data and metadata
            
        Returns:
            List of validation results
        """
        pass
    
    def _create_result(self, is_valid: bool, severity: SeverityLevel, 
                      message: str, anomaly_type: AnomalyType = None,
                      field: str = None, line_number: int = None,
                      details: Dict[str, Any] = None) -> ValidationResult:
        """
        Helper method to create validation results.
        
        Args:
            is_valid: Whether validation passed
            severity: Severity level of the result
            message: Human-readable message
            anomaly_type: Type of anomaly if validation failed
            field: Field name that was validated
            line_number: Line number in source document
            details: Additional details about the validation
            
        Returns:
            ValidationResult instance
        """
        return ValidationResult(
            is_valid=is_valid,
            severity=severity,
            anomaly_type=anomaly_type,
            message=message,
            field=field,
            line_number=line_number,
            details=details or {},
            timestamp=datetime.now()
        )


class PreValidationStrategy(ValidationStrategy):
    """
    Pre-validation strategy for basic file and data accessibility checks.
    
    This strategy performs initial validation to ensure the invoice data
    is accessible and meets basic requirements before detailed validation.
    """
    
    def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """
        Perform pre-validation checks.
        
        Args:
            context: Must contain 'invoice_path' and optionally 'invoice_data'
            
        Returns:
            List of validation results
        """
        results = []
        invoice_path = context.get('invoice_path')
        invoice_data = context.get('invoice_data')
        
        # Validate PDF file accessibility
        if invoice_path:
            pdf_result = self._validate_pdf_accessibility(Path(invoice_path))
            results.append(pdf_result)
            
            if not pdf_result.is_valid:
                return results  # Stop if PDF is not accessible
        
        # Validate basic invoice data structure
        if invoice_data:
            data_result = self._validate_invoice_data_structure(invoice_data)
            results.append(data_result)
        
        return results
    
    def _validate_pdf_accessibility(self, pdf_path: Path) -> ValidationResult:
        """Validate that PDF file is accessible."""
        try:
            if not pdf_path.exists():
                return self._create_result(
                    False, SeverityLevel.CRITICAL,
                    f"PDF file not found: {pdf_path}",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    details={'pdf_path': str(pdf_path), 'error': 'file_not_found'}
                )
            
            if not pdf_path.is_file():
                return self._create_result(
                    False, SeverityLevel.CRITICAL,
                    f"Path is not a file: {pdf_path}",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    details={'pdf_path': str(pdf_path), 'error': 'not_a_file'}
                )
            
            # Check file size (basic sanity check)
            file_size = pdf_path.stat().st_size
            if file_size == 0:
                return self._create_result(
                    False, SeverityLevel.CRITICAL,
                    f"PDF file is empty: {pdf_path}",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    details={'pdf_path': str(pdf_path), 'file_size': file_size}
                )
            
            return self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"PDF file is accessible: {pdf_path}",
                details={'pdf_path': str(pdf_path), 'file_size': file_size}
            )
            
        except Exception as e:
            return self._create_result(
                False, SeverityLevel.CRITICAL,
                f"Error accessing PDF file: {e}",
                AnomalyType.DATA_QUALITY_ISSUE,
                details={'pdf_path': str(pdf_path), 'error': str(e)}
            )
    
    def _validate_invoice_data_structure(self, invoice_data: InvoiceData) -> ValidationResult:
        """Validate basic invoice data structure."""
        if not isinstance(invoice_data, InvoiceData):
            return self._create_result(
                False, SeverityLevel.CRITICAL,
                "Invalid invoice data structure",
                AnomalyType.DATA_QUALITY_ISSUE,
                details={'data_type': type(invoice_data).__name__}
            )
        
        return self._create_result(
            True, SeverityLevel.INFORMATIONAL,
            "Invoice data structure is valid",
            details={'line_items_count': len(invoice_data.line_items)}
        )


class DataQualityValidationStrategy(ValidationStrategy):
    """
    Data quality validation strategy for ensuring extracted data meets standards.
    
    This strategy validates that all required fields are present and properly
    formatted according to business rules.
    """
    
    def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """
        Perform data quality validation.
        
        Args:
            context: Must contain 'invoice_data'
            
        Returns:
            List of validation results
        """
        results = []
        invoice_data = context.get('invoice_data')
        
        if not invoice_data:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                "No invoice data provided for validation",
                AnomalyType.DATA_QUALITY_ISSUE
            ))
            return results
        
        # Validate invoice metadata
        results.extend(self._validate_invoice_metadata(invoice_data))
        
        # Validate line items
        results.extend(self._validate_line_items(invoice_data))
        
        # Validate text extraction completeness
        results.extend(self._validate_text_extraction(invoice_data))
        
        return results
    
    def _validate_invoice_metadata(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """Validate invoice metadata fields."""
        results = []
        
        # Invoice number validation
        if not invoice_data.invoice_number:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                "Invoice number is missing",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='invoice_number'
            ))
        elif not self._is_valid_invoice_number(invoice_data.invoice_number):
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"Invalid invoice number format: {invoice_data.invoice_number}",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='invoice_number',
                details={'invoice_number': invoice_data.invoice_number}
            ))
        else:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"Invoice number is valid: {invoice_data.invoice_number}",
                field='invoice_number'
            ))
        
        # Invoice date validation
        if not invoice_data.invoice_date:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                "Invoice date is missing",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='invoice_date'
            ))
        elif not self._is_valid_invoice_date(invoice_data.invoice_date):
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"Invalid invoice date format: {invoice_data.invoice_date}",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='invoice_date',
                details={'invoice_date': invoice_data.invoice_date}
            ))
        else:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"Invoice date is valid: {invoice_data.invoice_date}",
                field='invoice_date'
            ))
        
        return results
    
    def _validate_line_items(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """Validate line items data quality."""
        results = []
        
        if not invoice_data.line_items:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                "No line items found in invoice",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='line_items'
            ))
            return results
        
        valid_items = 0
        for i, item in enumerate(invoice_data.line_items):
            item_results = self._validate_single_line_item(item, i + 1)
            results.extend(item_results)
            
            if all(r.is_valid for r in item_results):
                valid_items += 1
        
        # Summary result
        if valid_items == 0:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                "No valid line items found",
                AnomalyType.DATA_QUALITY_ISSUE,
                details={'total_items': len(invoice_data.line_items), 'valid_items': valid_items}
            ))
        else:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"Found {valid_items} valid line items out of {len(invoice_data.line_items)}",
                details={'total_items': len(invoice_data.line_items), 'valid_items': valid_items}
            ))
        
        return results
    
    def _validate_single_line_item(self, item: LineItem, line_number: int) -> List[ValidationResult]:
        """Validate a single line item."""
        results = []
        line_prefix = f"Line {line_number}"
        
        # Part number validation
        if not item.item_code:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"{line_prefix}: Part number is missing",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='item_code',
                line_number=line_number
            ))
        elif not self._is_valid_part_number(item.item_code):
            results.append(self._create_result(
                False, SeverityLevel.WARNING,
                f"{line_prefix}: Part number format is unusual: {item.item_code}",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='item_code',
                line_number=line_number,
                details={'part_number': item.item_code}
            ))
        
        # Price validation
        if item.rate is None:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"{line_prefix}: Price is missing",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='rate',
                line_number=line_number
            ))
        elif not self._is_reasonable_price(item.rate):
            results.append(self._create_result(
                False, SeverityLevel.WARNING,
                f"{line_prefix}: Price is outside reasonable range: ${item.rate}",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='rate',
                line_number=line_number,
                details={'price': float(item.rate)}
            ))
        
        # Quantity validation
        if item.quantity is None:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"{line_prefix}: Quantity is missing",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='quantity',
                line_number=line_number
            ))
        elif item.quantity <= 0:
            results.append(self._create_result(
                False, SeverityLevel.WARNING,
                f"{line_prefix}: Quantity is not positive: {item.quantity}",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='quantity',
                line_number=line_number,
                details={'quantity': item.quantity}
            ))
        
        return results
    
    def _validate_text_extraction(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """Validate text extraction completeness."""
        results = []
        
        if not invoice_data.raw_text:
            results.append(self._create_result(
                False, SeverityLevel.WARNING,
                "No raw text available for validation",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='raw_text'
            ))
            return results
        
        text_length = len(invoice_data.raw_text.strip())
        if text_length < 100:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"Extracted text is too short ({text_length} characters), may indicate extraction failure",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='raw_text',
                details={'text_length': text_length}
            ))
        else:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"Text extraction appears complete ({text_length} characters)",
                field='raw_text',
                details={'text_length': text_length}
            ))
        
        return results
    
    def _is_valid_invoice_number(self, invoice_number: str) -> bool:
        """Check if invoice number format is valid."""
        if not invoice_number or not isinstance(invoice_number, str):
            return False
        cleaned = invoice_number.strip()
        return cleaned.isdigit() and len(cleaned) >= 8
    
    def _is_valid_invoice_date(self, invoice_date: str) -> bool:
        """Check if invoice date format is valid."""
        if not invoice_date or not isinstance(invoice_date, str):
            return False
        
        date_patterns = [
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{1,2}/\d{1,2}/\d{4}',  # M/D/YYYY
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, invoice_date.strip()):
                return True
        return False
    
    def _is_valid_part_number(self, part_number: str) -> bool:
        """Check if part number format is valid."""
        if not part_number or not isinstance(part_number, str):
            return False
        cleaned = part_number.strip()
        return bool(re.match(r'^[A-Za-z0-9_\-\.]+$', cleaned)) and len(cleaned) >= 2
    
    def _is_reasonable_price(self, price: Decimal) -> bool:
        """Check if price is within reasonable business ranges."""
        return (self.config.min_reasonable_price <= price <= self.config.max_reasonable_price)


class FormatStructureValidationStrategy(ValidationStrategy):
    """
    Format structure validation strategy for invoice format compliance.
    
    This strategy ensures that invoices follow the required format structure
    with proper SUBTOTAL, FREIGHT, TAX, TOTAL sections and validates that
    the mathematical relationship (Subtotal + Freight + Tax = Total) holds true.
    """
    
    def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """
        Perform format structure validation.
        
        Args:
            context: Must contain 'invoice_data'
            
        Returns:
            List of validation results
        """
        results = []
        invoice_data = context.get('invoice_data')
        
        if not invoice_data:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                "No invoice data provided for format validation",
                AnomalyType.FORMAT_VIOLATION
            ))
            return results
        
        # Validate format sections count
        results.extend(self._validate_format_sections_count(invoice_data))
        
        # Validate format sections content
        results.extend(self._validate_format_sections_content(invoice_data))
        
        # Validate mathematical total calculation (replaces sequence validation)
        results.extend(self._validate_total_calculation(invoice_data))
        
        return results
    
    def _validate_format_sections_count(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """Validate that exactly 4 format sections are present."""
        results = []
        expected_count = len(self.config.required_format_sections)
        actual_count = len(invoice_data.format_sections)
        
        if actual_count != expected_count:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"Expected {expected_count} format sections, found {actual_count}",
                AnomalyType.LINE_COUNT_VIOLATION,
                field='format_sections',
                details={
                    'expected_count': expected_count,
                    'actual_count': actual_count,
                    'found_sections': [s.section_type for s in invoice_data.format_sections]
                }
            ))
        else:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"Correct number of format sections found: {actual_count}",
                field='format_sections',
                details={'section_count': actual_count}
            ))
        
        return results
    
    def _validate_total_calculation(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """
        Validate that Total = Subtotal + Freight + Tax (mathematical validation).
        
        This replaces the old proximity-based sequence validation with actual
        mathematical verification of the invoice totals.
        """
        results = []
        
        # Get all required amounts
        subtotal = invoice_data.get_subtotal_amount()
        freight = invoice_data.get_freight_amount()
        tax = invoice_data.get_tax_amount()
        total = invoice_data.get_total_amount()
        
        # Check if all required sections are present
        missing_sections = []
        if subtotal is None:
            missing_sections.append('SUBTOTAL')
        if freight is None:
            missing_sections.append('FREIGHT')
        if tax is None:
            missing_sections.append('TAX')
        if total is None:
            missing_sections.append('TOTAL')
        
        if missing_sections:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"Missing required format sections: {', '.join(missing_sections)}",
                AnomalyType.FORMAT_VIOLATION,
                field='format_sections',
                details={'missing_sections': missing_sections}
            ))
            return results
        
        # Perform mathematical validation
        expected_total = invoice_data.calculate_expected_total()
        discrepancy = invoice_data.get_total_calculation_discrepancy()
        
        # Use configurable tolerance (default 1 cent)
        tolerance = getattr(self.config, 'total_calculation_tolerance', Decimal('0.01'))
        
        if abs(discrepancy) <= tolerance:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"Total calculation is correct: ${subtotal} + ${freight} + ${tax} = ${total}",
                field='format_sections',
                details={
                    'subtotal': float(subtotal),
                    'freight': float(freight),
                    'tax': float(tax),
                    'expected_total': float(expected_total),
                    'actual_total': float(total),
                    'discrepancy': float(discrepancy),
                    'tolerance': float(tolerance)
                }
            ))
        else:
            # Determine severity based on discrepancy size
            severity = SeverityLevel.CRITICAL if abs(discrepancy) > Decimal('1.00') else SeverityLevel.WARNING
            
            direction = "higher" if discrepancy > 0 else "lower"
            results.append(self._create_result(
                False, severity,
                f"Total calculation error: Expected ${expected_total} (${subtotal} + ${freight} + ${tax}), "
                f"but found ${total} ({direction} by ${abs(discrepancy)})",
                AnomalyType.TOTAL_CALCULATION_ERROR,
                field='format_sections',
                details={
                    'subtotal': float(subtotal),
                    'freight': float(freight),
                    'tax': float(tax),
                    'expected_total': float(expected_total),
                    'actual_total': float(total),
                    'discrepancy': float(discrepancy),
                    'discrepancy_direction': direction,
                    'tolerance': float(tolerance)
                }
            ))
        
        return results
    
    def _validate_format_sections_content(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """Validate format sections have valid numeric content."""
        results = []
        
        for i, section in enumerate(invoice_data.format_sections):
            if section.amount is None:
                results.append(self._create_result(
                    False, SeverityLevel.CRITICAL,
                    f"{section.section_type} section has no amount",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    field='format_sections',
                    line_number=section.line_number,
                    details={'section_type': section.section_type, 'position': i + 1}
                ))
            elif section.amount < 0:
                results.append(self._create_result(
                    False, SeverityLevel.WARNING,
                    f"{section.section_type} section has negative amount: ${section.amount}",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    field='format_sections',
                    line_number=section.line_number,
                    details={'section_type': section.section_type, 'amount': float(section.amount)}
                ))
            else:
                results.append(self._create_result(
                    True, SeverityLevel.INFORMATIONAL,
                    f"{section.section_type} section is valid: ${section.amount}",
                    field='format_sections',
                    details={'section_type': section.section_type, 'amount': float(section.amount)}
                ))
        
        return results


class PartsLookupValidationStrategy(ValidationStrategy):
    """
    Parts lookup validation strategy for verifying parts exist in database.
    
    This strategy checks that all line item parts exist in the master parts
    database and handles unknown part discovery.
    """
    
    def __init__(self, config: ValidationConfiguration, db_manager: DatabaseManager):
        super().__init__(config, db_manager)
        self.parts_cache = {}  # Simple cache for performance
    
    def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """
        Perform parts lookup validation.
        
        Args:
            context: Must contain 'invoice_data' and optionally 'unknown_parts_collection'
            
        Returns:
            List of validation results
        """
        results = []
        invoice_data = context.get('invoice_data')
        unknown_parts_collection = context.get('unknown_parts_collection', [])
        
        if not invoice_data:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                "No invoice data provided for parts lookup",
                AnomalyType.DATA_QUALITY_ISSUE
            ))
            return results
        
        # Get all unique part numbers from line items
        part_numbers = set()
        for item in invoice_data.get_valid_line_items():
            if item.item_code:
                part_numbers.add(item.item_code)
        
        if not part_numbers:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                "No valid part numbers found in invoice",
                AnomalyType.DATA_QUALITY_ISSUE
            ))
            return results
        
        # Batch lookup parts
        found_parts, missing_parts = self._batch_lookup_parts(part_numbers)
        
        # Process found parts
        for part_number in found_parts:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"Part found in database: {part_number}",
                field='item_code',
                details={'part_number': part_number, 'authorized_price': float(found_parts[part_number].authorized_price)}
            ))
        
        # Process missing parts
        for part_number in missing_parts:
            # Collect unknown part information
            part_info = self._collect_unknown_part_info(part_number, invoice_data)
            unknown_parts_collection.append(part_info)
            
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"Part not found in database: {part_number}",
                AnomalyType.MISSING_PART,
                field='item_code',
                details={'part_number': part_number, 'discovered_info': part_info}
            ))
        
        # Summary result
        total_parts = len(part_numbers)
        found_count = len(found_parts)
        missing_count = len(missing_parts)
        
        if missing_count > 0:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                f"Parts lookup failed: {missing_count} unknown parts out of {total_parts}",
                AnomalyType.MISSING_PART,
                details={
                    'total_parts': total_parts,
                    'found_parts': found_count,
                    'missing_parts': missing_count,
                    'unknown_part_numbers': list(missing_parts)
                }
            ))
        else:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"All {total_parts} parts found in database",
                details={'total_parts': total_parts, 'found_parts': found_count}
            ))
        
        return results
    
    def _batch_lookup_parts(self, part_numbers: set) -> tuple[Dict[str, Part], set]:
        """
        Batch lookup parts in database with caching.
        
        Args:
            part_numbers: Set of part numbers to lookup
            
        Returns:
            Tuple of (found_parts_dict, missing_parts_set)
        """
        found_parts = {}
        missing_parts = set()
        
        # Check cache first
        uncached_parts = []
        for part_number in part_numbers:
            if part_number in self.parts_cache:
                if self.parts_cache[part_number] is not None:
                    found_parts[part_number] = self.parts_cache[part_number]
                else:
                    missing_parts.add(part_number)
            else:
                uncached_parts.append(part_number)
        
        # Lookup uncached parts
        for part_number in uncached_parts:
            try:
                part = self.db_manager.get_part(part_number)
                found_parts[part_number] = part
                self.parts_cache[part_number] = part
            except PartNotFoundError:
                missing_parts.add(part_number)
                self.parts_cache[part_number] = None  # Cache the miss
            except Exception as e:
                self.logger.error(f"Error looking up part {part_number}: {e}")
                missing_parts.add(part_number)
        
        return found_parts, missing_parts
    
    def _collect_unknown_part_info(self, part_number: str, invoice_data: InvoiceData) -> Dict[str, Any]:
        """Collect information about an unknown part for later processing."""
        # Find the line item with this part number
        for item in invoice_data.line_items:
            if item.item_code == part_number:
                return {
                    'part_number': part_number,
                    'invoice_number': invoice_data.invoice_number,
                    'invoice_date': invoice_data.invoice_date,
                    'description': item.description,
                    'discovered_price': float(item.rate) if item.rate else None,
                    'quantity': item.quantity,
                    'size': item.size,
                    'item_type': item.item_type,
                    'first_seen': datetime.now().isoformat()
                }
        
        # Fallback if not found in line items
        return {
            'part_number': part_number,
            'invoice_number': invoice_data.invoice_number,
            'invoice_date': invoice_data.invoice_date,
            'first_seen': datetime.now().isoformat()
        }