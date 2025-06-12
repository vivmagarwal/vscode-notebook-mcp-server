"""Cell management for the VSCode Notebook MCP Server."""

import logging
from typing import Any, Dict, List, Optional, Union, Tuple

import nbformat
from nbformat import v4 as nbf

from .exceptions import NotebookError, ValidationError
from .notebook_manager import NotebookManager

logger = logging.getLogger(__name__)


class CellManager:
    """Manages individual cell operations within notebooks."""
    
    def __init__(self, notebook_manager: NotebookManager) -> None:
        """Initialize cell manager.
        
        Args:
            notebook_manager: NotebookManager instance for notebook operations
        """
        self.notebook_manager = notebook_manager
    
    def add_cell(self, notebook_path: str, cell_type: str, content: str, 
                 index: Optional[int] = None) -> Dict[str, Any]:
        """Add a new cell to a notebook.
        
        Args:
            notebook_path: Path to notebook file
            cell_type: Type of cell ("code", "markdown", "raw")
            content: Cell content
            index: Position to insert cell (None for end)
            
        Returns:
            Result dictionary with operation details
        """
        # Validate cell type
        if cell_type not in ["code", "markdown", "raw"]:
            raise ValidationError(f"Invalid cell type", "cell_type", cell_type)
        
        # Load notebook
        notebook = self.notebook_manager.load_notebook(notebook_path)
        
        # Create new cell
        if cell_type == "code":
            new_cell = nbf.new_code_cell(content)
        elif cell_type == "markdown":
            new_cell = nbf.new_markdown_cell(content)
        else:  # raw
            new_cell = nbf.new_raw_cell(content)
        
        # Add cell at specified position
        if index is None:
            notebook.cells.append(new_cell)
            index = len(notebook.cells) - 1
        else:
            if 0 <= index <= len(notebook.cells):
                notebook.cells.insert(index, new_cell)
            else:
                raise ValidationError(f"Index out of range", "index", str(index))
        
        # Save notebook (no backup for regular cell operations)
        self.notebook_manager.save_notebook(notebook, notebook_path, create_backup=False)
        
        return {
            "success": True,
            "notebook_path": str(notebook_path),
            "cell_type": cell_type,
            "index": index,
            "total_cells": len(notebook.cells),
            "message": f"Added {cell_type} cell at index {index}"
        }
    
    def modify_cell(self, notebook_path: str, index: int, content: str) -> Dict[str, Any]:
        """Modify content of an existing cell.
        
        Args:
            notebook_path: Path to notebook file
            index: Index of cell to modify
            content: New cell content
            
        Returns:
            Result dictionary with operation details
        """
        notebook = self.notebook_manager.load_notebook(notebook_path)
        
        # Validate index
        if not (0 <= index < len(notebook.cells)):
            raise ValidationError(f"Cell index out of range", "index", str(index))
        
        cell = notebook.cells[index]
        old_content = cell.source
        cell.source = content
        
        # Clear outputs and execution count for code cells when modified
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
        
        # Save notebook (no backup for regular cell operations)
        self.notebook_manager.save_notebook(notebook, notebook_path, create_backup=False)
        
        return {
            "success": True,
            "notebook_path": str(notebook_path),
            "index": index,
            "cell_type": cell.cell_type,
            "content_length": len(content),
            "previous_content_length": len(old_content),
            "message": f"Modified {cell.cell_type} cell at index {index}"
        }
    
    def delete_cell(self, notebook_path: str, index: int) -> Dict[str, Any]:
        """Delete a cell from a notebook.
        
        Args:
            notebook_path: Path to notebook file
            index: Index of cell to delete
            
        Returns:
            Result dictionary with operation details
        """
        notebook = self.notebook_manager.load_notebook(notebook_path)
        
        # Validate index
        if not (0 <= index < len(notebook.cells)):
            raise ValidationError(f"Cell index out of range", "index", str(index))
        
        # Don't allow deleting the last cell if it would leave notebook empty
        if len(notebook.cells) == 1:
            raise NotebookError("Cannot delete the last cell in a notebook")
        
        deleted_cell = notebook.cells.pop(index)
        
        # Save notebook (no backup for regular cell operations)
        self.notebook_manager.save_notebook(notebook, notebook_path, create_backup=False)
        
        return {
            "success": True,
            "notebook_path": str(notebook_path),
            "deleted_index": index,
            "deleted_cell_type": deleted_cell.cell_type,
            "remaining_cells": len(notebook.cells),
            "message": f"Deleted {deleted_cell.cell_type} cell at index {index}"
        }
    
    def get_cell(self, notebook_path: str, index: int) -> Dict[str, Any]:
        """Get content and metadata of a specific cell.
        
        Args:
            notebook_path: Path to notebook file
            index: Index of cell to retrieve
            
        Returns:
            Cell information dictionary
        """
        notebook = self.notebook_manager.load_notebook(notebook_path)
        
        # Validate index
        if not (0 <= index < len(notebook.cells)):
            raise ValidationError(f"Cell index out of range", "index", str(index))
        
        cell = notebook.cells[index]
        
        result = {
            "success": True,
            "index": index,
            "cell_type": cell.cell_type,
            "source": cell.source,
            "metadata": dict(cell.metadata) if cell.metadata else {},
            "content_length": len(cell.source)
        }
        
        # Add code cell specific information
        if cell.cell_type == "code":
            result.update({
                "execution_count": cell.execution_count,
                "has_outputs": bool(cell.outputs),
                "output_count": len(cell.outputs) if cell.outputs else 0,
                "outputs": self._extract_cell_outputs(cell) if cell.outputs else []
            })
        
        return result
    
    def get_all_cells(self, notebook_path: str) -> Dict[str, Any]:
        """Get information about all cells in a notebook.
        
        Args:
            notebook_path: Path to notebook file
            
        Returns:
            Dictionary with all cells information
        """
        notebook = self.notebook_manager.load_notebook(notebook_path)
        
        cells_info = []
        for i, cell in enumerate(notebook.cells):
            cell_info = {
                "index": i,
                "cell_type": cell.cell_type,
                "source": cell.source,
                "content_length": len(cell.source),
                "metadata": dict(cell.metadata) if cell.metadata else {}
            }
            
            if cell.cell_type == "code":
                cell_info.update({
                    "execution_count": cell.execution_count,
                    "has_outputs": bool(cell.outputs),
                    "output_count": len(cell.outputs) if cell.outputs else 0
                })
            
            cells_info.append(cell_info)
        
        return {
            "success": True,
            "notebook_path": str(notebook_path),
            "total_cells": len(notebook.cells),
            "cells": cells_info
        }
    
    def move_cell(self, notebook_path: str, from_index: int, to_index: int) -> Dict[str, Any]:
        """Move a cell from one position to another.
        
        Args:
            notebook_path: Path to notebook file
            from_index: Current index of cell
            to_index: Target index for cell
            
        Returns:
            Result dictionary with operation details
        """
        notebook = self.notebook_manager.load_notebook(notebook_path)
        
        # Validate indices
        if not (0 <= from_index < len(notebook.cells)):
            raise ValidationError(f"Source index out of range", "from_index", str(from_index))
        
        if not (0 <= to_index < len(notebook.cells)):
            raise ValidationError(f"Target index out of range", "to_index", str(to_index))
        
        if from_index == to_index:
            return {
                "success": True,
                "notebook_path": str(notebook_path),
                "message": "Cell is already at target position"
            }
        
        # Move cell
        cell = notebook.cells.pop(from_index)
        notebook.cells.insert(to_index, cell)
        
        # Save notebook (no backup for regular cell operations)
        self.notebook_manager.save_notebook(notebook, notebook_path, create_backup=False)
        
        return {
            "success": True,
            "notebook_path": str(notebook_path),
            "from_index": from_index,
            "to_index": to_index,
            "cell_type": cell.cell_type,
            "message": f"Moved {cell.cell_type} cell from index {from_index} to {to_index}"
        }
    
    def duplicate_cell(self, notebook_path: str, index: int, 
                      target_index: Optional[int] = None) -> Dict[str, Any]:
        """Duplicate a cell at specified position.
        
        Args:
            notebook_path: Path to notebook file
            index: Index of cell to duplicate
            target_index: Position for duplicated cell (None for after original)
            
        Returns:
            Result dictionary with operation details
        """
        notebook = self.notebook_manager.load_notebook(notebook_path)
        
        # Validate index
        if not (0 <= index < len(notebook.cells)):
            raise ValidationError(f"Cell index out of range", "index", str(index))
        
        # Get original cell
        original_cell = notebook.cells[index]
        
        # Create duplicate
        if original_cell.cell_type == "code":
            new_cell = nbf.new_code_cell(original_cell.source)
        elif original_cell.cell_type == "markdown":
            new_cell = nbf.new_markdown_cell(original_cell.source)
        else:  # raw
            new_cell = nbf.new_raw_cell(original_cell.source)
        
        # Copy metadata
        if original_cell.metadata:
            new_cell.metadata = dict(original_cell.metadata)
        
        # Determine insertion position
        if target_index is None:
            target_index = index + 1
        elif not (0 <= target_index <= len(notebook.cells)):
            raise ValidationError(f"Target index out of range", "target_index", str(target_index))
        
        # Insert duplicate
        notebook.cells.insert(target_index, new_cell)
        
        # Save notebook (no backup for regular cell operations)
        self.notebook_manager.save_notebook(notebook, notebook_path, create_backup=False)
        
        return {
            "success": True,  
            "notebook_path": str(notebook_path),
            "original_index": index,
            "duplicate_index": target_index,
            "cell_type": original_cell.cell_type,
            "total_cells": len(notebook.cells),
            "message": f"Duplicated {original_cell.cell_type} cell from index {index} to {target_index}"
        }
    
    def search_cells(self, notebook_path: str, search_term: str, 
                    case_sensitive: bool = False, 
                    cell_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Search for content across cells.
        
        Args:
            notebook_path: Path to notebook file
            search_term: Text to search for
            case_sensitive: Whether search should be case sensitive
            cell_types: List of cell types to search (None for all)
            
        Returns:
            Search results dictionary
        """
        notebook = self.notebook_manager.load_notebook(notebook_path)
        
        if cell_types is None:
            cell_types = ["code", "markdown", "raw"]
        
        # Validate cell types
        valid_types = {"code", "markdown", "raw"}
        invalid_types = set(cell_types) - valid_types
        if invalid_types:
            raise ValidationError(f"Invalid cell types", "cell_types", str(invalid_types))
        
        matches = []
        search_text = search_term if case_sensitive else search_term.lower()
        
        for i, cell in enumerate(notebook.cells):
            if cell.cell_type not in cell_types:
                continue
                
            cell_content = cell.source
            check_content = cell_content if case_sensitive else cell_content.lower()
            
            if search_text in check_content:
                lines = cell_content.split('\n')
                matching_lines = []
                
                for line_num, line in enumerate(lines):
                    check_line = line if case_sensitive else line.lower()
                    if search_text in check_line:
                        # Find all occurrences in the line
                        positions = []
                        start = 0
                        while True:
                            pos = check_line.find(search_text, start)
                            if pos == -1:
                                break
                            positions.append(pos)
                            start = pos + 1
                        
                        matching_lines.append({
                            "line_number": line_num + 1,
                            "content": line,
                            "positions": positions
                        })
                
                matches.append({
                    "cell_index": i,
                    "cell_type": cell.cell_type,
                    "total_matches": sum(len(line["positions"]) for line in matching_lines),
                    "matching_lines": matching_lines
                })
        
        return {
            "success": True,
            "notebook_path": str(notebook_path),
            "search_term": search_term,
            "case_sensitive": case_sensitive,
            "searched_cell_types": cell_types,
            "total_matches": sum(match["total_matches"] for match in matches),
            "cells_with_matches": len(matches),
            "matches": matches
        }
    
    def replace_in_cells(self, notebook_path: str, search_term: str, replace_term: str,
                        case_sensitive: bool = False, 
                        cell_types: Optional[List[str]] = None,
                        max_replacements: Optional[int] = None) -> Dict[str, Any]:
        """Replace text across cells.
        
        Args:
            notebook_path: Path to notebook file  
            search_term: Text to search for
            replace_term: Text to replace with
            case_sensitive: Whether search should be case sensitive
            cell_types: List of cell types to search (None for all)
            max_replacements: Maximum number of replacements (None for unlimited)
            
        Returns:
            Replace results dictionary
        """
        notebook = self.notebook_manager.load_notebook(notebook_path)
        
        if cell_types is None:
            cell_types = ["code", "markdown", "raw"]
        
        # Validate cell types
        valid_types = {"code", "markdown", "raw"}
        invalid_types = set(cell_types) - valid_types
        if invalid_types:
            raise ValidationError(f"Invalid cell types", "cell_types", str(invalid_types))
        
        total_replacements = 0
        modified_cells = []
        
        for i, cell in enumerate(notebook.cells):
            if cell.cell_type not in cell_types:
                continue
            
            if max_replacements is not None and total_replacements >= max_replacements:
                break
            
            original_content = cell.source
            
            # Perform replacement
            if case_sensitive:
                new_content = original_content.replace(search_term, replace_term)
            else:
                # Case-insensitive replacement
                import re
                pattern = re.escape(search_term)
                new_content = re.sub(pattern, replace_term, original_content, flags=re.IGNORECASE)
            
            # Count replacements in this cell
            if case_sensitive:
                cell_replacements = original_content.count(search_term)
            else:
                cell_replacements = len(re.findall(re.escape(search_term), original_content, re.IGNORECASE))
            
            if new_content != original_content:
                # Apply replacement limit
                if max_replacements is not None:
                    remaining_replacements = max_replacements - total_replacements
                    if cell_replacements > remaining_replacements:
                        # Need to limit replacements in this cell
                        if case_sensitive:
                            parts = original_content.split(search_term)
                            new_content = replace_term.join(parts[:remaining_replacements + 1]) + search_term.join(parts[remaining_replacements + 1:])
                        else:
                            # More complex for case-insensitive
                            import re
                            count = 0
                            def replace_func(match):
                                nonlocal count
                                if count < remaining_replacements:
                                    count += 1
                                    return replace_term
                                return match.group(0)
                            
                            pattern = re.escape(search_term)
                            new_content = re.sub(pattern, replace_func, original_content, flags=re.IGNORECASE)
                        
                        cell_replacements = remaining_replacements
                
                cell.source = new_content
                total_replacements += cell_replacements
                
                # Clear outputs for code cells when modified
                if cell.cell_type == "code":
                    cell.outputs = []
                    cell.execution_count = None
                
                modified_cells.append({
                    "index": i,
                    "cell_type": cell.cell_type,
                    "replacements": cell_replacements
                })
        
        # Save notebook if any changes were made (no backup for regular cell operations)
        if modified_cells:
            self.notebook_manager.save_notebook(notebook, notebook_path, create_backup=False)
        
        return {
            "success": True,
            "notebook_path": str(notebook_path),
            "search_term": search_term,
            "replace_term": replace_term,
            "case_sensitive": case_sensitive,
            "total_replacements": total_replacements,
            "modified_cells": len(modified_cells),
            "cells": modified_cells
        }
    
    def _extract_cell_outputs(self, cell: nbformat.NotebookNode) -> List[Dict[str, Any]]:
        """Extract outputs from a code cell.
        
        Args:
            cell: Code cell with outputs
            
        Returns:
            List of output dictionaries
        """
        outputs = []
        
        for output in cell.outputs:
            output_info = {
                "output_type": output.output_type
            }
            
            if output.output_type == "stream":
                output_info.update({
                    "name": output.get("name", "stdout"),
                    "text": self._extract_text_from_output(output.get("text", ""))
                })
            elif output.output_type in ["display_data", "execute_result"]:
                output_info.update({
                    "data": dict(output.get("data", {})),
                    "metadata": dict(output.get("metadata", {}))
                })
                if output.output_type == "execute_result":
                    output_info["execution_count"] = output.get("execution_count")
            elif output.output_type == "error":
                output_info.update({
                    "ename": output.get("ename", ""),
                    "evalue": output.get("evalue", ""),
                    "traceback": output.get("traceback", [])
                })
            
            outputs.append(output_info)
        
        return outputs
    
    def _extract_text_from_output(self, text_data: Union[str, List[str]]) -> str:
        """Extract text from output data.
        
        Args:
            text_data: Text data from output
            
        Returns:
            Extracted text string
        """
        if isinstance(text_data, str):
            return text_data
        elif isinstance(text_data, list):
            return ''.join(text_data)
        else:
            return str(text_data)
