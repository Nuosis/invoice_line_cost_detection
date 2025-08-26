"""
Data models for extracted invoice information.

This module defines the data structures used to represent extracted invoice data,
including invoice metadata, line items, and format sections.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
import re


@dataclass
class LineItem:
    """
    Represents a single line item from an invoice.
    
    Attributes:
        item_code: Part number/item code (e.g., GS0448NVOT)
        description: Item description (e.g., SHIRT WORK LS BTN COTTON)
        item_type: Type of charge (Rent, Ruin charge, etc.)
        rate: Unit rate/price
        quantity: Quantity (defaults to 1 for compatibility)
        total: Total price (rate * quantity, calculated automatically)
        line_number: Original line number in invoice (for debugging)
        raw_text: Original text line (for debugging)
    """
    item_code: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[str] = None
    rate: Optional[Decimal] = None
    quantity: Optional[int] = 1
    total: Optional[Decimal] = None
    line_number: Optional[int] = None
    raw_text: Optional[str] = None

    def __post_init__(self):
        """Validate and normalize line item data after initialization."""
        # Convert numeric strings to appropriate types
        if isinstance(self.rate, (str, float, int)) and self.rate is not None:
            try:
                self.rate = Decimal(str(self.rate))
            except (ValueError, TypeError):
                self.rate = None
        
        # Convert quantity to int if provided as string
        if isinstance(self.quantity, str):
            try:
                self.quantity = int(float(self.quantity))
            except (ValueError, TypeError):
                self.quantity = 1  # Default to 1 if conversion fails
        elif self.quantity is None:
            self.quantity = 1  # Default to 1 if not provided
        
        # Convert total to Decimal if provided as string
        if isinstance(self.total, (str, float, int)) and self.total is not None:
            try:
                self.total = Decimal(str(self.total))
            except (ValueError, TypeError):
                self.total = None
        
        # Calculate total if not provided but rate and quantity are available
        if (self.total is None and
            self.rate is not None and
            self.quantity is not None):
            self.total = self.rate * self.quantity

    def is_valid(self) -> bool:
        """
        Check if line item has minimum required data.
        
        A line item is valid if it has:
        - A non-zero quantity (or defaults to 1)
        - A rate/price
        - A description (even if no part number)
        
        This allows for service charges, fees, and other line items without part numbers.
        """
        return (
            self.quantity is not None and
            self.quantity != 0 and
            self.rate is not None and
            self.description is not None and
            self.description.strip() != ""
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert line item to dictionary for serialization."""
        return {
            'item_code': self.item_code,
            'description': self.description,
            'item_type': self.item_type,
            'rate': float(self.rate) if self.rate else None,
            'quantity': self.quantity,
            'total': float(self.total) if self.total else None,
            'line_number': self.line_number,
            'raw_text': self.raw_text
        }


@dataclass
class FormatSection:
    """
    Represents a format section (SUBTOTAL, FREIGHT, TAX, TOTAL).
    
    Attributes:
        section_type: Type of section (SUBTOTAL, FREIGHT, TAX, TOTAL)
        amount: Amount for this section
        raw_text: Original text line (for debugging)
        line_number: Line number where found (for debugging)
    """
    section_type: str
    amount: Decimal
    raw_text: Optional[str] = None
    line_number: Optional[int] = None

    def __post_init__(self):
        """Validate and normalize format section data."""
        if isinstance(self.amount, (str, float, int)):
            try:
                self.amount = Decimal(str(self.amount))
            except (ValueError, TypeError):
                self.amount = Decimal('0.00')

    def to_dict(self) -> Dict[str, Any]:
        """Convert format section to dictionary for serialization."""
        return {
            'section_type': self.section_type,
            'amount': float(self.amount),
            'raw_text': self.raw_text,
            'line_number': self.line_number
        }


@dataclass
class InvoiceData:
    """
    Represents complete extracted invoice data.
    
    Attributes:
        invoice_number: Invoice number
        invoice_date: Invoice date
        customer_number: Customer account number
        customer_name: Customer name
        line_items: List of line items
        format_sections: List of format sections (SUBTOTAL, FREIGHT, TAX, TOTAL)
        pdf_path: Path to source PDF file
        extraction_timestamp: When the data was extracted
        raw_text: Complete extracted text (for debugging)
        page_count: Number of pages in PDF
        processing_notes: Any notes from processing
    """
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    customer_number: Optional[str] = None
    customer_name: Optional[str] = None
    line_items: List[LineItem] = field(default_factory=list)
    format_sections: List[FormatSection] = field(default_factory=list)
    pdf_path: Optional[str] = None
    extraction_timestamp: Optional[datetime] = None
    raw_text: Optional[str] = None
    page_count: Optional[int] = None
    processing_notes: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Set extraction timestamp if not provided."""
        if self.extraction_timestamp is None:
            self.extraction_timestamp = datetime.now()

    def is_valid(self) -> bool:
        """Check if invoice data has minimum required information."""
        return (
            self.invoice_number is not None and
            self.invoice_number.strip() != "" and
            self.invoice_date is not None and
            len(self.line_items) > 0 and
            len(self.format_sections) >= 4  # SUBTOTAL, FREIGHT, TAX, TOTAL
        )

    def get_format_section(self, section_type: str) -> Optional[FormatSection]:
        """Get a specific format section by type."""
        for section in self.format_sections:
            if section.section_type.upper() == section_type.upper():
                return section
        return None

    def get_valid_line_items(self) -> List[LineItem]:
        """Get only valid line items."""
        return [item for item in self.line_items if item.is_valid()]

    def get_total_amount(self) -> Optional[Decimal]:
        """Get the total amount from format sections."""
        total_section = self.get_format_section('TOTAL')
        return total_section.amount if total_section else None

    def get_subtotal_amount(self) -> Optional[Decimal]:
        """Get the subtotal amount from format sections."""
        subtotal_section = self.get_format_section('SUBTOTAL')
        return subtotal_section.amount if subtotal_section else None

    def get_freight_amount(self) -> Optional[Decimal]:
        """Get the freight amount from format sections."""
        freight_section = self.get_format_section('FREIGHT')
        return freight_section.amount if freight_section else None

    def get_tax_amount(self) -> Optional[Decimal]:
        """Get the tax amount from format sections."""
        tax_section = self.get_format_section('TAX')
        return tax_section.amount if tax_section else None

    def calculate_expected_total(self) -> Optional[Decimal]:
        """Calculate expected total as Subtotal + Freight + Tax."""
        subtotal = self.get_subtotal_amount()
        freight = self.get_freight_amount()
        tax = self.get_tax_amount()
        
        if subtotal is None or freight is None or tax is None:
            return None
            
        return subtotal + freight + tax

    def validate_total_calculation(self, tolerance: Decimal = Decimal('0.01')) -> bool:
        """
        Validate that Total = Subtotal + Freight + Tax within tolerance.
        
        Args:
            tolerance: Acceptable difference between expected and actual total
            
        Returns:
            True if calculation is valid, False otherwise
        """
        expected_total = self.calculate_expected_total()
        actual_total = self.get_total_amount()
        
        if expected_total is None or actual_total is None:
            return False
            
        difference = abs(expected_total - actual_total)
        return difference <= tolerance

    def get_total_calculation_discrepancy(self) -> Optional[Decimal]:
        """
        Get the discrepancy between expected and actual total.
        
        Returns:
            Difference amount (positive if actual > expected, negative if actual < expected)
            None if calculation cannot be performed
        """
        expected_total = self.calculate_expected_total()
        actual_total = self.get_total_amount()
        
        if expected_total is None or actual_total is None:
            return None
            
        return actual_total - expected_total

    def validate_format_sequence(self) -> bool:
        """Validate that format sections are in correct order."""
        expected_sequence = ['SUBTOTAL', 'FREIGHT', 'TAX', 'TOTAL']
        
        if len(self.format_sections) != 4:
            return False
            
        for i, expected_type in enumerate(expected_sequence):
            if i >= len(self.format_sections):
                return False
            if self.format_sections[i].section_type.upper() != expected_type:
                return False
                
        return True

    def add_processing_note(self, note: str):
        """Add a processing note."""
        self.processing_notes.append(f"{datetime.now().isoformat()}: {note}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert invoice data to dictionary for serialization."""
        return {
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'customer_number': self.customer_number,
            'customer_name': self.customer_name,
            'line_items': [item.to_dict() for item in self.line_items],
            'format_sections': [section.to_dict() for section in self.format_sections],
            'pdf_path': self.pdf_path,
            'extraction_timestamp': self.extraction_timestamp.isoformat() if self.extraction_timestamp else None,
            'page_count': self.page_count,
            'processing_notes': self.processing_notes,
            'is_valid': self.is_valid(),
            'total_line_items': len(self.line_items),
            'valid_line_items': len(self.get_valid_line_items())
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InvoiceData':
        """Create InvoiceData instance from dictionary."""
        # Convert line items
        line_items = []
        for item_data in data.get('line_items', []):
            line_items.append(LineItem(**item_data))
            
        # Convert format sections
        format_sections = []
        for section_data in data.get('format_sections', []):
            format_sections.append(FormatSection(**section_data))
            
        # Convert timestamp
        extraction_timestamp = None
        if data.get('extraction_timestamp'):
            extraction_timestamp = datetime.fromisoformat(data['extraction_timestamp'])
            
        return cls(
            invoice_number=data.get('invoice_number'),
            invoice_date=data.get('invoice_date'),
            customer_number=data.get('customer_number'),
            customer_name=data.get('customer_name'),
            line_items=line_items,
            format_sections=format_sections,
            pdf_path=data.get('pdf_path'),
            extraction_timestamp=extraction_timestamp,
            raw_text=data.get('raw_text'),
            page_count=data.get('page_count'),
            processing_notes=data.get('processing_notes', [])
        )


def validate_invoice_number(invoice_number: str) -> bool:
    """Validate invoice number format."""
    if not invoice_number or not isinstance(invoice_number, str):
        return False
    
    # Remove whitespace and check if it's numeric
    cleaned = invoice_number.strip()
    return cleaned.isdigit() and len(cleaned) >= 8


def validate_invoice_date(invoice_date: str) -> bool:
    """Validate invoice date format."""
    if not invoice_date or not isinstance(invoice_date, str):
        return False
    
    # Try common date formats
    date_patterns = [
        r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        r'\d{1,2}/\d{1,2}/\d{4}',  # M/D/YYYY
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, invoice_date.strip()):
            return True
    
    return False


def validate_part_number(part_number: str) -> bool:
    """Validate part number format."""
    if not part_number or not isinstance(part_number, str):
        return False
    
    # Basic validation - alphanumeric with some special characters
    cleaned = part_number.strip()
    return bool(re.match(r'^[A-Za-z0-9_\-\.]+$', cleaned)) and len(cleaned) >= 2


# Legacy classes kept for backward compatibility with existing CLI code
# These will be removed once all CLI code is updated to use the JSON-based approach

@dataclass
class InvoiceLineItem:
    """Legacy class for backward compatibility."""
    part_number: Optional[str] = None
    description: Optional[str] = None
    unit_price: Optional[Decimal] = None
    quantity: Optional[int] = None
    total_price: Optional[Decimal] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    line_number: Optional[int] = None

    def __post_init__(self):
        if isinstance(self.unit_price, (str, float, int)) and self.unit_price is not None:
            self.unit_price = Decimal(str(self.unit_price))
        if isinstance(self.total_price, (str, float, int)) and self.total_price is not None:
            self.total_price = Decimal(str(self.total_price))

    def is_valid(self) -> bool:
        return (self.part_number is not None and
                self.unit_price is not None and
                self.quantity is not None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'part_number': self.part_number,
            'description': self.description,
            'unit_price': float(self.unit_price) if self.unit_price else None,
            'quantity': self.quantity,
            'total_price': float(self.total_price) if self.total_price else None,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'line_number': self.line_number
        }

    @classmethod
    def from_line_item(cls, line_item: 'LineItem', invoice_number: str = None, invoice_date: str = None) -> 'InvoiceLineItem':
        """
        Create an InvoiceLineItem from a LineItem.
        
        Args:
            line_item: LineItem instance to convert
            invoice_number: Invoice number to associate with the line item
            invoice_date: Invoice date to associate with the line item
            
        Returns:
            InvoiceLineItem instance
        """
        return cls(
            part_number=line_item.item_code,
            description=line_item.description,
            unit_price=line_item.rate,
            quantity=line_item.quantity,
            total_price=line_item.total,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            line_number=line_item.line_number
        )


@dataclass
class ProcessingResult:
    """Legacy class for backward compatibility."""
    line_item: InvoiceLineItem
    validation_result: Optional[str] = None
    is_valid: bool = True
    issue_type: Optional[str] = None
    notes: Optional[str] = None
    processing_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'line_item': self.line_item.to_dict(),
            'validation_result': self.validation_result,
            'is_valid': self.is_valid,
            'issue_type': self.issue_type,
            'notes': self.notes,
            'processing_timestamp': self.processing_timestamp.isoformat()
        }

    @classmethod
    def create_passed(cls, line_item: InvoiceLineItem, notes: str = None) -> 'ProcessingResult':
        return cls(
            line_item=line_item,
            validation_result="PASS",
            is_valid=True,
            issue_type=None,
            notes=notes
        )

    @classmethod
    def create_failed(cls, line_item: InvoiceLineItem, issue_type: str, notes: str = None) -> 'ProcessingResult':
        return cls(
            line_item=line_item,
            validation_result="FAIL",
            is_valid=False,
            issue_type=issue_type,
            notes=notes
        )