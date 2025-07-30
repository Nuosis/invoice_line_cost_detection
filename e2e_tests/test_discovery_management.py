"""
End-to-End Tests for Discovery Management Commands

This test suite validates all discovery management functionality without using any mocking.
All tests create real database files, discovery sessions, and system resources, then clean up completely.

Test Coverage:
- Discovery review command (reviewing unknown parts interactively)
- Discovery sessions command (listing and managing discovery sessions)
- Discovery stats command (statistics and analytics)
- Discovery export command (exporting discovery data)
- Session management and cleanup
- Discovery workflow integration
- Error handling for invalid sessions
- Cross-platform compatibility
"""

import csv
import json
import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any
import datetime

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part, PartDiscoveryLog, DatabaseError
from processing.part_discovery_service import PartDiscoveryService
from processing.part_discovery_models import DiscoverySession, UnknownPart


class TestDiscoveryManagement(unittest.TestCase):
    """
    Comprehensive e2e tests for discovery management functionality.
    
    These tests validate that all discovery management commands work correctly
    in real-world conditions without any mocking.
    """
    
    def setUp(self):
        """
        Set up test environment for each test.
        
        Creates a unique temporary directory and database file for each test
        to ensure complete isolation.
        """
        # Create unique temporary directory for this test
        self.test_id = str(uuid.uuid4())[:8]
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_discovery_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_discovery_db_{self.test_id}.db"
        
        # Create directories for export files
        self.export_dir = self.temp_dir / "exports"
        self.export_dir.mkdir()
        
        # Track created resources for cleanup
        self.created_files = [self.db_path]
        self.created_dirs = [self.temp_dir, self.export_dir]
        self.db_manager = None
        self.discovery_service = None
        
    def tearDown(self):
        """
        Clean up all resources created during the test.
        
        Ensures no test artifacts are left behind, following the strict
        cleanup requirements for e2e tests.
        """
        # Close discovery service if it exists
        if self.discovery_service:
            try:
                self.discovery_service.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Close database manager if it exists
        if self.db_manager:
            try:
                self.db_manager.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove all created files
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove export files
        try:
            for export_file in self.export_dir.glob("*"):
                if export_file.is_file():
                    export_file.unlink()
        except Exception:
            pass
        
        # Remove all created directories
        for dir_path in reversed(self.created_dirs):  # Remove in reverse order
            try:
                if dir_path.exists():
                    dir_path.rmdir()
            except Exception:
                pass  # Ignore errors during cleanup
    
    def _setup_test_discovery_data(self):
        """Set up test discovery data for testing discovery management."""
        # Add some existing parts for comparison
        existing_parts = [
            Part(
                part_number="EXISTING001",
                authorized_price=Decimal("15.50"),
                description="Existing Part 1",
                category="Test"
            ),
            Part(
                part_number="EXISTING002",
                authorized_price=Decimal("25.00"),
                description="Existing Part 2",
                category="Test"
            )
        ]
        
        for part in existing_parts:
            self.db_manager.create_part(part)
        
        # Create discovery logs for testing
        discovery_logs = [
            PartDiscoveryLog(
                part_number="DISCOVERED001",
                action_taken="discovered",
                invoice_number="INV001",
                invoice_date="2025-01-15",
                discovered_price=Decimal("12.50"),
                processing_session_id="session_001",
                notes="First discovery session"
            ),
            PartDiscoveryLog(
                part_number="DISCOVERED002",
                action_taken="discovered",
                invoice_number="INV001",
                invoice_date="2025-01-15",
                discovered_price=Decimal("18.75"),
                processing_session_id="session_001",
                notes="First discovery session"
            ),
            PartDiscoveryLog(
                part_number="DISCOVERED003",
                action_taken="discovered",
                invoice_number="INV002",
                invoice_date="2025-01-16",
                discovered_price=Decimal("22.00"),
                processing_session_id="session_002",
                notes="Second discovery session"
            ),
            PartDiscoveryLog(
                part_number="DISCOVERED001",
                action_taken="added",
                invoice_number="INV003",
                invoice_date="2025-01-17",
                discovered_price=Decimal("12.50"),
                authorized_price=Decimal("12.50"),
                processing_session_id="session_003",
                notes="Added to database"
            )
        ]
        
        for log in discovery_logs:
            self.db_manager.create_discovery_log(log)
    
    def test_discovery_sessions_list_basic_functionality(self):
        """
        Test discovery sessions list command basic functionality.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Get discovery sessions (simulates: discovery sessions)
        sessions = self.discovery_service.get_discovery_sessions()
        
        # Verify we have discovery sessions
        self.assertGreater(len(sessions), 0)
        
        # Verify session structure
        session_ids = {session.session_id for session in sessions}
        expected_sessions = {"session_001", "session_002", "session_003"}
        
        for expected_session in expected_sessions:
            self.assertIn(expected_session, session_ids)
        
        # Verify session details
        session_001 = next(s for s in sessions if s.session_id == "session_001")
        self.assertEqual(session_001.parts_discovered, 2)
        self.assertEqual(session_001.parts_added, 0)
        self.assertIsNotNone(session_001.session_date)
    
    def test_discovery_sessions_list_with_limit(self):
        """
        Test discovery sessions list command with limit parameter.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Get limited discovery sessions (simulates: discovery sessions --limit 2)
        limited_sessions = self.discovery_service.get_discovery_sessions(limit=2)
        
        # Verify limit was applied
        self.assertLessEqual(len(limited_sessions), 2)
        
        # Verify sessions are ordered by date (most recent first)
        if len(limited_sessions) > 1:
            for i in range(len(limited_sessions) - 1):
                self.assertGreaterEqual(
                    limited_sessions[i].session_date,
                    limited_sessions[i + 1].session_date
                )
    
    def test_discovery_sessions_detailed_information(self):
        """
        Test discovery sessions command with detailed information.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Get detailed session information (simulates: discovery sessions --detailed)
        sessions = self.discovery_service.get_discovery_sessions(detailed=True)
        
        # Verify detailed information is available
        for session in sessions:
            self.assertIsInstance(session, DiscoverySession)
            self.assertIsNotNone(session.session_id)
            self.assertIsNotNone(session.session_date)
            self.assertIsNotNone(session.parts_discovered)
            self.assertIsNotNone(session.parts_added)
            self.assertIsNotNone(session.parts_skipped)
            
            # Verify session has discovery details
            if hasattr(session, 'discovery_details'):
                self.assertIsInstance(session.discovery_details, list)
    
    def test_discovery_review_specific_session(self):
        """
        Test discovery review command for a specific session.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Review specific session (simulates: discovery review --session-id session_001)
        session_review = self.discovery_service.review_discovery_session("session_001")
        
        # Verify session review data
        self.assertIsNotNone(session_review)
        self.assertEqual(session_review['session_id'], "session_001")
        self.assertIn('discovered_parts', session_review)
        self.assertIn('session_summary', session_review)
        
        # Verify discovered parts in session
        discovered_parts = session_review['discovered_parts']
        self.assertEqual(len(discovered_parts), 2)
        
        # Verify specific parts
        part_numbers = {part['part_number'] for part in discovered_parts}
        self.assertIn("DISCOVERED001", part_numbers)
        self.assertIn("DISCOVERED002", part_numbers)
        
        # Verify part details
        discovered001 = next(p for p in discovered_parts if p['part_number'] == "DISCOVERED001")
        self.assertEqual(discovered001['discovered_price'], Decimal("12.50"))
        self.assertEqual(discovered001['invoice_number'], "INV001")
        self.assertEqual(discovered001['action_taken'], "discovered")
    
    def test_discovery_review_interactive_mode(self):
        """
        Test discovery review command in interactive mode.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Get unknown parts for interactive review (simulates: discovery review --interactive)
        unknown_parts = self.discovery_service.get_unknown_parts_for_review("session_001")
        
        # Verify unknown parts structure
        self.assertGreater(len(unknown_parts), 0)
        
        for unknown_part in unknown_parts:
            self.assertIsInstance(unknown_part, UnknownPart)
            self.assertIsNotNone(unknown_part.part_number)
            self.assertIsNotNone(unknown_part.discovered_price)
            self.assertIsNotNone(unknown_part.invoice_number)
            self.assertIsNotNone(unknown_part.description)
        
        # Simulate interactive decisions
        for unknown_part in unknown_parts:
            # Simulate adding a part to database
            if unknown_part.part_number == "DISCOVERED001":
                new_part = Part(
                    part_number=unknown_part.part_number,
                    authorized_price=unknown_part.discovered_price,
                    description=unknown_part.description or f"Added from discovery",
                    category="discovered",
                    source="discovered",
                    first_seen_invoice=unknown_part.invoice_number
                )
                
                # Add part to database
                self.db_manager.create_part(new_part)
                
                # Log the action
                action_log = PartDiscoveryLog(
                    part_number=unknown_part.part_number,
                    action_taken="added",
                    invoice_number=unknown_part.invoice_number,
                    discovered_price=unknown_part.discovered_price,
                    authorized_price=unknown_part.discovered_price,
                    processing_session_id="interactive_session",
                    user_decision="add_to_database",
                    notes="Added via interactive review"
                )
                self.db_manager.create_discovery_log(action_log)
        
        # Verify part was added
        added_part = self.db_manager.get_part("DISCOVERED001")
        self.assertEqual(added_part.part_number, "DISCOVERED001")
        self.assertEqual(added_part.source, "discovered")
    
    def test_discovery_stats_overall_statistics(self):
        """
        Test discovery stats command for overall statistics.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Get overall discovery statistics (simulates: discovery stats)
        stats = self.discovery_service.get_discovery_statistics()
        
        # Verify statistics structure
        self.assertIsInstance(stats, dict)
        self.assertIn('total_sessions', stats)
        self.assertIn('total_parts_discovered', stats)
        self.assertIn('total_parts_added', stats)
        self.assertIn('total_parts_skipped', stats)
        self.assertIn('discovery_rate', stats)
        
        # Verify statistics values
        self.assertEqual(stats['total_sessions'], 3)
        self.assertEqual(stats['total_parts_discovered'], 3)  # 3 "discovered" actions
        self.assertEqual(stats['total_parts_added'], 1)  # 1 "added" action
        
        # Verify discovery rate calculation
        if stats['total_parts_discovered'] > 0:
            expected_rate = stats['total_parts_added'] / stats['total_parts_discovered']
            self.assertEqual(stats['discovery_rate'], expected_rate)
    
    def test_discovery_stats_time_period_filter(self):
        """
        Test discovery stats command with time period filtering.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Get statistics for specific time period (simulates: discovery stats --days 7)
        recent_stats = self.discovery_service.get_discovery_statistics(days=7)
        
        # Verify time-filtered statistics
        self.assertIsInstance(recent_stats, dict)
        self.assertIn('time_period', recent_stats)
        self.assertIn('total_sessions', recent_stats)
        self.assertIn('total_parts_discovered', recent_stats)
        
        # Since our test data is recent, should include all sessions
        self.assertGreater(recent_stats['total_sessions'], 0)
        
        # Test with very short time period (simulates: discovery stats --days 1)
        yesterday_stats = self.discovery_service.get_discovery_statistics(days=1)
        
        # Should have fewer or equal sessions compared to 7-day period
        self.assertLessEqual(yesterday_stats['total_sessions'], recent_stats['total_sessions'])
    
    def test_discovery_stats_session_specific(self):
        """
        Test discovery stats command for specific session.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Get statistics for specific session (simulates: discovery stats --session-id session_001)
        session_stats = self.discovery_service.get_session_statistics("session_001")
        
        # Verify session-specific statistics
        self.assertIsInstance(session_stats, dict)
        self.assertEqual(session_stats['session_id'], "session_001")
        self.assertIn('parts_discovered', session_stats)
        self.assertIn('parts_added', session_stats)
        self.assertIn('unique_invoices', session_stats)
        self.assertIn('price_range', session_stats)
        
        # Verify specific values for session_001
        self.assertEqual(session_stats['parts_discovered'], 2)
        self.assertEqual(session_stats['parts_added'], 0)
        self.assertEqual(session_stats['unique_invoices'], 1)  # Only INV001
        
        # Verify price range
        price_range = session_stats['price_range']
        self.assertIn('min_price', price_range)
        self.assertIn('max_price', price_range)
        self.assertEqual(price_range['min_price'], Decimal("12.50"))
        self.assertEqual(price_range['max_price'], Decimal("18.75"))
    
    def test_discovery_export_csv_functionality(self):
        """
        Test discovery export command with CSV format.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Export discovery data to CSV (simulates: discovery export --output discoveries.csv)
        export_path = self.export_dir / "discoveries_export.csv"
        self.created_files.append(export_path)
        
        export_result = self.discovery_service.export_discovery_data(
            str(export_path),
            format='csv'
        )
        
        # Verify export was successful
        self.assertTrue(export_result['success'])
        self.assertTrue(export_path.exists())
        
        # Verify CSV content
        with open(export_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            export_rows = list(reader)
        
        # Should have 4 discovery log entries
        self.assertEqual(len(export_rows), 4)
        
        # Verify CSV structure
        expected_columns = [
            'part_number', 'action_taken', 'invoice_number', 'invoice_date',
            'discovered_price', 'authorized_price', 'processing_session_id',
            'user_decision', 'discovery_date', 'notes'
        ]
        
        for column in expected_columns:
            self.assertIn(column, export_rows[0].keys())
        
        # Verify specific data
        discovered001_rows = [row for row in export_rows if row['part_number'] == 'DISCOVERED001']
        self.assertEqual(len(discovered001_rows), 2)  # One discovered, one added
        
        # Verify actions
        actions = {row['action_taken'] for row in discovered001_rows}
        self.assertIn('discovered', actions)
        self.assertIn('added', actions)
    
    def test_discovery_export_json_functionality(self):
        """
        Test discovery export command with JSON format.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Export discovery data to JSON (simulates: discovery export --output discoveries.json --format json)
        export_path = self.export_dir / "discoveries_export.json"
        self.created_files.append(export_path)
        
        export_result = self.discovery_service.export_discovery_data(
            str(export_path),
            format='json'
        )
        
        # Verify export was successful
        self.assertTrue(export_result['success'])
        self.assertTrue(export_path.exists())
        
        # Verify JSON content
        with open(export_path, 'r', encoding='utf-8') as jsonfile:
            export_data = json.load(jsonfile)
        
        # Verify JSON structure
        self.assertIn('export_metadata', export_data)
        self.assertIn('discovery_sessions', export_data)
        self.assertIn('discovery_logs', export_data)
        
        # Verify metadata
        metadata = export_data['export_metadata']
        self.assertIn('export_date', metadata)
        self.assertIn('total_sessions', metadata)
        self.assertIn('total_discoveries', metadata)
        
        # Verify discovery logs
        discovery_logs = export_data['discovery_logs']
        self.assertEqual(len(discovery_logs), 4)
        
        # Verify log structure
        for log in discovery_logs:
            self.assertIn('part_number', log)
            self.assertIn('action_taken', log)
            self.assertIn('processing_session_id', log)
            self.assertIn('discovery_date', log)
    
    def test_discovery_export_session_specific(self):
        """
        Test discovery export command for specific session.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Export specific session (simulates: discovery export --session-id session_001 --output session_001.csv)
        export_path = self.export_dir / "session_001_export.csv"
        self.created_files.append(export_path)
        
        export_result = self.discovery_service.export_discovery_data(
            str(export_path),
            format='csv',
            session_id='session_001'
        )
        
        # Verify export was successful
        self.assertTrue(export_result['success'])
        self.assertTrue(export_path.exists())
        
        # Verify CSV content is filtered to session_001
        with open(export_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            export_rows = list(reader)
        
        # Should have only 2 entries for session_001
        self.assertEqual(len(export_rows), 2)
        
        # Verify all rows are from session_001
        for row in export_rows:
            self.assertEqual(row['processing_session_id'], 'session_001')
        
        # Verify part numbers
        part_numbers = {row['part_number'] for row in export_rows}
        expected_parts = {'DISCOVERED001', 'DISCOVERED002'}
        self.assertEqual(part_numbers, expected_parts)
    
    def test_discovery_export_with_added_parts_filter(self):
        """
        Test discovery export command with added parts filter.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Export only added parts (simulates: discovery export --include-added --output added_parts.csv)
        export_path = self.export_dir / "added_parts_export.csv"
        self.created_files.append(export_path)
        
        export_result = self.discovery_service.export_discovery_data(
            str(export_path),
            format='csv',
            include_added_only=True
        )
        
        # Verify export was successful
        self.assertTrue(export_result['success'])
        self.assertTrue(export_path.exists())
        
        # Verify CSV content contains only added parts
        with open(export_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            export_rows = list(reader)
        
        # Should have only 1 entry (the "added" action)
        self.assertEqual(len(export_rows), 1)
        
        # Verify it's the added action
        added_row = export_rows[0]
        self.assertEqual(added_row['action_taken'], 'added')
        self.assertEqual(added_row['part_number'], 'DISCOVERED001')
        self.assertEqual(added_row['processing_session_id'], 'session_003')
    
    def test_discovery_error_handling_invalid_session(self):
        """
        Test error handling for invalid session IDs.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Test reviewing non-existent session
        with self.assertRaises(DatabaseError):
            self.discovery_service.review_discovery_session("nonexistent_session")
        
        # Test getting statistics for non-existent session
        with self.assertRaises(DatabaseError):
            self.discovery_service.get_session_statistics("nonexistent_session")
        
        # Test exporting non-existent session
        export_path = self.export_dir / "invalid_session.csv"
        self.created_files.append(export_path)
        
        export_result = self.discovery_service.export_discovery_data(
            str(export_path),
            format='csv',
            session_id='nonexistent_session'
        )
        
        # Should fail gracefully
        self.assertFalse(export_result['success'])
        self.assertIn('error', export_result)
    
    def test_discovery_session_cleanup(self):
        """
        Test discovery session cleanup functionality.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Add old discovery logs for cleanup testing
        old_date = datetime.datetime.now() - datetime.timedelta(days=30)
        old_logs = [
            PartDiscoveryLog(
                part_number="OLD001",
                action_taken="discovered",
                invoice_number="OLD_INV001",
                discovered_price=Decimal("10.00"),
                processing_session_id="old_session_001",
                discovery_date=old_date,
                notes="Old discovery session"
            ),
            PartDiscoveryLog(
                part_number="OLD002",
                action_taken="discovered",
                invoice_number="OLD_INV002",
                discovered_price=Decimal("15.00"),
                processing_session_id="old_session_002",
                discovery_date=old_date,
                notes="Old discovery session"
            )
        ]
        
        for log in old_logs:
            self.db_manager.create_discovery_log(log)
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Get all sessions before cleanup
        all_sessions_before = self.discovery_service.get_discovery_sessions()
        total_before = len(all_sessions_before)
        
        # Perform cleanup (simulates: discovery cleanup --days 7)
        cleanup_result = self.discovery_service.cleanup_old_sessions(days=7)
        
        # Verify cleanup results
        self.assertTrue(cleanup_result['success'])
        self.assertIn('sessions_cleaned', cleanup_result)
        self.assertIn('logs_removed', cleanup_result)
        
        # Get sessions after cleanup
        all_sessions_after = self.discovery_service.get_discovery_sessions()
        
        # Should have fewer sessions after cleanup
        self.assertLessEqual(len(all_sessions_after), total_before)
        
        # Verify recent sessions are preserved
        recent_session_ids = {session.session_id for session in all_sessions_after}
        self.assertIn("session_001", recent_session_ids)
        self.assertIn("session_002", recent_session_ids)
        self.assertIn("session_003", recent_session_ids)
    
    def test_discovery_cross_platform_compatibility(self):
        """
        Test discovery management functionality across different platforms.
        """
        # Initialize database manager and setup test data
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_discovery_data()
        
        # Initialize discovery service
        self.discovery_service = PartDiscoveryService(self.db_manager)
        
        # Test export with platform-specific paths
        export_path = self.export_dir / "cross_platform_export.csv"
        self.created_files.append(export_path)
        
        export_result = self.discovery_service.export_discovery_data(
            str(export_path),
            format='csv'
        )
        
        # Verify export works across platforms
        self.assertTrue(export_result['success'])
        self.assertTrue(export_path.exists())
        
        # Test file can be read correctly
        with open(export_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            export_rows = list(reader)
        
        self.assertGreater(len(export_rows), 0)
        
        # Test with special characters in session IDs and notes
        special_log = PartDiscoveryLog(
            part_number="SPECIAL_CHARS_001",
            action_taken="discovered",
            invoice_number="SPECIAL_INV_001",
            discovered_price=Decimal("20.00"),
            processing_session_id="session_with_émojis_🔧",
            notes="Notes with special chars: @#$%^&*()"
        )
        self.db_manager.create_discovery_log(special_log)
        
        # Export again with special characters
        special_export_path = self.export_dir / "special_chars_export.csv"
        self.created_files.append(special_export_path)
        
        special_export_result = self.discovery_service.export_discovery_data(
            str(special_export_path),
            format='csv'
        )
        
        # Verify special characters are handled correctly
        self.assertTrue(special_export_result['success'])
        
        with open(special_export_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            special_rows = list(reader)
        
        # Find the special character row
        special_row = next(
            row for row in special_rows 
            if row['part_number'] == 'SPECIAL_CHARS_001'
        )
        
        self.assertEqual(special_row['processing_session_id'], "session_with_émojis_🔧")
        self.assertEqual(special_row['notes'], "Notes with special chars: @#$%^&*()")


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)