"""Security management for the VSCode Notebook MCP Server."""

import os
import logging
from pathlib import Path
from typing import List, Union, Set

from .exceptions import SecurityError

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages security and access control for notebook operations."""
    
    def __init__(self, allowed_directories: List[str] = None) -> None:
        """Initialize security manager with allowed directories.
        
        Args:
            allowed_directories: List of directory paths that are allowed for operations.
                                If None, defaults to current working directory.
        """
        self.allowed_directories: Set[Path] = set()
        self._setup_allowed_directories(allowed_directories)
        
    def _setup_allowed_directories(self, directories: List[str] = None) -> None:
        """Setup allowed directories with validation."""
        if directories:
            for directory in directories:
                try:
                    abs_path = Path(directory).resolve()
                    if abs_path.exists() and abs_path.is_dir():
                        self.allowed_directories.add(abs_path)
                        logger.info(f"Added allowed directory: {abs_path}")
                    else:
                        logger.warning(f"Skipping invalid directory: {directory}")
                except (OSError, ValueError) as e:
                    logger.warning(f"Error processing directory {directory}: {e}")
        
        # If no allowed directories specified or none were valid, use current working directory
        if not self.allowed_directories:
            cwd = Path.cwd().resolve()
            self.allowed_directories.add(cwd)
            logger.info(f"Using current working directory: {cwd}")
    
    def validate_path(self, path: Union[str, Path]) -> Path:
        """Validate and resolve a path, ensuring it's within allowed directories.
        
        Args:
            path: Path to validate
            
        Returns:
            Resolved Path object
            
        Raises:
            SecurityError: If path is invalid or not within allowed directories
        """
        if not path or str(path).strip() == "":
            raise SecurityError("Empty path not allowed")
        
        path_obj = Path(path)
        
        # If path is absolute, validate it directly
        if path_obj.is_absolute():
            try:
                resolved_path = path_obj.resolve()
            except (OSError, ValueError) as e:
                raise SecurityError(f"Invalid path: {e}", str(path))
            
            # Check if absolute path is within any allowed directory
            for allowed_dir in self.allowed_directories:
                try:
                    resolved_path.relative_to(allowed_dir)
                    logger.debug(f"Absolute path {resolved_path} validated against {allowed_dir}")
                    return resolved_path
                except ValueError:
                    continue
            
            raise SecurityError(
                f"Absolute path not within allowed directories",
                str(resolved_path)
            )
        
        # For relative paths, try resolving relative to each allowed directory
        for allowed_dir in self.allowed_directories:
            try:
                # Try to resolve the path relative to this allowed directory
                candidate_path = (allowed_dir / path_obj).resolve()
                
                # Ensure the resolved path is still within the allowed directory
                # (protects against path traversal attacks like ../../../etc/passwd)
                candidate_path.relative_to(allowed_dir)
                
                logger.debug(f"Relative path {path} resolved to {candidate_path} using base {allowed_dir}")
                return candidate_path
            except (OSError, ValueError):
                # This allowed directory doesn't work, try the next one
                continue
        
        # If we get here, the path couldn't be resolved relative to any allowed directory
        raise SecurityError(
            f"Relative path could not be resolved within any allowed directories: {list(self.allowed_directories)}",
            str(path)
        )
    
    def validate_notebook_path(self, path: Union[str, Path]) -> Path:
        """Validate notebook path and ensure .ipynb extension.
        
        Args:
            path: Notebook path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            SecurityError: If path is invalid or doesn't have .ipynb extension
        """
        validated_path = self.validate_path(path)
        
        if not str(validated_path).endswith('.ipynb'):
            raise SecurityError(
                "Path must have .ipynb extension",
                str(validated_path)
            )
        
        return validated_path
    
    def validate_python_path(self, path: Union[str, Path]) -> Path:
        """Validate Python file path and ensure .py extension.
        
        Args:
            path: Python file path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            SecurityError: If path is invalid or doesn't have .py extension
        """
        validated_path = self.validate_path(path)
        
        if not str(validated_path).endswith('.py'):
            raise SecurityError(
                "Path must have .py extension",
                str(validated_path)
            )
        
        return validated_path
    
    def validate_directory(self, path: Union[str, Path]) -> Path:
        """Validate directory path.
        
        Args:
            path: Directory path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            SecurityError: If path is invalid or not a directory
        """
        validated_path = self.validate_path(path)
        
        if validated_path.exists() and not validated_path.is_dir():
            raise SecurityError(
                "Path exists but is not a directory",
                str(validated_path)
            )
        
        return validated_path
    
    def is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe (no path traversal, etc.).
        
        Args:
            filename: Filename to check
            
        Returns:
            True if filename is safe
        """
        if not filename or filename.strip() == "":
            return False
        
        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            return False
        
        # Check for hidden files (starting with .)
        if filename.startswith("."):
            return False
        
        # Check for reserved names on Windows
        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }
        if filename.upper() in reserved_names:
            return False
        
        return True
    
    def get_safe_backup_path(self, original_path: Path, timestamp: str) -> Path:
        """Generate a safe backup path for a file.
        
        Args:
            original_path: Original file path
            timestamp: Timestamp string to append
            
        Returns:
            Safe backup path
        """
        # Ensure the original path is within allowed directories
        validated_path = self.validate_path(original_path)
        
        # Create backup filename
        stem = validated_path.stem
        suffix = validated_path.suffix
        backup_name = f"{stem}.backup_{timestamp}{suffix}"
        
        # Ensure backup filename is safe
        if not self.is_safe_filename(backup_name):
            # Fallback to a simple safe name
            backup_name = f"backup_{timestamp}{suffix}"
        
        backup_path = validated_path.parent / backup_name
        return backup_path
    
    def list_allowed_directories(self) -> List[str]:
        """Get list of allowed directories as strings.
        
        Returns:
            List of allowed directory paths
        """
        return [str(path) for path in sorted(self.allowed_directories)]
    
    def can_access_path(self, path: Union[str, Path]) -> bool:
        """Check if a path can be accessed without raising an exception.
        
        Args:
            path: Path to check
            
        Returns:
            True if path can be accessed
        """
        try:
            self.validate_path(path)
            return True
        except SecurityError:
            return False
    
    def get_relative_path(self, path: Union[str, Path], base: Union[str, Path] = None) -> str:
        """Get relative path from base directory.
        
        Args:
            path: Path to make relative
            base: Base directory (if None, uses first allowed directory)
            
        Returns:
            Relative path string
        """
        validated_path = self.validate_path(path)
        
        if base is None:
            base = next(iter(self.allowed_directories))
        else:
            base = self.validate_path(base)
        
        try:
            relative = validated_path.relative_to(base)
            return str(relative)
        except ValueError:
            # If can't make relative, return absolute path
            return str(validated_path)
