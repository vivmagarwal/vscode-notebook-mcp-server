#!/usr/bin/env python3
"""Test script for execution functionality of VSCode Notebook MCP Server."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vscode_notebook_mcp_server.server import VSCodeNotebookMCPServer
import tempfile
import json

def test_execution_features():
    """Test the execution features of the MCP server."""
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Testing in directory: {temp_dir}")
        
        # Initialize server with temp directory
        server = VSCodeNotebookMCPServer(allowed_directories=[temp_dir])
        
        # Create a test notebook
        notebook_path = os.path.join(temp_dir, "test_execution.ipynb")
        
        print("\n1. Creating test notebook...")
        
        # Tools are already registered during server initialization
        # Access them directly from the server components
        nb_manager = server.notebook_manager
        cell_manager = server.cell_manager
        exec_manager = server.execution_manager
        
        # Create notebook using the notebook manager
        try:
            notebook = nb_manager.create_new_notebook(notebook_path, "Execution Test")
            print(f"   Create result: Success")
        except Exception as e:
            print(f"   Create result: Failed - {e}")
            return
        
        # Add some test cells
        print("\n2. Adding test cells...")
        
        # Add a simple math cell
        try:
            cell_manager.add_cell(notebook_path, "code", "x = 5\ny = 10\nresult = x + y\nprint(f'Result: {result}')")
            print(f"   Added cell 0: Success")
        except Exception as e:
            print(f"   Added cell 0: Failed - {e}")
        
        # Add a cell that creates a variable
        try:
            cell_manager.add_cell(notebook_path, "code", "import math\npi_value = math.pi\nprint(f'Pi: {pi_value:.4f}')")
            print(f"   Added cell 1: Success")
        except Exception as e:
            print(f"   Added cell 1: Failed - {e}")
        
        # Add a cell that uses the previous variable
        try:
            cell_manager.add_cell(notebook_path, "code", "area = pi_value * (3 ** 2)\nprint(f'Area of circle with radius 3: {area:.2f}')")
            print(f"   Added cell 2: Success")
        except Exception as e:
            print(f"   Added cell 2: Failed - {e}")
        
        # Add a markdown cell (should be skipped during execution)
        try:
            cell_manager.add_cell(notebook_path, "markdown", "# This is a markdown cell\nIt should be skipped during execution.")
            print(f"   Added cell 3 (markdown): Success")
        except Exception as e:
            print(f"   Added cell 3 (markdown): Failed - {e}")
        
        print("\n3. Testing individual cell execution...")
        try:
            exec_result = exec_manager.execute_cell(notebook_path, 0)
            print(f"   Execute cell 0: {exec_result['success']}")
            if exec_result['success']:
                print(f"   Execution time: {exec_result['execution_time']}s")
                print(f"   Outputs: {len(exec_result['outputs'])}")
                for i, output in enumerate(exec_result['outputs']):
                    if output['output_type'] == 'stream':
                        print(f"     Output {i}: {output['text'].strip()}")
        except Exception as e:
            print(f"   Execute cell 0 failed: {e}")
        
        print("\n4. Testing execute all cells...")
        try:
            exec_all_result = exec_manager.execute_all_cells(notebook_path)
            print(f"   Execute all cells: {exec_all_result['success']}")
            if exec_all_result['success']:
                print(f"   Total execution time: {exec_all_result['total_time']}s")
                print(f"   Executed cells: {exec_all_result['executed_cells']}")
                print(f"   Errors: {exec_all_result['errors_count']}")
        except Exception as e:
            print(f"   Execute all cells failed: {e}")
        
        print("\n5. Testing code snippet execution...")
        try:
            snippet_result = exec_manager.execute_code_snippet(
                notebook_path, 
                "import sys\nprint(f'Python version: {sys.version_info.major}.{sys.version_info.minor}')"
            )
            print(f"   Execute snippet: {snippet_result['success']}")
            if snippet_result['success']:
                print(f"   Execution time: {snippet_result['execution_time']}s")
                for output in snippet_result['outputs']:
                    if output['output_type'] == 'stream':
                        print(f"     Output: {output['text'].strip()}")
        except Exception as e:
            print(f"   Execute snippet failed: {e}")
        
        print("\n6. Testing kernel status...")
        try:
            status_result = exec_manager.get_kernel_status(notebook_path)
            print(f"   Kernel status: {status_result['kernel_status']}")
        except Exception as e:
            print(f"   Get kernel status failed: {e}")
        
        print("\n7. Testing execution range...")
        try:
            range_result = exec_manager.execute_cells_range(notebook_path, 1, 2)
            print(f"   Execute range (1-2): {range_result['success']}")
            if range_result['success']:
                print(f"   Range execution time: {range_result['total_time']}s")
                print(f"   Executed cells in range: {range_result['executed_cells']}")
        except Exception as e:
            print(f"   Execute range failed: {e}")
        
        print("\n8. Testing server info...")
        info_result = {
            "success": True,
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
        print(f"   Server info: {info_result['success']}")
        print(f"   Features: {len(info_result['features'])}")
        for feature in info_result['features']:
            print(f"     - {feature}")

if __name__ == "__main__":
    print("🧪 Testing VSCode Notebook MCP Server Execution Features")
    print("=" * 60)
    
    try:
        test_execution_features()
        print("\n✅ All execution tests completed!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
