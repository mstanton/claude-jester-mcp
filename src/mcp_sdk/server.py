"""
MCP SDK Server
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

This module implements the core MCP server functionality.
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from .types import (
    Tool, TextContent,
    CallToolRequest, CallToolResult,
    ListToolsRequest, ListToolsResult
)

T = TypeVar('T')
R = TypeVar('R')

def tool_handler(func: Callable[..., R]) -> Callable[..., R]:
    """Decorator for tool handlers."""
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> R:
        return await func(*args, **kwargs)
    return wrapper

class Server:
    """MCP server implementation."""
    
    def __init__(self, name: str):
        """Initialize the server."""
        self.name = name
        self.logger = logging.getLogger(f"mcp_server.{name}")
        self._tools: List[Tool] = []
        self._tool_handlers: Dict[str, Callable] = {}
        self._list_tools_handler: Optional[Callable] = None
    
    def list_tools(self) -> Callable[[Callable[..., ListToolsResult]], Callable[..., ListToolsResult]]:
        """Decorator for registering the list tools handler."""
        def decorator(func: Callable[..., ListToolsResult]) -> Callable[..., ListToolsResult]:
            self._list_tools_handler = func
            return func
        return decorator
    
    def call_tool(self) -> Callable[[Callable[..., CallToolResult]], Callable[..., CallToolResult]]:
        """Decorator for registering tool handlers."""
        def decorator(func: Callable[..., CallToolResult]) -> Callable[..., CallToolResult]:
            @wraps(func)
            async def wrapper(name: str, arguments: Dict[str, Any]) -> CallToolResult:
                return await func(name, arguments)
            return wrapper
        return decorator
    
    async def handle_list_tools(self) -> ListToolsResult:
        """Handle list tools request."""
        if self._list_tools_handler:
            return await self._list_tools_handler()
        return ListToolsResult(tools=self._tools)
    
    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle tool call request."""
        if name in self._tool_handlers:
            return await self._tool_handlers[name](name, arguments)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )],
            isError=True
        )
    
    async def run(self):
        """Run the server."""
        self.logger.info(f"Starting {self.name} server...")
        
        while True:
            try:
                # Read request from stdin
                request_line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not request_line:
                    break
                
                request = json.loads(request_line)
                request_type = request.get("type")
                
                if request_type == "list_tools":
                    result = await self.handle_list_tools()
                elif request_type == "call_tool":
                    result = await self.handle_call_tool(
                        request["name"],
                        request["arguments"]
                    )
                else:
                    result = CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"Unknown request type: {request_type}"
                        )],
                        isError=True
                    )
                
                # Write response to stdout
                response = json.dumps(result.__dict__)
                print(response, flush=True)
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON: {e}")
                continue
            except Exception as e:
                self.logger.error(f"Error handling request: {e}")
                continue 