from __future__ import annotations

"""
Validation model primitives required by tests and reporting.

This lightweight module provides:
- ValidationConfiguration
- SeverityLevel, AnomalyType
- ValidationAnomaly
- InvoiceValidationResult

It is intentionally minimal to satisfy unit and report tests without bringing in
heavy dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFORMATIONAL = "INFORMATIONAL"


class AnomalyType(str, Enum):
    PRICE_DISCREPANCY = "PRICE_DISCREPANCY"
    MISSING_PART = "MISSING_PART"
    FORMAT_VIOLATION = "FORMAT_VIOLATION"
    DATA_QUALITY_ISSUE = "DATA_QUALITY_ISSUE"


@dataclass
class ValidationConfiguration:
    """
    Streamlined configuration for v2.0 validation workflow.
    
    Simplified to support only binary validation (PASSED/FAILED/UNKNOWN)
    following the KISS principle from validation_logic_specification_v2.md.
    """
    # Price validation (binary only - match or no match)
    price_tolerance: Decimal = Decimal("0.001")
    
    # Discovery behavior (always enabled for streamlined workflow)
    interactive_discovery: bool = True
    batch_collect_unknown_parts: bool = True
    
    # Legacy attributes kept for backward compatibility with existing tests
    # These are deprecated and should not be used in new code
    price_discrepancy_warning_threshold: Decimal = Decimal("1.00")  # DEPRECATED
    price_discrepancy_critical_threshold: Decimal = Decimal("5.00")  # DEPRECATED


@dataclass
class ValidationAnomaly:
    """
    Represents a validation anomaly detected during processing.
    """
    anomaly_type: AnomalyType
    severity: SeverityLevel
    part_number: Optional[str] = None
    description: str = ""
    details: Dict[str, object] = field(default_factory=dict)
    resolution_action: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class InvoiceValidationResult:
    """
    Represents the result of validating a single invoice.
    This structure is intentionally simple and aligned with unit tests.
    """
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    invoice_file_path: Optional[Path] = None  # legacy name used by some code
    invoice_path: Optional[Path] = None       # commonly referenced by templates

    processing_session_id: Optional[str] = None
    processing_successful: bool = True
    processing_start_time: datetime = field(default_factory=datetime.now)
    processing_end_time: datetime = field(default_factory=datetime.now)
    processing_duration: float = 0.0  # seconds

    # Anomalies categorized by severity
    critical_anomalies: List[ValidationAnomaly] = field(default_factory=list)
    warning_anomalies: List[ValidationAnomaly] = field(default_factory=list)
    informational_anomalies: List[ValidationAnomaly] = field(default_factory=list)

    def get_all_anomalies(self) -> List[ValidationAnomaly]:
        """Return all anomalies regardless of severity."""
        return self.critical_anomalies + self.warning_anomalies + self.informational_anomalies

    def get_summary_statistics(self) -> Dict[str, object]:
        """Provide simple summary statistics consumed by reporting."""
        total = len(self.get_all_anomalies())
        return {
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "critical_anomalies": len(self.critical_anomalies),
            "warning_anomalies": len(self.warning_anomalies),
            "informational_anomalies": len(self.informational_anomalies),
            "total_anomalies": total,
            "processing_successful": self.processing_successful,
            "processing_start_time": self.processing_start_time.isoformat() if self.processing_start_time else None,
            "processing_end_time": self.processing_end_time.isoformat() if self.processing_end_time else None,
            "processing_duration": self.processing_duration,
        }