"""
MCP SDK Types
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

This module defines the core types used by the MCP SDK.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

@dataclass
class TextContent:
    """Text content for tool responses."""
    type: str = "text"
    text: str = ""

@dataclass
class Tool:
    """Tool definition for the MCP server."""
    name: str
    description: str
    inputSchema: Dict[str, Any]

@dataclass
class CallToolRequest:
    """Request to call a tool."""
    name: str
    arguments: Dict[str, Any]

@dataclass
class CallToolResult:
    """Result of a tool call."""
    content: List[TextContent]
    isError: bool = False

@dataclass
class ListToolsRequest:
    """Request to list available tools."""
    pass

@dataclass
class ListToolsResult:
    """Result of listing available tools."""
    tools: List[Tool] 