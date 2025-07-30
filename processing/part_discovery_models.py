"""
Shared models for the Part Discovery system.

This module contains data classes and models used across the part discovery
workflow to avoid circular imports between service and prompt modules.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime

from processing.models import LineItem


@dataclass
class UnknownPartContext:
    """
    Context information for an unknown part discovery.
    
    Attributes:
        part_number: The unknown part number
        invoice_number: Invoice where the part was found
        invoice_date: Date of the invoice
        line_item: The line item containing the part
        discovered_price: Price found in the invoice
        description: Part description if available
        quantity: Quantity from the line item
        wearer_info: Wearer information if available
        size: Size information if available
        item_type: Item type if available
    """
    part_number: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    line_item: Optional[LineItem] = None
    discovered_price: Optional[Decimal] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    wearer_info: Optional[str] = None
    size: Optional[str] = None
    item_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and serialization."""
        return {
            'part_number': self.part_number,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'discovered_price': float(self.discovered_price) if self.discovered_price else None,
            'description': self.description,
            'quantity': self.quantity,
            'wearer_info': self.wearer_info,
            'size': self.size,
            'item_type': self.item_type
        }


@dataclass
class DiscoverySession:
    """
    Discovery session information for testing and management.
    
    This class represents a discovery session with summary information
    used by the discovery management tests and CLI commands.
    """
    session_id: str
    session_date: datetime
    parts_discovered: int
    parts_added: int
    parts_skipped: int
    discovery_details: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_id': self.session_id,
            'session_date': self.session_date.isoformat(),
            'parts_discovered': self.parts_discovered,
            'parts_added': self.parts_added,
            'parts_skipped': self.parts_skipped,
            'discovery_details': self.discovery_details
        }


@dataclass
class UnknownPart:
    """
    Unknown part information for review and management.
    
    This class represents an unknown part discovered during processing
    that needs review or action.
    """
    part_number: str
    discovered_price: Optional[Decimal] = None
    invoice_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    occurrences: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'part_number': self.part_number,
            'discovered_price': float(self.discovered_price) if self.discovered_price else None,
            'invoice_number': self.invoice_number,
            'description': self.description,
            'quantity': self.quantity,
            'occurrences': self.occurrences
        }