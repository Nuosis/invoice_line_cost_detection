"""
Extended validation strategies for the Invoice Rate Detection System.

This module contains additional validation strategies including price validation
and business rules validation.
"""

import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional

from processing.models import InvoiceData, LineItem
from processing.validation_models import (
    ValidationResult, ValidationConfiguration, AnomalyType, SeverityLevel,
    PriceSuggestion
)
from processing.validation_strategies import ValidationStrategy
from database.models import Part, PartNotFoundError
from database.database import DatabaseManager


logger = logging.getLogger(__name__)


class PriceComparisonValidationStrategy(ValidationStrategy):
    """
    Price comparison validation strategy for detecting price discrepancies.
    
    This strategy compares invoice prices against authorized prices from the
    master parts database and identifies pricing anomalies.
    """
    
    def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """
        Perform price comparison validation.
        
        Args:
            context: Must contain 'invoice_data' and 'found_parts'
            
        Returns:
            List of validation results
        """
        results = []
        invoice_data = context.get('invoice_data')
        found_parts = context.get('found_parts', {})
        
        if not invoice_data:
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL,
                "No invoice data provided for price validation",
                AnomalyType.DATA_QUALITY_ISSUE
            ))
            return results
        
        if not found_parts:
            results.append(self._create_result(
                False, SeverityLevel.WARNING,
                "No parts data available for price comparison",
                AnomalyType.DATA_QUALITY_ISSUE
            ))
            return results
        
        # Validate prices for each line item
        for item in invoice_data.get_valid_line_items():
            if item.item_code in found_parts:
                part = found_parts[item.item_code]
                price_result = self._validate_item_price(item, part)
                results.append(price_result)
        
        # Generate summary
        price_discrepancies = [r for r in results if not r.is_valid and r.anomaly_type == AnomalyType.PRICE_DISCREPANCY]
        if price_discrepancies:
            critical_discrepancies = [r for r in price_discrepancies if r.severity == SeverityLevel.CRITICAL]
            results.append(self._create_result(
                False, SeverityLevel.CRITICAL if critical_discrepancies else SeverityLevel.WARNING,
                f"Found {len(price_discrepancies)} price discrepancies ({len(critical_discrepancies)} critical)",
                AnomalyType.PRICE_DISCREPANCY,
                details={
                    'total_discrepancies': len(price_discrepancies),
                    'critical_discrepancies': len(critical_discrepancies),
                    'warning_discrepancies': len(price_discrepancies) - len(critical_discrepancies)
                }
            ))
        else:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"All {len([r for r in results if r.is_valid])} prices match authorized amounts",
                details={'validated_items': len([r for r in results if r.is_valid])}
            ))
        
        return results
    
    def _validate_item_price(self, item: LineItem, part: Part) -> ValidationResult:
        """
        Validate a single line item price against authorized price.
        
        Args:
            item: Line item to validate
            part: Corresponding part from database
            
        Returns:
            ValidationResult for this price comparison
        """
        if item.rate is None:
            return self._create_result(
                False, SeverityLevel.CRITICAL,
                f"No price available for part {item.item_code}",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='rate',
                line_number=item.line_number,
                details={'part_number': item.item_code}
            )
        
        invoice_price = item.rate
        authorized_price = part.authorized_price
        price_difference = abs(invoice_price - authorized_price)
        
        # Check if prices match within tolerance
        if price_difference <= self.config.price_tolerance:
            return self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"Price matches authorized amount for {item.item_code}: ${invoice_price}",
                field='rate',
                line_number=item.line_number,
                details={
                    'part_number': item.item_code,
                    'invoice_price': float(invoice_price),
                    'authorized_price': float(authorized_price),
                    'difference': float(price_difference)
                }
            )
        
        # Calculate percentage difference
        percentage_difference = (price_difference / authorized_price) * 100 if authorized_price > 0 else 0
        
        # Determine severity based on thresholds
        severity = self._determine_price_discrepancy_severity(price_difference, percentage_difference)
        
        # Create detailed message
        direction = "higher" if invoice_price > authorized_price else "lower"
        message = (f"Price discrepancy for {item.item_code}: "
                  f"Invoice ${invoice_price} vs Authorized ${authorized_price} "
                  f"({direction} by ${price_difference:.2f}, {percentage_difference:.1f}%)")
        
        return self._create_result(
            False, severity,
            message,
            AnomalyType.PRICE_DISCREPANCY,
            field='rate',
            line_number=item.line_number,
            details={
                'part_number': item.item_code,
                'invoice_price': float(invoice_price),
                'authorized_price': float(authorized_price),
                'difference_amount': float(price_difference),
                'difference_percentage': float(percentage_difference),
                'direction': direction,
                'quantity': item.quantity,
                'total_impact': float(price_difference * (item.quantity or 1))
            }
        )
    
    def _determine_price_discrepancy_severity(self, amount_diff: Decimal, percent_diff: float) -> SeverityLevel:
        """
        Determine severity level based on price discrepancy thresholds.
        
        Args:
            amount_diff: Absolute price difference
            percent_diff: Percentage difference
            
        Returns:
            Appropriate severity level
        """
        # Critical thresholds
        if (amount_diff >= self.config.price_discrepancy_critical_threshold or 
            percent_diff >= self.config.price_percentage_critical_threshold):
            return SeverityLevel.CRITICAL
        
        # Warning thresholds
        if (amount_diff >= self.config.price_discrepancy_warning_threshold or 
            percent_diff >= self.config.price_percentage_warning_threshold):
            return SeverityLevel.WARNING
        
        # Should not reach here given tolerance check above, but fallback
        return SeverityLevel.WARNING


class BusinessRulesValidationStrategy(ValidationStrategy):
    """
    Business rules validation strategy for applying business-specific rules.
    
    This strategy validates data against business rules such as part number
    formats, price reasonableness, and invoice constraints.
    """
    
    def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """
        Perform business rules validation.
        
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
                "No invoice data provided for business rules validation",
                AnomalyType.DATA_QUALITY_ISSUE
            ))
            return results
        
        # Validate invoice-level business rules
        results.extend(self._validate_invoice_constraints(invoice_data))
        
        # Validate line item business rules
        results.extend(self._validate_line_item_business_rules(invoice_data))
        
        # Validate part number formats
        results.extend(self._validate_part_number_formats(invoice_data))
        
        # Validate price reasonableness
        results.extend(self._validate_price_reasonableness(invoice_data))
        
        return results
    
    def _validate_invoice_constraints(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """Validate invoice-level business constraints."""
        results = []
        
        # Date range validation
        if invoice_data.invoice_date:
            date_result = self._validate_invoice_date_range(invoice_data.invoice_date)
            results.append(date_result)
        
        # Line item count validation
        line_item_count = len(invoice_data.line_items)
        if line_item_count > self.config.max_line_items_per_invoice:
            results.append(self._create_result(
                False, SeverityLevel.WARNING,
                f"Unusually high number of line items: {line_item_count} (max recommended: {self.config.max_line_items_per_invoice})",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='line_items',
                details={'line_item_count': line_item_count, 'max_recommended': self.config.max_line_items_per_invoice}
            ))
        else:
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"Line item count is within normal range: {line_item_count}",
                field='line_items',
                details={'line_item_count': line_item_count}
            ))
        
        # Total amount validation
        total_amount = invoice_data.get_total_amount()
        if total_amount and total_amount > Decimal('10000.00'):
            results.append(self._create_result(
                True, SeverityLevel.INFORMATIONAL,
                f"High-value invoice detected: ${total_amount}",
                field='total_amount',
                details={'total_amount': float(total_amount)}
            ))
        
        return results
    
    def _validate_invoice_date_range(self, invoice_date: str) -> ValidationResult:
        """Validate invoice date is within reasonable range."""
        try:
            # Parse date (assuming MM/DD/YYYY format)
            date_parts = invoice_date.split('/')
            if len(date_parts) == 3:
                month, day, year = map(int, date_parts)
                parsed_date = datetime(year, month, day).date()
                
                today = datetime.now().date()
                
                # Check if date is too far in the future
                if parsed_date > today + timedelta(days=30):
                    return self._create_result(
                        False, SeverityLevel.WARNING,
                        f"Invoice date is far in the future: {invoice_date}",
                        AnomalyType.DATA_QUALITY_ISSUE,
                        field='invoice_date',
                        details={'invoice_date': invoice_date, 'days_in_future': (parsed_date - today).days}
                    )
                
                # Check if date is too old
                max_age_days = self.config.max_invoice_age_days
                if parsed_date < today - timedelta(days=max_age_days):
                    return self._create_result(
                        True, SeverityLevel.INFORMATIONAL,
                        f"Invoice date is over {max_age_days} days old: {invoice_date}",
                        field='invoice_date',
                        details={'invoice_date': invoice_date, 'age_days': (today - parsed_date).days}
                    )
                
                return self._create_result(
                    True, SeverityLevel.INFORMATIONAL,
                    f"Invoice date is within acceptable range: {invoice_date}",
                    field='invoice_date',
                    details={'invoice_date': invoice_date}
                )
            
        except (ValueError, TypeError) as e:
            return self._create_result(
                False, SeverityLevel.WARNING,
                f"Could not parse invoice date for range validation: {invoice_date}",
                AnomalyType.DATA_QUALITY_ISSUE,
                field='invoice_date',
                details={'invoice_date': invoice_date, 'error': str(e)}
            )
        
        return self._create_result(
            False, SeverityLevel.WARNING,
            f"Invalid invoice date format for range validation: {invoice_date}",
            AnomalyType.DATA_QUALITY_ISSUE,
            field='invoice_date',
            details={'invoice_date': invoice_date}
        )
    
    def _validate_line_item_business_rules(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """Validate line item business rules."""
        results = []
        
        for item in invoice_data.line_items:
            if not item.is_valid():
                continue
            
            # Validate quantity reasonableness
            if item.quantity and item.quantity > 100:
                results.append(self._create_result(
                    False, SeverityLevel.WARNING,
                    f"Unusually high quantity for {item.item_code}: {item.quantity}",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    field='quantity',
                    line_number=item.line_number,
                    details={'part_number': item.item_code, 'quantity': item.quantity}
                ))
            
            # Validate total calculation if available
            if item.rate and item.quantity and item.total:
                expected_total = item.rate * item.quantity
                actual_total = item.total
                difference = abs(expected_total - actual_total)
                
                if difference > Decimal('0.01'):  # Allow for rounding differences
                    results.append(self._create_result(
                        False, SeverityLevel.WARNING,
                        f"Line total calculation mismatch for {item.item_code}: "
                        f"Expected ${expected_total}, Found ${actual_total}",
                        AnomalyType.DATA_QUALITY_ISSUE,
                        field='total',
                        line_number=item.line_number,
                        details={
                            'part_number': item.item_code,
                            'rate': float(item.rate),
                            'quantity': item.quantity,
                            'expected_total': float(expected_total),
                            'actual_total': float(actual_total),
                            'difference': float(difference)
                        }
                    ))
        
        return results
    
    def _validate_part_number_formats(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """Validate part number formats according to business rules."""
        results = []
        
        # Common part number patterns
        common_patterns = [
            (r'^[A-Z]{2}\d{4}[A-Z]*$', 'Standard format (e.g., GS0448, GP0171NAVY)'),
            (r'^[A-Z]+\d+[A-Z]*$', 'Alphanumeric format (e.g., ABC123XYZ)'),
            (r'^[A-Z]+\-\d+$', 'Hyphenated format (e.g., PART-123)'),
        ]
        
        for item in invoice_data.get_valid_line_items():
            if not item.item_code:
                continue
            
            part_number = item.item_code.strip()
            
            # Basic format validation
            if not re.match(r'^[A-Za-z0-9_\-\.]+$', part_number):
                results.append(self._create_result(
                    False, SeverityLevel.WARNING,
                    f"Part number contains invalid characters: {part_number}",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    field='item_code',
                    line_number=item.line_number,
                    details={'part_number': part_number}
                ))
                continue
            
            # Length validation
            if len(part_number) < 2 or len(part_number) > 20:
                results.append(self._create_result(
                    False, SeverityLevel.WARNING,
                    f"Part number length unusual: {part_number} ({len(part_number)} characters)",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    field='item_code',
                    line_number=item.line_number,
                    details={'part_number': part_number, 'length': len(part_number)}
                ))
                continue
            
            # Pattern matching
            pattern_matched = False
            for pattern, description in common_patterns:
                if re.match(pattern, part_number.upper()):
                    pattern_matched = True
                    results.append(self._create_result(
                        True, SeverityLevel.INFORMATIONAL,
                        f"Part number follows {description}: {part_number}",
                        field='item_code',
                        line_number=item.line_number,
                        details={'part_number': part_number, 'pattern': description}
                    ))
                    break
            
            if not pattern_matched:
                results.append(self._create_result(
                    True, SeverityLevel.INFORMATIONAL,
                    f"Part number format is unusual but valid: {part_number}",
                    field='item_code',
                    line_number=item.line_number,
                    details={'part_number': part_number}
                ))
        
        return results
    
    def _validate_price_reasonableness(self, invoice_data: InvoiceData) -> List[ValidationResult]:
        """Validate that prices are within reasonable business ranges."""
        results = []
        
        for item in invoice_data.get_valid_line_items():
            if not item.rate:
                continue
            
            price = item.rate
            
            # Minimum price validation
            if price <= self.config.min_reasonable_price:
                results.append(self._create_result(
                    False, SeverityLevel.CRITICAL,
                    f"Price is unreasonably low for {item.item_code}: ${price}",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    field='rate',
                    line_number=item.line_number,
                    details={'part_number': item.item_code, 'price': float(price), 'min_reasonable': float(self.config.min_reasonable_price)}
                ))
                continue
            
            # Maximum price validation
            if price > self.config.max_reasonable_price:
                results.append(self._create_result(
                    False, SeverityLevel.WARNING,
                    f"Price is unusually high for {item.item_code}: ${price} (exceeds ${self.config.max_reasonable_price})",
                    AnomalyType.DATA_QUALITY_ISSUE,
                    field='rate',
                    line_number=item.line_number,
                    details={'part_number': item.item_code, 'price': float(price), 'max_reasonable': float(self.config.max_reasonable_price)}
                ))
                continue
            
            # High-precision price validation for expensive items
            if price > Decimal('100.00') and price.as_tuple().exponent < -2:
                results.append(self._create_result(
                    True, SeverityLevel.INFORMATIONAL,
                    f"High-precision price for expensive item {item.item_code}: ${price}",
                    field='rate',
                    line_number=item.line_number,
                    details={'part_number': item.item_code, 'price': float(price), 'precision': abs(price.as_tuple().exponent)}
                ))
            else:
                results.append(self._create_result(
                    True, SeverityLevel.INFORMATIONAL,
                    f"Price is within reasonable range for {item.item_code}: ${price}",
                    field='rate',
                    line_number=item.line_number,
                    details={'part_number': item.item_code, 'price': float(price)}
                ))
        
        return results


def suggest_authorized_price(part_number: str, discovered_price: Decimal, 
                           db_manager: DatabaseManager) -> List[PriceSuggestion]:
    """
    Generate price suggestions for unknown parts.
    
    Args:
        part_number: Unknown part number
        discovered_price: Price found in invoice
        db_manager: Database manager for similar parts lookup
        
    Returns:
        List of price suggestions ordered by confidence
    """
    suggestions = []
    
    # Suggestion 1: Use discovered price
    suggestions.append(PriceSuggestion(
        price=discovered_price,
        confidence=0.7,
        reason=f"Use price found in invoice (${discovered_price})",
        source_data={'source': 'invoice', 'original_price': float(discovered_price)}
    ))
    
    # Suggestion 2: Find similar part numbers
    try:
        similar_parts = find_similar_parts(part_number, db_manager)
        if similar_parts:
            avg_price = sum(p.authorized_price for p in similar_parts) / len(similar_parts)
            suggestions.append(PriceSuggestion(
                price=avg_price,
                confidence=0.8,
                reason=f"Average price of {len(similar_parts)} similar parts (${avg_price:.2f})",
                source_data={
                    'source': 'similar_parts',
                    'similar_count': len(similar_parts),
                    'similar_parts': [p.part_number for p in similar_parts],
                    'price_range': {
                        'min': float(min(p.authorized_price for p in similar_parts)),
                        'max': float(max(p.authorized_price for p in similar_parts))
                    }
                }
            ))
    except Exception as e:
        logger.warning(f"Error finding similar parts for {part_number}: {e}")
    
    # Suggestion 3: Round to common price points
    rounded_price = round_to_common_price_point(discovered_price)
    if rounded_price != discovered_price:
        suggestions.append(PriceSuggestion(
            price=rounded_price,
            confidence=0.6,
            reason=f"Rounded to common price point (${rounded_price})",
            source_data={'source': 'rounding', 'original_price': float(discovered_price)}
        ))
    
    return sorted(suggestions, key=lambda x: x.confidence, reverse=True)


def find_similar_parts(part_number: str, db_manager: DatabaseManager, limit: int = 5) -> List[Part]:
    """
    Find parts with similar part numbers.
    
    Args:
        part_number: Part number to find similar parts for
        db_manager: Database manager
        limit: Maximum number of similar parts to return
        
    Returns:
        List of similar parts
    """
    try:
        # Get all active parts
        all_parts = db_manager.list_parts(active_only=True)
        
        # Simple similarity scoring based on common prefixes/suffixes
        similar_parts = []
        part_upper = part_number.upper()
        
        for part in all_parts:
            similarity_score = calculate_part_similarity(part_upper, part.part_number.upper())
            if similarity_score > 0.5:  # Threshold for similarity
                similar_parts.append((part, similarity_score))
        
        # Sort by similarity score and return top matches
        similar_parts.sort(key=lambda x: x[1], reverse=True)
        return [part for part, score in similar_parts[:limit]]
        
    except Exception as e:
        logger.error(f"Error finding similar parts: {e}")
        return []


def calculate_part_similarity(part1: str, part2: str) -> float:
    """
    Calculate similarity score between two part numbers.
    
    Args:
        part1: First part number
        part2: Second part number
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if part1 == part2:
        return 1.0
    
    # Check for common prefix
    prefix_len = 0
    for i in range(min(len(part1), len(part2))):
        if part1[i] == part2[i]:
            prefix_len += 1
        else:
            break
    
    # Check for common suffix
    suffix_len = 0
    for i in range(1, min(len(part1), len(part2)) + 1):
        if part1[-i] == part2[-i]:
            suffix_len += 1
        else:
            break
    
    # Calculate similarity based on common characters
    max_len = max(len(part1), len(part2))
    common_chars = prefix_len + suffix_len
    
    # Avoid double counting if parts are very short
    if prefix_len + suffix_len > min(len(part1), len(part2)):
        common_chars = min(len(part1), len(part2))
    
    return common_chars / max_len if max_len > 0 else 0.0


def round_to_common_price_point(price: Decimal) -> Decimal:
    """
    Round price to common price points.
    
    Args:
        price: Original price
        
    Returns:
        Rounded price
    """
    # Common rounding rules
    if price < Decimal('1.00'):
        # Round to nearest cent
        return price.quantize(Decimal('0.01'))
    elif price < Decimal('10.00'):
        # Round to nearest 5 cents
        return (price * 20).quantize(Decimal('1')) / 20
    elif price < Decimal('100.00'):
        # Round to nearest 10 cents
        return (price * 10).quantize(Decimal('1')) / 10
    else:
        # Round to nearest dollar
        return price.quantize(Decimal('1'))