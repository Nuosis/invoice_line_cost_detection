"""
Simple Validation Engine for Invoice Rate Detection System.

This module provides a streamlined validation engine that:
1. Accepts ONLY the PDF extraction JSON format
2. Validates each part against the database
3. Handles interactive part discovery for unknown parts
4. Returns the input JSON with an added 'error_lines' array

No complex data model conversions - works directly with the extraction JSON.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from database.database import DatabaseManager
from database.models import Part


class ValidationEngine:
    """
    Simple validation engine that works directly with PDF extraction JSON.
    
    Input: PDF extraction JSON with parts array
    Output: Same JSON with added 'error_lines' array for failed validations
    """
    
    def __init__(self, db_manager: DatabaseManager, interactive_mode: bool = False):
        """
        Initialize the validation engine.
        
        Args:
            db_manager: Database manager for parts lookup
            interactive_mode: Enable interactive discovery for unknown parts
        """
        self.db_manager = db_manager
        self.interactive_mode = interactive_mode
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def validate_invoice_json(self, extraction_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate invoice extraction JSON and return with error_lines added.
        
        Args:
            extraction_json: The PDF extraction JSON with parts array
            
        Returns:
            Same JSON with added 'error_lines' array for failed validations
        """
        # Make a copy to avoid modifying the original
        result_json = extraction_json.copy()
        result_json['error_lines'] = []
        
        parts = extraction_json.get('parts', [])
        if not parts:
            self.logger.warning("No parts found in extraction JSON")
            return result_json
            
        self.logger.info(f"Validating {len(parts)} parts from invoice {extraction_json.get('invoice_metadata', {}).get('invoice_number', 'UNKNOWN')}")
        
        # Track unknown parts for interactive discovery
        unknown_parts = []
        
        for part_data in parts:
            database_fields = part_data.get('database_fields', {})
            lineitem_fields = part_data.get('lineitem_fields', {})
            
            # Validate this part
            validation_result = self._validate_single_part(database_fields, lineitem_fields)
            
            if validation_result['status'] == 'unknown_part':
                unknown_parts.append({
                    'part_data': part_data,
                    'validation_result': validation_result
                })
            elif validation_result['status'] == 'failed':
                # Add to error_lines with enhanced financial details
                qty = lineitem_fields.get('quantity', 1)  # Default to 1 if not found
                expected_price = validation_result.get('expected_price', 0)
                actual_price = database_fields.get('authorized_price', 0)
                
                error_line = {
                    'line_number': lineitem_fields.get('line_number'),
                    'part_number': database_fields.get('part_number'),
                    'description': database_fields.get('description'),
                    'qty': qty,
                    'expected_price': expected_price,
                    'actual_price': actual_price,
                    'expected_total': round(float(qty * expected_price), 2) if expected_price else 0,
                    'actual_total': round(float(qty * actual_price), 2) if actual_price else 0,
                    'error_type': validation_result.get('error_type'),
                    'error_message': validation_result.get('message'),
                    'raw_text': lineitem_fields.get('raw_text')
                }
                result_json['error_lines'].append(error_line)
        
        # Handle unknown parts
        if unknown_parts:
            if self.interactive_mode:
                self._handle_unknown_parts_interactive(unknown_parts, result_json)
            else:
                self._handle_unknown_parts_batch(unknown_parts, result_json)
        
        # Add validation summary
        result_json['validation_summary'] = {
            'total_parts': len(parts),
            'passed_parts': len(parts) - len(result_json['error_lines']) - len(unknown_parts),
            'failed_parts': len(result_json['error_lines']),
            'unknown_parts': len(unknown_parts),
            'interactive_mode': self.interactive_mode
        }
        
        self.logger.info(f"Validation complete: {result_json['validation_summary']}")
        return result_json
    
    def _validate_single_part(self, database_fields: Dict[str, Any], lineitem_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single part against the database.
        
        Args:
            database_fields: Part data ready for database operations
            lineitem_fields: Original line item data from PDF
            
        Returns:
            Validation result dict with status and details
        """
        part_number = database_fields.get('part_number')
        description = database_fields.get('description')
        item_type = database_fields.get('item_type')
        actual_price = database_fields.get('authorized_price')
        
        if actual_price is not None:
            actual_price = Decimal(str(actual_price))
        
        try:
            # Try to find part by composite key (item_type, description, part_number)
            existing_part = self.db_manager.find_part_by_components(
                item_type, description, part_number
            )
            
            if not existing_part and part_number:
                # Fallback to part number lookup
                try:
                    existing_part = self.db_manager.get_part(part_number)
                except Exception:
                    existing_part = None
            
            if existing_part:
                # Part found - validate price
                expected_price = existing_part.authorized_price
                
                if actual_price is None:
                    return {
                        'status': 'failed',
                        'error_type': 'missing_price',
                        'message': 'Price missing from invoice line',
                        'expected_price': float(expected_price)
                    }
                
                if expected_price == actual_price:
                    return {
                        'status': 'passed',
                        'message': f'Price matches expected: ${actual_price}',
                        'expected_price': float(expected_price)
                    }
                else:
                    return {
                        'status': 'failed',
                        'error_type': 'price_mismatch',
                        'message': f'Price mismatch: expected ${expected_price}, found ${actual_price}',
                        'expected_price': float(expected_price)
                    }
            else:
                # Part not found
                return {
                    'status': 'unknown_part',
                    'error_type': 'unknown_part',
                    'message': f'Part not found in database: {part_number or description}',
                    'discovered_price': float(actual_price) if actual_price else None
                }
                
        except Exception as e:
            self.logger.error(f"Error validating part {part_number}: {e}")
            return {
                'status': 'failed',
                'error_type': 'validation_error',
                'message': f'Validation error: {str(e)}'
            }
    
    def _handle_unknown_parts_interactive(self, unknown_parts: List[Dict], result_json: Dict[str, Any]):
        """
        Handle unknown parts with interactive discovery.
        
        Args:
            unknown_parts: List of unknown part data and validation results
            result_json: Result JSON to update
        """
        self.logger.info(f"Interactive discovery for {len(unknown_parts)} unknown parts")
        
        for unknown_part in unknown_parts:
            part_data = unknown_part['part_data']
            database_fields = part_data['database_fields']
            lineitem_fields = part_data['lineitem_fields']
            
            # For now, simulate interactive discovery by auto-adding
            # In real implementation, this would prompt the user
            try:
                new_part = Part(
                    part_number=database_fields.get('part_number'),
                    authorized_price=Decimal(str(database_fields['authorized_price'])),
                    description=database_fields.get('description'),
                    item_type=database_fields.get('item_type'),
                    source='discovered',
                    first_seen_invoice=result_json.get('invoice_metadata', {}).get('invoice_number'),
                    notes='Auto-discovered during validation'
                )
                
                created_part = self.db_manager.create_part(new_part)
                self.logger.info(f"Added unknown part: {new_part.part_number or new_part.description}")
                
            except Exception as e:
                self.logger.error(f"Failed to add unknown part: {e}")
                # Add to error_lines since we couldn't add it
                qty = lineitem_fields.get('quantity', 1)  # Default to 1 if not found
                actual_price = database_fields.get('authorized_price', 0)
                
                error_line = {
                    'line_number': lineitem_fields.get('line_number'),
                    'part_number': database_fields.get('part_number'),
                    'description': database_fields.get('description'),
                    'qty': qty,
                    'expected_price': None,
                    'actual_price': actual_price,
                    'expected_total': 0,  # No expected price for unknown parts
                    'actual_total': round(float(qty * actual_price), 2) if actual_price else 0,
                    'error_type': 'unknown_part_add_failed',
                    'error_message': f'Failed to add unknown part: {str(e)}',
                    'raw_text': lineitem_fields.get('raw_text')
                }
                result_json['error_lines'].append(error_line)
    
    def _handle_unknown_parts_batch(self, unknown_parts: List[Dict], result_json: Dict[str, Any]):
        """
        Handle unknown parts in batch mode (add to error_lines).
        
        Args:
            unknown_parts: List of unknown part data and validation results
            result_json: Result JSON to update
        """
        self.logger.info(f"Batch mode: adding {len(unknown_parts)} unknown parts to error_lines")
        
        for unknown_part in unknown_parts:
            part_data = unknown_part['part_data']
            database_fields = part_data['database_fields']
            lineitem_fields = part_data['lineitem_fields']
            validation_result = unknown_part['validation_result']
            
            qty = lineitem_fields.get('quantity', 1)  # Default to 1 if not found
            actual_price = database_fields.get('authorized_price', 0)
            
            error_line = {
                'line_number': lineitem_fields.get('line_number'),
                'part_number': database_fields.get('part_number'),
                'description': database_fields.get('description'),
                'qty': qty,
                'expected_price': None,
                'actual_price': actual_price,
                'expected_total': 0,  # No expected price for unknown parts
                'actual_total': round(float(qty * actual_price), 2) if actual_price else 0,
                'error_type': 'unknown_part',
                'error_message': validation_result.get('message'),
                'raw_text': lineitem_fields.get('raw_text')
            }
            result_json['error_lines'].append(error_line)
    
    # Legacy method for backward compatibility with existing CLI code
    def validate_invoice_items(self, line_items: List, validation_mode: str = "parts_based",
                             threshold: Optional[float] = None) -> List:
        """
        Legacy method for backward compatibility.
        
        This method converts the old interface to work with the new JSON-based approach.
        """
        # Convert old line items to extraction JSON format
        extraction_json = {
            'invoice_metadata': {
                'invoice_number': 'LEGACY',
                'invoice_date': None,
                'total_line_items': len(line_items)
            },
            'parts': []
        }
        
        for i, line_item in enumerate(line_items):
            part_data = {
                'database_fields': {
                    'part_number': getattr(line_item, 'part_number', None),
                    'authorized_price': float(getattr(line_item, 'unit_price', 0)),
                    'description': getattr(line_item, 'description', None),
                    'item_type': None,
                    'source': 'legacy'
                },
                'lineitem_fields': {
                    'line_number': i + 1,
                    'raw_text': f"Legacy line item {i + 1}"
                }
            }
            extraction_json['parts'].append(part_data)
        
        # Validate using new method
        result_json = self.validate_invoice_json(extraction_json)
        
        # Convert back to old ProcessingResult format
        from processing.models import ProcessingResult, InvoiceLineItem
        results = []
        
        for i, part_data in enumerate(extraction_json['parts']):
            line_item = line_items[i]
            
            # Check if this line is in error_lines
            is_error = any(
                error['line_number'] == i + 1 
                for error in result_json.get('error_lines', [])
            )
            
            if is_error:
                error = next(
                    error for error in result_json.get('error_lines', [])
                    if error['line_number'] == i + 1
                )
                result = ProcessingResult.create_failed(
                    line_item,
                    issue_type=error.get('error_type', 'VALIDATION_FAILED'),
                    notes=error.get('error_message', 'Validation failed')
                )
            else:
                result = ProcessingResult.create_passed(
                    line_item,
                    notes="Validation passed"
                )
            
            results.append(result)
        
        return results