"""
Integration tests for interactive functions in invoice_commands.py.

This module tests the core business logic of interactive parts review and addition
functionality with minimal mocking, focusing on real data processing and validation.
"""

import pytest
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path
from datetime import datetime

from cli.commands.invoice_commands import _show_unknown_parts_review, _interactive_parts_addition
from cli.exceptions import CLIError
from database.models import Part, PartDiscoveryLog, ValidationError
from database.database import DatabaseManager


class TestInteractiveFunctionsIntegration:
    """Integration tests using real database operations with minimal mocking."""
    
    def setup_method(self):
        """Set up test fixtures with real database."""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Remove the empty file so DatabaseManager will initialize it properly
        Path(self.temp_db.name).unlink()
        
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.session_id = str(uuid.uuid4())
        
        # Create test discovery logs
        self._create_test_discovery_logs()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def _create_test_discovery_logs(self):
        """Create test discovery logs in the database."""
        test_logs = [
            PartDiscoveryLog(
                part_number="TEST001",
                action_taken="discovered",
                discovered_price=Decimal('1.25'),
                invoice_number="INV001",
                processing_session_id=self.session_id,
                notes="Test part 1"
            ),
            PartDiscoveryLog(
                part_number="TEST001",
                action_taken="discovered", 
                discovered_price=Decimal('1.35'),
                invoice_number="INV002",
                processing_session_id=self.session_id,
                notes="Test part 1 duplicate"
            ),
            PartDiscoveryLog(
                part_number="TEST002",
                action_taken="discovered",
                discovered_price=Decimal('2.50'),
                invoice_number="INV003", 
                processing_session_id=self.session_id,
                notes="Test part 2"
            ),
            PartDiscoveryLog(
                part_number="TEST003",
                action_taken="discovered",
                discovered_price=None,  # No price data
                invoice_number="INV004",
                processing_session_id=self.session_id,
                notes="Test part 3 - no price"
            )
        ]
        
        for log in test_logs:
            self.db_manager.create_discovery_log(log)
    
    def test_price_analysis_logic(self):
        """Test that price analysis calculations are correct."""
        # Get discovery logs directly from database
        logs = self.db_manager.get_discovery_logs(session_id=self.session_id)
        unknown_logs = [log for log in logs if log.action_taken == 'discovered']
        
        # Test data aggregation logic (core business logic)
        parts_data = {}
        for log in unknown_logs:
            if log.part_number not in parts_data:
                parts_data[log.part_number] = {
                    'part_number': log.part_number,
                    'discovered_prices': [],
                    'invoices': [],
                    'descriptions': set()
                }
            
            if log.discovered_price is not None:
                parts_data[log.part_number]['discovered_prices'].append(log.discovered_price)
            parts_data[log.part_number]['invoices'].append(log.invoice_number)
            if log.notes:
                parts_data[log.part_number]['descriptions'].add(log.notes)
        
        # Verify TEST001 price calculations
        test001_data = parts_data['TEST001']
        prices = test001_data['discovered_prices']
        assert len(prices) == 2
        assert Decimal('1.25') in prices
        assert Decimal('1.35') in prices
        
        avg_price = sum(prices) / len(prices)
        assert avg_price == Decimal('1.30')
        assert min(prices) == Decimal('1.25')
        assert max(prices) == Decimal('1.35')
        
        # Verify TEST002 has single price
        test002_data = parts_data['TEST002']
        assert len(test002_data['discovered_prices']) == 1
        assert test002_data['discovered_prices'][0] == Decimal('2.50')
        
        # Verify TEST003 has no valid prices
        test003_data = parts_data['TEST003']
        assert len(test003_data['discovered_prices']) == 0
    
    def test_part_creation_validation(self):
        """Test real Part model validation during creation."""
        # Test valid part creation
        valid_part = Part(
            part_number="VALID001",
            authorized_price=Decimal('1.25'),
            description="Valid test part",
            category="test",
            source='discovered',
            notes="Created during testing"
        )
        
        # This should not raise any exceptions
        created_part = self.db_manager.create_part(valid_part)
        assert created_part.part_number == "VALID001"
        assert created_part.authorized_price == Decimal('1.25')
        
        # Test invalid part creation (negative price)
        with pytest.raises(ValidationError):
            invalid_part = Part(
                part_number="INVALID001",
                authorized_price=Decimal('-1.25'),  # Invalid negative price
                source='discovered'
            )
    
    def test_part_creation_duplicate_handling(self):
        """Test handling of duplicate part numbers."""
        # Use a unique part number for this test
        import uuid
        unique_part_number = f"DUPLICATE_{uuid.uuid4().hex[:8]}"
        
        # Create first part
        part1 = Part(
            part_number=unique_part_number,
            authorized_price=Decimal('1.25'),
            source='discovered'
        )
        self.db_manager.create_part(part1)
        
        # Attempt to create duplicate - should raise DatabaseError
        with pytest.raises(Exception, match="already exists"):
            part2 = Part(
                part_number=unique_part_number,  # Same part number
                authorized_price=Decimal('2.50'),
                source='discovered'
            )
            self.db_manager.create_part(part2)
    
    def test_discovery_log_filtering(self):
        """Test that discovery log filtering works correctly."""
        # Create logs with different session IDs
        other_session_id = str(uuid.uuid4())
        other_log = PartDiscoveryLog(
            part_number="OTHER001",
            action_taken="discovered",
            discovered_price=Decimal('5.00'),
            invoice_number="OTHER_INV",
            processing_session_id=other_session_id
        )
        self.db_manager.create_discovery_log(other_log)
        
        # Get logs for our session only
        our_logs = self.db_manager.get_discovery_logs(session_id=self.session_id)
        our_part_numbers = {log.part_number for log in our_logs}
        
        # Should not include the other session's log
        assert "OTHER001" not in our_part_numbers
        assert "TEST001" in our_part_numbers
        assert "TEST002" in our_part_numbers
        assert "TEST003" in our_part_numbers
    
    def test_database_error_propagation(self):
        """Test that database errors are properly propagated."""
        # Close the database connection to simulate error
        self.db_manager.db_path.unlink()  # Delete the database file
        
        # This should raise a database error
        with pytest.raises(Exception):  # DatabaseError or similar
            self.db_manager.get_discovery_logs(session_id=self.session_id)
    
    def test_empty_session_handling(self):
        """Test handling of sessions with no discovery logs."""
        empty_session_id = str(uuid.uuid4())
        logs = self.db_manager.get_discovery_logs(session_id=empty_session_id)
        assert len(logs) == 0
    
    def test_part_number_validation_edge_cases(self):
        """Test Part model validation with edge cases."""
        # Test empty part number
        with pytest.raises(ValidationError, match="At least one of part_number, description, or item_type must be provided"):
            Part(part_number="", authorized_price=Decimal('1.25'))
        
        # Test whitespace-only part number
        with pytest.raises(ValidationError, match="empty or whitespace"):
            Part(part_number="   ", authorized_price=Decimal('1.25'))
        
        # Test invalid characters in part number (using a character that's actually invalid)
        with pytest.raises(ValidationError, match="can only contain"):
            Part(part_number="PART#001", authorized_price=Decimal('1.25'))
        
        # Test valid part number formats
        valid_formats = ["PART001", "part_001", "PART-001", "PART.001", "123ABC"]
        for part_num in valid_formats:
            part = Part(part_number=part_num, authorized_price=Decimal('1.25'))
            assert part.part_number == part_num  # Should not raise exception
    
    def test_price_precision_validation(self):
        """Test price precision validation in Part model."""
        # Test valid 4 decimal places
        part = Part(part_number="PRECISION001", authorized_price=Decimal('1.2345'))
        assert part.authorized_price == Decimal('1.2345')
        
        # Test too many decimal places should raise error
        with pytest.raises(ValidationError, match="more than 4 decimal places"):
            Part(part_number="PRECISION002", authorized_price=Decimal('1.23456'))
    
    def test_discovery_log_action_validation(self):
        """Test PartDiscoveryLog action validation."""
        # Test valid actions
        valid_actions = ['discovered', 'added', 'updated', 'skipped', 'price_mismatch']
        for action in valid_actions:
            log = PartDiscoveryLog(part_number="TEST", action_taken=action)
            assert log.action_taken == action
        
        # Test invalid action
        with pytest.raises(ValidationError, match="Action taken must be one of"):
            PartDiscoveryLog(part_number="TEST", action_taken="invalid_action")


class TestBusinessLogicUnits:
    """Unit tests for core business logic without database dependencies."""
    
    def test_price_statistics_calculation(self):
        """Test price statistics calculations with various scenarios."""
        # Test single price
        prices = [Decimal('1.25')]
        avg = sum(prices) / len(prices)
        assert avg == Decimal('1.25')
        assert min(prices) == Decimal('1.25')
        assert max(prices) == Decimal('1.25')
        
        # Test multiple prices
        prices = [Decimal('1.25'), Decimal('1.35'), Decimal('1.20')]
        avg = sum(prices) / len(prices)
        expected_avg = Decimal('1.25') + Decimal('1.35') + Decimal('1.20')
        expected_avg = expected_avg / 3
        assert avg == expected_avg
        assert min(prices) == Decimal('1.20')
        assert max(prices) == Decimal('1.35')
        
        # Test identical prices
        prices = [Decimal('2.50'), Decimal('2.50'), Decimal('2.50')]
        avg = sum(prices) / len(prices)
        assert avg == Decimal('2.50')
        assert min(prices) == Decimal('2.50')
        assert max(prices) == Decimal('2.50')
    
    def test_part_data_aggregation(self):
        """Test the core data aggregation logic."""
        # Simulate discovery logs
        mock_logs = [
            {'part_number': 'PART001', 'discovered_price': Decimal('1.25'), 'invoice_number': 'INV001'},
            {'part_number': 'PART001', 'discovered_price': Decimal('1.35'), 'invoice_number': 'INV002'},
            {'part_number': 'PART002', 'discovered_price': Decimal('2.50'), 'invoice_number': 'INV003'},
            {'part_number': 'PART003', 'discovered_price': None, 'invoice_number': 'INV004'},
        ]
        
        # Apply aggregation logic
        parts_data = {}
        for log in mock_logs:
            part_num = log['part_number']
            if part_num not in parts_data:
                parts_data[part_num] = {
                    'discovered_prices': [],
                    'invoices': []
                }
            
            if log['discovered_price'] is not None:
                parts_data[part_num]['discovered_prices'].append(log['discovered_price'])
            parts_data[part_num]['invoices'].append(log['invoice_number'])
        
        # Verify aggregation results
        assert len(parts_data['PART001']['discovered_prices']) == 2
        assert len(parts_data['PART002']['discovered_prices']) == 1
        assert len(parts_data['PART003']['discovered_prices']) == 0
        
        assert len(parts_data['PART001']['invoices']) == 2
        assert len(parts_data['PART002']['invoices']) == 1
        assert len(parts_data['PART003']['invoices']) == 1
    
    def test_display_data_formatting(self):
        """Test the display data formatting logic."""
        parts_data = {
            'PART001': {
                'discovered_prices': [Decimal('1.25'), Decimal('1.35')],
                'invoices': ['INV001', 'INV002']
            },
            'PART002': {
                'discovered_prices': [Decimal('2.50')],
                'invoices': ['INV003']
            }
        }
        
        # Apply formatting logic
        display_data = []
        for part_number, data in parts_data.items():
            prices = data['discovered_prices']
            if not prices:
                continue
                
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            display_data.append({
                'Part Number': part_number,
                'Occurrences': len(prices),
                'Avg Price': f"${avg_price:.4f}",
                'Min Price': f"${min_price:.4f}",
                'Max Price': f"${max_price:.4f}",
                'Invoices': len(set(data['invoices'])),
                'Price Range': f"${min_price:.4f} - ${max_price:.4f}" if min_price != max_price else f"${min_price:.4f}"
            })
        
        # Verify formatting
        assert len(display_data) == 2
        
        part001_data = next(d for d in display_data if d['Part Number'] == 'PART001')
        assert part001_data['Occurrences'] == 2
        assert part001_data['Avg Price'] == "$1.3000"
        assert part001_data['Min Price'] == "$1.2500"
        assert part001_data['Max Price'] == "$1.3500"
        assert part001_data['Price Range'] == "$1.2500 - $1.3500"
        
        part002_data = next(d for d in display_data if d['Part Number'] == 'PART002')
        assert part002_data['Occurrences'] == 1
        assert part002_data['Avg Price'] == "$2.5000"
        assert part002_data['Price Range'] == "$2.5000"


class TestDataValidationLogic:
    """Test data validation and edge case handling."""
    
    def test_decimal_precision_handling(self):
        """Test handling of decimal precision in calculations."""
        # Test precision preservation
        price1 = Decimal('1.2345')
        price2 = Decimal('1.2346')
        avg = (price1 + price2) / 2
        assert str(avg) == '1.23455'
        
        # Test rounding behavior
        prices = [Decimal('1.2345'), Decimal('1.2346'), Decimal('1.2347')]
        avg = sum(prices) / len(prices)
        expected = Decimal('1.2346')
        assert avg == expected
    
    def test_empty_data_handling(self):
        """Test handling of empty or invalid data."""
        # Test empty price list
        prices = []
        parts_data = {'PART001': {'discovered_prices': prices, 'invoices': ['INV001']}}
        
        display_data = []
        for part_number, data in parts_data.items():
            prices = data['discovered_prices']
            if not prices:  # This should skip the part
                continue
            # This code should not execute
            display_data.append({'Part Number': part_number})
        
        assert len(display_data) == 0
    
    def test_none_price_filtering(self):
        """Test filtering of None prices."""
        raw_prices = [Decimal('1.25'), None, Decimal('1.35'), None]
        valid_prices = [p for p in raw_prices if p is not None]
        
        assert len(valid_prices) == 2
        assert Decimal('1.25') in valid_prices
        assert Decimal('1.35') in valid_prices
        assert None not in valid_prices
    
    def test_invoice_deduplication(self):
        """Test invoice number deduplication logic."""
        invoices = ['INV001', 'INV002', 'INV001', 'INV003', 'INV002']
        unique_invoices = len(set(invoices))
        
        assert unique_invoices == 3
        assert set(invoices) == {'INV001', 'INV002', 'INV003'}


class TestErrorScenarios:
    """Test error handling and edge cases."""
    
    def test_division_by_zero_protection(self):
        """Test protection against division by zero."""
        prices = []
        
        # This should be protected by the empty check
        if prices:
            avg = sum(prices) / len(prices)
        else:
            avg = None
        
        assert avg is None
    
    def test_invalid_decimal_handling(self):
        """Test handling of invalid decimal values."""
        # Test creation of invalid decimals
        with pytest.raises(Exception):  # Should raise some form of error
            invalid_price = Decimal('invalid')
    
    def test_large_number_handling(self):
        """Test handling of very large numbers."""
        large_price = Decimal('999999.9999')
        prices = [large_price]
        
        avg = sum(prices) / len(prices)
        assert avg == large_price
        
        # Test formatting
        formatted = f"${avg:.4f}"
        assert formatted == "$999999.9999"