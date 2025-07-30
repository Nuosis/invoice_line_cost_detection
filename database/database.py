"""
Database layer for the Invoice Rate Detection System.

This module provides the core database functionality including connection management,
initialization, and CRUD operations for all database entities.
"""

import sqlite3
import logging
import shutil
import uuid
import csv
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Tuple
from decimal import Decimal

from database.models import (
    Part, Configuration, PartDiscoveryLog, DEFAULT_CONFIG,
    ValidationError, DatabaseError, PartNotFoundError, ConfigurationError
)


# Configure logging
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Main database manager class that handles all database operations.
    
    This class follows the Repository pattern and provides a clean interface
    for all database operations while handling connection management, transactions,
    and error handling.
    """
    
    def __init__(self, db_path: str = "invoice_detection.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database if it doesn't exist
        if not self.db_path.exists():
            logger.info(f"Creating new database at {self.db_path}")
            self.initialize_database()
        else:
            logger.info(f"Using existing database at {self.db_path}")
            # Verify database integrity
            self._verify_database_schema()

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Ensures proper connection handling and automatic cleanup.
        Enables foreign key constraints and WAL mode for better performance.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Set reasonable timeout
            conn.execute("PRAGMA busy_timeout = 30000")
            
            yield conn
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Automatically handles commit/rollback and provides transaction isolation.
        
        Yields:
            sqlite3.Connection: Database connection within transaction
        """
        with self.get_connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
                logger.debug("Transaction committed successfully")
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back due to error: {e}")
                raise

    def initialize_database(self) -> None:
        """
        Initialize the database with schema and default data.
        
        Creates all tables, indexes, triggers, views, and inserts default configuration.
        
        Raises:
            DatabaseError: If database initialization fails
        """
        try:
            with self.transaction() as conn:
                # Read and execute the migration script
                migration_sql = self._get_migration_sql()
                
                # Execute each statement in the migration
                # Use executescript to handle multi-line statements properly
                conn.executescript(migration_sql)
                
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")

    def _get_migration_sql(self) -> str:
        """
        Get the SQL migration script for database initialization.
        
        Returns:
            str: Complete SQL migration script
        """
        return """
        -- Enable foreign key constraints
        PRAGMA foreign_keys = ON;

        -- Create parts table
        CREATE TABLE parts (
            part_number TEXT PRIMARY KEY,
            authorized_price DECIMAL(10,4) NOT NULL CHECK (authorized_price > 0),
            description TEXT,
            category TEXT,
            source TEXT DEFAULT 'manual' CHECK (source IN ('manual', 'discovered', 'imported')),
            first_seen_invoice TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1 CHECK (is_active IN (0, 1)),
            notes TEXT
        );

        -- Create config table
        CREATE TABLE config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            data_type TEXT DEFAULT 'string' CHECK (data_type IN ('string', 'number', 'boolean', 'json')),
            description TEXT,
            category TEXT DEFAULT 'general',
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create part discovery log table
        CREATE TABLE part_discovery_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            invoice_number TEXT,
            invoice_date TEXT,
            discovered_price DECIMAL(10,4) CHECK (discovered_price IS NULL OR discovered_price > 0),
            authorized_price DECIMAL(10,4) CHECK (authorized_price IS NULL OR authorized_price > 0),
            action_taken TEXT NOT NULL CHECK (action_taken IN ('discovered', 'added', 'updated', 'skipped', 'price_mismatch')),
            user_decision TEXT,
            discovery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processing_session_id TEXT,
            notes TEXT
        );

        -- Create indexes for performance
        CREATE INDEX idx_parts_number ON parts(part_number);
        CREATE INDEX idx_parts_active ON parts(is_active) WHERE is_active = 1;
        CREATE INDEX idx_parts_category ON parts(category);
        CREATE INDEX idx_config_category ON config(category);
        CREATE INDEX idx_discovery_part ON part_discovery_log(part_number);
        CREATE INDEX idx_discovery_invoice ON part_discovery_log(invoice_number);
        CREATE INDEX idx_discovery_date ON part_discovery_log(discovery_date);
        CREATE INDEX idx_discovery_session ON part_discovery_log(processing_session_id);

        -- Insert initial configuration data
        INSERT INTO config (key, value, data_type, description, category) VALUES
        ('validation_mode', 'parts_based', 'string', 'Validation mode: parts_based or threshold_based', 'validation'),
        ('default_output_format', 'csv', 'string', 'Default report output format', 'reporting'),
        ('interactive_discovery', 'true', 'boolean', 'Enable interactive part discovery during processing', 'discovery'),
        ('auto_add_discovered_parts', 'false', 'boolean', 'Automatically add discovered parts without user confirmation', 'discovery'),
        ('price_tolerance', '0.001', 'number', 'Price comparison tolerance for floating point precision', 'validation'),
        ('backup_retention_days', '30', 'number', 'Number of days to retain database backups', 'maintenance'),
        ('log_retention_days', '365', 'number', 'Number of days to retain discovery log entries', 'maintenance'),
        ('database_version', '1.0', 'string', 'Current database schema version', 'system');

        -- Create triggers to update last_updated timestamps
        CREATE TRIGGER update_parts_timestamp
            AFTER UPDATE ON parts
            FOR EACH ROW
            BEGIN
                UPDATE parts SET last_updated = CURRENT_TIMESTAMP WHERE part_number = NEW.part_number;
            END;

        CREATE TRIGGER update_config_timestamp
            AFTER UPDATE ON config
            FOR EACH ROW
            BEGIN
                UPDATE config SET last_updated = CURRENT_TIMESTAMP WHERE key = NEW.key;
            END;

        -- Create view for active parts (commonly used query)
        CREATE VIEW active_parts AS
        SELECT part_number, authorized_price, description, category, source, first_seen_invoice, created_date, last_updated, notes
        FROM parts
        WHERE is_active = 1;

        -- Create view for recent discoveries (last 30 days)
        CREATE VIEW recent_discoveries AS
        SELECT pdl.*, p.description, p.authorized_price as current_authorized_price
        FROM part_discovery_log pdl
        LEFT JOIN parts p ON pdl.part_number = p.part_number
        WHERE pdl.discovery_date >= datetime('now', '-30 days')
        ORDER BY pdl.discovery_date DESC;
        """

    def _verify_database_schema(self) -> None:
        """
        Verify that the database schema is correct and up-to-date.
        
        Raises:
            DatabaseError: If schema verification fails
        """
        try:
            with self.get_connection() as conn:
                # Check if required tables exist
                required_tables = ['parts', 'config', 'part_discovery_log']
                
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = set(required_tables) - set(existing_tables)
                if missing_tables:
                    raise DatabaseError(f"Missing required tables: {missing_tables}")
                
                # Check database version
                try:
                    cursor = conn.execute("SELECT value FROM config WHERE key = 'database_version'")
                    version_row = cursor.fetchone()
                    if not version_row:
                        logger.warning("Database version not found in config")
                    else:
                        logger.info(f"Database version: {version_row[0]}")
                except sqlite3.Error:
                    logger.warning("Could not retrieve database version")
                
                logger.debug("Database schema verification completed successfully")
                
        except Exception as e:
            logger.error(f"Database schema verification failed: {e}")
            raise DatabaseError(f"Schema verification failed: {e}")

    # Parts CRUD Operations
    
    def create_part(self, part: Part) -> Part:
        """
        Create a new part in the database.
        
        Args:
            part: Part instance to create
            
        Returns:
            Part: Created part with updated timestamps
            
        Raises:
            ValidationError: If part data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Validate part data
            part.validate()
            
            with self.get_connection() as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    
                    # Set creation timestamp
                    part.created_date = datetime.now()
                    part.last_updated = part.created_date
                    
                    conn.execute("""
                        INSERT INTO parts (
                            part_number, authorized_price, description, category, source,
                            first_seen_invoice, created_date, last_updated, is_active, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        part.part_number, float(part.authorized_price), part.description,
                        part.category, part.source, part.first_seen_invoice,
                        part.created_date.isoformat(), part.last_updated.isoformat(),
                        part.is_active, part.notes
                    ))
                    
                    conn.commit()
                    logger.info(f"Created part: {part.part_number}")
                    return part
                    
                except sqlite3.IntegrityError as e:
                    conn.rollback()
                    if "UNIQUE constraint failed" in str(e):
                        raise DatabaseError(f"Part {part.part_number} already exists")
                    raise DatabaseError(f"Failed to create part: {e}")
                except Exception as e:
                    conn.rollback()
                    raise
                
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create part {part.part_number}: {e}")
            raise DatabaseError(f"Failed to create part: {e}")

    def get_part(self, part_number: str) -> Part:
        """
        Retrieve a part by part number.
        
        Args:
            part_number: Part number to retrieve
            
        Returns:
            Part: Retrieved part
            
        Raises:
            PartNotFoundError: If part is not found
            DatabaseError: If database operation fails
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT part_number, authorized_price, description, category, source,
                           first_seen_invoice, created_date, last_updated, is_active, notes
                    FROM parts WHERE part_number = ?
                """, (part_number,))
                
                row = cursor.fetchone()
                if not row:
                    raise PartNotFoundError(f"Part {part_number} not found")
                
                return self._row_to_part(row)
                
        except PartNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve part {part_number}: {e}")
            raise DatabaseError(f"Failed to retrieve part: {e}")

    def update_part(self, part_number_or_part: Union[str, Part], **kwargs) -> Part:
        """
        Update an existing part in the database.
        
        Args:
            part_number_or_part: Either a Part instance or part number string
            **kwargs: Fields to update (authorized_price, description, category, etc.)
            
        Returns:
            Part: Updated part with new timestamp
            
        Raises:
            PartNotFoundError: If part is not found
            ValidationError: If part data is invalid
            DatabaseError: If database operation fails
        """
        try:
            if isinstance(part_number_or_part, Part):
                # Original behavior - update with Part instance
                part = part_number_or_part
                part.validate()
                
                with self.transaction() as conn:
                    part.last_updated = datetime.now()
                    
                    cursor = conn.execute("""
                        UPDATE parts SET
                            authorized_price = ?, description = ?, category = ?, source = ?,
                            first_seen_invoice = ?, last_updated = ?, is_active = ?, notes = ?
                        WHERE part_number = ?
                    """, (
                        float(part.authorized_price), part.description, part.category,
                        part.source, part.first_seen_invoice, part.last_updated.isoformat(),
                        part.is_active, part.notes, part.part_number
                    ))
                    
                    if cursor.rowcount == 0:
                        raise PartNotFoundError(f"Part {part.part_number} not found")
                    
                    logger.info(f"Updated part: {part.part_number}")
                    return part
            else:
                # New behavior - update by part number with kwargs
                part_number = part_number_or_part
                
                # Get existing part
                existing_part = self.get_part(part_number)
                
                # Update fields from kwargs
                if 'authorized_price' in kwargs:
                    existing_part.authorized_price = Decimal(str(kwargs['authorized_price']))
                if 'description' in kwargs:
                    existing_part.description = kwargs['description']
                if 'category' in kwargs:
                    existing_part.category = kwargs['category']
                if 'source' in kwargs:
                    existing_part.source = kwargs['source']
                if 'first_seen_invoice' in kwargs:
                    existing_part.first_seen_invoice = kwargs['first_seen_invoice']
                if 'is_active' in kwargs:
                    existing_part.is_active = kwargs['is_active']
                if 'notes' in kwargs:
                    existing_part.notes = kwargs['notes']
                
                # Validate and save
                existing_part.validate()
                
                with self.transaction() as conn:
                    existing_part.last_updated = datetime.now()
                    
                    cursor = conn.execute("""
                        UPDATE parts SET
                            authorized_price = ?, description = ?, category = ?, source = ?,
                            first_seen_invoice = ?, last_updated = ?, is_active = ?, notes = ?
                        WHERE part_number = ?
                    """, (
                        float(existing_part.authorized_price), existing_part.description, existing_part.category,
                        existing_part.source, existing_part.first_seen_invoice, existing_part.last_updated.isoformat(),
                        existing_part.is_active, existing_part.notes, existing_part.part_number
                    ))
                    
                    if cursor.rowcount == 0:
                        raise PartNotFoundError(f"Part {part_number} not found")
                    
                    logger.info(f"Updated part: {part_number}")
                    return existing_part
                
        except PartNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update part: {e}")
            raise DatabaseError(f"Failed to update part: {e}")

    def delete_part(self, part_number: str, soft_delete: bool = True) -> None:
        """
        Delete a part from the database.
        
        Args:
            part_number: Part number to delete
            soft_delete: If True, mark as inactive; if False, permanently delete
            
        Raises:
            PartNotFoundError: If part is not found
            DatabaseError: If database operation fails
        """
        try:
            with self.transaction() as conn:
                if soft_delete:
                    # Soft delete - mark as inactive
                    cursor = conn.execute("""
                        UPDATE parts SET is_active = 0, last_updated = CURRENT_TIMESTAMP
                        WHERE part_number = ?
                    """, (part_number,))
                    
                    if cursor.rowcount == 0:
                        raise PartNotFoundError(f"Part {part_number} not found")
                    
                    logger.info(f"Soft deleted part: {part_number}")
                else:
                    # Hard delete - permanently remove
                    cursor = conn.execute("DELETE FROM parts WHERE part_number = ?", (part_number,))
                    
                    if cursor.rowcount == 0:
                        raise PartNotFoundError(f"Part {part_number} not found")
                    
                    logger.info(f"Hard deleted part: {part_number}")
                    
        except PartNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete part {part_number}: {e}")
            raise DatabaseError(f"Failed to delete part: {e}")

    def list_parts(self, active_only: bool = False, category: Optional[str] = None,
                   limit: Optional[int] = None, offset: int = 0) -> List[Part]:
        """
        List parts with optional filtering.
        
        Args:
            active_only: If True, only return active parts; if False, return all parts
            category: Optional category filter
            limit: Maximum number of parts to return
            offset: Number of parts to skip
            
        Returns:
            List[Part]: List of parts matching criteria
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT part_number, authorized_price, description, category, source,
                           first_seen_invoice, created_date, last_updated, is_active, notes
                    FROM parts
                    WHERE 1=1
                """
                params = []
                
                if active_only:
                    query += " AND is_active = 1"
                
                if category:
                    query += " AND category = ?"
                    params.append(category)
                
                query += " ORDER BY part_number"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                    
                    if offset > 0:
                        query += " OFFSET ?"
                        params.append(offset)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._row_to_part(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list parts: {e}")
            raise DatabaseError(f"Failed to list parts: {e}")

    def _row_to_part(self, row: sqlite3.Row) -> Part:
        """
        Convert a database row to a Part instance.
        
        Args:
            row: Database row
            
        Returns:
            Part: Part instance
        """
        created_date = None
        if row['created_date']:
            created_date = datetime.fromisoformat(row['created_date'])
        
        last_updated = None
        if row['last_updated']:
            last_updated = datetime.fromisoformat(row['last_updated'])
        
        return Part(
            part_number=row['part_number'],
            authorized_price=Decimal(str(row['authorized_price'])),
            description=row['description'],
            category=row['category'],
            source=row['source'],
            first_seen_invoice=row['first_seen_invoice'],
            created_date=created_date,
            last_updated=last_updated,
            is_active=bool(row['is_active']),
            notes=row['notes']
        )

    # Database utility methods
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics and information.
        
        Returns:
            Dict[str, Any]: Database statistics
        """
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Get table counts
                cursor = conn.execute("SELECT COUNT(*) FROM parts")
                stats['total_parts'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM parts WHERE is_active = 1")
                stats['active_parts'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM config")
                stats['config_entries'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM part_discovery_log")
                stats['discovery_log_entries'] = cursor.fetchone()[0]
                
                # Get database file size
                stats['database_size_bytes'] = self.db_path.stat().st_size
                
                # Get database version
                cursor = conn.execute("SELECT value FROM config WHERE key = 'database_version'")
                version_row = cursor.fetchone()
                stats['database_version'] = version_row[0] if version_row else 'unknown'
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise DatabaseError(f"Failed to get database stats: {e}")

    def vacuum_database(self) -> None:
        """
        Vacuum the database to reclaim space and optimize performance.
        
        Raises:
            DatabaseError: If vacuum operation fails
        """
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("Database vacuum completed successfully")
                
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
            raise DatabaseError(f"Failed to vacuum database: {e}")

    # Configuration CRUD Operations
    
    def create_config(self, config: Configuration) -> Configuration:
        """
        Create a new configuration setting.
        
        Args:
            config: Configuration instance to create
            
        Returns:
            Configuration: Created configuration with updated timestamps
            
        Raises:
            ValidationError: If configuration data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Validate configuration data
            config.validate()
            
            with self.get_connection() as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    
                    # Set creation timestamp
                    config.created_date = datetime.now()
                    config.last_updated = config.created_date
                    
                    conn.execute("""
                        INSERT INTO config (key, value, data_type, description, category, created_date, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        config.key, config.value, config.data_type, config.description,
                        config.category, config.created_date.isoformat(), config.last_updated.isoformat()
                    ))
                    
                    conn.commit()
                    logger.info(f"Created configuration: {config.key}")
                    return config
                    
                except sqlite3.IntegrityError as e:
                    conn.rollback()
                    if "UNIQUE constraint failed" in str(e):
                        raise ValidationError(f"Configuration key {config.key} already exists")
                    raise DatabaseError(f"Failed to create configuration: {e}")
                except Exception as e:
                    conn.rollback()
                    raise
                
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create configuration {config.key}: {e}")
            raise DatabaseError(f"Failed to create configuration: {e}")

    def get_config(self, key: str) -> Configuration:
        """
        Retrieve a configuration setting by key.
        
        Args:
            key: Configuration key to retrieve
            
        Returns:
            Configuration: Retrieved configuration
            
        Raises:
            ConfigurationError: If configuration is not found
            DatabaseError: If database operation fails
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT key, value, data_type, description, category, created_date, last_updated
                    FROM config WHERE key = ?
                """, (key,))
                
                row = cursor.fetchone()
                if not row:
                    raise ConfigurationError(f"Configuration key {key} not found")
                
                return self._row_to_config(row)
                
        except ConfigurationError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve configuration {key}: {e}")
            raise DatabaseError(f"Failed to retrieve configuration: {e}")

    def update_config(self, config: Configuration) -> Configuration:
        """
        Update an existing configuration setting.
        
        Args:
            config: Configuration instance with updated data
            
        Returns:
            Configuration: Updated configuration with new timestamp
            
        Raises:
            ConfigurationError: If configuration is not found
            ValidationError: If configuration data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Validate configuration data
            config.validate()
            
            with self.transaction() as conn:
                # Update timestamp
                config.last_updated = datetime.now()
                
                cursor = conn.execute("""
                    UPDATE config SET
                        value = ?, data_type = ?, description = ?, category = ?, last_updated = ?
                    WHERE key = ?
                """, (
                    config.value, config.data_type, config.description,
                    config.category, config.last_updated.isoformat(), config.key
                ))
                
                if cursor.rowcount == 0:
                    raise ConfigurationError(f"Configuration key {config.key} not found")
                
                logger.info(f"Updated configuration: {config.key}")
                return config
                
        except ConfigurationError:
            raise
        except Exception as e:
            logger.error(f"Failed to update configuration {config.key}: {e}")
            raise DatabaseError(f"Failed to update configuration: {e}")

    def delete_config(self, key: str) -> None:
        """
        Delete a configuration setting.
        
        Args:
            key: Configuration key to delete
            
        Raises:
            ConfigurationError: If configuration is not found
            DatabaseError: If database operation fails
        """
        try:
            with self.transaction() as conn:
                cursor = conn.execute("DELETE FROM config WHERE key = ?", (key,))
                
                if cursor.rowcount == 0:
                    raise ConfigurationError(f"Configuration key {key} not found")
                
                logger.info(f"Deleted configuration: {key}")
                
        except ConfigurationError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete configuration {key}: {e}")
            raise DatabaseError(f"Failed to delete configuration: {e}")

    def list_config(self, category: Optional[str] = None) -> List[Configuration]:
        """
        List configuration settings with optional category filter.
        
        Args:
            category: Optional category filter
            
        Returns:
            List[Configuration]: List of configurations matching criteria
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with self.get_connection() as conn:
                if category:
                    cursor = conn.execute("""
                        SELECT key, value, data_type, description, category, created_date, last_updated
                        FROM config WHERE category = ? ORDER BY key
                    """, (category,))
                else:
                    cursor = conn.execute("""
                        SELECT key, value, data_type, description, category, created_date, last_updated
                        FROM config ORDER BY key
                    """)
                
                rows = cursor.fetchall()
                return [self._row_to_config(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list configurations: {e}")
            raise DatabaseError(f"Failed to list configurations: {e}")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with automatic type conversion.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Any: Configuration value converted to proper type, or default
            
        Raises:
            DatabaseError: If key not found and no default provided
        """
        try:
            config = self.get_config(key)
            return config.get_typed_value()
        except ConfigurationError:
            if default is None:
                raise DatabaseError(f"Configuration key '{key}' not found")
            return default

    def set_config_value(self, key: str, value: Any, data_type: Optional[str] = None,
                        description: Optional[str] = None, category: str = 'general') -> None:
        """
        Set a configuration value with automatic type detection and validation.
        
        Args:
            key: Configuration key
            value: Value to set
            data_type: Optional explicit data type
            description: Optional description
            category: Configuration category
            
        Raises:
            ValidationError: If value is invalid for the configuration
        """
        # Track whether data_type was explicitly provided
        explicit_data_type = data_type is not None
        
        # Auto-detect data type if not provided
        if data_type is None:
            if isinstance(value, bool):
                data_type = 'boolean'
            elif isinstance(value, (int, float)):
                data_type = 'number'
            elif isinstance(value, (dict, list)):
                data_type = 'json'
            else:
                data_type = 'string'
        
        # Validate specific configuration values
        self._validate_config_value(key, value, data_type)
        
        config = Configuration(
            key=key,
            value='',  # Will be set by set_typed_value
            data_type=data_type,
            description=description,
            category=category
        )
        config.set_typed_value(value)
        
        try:
            # Try to update existing config
            existing_config = self.get_config(key)
            
            # For existing configs, preserve the original data type unless explicitly overridden
            if not explicit_data_type:
                # Use the existing configuration's data type
                original_data_type = existing_config.data_type
                # Re-validate with the original data type
                self._validate_config_value(key, value, original_data_type)
                
                # Create a temporary config with the original data type for conversion
                temp_config = Configuration(
                    key=key,
                    value='',
                    data_type=original_data_type,
                    description=existing_config.description,
                    category=existing_config.category
                )
                temp_config.set_typed_value(value)
                existing_config.value = temp_config.value
                existing_config.data_type = original_data_type
            else:
                # Use the explicitly provided data type
                existing_config.set_typed_value(value)
                existing_config.data_type = data_type
            
            if description:
                existing_config.description = description
            if category != 'general':
                existing_config.category = category
            self.update_config(existing_config)
        except ConfigurationError:
            # Create new config if it doesn't exist
            self.create_config(config)
    
    def _validate_config_value(self, key: str, value: Any, data_type: str) -> None:
        """
        Validate configuration values according to business rules.
        
        Args:
            key: Configuration key
            value: Value to validate
            data_type: Expected data type
            
        Raises:
            ValidationError: If value is invalid
        """
        # Validate data type conversion
        if data_type == 'boolean':
            if isinstance(value, str):
                if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                    raise ValidationError(f"Invalid boolean value: '{value}'. Must be true/false, 1/0, yes/no, or on/off")
            elif not isinstance(value, bool):
                raise ValidationError(f"Invalid boolean value: '{value}'. Must be a boolean or valid string representation")
        
        elif data_type == 'number':
            try:
                float_value = float(value)
                # Validate specific numeric constraints
                if key in ('log_retention_days', 'backup_retention_days') and float_value < 0:
                    raise ValidationError(f"Value for '{key}' must be non-negative")
                if key == 'price_tolerance' and (float_value < 0 or float_value > 1):
                    raise ValidationError(f"Price tolerance must be between 0 and 1")
            except (ValueError, TypeError):
                raise ValidationError(f"Invalid number value: '{value}'. Must be a valid number")
        
        # Validate specific configuration keys
        if key == 'validation_mode':
            valid_modes = ('parts_based', 'threshold_based')
            if value not in valid_modes:
                raise ValidationError(f"Invalid validation mode: '{value}'. Must be one of: {', '.join(valid_modes)}")
        
        elif key == 'default_output_format':
            valid_formats = ('csv', 'json', 'txt')
            if value not in valid_formats:
                raise ValidationError(f"Invalid output format: '{value}'. Must be one of: {', '.join(valid_formats)}")

    def reset_config_to_default(self, key: str) -> bool:
        """
        Reset a configuration value to its default.
        
        Args:
            key: Configuration key to reset
            
        Returns:
            bool: True if reset successful, False otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Define default configurations
            default_configs = {
                'validation_mode': 'parts_based',
                'default_output_format': 'csv',
                'interactive_discovery': 'true',
                'auto_add_discovered_parts': 'false',
                'price_tolerance': '0.001',
                'backup_retention_days': '30',
                'log_retention_days': '365',
                'database_version': '1.0'
            }
            
            if key not in default_configs:
                raise DatabaseError(f"No default value defined for configuration key: {key}")
            
            default_value = default_configs[key]
            
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "UPDATE config SET value = ? WHERE key = ?",
                    (default_value, key)
                )
                
                if cursor.rowcount == 0:
                    raise DatabaseError(f"Configuration key '{key}' not found")
                
                conn.commit()
                logger.info(f"Reset configuration '{key}' to default value: {default_value}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to reset configuration '{key}': {e}")
            raise DatabaseError(f"Failed to reset configuration: {e}")

    def _row_to_config(self, row: sqlite3.Row) -> Configuration:
        """
        Convert a database row to a Configuration instance.
        
        Args:
            row: Database row
            
        Returns:
            Configuration: Configuration instance
        """
        created_date = None
        if row['created_date']:
            created_date = datetime.fromisoformat(row['created_date'])
        
        last_updated = None
        if row['last_updated']:
            last_updated = datetime.fromisoformat(row['last_updated'])
        
        return Configuration(
            key=row['key'],
            value=row['value'],
            data_type=row['data_type'],
            description=row['description'],
            category=row['category'],
            created_date=created_date,
            last_updated=last_updated
        )

    # Part Discovery Log Operations
    
    def create_discovery_log(self, log_entry: PartDiscoveryLog) -> PartDiscoveryLog:
        """
        Create a new part discovery log entry.
        
        Args:
            log_entry: PartDiscoveryLog instance to create
            
        Returns:
            PartDiscoveryLog: Created log entry with ID and timestamp
            
        Raises:
            ValidationError: If log entry data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Validate log entry data
            log_entry.validate()
            
            with self.transaction() as conn:
                # Set discovery timestamp if not provided
                if log_entry.discovery_date is None:
                    log_entry.discovery_date = datetime.now()
                
                cursor = conn.execute("""
                    INSERT INTO part_discovery_log (
                        part_number, invoice_number, invoice_date, discovered_price,
                        authorized_price, action_taken, user_decision, discovery_date,
                        processing_session_id, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_entry.part_number, log_entry.invoice_number, log_entry.invoice_date,
                    float(log_entry.discovered_price) if log_entry.discovered_price else None,
                    float(log_entry.authorized_price) if log_entry.authorized_price else None,
                    log_entry.action_taken, log_entry.user_decision,
                    log_entry.discovery_date.isoformat(), log_entry.processing_session_id,
                    log_entry.notes
                ))
                
                log_entry.id = cursor.lastrowid
                logger.debug(f"Created discovery log entry: {log_entry.id}")
                return log_entry
                
        except Exception as e:
            logger.error(f"Failed to create discovery log entry: {e}")
            raise DatabaseError(f"Failed to create discovery log entry: {e}")

    def get_discovery_logs(self, part_number: Optional[str] = None,
                          invoice_number: Optional[str] = None,
                          session_id: Optional[str] = None,
                          days_back: Optional[int] = None,
                          limit: Optional[int] = None) -> List[PartDiscoveryLog]:
        """
        Retrieve discovery log entries with optional filtering.
        
        Args:
            part_number: Filter by part number
            invoice_number: Filter by invoice number
            session_id: Filter by processing session ID
            days_back: Filter to entries within this many days
            limit: Maximum number of entries to return
            
        Returns:
            List[PartDiscoveryLog]: List of discovery log entries
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT id, part_number, invoice_number, invoice_date, discovered_price,
                           authorized_price, action_taken, user_decision, discovery_date,
                           processing_session_id, notes
                    FROM part_discovery_log
                    WHERE 1=1
                """
                params = []
                
                if part_number:
                    query += " AND part_number = ?"
                    params.append(part_number)
                
                if invoice_number:
                    query += " AND invoice_number = ?"
                    params.append(invoice_number)
                
                if session_id:
                    query += " AND processing_session_id = ?"
                    params.append(session_id)
                
                if days_back:
                    query += " AND discovery_date >= datetime('now', '-{} days')".format(days_back)
                
                query += " ORDER BY discovery_date DESC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._row_to_discovery_log(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to retrieve discovery logs: {e}")
            raise DatabaseError(f"Failed to retrieve discovery logs: {e}")

    def cleanup_old_discovery_logs(self, retention_days: int = 365) -> int:
        """
        Clean up old discovery log entries based on retention policy.
        
        Args:
            retention_days: Number of days to retain log entries
            
        Returns:
            int: Number of entries deleted
            
        Raises:
            DatabaseError: If cleanup operation fails
        """
        try:
            with self.transaction() as conn:
                cursor = conn.execute("""
                    DELETE FROM part_discovery_log
                    WHERE discovery_date < datetime('now', '-{} days')
                """.format(retention_days))
                
                deleted_count = cursor.rowcount
                logger.info(f"Cleaned up {deleted_count} old discovery log entries")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup discovery logs: {e}")
            raise DatabaseError(f"Failed to cleanup discovery logs: {e}")

    def _row_to_discovery_log(self, row: sqlite3.Row) -> PartDiscoveryLog:
        """
        Convert a database row to a PartDiscoveryLog instance.
        
        Args:
            row: Database row
            
        Returns:
            PartDiscoveryLog: PartDiscoveryLog instance
        """
        discovery_date = None
        if row['discovery_date']:
            discovery_date = datetime.fromisoformat(row['discovery_date'])
        
        discovered_price = None
        if row['discovered_price'] is not None:
            discovered_price = Decimal(str(row['discovered_price']))
        
        authorized_price = None
        if row['authorized_price'] is not None:
            authorized_price = Decimal(str(row['authorized_price']))
        
        return PartDiscoveryLog(
            id=row['id'],
            part_number=row['part_number'],
            invoice_number=row['invoice_number'],
            invoice_date=row['invoice_date'],
            discovered_price=discovered_price,
            authorized_price=authorized_price,
            action_taken=row['action_taken'],
            user_decision=row['user_decision'],
            discovery_date=discovery_date,
            processing_session_id=row['processing_session_id'],
            notes=row['notes']
        )

    # Backup and Restore Operations
    
    def create_backup(self, backup_path: Optional[str] = None) -> str:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Optional custom backup path
            
        Returns:
            str: Path to the created backup file
            
        Raises:
            DatabaseError: If backup operation fails
        """
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.db_path.stem}_backup_{timestamp}.db"
            
            backup_path = Path(backup_path)
            
            # Create backup directory if needed
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Database backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise DatabaseError(f"Failed to create backup: {e}")

    def restore_backup(self, backup_path: str) -> None:
        """
        Restore database from a backup file.
        
        Args:
            backup_path: Path to the backup file
            
        Raises:
            DatabaseError: If restore operation fails
        """
        try:
            backup_path = Path(backup_path)
            
            if not backup_path.exists():
                raise DatabaseError(f"Backup file not found: {backup_path}")
            
            # Create a backup of current database before restore
            current_backup = self.create_backup(f"{self.db_path.stem}_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            logger.info(f"Created pre-restore backup: {current_backup}")
            
            # Replace current database with backup
            shutil.copy2(backup_path, self.db_path)
            
            # Verify restored database
            self._verify_database_schema()
            
            logger.info(f"Database restored from backup: {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            raise DatabaseError(f"Failed to restore backup: {e}")

    def cleanup_old_backups(self, backup_dir: str, retention_days: int = 30) -> int:
        """
        Clean up old backup files based on retention policy.
        
        Args:
            backup_dir: Directory containing backup files
            retention_days: Number of days to retain backup files
            
        Returns:
            int: Number of backup files deleted
            
        Raises:
            DatabaseError: If cleanup operation fails
        """
        try:
            backup_dir = Path(backup_dir)
            if not backup_dir.exists():
                return 0
            
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            deleted_count = 0
            
            # Find and delete old backup files
            for backup_file in backup_dir.glob("*_backup_*.db"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old backup: {backup_file}")
            
            logger.info(f"Cleaned up {deleted_count} old backup files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            raise DatabaseError(f"Failed to cleanup old backups: {e}")

    # CSV Import/Export Operations
    
    def import_parts_from_csv(self, csv_file_path: str, update_existing: bool = False) -> int:
        """
        Import parts from a CSV file.
        
        Args:
            csv_file_path: Path to the CSV file
            update_existing: If True, update existing parts; if False, skip duplicates
            
        Returns:
            int: Number of parts imported
            
        Raises:
            DatabaseError: If import operation fails
        """
        try:
            csv_path = Path(csv_file_path)
            if not csv_path.exists():
                raise DatabaseError(f"CSV file not found: {csv_file_path}")
            
            imported_count = 0
            
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    try:
                        # Create Part from CSV row
                        part = Part(
                            part_number=row['part_number'],
                            authorized_price=Decimal(str(row['authorized_price'])),
                            description=row.get('description', ''),
                            category=row.get('category', ''),
                            source=row.get('source', 'imported'),
                            first_seen_invoice=row.get('first_seen_invoice', ''),
                            notes=row.get('notes', '')
                        )
                        
                        # Handle is_active field
                        if 'is_active' in row:
                            part.is_active = str(row['is_active']).lower() in ('true', '1', 'yes')
                        
                        try:
                            # Try to create new part
                            self.create_part(part)
                            imported_count += 1
                            logger.debug(f"Imported part: {part.part_number}")
                        except DatabaseError as e:
                            if "already exists" in str(e) and update_existing:
                                # Update existing part
                                self.update_part(part)
                                imported_count += 1
                                logger.debug(f"Updated existing part: {part.part_number}")
                            else:
                                logger.warning(f"Skipped part {part.part_number}: {e}")
                                
                    except Exception as e:
                        logger.error(f"Failed to import row {row}: {e}")
                        continue
            
            logger.info(f"Imported {imported_count} parts from {csv_file_path}")
            return imported_count
            
        except Exception as e:
            logger.error(f"Failed to import CSV file {csv_file_path}: {e}")
            raise DatabaseError(f"Failed to import CSV file: {e}")
    
    def export_parts_to_csv(self, csv_file_path: str, active_only: bool = False,
                           category: Optional[str] = None) -> int:
        """
        Export parts to a CSV file.
        
        Args:
            csv_file_path: Path to the output CSV file
            active_only: If True, only export active parts
            category: Optional category filter
            
        Returns:
            int: Number of parts exported
            
        Raises:
            DatabaseError: If export operation fails
        """
        try:
            csv_path = Path(csv_file_path)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get parts to export
            parts = self.list_parts(active_only=active_only, category=category)
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'part_number', 'authorized_price', 'description', 'category',
                    'source', 'first_seen_invoice', 'created_date', 'last_updated',
                    'is_active', 'notes'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                for part in parts:
                    writer.writerow({
                        'part_number': part.part_number,
                        'authorized_price': f"{part.authorized_price:.2f}",
                        'description': part.description or '',
                        'category': part.category or '',
                        'source': part.source or '',
                        'first_seen_invoice': part.first_seen_invoice or '',
                        'created_date': part.created_date.isoformat() if part.created_date else '',
                        'last_updated': part.last_updated.isoformat() if part.last_updated else '',
                        'is_active': str(part.is_active).lower(),
                        'notes': part.notes or ''
                    })
            
            logger.info(f"Exported {len(parts)} parts to {csv_file_path}")
            return len(parts)
            
        except Exception as e:
            logger.error(f"Failed to export parts to CSV {csv_file_path}: {e}")
            raise DatabaseError(f"Failed to export parts to CSV: {e}")
    
    # Parts Statistics Operations
    
    def get_parts_statistics(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive parts statistics.
        
        Args:
            category: Optional category filter
            
        Returns:
            Dict[str, Any]: Statistics dictionary
            
        Raises:
            DatabaseError: If statistics operation fails
        """
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Base query conditions
                where_clause = "WHERE 1=1"
                params = []
                
                if category:
                    where_clause += " AND category = ?"
                    params.append(category)
                
                # Total parts count
                cursor = conn.execute(f"SELECT COUNT(*) FROM parts {where_clause}", params)
                stats['total_parts'] = cursor.fetchone()[0]
                
                # Active parts count
                active_where = where_clause + " AND is_active = 1"
                cursor = conn.execute(f"SELECT COUNT(*) FROM parts {active_where}", params)
                stats['active_parts'] = cursor.fetchone()[0]
                
                # Inactive parts count
                stats['inactive_parts'] = stats['total_parts'] - stats['active_parts']
                
                if not category:
                    # Category breakdown (only if not filtering by category)
                    cursor = conn.execute("""
                        SELECT category, COUNT(*) as count
                        FROM parts
                        WHERE category IS NOT NULL AND category != ''
                        GROUP BY category
                        ORDER BY count DESC
                    """)
                    category_breakdown = {}
                    for row in cursor.fetchall():
                        category_breakdown[row[0]] = row[1]
                    
                    stats['category_breakdown'] = category_breakdown
                    stats['categories_count'] = len(category_breakdown)
                    
                    # Price statistics
                    cursor = conn.execute("""
                        SELECT
                            MIN(authorized_price) as min_price,
                            MAX(authorized_price) as max_price,
                            AVG(authorized_price) as avg_price
                        FROM parts
                        WHERE is_active = 1
                    """)
                    price_row = cursor.fetchone()
                    if price_row and price_row[0] is not None:
                        stats['price_statistics'] = {
                            'min_price': float(price_row[0]),
                            'max_price': float(price_row[1]),
                            'avg_price': round(float(price_row[2]), 2)
                        }
                else:
                    stats['categories_count'] = 1 if stats['total_parts'] > 0 else 0
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get parts statistics: {e}")
            raise DatabaseError(f"Failed to get parts statistics: {e}")

    def run_maintenance(self, vacuum: bool = True, cleanup_logs: bool = True,
                       verify_integrity: bool = True, auto_backup: bool = False,
                       backup_dir: str = None) -> Dict[str, Any]:
        """
        Run database maintenance operations.
        
        Args:
            vacuum: Whether to vacuum the database
            cleanup_logs: Whether to cleanup old discovery logs
            verify_integrity: Whether to verify database integrity
            auto_backup: Whether to create a backup before maintenance
            backup_dir: Directory for backup files
            
        Returns:
            Dict[str, Any]: Results of maintenance operations
        """
        results = {
            'success': True,
            'operations_performed': [],
            'vacuum_performed': False,
            'integrity_check_passed': True,
            'integrity_issues': [],
            'logs_cleaned': 0,
            'backup_created': False
        }
        
        try:
            # Create backup if requested
            if auto_backup:
                if backup_dir:
                    backup_path = Path(backup_dir) / f"pre_maintenance_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    backup_result = self.create_backup(str(backup_path))
                    results['backup_created'] = True
                    results['backup_path'] = backup_result
                    results['operations_performed'].append('backup')
            
            # Vacuum database
            if vacuum:
                self.vacuum_database()
                results['vacuum_performed'] = True
                results['operations_performed'].append('vacuum')
            
            # Cleanup old logs
            if cleanup_logs:
                retention_days = int(self.get_config_value('log_retention_days', 365))
                cleaned_count = self.cleanup_old_discovery_logs(retention_days)
                results['logs_cleaned'] = cleaned_count
                results['operations_performed'].append('cleanup_logs')
            
            # Verify integrity
            if verify_integrity:
                try:
                    with self.get_connection() as conn:
                        cursor = conn.execute("PRAGMA integrity_check")
                        integrity_result = cursor.fetchone()[0]
                        if integrity_result != 'ok':
                            results['integrity_check_passed'] = False
                            results['integrity_issues'].append(integrity_result)
                        results['operations_performed'].append('integrity_check')
                except Exception as e:
                    results['integrity_check_passed'] = False
                    results['integrity_issues'].append(f"Integrity check failed: {e}")
            
            logger.info(f"Maintenance completed: {results['operations_performed']}")
            return results
            
        except Exception as e:
            logger.error(f"Maintenance operation failed: {e}")
            results['success'] = False
            results['error'] = str(e)
            return results
    
    def list_discovery_logs(self, limit: Optional[int] = None) -> List[PartDiscoveryLog]:
        """
        List discovery log entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List[PartDiscoveryLog]: List of discovery log entries
        """
        return self.get_discovery_logs(limit=limit)

    def close(self) -> None:
        """
        Close the database manager and perform any necessary cleanup.
        
        This method is provided for compatibility with test frameworks and
        other code that expects a close() method. Since this class uses
        context managers for connection handling, there's no persistent
        connection to close, but this method can be used for any future
        cleanup operations.
        """
        # Currently no persistent connections to close since we use context managers
        # This method is here for compatibility and future extensibility
        logger.debug("DatabaseManager close() called - no persistent connections to close")
        pass
    
    def import_parts_with_error_handling(self, csv_file_path: str, update_existing: bool = False) -> Dict[str, Any]:
        """
        Import parts from a CSV file with comprehensive error handling.
        
        This method wraps the standard import_parts_from_csv method with additional
        error handling to provide detailed error information for e2e testing.
        
        Args:
            csv_file_path: Path to the CSV file
            update_existing: If True, update existing parts; if False, skip duplicates
            
        Returns:
            Dict containing import results and error information
        """
        result = {
            'success': False,
            'errors': [],
            'valid_rows_processed': 0,
            'invalid_rows_skipped': 0,
            'total_rows': 0,
            'processing_time': 0
        }
        
        import time
        import csv as csv_module
        from pathlib import Path
        from decimal import InvalidOperation
        
        start_time = time.time()
        
        try:
            csv_path = Path(csv_file_path)
            if not csv_path.exists():
                result['errors'].append(f"CSV file not found: {csv_file_path}")
                return result
            
            # Count total rows first
            try:
                with open(csv_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv_module.DictReader(csvfile)
                    result['total_rows'] = sum(1 for _ in reader)
            except Exception as e:
                result['errors'].append(f"Failed to read CSV file: {e}")
                return result
            
            # Process the CSV with error handling
            try:
                with open(csv_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv_module.DictReader(csvfile)
                    
                    for row_num, row in enumerate(reader, 1):
                        try:
                            # Validate required fields
                            if 'part_number' not in row or not row['part_number']:
                                result['errors'].append(f"Row {row_num}: Missing part_number")
                                result['invalid_rows_skipped'] += 1
                                continue
                            
                            if 'authorized_price' not in row or not row['authorized_price']:
                                result['errors'].append(f"Row {row_num}: Missing authorized_price")
                                result['invalid_rows_skipped'] += 1
                                continue
                            
                            # Try to parse price
                            try:
                                price = Decimal(str(row['authorized_price']))
                                if price <= 0:
                                    result['errors'].append(f"Row {row_num}: Invalid price (must be positive)")
                                    result['invalid_rows_skipped'] += 1
                                    continue
                            except (ValueError, InvalidOperation):
                                result['errors'].append(f"Row {row_num}: Invalid price format")
                                result['invalid_rows_skipped'] += 1
                                continue
                            
                            # Create Part from CSV row
                            part = Part(
                                part_number=row['part_number'],
                                authorized_price=price,
                                description=row.get('description', ''),
                                category=row.get('category', ''),
                                source=row.get('source', 'imported'),
                                first_seen_invoice=row.get('first_seen_invoice', ''),
                                notes=row.get('notes', '')
                            )
                            
                            # Handle is_active field
                            if 'is_active' in row:
                                part.is_active = str(row['is_active']).lower() in ('true', '1', 'yes')
                            
                            try:
                                # Try to create new part
                                self.create_part(part)
                                result['valid_rows_processed'] += 1
                                logger.debug(f"Imported part: {part.part_number}")
                            except DatabaseError as e:
                                if "already exists" in str(e) and update_existing:
                                    # Update existing part
                                    try:
                                        self.update_part(part)
                                        result['valid_rows_processed'] += 1
                                        logger.debug(f"Updated existing part: {part.part_number}")
                                    except Exception as update_error:
                                        result['errors'].append(f"Row {row_num}: Failed to update {part.part_number}: {update_error}")
                                        result['invalid_rows_skipped'] += 1
                                else:
                                    result['errors'].append(f"Row {row_num}: {e}")
                                    result['invalid_rows_skipped'] += 1
                                    
                        except Exception as e:
                            result['errors'].append(f"Row {row_num}: Unexpected error: {e}")
                            result['invalid_rows_skipped'] += 1
                            continue
                
                # Determine success based on results
                if result['valid_rows_processed'] > 0:
                    result['success'] = True
                elif result['total_rows'] == 0:
                    result['success'] = True  # Empty file is technically successful
                    result['errors'].append("CSV file is empty")
                
                result['processing_time'] = time.time() - start_time
                
                logger.info(f"CSV import completed: {result['valid_rows_processed']} processed, {result['invalid_rows_skipped']} skipped")
                return result
                
            except Exception as e:
                result['errors'].append(f"Failed to process CSV content: {e}")
                result['processing_time'] = time.time() - start_time
                return result
                
        except Exception as e:
            result['errors'].append(f"Import operation failed: {e}")
            result['processing_time'] = time.time() - start_time
            logger.error(f"Failed to import CSV file {csv_file_path}: {e}")
            return result