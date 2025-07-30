"""
Test cleanup utilities for managing test artifacts.

This module provides utilities to clean up files created during testing,
particularly database backup files that may be left behind.
"""

import glob
import logging
from pathlib import Path
from typing import List

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