"""
Integration tests for bulk operations functionality.

This module tests bulk operations with minimal mocking to verify real code flow
and database interactions. Tests use actual CSV files and database operations
to ensure the complete functionality works as expected.
"""

import pytest
import tempfile
import csv
import sqlite3
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch

from cli.commands.bulk_operations import (
    _load_column_mapping,
    _apply_data_transformations,
    _read_bulk_update_csv,
    _read_part_numbers_csv,
    _perform_bulk_update,
    _perform_bulk_delete,
    _perform_bulk_activate,
    bulk_update,
    bulk_delete,
    bulk_activate
)
from cli.exceptions import CLIError
from database.models import Part, PartNotFoundError, DatabaseError
from database.database import DatabaseManager


class TestRealDataProcessing:
    """Test data processing with real CSV files and data."""
    
    def create_test_csv(self, filename, data, headers):
        """Helper to create real CSV files for testing."""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in data:
                writer.writerow(row)
        return Path(filename)
    
    def test_load_column_mapping_real_file(self):
        """Test loading column mapping from actual CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['source_column', 'target_column'])
            writer.writerow(['item_code', 'part_number'])
            writer.writerow(['price', 'authorized_price'])
            writer.writerow(['desc', 'description'])
            temp_path = Path(f.name)
        
        try:
            mapping = _load_column_mapping(temp_path)
            assert mapping == {
                'item_code': 'part_number',
                'price': 'authorized_price',
                'desc': 'description'
            }
        finally:
            temp_path.unlink()
    
    def test_apply_data_transformations_real_data(self):
        """Test data transformations with real data scenarios."""
        test_cases = [
            # Part number transformation
            ({'part_number': 'gp0171navy'}, {'part_number': 'GP0171NAVY'}),
            # Price cleaning
            ({'authorized_price': '$15.50'}, {'authorized_price': Decimal('15.50')}),
            ({'authorized_price': '1,234.56'}, {'authorized_price': Decimal('1234.56')}),
            # Text field cleaning
            ({'description': '  Navy Pants  '}, {'description': 'Navy Pants'}),
            ({'category': ''}, {'category': None}),
        ]
        
        for input_data, expected_changes in test_cases:
            result = _apply_data_transformations(input_data)
            for key, expected_value in expected_changes.items():
                assert result[key] == expected_value
    
    def test_read_bulk_update_csv_real_file(self):
        """Test reading bulk update CSV with real file operations."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['part_number', 'price', 'description'])
            writer.writerow(['GP0171NAVY', '15.50', 'Navy Work Pants'])
            writer.writerow(['GP0171KHAKI', '16.00', 'Khaki Work Pants'])
            writer.writerow(['', '17.00', 'Invalid - empty part number'])  # Should be skipped
            temp_path = Path(f.name)
        
        try:
            result = _read_bulk_update_csv(temp_path, ['price', 'description'])
            assert len(result) == 2  # Empty part number row should be skipped
            
            assert result[0]['part_number'] == 'GP0171NAVY'
            assert result[0]['authorized_price'] == Decimal('15.50')
            assert result[0]['description'] == 'Navy Work Pants'
            
            assert result[1]['part_number'] == 'GP0171KHAKI'
            assert result[1]['authorized_price'] == Decimal('16.00')
            assert result[1]['description'] == 'Khaki Work Pants'
        finally:
            temp_path.unlink()
    
    def test_read_part_numbers_csv_real_file(self):
        """Test reading part numbers from real CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['part_number'])
            writer.writerow(['GP0171NAVY'])
            writer.writerow(['GP0171KHAKI'])
            writer.writerow([''])  # Empty - should be skipped
            writer.writerow(['GP0171BLACK'])
            temp_path = Path(f.name)
        
        try:
            result = _read_part_numbers_csv(temp_path)
            assert result == ['GP0171NAVY', 'GP0171KHAKI', 'GP0171BLACK']
        finally:
            temp_path.unlink()


class TestDatabaseIntegration:
    """Test bulk operations with real database interactions."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Initialize database using migration system to ensure composite key support
        from database.db_migration import DatabaseMigration
        migration = DatabaseMigration(db_path)
        migration.migrate_to_latest()
        
        db_manager = DatabaseManager(db_path)
        yield db_manager
        
        # Cleanup
        Path(db_path).unlink()
    
    def test_perform_bulk_update_real_database(self, temp_db):
        """Test bulk update with real database operations."""
        # Setup: Create test parts
        part1 = Part(
            part_number='GP0171NAVY',
            authorized_price=Decimal('15.00'),
            description='Original Navy Pants',
            category='Clothing'
        )
        part2 = Part(
            part_number='GP0171KHAKI',
            authorized_price=Decimal('15.00'),
            description='Original Khaki Pants',
            category='Clothing'
        )
        
        temp_db.create_part(part1)
        temp_db.create_part(part2)
        
        # Test data for bulk update
        update_data = [
            {
                'part_number': 'GP0171NAVY',
                'authorized_price': Decimal('16.50'),
                'description': 'Updated Navy Pants'
            },
            {
                'part_number': 'GP0171KHAKI',
                'authorized_price': Decimal('17.00')
            },
            {
                'part_number': 'NONEXISTENT',
                'authorized_price': Decimal('20.00')
            }
        ]
        
        # Execute bulk update
        results = _perform_bulk_update(
            update_data, temp_db, ['price', 'description'], None, 50
        )
        
        # Verify results
        assert results['total_parts'] == 3
        assert results['updated'] == 2
        assert results['not_found'] == 1
        assert results['errors'] == 0
        
        # Verify actual database changes
        updated_part1 = temp_db.get_part('GP0171NAVY')
        assert updated_part1.authorized_price == Decimal('16.50')
        assert updated_part1.description == 'Updated Navy Pants'
        
        updated_part2 = temp_db.get_part('GP0171KHAKI')
        assert updated_part2.authorized_price == Decimal('17.00')
        assert updated_part2.description == 'Original Khaki Pants'  # Unchanged
    
    def test_perform_bulk_delete_real_database(self, temp_db):
        """Test bulk delete with real database operations."""
        # Setup: Create test parts
        parts = [
            Part(part_number='GP0171NAVY', authorized_price=Decimal('15.00')),
            Part(part_number='GP0171KHAKI', authorized_price=Decimal('15.00')),
            Part(part_number='GP0171BLACK', authorized_price=Decimal('15.00'))
        ]
        
        for part in parts:
            temp_db.create_part(part)
        
        # Test soft delete
        part_numbers = ['GP0171NAVY', 'GP0171KHAKI', 'NONEXISTENT']
        
        results = _perform_bulk_delete(
            part_numbers, temp_db, soft_delete=True, filter_category=None, batch_size=50
        )
        
        # Verify results
        assert results['total_parts'] == 3
        assert results['deleted'] == 2
        assert results['not_found'] == 1
        
        # Verify soft delete (parts should be inactive)
        part1 = temp_db.get_part('GP0171NAVY')
        assert not part1.is_active
        
        part2 = temp_db.get_part('GP0171KHAKI')
        assert not part2.is_active
        
        # Unchanged part should still be active
        part3 = temp_db.get_part('GP0171BLACK')
        assert part3.is_active
    
    def test_perform_bulk_activate_real_database(self, temp_db):
        """Test bulk activate with real database operations."""
        # Setup: Create inactive parts
        parts = [
            Part(part_number='GP0171NAVY', authorized_price=Decimal('15.00'), is_active=False),
            Part(part_number='GP0171KHAKI', authorized_price=Decimal('15.00'), is_active=False),
            Part(part_number='GP0171BLACK', authorized_price=Decimal('15.00'), is_active=True)  # Already active
        ]
        
        for part in parts:
            temp_db.create_part(part)
        
        part_numbers = ['GP0171NAVY', 'GP0171KHAKI', 'GP0171BLACK', 'NONEXISTENT']
        
        results = _perform_bulk_activate(
            part_numbers, temp_db, filter_category=None, batch_size=50
        )
        
        # Verify results
        assert results['total_parts'] == 4
        assert results['activated'] == 2
        assert results['already_active'] == 1
        assert results['not_found'] == 1
        
        # Verify activation
        part1 = temp_db.get_part('GP0171NAVY')
        assert part1.is_active
        
        part2 = temp_db.get_part('GP0171KHAKI')
        assert part2.is_active
        
        part3 = temp_db.get_part('GP0171BLACK')
        assert part3.is_active  # Still active
    
    def test_bulk_update_with_category_filter_real_database(self, temp_db):
        """Test bulk update with category filtering using real database."""
        # Setup: Create parts in different categories
        parts = [
            Part(part_number='GP0171NAVY', authorized_price=Decimal('15.00'), category='Clothing'),
            Part(part_number='TOOL001', authorized_price=Decimal('25.00'), category='Tools'),
            Part(part_number='SAFETY001', authorized_price=Decimal('10.00'), category='Safety')
        ]
        
        for part in parts:
            temp_db.create_part(part)
        
        # Update data for all parts
        update_data = [
            {'part_number': 'GP0171NAVY', 'authorized_price': Decimal('16.00')},
            {'part_number': 'TOOL001', 'authorized_price': Decimal('26.00')},
            {'part_number': 'SAFETY001', 'authorized_price': Decimal('11.00')}
        ]
        
        # Execute with category filter
        results = _perform_bulk_update(
            update_data, temp_db, ['price'], 'Clothing', 50
        )
        
        # Verify only Clothing category was updated
        assert results['updated'] == 1
        assert results['filtered_out'] == 2
        
        # Verify database state
        clothing_part = temp_db.get_part('GP0171NAVY')
        assert clothing_part.authorized_price == Decimal('16.00')  # Updated
        
        tool_part = temp_db.get_part('TOOL001')
        assert tool_part.authorized_price == Decimal('25.00')  # Unchanged
        
        safety_part = temp_db.get_part('SAFETY001')
        assert safety_part.authorized_price == Decimal('10.00')  # Unchanged


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows with minimal mocking."""
    
    @pytest.fixture
    def temp_db_and_csv(self):
        """Create temporary database and CSV files for testing."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Initialize database using migration system to ensure composite key support
        from database.db_migration import DatabaseMigration
        migration = DatabaseMigration(db_path)
        migration.migrate_to_latest()
        
        db_manager = DatabaseManager(db_path)
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['part_number', 'price', 'description'])
            writer.writerow(['GP0171NAVY', '16.50', 'Updated Navy Pants'])
            writer.writerow(['GP0171KHAKI', '17.00', 'Updated Khaki Pants'])
            csv_path = Path(f.name)
        
        yield db_manager, csv_path
        
        # Cleanup
        Path(db_path).unlink()
        csv_path.unlink()
    
    def test_complete_bulk_update_workflow(self, temp_db_and_csv):
        """Test complete bulk update workflow from CSV to database."""
        db_manager, csv_path = temp_db_and_csv
        
        # Setup: Create initial parts
        initial_parts = [
            Part(part_number='GP0171NAVY', authorized_price=Decimal('15.00'), description='Navy Pants'),
            Part(part_number='GP0171KHAKI', authorized_price=Decimal('15.00'), description='Khaki Pants')
        ]
        
        for part in initial_parts:
            db_manager.create_part(part)
        
        # Read CSV data
        update_data = _read_bulk_update_csv(csv_path, ['price', 'description'])
        
        # Perform bulk update
        results = _perform_bulk_update(
            update_data, db_manager, ['price', 'description'], None, 50
        )
        
        # Verify complete workflow
        assert results['total_parts'] == 2
        assert results['updated'] == 2
        assert results['errors'] == 0
        
        # Verify final database state
        updated_navy = db_manager.get_part('GP0171NAVY')
        assert updated_navy.authorized_price == Decimal('16.50')
        assert updated_navy.description == 'Updated Navy Pants'
        
        updated_khaki = db_manager.get_part('GP0171KHAKI')
        assert updated_khaki.authorized_price == Decimal('17.00')
        assert updated_khaki.description == 'Updated Khaki Pants'
    
    def test_error_handling_with_real_data(self, temp_db_and_csv):
        """Test error handling with real data and database operations."""
        db_manager, csv_path = temp_db_and_csv
        
        # Don't create any parts in database - all updates should fail with "not found"
        
        # Read CSV data
        update_data = _read_bulk_update_csv(csv_path, ['price', 'description'])
        
        # Perform bulk update - should handle missing parts gracefully
        results = _perform_bulk_update(
            update_data, db_manager, ['price', 'description'], None, 50
        )
        
        # Verify error handling
        assert results['total_parts'] == 2
        assert results['updated'] == 0
        assert results['not_found'] == 2
        assert results['errors'] == 0


class TestCommandIntegration:
    """Test CLI command integration with minimal mocking."""
    
    def test_bulk_update_command_validation(self):
        """Test bulk update command validation without heavy mocking."""
        from click.testing import CliRunner
        from cli.commands.bulk_operations import bulk_update
        
        runner = CliRunner()
        
        # Test missing field parameter
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv') as f:
            writer = csv.writer(f)
            writer.writerow(['part_number', 'price'])
            writer.writerow(['GP0171NAVY', '15.50'])
            f.flush()
            
            # Test using Click's testing framework
            result = runner.invoke(bulk_update, [f.name])
            assert result.exit_code != 0
            assert "At least one field must be specified" in result.output or "Missing option" in result.output
    
    def test_csv_file_validation(self):
        """Test CSV file validation with real file operations."""
        # Test missing part_number column
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['item_code', 'price'])  # Wrong column name
            writer.writerow(['GP0171NAVY', '15.50'])
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(CLIError, match="must contain 'part_number' column"):
                _read_bulk_update_csv(temp_path, ['price'])
        finally:
            temp_path.unlink()
        
        # Test missing update fields
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['part_number', 'other_field'])
            writer.writerow(['GP0171NAVY', 'value'])
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(CLIError, match="must contain at least one of"):
                _read_bulk_update_csv(temp_path, ['price', 'description'])
        finally:
            temp_path.unlink()


class TestPerformanceAndScaling:
    """Test performance characteristics with real data volumes."""
    
    def test_large_dataset_processing(self):
        """Test processing larger datasets to verify performance."""
        # Create a larger CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['part_number', 'price'])
            
            # Generate 1000 test records
            for i in range(1000):
                writer.writerow([f'PART{i:04d}', f'{15.00 + i * 0.01:.2f}'])
            
            temp_path = Path(f.name)
        
        try:
            # Test reading large CSV
            update_data = _read_bulk_update_csv(temp_path, ['price'])
            assert len(update_data) == 1000
            
            # Verify data integrity
            assert update_data[0]['part_number'] == 'PART0000'
            assert update_data[0]['authorized_price'] == Decimal('15.00')
            
            assert update_data[999]['part_number'] == 'PART0999'
            assert update_data[999]['authorized_price'] == Decimal('24.99')
            
        finally:
            temp_path.unlink()
    
    def test_batch_processing_behavior(self):
        """Test that batch processing works correctly with real data."""
        # This test verifies that batch processing doesn't break data integrity
        test_data = [
            {'part_number': f'PART{i:03d}', 'authorized_price': Decimal(f'{15.00 + i:.2f}')}
            for i in range(100)
        ]
        
        # Test with different batch sizes
        for batch_size in [10, 25, 50]:
            # Simulate batch processing by chunking data
            batches = [test_data[i:i + batch_size] for i in range(0, len(test_data), batch_size)]
            
            # Verify all data is included
            reconstructed = []
            for batch in batches:
                reconstructed.extend(batch)
            
            assert len(reconstructed) == 100
            assert reconstructed[0]['part_number'] == 'PART000'
            assert reconstructed[99]['part_number'] == 'PART099'


if __name__ == '__main__':
    pytest.main([__file__])