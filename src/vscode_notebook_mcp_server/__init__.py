"""VSCode Notebook MCP Server - Production-ready MCP server for VSCode Python notebooks."""

__version__ = "1.0.0"
__author__ = "AI Assistant"
__email__ = "ai@example.com"
__description__ = "Production-ready MCP server for VSCode Python notebooks with full local compatibility"

from .exceptions import (
    NotebookError,
    SecurityError,
    KernelError,
    ValidationError,
    FileSystemError,
)
from .security import SecurityManager
from .notebook_manager import NotebookManager
from .cell_manager import CellManager
from .server import VSCodeNotebookMCPServer, main

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "NotebookError",
    "SecurityError", 
    "KernelError",
    "ValidationError",
    "FileSystemError",
    "SecurityManager",
    "NotebookManager",
    "CellManager",
    "VSCodeNotebookMCPServer",
    "main",
]
