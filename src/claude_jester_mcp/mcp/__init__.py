"""
Module: mcp/__init__.py
Purpose: MCP package initialization
Author: Enterprise Security Team
Version: 2.1.0

Security Classification:
- CONFIDENTIAL: Contains security enforcement mechanisms
- COMPLIANCE: PCI-DSS 4.0, SOC2, GDPR Article 32
"""

from .server import MCPServer

__all__ = ["MCPServer"] 