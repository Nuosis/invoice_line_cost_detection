"""
Validation result data structures for the Invoice Rate Detection System.

This module defines the data structures used to represent validation results,
anomalies, and validation configurations. It reuses existing models from
processing.models and database.models to avoid duplication.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union
from enum import Enum

# Import existing models to avoid duplication
from processing.models import InvoiceData, LineItem, FormatSection
from database.models import Part, Configuration, PartDiscoveryLog, ValidationError


class AnomalyType(Enum):
    """Types of validation anomalies that can be detected."""
    PRICE_DISCREPANCY = "PRICE_DISCREPANCY"
    MISSING_PART = "MISSING_PART"
    FORMAT_VIOLATION = "FORMAT_VIOLATION"
    LINE_COUNT_VIOLATION = "LINE_COUNT_VIOLATION"
    DATA_QUALITY_ISSUE = "DATA_QUALITY_ISSUE"


class SeverityLevel(Enum):
    """Severity levels for validation results."""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFORMATIONAL = "INFORMATIONAL"


class AuditEventType(Enum):
    """Types of audit events to log."""
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    VALIDATION_FAILED = "validation_failed"
    ANOMALY_DETECTED = "anomaly_detected"
    PART_DISCOVERED = "part_discovered"
    PART_ADDED = "part_added"
    USER_INTERACTION = "user_interaction"
    CONFIGURATION_CHANGED = "configuration_changed"


@dataclass
class ValidationResult:
    """
    Represents the result of a single validation check.
    
    This is the base result structure used by all validation strategies
    to report their findings.
    """
    is_valid: bool
    severity: SeverityLevel
    anomaly_type: Optional[AnomalyType] = None
    message: str = ""
    field: Optional[str] = None
    line_number: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary for serialization."""
        return {
            'is_valid': self.is_valid,
            'severity': self.severity.value,
            'anomaly_type': self.anomaly_type.value if self.anomaly_type else None,
            'message': self.message,
            'field': self.field,
            'line_number': self.line_number,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ValidationAnomaly:
    """
    Represents a validation anomaly detected during processing.
    
    This structure contains detailed information about anomalies
    for reporting and audit purposes.
    """
    anomaly_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    anomaly_type: AnomalyType = AnomalyType.DATA_QUALITY_ISSUE
    severity: SeverityLevel = SeverityLevel.WARNING
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    part_number: Optional[str] = None
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.now)
    resolution_action: Optional[str] = None
    user_decision: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert anomaly to dictionary for serialization."""
        return {
            'anomaly_id': self.anomaly_id,
            'anomaly_type': self.anomaly_type.value,
            'severity': self.severity.value,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'part_number': self.part_number,
            'description': self.description,
            'details': self.details,
            'detected_at': self.detected_at.isoformat(),
            'resolution_action': self.resolution_action,
            'user_decision': self.user_decision
        }

    @classmethod
    def from_validation_result(cls, result: ValidationResult, 
                             invoice_number: str = None,
                             invoice_date: str = None,
                             part_number: str = None) -> 'ValidationAnomaly':
        """Create an anomaly from a validation result."""
        return cls(
            anomaly_type=result.anomaly_type or AnomalyType.DATA_QUALITY_ISSUE,
            severity=result.severity,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            part_number=part_number,
            description=result.message,
            details=result.details.copy(),
            detected_at=result.timestamp
        )


@dataclass
class InvoiceValidationResult:
    """
    Represents the complete validation result for an invoice.
    
    This structure contains all validation results, anomalies, and
    processing metadata for a single invoice.
    """
    invoice_number: str
    invoice_date: str
    invoice_path: str
    processing_session_id: str
    
    # Validation status
    is_valid: bool = True
    processing_successful: bool = False
    processing_start_time: datetime = field(default_factory=datetime.now)
    processing_end_time: datetime = field(default_factory=datetime.now)
    processing_duration: float = 0.0
    
    # Validation results by category
    pre_validation_results: List[ValidationResult] = field(default_factory=list)
    data_quality_results: List[ValidationResult] = field(default_factory=list)
    format_validation_results: List[ValidationResult] = field(default_factory=list)
    parts_lookup_results: List[ValidationResult] = field(default_factory=list)
    price_validation_results: List[ValidationResult] = field(default_factory=list)
    business_rules_results: List[ValidationResult] = field(default_factory=list)
    
    # Anomalies categorized by severity
    critical_anomalies: List[ValidationAnomaly] = field(default_factory=list)
    warning_anomalies: List[ValidationAnomaly] = field(default_factory=list)
    informational_anomalies: List[ValidationAnomaly] = field(default_factory=list)
    
    # Discovery tracking
    unknown_parts_discovered: List[str] = field(default_factory=list)
    parts_added_during_processing: List[str] = field(default_factory=list)

    def get_all_anomalies(self) -> List[ValidationAnomaly]:
        """Get all anomalies regardless of severity."""
        return (self.critical_anomalies + 
                self.warning_anomalies + 
                self.informational_anomalies)

    def has_critical_issues(self) -> bool:
        """Check if invoice has critical validation issues."""
        return len(self.critical_anomalies) > 0

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for this validation result."""
        all_results = (
            self.pre_validation_results +
            self.data_quality_results +
            self.format_validation_results +
            self.parts_lookup_results +
            self.price_validation_results +
            self.business_rules_results
        )
        
        return {
            'total_checks': len(all_results),
            'passed_checks': sum(1 for r in all_results if r.is_valid),
            'failed_checks': sum(1 for r in all_results if not r.is_valid),
            'critical_anomalies': len(self.critical_anomalies),
            'warning_anomalies': len(self.warning_anomalies),
            'informational_anomalies': len(self.informational_anomalies),
            'unknown_parts': len(self.unknown_parts_discovered),
            'parts_added': len(self.parts_added_during_processing),
            'processing_duration': self.processing_duration,
            'is_valid': self.is_valid,
            'processing_successful': self.processing_successful
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary for serialization."""
        return {
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'invoice_path': self.invoice_path,
            'processing_session_id': self.processing_session_id,
            'is_valid': self.is_valid,
            'processing_successful': self.processing_successful,
            'processing_start_time': self.processing_start_time.isoformat(),
            'processing_end_time': self.processing_end_time.isoformat(),
            'processing_duration': self.processing_duration,
            'pre_validation_results': [r.to_dict() for r in self.pre_validation_results],
            'data_quality_results': [r.to_dict() for r in self.data_quality_results],
            'format_validation_results': [r.to_dict() for r in self.format_validation_results],
            'parts_lookup_results': [r.to_dict() for r in self.parts_lookup_results],
            'price_validation_results': [r.to_dict() for r in self.price_validation_results],
            'business_rules_results': [r.to_dict() for r in self.business_rules_results],
            'critical_anomalies': [a.to_dict() for a in self.critical_anomalies],
            'warning_anomalies': [a.to_dict() for a in self.warning_anomalies],
            'informational_anomalies': [a.to_dict() for a in self.informational_anomalies],
            'unknown_parts_discovered': self.unknown_parts_discovered,
            'parts_added_during_processing': self.parts_added_during_processing,
            'summary_statistics': self.get_summary_statistics()
        }


@dataclass
class ValidationConfiguration:
    """
    Configuration parameters for validation behavior.
    
    This structure contains all configurable parameters that control
    how validation is performed. It extends the existing Configuration
    model with validation-specific settings.
    """
    # Price validation settings
    price_tolerance: Decimal = Decimal('0.001')
    price_discrepancy_warning_threshold: Decimal = Decimal('1.00')
    price_discrepancy_critical_threshold: Decimal = Decimal('5.00')
    price_percentage_warning_threshold: float = 5.0
    price_percentage_critical_threshold: float = 20.0
    
    # Format validation settings
    strict_format_validation: bool = True
    required_format_sections: List[str] = field(
        default_factory=lambda: ['SUBTOTAL', 'FREIGHT', 'TAX', 'TOTAL']
    )
    
    # Part discovery settings
    interactive_discovery: bool = True
    auto_add_discovered_parts: bool = False
    batch_collect_unknown_parts: bool = True
    
    # Performance settings
    enable_validation_caching: bool = True
    cache_size: int = 1000
    batch_size: int = 50
    
    # Business rules settings
    max_reasonable_price: Decimal = Decimal('1000.00')
    min_reasonable_price: Decimal = Decimal('0.01')
    max_invoice_age_days: int = 365
    max_line_items_per_invoice: int = 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'price_tolerance': float(self.price_tolerance),
            'price_discrepancy_warning_threshold': float(self.price_discrepancy_warning_threshold),
            'price_discrepancy_critical_threshold': float(self.price_discrepancy_critical_threshold),
            'price_percentage_warning_threshold': self.price_percentage_warning_threshold,
            'price_percentage_critical_threshold': self.price_percentage_critical_threshold,
            'strict_format_validation': self.strict_format_validation,
            'required_format_sections': self.required_format_sections,
            'interactive_discovery': self.interactive_discovery,
            'auto_add_discovered_parts': self.auto_add_discovered_parts,
            'batch_collect_unknown_parts': self.batch_collect_unknown_parts,
            'enable_validation_caching': self.enable_validation_caching,
            'cache_size': self.cache_size,
            'batch_size': self.batch_size,
            'max_reasonable_price': float(self.max_reasonable_price),
            'min_reasonable_price': float(self.min_reasonable_price),
            'max_invoice_age_days': self.max_invoice_age_days,
            'max_line_items_per_invoice': self.max_line_items_per_invoice
        }

    @classmethod
    def from_database_config(cls, db_manager) -> 'ValidationConfiguration':
        """
        Create ValidationConfiguration from database configuration values.
        
        Args:
            db_manager: DatabaseManager instance to read configuration from
            
        Returns:
            ValidationConfiguration with values from database
        """
        config = cls()
        
        # Load configuration values from database with fallbacks
        config.price_tolerance = Decimal(str(
            db_manager.get_config_value('price_tolerance', config.price_tolerance)
        ))
        config.interactive_discovery = db_manager.get_config_value(
            'interactive_discovery', config.interactive_discovery
        )
        config.auto_add_discovered_parts = db_manager.get_config_value(
            'auto_add_discovered_parts', config.auto_add_discovered_parts
        )
        config.strict_format_validation = db_manager.get_config_value(
            'strict_format_validation', config.strict_format_validation
        )
        
        return config


@dataclass
class PartDiscoveryResult:
    """
    Result of part discovery workflow.
    
    This structure represents the outcome of discovering and handling
    an unknown part during validation.
    """
    action: str  # 'added', 'skipped', 'skip_all'
    part: Optional[Part] = None
    continue_processing: bool = True
    user_decision: Optional[str] = None
    discovery_log: Optional[PartDiscoveryLog] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert discovery result to dictionary for serialization."""
        return {
            'action': self.action,
            'part': self.part.to_dict() if self.part else None,
            'continue_processing': self.continue_processing,
            'user_decision': self.user_decision,
            'discovery_log': self.discovery_log.to_dict() if self.discovery_log else None
        }


@dataclass
class PriceSuggestion:
    """
    Price suggestion for unknown parts.
    
    This structure represents a suggested price for an unknown part
    based on various algorithms and heuristics.
    """
    price: Decimal
    confidence: float  # 0.0 to 1.0
    reason: str
    source_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert price suggestion to dictionary for serialization."""
        return {
            'price': float(self.price),
            'confidence': self.confidence,
            'reason': self.reason,
            'source_data': self.source_data
        }


@dataclass
class RecoveryAction:
    """
    Recovery action for handling validation errors.
    
    This structure represents an action to take when a validation
    error occurs, including user intervention requirements.
    """
    action: str  # 'stop_processing', 'retry_validation', 'skip_part', 'collect_and_continue'
    message: str
    user_intervention_required: bool = False
    retry_count: int = 0
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert recovery action to dictionary for serialization."""
        return {
            'action': self.action,
            'message': self.message,
            'user_intervention_required': self.user_intervention_required,
            'retry_count': self.retry_count,
            'context': self.context
        }


# Default validation configuration
DEFAULT_VALIDATION_CONFIG = ValidationConfiguration()