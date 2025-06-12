# VSCode Notebook MCP Server

A production-ready Model Context Protocol (MCP) server specifically designed for seamless integration with VSCode Python notebooks. This server provides comprehensive notebook operations while maintaining security, reliability, and performance.

## 🎯 Key Features

### ✅ VSCode Native Compatibility
- **Full VSCode Integration**: Works seamlessly with VSCode's native notebook interface
- **Local File Operations**: Direct manipulation of `.ipynb` files without external dependencies
- **Kernel Integration**: Supports all Python kernels available in your VSCode environment
- **Real-time Execution**: Execute cells and see results immediately in your workflow

### 🔒 Enterprise-Grade Security
- **Path Validation**: Strict directory access controls with whitelist-based security
- **Input Sanitization**: Comprehensive validation of all user inputs and file paths
- **Safe Execution**: Sandboxed code execution with configurable timeouts
- **Audit Logging**: Complete operation logging for security and debugging

### 🏗️ Modern Architecture
- **Type Safety**: Full type hints for better IDE support and error catching
- **Async Support**: Proper async/await patterns for optimal performance
- **Error Handling**: Comprehensive error handling with detailed feedback
- **Resource Management**: Automatic cleanup of kernels and resources

### 📦 Standards Compliance
- **UV Package Manager**: Modern Python packaging with `uv` support
- **Hatchling Build**: Fast, reliable builds with hatchling
- **Code Quality**: Black, Ruff, and MyPy integration for code quality
- **Testing**: Comprehensive test suite with pytest

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- VSCode with Python extension
- `uv` package manager (recommended) or `pip`

### Installation

#### Using UV (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/your-org/vscode-notebook-mcp-server.git
cd vscode-notebook-mcp-server

# Install dependencies
uv sync

# Run the server
uv run vscode-notebook-mcp-server
```

#### Using Pip

```bash
# Clone the repository
git clone https://github.com/your-org/vscode-notebook-mcp-server.git
cd vscode-notebook-mcp-server

# Install in development mode
pip install -e .

# Run the server
vscode-notebook-mcp-server
```

### Configuration

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "vscode-notebook": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/vscode-notebook-mcp-server",
        "run",
        "vscode-notebook-mcp-server"
      ],
      "env": {
        "ALLOWED_DIRS": "/path/to/your/notebooks:/another/path"
      }
    }
  }
}
```

Or using direct execution:

```json
{
  "mcpServers": {
    "vscode-notebook": {
      "command": "vscode-notebook-mcp-server",
      "args": ["--allowed-dirs", "/path/to/your/notebooks"],
      "env": {}
    }
  }
}
```

## 🛠️ Available Tools

### 📂 File Operations

#### `list_notebooks(directory: str = ".") -> Dict[str, Any]`
List all notebook files in a directory with metadata.

```python
# Example response
{
  "success": true,
  "directory": "/path/to/notebooks",
  "count": 3,
  "notebooks": [
    {
      "path": "/path/to/notebooks/analysis.ipynb",
      "name": "analysis.ipynb",
      "size": 15420,
      "modified": "2025-01-12T21:30:00"
    }
  ]
}
```

#### `read_notebook(notebook_path: str) -> Dict[str, Any]`
Read and analyze a complete notebook file.

#### `create_notebook(notebook_path: str, title: str = "New Notebook") -> Dict[str, Any]`
Create a new notebook with proper VSCode-compatible metadata.

#### `backup_notebook(notebook_path: str) -> Dict[str, Any]`
Create a timestamped backup of a notebook.

### 📝 Cell Operations

#### `add_cell(notebook_path: str, cell_type: str, content: str, index: Optional[int] = None) -> Dict[str, Any]`
Add a new cell to a notebook.
- **cell_type**: `"code"`, `"markdown"`, or `"raw"`
- **index**: Position to insert (default: append)

#### `modify_cell(notebook_path: str, index: int, content: str) -> Dict[str, Any]`
Modify the content of an existing cell.

#### `delete_cell(notebook_path: str, index: int) -> Dict[str, Any]`
Remove a cell from the notebook.

#### `get_cell(notebook_path: str, index: int) -> Dict[str, Any]`
Retrieve detailed information about a specific cell.

#### `move_cell(notebook_path: str, from_index: int, to_index: int) -> Dict[str, Any]`
Move a cell to a different position.

### ⚡ Execution Operations

#### `execute_cell(notebook_path: str, cell_index: int, timeout: Optional[int] = None) -> Dict[str, Any]`
Execute a single code cell and capture outputs in real-time.

```python
# Example response
{
  "success": true,
  "cell_index": 0,
  "execution_count": 1,
  "execution_time": 0.125,
  "outputs": [
    {
      "output_type": "stream",
      "name": "stdout", 
      "text": "Result: 15\n"
    }
  ],
  "message": "Successfully executed cell 0"
}
```

#### `execute_all_cells(notebook_path: str, timeout: Optional[int] = None, stop_on_error: bool = False) -> Dict[str, Any]`
Execute all code cells in the notebook sequentially with comprehensive error handling.

#### `execute_cells_range(notebook_path: str, start_index: int, end_index: int, timeout: Optional[int] = None, stop_on_error: bool = False) -> Dict[str, Any]`
Execute a specific range of cells (inclusive indices).

#### `execute_code_snippet(notebook_path: str, code: str, timeout: Optional[int] = None) -> Dict[str, Any]`
Execute arbitrary code without modifying the notebook file.

#### `restart_kernel(notebook_path: str) -> Dict[str, Any]`
Restart the Jupyter kernel for a notebook.

#### `get_kernel_status(notebook_path: str) -> Dict[str, Any]`
Get the current status of a notebook's kernel.

#### `interrupt_kernel(notebook_path: str) -> Dict[str, Any]`
Interrupt a running kernel execution.

### 🔍 Analysis Operations

#### `search_cells(notebook_path: str, search_term: str, case_sensitive: bool = False) -> Dict[str, Any]`
Search for content across all cells.

#### `get_notebook_statistics(notebook_path: str) -> Dict[str, Any]`
Get comprehensive statistics about the notebook.

#### `analyze_dependencies(notebook_path: str) -> Dict[str, Any]`
Analyze Python imports and dependencies used in the notebook.

### 🔄 Conversion Operations

#### `export_to_python(notebook_path: str, output_path: Optional[str] = None) -> Dict[str, Any]`
Export notebook to a Python script.

#### `export_to_markdown(notebook_path: str, output_path: Optional[str] = None) -> Dict[str, Any]`
Export notebook to Markdown format.

#### `import_from_python(python_path: str, notebook_path: str) -> Dict[str, Any]`
Convert a Python script to a notebook.

### 🔧 Utility Operations

#### `list_kernels() -> Dict[str, Any]`
List all available Python kernels.

#### `validate_notebook(notebook_path: str) -> Dict[str, Any]`
Validate notebook format and structure.

#### `get_server_info() -> Dict[str, Any]`
Get server status and configuration.

#### `list_allowed_directories() -> Dict[str, Any]`
List directories accessible to the server.

## 🔧 Configuration Options

### Environment Variables

- `ALLOWED_DIRS`: Colon-separated list of allowed directories
- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `MAX_EXECUTION_TIME`: Default timeout for cell execution (seconds)
- `BACKUP_ENABLED`: Enable automatic backups (`true`/`false`)

### Command Line Arguments

```bash
vscode-notebook-mcp-server --help
```

Options:
- `--allowed-dirs DIR [DIR ...]`: Specify allowed directories
- `--log-level LEVEL`: Set logging level
- `--backup/--no-backup`: Enable/disable automatic backups
- `--max-execution-time SECONDS`: Set default execution timeout
- `--config FILE`: Load configuration from file

## 🛡️ Security Features

### Directory Access Control
- Whitelist-based directory access
- Path traversal prevention
- Symlink resolution and validation

### Input Validation
- Strict parameter validation
- File extension verification
- Content size limits

### Execution Safety
- Kernel isolation
- Configurable timeouts
- Resource cleanup

## 🧪 Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/your-org/vscode-notebook-mcp-server.git
cd vscode-notebook-mcp-server
uv sync --dev

# Run tests
uv run pytest

# Code formatting
uv run black .
uv run ruff check .

# Type checking
uv run mypy .
```

### Running Tests

```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest -m "not integration"

# With coverage
uv run pytest --cov=vscode_notebook_mcp_server

# Specific test
uv run pytest tests/test_notebook_operations.py::test_create_notebook
```

### Project Structure

```
vscode-notebook-mcp-server/
├── src/vscode_notebook_mcp_server/
│   ├── __init__.py
│   ├── main.py              # Entry point and CLI
│   ├── server.py            # Main MCP server implementation
│   ├── security.py          # Security and access control
│   ├── notebook_manager.py  # Notebook file operations
│   ├── kernel_manager.py    # Kernel execution management
│   ├── converters.py        # Format conversion utilities
│   └── exceptions.py        # Custom exceptions
├── tests/
│   ├── test_notebook_operations.py
│   ├── test_security.py
│   ├── test_execution.py
│   └── fixtures/
├── pyproject.toml
├── README.md
└── LICENSE
```

## 📊 Performance

- **Startup Time**: < 1 second
- **Memory Usage**: ~50MB base + kernel overhead
- **Concurrent Operations**: Supports multiple notebook operations
- **File Size Limits**: Configurable (default: 100MB per notebook)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`uv run pytest`)
6. Format code (`uv run black . && uv run ruff check .`)
7. Commit changes (`git commit -m 'Add amazing feature'`)
8. Push to branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Model Context Protocol (MCP) team for the excellent framework
- Jupyter Project for the notebook format specification
- VSCode team for the outstanding notebook support
- The Python community for the amazing ecosystem

## 📞 Support

- 📚 [Documentation](https://github.com/your-org/vscode-notebook-mcp-server#readme)
- 🐛 [Bug Reports](https://github.com/your-org/vscode-notebook-mcp-server/issues)
- 💬 [Discussions](https://github.com/your-org/vscode-notebook-mcp-server/discussions)
- 📧 [Email Support](mailto:support@example.com)

---

**Made with ❤️ for the VSCode and AI community**
