"""
MCP SDK
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

This package provides the core MCP SDK functionality for Claude Jester.
"""

from .server import Server
from .types import (
    Tool, TextContent,
    CallToolRequest, CallToolResult,
    ListToolsRequest, ListToolsResult
)

__version__ = "0.1.0"
__all__ = [
    "Server",
    "Tool",
    "TextContent",
    "CallToolRequest",
    "CallToolResult",
    "ListToolsRequest",
    "ListToolsResult"
] 