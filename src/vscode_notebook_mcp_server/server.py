"""Main server implementation for the VSCode Notebook MCP Server."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import Tool

from .exceptions import NotebookError, SecurityError, ValidationError, FileSystemError, ExecutionError
from .security import SecurityManager
from .notebook_manager import NotebookManager
from .cell_manager import CellManager
from .execution_manager import ExecutionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VSCodeNotebookMCPServer:
    """Main MCP server for VSCode notebook operations."""
    
    def __init__(self, allowed_directories: Optional[List[str]] = None, debug: bool = False):
        """Initialize the server.
        
        Args:
            allowed_directories: List of directories allowed for operations
            debug: Enable debug logging
        """
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            
        # Initialize components
        self.security_manager = SecurityManager(allowed_directories)
        self.notebook_manager = NotebookManager(self.security_manager)
        self.cell_manager = CellManager(self.notebook_manager)
        self.execution_manager = ExecutionManager(self.notebook_manager)
        
        # Initialize MCP server
        @asynccontextmanager
        async def lifespan(server: FastMCP):
            logger.info("VSCode Notebook MCP Server starting")
            logger.info(f"Allowed directories: {self.security_manager.list_allowed_directories()}")
            yield
            logger.info("VSCode Notebook MCP Server shutting down")
            # Cleanup running kernels
            self.execution_manager.cleanup()
        
        self.mcp = FastMCP(
            "vscode-notebook-mcp-server",
            description="Production-ready MCP server for VSCode notebook operations with comprehensive security and error handling",
            lifespan=lifespan
        )
        
        # Register all tools
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all MCP tools."""
        
        # Notebook operations
        @self.mcp.tool()
        def list_notebooks(directory: str = ".") -> Dict[str, Any]:
            """List all notebook files in a directory.
            
            Args:
                directory: Directory to search for notebooks (default: current directory)
                
            Returns:
                Dictionary with success status and list of notebooks
            """
            try:
                notebooks = self.notebook_manager.list_notebooks(directory)
                return {
                    "success": True,
                    "directory": directory,
                    "count": len(notebooks),
                    "notebooks": notebooks
                }
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def get_notebook_info(notebook_path: str) -> Dict[str, Any]:
            """Get comprehensive information about a notebook.
            
            Args:
                notebook_path: Path to the notebook file
                
            Returns:
                Dictionary with notebook information and metadata
            """
            try:
                info = self.notebook_manager.get_notebook_info(notebook_path)
                return {
                    "success": True,
                    **info
                }
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def create_notebook(notebook_path: str, title: str = "New Notebook", 
                          language: str = "python") -> Dict[str, Any]:
            """Create a new notebook file.
            
            Args:
                notebook_path: Path for the new notebook (must end with .ipynb)
                title: Title for the notebook
                language: Programming language for the notebook
                
            Returns:
                Dictionary with creation status and details
            """
            try:
                notebook = self.notebook_manager.create_new_notebook(notebook_path, title, language)
                return {
                    "success": True,
                    "notebook_path": notebook_path,
                    "title": title,
                    "language": language,
                    "cells_count": len(notebook.cells),
                    "message": f"Created new {language} notebook: {title}"
                }
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def export_to_python(notebook_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
            """Export a notebook to a Python script.
            
            Args:
                notebook_path: Path to the notebook file
                output_path: Path for the output Python file (optional)
                
            Returns:
                Dictionary with export status and output path
            """
            try:
                python_path = self.notebook_manager.export_to_python(notebook_path, output_path)
                return {
                    "success": True,
                    "notebook_path": notebook_path,
                    "python_path": python_path,
                    "message": f"Exported notebook to Python script"
                }
            except Exception as e:
                return self._handle_error(e)
        
        # Cell operations
        @self.mcp.tool()
        def add_cell(notebook_path: str, cell_type: str, content: str, 
                    index: Optional[int] = None) -> Dict[str, Any]:
            """Add a new cell to a notebook.
            
            Args:
                notebook_path: Path to the notebook file
                cell_type: Type of cell ("code", "markdown", or "raw")
                content: Content for the new cell
                index: Position to insert cell (optional, defaults to end)
                
            Returns:
                Dictionary with operation status and details
            """
            try:
                result = self.cell_manager.add_cell(notebook_path, cell_type, content, index)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def modify_cell(notebook_path: str, index: int, content: str) -> Dict[str, Any]:
            """Modify the content of an existing cell.
            
            Args:
                notebook_path: Path to the notebook file
                index: Index of the cell to modify
                content: New content for the cell
                
            Returns:
                Dictionary with operation status and details
            """
            try:
                result = self.cell_manager.modify_cell(notebook_path, index, content)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def delete_cell(notebook_path: str, index: int) -> Dict[str, Any]:
            """Delete a cell from a notebook.
            
            Args:
                notebook_path: Path to the notebook file
                index: Index of the cell to delete
                
            Returns:
                Dictionary with operation status and details
            """
            try:
                result = self.cell_manager.delete_cell(notebook_path, index)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def get_cell(notebook_path: str, index: int) -> Dict[str, Any]:
            """Get information about a specific cell.
            
            Args:
                notebook_path: Path to the notebook file
                index: Index of the cell to retrieve
                
            Returns:
                Dictionary with cell information and content
            """
            try:
                result = self.cell_manager.get_cell(notebook_path, index)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def get_all_cells(notebook_path: str) -> Dict[str, Any]:
            """Get information about all cells in a notebook.
            
            Args:
                notebook_path: Path to the notebook file
                
            Returns:
                Dictionary with all cells information
            """
            try:
                result = self.cell_manager.get_all_cells(notebook_path)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def move_cell(notebook_path: str, from_index: int, to_index: int) -> Dict[str, Any]:
            """Move a cell from one position to another.
            
            Args:
                notebook_path: Path to the notebook file
                from_index: Current index of the cell
                to_index: Target index for the cell
                
            Returns:
                Dictionary with operation status and details
            """
            try:
                result = self.cell_manager.move_cell(notebook_path, from_index, to_index)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def duplicate_cell(notebook_path: str, index: int, 
                          target_index: Optional[int] = None) -> Dict[str, Any]:
            """Duplicate a cell at a specified position.
            
            Args:
                notebook_path: Path to the notebook file
                index: Index of the cell to duplicate
                target_index: Position for the duplicated cell (optional)
                
            Returns:
                Dictionary with operation status and details
            """
            try:
                result = self.cell_manager.duplicate_cell(notebook_path, index, target_index)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def search_cells(notebook_path: str, search_term: str, 
                        case_sensitive: bool = False,
                        cell_types: Optional[List[str]] = None) -> Dict[str, Any]:
            """Search for text across cells in a notebook.
            
            Args:
                notebook_path: Path to the notebook file
                search_term: Text to search for
                case_sensitive: Whether search should be case sensitive
                cell_types: List of cell types to search (optional)
                
            Returns:
                Dictionary with search results
            """
            try:
                result = self.cell_manager.search_cells(
                    notebook_path, search_term, case_sensitive, cell_types
                )
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def replace_in_cells(notebook_path: str, search_term: str, replace_term: str,
                           case_sensitive: bool = False,
                           cell_types: Optional[List[str]] = None,
                           max_replacements: Optional[int] = None) -> Dict[str, Any]:
            """Replace text across cells in a notebook.
            
            Args:
                notebook_path: Path to the notebook file
                search_term: Text to search for
                replace_term: Text to replace with
                case_sensitive: Whether search should be case sensitive
                cell_types: List of cell types to search (optional)
                max_replacements: Maximum number of replacements (optional)
                
            Returns:
                Dictionary with replacement results
            """
            try:
                result = self.cell_manager.replace_in_cells(
                    notebook_path, search_term, replace_term, 
                    case_sensitive, cell_types, max_replacements
                )
                return result
            except Exception as e:
                return self._handle_error(e)
        
        # Execution operations
        @self.mcp.tool()
        def execute_cell(notebook_path: str, cell_index: int, 
                        timeout: Optional[int] = None) -> Dict[str, Any]:
            """Execute a specific cell in a notebook.
            
            Args:
                notebook_path: Path to the notebook file
                cell_index: Index of the cell to execute
                timeout: Execution timeout in seconds (optional)
                
            Returns:
                Dictionary with execution results and outputs
            """
            try:
                result = self.execution_manager.execute_cell(notebook_path, cell_index, timeout)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def execute_all_cells(notebook_path: str, timeout: Optional[int] = None,
                             stop_on_error: bool = False) -> Dict[str, Any]:
            """Execute all cells in a notebook sequentially.
            
            Args:
                notebook_path: Path to the notebook file
                timeout: Execution timeout per cell in seconds (optional)
                stop_on_error: Whether to stop execution on first error (optional)
                
            Returns:
                Dictionary with execution results for all cells
            """
            try:
                result = self.execution_manager.execute_all_cells(notebook_path, timeout, stop_on_error)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def execute_cells_range(notebook_path: str, start_index: int, end_index: int,
                               timeout: Optional[int] = None,
                               stop_on_error: bool = False) -> Dict[str, Any]:
            """Execute a range of cells in a notebook.
            
            Args:
                notebook_path: Path to the notebook file
                start_index: Starting cell index (inclusive)
                end_index: Ending cell index (inclusive)
                timeout: Execution timeout per cell in seconds (optional)
                stop_on_error: Whether to stop execution on first error (optional)
                
            Returns:
                Dictionary with execution results for the specified range
            """
            try:
                result = self.execution_manager.execute_cells_range(
                    notebook_path, start_index, end_index, timeout, stop_on_error
                )
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def execute_code_snippet(notebook_path: str, code: str,
                                timeout: Optional[int] = None) -> Dict[str, Any]:
            """Execute arbitrary code without modifying the notebook.
            
            Args:
                notebook_path: Path to notebook (to determine kernel context)
                code: Code to execute
                timeout: Execution timeout in seconds (optional)
                
            Returns:
                Dictionary with execution results
            """
            try:
                result = self.execution_manager.execute_code_snippet(notebook_path, code, timeout)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def restart_kernel(notebook_path: str) -> Dict[str, Any]:
            """Restart the kernel for a notebook.
            
            Args:
                notebook_path: Path to the notebook file
                
            Returns:
                Dictionary with operation status
            """
            try:
                result = self.execution_manager.restart_kernel(notebook_path)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def get_kernel_status(notebook_path: str) -> Dict[str, Any]:
            """Get the status of a notebook's kernel.
            
            Args:
                notebook_path: Path to the notebook file
                
            Returns:
                Dictionary with kernel status information
            """
            try:
                result = self.execution_manager.get_kernel_status(notebook_path)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def interrupt_kernel(notebook_path: str) -> Dict[str, Any]:
            """Interrupt a running kernel.
            
            Args:
                notebook_path: Path to the notebook file
                
            Returns:
                Dictionary with operation status
            """
            try:
                result = self.execution_manager.interrupt_kernel(notebook_path)
                return result
            except Exception as e:
                return self._handle_error(e)
        
        # Utility functions
        @self.mcp.tool()
        def list_allowed_directories() -> Dict[str, Any]:
            """List directories that are allowed for notebook operations.
            
            Returns:
                Dictionary with list of allowed directories
            """
            try:
                directories = self.security_manager.list_allowed_directories()
                return {
                    "success": True,
                    "allowed_directories": directories,
                    "count": len(directories)
                }
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def validate_notebook_path(path: str) -> Dict[str, Any]:
            """Validate a notebook path for security and format.
            
            Args:
                path: Path to validate
                
            Returns:
                Dictionary with validation results
            """
            try:
                validated_path = self.security_manager.validate_notebook_path(path)
                return {
                    "success": True,
                    "original_path": path,
                    "validated_path": str(validated_path),
                    "exists": validated_path.exists(),
                    "is_notebook": str(validated_path).endswith('.ipynb'),
                    "message": "Path is valid and accessible"
                }
            except Exception as e:
                return self._handle_error(e)
        
        @self.mcp.tool()
        def get_server_info() -> Dict[str, Any]:
            """Get information about the MCP server.
            
            Returns:
                Dictionary with server information
            """
            return {
                "success": True,
                "server_name": "VSCode Notebook MCP Server",
                "version": "1.0.0",
                "description": "Production-ready MCP server for VSCode notebook operations",
                "allowed_directories": self.security_manager.list_allowed_directories(),
                "features": [
                    "Notebook management (create, read, list, export)",
                    "Cell operations (add, modify, delete, move, duplicate)",
                    "Search and replace across cells",
                    "Cell execution (execute individual cells, all cells, ranges)",
                    "Code snippet execution (without modifying notebook)",
                    "Kernel management (start, restart, interrupt, status)",
                    "Live output capture (text, errors, display data)",
                    "Security-first design with path validation",
                    "Automatic backup creation",
                    "Comprehensive error handling"
                ]
            }
    
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle errors and return appropriate response.
        
        Args:
            error: Exception that occurred
            
        Returns:
            Error response dictionary
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Log the error
        logger.error(f"{error_type}: {error_message}")
        
        # Create appropriate response based on error type
        if isinstance(error, SecurityError):
            return {
                "success": False,
                "error_type": "SecurityError",
                "error": "Access denied or invalid path",
                "details": error_message
            }
        elif isinstance(error, ValidationError):
            return {
                "success": False,
                "error_type": "ValidationError", 
                "error": "Invalid input or parameters",
                "details": error_message
            }
        elif isinstance(error, NotebookError):
            return {
                "success": False,
                "error_type": "NotebookError",
                "error": "Notebook operation failed",
                "details": error_message
            }
        elif isinstance(error, FileSystemError):
            return {
                "success": False,
                "error_type": "FileSystemError",
                "error": "File system operation failed",
                "details": error_message
            }
        elif isinstance(error, ExecutionError):
            return {
                "success": False,
                "error_type": "ExecutionError",
                "error": "Code execution failed",
                "details": error_message
            }
        else:
            # Generic error handling
            return {
                "success": False,
                "error_type": error_type,
                "error": "An unexpected error occurred",
                "details": error_message
            }
    
    def run(self) -> None:
        """Start the MCP server."""
        try:
            logger.info("Starting VSCode Notebook MCP Server...")
            self.mcp.run()
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise


def main():
    """Main entry point for the server."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="VSCode Notebook MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use current directory
  %(prog)s --allowed-dirs /path/to/notebooks  # Single allowed directory
  %(prog)s --allowed-dirs /path/1 /path/2     # Multiple allowed directories
  %(prog)s --debug                            # Enable debug logging
        """
    )
    
    parser.add_argument(
        "--allowed-dirs", 
        nargs="*", 
        help="Allowed directories for notebook operations (default: current directory)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Create and run server
    try:
        server = VSCodeNotebookMCPServer(
            allowed_directories=args.allowed_dirs,
            debug=args.debug
        )
        server.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        exit(1)


if __name__ == "__main__":
    main()
