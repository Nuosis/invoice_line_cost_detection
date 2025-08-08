"""
Version management utilities for the Invoice Rate Detection System.

This module provides dynamic version information that includes git commit hashes
and handles cases where git is not available or the repository is not initialized.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional


# Base version - this is the only place you need to update the version number
BASE_VERSION = "1.0.0"


def get_git_commit_hash(short: bool = True) -> Optional[str]:
    """
    Get the current git commit hash.
    
    Args:
        short: If True, return short hash (7 chars), otherwise full hash
        
    Returns:
        Git commit hash string or None if not available
    """
    try:
        # Get the directory where this file is located
        repo_root = Path(__file__).parent.parent
        
        # Try to get git commit hash
        cmd = ["git", "rev-parse"]
        if short:
            cmd.append("--short")
        cmd.append("HEAD")
        
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return None


def get_git_commit_count() -> int:
    """
    Get the total number of commits in the current branch.
    
    Returns:
        Number of commits or 0 if not available
    """
    try:
        repo_root = Path(__file__).parent.parent
        
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return int(result.stdout.strip())
        else:
            return 0
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, ValueError):
        return 0


def get_git_branch() -> Optional[str]:
    """
    Get the current git branch name.
    
    Returns:
        Git branch name or None if not available
    """
    try:
        repo_root = Path(__file__).parent.parent
        
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return None


def is_git_dirty() -> bool:
    """
    Check if there are uncommitted changes in the git repository.
    
    Returns:
        True if there are uncommitted changes, False otherwise
    """
    try:
        repo_root = Path(__file__).parent.parent
        
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return bool(result.stdout.strip())
        else:
            return False
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return False


def get_version(include_commit: bool = True, include_dirty: bool = True) -> str:
    """
    Get the full version string with automatic patch increment based on commit count.
    
    Args:
        include_commit: Include commit count as patch increment (recommended: True)
        include_dirty: Include dirty indicator if repository has uncommitted changes
        
    Returns:
        Version string in format: MAJOR.MINOR.PATCH[+dirty]
        Where PATCH = base patch + commit count
    """
    # Parse base version to get major, minor, patch
    version_parts = BASE_VERSION.split('.')
    if len(version_parts) != 3:
        # Fallback if base version format is unexpected
        version = BASE_VERSION
    else:
        major, minor, base_patch = version_parts
        
        if include_commit:
            commit_count = get_git_commit_count()
            # Increment patch number by commit count
            new_patch = int(base_patch) + commit_count
            version = f"{major}.{minor}.{new_patch}"
        else:
            version = BASE_VERSION
    
    if include_dirty and is_git_dirty():
        version = f"{version}+dirty"
    
    return version


def get_version_info() -> dict:
    """
    Get comprehensive version information.
    
    Returns:
        Dictionary containing version details
    """
    commit_hash = get_git_commit_hash(short=False)
    short_hash = get_git_commit_hash(short=True)
    branch = get_git_branch()
    dirty = is_git_dirty()
    commit_count = get_git_commit_count()
    
    return {
        "version": get_version(),
        "base_version": BASE_VERSION,
        "commit_hash": commit_hash,
        "short_hash": short_hash,
        "commit_count": commit_count,
        "branch": branch,
        "dirty": dirty,
        "python_version": sys.version.split()[0],
        "git_available": commit_hash is not None
    }


# For backward compatibility and easy imports
__version__ = get_version()


if __name__ == "__main__":
    # CLI for testing version utilities
    import json
    
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        print(json.dumps(get_version_info(), indent=2))
    else:
        info = get_version_info()
        print(f"Version: {info['version']}")
        print(f"Base Version: {info['base_version']}")
        if info['git_available']:
            print(f"Commit Count: {info['commit_count']}")
            print(f"Commit: {info['commit_hash']}")
            print(f"Branch: {info['branch']}")
            print(f"Dirty: {info['dirty']}")
        else:
            print("Git information not available")
        print(f"Python: {info['python_version']}")