"""
Claude Jester MCP Server Package
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

This package contains the MCP server implementation for Claude Jester MCP.
It provides the interface between Claude Desktop and the code execution engine.
"""

from .server import MCPServer

__all__ = ["MCPServer"] 