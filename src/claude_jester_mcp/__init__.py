"""
Claude Jester MCP Package
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

This package provides a secure, enterprise-grade interface for Claude Desktop
code execution and testing capabilities.
"""

__version__ = "2.1.0"
__author__ = "Enterprise Security Team"
__security_classification__ = "CONFIDENTIAL"

# Import key components for easier access
from .cli import app as cli_app
from .core.executor import CodeExecutor
from .core.learning_system import LearningSystem
from .core.quantum_debugger import QuantumDebugger
from .mcp.server import MCPServer
from .monitoring.monitoring_dashboard import MonitoringDashboard

__all__ = [
    "cli_app",
    "CodeExecutor",
    "LearningSystem",
    "QuantumDebugger",
    "MCPServer",
    "MonitoringDashboard",
] 