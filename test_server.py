#!/usr/bin/env python3
"""
Test script for the VSCode Notebook MCP Server.
This script demonstrates the key functionality of the server.
"""

import os
import tempfile
import json
from pathlib import Path

# Test the server components directly
from src.vscode_notebook_mcp_server import (
    SecurityManager,
    NotebookManager,
    CellManager,
    VSCodeNotebookMCPServer
)

def test_basic_functionality():
    """Test basic server functionality."""
    print("🧪 Testing VSCode Notebook MCP Server")
    print("=" * 50)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Initialize components
        security_manager = SecurityManager([temp_dir])
        notebook_manager = NotebookManager(security_manager)
        cell_manager = CellManager(notebook_manager)
        
        # Test notebook creation
        notebook_path = os.path.join(temp_dir, "test_notebook.ipynb")
        print(f"\n📝 Creating notebook: {notebook_path}")
        
        try:
            notebook = notebook_manager.create_new_notebook(
                notebook_path, 
                "Test Notebook", 
                "python"
            )
            print(f"✅ Successfully created notebook with {len(notebook.cells)} cells")
        except Exception as e:
            print(f"❌ Failed to create notebook: {e}")
            return False
        
        # Test adding cells
        print("\n🔄 Testing cell operations...")
        
        try:
            # Add a markdown cell
            result = cell_manager.add_cell(
                notebook_path, 
                "markdown", 
                "# Test Markdown Cell\nThis is a test markdown cell."
            )
            print(f"✅ Added markdown cell: {result['success']}")
            
            # Add a code cell
            result = cell_manager.add_cell(
                notebook_path, 
                "code", 
                "print('Hello from VSCode Notebook MCP Server!')\nx = 42\nprint(f'The answer is {x}')"
            )
            print(f"✅ Added code cell: {result['success']}")
            
            # Get notebook info
            info = notebook_manager.get_notebook_info(notebook_path)
            print(f"✅ Notebook now has {info['cell_count']} cells")
            
        except Exception as e:
            print(f"❌ Cell operations failed: {e}")
            return False
        
        # Test search functionality
        print("\n🔍 Testing search functionality...")
        
        try:
            search_result = cell_manager.search_cells(
                notebook_path, 
                "Test", 
                case_sensitive=False
            )
            print(f"✅ Search found {search_result['cells_with_matches']} cells with matches")
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return False
        
        # Test export functionality
        print("\n📤 Testing export functionality...")
        
        try:
            python_path = notebook_manager.export_to_python(notebook_path)
            if os.path.exists(python_path):
                print(f"✅ Successfully exported to Python: {python_path}")
                
                # Show first few lines of exported file
                with open(python_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]
                    print("📄 First 10 lines of exported Python file:")
                    for i, line in enumerate(lines, 1):
                        print(f"   {i:2d}: {line.rstrip()}")
            else:
                print("❌ Export file not found")
                return False
                
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False
        
        # Test security validation
        print("\n🔒 Testing security features...")
        
        try:
            # Test valid path
            valid_path = security_manager.validate_notebook_path(notebook_path)
            print(f"✅ Valid path accepted: {valid_path}")
            
            # Test invalid path (should raise SecurityError)
            try:
                invalid_path = "/etc/passwd"
                security_manager.validate_notebook_path(invalid_path)
                print("❌ Security validation failed - invalid path accepted")
                return False
            except Exception:
                print("✅ Security validation working - invalid path rejected")
                
        except Exception as e:
            print(f"❌ Security test failed: {e}")
            return False
        
        print("\n🎉 All tests passed successfully!")
        print("\n📊 Test Summary:")
        print(f"   ✅ Notebook creation: Working")
        print(f"   ✅ Cell operations: Working") 
        print(f"   ✅ Search functionality: Working")
        print(f"   ✅ Export functionality: Working")
        print(f"   ✅ Security validation: Working")
        
        return True

def test_server_initialization():
    """Test server initialization."""
    print("\n🚀 Testing server initialization...")
    
    try:
        # Create server instance
        server = VSCodeNotebookMCPServer(debug=True)
        print("✅ Server initialized successfully")
        
        # Test that MCP server is properly configured
        if hasattr(server, 'mcp') and server.mcp is not None:
            print("✅ MCP server component initialized")
        else:
            print("❌ MCP server component not initialized")
            return False
            
        print("✅ Server initialization test passed")
        return True
        
    except Exception as e:
        print(f"❌ Server initialization failed: {e}")
        return False

def show_usage_example():
    """Show usage example for the server."""
    print("\n📖 Usage Example:")
    print("=" * 50)
    
    example_commands = [
        "# Start the server with default settings",
        "python -m vscode_notebook_mcp_server",
        "",
        "# Start with specific allowed directories",
        "python -m vscode_notebook_mcp_server --allowed-dirs /path/to/notebooks /another/path",
        "",
        "# Start with debug logging",
        "python -m vscode_notebook_mcp_server --debug",
        "",
        "# Or run the server directly",
        "python src/vscode_notebook_mcp_server/server.py --allowed-dirs ./notebooks --debug"
    ]
    
    for cmd in example_commands:
        if cmd.startswith("#"):
            print(f"\033[90m{cmd}\033[0m")  # Gray comments
        elif cmd == "":
            print()
        else:
            print(f"\033[92m{cmd}\033[0m")  # Green commands

def main():
    """Main test function."""
    print("🧪 VSCode Notebook MCP Server - Test Suite")
    print("=" * 60)
    
    # Run basic functionality tests
    if not test_basic_functionality():
        print("\n❌ Basic functionality tests failed!")
        return 1
    
    # Test server initialization
    if not test_server_initialization():
        print("\n❌ Server initialization tests failed!")
        return 1
    
    # Show usage example
    show_usage_example()
    
    print("\n🎉 All tests completed successfully!")
    print("\nThe VSCode Notebook MCP Server is ready for use!")
    
    return 0

if __name__ == "__main__":
    exit(main())
