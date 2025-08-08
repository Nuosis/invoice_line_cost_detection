"""
Comprehensive tests for the Interactive Part Discovery functionality.

This module tests all aspects of the part discovery system including:
- Unknown part detection
- Interactive discovery workflows
- Batch discovery processing
- Discovery logging and audit trails
- Integration with validation engine
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from processing.part_discovery_service import (
    InteractivePartDiscoveryService, PartDiscoveryResult,
    DiscoverySession
)
from processing.part_discovery_models import UnknownPartContext
from processing.models import InvoiceData, LineItem
from processing.validation_engine import ValidationEngine
from database.models import Part, PartDiscoveryLog, DatabaseError, ValidationError
from database.database import DatabaseManager
from processing.validation_models import ValidationConfiguration
from cli.exceptions import UserCancelledError


class TestUnknownPartContext:
    """Test the UnknownPartContext data class."""
    
    def test_unknown_part_context_creation(self):
        """Test creating an UnknownPartContext."""
        context = UnknownPartContext(
            part_number="TEST123",
            invoice_number="INV001",
            invoice_date="2024-01-15",
            discovered_price=Decimal("15.50"),
            description="Test Part",
            quantity=2
        )
        
        assert context.part_number == "TEST123"
        assert context.invoice_number == "INV001"
        assert context.discovered_price == Decimal("15.50")
        assert context.quantity == 2
    
    def test_unknown_part_context_to_dict(self):
        """Test converting UnknownPartContext to dictionary."""
        context = UnknownPartContext(
            part_number="TEST123",
            discovered_price=Decimal("15.50")
        )
        
        result = context.to_dict()
        
        assert result['part_number'] == "TEST123"
        assert result['discovered_price'] == 15.50
        assert 'invoice_number' in result


class TestPartDiscoveryResult:
    """Test the PartDiscoveryResult data class."""
    
    def test_discovery_result_successful(self):
        """Test successful discovery result."""
        part = Part(part_number="TEST123", authorized_price=Decimal("15.50"))
        result = PartDiscoveryResult(
            part_number="TEST123",
            action_taken="added",
            part_added=part
        )
        
        assert result.was_successful
        assert result.part_number == "TEST123"
        assert result.action_taken == "added"
        assert result.part_added == part
    
    def test_discovery_result_failed(self):
        """Test failed discovery result."""
        result = PartDiscoveryResult(
            part_number="TEST123",
            action_taken="failed",
            error_message="Database error"
        )
        
        assert not result.was_successful
        assert result.error_message == "Database error"


class TestDiscoverySession:
    """Test the DiscoverySession data class."""
    
    def test_discovery_session_creation(self):
        """Test creating a discovery session."""
        session_id = str(uuid.uuid4())
        session = DiscoverySession(session_id=session_id)
        
        assert session.session_id == session_id
        assert session.processing_mode == 'interactive'
        assert len(session.unknown_parts) == 0
    
    def test_add_unknown_part(self):
        """Test adding unknown parts to session."""
        session = DiscoverySession(session_id="test-session")
        
        context1 = UnknownPartContext(part_number="PART1")
        context2 = UnknownPartContext(part_number="PART1")  # Same part
        context3 = UnknownPartContext(part_number="PART2")  # Different part
        
        session.add_unknown_part(context1)
        session.add_unknown_part(context2)
        session.add_unknown_part(context3)
        
        assert len(session.unknown_parts) == 2  # Two unique parts
        assert len(session.unknown_parts["PART1"]) == 2  # Two contexts for PART1
        assert len(session.unknown_parts["PART2"]) == 1  # One context for PART2
    
    def test_get_unique_part_numbers(self):
        """Test getting unique part numbers from session."""
        session = DiscoverySession(session_id="test-session")
        
        session.add_unknown_part(UnknownPartContext(part_number="PART1"))
        session.add_unknown_part(UnknownPartContext(part_number="PART2"))
        session.add_unknown_part(UnknownPartContext(part_number="PART1"))
        
        unique_parts = session.get_unique_part_numbers()
        
        assert len(unique_parts) == 2
        assert "PART1" in unique_parts
        assert "PART2" in unique_parts
    
    def test_get_session_summary(self):
        """Test getting session summary."""
        session = DiscoverySession(session_id="test-session")
        
        session.add_unknown_part(UnknownPartContext(part_number="PART1"))
        session.add_unknown_part(UnknownPartContext(part_number="PART2"))
        session.parts_added.append(Part(part_number="PART1", authorized_price=Decimal("10.00")))
        
        summary = session.get_session_summary()
        
        assert summary['session_id'] == "test-session"
        assert summary['unique_parts_discovered'] == 2
        assert summary['total_occurrences'] == 2
        assert summary['parts_added'] == 1


class TestInteractivePartDiscoveryService:
    """Test the InteractivePartDiscoveryService class."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock(spec=DatabaseManager)
        return db_manager
    
    @pytest.fixture
    def discovery_service(self, mock_db_manager):
        """Create a discovery service with mocked dependencies."""
        return InteractivePartDiscoveryService(mock_db_manager)
    
    @pytest.fixture
    def sample_invoice_data(self):
        """Create sample invoice data for testing."""
        line_items = [
            LineItem(
                item_code="KNOWN_PART",
                description="Known Part",
                rate=Decimal("10.00")
            ),
            LineItem(
                item_code="UNKNOWN_PART1",
                description="Unknown Part 1",
                rate=Decimal("15.50")
            ),
            LineItem(
                item_code="UNKNOWN_PART2",
                description="Unknown Part 2",
                rate=Decimal("20.00")
            )
        ]
        
        return InvoiceData(
            invoice_number="INV001",
            invoice_date="2024-01-15",
            line_items=line_items
        )
    
    def test_start_discovery_session(self, discovery_service):
        """Test starting a discovery session."""
        session_id = discovery_service.start_discovery_session()
        
        assert session_id in discovery_service.active_sessions
        session = discovery_service.active_sessions[session_id]
        assert session.processing_mode == 'interactive'
    
    def test_start_discovery_session_custom_mode(self, discovery_service):
        """Test starting a discovery session with custom mode."""
        session_id = discovery_service.start_discovery_session(
            processing_mode='batch_collect'
        )
        
        session = discovery_service.active_sessions[session_id]
        assert session.processing_mode == 'batch_collect'
    
    def test_discover_unknown_parts_from_invoice(self, discovery_service, mock_db_manager, sample_invoice_data):
        """Test discovering unknown parts from an invoice."""
        # Mock database responses
        def mock_get_part(part_number):
            if part_number == "KNOWN_PART":
                return Part(part_number=part_number, authorized_price=Decimal("10.00"))
            else:
                raise Exception("Part not found")
        
        mock_db_manager.get_part.side_effect = mock_get_part
        mock_db_manager.create_discovery_log.return_value = None
        
        # Start session and discover parts
        session_id = discovery_service.start_discovery_session()
        unknown_contexts = discovery_service.discover_unknown_parts_from_invoice(
            sample_invoice_data, session_id
        )
        
        # Verify results
        assert len(unknown_contexts) == 2
        part_numbers = [ctx.part_number for ctx in unknown_contexts]
        assert "UNKNOWN_PART1" in part_numbers
        assert "UNKNOWN_PART2" in part_numbers
        
        # Verify session was updated
        session = discovery_service.active_sessions[session_id]
        assert len(session.unknown_parts) == 2
    
    def test_check_part_exists(self, discovery_service, mock_db_manager):
        """Test checking if a part exists."""
        # Mock existing part
        mock_db_manager.get_part.return_value = Part(
            part_number="EXISTS", authorized_price=Decimal("10.00")
        )
        
        assert discovery_service.check_part_exists("EXISTS") is True
        
        # Mock non-existing part
        mock_db_manager.get_part.side_effect = Exception("Not found")
        
        assert discovery_service.check_part_exists("NOT_EXISTS") is False
    
    def test_process_unknown_parts_batch(self, discovery_service, mock_db_manager):
        """Test batch processing of unknown parts."""
        mock_db_manager.create_discovery_log.return_value = None
        
        # Start session and add unknown parts
        session_id = discovery_service.start_discovery_session(processing_mode='batch_collect')
        session = discovery_service.active_sessions[session_id]
        
        session.add_unknown_part(UnknownPartContext(part_number="PART1"))
        session.add_unknown_part(UnknownPartContext(part_number="PART2"))
        
        # Process in batch mode
        results = discovery_service.process_unknown_parts_batch(session_id)
        
        assert len(results) == 2
        for result in results:
            assert result.action_taken == 'skipped'
            assert result.user_decision == 'batch_collected'
    
    def test_process_unknown_parts_interactive_add_logic(self, discovery_service, mock_db_manager):
        """Test interactive processing logic with user choosing to add part."""
        # Mock the prompt handler directly on the service instance
        mock_prompt = Mock()
        discovery_service.prompt_handler = mock_prompt
        
        # Mock user decision to add part (simulates user input without actual prompting)
        mock_prompt.prompt_for_unknown_part.return_value = {
            'action': 'add_to_database_now',
            'part_details': {
                'authorized_price': Decimal('15.50'),
                'description': 'Test Part',
                'category': 'Test',
                'notes': 'Added via discovery'
            }
        }
        
        # Mock database operations
        created_part = Part(
            part_number="PART1",
            authorized_price=Decimal('15.50'),
            description='Test Part'
        )
        mock_db_manager.create_part.return_value = created_part
        mock_db_manager.create_discovery_log.return_value = None
        
        # Start session and add unknown part
        session_id = discovery_service.start_discovery_session()
        session = discovery_service.active_sessions[session_id]
        session.add_unknown_part(UnknownPartContext(part_number="PART1"))
        
        # Process interactively - this tests the business logic flow
        results = discovery_service.process_unknown_parts_interactive(session_id)
        
        # Verify the interactive workflow logic
        assert len(results) == 1
        result = results[0]
        assert result.action_taken == 'added'
        assert result.part_added == created_part
        assert result.was_successful
        
        # Verify the prompt was called with correct parameters
        mock_prompt.prompt_for_unknown_part.assert_called_once()
        
        # Verify database operations were called
        mock_db_manager.create_part.assert_called_once()
        mock_db_manager.create_discovery_log.assert_called_once()
    
    def test_process_unknown_parts_interactive_skip_logic(self, discovery_service, mock_db_manager):
        """Test interactive processing logic with user choosing to skip part."""
        # Mock the prompt handler directly on the service instance
        mock_prompt = Mock()
        discovery_service.prompt_handler = mock_prompt
        
        # Mock user decision to skip part (simulates user choosing to skip)
        mock_prompt.prompt_for_unknown_part.return_value = {
            'action': 'skip_this_part'
        }
        
        mock_db_manager.create_discovery_log.return_value = None
        
        # Start session and add unknown part
        session_id = discovery_service.start_discovery_session()
        session = discovery_service.active_sessions[session_id]
        session.add_unknown_part(UnknownPartContext(part_number="PART1"))
        
        # Process interactively - this tests the skip workflow logic
        results = discovery_service.process_unknown_parts_interactive(session_id)
        
        # Verify the skip workflow logic
        assert len(results) == 1
        result = results[0]
        assert result.action_taken == 'skipped'
        assert result.user_decision == 'skip_this_part'
        # Note: According to the PartDiscoveryResult.was_successful property,
        # 'skipped' is considered successful (no error occurred)
        assert result.was_successful
        
        # Verify the prompt was called
        mock_prompt.prompt_for_unknown_part.assert_called_once()
        
        # Verify no part was created (since it was skipped)
        mock_db_manager.create_part.assert_not_called()
        
        # Verify discovery log was still created to track the skip
        mock_db_manager.create_discovery_log.assert_called_once()
    
    def test_process_unknown_parts_interactive_user_cancelled_logic(self, discovery_service, mock_db_manager):
        """Test interactive processing logic when user cancels."""
        # Mock the prompt handler directly on the service instance
        mock_prompt = Mock()
        discovery_service.prompt_handler = mock_prompt
        mock_prompt.prompt_for_unknown_part.side_effect = UserCancelledError("User cancelled operation")
        
        mock_db_manager.create_discovery_log.return_value = None
        
        # Start session and add unknown part
        session_id = discovery_service.start_discovery_session()
        session = discovery_service.active_sessions[session_id]
        session.add_unknown_part(UnknownPartContext(part_number="PART1"))
        
        # Process interactively - this tests the cancellation workflow logic
        results = discovery_service.process_unknown_parts_interactive(session_id)
        
        # Verify the cancellation workflow logic
        assert len(results) == 1
        result = results[0]
        assert result.action_taken == 'stop_processing'
        assert result.user_decision == 'cancelled'
        # Note: According to the PartDiscoveryResult.was_successful property,
        # 'stop_processing' is not in the successful actions list
        assert not result.was_successful
        
        # Verify the prompt was called before cancellation
        mock_prompt.prompt_for_unknown_part.assert_called_once()
        
        # Verify no part was created due to cancellation
        mock_db_manager.create_part.assert_not_called()
        
        # Note: The cancellation logic in the service creates a special result
        # but doesn't log individual part discoveries for cancellation
        # The logging happens in the main processing loop, not in the exception handler
    
    def test_get_session_summary(self, discovery_service):
        """Test getting session summary."""
        session_id = discovery_service.start_discovery_session()
        session = discovery_service.active_sessions[session_id]
        
        session.add_unknown_part(UnknownPartContext(part_number="PART1"))
        session.parts_added.append(Part(part_number="PART1", authorized_price=Decimal("10.00")))
        
        summary = discovery_service.get_session_summary(session_id)
        
        assert summary['session_id'] == session_id
        assert summary['unique_parts_discovered'] == 1
        assert summary['parts_added'] == 1
    
    def test_get_session_summary_from_logs(self, discovery_service, mock_db_manager):
        """Test getting session summary from database logs."""
        # Mock discovery logs
        mock_logs = [
            Mock(part_number="PART1", action_taken="discovered"),
            Mock(part_number="PART2", action_taken="discovered"),
            Mock(part_number="PART1", action_taken="added")
        ]
        mock_db_manager.get_discovery_logs.return_value = mock_logs
        
        # Get summary for non-active session
        summary = discovery_service.get_session_summary("non-active-session")
        
        assert summary['unique_parts_discovered'] == 2
        assert summary['total_occurrences'] == 3
        assert summary['parts_added'] == 1
        assert summary['from_database_logs'] is True
    
    def test_end_discovery_session(self, discovery_service):
        """Test ending a discovery session."""
        session_id = discovery_service.start_discovery_session()
        
        # Verify session exists
        assert session_id in discovery_service.active_sessions
        
        # End session
        summary = discovery_service.end_discovery_session(session_id)
        
        # Verify session was removed
        assert session_id not in discovery_service.active_sessions
        assert 'session_id' in summary
    
    def test_get_unknown_parts_for_review(self, discovery_service, mock_db_manager):
        """Test getting unknown parts formatted for review."""
        # Mock discovery logs with price data
        mock_logs = [
            Mock(
                part_number="PART1",
                action_taken="discovered",
                discovered_price=Decimal("10.00"),
                invoice_number="INV001",
                notes="Test Part 1"
            ),
            Mock(
                part_number="PART1",
                action_taken="discovered",
                discovered_price=Decimal("12.00"),
                invoice_number="INV002",
                notes="Test Part 1"
            ),
            Mock(
                part_number="PART2",
                action_taken="discovered",
                discovered_price=Decimal("15.00"),
                invoice_number="INV001",
                notes="Test Part 2"
            )
        ]
        mock_db_manager.get_discovery_logs.return_value = mock_logs
        
        review_data = discovery_service.get_unknown_parts_for_review("test-session")
        
        assert len(review_data) == 2
        
        # Check PART1 data
        part1_data = next(item for item in review_data if item['part_number'] == 'PART1')
        assert part1_data['occurrences'] == 2
        assert part1_data['avg_price'] == 11.00  # (10.00 + 12.00) / 2
        assert part1_data['min_price'] == Decimal("10.00")
        assert part1_data['max_price'] == Decimal("12.00")
        assert part1_data['price_variance'] == Decimal("2.00")
        
        # Check PART2 data
        part2_data = next(item for item in review_data if item['part_number'] == 'PART2')
        assert part2_data['occurrences'] == 1
        assert part2_data['avg_price'] == 15.00


class TestValidationEngineIntegration:
    """Test integration of discovery service with validation engine."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        return Mock(spec=DatabaseManager)
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock validation configuration."""
        config = Mock(spec=ValidationConfiguration)
        config.interactive_discovery = True
        config.batch_collect_unknown_parts = False
        return config
    
    @pytest.fixture
    def validation_engine(self, mock_db_manager, mock_config):
        """Create a validation engine with mocked dependencies."""
        with patch('processing.validation_engine.PDFProcessor'), \
             patch('processing.validation_engine.AuditTrailManager'), \
             patch('processing.validation_engine.ValidationErrorHandler'):
            
            engine = ValidationEngine(mock_db_manager, mock_config)
            return engine
    
    def test_validation_engine_has_discovery_service(self, validation_engine):
        """Test that validation engine has discovery service."""
        assert hasattr(validation_engine, 'discovery_service')
        assert isinstance(validation_engine.discovery_service, InteractivePartDiscoveryService)
    
    def test_get_discovery_service(self, validation_engine):
        """Test getting discovery service from validation engine."""
        discovery_service = validation_engine.get_discovery_service()
        assert discovery_service is validation_engine.discovery_service
    
    @patch('processing.validation_engine.ValidationEngine._extract_invoice_data')
    def test_validate_invoice_with_discovery_interactive(self, mock_extract, validation_engine, mock_db_manager):
        """Test validation with interactive discovery."""
        # Mock invoice data
        mock_invoice_data = Mock()
        mock_extract.return_value = mock_invoice_data
        
        # Mock discovery service methods
        validation_engine.discovery_service.start_discovery_session = Mock(return_value="test-session")
        validation_engine.discovery_service.discover_unknown_parts_from_invoice = Mock(return_value=[
            UnknownPartContext(part_number="UNKNOWN1")
        ])
        validation_engine.discovery_service.process_unknown_parts_interactive = Mock(return_value=[
            PartDiscoveryResult(part_number="UNKNOWN1", action_taken="added")
        ])
        validation_engine.discovery_service.end_discovery_session = Mock(return_value={})
        
        # Mock validation result
        with patch.object(validation_engine, 'validate_invoice') as mock_validate:
            mock_result = Mock()
            mock_result.processing_successful = True
            mock_validate.return_value = mock_result
            
            # Test validation with discovery
            validation_result, discovery_results = validation_engine.validate_invoice_with_discovery(
                Path("test.pdf"), interactive_discovery=True
            )
            
            assert validation_result == mock_result
            assert len(discovery_results) == 1
            assert discovery_results[0].part_number == "UNKNOWN1"
    
    @patch('processing.validation_engine.ValidationEngine._extract_invoice_data')
    def test_validate_batch_with_discovery(self, mock_extract, validation_engine):
        """Test batch validation with discovery."""
        # Mock invoice data
        mock_invoice_data = Mock()
        mock_extract.return_value = mock_invoice_data
        
        # Mock discovery service methods
        validation_engine.discovery_service.start_discovery_session = Mock(return_value="test-session")
        validation_engine.discovery_service.discover_unknown_parts_from_invoice = Mock(return_value=[
            UnknownPartContext(part_number="UNKNOWN1")
        ])
        validation_engine.discovery_service.process_unknown_parts_batch = Mock(return_value=[
            PartDiscoveryResult(part_number="UNKNOWN1", action_taken="skipped")
        ])
        validation_engine.discovery_service.end_discovery_session = Mock(return_value={})
        
        # Mock validation results
        with patch.object(validation_engine, 'validate_invoice') as mock_validate:
            mock_result = Mock()
            mock_result.processing_successful = True
            mock_validate.return_value = mock_result
            
            # Test batch validation with discovery
            validation_results, discovery_results = validation_engine.validate_batch_with_discovery(
                [Path("test1.pdf"), Path("test2.pdf")], interactive_discovery=False
            )
            
            assert len(validation_results) == 2
            assert len(discovery_results) == 1
            assert discovery_results[0].action_taken == "skipped"


class TestDiscoveryLogging:
    """Test discovery logging and audit trail functionality."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        return Mock(spec=DatabaseManager)
    
    @pytest.fixture
    def discovery_service(self, mock_db_manager):
        """Create a discovery service with mocked dependencies."""
        return InteractivePartDiscoveryService(mock_db_manager)
    
    def test_discovery_logging_on_part_discovery(self, discovery_service, mock_db_manager):
        """Test that discovery events are logged to database."""
        mock_db_manager.get_part.side_effect = Exception("Part not found")
        mock_db_manager.create_discovery_log.return_value = None
        
        # Create sample invoice data
        invoice_data = InvoiceData(
            invoice_number="INV001",
            invoice_date="2024-01-15",
            line_items=[
                LineItem(
                    item_code="UNKNOWN_PART",
                    description="Unknown Part",
                    rate=Decimal("15.50")
                )
            ]
        )
        
        # Start session and discover parts
        session_id = discovery_service.start_discovery_session()
        discovery_service.discover_unknown_parts_from_invoice(invoice_data, session_id)
        
        # Verify discovery log was created
        mock_db_manager.create_discovery_log.assert_called_once()
        
        # Verify log entry details
        call_args = mock_db_manager.create_discovery_log.call_args[0][0]
        assert isinstance(call_args, PartDiscoveryLog)
        assert call_args.part_number == "UNKNOWN_PART"
        assert call_args.action_taken == "discovered"
        assert call_args.processing_session_id == session_id
    
    def test_discovery_logging_handles_errors(self, discovery_service, mock_db_manager):
        """Test that discovery logging handles database errors gracefully."""
        mock_db_manager.get_part.side_effect = Exception("Part not found")
        mock_db_manager.create_discovery_log.side_effect = DatabaseError("Logging failed")
        
        # Create sample invoice data
        invoice_data = InvoiceData(
            invoice_number="INV001",
            line_items=[
                LineItem(item_code="UNKNOWN_PART", rate=Decimal("15.50"))
            ]
        )
        
        # Should not raise exception even if logging fails
        session_id = discovery_service.start_discovery_session()
        unknown_contexts = discovery_service.discover_unknown_parts_from_invoice(invoice_data, session_id)
        
        # Discovery should still work
        assert len(unknown_contexts) == 1
        assert unknown_contexts[0].part_number == "UNKNOWN_PART"


if __name__ == '__main__':
    pytest.main([__file__])