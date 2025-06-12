"""Execution management for the VSCode Notebook MCP Server."""

import asyncio
import base64
import io
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

from .exceptions import NotebookError, ExecutionError
from .notebook_manager import NotebookManager

logger = logging.getLogger(__name__)


class ExecutionManager:
    """Manages kernel execution for notebooks."""
    
    def __init__(self, notebook_manager: NotebookManager) -> None:
        """Initialize execution manager.
        
        Args:
            notebook_manager: NotebookManager instance for notebook operations
        """
        self.notebook_manager = notebook_manager
        self.kernels: Dict[str, KernelManager] = {}
        self.kernel_specs = KernelSpecManager()
        self.execution_timeout = 60  # Default timeout in seconds
    
    def _get_kernel_for_notebook(self, notebook_path: str) -> KernelManager:
        """Get or create a kernel for the specified notebook.
        
        Args:
            notebook_path: Path to the notebook
            
        Returns:
            KernelManager instance
        """
        # Use notebook path as kernel identifier
        kernel_id = str(Path(notebook_path).resolve())
        
        if kernel_id not in self.kernels:
            # Load notebook to determine kernel spec
            notebook = self.notebook_manager.load_notebook(notebook_path)
            kernel_name = self._get_kernel_name_from_notebook(notebook)
            
            # Create new kernel
            km = KernelManager(kernel_name=kernel_name)
            km.start_kernel()
            
            # Wait for kernel to be ready
            kc = km.client()
            kc.wait_for_ready(timeout=30)
            try:
                if hasattr(kc, 'stop_channels'):
                    kc.stop_channels()
            except Exception:
                pass
            
            self.kernels[kernel_id] = km
            logger.info(f"Started new kernel for {notebook_path} with spec: {kernel_name}")
        
        return self.kernels[kernel_id]
    
    def _get_kernel_name_from_notebook(self, notebook: nbformat.NotebookNode) -> str:
        """Extract kernel name from notebook metadata.
        
        Args:
            notebook: Notebook object
            
        Returns:
            Kernel specification name
        """
        # Try to get from kernelspec
        kernelspec = notebook.metadata.get('kernelspec', {})
        kernel_name = kernelspec.get('name', 'python3')
        
        # Validate kernel exists
        try:
            self.kernel_specs.get_kernel_spec(kernel_name)
            return kernel_name
        except Exception:
            # Fallback to python3 if specified kernel doesn't exist
            logger.warning(f"Kernel '{kernel_name}' not found, falling back to 'python3'")
            return 'python3'
    
    def execute_cell(self, notebook_path: str, cell_index: int, 
                    timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute a specific cell in a notebook.
        
        Args:
            notebook_path: Path to the notebook
            cell_index: Index of the cell to execute
            timeout: Execution timeout in seconds
            
        Returns:
            Execution result dictionary
        """
        start_time = time.time()
        timeout = timeout or self.execution_timeout
        
        try:
            # Load notebook and validate cell index
            notebook = self.notebook_manager.load_notebook(notebook_path)
            
            if not (0 <= cell_index < len(notebook.cells)):
                raise ExecutionError(f"Cell index {cell_index} out of range (0-{len(notebook.cells)-1})")
            
            cell = notebook.cells[cell_index]
            
            # Only execute code cells
            if cell.cell_type != 'code':
                return {
                    "success": True,
                    "cell_index": cell_index,
                    "cell_type": cell.cell_type,
                    "execution_time": 0,
                    "outputs": [],
                    "message": f"Skipped {cell.cell_type} cell (only code cells can be executed)"
                }
            
            # Get kernel and execute
            km = self._get_kernel_for_notebook(notebook_path)
            kc = km.client()
            
            try:
                # Execute the cell code
                msg_id = kc.execute(cell.source)
                
                # Collect outputs
                outputs = []
                execution_count = None
                
                while True:
                    try:
                        msg = kc.get_iopub_msg(timeout=timeout)
                        msg_type = msg['msg_type']
                        content = msg['content']
                        
                        if msg_type == 'execute_input':
                            execution_count = content.get('execution_count')
                        
                        elif msg_type in ['stream', 'display_data', 'execute_result', 'error']:
                            output = self._process_output(msg_type, content)
                            if output:
                                outputs.append(output)
                        
                        elif msg_type == 'status' and content.get('execution_state') == 'idle':
                            break
                            
                    except Exception as e:
                        if "timeout" in str(e).lower():
                            raise ExecutionError(f"Cell execution timed out after {timeout} seconds")
                        break
                
                # Update cell in notebook
                cell.execution_count = execution_count
                cell.outputs = self._convert_outputs_to_nbformat(outputs)
                
                # Save notebook with execution results
                self.notebook_manager.save_notebook(notebook, notebook_path, create_backup=False)
                
                execution_time = time.time() - start_time
                
                return {
                    "success": True,
                    "notebook_path": str(notebook_path),
                    "cell_index": cell_index,
                    "cell_type": cell.cell_type,
                    "execution_count": execution_count,
                    "execution_time": round(execution_time, 3),
                    "outputs": outputs,
                    "source": cell.source,
                    "message": f"Successfully executed cell {cell_index}"
                }
                
            finally:
                # Safely close client
                try:
                    if hasattr(kc, 'stop_channels'):
                        kc.stop_channels()
                except Exception:
                    pass
        
        except Exception as e:
            execution_time = time.time() - start_time
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Failed to execute cell {cell_index}: {e}")
    
    def execute_all_cells(self, notebook_path: str, 
                         timeout: Optional[int] = None,
                         stop_on_error: bool = False) -> Dict[str, Any]:
        """Execute all cells in a notebook sequentially.
        
        Args:
            notebook_path: Path to the notebook
            timeout: Execution timeout per cell in seconds
            stop_on_error: Whether to stop execution on first error
            
        Returns:
            Execution results dictionary
        """
        start_time = time.time()
        
        try:
            notebook = self.notebook_manager.load_notebook(notebook_path)
            
            results = []
            executed_cells = 0
            errors = []
            
            for i in range(len(notebook.cells)):
                try:
                    result = self.execute_cell(notebook_path, i, timeout)
                    results.append(result)
                    
                    if notebook.cells[i].cell_type == 'code':
                        executed_cells += 1
                        
                    # Check for errors in outputs
                    cell_errors = [out for out in result.get('outputs', []) if out.get('output_type') == 'error']
                    if cell_errors:
                        errors.extend(cell_errors)
                        if stop_on_error:
                            break
                            
                except Exception as e:
                    error_result = {
                        "success": False,
                        "cell_index": i,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    results.append(error_result)
                    errors.append(error_result)
                    
                    if stop_on_error:
                        break
            
            total_time = time.time() - start_time
            
            return {
                "success": True,
                "notebook_path": str(notebook_path),
                "total_cells": len(notebook.cells),
                "executed_cells": executed_cells,
                "total_time": round(total_time, 3),
                "errors_count": len(errors),
                "results": results,
                "errors": errors,
                "message": f"Executed {executed_cells} code cells in {total_time:.2f}s"
            }
            
        except Exception as e:
            raise ExecutionError(f"Failed to execute notebook: {e}")
    
    def execute_cells_range(self, notebook_path: str, start_index: int, end_index: int,
                           timeout: Optional[int] = None,
                           stop_on_error: bool = False) -> Dict[str, Any]:
        """Execute a range of cells in a notebook.
        
        Args:
            notebook_path: Path to the notebook
            start_index: Starting cell index (inclusive)
            end_index: Ending cell index (inclusive)
            timeout: Execution timeout per cell in seconds
            stop_on_error: Whether to stop execution on first error
            
        Returns:
            Execution results dictionary
        """
        try:
            notebook = self.notebook_manager.load_notebook(notebook_path)
            
            # Validate range
            if not (0 <= start_index <= end_index < len(notebook.cells)):
                raise ExecutionError(f"Invalid range: {start_index}-{end_index} for notebook with {len(notebook.cells)} cells")
            
            start_time = time.time()
            results = []
            executed_cells = 0
            errors = []
            
            for i in range(start_index, end_index + 1):
                try:
                    result = self.execute_cell(notebook_path, i, timeout)
                    results.append(result)
                    
                    if notebook.cells[i].cell_type == 'code':
                        executed_cells += 1
                        
                    # Check for errors
                    cell_errors = [out for out in result.get('outputs', []) if out.get('output_type') == 'error']
                    if cell_errors:
                        errors.extend(cell_errors)
                        if stop_on_error:
                            break
                            
                except Exception as e:
                    error_result = {
                        "success": False,
                        "cell_index": i,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    results.append(error_result)
                    errors.append(error_result)
                    
                    if stop_on_error:
                        break
            
            total_time = time.time() - start_time
            
            return {
                "success": True,
                "notebook_path": str(notebook_path),
                "start_index": start_index,
                "end_index": end_index,
                "range_size": end_index - start_index + 1,
                "executed_cells": executed_cells,
                "total_time": round(total_time, 3),
                "errors_count": len(errors),
                "results": results,
                "errors": errors,
                "message": f"Executed cells {start_index}-{end_index} ({executed_cells} code cells) in {total_time:.2f}s"
            }
            
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Failed to execute cell range: {e}")
    
    def execute_code_snippet(self, notebook_path: str, code: str,
                           timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute arbitrary code without modifying the notebook.
        
        Args:
            notebook_path: Path to notebook (to determine kernel context)
            code: Code to execute
            timeout: Execution timeout in seconds
            
        Returns:
            Execution results dictionary
        """
        start_time = time.time()
        timeout = timeout or self.execution_timeout
        
        try:
            # Get kernel for context
            km = self._get_kernel_for_notebook(notebook_path)
            kc = km.client()
            
            try:
                # Execute code
                msg_id = kc.execute(code)
                
                outputs = []
                execution_count = None
                
                while True:
                    try:
                        msg = kc.get_iopub_msg(timeout=timeout)
                        msg_type = msg['msg_type']
                        content = msg['content']
                        
                        if msg_type == 'execute_input':
                            execution_count = content.get('execution_count')
                        
                        elif msg_type in ['stream', 'display_data', 'execute_result', 'error']:
                            output = self._process_output(msg_type, content)
                            if output:
                                outputs.append(output)
                        
                        elif msg_type == 'status' and content.get('execution_state') == 'idle':
                            break
                            
                    except Exception as e:
                        if "timeout" in str(e).lower():
                            raise ExecutionError(f"Code execution timed out after {timeout} seconds")
                        break
                
                execution_time = time.time() - start_time
                
                return {
                    "success": True,
                    "notebook_path": str(notebook_path),
                    "code": code,
                    "execution_count": execution_count,
                    "execution_time": round(execution_time, 3),
                    "outputs": outputs,
                    "message": "Successfully executed code snippet"
                }
                
            finally:
                # Safely close client
                try:
                    if hasattr(kc, 'stop_channels'):
                        kc.stop_channels()
                except Exception:
                    pass
        
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Failed to execute code snippet: {e}")
    
    def restart_kernel(self, notebook_path: str) -> Dict[str, Any]:
        """Restart the kernel for a notebook.
        
        Args:
            notebook_path: Path to the notebook
            
        Returns:
            Operation result dictionary
        """
        try:
            kernel_id = str(Path(notebook_path).resolve())
            
            if kernel_id in self.kernels:
                # Stop existing kernel
                km = self.kernels[kernel_id]
                km.shutdown_kernel()
                del self.kernels[kernel_id]
            
            # Start new kernel
            km = self._get_kernel_for_notebook(notebook_path)
            
            return {
                "success": True,
                "notebook_path": str(notebook_path),
                "message": "Kernel restarted successfully"
            }
            
        except Exception as e:
            raise ExecutionError(f"Failed to restart kernel: {e}")
    
    def get_kernel_status(self, notebook_path: str) -> Dict[str, Any]:
        """Get the status of a notebook's kernel.
        
        Args:
            notebook_path: Path to the notebook
            
        Returns:
            Kernel status dictionary
        """
        try:
            kernel_id = str(Path(notebook_path).resolve())
            
            if kernel_id not in self.kernels:
                return {
                    "success": True,
                    "notebook_path": str(notebook_path),
                    "kernel_status": "not_started",
                    "message": "No kernel running for this notebook"
                }
            
            km = self.kernels[kernel_id]
            kc = km.client()
            
            try:
                # Check if kernel is responsive
                kc.execute("1+1")
                msg = kc.get_shell_msg(timeout=1)
                
                return {
                    "success": True,
                    "notebook_path": str(notebook_path),
                    "kernel_status": "idle",
                    "kernel_id": km.kernel.kernel_id if hasattr(km, 'kernel') else None,
                    "message": "Kernel is running and responsive"
                }
                
            except Exception:
                return {
                    "success": True,
                    "notebook_path": str(notebook_path),
                    "kernel_status": "busy_or_unresponsive",
                    "message": "Kernel is running but may be busy or unresponsive"
                }
            finally:
                try:
                    if hasattr(kc, 'stop_channels'):
                        kc.stop_channels()
                except Exception:
                    pass
            
        except Exception as e:
            return {
                "success": False,
                "notebook_path": str(notebook_path),
                "error": str(e),
                "message": "Failed to get kernel status"
            }
    
    def interrupt_kernel(self, notebook_path: str) -> Dict[str, Any]:
        """Interrupt a running kernel.
        
        Args:
            notebook_path: Path to the notebook
            
        Returns:
            Operation result dictionary
        """
        try:
            kernel_id = str(Path(notebook_path).resolve())
            
            if kernel_id not in self.kernels:
                return {
                    "success": False,
                    "notebook_path": str(notebook_path),
                    "message": "No kernel running for this notebook"
                }
            
            km = self.kernels[kernel_id]
            km.interrupt_kernel()
            
            return {
                "success": True,
                "notebook_path": str(notebook_path),
                "message": "Kernel interrupted successfully"
            }
            
        except Exception as e:
            raise ExecutionError(f"Failed to interrupt kernel: {e}")
    
    def _process_output(self, msg_type: str, content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process kernel output message into standardized format.
        
        Args:
            msg_type: Type of the message
            content: Message content
            
        Returns:
            Processed output dictionary or None
        """
        if msg_type == 'stream':
            return {
                "output_type": "stream",
                "name": content.get("name", "stdout"),
                "text": content.get("text", "")
            }
        
        elif msg_type == 'display_data':
            return {
                "output_type": "display_data",
                "data": content.get("data", {}),
                "metadata": content.get("metadata", {})
            }
        
        elif msg_type == 'execute_result':
            return {
                "output_type": "execute_result",
                "execution_count": content.get("execution_count"),
                "data": content.get("data", {}),
                "metadata": content.get("metadata", {})
            }
        
        elif msg_type == 'error':
            return {
                "output_type": "error",
                "ename": content.get("ename", ""),
                "evalue": content.get("evalue", ""),
                "traceback": content.get("traceback", [])
            }
        
        return None
    
    def _convert_outputs_to_nbformat(self, outputs: List[Dict[str, Any]]) -> List[nbformat.NotebookNode]:
        """Convert processed outputs back to nbformat.
        
        Args:
            outputs: List of processed output dictionaries
            
        Returns:
            List of nbformat output nodes
        """
        nbformat_outputs = []
        
        for output in outputs:
            if output['output_type'] == 'stream':
                nb_output = nbformat.v4.new_output(
                    output_type='stream',
                    name=output['name'],
                    text=output['text']
                )
            
            elif output['output_type'] == 'display_data':
                nb_output = nbformat.v4.new_output(
                    output_type='display_data',
                    data=output['data'],
                    metadata=output['metadata']
                )
            
            elif output['output_type'] == 'execute_result':
                nb_output = nbformat.v4.new_output(
                    output_type='execute_result',
                    execution_count=output['execution_count'],
                    data=output['data'],
                    metadata=output['metadata']
                )
            
            elif output['output_type'] == 'error':
                nb_output = nbformat.v4.new_output(
                    output_type='error',
                    ename=output['ename'],
                    evalue=output['evalue'],
                    traceback=output['traceback']
                )
            
            else:
                continue
            
            nbformat_outputs.append(nb_output)
        
        return nbformat_outputs
    
    def cleanup(self) -> None:
        """Clean up all running kernels."""
        for kernel_id, km in self.kernels.items():
            try:
                km.shutdown_kernel()
                logger.info(f"Shutdown kernel: {kernel_id}")
            except Exception as e:
                logger.warning(f"Error shutting down kernel {kernel_id}: {e}")
        
        self.kernels.clear()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.cleanup()
        except Exception:
            pass
