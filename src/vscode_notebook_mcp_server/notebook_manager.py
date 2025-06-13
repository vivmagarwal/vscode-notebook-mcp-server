"""Notebook management for the VSCode Notebook MCP Server."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple

import nbformat
from nbformat import v4 as nbf
from nbformat.validator import ValidationError

from .exceptions import NotebookError, FileSystemError, ValidationError as CustomValidationError
from .security import SecurityManager

logger = logging.getLogger(__name__)


class NotebookManager:
    """Manages notebook file operations with proper error handling and security."""
    
    def __init__(self, security_manager: SecurityManager) -> None:
        """Initialize notebook manager.
        
        Args:
            security_manager: Security manager instance for path validation
        """
        self.security = security_manager
    
    def load_notebook(self, path: Union[str, Path]) -> nbformat.NotebookNode:
        """Load a notebook with proper validation.
        
        Args:
            path: Path to notebook file
            
        Returns:
            Loaded notebook
            
        Raises:
            NotebookError: If notebook cannot be loaded
            FileSystemError: If file system operation fails
        """
        validated_path = self.security.validate_notebook_path(path)
        
        if not validated_path.exists():
            raise FileSystemError(
                f"Notebook file not found",
                str(validated_path),
                "load"
            )
        
        try:
            with open(validated_path, 'r', encoding='utf-8') as f:
                notebook = nbformat.read(f, as_version=4)
            
            # Validate notebook structure
            try:
                nbformat.validate(notebook)
                logger.debug(f"Notebook validation successful: {validated_path}")
            except ValidationError as e:
                logger.warning(f"Notebook validation warning for {validated_path}: {e}")
                # Continue anyway, but log the warning
            
            # Ensure notebook has required metadata
            self._ensure_notebook_metadata(notebook)
            
            return notebook
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise NotebookError(f"Failed to parse notebook file: {e}", str(validated_path))
        except Exception as e:
            raise NotebookError(f"Unexpected error loading notebook: {e}", str(validated_path))
    
    def save_notebook(self, notebook: nbformat.NotebookNode, path: Union[str, Path], 
                     create_backup: bool = False) -> None:
        """Save a notebook with optional backup.
        
        Args:
            notebook: Notebook to save
            path: Path to save notebook
            create_backup: Whether to create backup if file exists
            
        Raises:
            NotebookError: If notebook cannot be saved
            FileSystemError: If file system operation fails
        """
        validated_path = self.security.validate_notebook_path(path)
        
        # Create backup if requested and file exists
        if create_backup and validated_path.exists():
            self._create_backup(validated_path)
        
        # Ensure parent directory exists
        try:
            validated_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise FileSystemError(
                f"Failed to create parent directory: {e}",
                str(validated_path.parent),
                "mkdir"
            )
        
        # Validate notebook before saving (with lenient validation for newer notebook formats)
        try:
            nbformat.validate(notebook)
        except ValidationError as e:
            # Allow validation to pass if the only issue is unexpected 'id' fields in cells
            error_str = str(e)
            if "'id' was unexpected" in error_str:
                logger.debug(f"Ignoring validation warning about 'id' fields: {e}")
            else:
                raise CustomValidationError(f"Notebook validation failed: {e}")
        
        # Save notebook
        try:
            with open(validated_path, 'w', encoding='utf-8') as f:
                nbformat.write(notebook, f)
            
            logger.info(f"Saved notebook: {validated_path}")
            
        except Exception as e:
            raise FileSystemError(
                f"Failed to save notebook: {e}",
                str(validated_path),
                "save"
            )
    
    def create_new_notebook(self, path: Union[str, Path], title: str = "New Notebook", 
                           language: str = "python") -> nbformat.NotebookNode:
        """Create a new notebook with proper metadata.
        
        Args:
            path: Path for new notebook
            title: Title for the notebook
            language: Programming language for the notebook
            
        Returns:
            Created notebook
            
        Raises:
            NotebookError: If notebook cannot be created
            FileSystemError: If file already exists
        """
        validated_path = self.security.validate_notebook_path(path)
        
        if validated_path.exists():
            raise FileSystemError(
                f"Notebook already exists",
                str(validated_path),
                "create"
            )
        
        # Create new notebook with proper metadata
        notebook = nbf.new_notebook()
        
        # Set up kernel metadata based on language
        kernel_metadata = self._get_kernel_metadata(language)
        notebook.metadata.update(kernel_metadata)
        
        # Add custom metadata
        notebook.metadata.update({
            "title": title,
            "created": datetime.now().isoformat(),
            "vscode_notebook_mcp": {
                "version": "1.0.0",
                "created_by": "VSCode Notebook MCP Server"
            }
        })
        
        # Add initial cells
        notebook.cells.append(nbf.new_markdown_cell(f"# {title}\n\nNotebook created with VSCode Notebook MCP Server."))
        
        if language == "python":
            notebook.cells.append(nbf.new_code_cell("# Your Python code here\nprint('Hello, VSCode Notebook!')"))
        else:
            notebook.cells.append(nbf.new_code_cell("# Your code here"))
        
        # Save the new notebook
        self.save_notebook(notebook, validated_path, create_backup=False)
        
        return notebook
    
    def get_notebook_info(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Get comprehensive information about a notebook.
        
        Args:
            path: Path to notebook
            
        Returns:
            Dictionary with notebook information
        """
        validated_path = self.security.validate_notebook_path(path)
        
        if not validated_path.exists():
            raise FileSystemError(
                f"Notebook file not found",
                str(validated_path),
                "info"
            )
        
        try:
            # Get file stats
            stat = validated_path.stat()
            
            # Load notebook for analysis
            notebook = self.load_notebook(validated_path)
            
            # Analyze cells
            cell_stats = self._analyze_cells(notebook.cells)
            
            # Get notebook metadata
            metadata = dict(notebook.metadata)
            
            return {
                "path": str(validated_path),
                "name": validated_path.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "metadata": metadata,
                "cell_count": len(notebook.cells),
                "cell_stats": cell_stats,
                "nbformat_version": f"{notebook.nbformat}.{notebook.nbformat_minor}",
                "language": metadata.get("language_info", {}).get("name", "unknown"),
                "kernel": metadata.get("kernelspec", {}).get("name", "unknown")
            }
            
        except Exception as e:
            if isinstance(e, (NotebookError, FileSystemError)):
                raise
            raise NotebookError(f"Failed to get notebook info: {e}", str(validated_path))
    
    def list_notebooks(self, directory: Union[str, Path] = ".") -> List[Dict[str, Any]]:
        """List all notebooks in a directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of notebook information dictionaries
        """
        validated_dir = self.security.validate_directory(directory)
        
        if not validated_dir.exists():
            raise FileSystemError(
                f"Directory not found",
                str(validated_dir),
                "list"
            )
        
        notebooks = []
        try:
            for notebook_path in validated_dir.glob("**/*.ipynb"):
                try:
                    # Quick file stats without loading full notebook
                    if self.security.can_access_path(notebook_path):
                        stat = notebook_path.stat()
                        notebooks.append({
                            "path": str(notebook_path),
                            "name": notebook_path.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "relative_path": self.security.get_relative_path(notebook_path, validated_dir)
                        })
                except Exception as e:
                    logger.warning(f"Error reading {notebook_path}: {e}")
                    continue
                    
        except Exception as e:
            raise FileSystemError(
                f"Failed to list notebooks: {e}",
                str(validated_dir),
                "list"
            )
        
        return sorted(notebooks, key=lambda x: x["name"])
    
    def export_to_python(self, notebook_path: Union[str, Path], 
                        output_path: Optional[Union[str, Path]] = None) -> str:
        """Export notebook to Python script.
        
        Args:
            notebook_path: Path to notebook
            output_path: Path for output Python file (optional)
            
        Returns:
            Path to exported Python file
        """
        notebook = self.load_notebook(notebook_path)
        validated_notebook_path = self.security.validate_notebook_path(notebook_path)
        
        if output_path is None:
            output_path = validated_notebook_path.with_suffix('.py')
        else:
            output_path = self.security.validate_python_path(output_path)
        
        python_lines = []
        
        # Add header
        python_lines.extend([
            f"# Generated from {validated_notebook_path.name}",
            f"# Generated at {datetime.now().isoformat()}",
            f"# VSCode Notebook MCP Server",
            ""
        ])
        
        # Process cells
        for i, cell in enumerate(notebook.cells):
            if cell.cell_type == "code":
                python_lines.extend([
                    f"# %% Cell {i + 1} - Code",
                    cell.source,
                    ""
                ])
            elif cell.cell_type == "markdown":
                python_lines.append(f"# %% Cell {i + 1} - Markdown")
                for line in cell.source.split('\n'):
                    python_lines.append(f"# {line}")
                python_lines.append("")
            elif cell.cell_type == "raw":
                python_lines.extend([
                    f"# %% Cell {i + 1} - Raw",
                    f'"""\n{cell.source}\n"""',
                    ""
                ])
        
        # Write Python file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(python_lines))
            
            logger.info(f"Exported notebook to Python: {output_path}")
            return str(output_path)
            
        except Exception as e:
            raise FileSystemError(
                f"Failed to export to Python: {e}",
                str(output_path),
                "export"
            )
    
    def _create_backup(self, path: Path) -> None:
        """Create backup of existing file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.security.get_safe_backup_path(path, timestamp)
        
        try:
            backup_path.write_bytes(path.read_bytes())
            logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
    
    def _ensure_notebook_metadata(self, notebook: nbformat.NotebookNode) -> None:
        """Ensure notebook has required metadata."""
        if not hasattr(notebook, 'metadata'):
            notebook.metadata = {}
        
        # Ensure kernelspec exists
        if 'kernelspec' not in notebook.metadata:
            notebook.metadata['kernelspec'] = {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            }
        
        # Ensure language_info exists
        if 'language_info' not in notebook.metadata:
            notebook.metadata['language_info'] = {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3"
            }
    
    def _get_kernel_metadata(self, language: str) -> Dict[str, Any]:
        """Get kernel metadata for specific language."""
        if language.lower() == "python":
            return {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "codemirror_mode": {"name": "ipython", "version": 3},
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3"
                }
            }
        else:
            # Generic metadata for other languages
            return {
                "kernelspec": {
                    "display_name": language.title(),
                    "language": language.lower(),
                    "name": language.lower()
                },
                "language_info": {
                    "name": language.lower(),
                    "file_extension": f".{language.lower()}"
                }
            }
    
    def _analyze_cells(self, cells: List[nbformat.NotebookNode]) -> Dict[str, Any]:
        """Analyze cells and return statistics."""
        stats = {
            "total": len(cells),
            "code": 0,
            "markdown": 0,
            "raw": 0,
            "executed_code": 0,
            "has_outputs": 0
        }
        
        for cell in cells:
            cell_type = cell.cell_type
            stats[cell_type] = stats.get(cell_type, 0) + 1
            
            if cell_type == "code":
                if cell.get("execution_count") is not None:
                    stats["executed_code"] += 1
                if cell.get("outputs"):
                    stats["has_outputs"] += 1
        
        return stats
