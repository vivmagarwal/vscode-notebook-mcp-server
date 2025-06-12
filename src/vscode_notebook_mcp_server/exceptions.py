"""Custom exceptions for the VSCode Notebook MCP Server."""

from typing import Optional


class NotebookError(Exception):
    """Base exception for notebook-related operations."""
    
    def __init__(self, message: str, path: Optional[str] = None) -> None:
        self.message = message
        self.path = path
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.path:
            return f"{self.message} (path: {self.path})"
        return self.message


class SecurityError(Exception):
    """Exception raised for security violations."""
    
    def __init__(self, message: str, attempted_path: Optional[str] = None) -> None:
        self.message = message
        self.attempted_path = attempted_path
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.attempted_path:
            return f"Security violation: {self.message} (attempted path: {self.attempted_path})"
        return f"Security violation: {self.message}"


class KernelError(Exception):
    """Exception raised for kernel-related operations."""
    
    def __init__(self, message: str, kernel_spec: Optional[str] = None) -> None:
        self.message = message
        self.kernel_spec = kernel_spec
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.kernel_spec:
            return f"Kernel error: {self.message} (kernel: {self.kernel_spec})"
        return f"Kernel error: {self.message}"


class ValidationError(Exception):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[str] = None) -> None:
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.field and self.value:
            return f"Validation error: {self.message} (field: {self.field}, value: {self.value})"
        elif self.field:
            return f"Validation error: {self.message} (field: {self.field})"
        return f"Validation error: {self.message}"


class ExecutionError(Exception):
    """Exception raised for code execution errors."""
    
    def __init__(self, message: str, cell_index: Optional[int] = None, traceback: Optional[str] = None) -> None:
        self.message = message
        self.cell_index = cell_index
        self.traceback = traceback
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.cell_index is not None:
            return f"Execution error in cell {self.cell_index}: {self.message}"
        return f"Execution error: {self.message}"


class FileSystemError(Exception):
    """Exception raised for file system operations."""
    
    def __init__(self, message: str, path: Optional[str] = None, operation: Optional[str] = None) -> None:
        self.message = message
        self.path = path
        self.operation = operation
        super().__init__(message)
    
    def __str__(self) -> str:
        parts = [f"File system error: {self.message}"]
        if self.operation:
            parts.append(f"operation: {self.operation}")
        if self.path:
            parts.append(f"path: {self.path}")
        return " (".join(parts) + ")" if len(parts) > 1 else parts[0]
