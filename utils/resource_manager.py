"""
Resource Management Utilities

Provides context managers and utilities for proper resource cleanup
to prevent memory leaks and ensure stability.
"""

import os
import tempfile
import shutil
from contextlib import contextmanager
from typing import Optional, Generator
from pathlib import Path


@contextmanager
def temporary_directory(prefix: str = "refactor_", suffix: str = "", cleanup: bool = True) -> Generator[str, None, None]:
    """
    Context manager for temporary directories with automatic cleanup
    
    Args:
        prefix: Prefix for temporary directory name
        suffix: Suffix for temporary directory name
        cleanup: Whether to cleanup on exit
        
    Yields:
        Path to temporary directory
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix, suffix=suffix)
    try:
        yield temp_dir
    finally:
        if cleanup and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                # Log but don't raise - cleanup is best effort
                print(f"Warning: Could not cleanup temporary directory {temp_dir}: {e}")


@contextmanager
def temporary_file(mode: str = 'w', suffix: str = '', prefix: str = 'tmp', delete: bool = True) -> Generator[str, None, None]:
    """
    Context manager for temporary files with automatic cleanup
    
    Args:
        mode: File mode ('w', 'r', etc.)
        suffix: File suffix
        prefix: File prefix
        delete: Whether to delete on exit
        
    Yields:
        Path to temporary file
    """
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    try:
        os.close(fd)  # Close file descriptor, we'll use path
        yield temp_path
    finally:
        if delete and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                print(f"Warning: Could not cleanup temporary file {temp_path}: {e}")


class ResourceManager:
    """
    Manages resources with automatic cleanup
    
    Usage:
        with ResourceManager() as rm:
            file1 = rm.create_temp_file()
            dir1 = rm.create_temp_dir()
            # Resources automatically cleaned up on exit
    """
    
    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []
        self.open_files = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def create_temp_file(self, suffix: str = '', prefix: str = 'tmp') -> str:
        """Create a temporary file that will be cleaned up"""
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)
        self.temp_files.append(temp_path)
        return temp_path
    
    def create_temp_dir(self, suffix: str = '', prefix: str = 'refactor_') -> str:
        """Create a temporary directory that will be cleaned up"""
        temp_dir = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def cleanup(self):
        """Cleanup all managed resources"""
        # Close open files
        for file_obj in self.open_files:
            try:
                if not file_obj.closed:
                    file_obj.close()
            except Exception as e:
                print(f"Warning: Could not close file: {e}")
        
        # Remove temporary files
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"Warning: Could not remove temp file {temp_file}: {e}")
        
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Could not remove temp dir {temp_dir}: {e}")
        
        # Clear lists
        self.temp_files.clear()
        self.temp_dirs.clear()
        self.open_files.clear()


def safe_remove(path: str, is_dir: bool = False):
    """
    Safely remove a file or directory
    
    Args:
        path: Path to remove
        is_dir: Whether path is a directory
    """
    if not os.path.exists(path):
        return
    
    try:
        if is_dir:
            shutil.rmtree(path, ignore_errors=True)
        else:
            os.unlink(path)
    except Exception as e:
        print(f"Warning: Could not remove {path}: {e}")


def ensure_directory_exists(path: str):
    """
    Ensure a directory exists, creating it if necessary
    
    Args:
        path: Directory path
        
    Raises:
        OSError: If directory cannot be created
    """
    Path(path).mkdir(parents=True, exist_ok=True)
