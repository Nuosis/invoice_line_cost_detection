"""
Main validation engine for the Invoice Rate Detection System.

This module contains the ValidationEngine class that orchestrates all validation
strategies and provides the main interface for invoice validation.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from processing.models import InvoiceData
from processing.pdf_processor import PDFProcessor
from processing.validation_models import (
    ValidationConfiguration, InvoiceValidationResult, ValidationAnomaly,
    AuditEventType, RecoveryAction, PartDiscoveryResult, SeverityLevel
)
from processing.validation_strategies import (
    PreValidationStrategy, DataQualityValidationStrategy, 
    FormatStructureValidationStrategy, PartsLookupValidationStrategy
)
from processing.validation_strategies_extended import (
    PriceComparisonValidationStrategy, BusinessRulesValidationStrategy
)
from processing.exceptions import PDFProcessingError
from processing.part_discovery_service import InteractivePartDiscoveryService
from database.models import Part, PartDiscoveryLog
from database.database import DatabaseManager


logger = logging.getLogger(__name__)


class ValidationErrorHandler:
    """Handles validation errors with appropriate recovery strategies."""
    
    def __init__(self, config: ValidationConfiguration, db_manager: DatabaseManager):
        """
        Initialize error handler.
        
        Args:
            config: Validation configuration
            db_manager: Database manager for part operations
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def handle_critical_error(self, error_results: List, context: Dict[str, Any]) -> RecoveryAction:
        """
        Handle critical validation errors.
        
        Args:
            error_results: List of critical validation results
            context: Validation context
            
        Returns:
            RecoveryAction indicating how to proceed
        """
        # Check for unknown parts errors
        missing_part_errors = [r for r in error_results if r.anomaly_type and r.anomaly_type.value == 'MISSING_PART']
        if missing_part_errors and self.config.interactive_discovery:
            return self._handle_unknown_parts_interactive(missing_part_errors, context)
        elif missing_part_errors and self.config.batch_collect_unknown_parts:
            return self._handle_unknown_parts_batch(missing_part_errors, context)
        
        # Check for format violations
        format_errors = [r for r in error_results if r.anomaly_type and r.anomaly_type.value in ['FORMAT_VIOLATION', 'LINE_COUNT_VIOLATION']]
        if format_errors:
            return RecoveryAction(
                action='stop_processing',
                message=f'Critical format violations detected: {len(format_errors)} errors',
                user_intervention_required=True,
                context={'format_errors': [r.message for r in format_errors]}
            )
        
        # Default: stop processing for critical errors
        return RecoveryAction(
            action='stop_processing',
            message=f'Critical validation errors detected: {len(error_results)} errors',
            user_intervention_required=True,
            context={'error_messages': [r.message for r in error_results]}
        )
    
    def _handle_unknown_parts_interactive(self, missing_part_errors: List, context: Dict[str, Any]) -> RecoveryAction:
        """Handle unknown parts with interactive discovery."""
        unknown_parts = context.get('unknown_parts_collection', [])
        
        if unknown_parts:
            return RecoveryAction(
                action='interactive_discovery',
                message=f'Found {len(unknown_parts)} unknown parts - interactive discovery required',
                user_intervention_required=True,
                context={'unknown_parts': unknown_parts}
            )
        
        return RecoveryAction(
            action='collect_and_continue',
            message='Unknown parts collected for review',
            user_intervention_required=False
        )
    
    def _handle_unknown_parts_batch(self, missing_part_errors: List, context: Dict[str, Any]) -> RecoveryAction:
        """Handle unknown parts in batch collection mode."""
        unknown_parts = context.get('unknown_parts_collection', [])
        
        return RecoveryAction(
            action='collect_and_continue',
            message=f'Collected {len(unknown_parts)} unknown parts for later review',
            user_intervention_required=False,
            context={'unknown_parts_count': len(unknown_parts)}
        )


class AuditTrailManager:
    """Manages audit trail logging for validation operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize audit trail manager.
        
        Args:
            db_manager: Database manager for logging operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def log_event(self, event_type: AuditEventType, message: str, 
                  invoice_number: str = None, session_id: str = None,
                  event_data: Dict[str, Any] = None):
        """
        Log an audit event.
        
        Args:
            event_type: Type of audit event
            message: Human-readable message
            invoice_number: Related invoice number
            session_id: Processing session ID
            event_data: Additional event data
        """
        try:
            # Log to application logger
            self.logger.info(f"AUDIT [{event_type.value}] {message}", extra={
                'invoice_number': invoice_number,
                'session_id': session_id,
                'event_data': event_data
            })
            
            # Could also log to database audit table if needed
            # For now, we rely on the discovery log for part-related events
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")


class ValidationEngine:
    """
    Main validation engine coordinating all validation phases.
    
    This class orchestrates the complete validation workflow using the Strategy
    pattern for different validation approaches.
    """
    
    def __init__(self, db_manager: DatabaseManager, 
                 config: Optional[ValidationConfiguration] = None):
        """
        Initialize the validation engine.
        
        Args:
            db_manager: Database manager for data access
            config: Validation configuration (uses default if not provided)
        """
        self.db_manager = db_manager
        self.config = config or ValidationConfiguration.from_database_config(db_manager)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize components
        self.pdf_processor = PDFProcessor(logger=self.logger)
        self.audit_manager = AuditTrailManager(db_manager)
        self.error_handler = ValidationErrorHandler(self.config, db_manager)
        self.discovery_service = InteractivePartDiscoveryService(db_manager)
        
        # Initialize validation strategies
        self.validators = {
            'pre_validation': PreValidationStrategy(self.config, db_manager),
            'data_quality': DataQualityValidationStrategy(self.config, db_manager),
            'format_structure': FormatStructureValidationStrategy(self.config, db_manager),
            'parts_lookup': PartsLookupValidationStrategy(self.config, db_manager),
            'price_comparison': PriceComparisonValidationStrategy(self.config, db_manager),
            'business_rules': BusinessRulesValidationStrategy(self.config, db_manager)
        }
        
        self.logger.info("ValidationEngine initialized with all strategies")
    
    def validate_invoice(self, invoice_path: Path, session_id: Optional[str] = None) -> InvoiceValidationResult:
        """
        Validate a single invoice through all validation phases.
        
        Args:
            invoice_path: Path to the PDF invoice file
            session_id: Optional processing session ID
            
        Returns:
            Complete validation result for the invoice
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        start_time = datetime.now()
        
        # Initialize result structure
        result = InvoiceValidationResult(
            invoice_number="",
            invoice_date="",
            invoice_path=str(invoice_path),
            processing_session_id=session_id,
            processing_start_time=start_time
        )
        
        try:
            self.logger.info(f"Starting validation for {invoice_path}")
            self.audit_manager.log_event(
                AuditEventType.VALIDATION_STARTED,
                f"Started validation for {invoice_path}",
                session_id=session_id
            )
            
            # Step 1: Extract invoice data from PDF
            invoice_data = self._extract_invoice_data(invoice_path, result)
            if not invoice_data:
                return self._finalize_result(result, False, "PDF extraction failed")
            
            # Update result with invoice metadata
            result.invoice_number = invoice_data.invoice_number or "UNKNOWN"
            result.invoice_date = invoice_data.invoice_date or "UNKNOWN"
            
            # Step 2: Execute validation phases sequentially
            context = {
                'invoice_path': invoice_path,
                'invoice_data': invoice_data,
                'session_id': session_id,
                'unknown_parts_collection': [],
                'found_parts': {},
                'discovery_service': self.discovery_service
            }
            
            # Execute each validation phase
            validation_successful = self._execute_validation_phases(context, result)
            
            if validation_successful:
                # Categorize all anomalies by severity
                self._categorize_anomalies(result)
                
                # Final validation status
                result.is_valid = len(result.critical_anomalies) == 0
                result.processing_successful = True
                
                self.audit_manager.log_event(
                    AuditEventType.VALIDATION_COMPLETED,
                    f"Validation completed for {invoice_path}",
                    invoice_number=result.invoice_number,
                    session_id=session_id,
                    event_data=result.get_summary_statistics()
                )
            else:
                result.is_valid = False
                result.processing_successful = False
                
                self.audit_manager.log_event(
                    AuditEventType.VALIDATION_FAILED,
                    f"Validation failed for {invoice_path}",
                    invoice_number=result.invoice_number,
                    session_id=session_id
                )
            
        except Exception as e:
            self.logger.exception(f"Validation failed for {invoice_path}: {e}")
            result.processing_successful = False
            result.is_valid = False
            
            self.audit_manager.log_event(
                AuditEventType.VALIDATION_FAILED,
                f"Validation exception for {invoice_path}: {str(e)}",
                invoice_number=result.invoice_number,
                session_id=session_id
            )
        
        return self._finalize_result(result, result.processing_successful, 
                                   "Validation completed" if result.processing_successful else "Validation failed")
    
    def _extract_invoice_data(self, invoice_path: Path, result: InvoiceValidationResult) -> Optional[InvoiceData]:
        """
        Extract invoice data from PDF.
        
        Args:
            invoice_path: Path to PDF file
            result: Validation result to update
            
        Returns:
            InvoiceData if successful, None otherwise
        """
        try:
            invoice_data = self.pdf_processor.process_pdf(invoice_path)
            self.logger.debug(f"Successfully extracted data from {invoice_path}")
            return invoice_data
            
        except PDFProcessingError as e:
            self.logger.error(f"PDF processing failed for {invoice_path}: {e}")
            # Add critical anomaly for PDF processing failure
            anomaly = ValidationAnomaly(
                anomaly_type=e.__class__.__name__,
                severity=SeverityLevel.CRITICAL,
                invoice_number="UNKNOWN",
                invoice_date="UNKNOWN",
                description=f"PDF processing failed: {str(e)}",
                details={'error_type': e.__class__.__name__, 'pdf_path': str(invoice_path)}
            )
            result.critical_anomalies.append(anomaly)
            return None
        except Exception as e:
            self.logger.exception(f"Unexpected error extracting data from {invoice_path}: {e}")
            return None
    
    def _execute_validation_phases(self, context: Dict[str, Any], 
                                 result: InvoiceValidationResult) -> bool:
        """
        Execute all validation phases sequentially.
        
        Args:
            context: Validation context
            result: Validation result to populate
            
        Returns:
            True if validation should continue, False if critical failure
        """
        phase_order = [
            ('pre_validation', result.pre_validation_results),
            ('data_quality', result.data_quality_results),
            ('format_structure', result.format_validation_results),
            ('parts_lookup', result.parts_lookup_results),
            ('price_comparison', result.price_validation_results),
            ('business_rules', result.business_rules_results)
        ]
        
        for phase_name, results_list in phase_order:
            try:
                self.logger.debug(f"Executing {phase_name} validation")
                validator = self.validators[phase_name]
                phase_results = validator.validate(context)
                results_list.extend(phase_results)
                
                # Check for critical errors that require stopping
                critical_errors = [r for r in phase_results if not r.is_valid and r.severity == SeverityLevel.CRITICAL]
                if critical_errors:
                    self.logger.warning(f"Critical errors in {phase_name}: {len(critical_errors)}")
                    
                    # Attempt error recovery
                    recovery_action = self.error_handler.handle_critical_error(critical_errors, context)
                    
                    if recovery_action.action == 'stop_processing':
                        self.logger.error(f"Stopping validation due to critical errors in {phase_name}")
                        return False
                    elif recovery_action.action == 'interactive_discovery':
                        # For now, we'll collect unknown parts and continue
                        # Interactive discovery would be handled by the CLI layer
                        self.logger.info("Unknown parts collected for interactive discovery")
                        continue
                    elif recovery_action.action == 'collect_and_continue':
                        self.logger.info("Continuing validation after collecting unknown parts")
                        continue
                
                # Special handling for parts lookup phase
                if phase_name == 'parts_lookup':
                    self._update_context_with_found_parts(context, phase_results)
                
            except Exception as e:
                self.logger.exception(f"Error in {phase_name} validation: {e}")
                return False
        
        return True
    
    def _update_context_with_found_parts(self, context: Dict[str, Any], 
                                       parts_results: List) -> None:
        """
        Update context with found parts for price validation.
        
        Args:
            context: Validation context to update
            parts_results: Results from parts lookup validation
        """
        found_parts = {}
        
        # Extract found parts from validation results
        for result in parts_results:
            if result.is_valid and result.details.get('part_number'):
                part_number = result.details['part_number']
                if 'authorized_price' in result.details:
                    # Create a minimal Part object for price comparison
                    found_parts[part_number] = type('Part', (), {
                        'part_number': part_number,
                        'authorized_price': result.details['authorized_price']
                    })()
        
        context['found_parts'] = found_parts
        self.logger.debug(f"Updated context with {len(found_parts)} found parts")
    
    def _categorize_anomalies(self, result: InvoiceValidationResult) -> None:
        """
        Categorize all validation results into anomalies by severity.
        
        Args:
            result: Validation result to update
        """
        all_results = (
            result.pre_validation_results +
            result.data_quality_results +
            result.format_validation_results +
            result.parts_lookup_results +
            result.price_validation_results +
            result.business_rules_results
        )
        
        for validation_result in all_results:
            if not validation_result.is_valid:
                anomaly = ValidationAnomaly.from_validation_result(
                    validation_result,
                    invoice_number=result.invoice_number,
                    invoice_date=result.invoice_date,
                    part_number=validation_result.details.get('part_number')
                )
                
                if validation_result.severity == SeverityLevel.CRITICAL:
                    result.critical_anomalies.append(anomaly)
                elif validation_result.severity == SeverityLevel.WARNING:
                    result.warning_anomalies.append(anomaly)
                else:
                    result.informational_anomalies.append(anomaly)
                
                # Log anomaly detection
                self.audit_manager.log_event(
                    AuditEventType.ANOMALY_DETECTED,
                    f"Anomaly detected: {anomaly.description}",
                    invoice_number=result.invoice_number,
                    session_id=result.processing_session_id,
                    event_data=anomaly.to_dict()
                )
    
    def _finalize_result(self, result: InvoiceValidationResult, 
                        success: bool, message: str) -> InvoiceValidationResult:
        """
        Finalize the validation result with timing and status.
        
        Args:
            result: Validation result to finalize
            success: Whether validation was successful
            message: Final status message
            
        Returns:
            Finalized validation result
        """
        result.processing_end_time = datetime.now()
        result.processing_duration = (
            result.processing_end_time - result.processing_start_time
        ).total_seconds()
        
        self.logger.info(f"Validation completed for {result.invoice_path}: "
                        f"{'SUCCESS' if success else 'FAILED'} "
                        f"({result.processing_duration:.2f}s)")
        
        return result
    
    def validate_batch(self, invoice_paths: List[Path], 
                      session_id: Optional[str] = None) -> List[InvoiceValidationResult]:
        """
        Validate multiple invoices in batch.
        
        Args:
            invoice_paths: List of PDF file paths to validate
            session_id: Optional batch processing session ID
            
        Returns:
            List of validation results
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        self.logger.info(f"Starting batch validation of {len(invoice_paths)} invoices")
        
        results = []
        for i, invoice_path in enumerate(invoice_paths, 1):
            self.logger.info(f"Processing invoice {i}/{len(invoice_paths)}: {invoice_path}")
            
            try:
                result = self.validate_invoice(invoice_path, session_id)
                results.append(result)
            except Exception as e:
                self.logger.exception(f"Failed to validate {invoice_path}: {e}")
                # Create a minimal failed result
                failed_result = InvoiceValidationResult(
                    invoice_number="UNKNOWN",
                    invoice_date="UNKNOWN",
                    invoice_path=str(invoice_path),
                    processing_session_id=session_id,
                    is_valid=False,
                    processing_successful=False
                )
                results.append(failed_result)
        
        # Log batch completion
        successful_count = sum(1 for r in results if r.processing_successful)
        self.logger.info(f"Batch validation completed: {successful_count}/{len(results)} successful")
        
        return results
    
    def validate_invoice_with_discovery(self, invoice_path: Path, session_id: Optional[str] = None,
                                      interactive_discovery: bool = False) -> tuple:
        """
        Validate an invoice with integrated part discovery.
        
        Args:
            invoice_path: Path to the PDF invoice file
            session_id: Optional processing session ID
            interactive_discovery: Enable interactive part discovery
            
        Returns:
            Tuple of (InvoiceValidationResult, List[PartDiscoveryResult])
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Start discovery session
        discovery_mode = 'interactive' if interactive_discovery else 'batch_collect'
        self.discovery_service.start_discovery_session(session_id, discovery_mode)
        
        # Perform standard validation
        validation_result = self.validate_invoice(invoice_path, session_id)
        
        # Handle discovery if unknown parts were found
        discovery_results = []
        if validation_result.processing_successful:
            # Extract invoice data for discovery
            invoice_data = self._extract_invoice_data(invoice_path, validation_result)
            if invoice_data:
                # Discover unknown parts
                unknown_contexts = self.discovery_service.discover_unknown_parts_from_invoice(
                    invoice_data, session_id
                )
                
                if unknown_contexts:
                    if interactive_discovery:
                        discovery_results = self.discovery_service.process_unknown_parts_interactive(session_id)
                    else:
                        discovery_results = self.discovery_service.process_unknown_parts_batch(session_id)
        
        # End discovery session
        self.discovery_service.end_discovery_session(session_id)
        
        return validation_result, discovery_results
    
    def validate_batch_with_discovery(self, invoice_paths: List[Path],
                                    session_id: Optional[str] = None,
                                    interactive_discovery: bool = False) -> tuple:
        """
        Validate multiple invoices with integrated part discovery.
        
        Args:
            invoice_paths: List of PDF file paths to validate
            session_id: Optional batch processing session ID
            interactive_discovery: Enable interactive part discovery
            
        Returns:
            Tuple of (List[InvoiceValidationResult], List[PartDiscoveryResult])
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Start discovery session
        discovery_mode = 'interactive' if interactive_discovery else 'batch_collect'
        self.discovery_service.start_discovery_session(session_id, discovery_mode)
        
        self.logger.info(f"Starting batch validation with discovery of {len(invoice_paths)} invoices")
        
        validation_results = []
        all_unknown_contexts = []
        
        # Process each invoice and collect unknown parts
        for i, invoice_path in enumerate(invoice_paths, 1):
            self.logger.info(f"Processing invoice {i}/{len(invoice_paths)}: {invoice_path}")
            
            try:
                # Validate individual invoice
                result = self.validate_invoice(invoice_path, session_id)
                validation_results.append(result)
                
                # Discover unknown parts if validation was successful
                if result.processing_successful:
                    invoice_data = self._extract_invoice_data(invoice_path, result)
                    if invoice_data:
                        unknown_contexts = self.discovery_service.discover_unknown_parts_from_invoice(
                            invoice_data, session_id
                        )
                        all_unknown_contexts.extend(unknown_contexts)
                        
            except Exception as e:
                self.logger.exception(f"Failed to validate {invoice_path}: {e}")
                # Create a minimal failed result
                failed_result = InvoiceValidationResult(
                    invoice_number="UNKNOWN",
                    invoice_date="UNKNOWN",
                    invoice_path=str(invoice_path),
                    processing_session_id=session_id,
                    is_valid=False,
                    processing_successful=False
                )
                validation_results.append(failed_result)
        
        # Process all discovered unknown parts
        discovery_results = []
        if all_unknown_contexts:
            self.logger.info(f"Processing {len(all_unknown_contexts)} unknown part contexts")
            
            if interactive_discovery:
                discovery_results = self.discovery_service.process_unknown_parts_interactive(session_id)
            else:
                discovery_results = self.discovery_service.process_unknown_parts_batch(session_id)
        
        # Log batch completion
        successful_count = sum(1 for r in validation_results if r.processing_successful)
        unknown_parts_count = len(set(ctx.part_number for ctx in all_unknown_contexts))
        
        self.logger.info(
            f"Batch validation with discovery completed: {successful_count}/{len(validation_results)} successful, "
            f"{unknown_parts_count} unique unknown parts discovered"
        )
        
        # End discovery session
        session_summary = self.discovery_service.end_discovery_session(session_id)
        self.logger.info(f"Discovery session summary: {session_summary}")
        
        return validation_results, discovery_results
    
    def get_discovery_service(self) -> InteractivePartDiscoveryService:
        """
        Get the discovery service instance.
        
        Returns:
            InteractivePartDiscoveryService instance
        """
        return self.discovery_service