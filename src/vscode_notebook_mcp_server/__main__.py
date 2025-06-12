#!/usr/bin/env python3
"""
Entry point for running the VSCode Notebook MCP Server as a module.

Usage:
    python -m vscode_notebook_mcp_server
    python -m vscode_notebook_mcp_server --debug
    python -m vscode_notebook_mcp_server --allowed-dirs /path/to/notebooks
"""

from .server import main

if __name__ == "__main__":
    main()
