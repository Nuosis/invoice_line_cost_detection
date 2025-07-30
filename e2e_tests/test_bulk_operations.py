"""
End-to-End Tests for Bulk Operations Commands

This test suite validates all bulk operations functionality without using any mocking.
All tests create real database files, CSV files, and system resources, then clean up completely.

Test Coverage:
- Bulk update command (updating multiple parts from CSV)
- Bulk delete command (soft and hard deletion of multiple parts)
- Bulk activate command (reactivating multiple deactivated parts)
- CSV file processing and validation
- Batch size handling and performance
- Error handling for invalid operations
- Dry-run functionality for preview
- Cross-platform file handling
"""

import csv
import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

# Import the modules we're testing
from database.database import DatabaseManager
from database.models import Part, DatabaseError, ValidationError
from cli.commands.bulk_operations import BulkOperationsManager


class TestBulkOperations(unittest.TestCase):
    """
    Comprehensive e2e tests for bulk operations functionality.
    
    These tests validate that all bulk operations commands work correctly
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
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_bulk_test_{self.test_id}_"))
        
        # Create unique database file path
        self.db_path = self.temp_dir / f"test_bulk_db_{self.test_id}.db"
        
        # Create directories for CSV files
        self.csv_dir = self.temp_dir / "csv_files"
        self.csv_dir.mkdir()
        
        # Track created resources for cleanup
        self.created_files = [self.db_path]
        self.created_dirs = [self.temp_dir, self.csv_dir]
        self.db_manager = None
        self.bulk_manager = None
        
    def tearDown(self):
        """
        Clean up all resources created during the test.
        
        Ensures no test artifacts are left behind, following the strict
        cleanup requirements for e2e tests.
        """
        # Close bulk operations manager if it exists
        if self.bulk_manager:
            try:
                self.bulk_manager.close()
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
        
        # Remove CSV files
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
    
    def _setup_test_parts(self):
        """Set up test parts for bulk operations testing."""
        test_parts = [
            Part(
                part_number="BULK001",
                authorized_price=Decimal("10.00"),
                description="Bulk Test Part 1",
                category="Category A",
                is_active=True
            ),
            Part(
                part_number="BULK002",
                authorized_price=Decimal("20.00"),
                description="Bulk Test Part 2",
                category="Category A",
                is_active=True
            ),
            Part(
                part_number="BULK003",
                authorized_price=Decimal("30.00"),
                description="Bulk Test Part 3",
                category="Category B",
                is_active=True
            ),
            Part(
                part_number="BULK004",
                authorized_price=Decimal("40.00"),
                description="Bulk Test Part 4",
                category="Category B",
                is_active=False  # Inactive for activation testing
            ),
            Part(
                part_number="BULK005",
                authorized_price=Decimal("50.00"),
                description="Bulk Test Part 5",
                category="Category C",
                is_active=False  # Inactive for activation testing
            )
        ]
        
        for part in test_parts:
            self.db_manager.create_part(part)
    
    def _create_bulk_update_csv(self, filename: str, data: List[Dict[str, Any]]) -> Path:
        """Create a CSV file for bulk update testing."""
        csv_path = self.csv_dir / filename
        self.created_files.append(csv_path)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            if data:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
        
        return csv_path
    
    def test_bulk_update_price_field(self):
        """
        Test bulk update command for updating prices.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with price updates
        update_data = [
            {"part_number": "BULK001", "price": "15.50"},
            {"part_number": "BULK002", "price": "25.75"},
            {"part_number": "BULK003", "price": "35.00"}
        ]
        
        csv_path = self._create_bulk_update_csv("price_updates.csv", update_data)
        
        # Perform bulk update (simulates: parts bulk-update price_updates.csv --field price)
        update_result = self.bulk_manager.bulk_update_parts(
            str(csv_path),
            fields=['price'],
            batch_size=10
        )
        
        # Verify update was successful
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['updated_count'], 3)
        self.assertEqual(update_result['failed_count'], 0)
        
        # Verify prices were updated
        updated_part1 = self.db_manager.get_part("BULK001")
        self.assertEqual(updated_part1.authorized_price, Decimal("15.50"))
        
        updated_part2 = self.db_manager.get_part("BULK002")
        self.assertEqual(updated_part2.authorized_price, Decimal("25.75"))
        
        updated_part3 = self.db_manager.get_part("BULK003")
        self.assertEqual(updated_part3.authorized_price, Decimal("35.00"))
        
        # Verify other fields remained unchanged
        self.assertEqual(updated_part1.description, "Bulk Test Part 1")
        self.assertEqual(updated_part1.category, "Category A")
    
    def test_bulk_update_multiple_fields(self):
        """
        Test bulk update command for updating multiple fields.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with multiple field updates
        update_data = [
            {
                "part_number": "BULK001",
                "price": "12.50",
                "description": "Updated Bulk Part 1",
                "category": "Updated Category A"
            },
            {
                "part_number": "BULK002",
                "price": "22.50",
                "description": "Updated Bulk Part 2",
                "category": "Updated Category A"
            }
        ]
        
        csv_path = self._create_bulk_update_csv("multi_field_updates.csv", update_data)
        
        # Perform bulk update (simulates: parts bulk-update multi_field_updates.csv --field price --field description --field category)
        update_result = self.bulk_manager.bulk_update_parts(
            str(csv_path),
            fields=['price', 'description', 'category'],
            batch_size=10
        )
        
        # Verify update was successful
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['updated_count'], 2)
        
        # Verify all fields were updated
        updated_part1 = self.db_manager.get_part("BULK001")
        self.assertEqual(updated_part1.authorized_price, Decimal("12.50"))
        self.assertEqual(updated_part1.description, "Updated Bulk Part 1")
        self.assertEqual(updated_part1.category, "Updated Category A")
        
        updated_part2 = self.db_manager.get_part("BULK002")
        self.assertEqual(updated_part2.authorized_price, Decimal("22.50"))
        self.assertEqual(updated_part2.description, "Updated Bulk Part 2")
        self.assertEqual(updated_part2.category, "Updated Category A")
    
    def test_bulk_update_with_category_filter(self):
        """
        Test bulk update command with category filtering.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with updates for multiple categories
        update_data = [
            {"part_number": "BULK001", "price": "11.00"},  # Category A
            {"part_number": "BULK002", "price": "21.00"},  # Category A
            {"part_number": "BULK003", "price": "31.00"},  # Category B
        ]
        
        csv_path = self._create_bulk_update_csv("category_filtered_updates.csv", update_data)
        
        # Perform bulk update with category filter (simulates: parts bulk-update updates.csv --field price --filter-category "Category A")
        update_result = self.bulk_manager.bulk_update_parts(
            str(csv_path),
            fields=['price'],
            filter_category="Category A",
            batch_size=10
        )
        
        # Verify update was successful but filtered
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['updated_count'], 2)  # Only Category A parts
        self.assertEqual(update_result['skipped_count'], 1)  # Category B part skipped
        
        # Verify Category A parts were updated
        updated_part1 = self.db_manager.get_part("BULK001")
        self.assertEqual(updated_part1.authorized_price, Decimal("11.00"))
        
        updated_part2 = self.db_manager.get_part("BULK002")
        self.assertEqual(updated_part2.authorized_price, Decimal("21.00"))
        
        # Verify Category B part was not updated
        unchanged_part3 = self.db_manager.get_part("BULK003")
        self.assertEqual(unchanged_part3.authorized_price, Decimal("30.00"))  # Original price
    
    def test_bulk_update_dry_run(self):
        """
        Test bulk update command with dry-run option.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with price updates
        update_data = [
            {"part_number": "BULK001", "price": "99.99"},
            {"part_number": "BULK002", "price": "88.88"}
        ]
        
        csv_path = self._create_bulk_update_csv("dry_run_updates.csv", update_data)
        
        # Perform dry-run bulk update (simulates: parts bulk-update updates.csv --field price --dry-run)
        dry_run_result = self.bulk_manager.bulk_update_parts(
            str(csv_path),
            fields=['price'],
            dry_run=True,
            batch_size=10
        )
        
        # Verify dry-run was successful
        self.assertTrue(dry_run_result['success'])
        self.assertTrue(dry_run_result['dry_run'])
        self.assertEqual(dry_run_result['would_update_count'], 2)
        self.assertIn('preview_changes', dry_run_result)
        
        # Verify no actual changes were made
        unchanged_part1 = self.db_manager.get_part("BULK001")
        self.assertEqual(unchanged_part1.authorized_price, Decimal("10.00"))  # Original price
        
        unchanged_part2 = self.db_manager.get_part("BULK002")
        self.assertEqual(unchanged_part2.authorized_price, Decimal("20.00"))  # Original price
        
        # Verify preview changes are available
        preview_changes = dry_run_result['preview_changes']
        self.assertEqual(len(preview_changes), 2)
        
        bulk001_preview = next(change for change in preview_changes if change['part_number'] == 'BULK001')
        self.assertEqual(bulk001_preview['current_price'], Decimal("10.00"))
        self.assertEqual(bulk001_preview['new_price'], Decimal("99.99"))
    
    def test_bulk_update_with_batch_size(self):
        """
        Test bulk update command with custom batch size.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Add more parts for batch testing
        additional_parts = []
        for i in range(10):
            part = Part(
                part_number=f"BATCH{i:03d}",
                authorized_price=Decimal(f"{i * 5}.00"),
                description=f"Batch Test Part {i}",
                category="Batch"
            )
            self.db_manager.create_part(part)
            additional_parts.append(part)
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with updates for batch parts
        update_data = []
        for i in range(10):
            update_data.append({
                "part_number": f"BATCH{i:03d}",
                "price": f"{(i * 5) + 10}.00"
            })
        
        csv_path = self._create_bulk_update_csv("batch_updates.csv", update_data)
        
        # Perform bulk update with small batch size (simulates: parts bulk-update updates.csv --field price --batch-size 3)
        update_result = self.bulk_manager.bulk_update_parts(
            str(csv_path),
            fields=['price'],
            batch_size=3
        )
        
        # Verify update was successful
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['updated_count'], 10)
        self.assertIn('batches_processed', update_result)
        self.assertEqual(update_result['batches_processed'], 4)  # 10 parts / 3 batch size = 4 batches
        
        # Verify all parts were updated
        for i in range(10):
            updated_part = self.db_manager.get_part(f"BATCH{i:03d}")
            expected_price = Decimal(f"{(i * 5) + 10}.00")
            self.assertEqual(updated_part.authorized_price, expected_price)
    
    def test_bulk_delete_soft_deletion(self):
        """
        Test bulk delete command with soft deletion.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with parts to delete
        delete_data = [
            {"part_number": "BULK001"},
            {"part_number": "BULK002"},
            {"part_number": "BULK003"}
        ]
        
        csv_path = self._create_bulk_update_csv("parts_to_delete.csv", delete_data)
        
        # Perform bulk soft delete (simulates: parts bulk-delete parts_to_delete.csv)
        delete_result = self.bulk_manager.bulk_delete_parts(
            str(csv_path),
            soft_delete=True
        )
        
        # Verify deletion was successful
        self.assertTrue(delete_result['success'])
        self.assertEqual(delete_result['deleted_count'], 3)
        self.assertEqual(delete_result['failed_count'], 0)
        
        # Verify parts are soft deleted (inactive)
        deleted_part1 = self.db_manager.get_part("BULK001")
        self.assertFalse(deleted_part1.is_active)
        
        deleted_part2 = self.db_manager.get_part("BULK002")
        self.assertFalse(deleted_part2.is_active)
        
        deleted_part3 = self.db_manager.get_part("BULK003")
        self.assertFalse(deleted_part3.is_active)
        
        # Verify parts still exist in database
        all_parts = self.db_manager.list_parts()
        part_numbers = {part.part_number for part in all_parts}
        self.assertIn("BULK001", part_numbers)
        self.assertIn("BULK002", part_numbers)
        self.assertIn("BULK003", part_numbers)
        
        # Verify active parts count
        active_parts = self.db_manager.list_parts(active_only=True)
        active_part_numbers = {part.part_number for part in active_parts}
        self.assertNotIn("BULK001", active_part_numbers)
        self.assertNotIn("BULK002", active_part_numbers)
        self.assertNotIn("BULK003", active_part_numbers)
    
    def test_bulk_delete_hard_deletion(self):
        """
        Test bulk delete command with hard deletion.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with parts to delete
        delete_data = [
            {"part_number": "BULK001"},
            {"part_number": "BULK002"}
        ]
        
        csv_path = self._create_bulk_update_csv("parts_to_hard_delete.csv", delete_data)
        
        # Perform bulk hard delete (simulates: parts bulk-delete parts_to_delete.csv --hard)
        delete_result = self.bulk_manager.bulk_delete_parts(
            str(csv_path),
            soft_delete=False
        )
        
        # Verify deletion was successful
        self.assertTrue(delete_result['success'])
        self.assertEqual(delete_result['deleted_count'], 2)
        
        # Verify parts are completely removed from database
        with self.assertRaises(DatabaseError):
            self.db_manager.get_part("BULK001")
        
        with self.assertRaises(DatabaseError):
            self.db_manager.get_part("BULK002")
        
        # Verify other parts still exist
        remaining_part = self.db_manager.get_part("BULK003")
        self.assertEqual(remaining_part.part_number, "BULK003")
        
        # Verify total parts count decreased
        all_parts = self.db_manager.list_parts()
        self.assertEqual(len(all_parts), 3)  # 5 original - 2 deleted = 3
    
    def test_bulk_delete_dry_run(self):
        """
        Test bulk delete command with dry-run option.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with parts to delete
        delete_data = [
            {"part_number": "BULK001"},
            {"part_number": "BULK002"},
            {"part_number": "BULK003"}
        ]
        
        csv_path = self._create_bulk_update_csv("dry_run_delete.csv", delete_data)
        
        # Perform dry-run bulk delete (simulates: parts bulk-delete parts_to_delete.csv --dry-run)
        dry_run_result = self.bulk_manager.bulk_delete_parts(
            str(csv_path),
            dry_run=True
        )
        
        # Verify dry-run was successful
        self.assertTrue(dry_run_result['success'])
        self.assertTrue(dry_run_result['dry_run'])
        self.assertEqual(dry_run_result['would_delete_count'], 3)
        self.assertIn('preview_deletions', dry_run_result)
        
        # Verify no actual deletions were made
        part1 = self.db_manager.get_part("BULK001")
        self.assertTrue(part1.is_active)
        
        part2 = self.db_manager.get_part("BULK002")
        self.assertTrue(part2.is_active)
        
        part3 = self.db_manager.get_part("BULK003")
        self.assertTrue(part3.is_active)
        
        # Verify preview deletions are available
        preview_deletions = dry_run_result['preview_deletions']
        self.assertEqual(len(preview_deletions), 3)
        
        deletion_part_numbers = {deletion['part_number'] for deletion in preview_deletions}
        self.assertEqual(deletion_part_numbers, {"BULK001", "BULK002", "BULK003"})
    
    def test_bulk_delete_with_force_option(self):
        """
        Test bulk delete command with force option (no confirmation).
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with parts to delete
        delete_data = [
            {"part_number": "BULK001"},
            {"part_number": "BULK002"}
        ]
        
        csv_path = self._create_bulk_update_csv("force_delete.csv", delete_data)
        
        # Perform bulk delete with force (simulates: parts bulk-delete parts_to_delete.csv --force)
        delete_result = self.bulk_manager.bulk_delete_parts(
            str(csv_path),
            force=True
        )
        
        # Verify deletion was successful
        self.assertTrue(delete_result['success'])
        self.assertTrue(delete_result['forced'])
        self.assertEqual(delete_result['deleted_count'], 2)
        
        # Verify parts were deleted
        deleted_part1 = self.db_manager.get_part("BULK001")
        self.assertFalse(deleted_part1.is_active)
        
        deleted_part2 = self.db_manager.get_part("BULK002")
        self.assertFalse(deleted_part2.is_active)
    
    def test_bulk_activate_functionality(self):
        """
        Test bulk activate command functionality.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with parts to activate (BULK004 and BULK005 are inactive)
        activate_data = [
            {"part_number": "BULK004"},
            {"part_number": "BULK005"}
        ]
        
        csv_path = self._create_bulk_update_csv("parts_to_activate.csv", activate_data)
        
        # Verify parts are initially inactive
        inactive_part4 = self.db_manager.get_part("BULK004")
        self.assertFalse(inactive_part4.is_active)
        
        inactive_part5 = self.db_manager.get_part("BULK005")
        self.assertFalse(inactive_part5.is_active)
        
        # Perform bulk activate (simulates: parts bulk-activate parts_to_activate.csv)
        activate_result = self.bulk_manager.bulk_activate_parts(str(csv_path))
        
        # Verify activation was successful
        self.assertTrue(activate_result['success'])
        self.assertEqual(activate_result['activated_count'], 2)
        self.assertEqual(activate_result['failed_count'], 0)
        
        # Verify parts are now active
        activated_part4 = self.db_manager.get_part("BULK004")
        self.assertTrue(activated_part4.is_active)
        
        activated_part5 = self.db_manager.get_part("BULK005")
        self.assertTrue(activated_part5.is_active)
    
    def test_bulk_activate_with_category_filter(self):
        """
        Test bulk activate command with category filtering.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with parts to activate from different categories
        activate_data = [
            {"part_number": "BULK004"},  # Category B
            {"part_number": "BULK005"}   # Category C
        ]
        
        csv_path = self._create_bulk_update_csv("category_filtered_activate.csv", activate_data)
        
        # Perform bulk activate with category filter (simulates: parts bulk-activate parts.csv --filter-category "Category B")
        activate_result = self.bulk_manager.bulk_activate_parts(
            str(csv_path),
            filter_category="Category B"
        )
        
        # Verify activation was filtered
        self.assertTrue(activate_result['success'])
        self.assertEqual(activate_result['activated_count'], 1)  # Only Category B part
        self.assertEqual(activate_result['skipped_count'], 1)    # Category C part skipped
        
        # Verify Category B part was activated
        activated_part4 = self.db_manager.get_part("BULK004")
        self.assertTrue(activated_part4.is_active)
        
        # Verify Category C part remained inactive
        unchanged_part5 = self.db_manager.get_part("BULK005")
        self.assertFalse(unchanged_part5.is_active)
    
    def test_bulk_activate_dry_run(self):
        """
        Test bulk activate command with dry-run option.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV with parts to activate
        activate_data = [
            {"part_number": "BULK004"},
            {"part_number": "BULK005"}
        ]
        
        csv_path = self._create_bulk_update_csv("dry_run_activate.csv", activate_data)
        
        # Perform dry-run bulk activate (simulates: parts bulk-activate parts.csv --dry-run)
        dry_run_result = self.bulk_manager.bulk_activate_parts(
            str(csv_path),
            dry_run=True
        )
        
        # Verify dry-run was successful
        self.assertTrue(dry_run_result['success'])
        self.assertTrue(dry_run_result['dry_run'])
        self.assertEqual(dry_run_result['would_activate_count'], 2)
        self.assertIn('preview_activations', dry_run_result)
        
        # Verify no actual activations were made
        unchanged_part4 = self.db_manager.get_part("BULK004")
        self.assertFalse(unchanged_part4.is_active)
        
        unchanged_part5 = self.db_manager.get_part("BULK005")
        self.assertFalse(unchanged_part5.is_active)
        
        # Verify preview activations are available
        preview_activations = dry_run_result['preview_activations']
        self.assertEqual(len(preview_activations), 2)
        
        activation_part_numbers = {activation['part_number'] for activation in preview_activations}
        self.assertEqual(activation_part_numbers, {"BULK004", "BULK005"})
    
    def test_bulk_operations_error_handling(self):
        """
        Test error handling for various bulk operation scenarios.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Test with non-existent CSV file
        with self.assertRaises(DatabaseError):
            self.bulk_manager.bulk_update_parts(
                "nonexistent_file.csv",
                fields=['price']
            )
        
        # Test with invalid CSV format
        invalid_csv_path = self.csv_dir / "invalid.csv"
        self.created_files.append(invalid_csv_path)
        
        with open(invalid_csv_path, 'w', encoding='utf-8') as f:
            f.write("invalid,csv,format\nwithout,proper,headers")
        
        update_result = self.bulk_manager.bulk_update_parts(
            str(invalid_csv_path),
            fields=['price']
        )
        
        # Should fail gracefully
        self.assertFalse(update_result['success'])
        self.assertIn('error', update_result)
        
        # Test with non-existent part numbers
        nonexistent_data = [
            {"part_number": "NONEXISTENT001", "price": "10.00"},
            {"part_number": "NONEXISTENT002", "price": "20.00"}
        ]
        
        nonexistent_csv_path = self._create_bulk_update_csv("nonexistent_parts.csv", nonexistent_data)
        
        update_result = self.bulk_manager.bulk_update_parts(
            str(nonexistent_csv_path),
            fields=['price']
        )
        
        # Should handle non-existent parts gracefully
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['updated_count'], 0)
        self.assertEqual(update_result['failed_count'], 2)
        self.assertIn('errors', update_result)
    
    def test_bulk_operations_cross_platform_compatibility(self):
        """
        Test bulk operations functionality across different platforms.
        """
        # Initialize database manager and setup test parts
        self.db_manager = DatabaseManager(str(self.db_path))
        self._setup_test_parts()
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Test with special characters in CSV data
        special_data = [
            {"part_number": "SPECIAL_001", "price": "15.50", "description": "Part with émojis 🔧"},
            {"part_number": "SPECIAL_002", "price": "25.75", "description": "Part with special chars: @#$%^&*()"}
        ]
        
        # Add the special parts first
        for data in special_data:
            special_part = Part(
                part_number=data["part_number"],
                authorized_price=Decimal("10.00"),  # Original price
                description="Original Description",
                category="Special"
            )
            self.db_manager.create_part(special_part)
        
        csv_path = self._create_bulk_update_csv("special_chars_update.csv", special_data)
        
        # Perform bulk update with special characters
        update_result = self.bulk_manager.bulk_update_parts(
            str(csv_path),
            fields=['price', 'description']
        )
        
        # Verify update works with special characters
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['updated_count'], 2)
        
        # Verify special characters are preserved
        updated_part1 = self.db_manager.get_part("SPECIAL_001")
        self.assertEqual(updated_part1.description, "Part with émojis 🔧")
        
        updated_part2 = self.db_manager.get_part("SPECIAL_002")
        self.assertEqual(updated_part2.description, "Part with special chars: @#$%^&*()")
    
    def test_bulk_operations_performance_large_dataset(self):
        """
        Test bulk operations performance with large datasets.
        """
        # Initialize database manager
        self.db_manager = DatabaseManager(str(self.db_path))
        
        # Create a large number of parts for performance testing
        import time
        start_time = time.time()
        
        large_parts = []
        for i in range(100):
            part = Part(
                part_number=f"PERF{i:04d}",
                authorized_price=Decimal(f"{10 + (i % 50)}.{i % 100:02d}"),
                description=f"Performance Test Part {i}",
                category=f"Category{i % 10}"
            )
            self.db_manager.create_part(part)
            large_parts.append(part)
        
        creation_time = time.time() - start_time
        
        # Initialize bulk operations manager
        self.bulk_manager = BulkOperationsManager(self.db_manager)
        
        # Create CSV for bulk update
        update_data = []
        for i in range(100):
            update_data.append({
                "part_number": f"PERF{i:04d}",
                "price": f"{15 + (i % 50)}.{(i + 50) % 100:02d}"
            })
        
        csv_path = self._create_bulk_update_csv("performance_updates.csv", update_data)
        
        # Test bulk update performance
        update_start_time = time.time()
        update_result = self.bulk_manager.bulk_update_parts(
            str(csv_path),
            fields=['price'],
            batch_size=20
        )
        update_time = time.time() - update_start_time
        
        # Verify performance results
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['updated_count'], 100)
        self.assertLess(update_time, 10.0, "Bulk update of 100 parts should take less than 10 seconds")
        
        # Verify batching worked correctly
        self.assertEqual(update_result['batches_processed'], 5)  # 100 parts / 20 batch size = 5 batches
        
        # Test bulk delete performance
        delete_data = [{"part_number": f"PERF{i:04d}"} for i in range(50)]
        delete_csv_path = self._create_bulk_update_csv("performance_deletes.csv", delete_data)
        
        delete_start_time = time.time()
        delete_result = self.bulk_manager.bulk_delete_parts(str(delete_csv_path))
        delete_time = time.time() - delete_start_time
        
        # Verify delete performance
        self.assertTrue(delete_result['success'])
        self.assertEqual(delete_result['deleted_count'], 50)
        self.assertLess(delete_time, 5.0, "Bulk delete of 50 parts should take less than 5 seconds")


if __name__ == '__main__':
    # Configure logging for test execution
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run the tests
    unittest.main(verbosity=2)