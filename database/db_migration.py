"""
Database migration script for the Invoice Rate Detection System.

This script handles database schema creation, updates, and data migration.
It can be run standalone or imported as a module.
"""

import sqlite3
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseMigration:
    """
    Handles database schema migrations and updates.
    """
    
    def __init__(self, db_path: str = "invoice_detection.db"):
        """
        Initialize the migration manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.migrations = self._get_migrations()
    
    def _get_migrations(self) -> Dict[str, str]:
        """
        Get all available migrations.
        
        Returns:
            Dict[str, str]: Migration version to SQL mapping
        """
        return {
            "1.0": self._get_initial_schema()
        }
    
    def _get_initial_schema(self) -> str:
        """
        Get the initial database schema (version 1.0).
        
        Returns:
            str: SQL for initial schema creation
        """
        return """
        -- Invoice Rate Detection System - Database Migration Script
        -- Version: 1.0
        -- Description: Initial database schema creation

        -- Enable foreign key constraints
        PRAGMA foreign_keys = ON;

        -- Create parts table
        CREATE TABLE IF NOT EXISTS parts (
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
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            data_type TEXT DEFAULT 'string' CHECK (data_type IN ('string', 'number', 'boolean', 'json')),
            description TEXT,
            category TEXT DEFAULT 'general',
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create part discovery log table
        CREATE TABLE IF NOT EXISTS part_discovery_log (
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
            notes TEXT,
            FOREIGN KEY (part_number) REFERENCES parts(part_number) ON DELETE SET NULL
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_parts_number ON parts(part_number);
        CREATE INDEX IF NOT EXISTS idx_parts_active ON parts(is_active) WHERE is_active = 1;
        CREATE INDEX IF NOT EXISTS idx_parts_category ON parts(category);
        CREATE INDEX IF NOT EXISTS idx_config_category ON config(category);
        CREATE INDEX IF NOT EXISTS idx_discovery_part ON part_discovery_log(part_number);
        CREATE INDEX IF NOT EXISTS idx_discovery_invoice ON part_discovery_log(invoice_number);
        CREATE INDEX IF NOT EXISTS idx_discovery_date ON part_discovery_log(discovery_date);
        CREATE INDEX IF NOT EXISTS idx_discovery_session ON part_discovery_log(processing_session_id);

        -- Insert initial configuration data
        INSERT OR IGNORE INTO config (key, value, data_type, description, category) VALUES
        ('validation_mode', 'parts_based', 'string', 'Validation mode: parts_based or threshold_based', 'validation'),
        ('default_output_format', 'csv', 'string', 'Default report output format', 'reporting'),
        ('interactive_discovery', 'true', 'boolean', 'Enable interactive part discovery during processing', 'discovery'),
        ('auto_add_discovered_parts', 'false', 'boolean', 'Automatically add discovered parts without user confirmation', 'discovery'),
        ('price_tolerance', '0.001', 'number', 'Price comparison tolerance for floating point precision', 'validation'),
        ('backup_retention_days', '30', 'number', 'Number of days to retain database backups', 'maintenance'),
        ('log_retention_days', '365', 'number', 'Number of days to retain discovery log entries', 'maintenance'),
        ('database_version', '1.0', 'string', 'Current database schema version', 'system');

        -- Create triggers to update last_updated timestamps
        CREATE TRIGGER IF NOT EXISTS update_parts_timestamp
            AFTER UPDATE ON parts
            FOR EACH ROW
            BEGIN
                UPDATE parts SET last_updated = CURRENT_TIMESTAMP WHERE part_number = NEW.part_number;
            END;

        CREATE TRIGGER IF NOT EXISTS update_config_timestamp
            AFTER UPDATE ON config
            FOR EACH ROW
            BEGIN
                UPDATE config SET last_updated = CURRENT_TIMESTAMP WHERE key = NEW.key;
            END;

        -- Create view for active parts (commonly used query)
        CREATE VIEW IF NOT EXISTS active_parts AS
        SELECT part_number, authorized_price, description, category, source, first_seen_invoice, created_date, last_updated, notes
        FROM parts
        WHERE is_active = 1;

        -- Create view for recent discoveries (last 30 days)
        CREATE VIEW IF NOT EXISTS recent_discoveries AS
        SELECT pdl.*, p.description, p.authorized_price as current_authorized_price
        FROM part_discovery_log pdl
        LEFT JOIN parts p ON pdl.part_number = p.part_number
        WHERE pdl.discovery_date >= datetime('now', '-30 days')
        ORDER BY pdl.discovery_date DESC;
        """
    
    def get_current_version(self) -> str:
        """
        Get the current database version.
        
        Returns:
            str: Current database version, or "0.0" if not found
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("SELECT value FROM config WHERE key = 'database_version'")
                row = cursor.fetchone()
                return row[0] if row else "0.0"
        except sqlite3.Error:
            return "0.0"
    
    def get_available_versions(self) -> List[str]:
        """
        Get list of available migration versions.
        
        Returns:
            List[str]: List of available versions
        """
        return sorted(self.migrations.keys())
    
    def migrate_to_version(self, target_version: str) -> bool:
        """
        Migrate database to a specific version.
        
        Args:
            target_version: Target version to migrate to
            
        Returns:
            bool: True if migration successful, False otherwise
        """
        if target_version not in self.migrations:
            logger.error(f"Migration version {target_version} not found")
            return False
        
        current_version = self.get_current_version()
        
        if current_version == target_version:
            logger.info(f"Database is already at version {target_version}")
            return True
        
        logger.info(f"Migrating database from version {current_version} to {target_version}")
        
        try:
            # Create database directory if it doesn't exist
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                # Execute migration SQL
                migration_sql = self.migrations[target_version]
                
                # Use executescript to handle multi-line statements properly
                conn.executescript(migration_sql)
                
                # Update database version
                conn.execute("""
                    INSERT OR REPLACE INTO config (key, value, data_type, description, category)
                    VALUES ('database_version', ?, 'string', 'Current database schema version', 'system')
                """, (target_version,))
                
                conn.commit()
                
            logger.info(f"Successfully migrated database to version {target_version}")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def migrate_to_latest(self) -> bool:
        """
        Migrate database to the latest version.
        
        Returns:
            bool: True if migration successful, False otherwise
        """
        latest_version = max(self.migrations.keys())
        return self.migrate_to_version(latest_version)
    
    def verify_schema(self) -> Tuple[bool, List[str]]:
        """
        Verify that the database schema is correct.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Check if required tables exist
                required_tables = ['parts', 'config', 'part_discovery_log']
                
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = set(required_tables) - set(existing_tables)
                if missing_tables:
                    issues.append(f"Missing required tables: {missing_tables}")
                
                # Check if required indexes exist
                required_indexes = [
                    'idx_parts_number', 'idx_parts_active', 'idx_parts_category',
                    'idx_config_category', 'idx_discovery_part', 'idx_discovery_invoice',
                    'idx_discovery_date', 'idx_discovery_session'
                ]
                
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name NOT LIKE 'sqlite_%'
                """)
                existing_indexes = [row[0] for row in cursor.fetchall()]
                
                missing_indexes = set(required_indexes) - set(existing_indexes)
                if missing_indexes:
                    issues.append(f"Missing required indexes: {missing_indexes}")
                
                # Check if required views exist
                required_views = ['active_parts', 'recent_discoveries']
                
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='view'
                """)
                existing_views = [row[0] for row in cursor.fetchall()]
                
                missing_views = set(required_views) - set(existing_views)
                if missing_views:
                    issues.append(f"Missing required views: {missing_views}")
                
                # Check database version
                try:
                    cursor = conn.execute("SELECT value FROM config WHERE key = 'database_version'")
                    version_row = cursor.fetchone()
                    if not version_row:
                        issues.append("Database version not found in config")
                except sqlite3.Error:
                    issues.append("Could not retrieve database version")
                
        except Exception as e:
            issues.append(f"Schema verification failed: {e}")
        
        return len(issues) == 0, issues
    
    def create_sample_data(self) -> bool:
        """
        Create sample data for testing purposes.
        
        Returns:
            bool: True if sample data created successfully, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Insert sample parts
                sample_parts = [
                    ('GS0448', 0.3000, 'SHIRT WORK LS BTN COTTON', 'Clothing', 'manual', None, 1, 'Sample part for testing'),
                    ('GP0171NAVY', 0.2500, 'PANTS WORK NAVY', 'Clothing', 'manual', None, 1, 'Sample part for testing'),
                    ('TOOL001', 15.9900, 'HAMMER CLAW 16OZ', 'Tools', 'manual', None, 1, 'Sample part for testing'),
                ]
                
                for part in sample_parts:
                    conn.execute("""
                        INSERT OR IGNORE INTO parts (
                            part_number, authorized_price, description, category, source,
                            first_seen_invoice, is_active, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, part)
                
                conn.commit()
                logger.info("Sample data created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create sample data: {e}")
            return False


def main():
    """
    Main function for running migrations from command line.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration tool for Invoice Rate Detection System')
    parser.add_argument('--db-path', default='invoice_detection.db', help='Path to database file')
    parser.add_argument('--version', help='Target version to migrate to')
    parser.add_argument('--latest', action='store_true', help='Migrate to latest version')
    parser.add_argument('--verify', action='store_true', help='Verify database schema')
    parser.add_argument('--current-version', action='store_true', help='Show current database version')
    parser.add_argument('--sample-data', action='store_true', help='Create sample data for testing')
    parser.add_argument('--list-versions', action='store_true', help='List available migration versions')
    
    args = parser.parse_args()
    
    migration = DatabaseMigration(args.db_path)
    
    if args.current_version:
        version = migration.get_current_version()
        print(f"Current database version: {version}")
        return
    
    if args.list_versions:
        versions = migration.get_available_versions()
        print("Available migration versions:")
        for version in versions:
            print(f"  - {version}")
        return
    
    if args.verify:
        is_valid, issues = migration.verify_schema()
        if is_valid:
            print("Database schema is valid")
        else:
            print("Database schema issues found:")
            for issue in issues:
                print(f"  - {issue}")
        return
    
    if args.latest:
        success = migration.migrate_to_latest()
        sys.exit(0 if success else 1)
    
    if args.version:
        success = migration.migrate_to_version(args.version)
        sys.exit(0 if success else 1)
    
    if args.sample_data:
        success = migration.create_sample_data()
        sys.exit(0 if success else 1)
    
    # Default action: migrate to latest
    success = migration.migrate_to_latest()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()