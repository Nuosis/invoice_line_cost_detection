"""
Report utilities for handling document directory and auto-opening reports.

This module provides utilities for:
- Creating and managing the documents/ directory for reports
- Auto-opening generated reports in the default application
- Cross-platform file opening functionality
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


def get_documents_directory() -> Path:
    """
    Get the documents directory for saving reports.
    
    Creates the directory if it doesn't exist.
    
    Returns:
        Path to the documents directory
    """
    # Create documents directory in the current working directory
    documents_dir = Path.cwd() / "documents"
    documents_dir.mkdir(exist_ok=True)
    
    # Only log when this is actually being used as the final output location
    # The CLI should pass explicit output paths to avoid using this default
    logger.debug(f"Using fallback documents directory: {documents_dir}")
    return documents_dir


def get_default_report_path(base_name: str, format: str = "csv") -> Path:
    """
    Get the default path for a report file in the documents directory.
    
    Args:
        base_name: Base name for the report file
        format: File format (csv, txt, json)
        
    Returns:
        Path to the report file in documents directory
    """
    documents_dir = get_documents_directory()
    return documents_dir / f"{base_name}.{format}"


def open_file_in_default_application(file_path: Path) -> bool:
    """
    Open a file in the default application for the operating system.
    
    Args:
        file_path: Path to the file to open
        
    Returns:
        True if successful, False otherwise
    """
    if not file_path.exists():
        logger.error(f"File does not exist: {file_path}")
        return False
    
    # Check file size and readability
    try:
        file_size = file_path.stat().st_size
        logger.info(f"Attempting to open file: {file_path} (size: {file_size} bytes)")
        
        # Verify file is readable
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(100)  # Read first 100 chars to verify file is valid
            
    except Exception as e:
        logger.error(f"File validation failed for {file_path}: {e}")
        return False
    
    try:
        system = platform.system().lower()
        logger.info(f"Opening file on {system} system: {file_path}")
        
        if system == "windows":
            # Windows
            os.startfile(str(file_path))
        elif system == "darwin":
            # macOS
            result = subprocess.run(["open", str(file_path)],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.error(f"macOS open command failed: {result.stderr}")
                return False
        else:
            # Linux and other Unix-like systems
            result = subprocess.run(["xdg-open", str(file_path)],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.error(f"Linux xdg-open command failed: {result.stderr}")
                return False
        
        logger.info(f"Successfully opened file: {file_path}")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout opening file {file_path}")
        return False
    except Exception as e:
        logger.error(f"Failed to open file {file_path}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        return False


def auto_open_reports(report_files: Dict[str, Path], primary_format: str = "csv") -> None:
    """
    Auto-open generated reports, prioritizing the primary format.
    
    Args:
        report_files: Dictionary mapping format to file path
        primary_format: Primary format to open (defaults to csv)
    """
    if not report_files:
        logger.warning("No report files to open")
        return
    
    # Try to open the primary format first
    if primary_format in report_files:
        file_path = report_files[primary_format]
        if open_file_in_default_application(file_path):
            logger.info(f"Auto-opened {primary_format.upper()} report: {file_path}")
            return
    
    # Fallback to any available format
    for format_name, file_path in report_files.items():
        if open_file_in_default_application(file_path):
            logger.info(f"Auto-opened {format_name.upper()} report: {file_path}")
            return
    
    logger.warning("Failed to auto-open any report files")


def ensure_documents_directory_exists() -> Path:
    """
    Ensure the documents directory exists and return its path.
    
    Returns:
        Path to the documents directory
    """
    return get_documents_directory()


def get_report_summary_message(report_files: Dict[str, Path]) -> str:
    """
    Generate a summary message about generated reports.
    
    Args:
        report_files: Dictionary mapping format to file path
        
    Returns:
        Summary message string
    """
    if not report_files:
        return "No reports were generated."
    
    documents_dir = get_documents_directory()
    
    lines = [
        f"Reports saved to documents directory: {documents_dir}",
        ""
    ]
    
    for format_name, file_path in sorted(report_files.items()):
        lines.append(f"  {format_name.upper()}: {file_path.name}")
    
    lines.extend([
        "",
        "Reports have been automatically opened in your default application.",
        f"You can also find them in: {documents_dir}"
    ])
    
    return "\n".join(lines)


def cleanup_old_reports(days_to_keep: int = 30) -> int:
    """
    Clean up old report files from the documents directory.
    
    Args:
        days_to_keep: Number of days to keep reports (default: 30)
        
    Returns:
        Number of files cleaned up
    """
    documents_dir = get_documents_directory()
    
    if not documents_dir.exists():
        return 0
    
    import time
    current_time = time.time()
    cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)
    
    cleaned_count = 0
    
    try:
        for file_path in documents_dir.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                # Only clean up report files (csv, txt, json)
                if file_path.suffix.lower() in ['.csv', '.txt', '.json']:
                    file_path.unlink()
                    cleaned_count += 1
                    logger.info(f"Cleaned up old report: {file_path}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old report files")
        
    except Exception as e:
        logger.error(f"Error during report cleanup: {e}")
    
    return cleaned_count