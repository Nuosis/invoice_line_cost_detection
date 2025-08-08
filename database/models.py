"""
Data models and validation classes for the Invoice Rate Detection System.

This module defines the data structures and validation logic for all database entities
including Parts, Configuration, and Part Discovery Log entries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal, Any, Dict, Union
import re
import json


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DatabaseError(Exception):
    """Base exception for database-related errors."""
    pass


class PartNotFoundError(DatabaseError):
    """Raised when a requested part is not found."""
    pass


class ConfigurationError(DatabaseError):
    """Raised when configuration operations fail."""
    pass


@dataclass
class Part:
    """
    Represents a part in the master parts database.

    Attributes:
        part_number: Part identifier (can be empty for items without traditional part numbers)
        authorized_price: Expected/authorized price with 4 decimal precision
        description: Human-readable part description
        item_type: Type/category of the part (e.g., Rent, Charge, etc.)
        category: Optional categorization for parts organization
        source: How the part was added ('manual', 'discovered', 'imported')
        first_seen_invoice: Invoice number where this part was first discovered
        created_date: When the part was added to the database
        last_updated: When the part was last modified
        is_active: Soft delete flag for deactivating parts
        notes: Additional notes or comments about the part
        composite_key: Computed composite identifier (item_type|description|part_number)
    """
    part_number: Optional[str]
    authorized_price: Decimal
    description: Optional[str] = None
    item_type: Optional[str] = None
    category: Optional[str] = None
    source: Literal['manual', 'discovered', 'imported'] = 'manual'
    first_seen_invoice: Optional[str] = None
    created_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None
    composite_key: Optional[str] = field(init=False)

    def __post_init__(self):
        """Validate part data and generate composite key after initialization."""
        self.composite_key = self.generate_composite_key()
        self.validate()

    @staticmethod
    def normalize_component(component: Optional[str]) -> str:
        """
        Normalize a component for composite key generation.
        
        Args:
            component: Component to normalize
            
        Returns:
            Normalized component string
        """
        if not component:
            return ""
        
        # Strip whitespace and convert to uppercase for consistency
        normalized = str(component).strip().upper()
        
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized

    def generate_composite_key(self) -> str:
        """
        Generate composite key from item_type, description, and part_number.
        
        Returns:
            Composite key string in format: item_type|description|part_number
        """
        item_type_norm = self.normalize_component(self.item_type)
        description_norm = self.normalize_component(self.description)
        part_number_norm = self.normalize_component(self.part_number)
        
        # Create composite key - all components are included even if empty
        composite = f"{item_type_norm}|{description_norm}|{part_number_norm}"
        
        return composite

    def validate(self) -> None:
        """
        Validate part data according to business rules.
        
        Raises:
            ValidationError: If validation fails
        """
        # At least one of part_number, description, or item_type must be provided
        if not any([self.part_number, self.description, self.item_type]):
            raise ValidationError("At least one of part_number, description, or item_type must be provided")
        
        # Validate part number format if provided
        if self.part_number:
            if not isinstance(self.part_number, str):
                raise ValidationError("Part number must be a string")
            
            if not self.part_number.strip():
                raise ValidationError("Part number cannot be empty or whitespace only")
            
            # Basic part number format validation (alphanumeric with some special chars)
            if not re.match(r'^[A-Za-z0-9_\-\.\s@]+$', self.part_number):
                raise ValidationError(
                    "Part number can only contain letters, numbers, underscores, hyphens, periods, spaces, and @ symbols"
                )

        # Validate authorized price
        if not isinstance(self.authorized_price, (Decimal, float, int)):
            raise ValidationError("Authorized price must be a number")
        
        self.authorized_price = Decimal(str(self.authorized_price))
        
        if self.authorized_price <= 0:
            raise ValidationError("Authorized price must be positive")
        
        # Ensure 4 decimal places precision
        if self.authorized_price.as_tuple().exponent < -4:
            raise ValidationError("Authorized price cannot have more than 4 decimal places")

        # Validate source
        if self.source not in ('manual', 'discovered', 'imported'):
            raise ValidationError("Source must be one of: manual, discovered, imported")

        # Validate boolean fields
        if not isinstance(self.is_active, bool):
            raise ValidationError("is_active must be a boolean")

        # Validate composite key is not empty
        if not self.composite_key or self.composite_key == "||":
            raise ValidationError("Composite key cannot be empty - at least one component must have a value")

    def to_dict(self) -> Dict[str, Any]:
        """Convert part to dictionary for database operations."""
        return {
            'part_number': self.part_number,
            'authorized_price': float(self.authorized_price),
            'description': self.description,
            'item_type': self.item_type,
            'category': self.category,
            'source': self.source,
            'first_seen_invoice': self.first_seen_invoice,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'is_active': self.is_active,
            'notes': self.notes,
            'composite_key': self.composite_key
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Part':
        """Create Part instance from dictionary."""
        # Convert string dates back to datetime objects
        created_date = None
        if data.get('created_date'):
            created_date = datetime.fromisoformat(data['created_date'])
        
        last_updated = None
        if data.get('last_updated'):
            last_updated = datetime.fromisoformat(data['last_updated'])
    
        return cls(
            part_number=data.get('part_number'),  # Allow None for part_number
            authorized_price=Decimal(str(data['authorized_price'])),
            description=data.get('description'),
            item_type=data.get('item_type'),
            category=data.get('category'),
            source=data.get('source', 'manual'),
            first_seen_invoice=data.get('first_seen_invoice'),
            created_date=created_date,
            last_updated=last_updated,
            is_active=data.get('is_active', True),
            notes=data.get('notes')
        )

    @classmethod
    def create_from_line_item(cls, item_type: Optional[str], description: Optional[str],
                            part_number: Optional[str], authorized_price: Decimal,
                            **kwargs) -> 'Part':
        """
        Create a Part instance from line item components.
        
        Args:
            item_type: Item type from line item
            description: Description from line item
            part_number: Part number from line item (can be None)
            authorized_price: Price for the part
            **kwargs: Additional part attributes
            
        Returns:
            Part instance with generated composite key
        """
        return cls(
            part_number=part_number,
            authorized_price=authorized_price,
            description=description,
            item_type=item_type,
            **kwargs
        )

    def get_identifier(self) -> str:
        """
        Get the unique identifier for this part.
        
        Returns:
            Composite key that uniquely identifies this part
        """
        return self.composite_key or self.generate_composite_key()

    @classmethod
    def generate_identifier_from_components(cls, item_type: Optional[str],
                                          description: Optional[str],
                                          part_number: Optional[str]) -> str:
        """
        Generate composite identifier from components without creating a Part instance.
        
        Args:
            item_type: Item type component
            description: Description component
            part_number: Part number component
            
        Returns:
            Composite key string
        """
        item_type_norm = cls.normalize_component(item_type)
        description_norm = cls.normalize_component(description)
        part_number_norm = cls.normalize_component(part_number)
        
        return f"{item_type_norm}|{description_norm}|{part_number_norm}"


@dataclass
class Configuration:
    """
    Represents a configuration setting.
    
    Attributes:
        key: Configuration setting name (primary key)
        value: Configuration value stored as text
        data_type: Type hint for value parsing ('string', 'number', 'boolean', 'json')
        description: Human-readable description of the setting
        category: Grouping for related settings
        created_date: When the setting was first created
        last_updated: When the setting was last modified
    """
    key: str
    value: str
    data_type: Literal['string', 'number', 'boolean', 'json'] = 'string'
    description: Optional[str] = None
    category: str = 'general'
    created_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def __post_init__(self):
        """Validate configuration data after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate configuration data according to business rules.
        
        Raises:
            ValidationError: If validation fails
        """
        # Validate key
        if not self.key or not isinstance(self.key, str):
            raise ValidationError("Configuration key must be a non-empty string")
        
        if not self.key.strip():
            raise ValidationError("Configuration key cannot be empty or whitespace only")

        # Validate value
        if not isinstance(self.value, str):
            raise ValidationError("Configuration value must be a string")

        # Validate data_type
        if self.data_type not in ('string', 'number', 'boolean', 'json'):
            raise ValidationError("Data type must be one of: string, number, boolean, json")

        # Validate value according to data_type (skip validation for empty values during construction)
        if self.value:  # Only validate non-empty values
            try:
                self.get_typed_value()
            except (ValueError, json.JSONDecodeError) as e:
                raise ValidationError(f"Value '{self.value}' is not valid for data type '{self.data_type}': {e}")

    def get_typed_value(self) -> Union[str, float, bool, Dict, list]:
        """
        Get the configuration value converted to its proper type.
        
        Returns:
            The value converted according to data_type
            
        Raises:
            ValueError: If value cannot be converted to the specified type
        """
        if self.data_type == 'string':
            return self.value
        elif self.data_type == 'number':
            return float(self.value)
        elif self.data_type == 'boolean':
            if self.value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif self.value.lower() in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"Cannot convert '{self.value}' to boolean")
        elif self.data_type == 'json':
            return json.loads(self.value)
        else:
            raise ValueError(f"Unknown data type: {self.data_type}")

    def set_typed_value(self, value: Union[str, float, bool, Dict, list]) -> None:
        """
        Set the configuration value from a typed value.
        
        Args:
            value: The value to set, will be converted to string representation
        """
        if self.data_type == 'string':
            self.value = str(value)
        elif self.data_type == 'number':
            self.value = str(float(value))
        elif self.data_type == 'boolean':
            # Handle string-to-boolean conversion properly
            if isinstance(value, str):
                if value.lower() in ('true', '1', 'yes', 'on'):
                    self.value = 'true'
                elif value.lower() in ('false', '0', 'no', 'off'):
                    self.value = 'false'
                else:
                    raise ValueError(f"Cannot convert string '{value}' to boolean")
            else:
                # For non-string values, use standard boolean conversion
                self.value = 'true' if bool(value) else 'false'
        elif self.data_type == 'json':
            self.value = json.dumps(value)
        else:
            raise ValueError(f"Unknown data type: {self.data_type}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for database operations."""
        return {
            'key': self.key,
            'value': self.value,
            'data_type': self.data_type,
            'description': self.description,
            'category': self.category,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Configuration':
        """Create Configuration instance from dictionary."""
        # Convert string dates back to datetime objects
        created_date = None
        if data.get('created_date'):
            created_date = datetime.fromisoformat(data['created_date'])
        
        last_updated = None
        if data.get('last_updated'):
            last_updated = datetime.fromisoformat(data['last_updated'])

        return cls(
            key=data['key'],
            value=data['value'],
            data_type=data.get('data_type', 'string'),
            description=data.get('description'),
            category=data.get('category', 'general'),
            created_date=created_date,
            last_updated=last_updated
        )


@dataclass
class PartDiscoveryLog:
    """
    Represents a part discovery log entry for audit trail.
    
    Attributes:
        id: Auto-incrementing primary key
        part_number: Part number that was discovered/modified
        invoice_number: Invoice where the part was found
        invoice_date: Date of the invoice
        discovered_price: Price found in the invoice
        authorized_price: Authorized price at time of discovery
        action_taken: Action performed
        user_decision: User's decision during interactive discovery
        discovery_date: When the discovery occurred
        processing_session_id: UUID to group discoveries from same processing run
        notes: Additional context or user notes
    """
    part_number: str
    action_taken: Literal['discovered', 'added', 'updated', 'skipped', 'price_mismatch']
    id: Optional[int] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    discovered_price: Optional[Decimal] = None
    authorized_price: Optional[Decimal] = None
    user_decision: Optional[str] = None
    discovery_date: Optional[datetime] = None
    processing_session_id: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        """Validate discovery log data after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate discovery log data according to business rules.
        
        Raises:
            ValidationError: If validation fails
        """
        # Validate part number
        if not self.part_number or not isinstance(self.part_number, str):
            raise ValidationError("Part number must be a non-empty string")

        # Validate action_taken
        valid_actions = ('discovered', 'added', 'updated', 'skipped', 'price_mismatch')
        if self.action_taken not in valid_actions:
            raise ValidationError(f"Action taken must be one of: {', '.join(valid_actions)}")

        # Validate prices if provided
        if self.discovered_price is not None:
            if not isinstance(self.discovered_price, (Decimal, float, int)):
                raise ValidationError("Discovered price must be a number")
            self.discovered_price = Decimal(str(self.discovered_price))
            if self.discovered_price <= 0:
                raise ValidationError("Discovered price must be positive")

        if self.authorized_price is not None:
            if not isinstance(self.authorized_price, (Decimal, float, int)):
                raise ValidationError("Authorized price must be a number")
            self.authorized_price = Decimal(str(self.authorized_price))
            if self.authorized_price <= 0:
                raise ValidationError("Authorized price must be positive")

    def to_dict(self) -> Dict[str, Any]:
        """Convert discovery log to dictionary for database operations."""
        return {
            'id': self.id,
            'part_number': self.part_number,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'discovered_price': float(self.discovered_price) if self.discovered_price else None,
            'authorized_price': float(self.authorized_price) if self.authorized_price else None,
            'action_taken': self.action_taken,
            'user_decision': self.user_decision,
            'discovery_date': self.discovery_date.isoformat() if self.discovery_date else None,
            'processing_session_id': self.processing_session_id,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PartDiscoveryLog':
        """Create PartDiscoveryLog instance from dictionary."""
        # Convert string dates back to datetime objects
        discovery_date = None
        if data.get('discovery_date'):
            discovery_date = datetime.fromisoformat(data['discovery_date'])

        # Convert prices to Decimal if present
        discovered_price = None
        if data.get('discovered_price') is not None:
            discovered_price = Decimal(str(data['discovered_price']))

        authorized_price = None
        if data.get('authorized_price') is not None:
            authorized_price = Decimal(str(data['authorized_price']))

        return cls(
            id=data.get('id'),
            part_number=data['part_number'],
            invoice_number=data.get('invoice_number'),
            invoice_date=data.get('invoice_date'),
            discovered_price=discovered_price,
            authorized_price=authorized_price,
            action_taken=data['action_taken'],
            user_decision=data.get('user_decision'),
            discovery_date=discovery_date,
            processing_session_id=data.get('processing_session_id'),
            notes=data.get('notes')
        )


# Default configuration values
DEFAULT_CONFIG = {
    'validation_mode': Configuration(
        key='validation_mode',
        value='parts_based',
        data_type='string',
        description='Validation mode: parts_based or threshold_based',
        category='validation'
    ),
    'default_output_format': Configuration(
        key='default_output_format',
        value='csv',
        data_type='string',
        description='Default report output format',
        category='reporting'
    ),
    'interactive_discovery': Configuration(
        key='interactive_discovery',
        value='true',
        data_type='boolean',
        description='Enable interactive part discovery during processing',
        category='discovery'
    ),
    'auto_add_discovered_parts': Configuration(
        key='auto_add_discovered_parts',
        value='false',
        data_type='boolean',
        description='Automatically add discovered parts without user confirmation',
        category='discovery'
    ),
    'discovery_batch_mode': Configuration(
        key='discovery_batch_mode',
        value='false',
        data_type='boolean',
        description='Collect unknown parts for batch review instead of interactive prompts',
        category='discovery'
    ),
    'discovery_prompt_timeout': Configuration(
        key='discovery_prompt_timeout',
        value='300',
        data_type='number',
        description='Timeout in seconds for interactive discovery prompts (0 = no timeout)',
        category='discovery'
    ),
    'discovery_max_price_variance': Configuration(
        key='discovery_max_price_variance',
        value='0.10',
        data_type='number',
        description='Maximum price variance threshold for flagging discovered parts',
        category='discovery'
    ),
    'discovery_auto_skip_duplicates': Configuration(
        key='discovery_auto_skip_duplicates',
        value='true',
        data_type='boolean',
        description='Automatically skip parts already discovered in current session',
        category='discovery'
    ),
    'discovery_require_description': Configuration(
        key='discovery_require_description',
        value='false',
        data_type='boolean',
        description='Require description when adding discovered parts',
        category='discovery'
    ),
    'discovery_default_category': Configuration(
        key='discovery_default_category',
        value='discovered',
        data_type='string',
        description='Default category for newly discovered parts',
        category='discovery'
    ),
    'discovery_session_cleanup_days': Configuration(
        key='discovery_session_cleanup_days',
        value='7',
        data_type='number',
        description='Days after which inactive discovery sessions are cleaned up',
        category='discovery'
    ),
    'price_tolerance': Configuration(
        key='price_tolerance',
        value='0.001',
        data_type='number',
        description='Price comparison tolerance for floating point precision',
        category='validation'
    ),
    'backup_retention_days': Configuration(
        key='backup_retention_days',
        value='30',
        data_type='number',
        description='Number of days to retain database backups',
        category='maintenance'
    ),
    'log_retention_days': Configuration(
        key='log_retention_days',
        value='365',
        data_type='number',
        description='Number of days to retain discovery log entries',
        category='maintenance'
    ),
    'database_version': Configuration(
        key='database_version',
        value='1.0',
        data_type='string',
        description='Current database schema version',
        category='system'
    ),
    'default_invoice_location': Configuration(
        key='default_invoice_location',
        value='desktop/invoices/',
        data_type='string',
        description='Default directory path for invoice files',
        category='general'
    ),
    'auto_output_location': Configuration(
        key='auto_output_location',
        value='true',
        data_type='boolean',
        description='Automatically determine output file location',
        category='general'
    ),
    'preconfigured_mode': Configuration(
        key='preconfigured_mode',
        value='false',
        data_type='boolean',
        description='Enable preconfigured processing mode',
        category='general'
    )
}