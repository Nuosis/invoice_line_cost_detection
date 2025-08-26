"""
End-to-End Tests for Parts Management Commands

This test suite validates all parts management functionality without using any mocking.
All tests create real database files and system resources, then clean up completely.

Test Coverage:
- Parts add command (individual part creation)
- Parts list command (listing with filters and formats)
- Parts get command (retrieving specific part details)
- Parts update command (modifying existing parts)
- Parts delete command (soft and hard deletion)
- Parts import command (CSV import functionality)
- Parts export command (CSV export functionality)
- Parts stats command (statistics and reporting)
- Error handling for invalid operations
- Cross-platform compatibility
"""

import csv
import os
import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part, DatabaseError, ValidationError


class TestPartsManagement(unittest.TestCase):
    """
    Comprehensive e2e tests for parts management functionality.
    
    These tests validate that all parts management commands work correctly
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
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_parts_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_parts_db_{self.test_id}.db"
        
        # Create temporary CSV files directory
        self.csv_dir = self.temp_dir / "csv_files"
        self.csv_dir.mkdir()
        
        # Track created resources for cleanup
        self.created_files = [self.db_path]
        self.created_dirs = [self.temp_dir, self.csv_dir]
        self.db_manager = None
        
    def tearDown(self):
        """
        Clean up all resources created during the test.
        
        Ensures no test artifacts are left behind, following the strict
        cleanup requirements for e2e tests.
        """
        # Close database manager if it exists
        if self.db_manager:
            try:
                self.db_manager.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove all created files (including CSV files)
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Remove CSV files in csv_dir
        try:
            for csv_file in self.csv_dir.glob("*.csv"):
                csv_file.unlink()
        except Exception:
            pass
        
        # Remove all created directories
        for dir_path in reversed(self.created_dirs):  # Remove in reverse order
            try:
                if dir_path.exists():
                    dir_path.rmdir()
            except Exception:
                pass  # Ignore errors during cleanup
    
    def test_parts_add_basic_functionality(self):
        """
        Test basic parts add command functionality.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test adding a basic part
        test_part = Part(
            part_number="TEST001",
            authorized_price=Decimal("15.50"),
            description="Test Part 1"
        )
        
        # Add the part (simulates: parts add TEST001 15.50 --description "Test Part 1")
        self.db_manager.create_part(test_part)
        
        # Verify part was added
        retrieved_part = self.db_manager.get_part("TEST001")
        self.assertEqual(retrieved_part.part_number, "TEST001")
        self.assertEqual(retrieved_part.authorized_price, Decimal("15.50"))
        self.assertEqual(retrieved_part.description, "Test Part 1")
        self.assertTrue(retrieved_part.is_active)
        
        # Verify database stats updated
        stats = self.db_manager.get_database_stats()
        self.assertEqual(stats['total_parts'], 1)
        self.assertEqual(stats['active_parts'], 1)
    
    def test_parts_add_with_full_details(self):
        """
        Test parts add command with all optional fields.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test adding a part with full details
        test_part = Part(
            part_number="FULL001",
            authorized_price=Decimal("25.75"),
            description="Full Details Test Part",
            category="Test Category",
            source="manual",
            first_seen_invoice="INV001",
            notes="Test notes for this part"
        )
        
        # Add the part (simulates: parts add FULL001 25.75 --description "..." --category "..." --notes "...")
        self.db_manager.create_part(test_part)
        
        # Verify all fields were saved correctly
        retrieved_part = self.db_manager.get_part("FULL001")
        self.assertEqual(retrieved_part.part_number, "FULL001")
        self.assertEqual(retrieved_part.authorized_price, Decimal("25.75"))
        self.assertEqual(retrieved_part.description, "Full Details Test Part")
        self.assertEqual(retrieved_part.category, "Test Category")
        self.assertEqual(retrieved_part.source, "manual")
        self.assertEqual(retrieved_part.first_seen_invoice, "INV001")
        self.assertEqual(retrieved_part.notes, "Test notes for this part")
        self.assertTrue(retrieved_part.is_active)
        self.assertIsNotNone(retrieved_part.created_date)
        self.assertIsNotNone(retrieved_part.last_updated)
    
    def test_parts_list_basic_functionality(self):
        """
        Test basic parts list command functionality.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add multiple test parts
        test_parts = [
            Part(part_number="LIST001", authorized_price=Decimal("10.00"), description="List Test 1", category="Category A"),
            Part(part_number="LIST002", authorized_price=Decimal("20.00"), description="List Test 2", category="Category B"),
            Part(part_number="LIST003", authorized_price=Decimal("30.00"), description="List Test 3", category="Category A", is_active=False)
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
        
        # Test listing all parts (simulates: parts list)
        all_parts = self.db_manager.list_parts()
        self.assertEqual(len(all_parts), 3)
        
        # Verify parts are returned in correct order (by part_number)
        part_numbers = [part.part_number for part in all_parts]
        self.assertEqual(part_numbers, ["LIST001", "LIST002", "LIST003"])
        
        # Test listing only active parts (simulates: parts list --active-only)
        active_parts = self.db_manager.list_parts(active_only=True)
        self.assertEqual(len(active_parts), 2)
        active_part_numbers = [part.part_number for part in active_parts]
        self.assertIn("LIST001", active_part_numbers)
        self.assertIn("LIST002", active_part_numbers)
        self.assertNotIn("LIST003", active_part_numbers)
    
    def test_parts_list_with_category_filter(self):
        """
        Test parts list command with category filtering.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add parts with different categories
        test_parts = [
            Part(part_number="CAT001", authorized_price=Decimal("10.00"), category="Clothing"),
            Part(part_number="CAT002", authorized_price=Decimal("20.00"), category="Tools"),
            Part(part_number="CAT003", authorized_price=Decimal("30.00"), category="Clothing"),
            Part(part_number="CAT004", authorized_price=Decimal("40.00"), category="Safety")
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
        
        # Test filtering by category (simulates: parts list --category "Clothing")
        clothing_parts = self.db_manager.list_parts(category="Clothing")
        self.assertEqual(len(clothing_parts), 2)
        
        clothing_part_numbers = [part.part_number for part in clothing_parts]
        self.assertIn("CAT001", clothing_part_numbers)
        self.assertIn("CAT003", clothing_part_numbers)
        
        # Test filtering by different category
        tools_parts = self.db_manager.list_parts(category="Tools")
        self.assertEqual(len(tools_parts), 1)
        self.assertEqual(tools_parts[0].part_number, "CAT002")
    
    def test_parts_get_functionality(self):
        """
        Test parts get command functionality.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add a test part
        test_part = Part(
            part_number="GET001",
            authorized_price=Decimal("45.25"),
            description="Get Test Part",
            category="Test",
            notes="Detailed notes for get test"
        )
        self.db_manager.create_part(test_part)
        
        # Test getting existing part (simulates: parts get GET001)
        retrieved_part = self.db_manager.get_part("GET001")
        self.assertIsNotNone(retrieved_part)
        self.assertEqual(retrieved_part.part_number, "GET001")
        self.assertEqual(retrieved_part.authorized_price, Decimal("45.25"))
        self.assertEqual(retrieved_part.description, "Get Test Part")
        self.assertEqual(retrieved_part.category, "Test")
        self.assertEqual(retrieved_part.notes, "Detailed notes for get test")
        
        # Test getting non-existent part (simulates: parts get NONEXISTENT)
        with self.assertRaises(DatabaseError):
            self.db_manager.get_part("NONEXISTENT")
    
    def test_parts_update_functionality(self):
        """
        Test parts update command functionality.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add a test part
        original_part = Part(
            part_number="UPDATE001",
            authorized_price=Decimal("10.00"),
            description="Original Description",
            category="Original Category"
        )
        self.db_manager.create_part(original_part)
        
        # Test updating price (simulates: parts update UPDATE001 --price 15.50)
        self.db_manager.update_part("UPDATE001", authorized_price=Decimal("15.50"))
        
        updated_part = self.db_manager.get_part("UPDATE001")
        self.assertEqual(updated_part.authorized_price, Decimal("15.50"))
        self.assertEqual(updated_part.description, "Original Description")  # Should remain unchanged
        
        # Test updating multiple fields (simulates: parts update UPDATE001 --description "New Desc" --category "New Cat")
        self.db_manager.update_part(
            "UPDATE001",
            description="New Description",
            category="New Category",
            notes="Added notes"
        )
        
        updated_part = self.db_manager.get_part("UPDATE001")
        self.assertEqual(updated_part.authorized_price, Decimal("15.50"))  # Should remain from previous update
        self.assertEqual(updated_part.description, "New Description")
        self.assertEqual(updated_part.category, "New Category")
        self.assertEqual(updated_part.notes, "Added notes")
        
        # Verify last_updated timestamp was updated
        self.assertIsNotNone(updated_part.last_updated)
    
    def test_parts_update_activation_status(self):
        """
        Test parts update command for activation/deactivation.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add a test part
        test_part = Part(part_number="ACTIVE001", authorized_price=Decimal("20.00"))
        self.db_manager.create_part(test_part)
        
        # Verify part is initially active
        part = self.db_manager.get_part("ACTIVE001")
        self.assertTrue(part.is_active)
        
        # Test deactivation (simulates: parts update ACTIVE001 --deactivate)
        self.db_manager.update_part("ACTIVE001", is_active=False)
        
        deactivated_part = self.db_manager.get_part("ACTIVE001")
        self.assertFalse(deactivated_part.is_active)
        
        # Test reactivation (simulates: parts update ACTIVE001 --activate)
        self.db_manager.update_part("ACTIVE001", is_active=True)
        
        reactivated_part = self.db_manager.get_part("ACTIVE001")
        self.assertTrue(reactivated_part.is_active)
    
    def test_parts_delete_soft_functionality(self):
        """
        Test parts delete command with soft deletion.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add a test part
        test_part = Part(part_number="DELETE001", authorized_price=Decimal("30.00"))
        self.db_manager.create_part(test_part)
        
        # Verify part exists and is active
        part = self.db_manager.get_part("DELETE001")
        self.assertTrue(part.is_active)
        
        # Test soft deletion (simulates: parts delete DELETE001 --soft)
        self.db_manager.delete_part("DELETE001", soft_delete=True)
        
        # Part should still exist but be inactive
        deleted_part = self.db_manager.get_part("DELETE001")
        self.assertFalse(deleted_part.is_active)
        
        # Verify part doesn't appear in active-only listings
        active_parts = self.db_manager.list_parts(active_only=True)
        active_part_numbers = [part.part_number for part in active_parts]
        self.assertNotIn("DELETE001", active_part_numbers)
        
        # But appears in all parts listing
        all_parts = self.db_manager.list_parts()
        all_part_numbers = [part.part_number for part in all_parts]
        self.assertIn("DELETE001", all_part_numbers)
    
    def test_parts_delete_hard_functionality(self):
        """
        Test parts delete command with hard deletion.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add a test part
        test_part = Part(part_number="HARDDELETE001", authorized_price=Decimal("40.00"))
        self.db_manager.create_part(test_part)
        
        # Verify part exists
        part = self.db_manager.get_part("HARDDELETE001")
        self.assertIsNotNone(part)
        
        # Test hard deletion (simulates: parts delete HARDDELETE001 --hard)
        self.db_manager.delete_part("HARDDELETE001", soft_delete=False)
        
        # Part should no longer exist
        with self.assertRaises(DatabaseError):
            self.db_manager.get_part("HARDDELETE001")
        
        # Verify part doesn't appear in any listings
        all_parts = self.db_manager.list_parts()
        all_part_numbers = [part.part_number for part in all_parts]
        self.assertNotIn("HARDDELETE001", all_part_numbers)
    
    def test_parts_import_csv_functionality(self):
        """
        Test parts import command with CSV file.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create test CSV file
        csv_file_path = self.csv_dir / "import_test.csv"
        self.created_files.append(csv_file_path)
        
        test_data = [
            ["part_number", "authorized_price", "description", "category", "notes"],
            ["IMP001", "10.50", "Import Test 1", "Category A", "Notes for part 1"],
            ["IMP002", "20.75", "Import Test 2", "Category B", "Notes for part 2"],
            ["IMP003", "30.00", "Import Test 3", "Category A", "Notes for part 3"]
        ]
        
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(test_data)
        
        # Test CSV import (simulates: parts import import_test.csv)
        self.db_manager.import_parts_from_csv(str(csv_file_path))
        
        # Verify all parts were imported
        imported_parts = self.db_manager.list_parts()
        self.assertEqual(len(imported_parts), 3)
        
        # Verify specific part details
        part1 = self.db_manager.get_part("IMP001")
        self.assertEqual(part1.authorized_price, Decimal("10.50"))
        self.assertEqual(part1.description, "Import Test 1")
        self.assertEqual(part1.category, "Category A")
        self.assertEqual(part1.notes, "Notes for part 1")
        
        part2 = self.db_manager.get_part("IMP002")
        self.assertEqual(part2.authorized_price, Decimal("20.75"))
        self.assertEqual(part2.description, "Import Test 2")
        self.assertEqual(part2.category, "Category B")
    
    def test_parts_import_csv_with_update_existing(self):
        """
        Test parts import command with update existing functionality.
        
        With composite keys, parts are identified by item_type|description|part_number.
        This test verifies that CSV import correctly handles the composite key system.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add an existing part
        existing_part = Part(
            part_number="EXISTING001",
            authorized_price=Decimal("50.00"),
            description="Original Description"
        )
        self.db_manager.create_part(existing_part)
        
        # Create CSV with same composite key (same description and part_number) and new part
        csv_file_path = self.csv_dir / "update_import_test.csv"
        self.created_files.append(csv_file_path)
        
        test_data = [
            ["part_number", "authorized_price", "description", "category"],
            ["EXISTING001", "75.00", "Original Description", "Updated Category"],  # Same composite key
            ["NEW001", "25.00", "New Part", "New Category"]
        ]
        
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(test_data)
        
        # Test import with update existing (simulates: parts import update_import_test.csv --update-existing)
        self.db_manager.import_parts_from_csv(str(csv_file_path), update_existing=True)
        
        # Verify existing part was updated (same composite key, so it should update)
        updated_part = self.db_manager.get_part("EXISTING001")
        self.assertEqual(updated_part.authorized_price, Decimal("75.00"))
        self.assertEqual(updated_part.description, "Original Description")  # Same description
        self.assertEqual(updated_part.category, "Updated Category")
        
        # Verify new part was added
        new_part = self.db_manager.get_part("NEW001")
        self.assertEqual(new_part.authorized_price, Decimal("25.00"))
        self.assertEqual(new_part.description, "New Part")
        
        # Verify total count - should still be 2 parts
        all_parts = self.db_manager.list_parts()
        self.assertEqual(len(all_parts), 2)
    
    def test_parts_export_csv_functionality(self):
        """
        Test parts export command functionality.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add test parts
        test_parts = [
            Part(part_number="EXP001", authorized_price=Decimal("15.50"), description="Export Test 1", category="Category A"),
            Part(part_number="EXP002", authorized_price=Decimal("25.75"), description="Export Test 2", category="Category B"),
            Part(part_number="EXP003", authorized_price=Decimal("35.00"), description="Export Test 3", category="Category A", is_active=False)
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
        
        # Test export all parts (simulates: parts export all_parts.csv)
        export_file_path = self.csv_dir / "export_all.csv"
        self.created_files.append(export_file_path)
        
        self.db_manager.export_parts_to_csv(str(export_file_path))
        
        # Verify export file was created
        self.assertTrue(export_file_path.exists())
        
        # Verify export file contents
        with open(export_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            exported_rows = list(reader)
        
        self.assertEqual(len(exported_rows), 3)
        
        # Verify specific exported data
        exp001_row = next(row for row in exported_rows if row['part_number'] == 'EXP001')
        self.assertEqual(exp001_row['authorized_price'], '15.50')
        self.assertEqual(exp001_row['description'], 'Export Test 1')
        self.assertEqual(exp001_row['category'], 'Category A')
        
        # Test export with category filter (simulates: parts export category_a.csv --category "Category A")
        category_export_path = self.csv_dir / "export_category_a.csv"
        self.created_files.append(category_export_path)
        
        self.db_manager.export_parts_to_csv(str(category_export_path), category="Category A")
        
        # Verify filtered export
        with open(category_export_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            category_rows = list(reader)
        
        self.assertEqual(len(category_rows), 2)  # EXP001 and EXP003
        for row in category_rows:
            self.assertEqual(row['category'], 'Category A')
    
    def test_parts_export_csv_active_only(self):
        """
        Test parts export command with active-only filter.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add test parts (mix of active and inactive)
        test_parts = [
            Part(part_number="ACTIVE001", authorized_price=Decimal("10.00"), is_active=True),
            Part(part_number="ACTIVE002", authorized_price=Decimal("20.00"), is_active=True),
            Part(part_number="INACTIVE001", authorized_price=Decimal("30.00"), is_active=False)
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
        
        # Test export active only (simulates: parts export active_parts.csv --active-only)
        active_export_path = self.csv_dir / "export_active_only.csv"
        self.created_files.append(active_export_path)
        
        self.db_manager.export_parts_to_csv(str(active_export_path), active_only=True)
        
        # Verify only active parts were exported
        with open(active_export_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            active_rows = list(reader)
        
        self.assertEqual(len(active_rows), 2)
        active_part_numbers = [row['part_number'] for row in active_rows]
        self.assertIn('ACTIVE001', active_part_numbers)
        self.assertIn('ACTIVE002', active_part_numbers)
        self.assertNotIn('INACTIVE001', active_part_numbers)
    
    def test_parts_stats_functionality(self):
        """
        Test parts stats command functionality.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Add test parts with various categories and statuses
        test_parts = [
            Part(part_number="STAT001", authorized_price=Decimal("10.00"), category="Clothing", is_active=True),
            Part(part_number="STAT002", authorized_price=Decimal("20.00"), category="Clothing", is_active=True),
            Part(part_number="STAT003", authorized_price=Decimal("30.00"), category="Tools", is_active=True),
            Part(part_number="STAT004", authorized_price=Decimal("40.00"), category="Tools", is_active=False),
            Part(part_number="STAT005", authorized_price=Decimal("50.00"), category="Safety", is_active=True)
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
        
        # Test overall stats (simulates: parts stats)
        overall_stats = self.db_manager.get_parts_statistics()
        
        self.assertEqual(overall_stats['total_parts'], 5)
        self.assertEqual(overall_stats['active_parts'], 4)
        self.assertEqual(overall_stats['inactive_parts'], 1)
        self.assertEqual(overall_stats['categories_count'], 3)
        
        # Verify category breakdown
        self.assertIn('category_breakdown', overall_stats)
        category_breakdown = overall_stats['category_breakdown']
        self.assertEqual(category_breakdown['Clothing'], 2)
        self.assertEqual(category_breakdown['Tools'], 2)
        self.assertEqual(category_breakdown['Safety'], 1)
        
        # Test category-specific stats (simulates: parts stats --category "Clothing")
        clothing_stats = self.db_manager.get_parts_statistics(category="Clothing")
        
        self.assertEqual(clothing_stats['total_parts'], 2)
        self.assertEqual(clothing_stats['active_parts'], 2)
        self.assertEqual(clothing_stats['inactive_parts'], 0)
    
    def test_parts_error_handling(self):
        """
        Test error handling for various invalid operations.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test adding duplicate part
        test_part = Part(part_number="DUPLICATE001", authorized_price=Decimal("10.00"))
        self.db_manager.create_part(test_part)
        
        # Attempting to add same part again should raise error
        duplicate_part = Part(part_number="DUPLICATE001", authorized_price=Decimal("20.00"))
        with self.assertRaises(DatabaseError):
            self.db_manager.create_part(duplicate_part)
        
        # Test updating non-existent part
        with self.assertRaises(DatabaseError):
            self.db_manager.update_part("NONEXISTENT", authorized_price=Decimal("15.00"))
        
        # Test deleting non-existent part
        with self.assertRaises(DatabaseError):
            self.db_manager.delete_part("NONEXISTENT")
        
        # Test invalid price values
        with self.assertRaises(ValidationError):
            invalid_part = Part(part_number="INVALID001", authorized_price=Decimal("-10.00"))
            self.db_manager.create_part(invalid_part)
        
        # Test importing non-existent CSV file
        with self.assertRaises(DatabaseError):
            self.db_manager.import_parts_from_csv("nonexistent_file.csv")
    
    def test_parts_cross_platform_compatibility(self):
        """
        Test parts management functionality across different platforms.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Test with various character encodings and special characters
        test_parts = [
            Part(part_number="UNICODE001", authorized_price=Decimal("10.00"), description="Test with émojis 🔧"),
            Part(part_number="SPECIAL002", authorized_price=Decimal("20.00"), description="Test with special chars: @#$%^&*()"),
            Part(part_number="LONG003", authorized_price=Decimal("30.00"), description="A" * 200)  # Long description
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
        
        # Verify all parts were stored and retrieved correctly
        for part in test_parts:
            retrieved_part = self.db_manager.get_part(part.part_number)
            self.assertEqual(retrieved_part.description, part.description)
        
        # Test CSV export/import with special characters
        export_path = self.csv_dir / "special_chars_export.csv"
        self.created_files.append(export_path)
        
        self.db_manager.export_parts_to_csv(str(export_path))
        
        # Verify export file can be read correctly
        with open(export_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            exported_rows = list(reader)
        
        self.assertEqual(len(exported_rows), 3)
        
        # Find the unicode part and verify its description
        unicode_row = next(row for row in exported_rows if row['part_number'] == 'UNICODE001')
        self.assertEqual(unicode_row['description'], "Test with émojis 🔧")


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)