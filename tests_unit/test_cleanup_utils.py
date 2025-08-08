"""
Test cleanup utilities for managing test artifacts.

This module provides utilities to clean up files created during testing,
particularly database backup files that may be left behind.
"""

import glob
import logging
import tempfile
import unittest
from pathlib import Path
from typing import List
from unittest.mock import patch, MagicMock

logger = logging.getLogger(__name__)


def cleanup_test_backup_files(base_dir: str = ".") -> List[str]:
    """
    Clean up test backup files from the specified directory.
    
    Args:
        base_dir: Directory to clean up (default: current directory)
        
    Returns:
        List[str]: List of files that were deleted
    """
    base_path = Path(base_dir)
    deleted_files = []
    
    # Patterns for test backup files
    patterns = [
        "test_*_backup_*.db",
        "test_*_pre_restore_*.db",
        "*test*_backup_*.db",
        "*test*_pre_restore_*.db",
        "test_backup_*.db"
    ]
    
    for pattern in patterns:
        for file_path in base_path.glob(pattern):
            try:
                file_path.unlink()
                deleted_files.append(str(file_path))
                logger.debug(f"Deleted test backup file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete test backup file {file_path}: {e}")
    
    if deleted_files:
        logger.info(f"Cleaned up {len(deleted_files)} test backup files")
    
    return deleted_files


def cleanup_all_backup_files(base_dir: str = ".") -> List[str]:
    """
    Clean up ALL backup files from the specified directory.
    
    WARNING: This will delete all backup files, not just test files.
    Use with caution!
    
    Args:
        base_dir: Directory to clean up (default: current directory)
        
    Returns:
        List[str]: List of files that were deleted
    """
    base_path = Path(base_dir)
    deleted_files = []
    
    # Patterns for all backup files
    patterns = [
        "*_backup_*.db",
        "*_pre_restore_*.db"
    ]
    
    for pattern in patterns:
        for file_path in base_path.glob(pattern):
            try:
                file_path.unlink()
                deleted_files.append(str(file_path))
                logger.debug(f"Deleted backup file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete backup file {file_path}: {e}")
    
    if deleted_files:
        logger.info(f"Cleaned up {len(deleted_files)} backup files")
    
    return deleted_files


class TestCleanupTestBackupFiles(unittest.TestCase):
    """Test cases for cleanup_test_backup_files function."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        # Clean up any remaining files
        for file_path in self.temp_path.glob("*"):
            if file_path.is_file():
                file_path.unlink()
        self.temp_path.rmdir()
    
    def test_cleanup_test_backup_files_no_files(self):
        """Test cleanup when no backup files exist."""
        result = cleanup_test_backup_files(self.temp_dir)
        self.assertEqual(result, [])
    
    def test_cleanup_test_backup_files_with_test_files(self):
        """Test cleanup with various test backup file patterns."""
        # Create test backup files
        test_files = [
            "test_db_backup_20240101.db",
            "test_main_pre_restore_20240101.db",
            "mytest_backup_20240101.db",
            "data_test_backup_20240101.db",
            "test_backup_20240101.db"
        ]
        
        created_files = []
        for filename in test_files:
            file_path = self.temp_path / filename
            file_path.touch()
            created_files.append(str(file_path))
        
        # Run cleanup
        result = cleanup_test_backup_files(self.temp_dir)
        
        # Verify all test files were deleted
        self.assertEqual(len(result), len(test_files))
        for file_path in created_files:
            self.assertIn(file_path, result)
            self.assertFalse(Path(file_path).exists())
    
    def test_cleanup_test_backup_files_ignores_non_test_files(self):
        """Test that cleanup ignores non-test backup files."""
        # Create mix of test and non-test files
        test_files = ["test_backup_20240101.db"]
        non_test_files = [
            "prod_backup_20240101.db",
            "main_backup_20240101.db",
            "regular_file.txt",
            "backup_file.db"
        ]
        
        # Create all files
        for filename in test_files + non_test_files:
            (self.temp_path / filename).touch()
        
        # Run cleanup
        result = cleanup_test_backup_files(self.temp_dir)
        
        # Verify only test files were deleted
        self.assertEqual(len(result), len(test_files))
        
        # Non-test files should still exist
        for filename in non_test_files:
            self.assertTrue((self.temp_path / filename).exists())
    
    @patch('tests_unit.test_cleanup_utils.logger')
    def test_cleanup_test_backup_files_with_permission_error(self, mock_logger):
        """Test cleanup handles permission errors gracefully."""
        # Create a test file
        test_file = self.temp_path / "test_backup_20240101.db"
        test_file.touch()
        
        # Mock unlink to raise PermissionError
        with patch.object(Path, 'unlink', side_effect=PermissionError("Permission denied")):
            result = cleanup_test_backup_files(self.temp_dir)
        
        # Should return empty list and log warning
        self.assertEqual(result, [])
        # The file matches multiple patterns, so warning may be called multiple times
        self.assertTrue(mock_logger.warning.called)
        self.assertGreater(mock_logger.warning.call_count, 0)
    
    @patch('tests_unit.test_cleanup_utils.logger')
    def test_cleanup_test_backup_files_logs_info_when_files_deleted(self, mock_logger):
        """Test that info is logged when files are deleted."""
        # Create test file
        test_file = self.temp_path / "test_backup_20240101.db"
        test_file.touch()
        
        # Run cleanup
        result = cleanup_test_backup_files(self.temp_dir)
        
        # Verify logging
        self.assertEqual(len(result), 1)
        mock_logger.info.assert_called_once_with("Cleaned up 1 test backup files")
    
    def test_cleanup_test_backup_files_default_directory(self):
        """Test cleanup with default directory parameter."""
        # This test runs in current directory, so we just verify it doesn't crash
        result = cleanup_test_backup_files()
        self.assertIsInstance(result, list)


class TestCleanupAllBackupFiles(unittest.TestCase):
    """Test cases for cleanup_all_backup_files function."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        # Clean up any remaining files
        for file_path in self.temp_path.glob("*"):
            if file_path.is_file():
                file_path.unlink()
        self.temp_path.rmdir()
    
    def test_cleanup_all_backup_files_no_files(self):
        """Test cleanup when no backup files exist."""
        result = cleanup_all_backup_files(self.temp_dir)
        self.assertEqual(result, [])
    
    def test_cleanup_all_backup_files_with_various_patterns(self):
        """Test cleanup with various backup file patterns."""
        # Create backup files with different patterns
        backup_files = [
            "test_backup_20240101.db",
            "prod_backup_20240101.db",
            "main_backup_20240101.db",
            "data_pre_restore_20240101.db",
            "system_pre_restore_20240101.db"
        ]
        
        created_files = []
        for filename in backup_files:
            file_path = self.temp_path / filename
            file_path.touch()
            created_files.append(str(file_path))
        
        # Run cleanup
        result = cleanup_all_backup_files(self.temp_dir)
        
        # Verify all backup files were deleted
        self.assertEqual(len(result), len(backup_files))
        for file_path in created_files:
            self.assertIn(file_path, result)
            self.assertFalse(Path(file_path).exists())
    
    def test_cleanup_all_backup_files_ignores_non_backup_files(self):
        """Test that cleanup ignores non-backup files."""
        # Create mix of backup and non-backup files
        backup_files = ["main_backup_20240101.db"]
        non_backup_files = [
            "regular_file.txt",
            "database.db",
            "config.json",
            "backup_file.txt"  # Wrong extension
        ]
        
        # Create all files
        for filename in backup_files + non_backup_files:
            (self.temp_path / filename).touch()
        
        # Run cleanup
        result = cleanup_all_backup_files(self.temp_dir)
        
        # Verify only backup files were deleted
        self.assertEqual(len(result), len(backup_files))
        
        # Non-backup files should still exist
        for filename in non_backup_files:
            self.assertTrue((self.temp_path / filename).exists())
    
    @patch('tests_unit.test_cleanup_utils.logger')
    def test_cleanup_all_backup_files_with_error(self, mock_logger):
        """Test cleanup handles errors gracefully."""
        # Create a backup file
        backup_file = self.temp_path / "main_backup_20240101.db"
        backup_file.touch()
        
        # Mock unlink to raise OSError
        with patch.object(Path, 'unlink', side_effect=OSError("File in use")):
            result = cleanup_all_backup_files(self.temp_dir)
        
        # Should return empty list and log warning
        self.assertEqual(result, [])
        mock_logger.warning.assert_called_once()
    
    @patch('tests_unit.test_cleanup_utils.logger')
    def test_cleanup_all_backup_files_logs_info_when_files_deleted(self, mock_logger):
        """Test that info is logged when files are deleted."""
        # Create backup file
        backup_file = self.temp_path / "main_backup_20240101.db"
        backup_file.touch()
        
        # Run cleanup
        result = cleanup_all_backup_files(self.temp_dir)
        
        # Verify logging
        self.assertEqual(len(result), 1)
        mock_logger.info.assert_called_once_with("Cleaned up 1 backup files")
    
    def test_cleanup_all_backup_files_default_directory(self):
        """Test cleanup with default directory parameter."""
        # This test runs in current directory, so we just verify it doesn't crash
        result = cleanup_all_backup_files()
        self.assertIsInstance(result, list)


class TestCleanupUtilsIntegration(unittest.TestCase):
    """Integration tests for cleanup utilities."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        # Clean up any remaining files
        for file_path in self.temp_path.glob("*"):
            if file_path.is_file():
                file_path.unlink()
        self.temp_path.rmdir()
    
    def test_test_cleanup_vs_all_cleanup_behavior(self):
        """Test difference between test-specific and all backup cleanup."""
        # Create mix of test and non-test backup files
        test_backup_files = [
            "test_backup_20240101.db",
            "mytest_backup_20240101.db"
        ]
        non_test_backup_files = [
            "prod_backup_20240101.db",
            "main_backup_20240101.db"
        ]
        
        # Create all files
        all_files = test_backup_files + non_test_backup_files
        for filename in all_files:
            (self.temp_path / filename).touch()
        
        # Run test cleanup first
        test_result = cleanup_test_backup_files(self.temp_dir)
        
        # Verify only test files were deleted
        self.assertEqual(len(test_result), len(test_backup_files))
        
        # Non-test backup files should still exist
        for filename in non_test_backup_files:
            self.assertTrue((self.temp_path / filename).exists())
        
        # Now run all cleanup
        all_result = cleanup_all_backup_files(self.temp_dir)
        
        # Verify remaining backup files were deleted
        self.assertEqual(len(all_result), len(non_test_backup_files))
        
        # All backup files should now be gone
        for filename in non_test_backup_files:
            self.assertFalse((self.temp_path / filename).exists())


if __name__ == '__main__':
    unittest.main()