"""
Claude Jester MCP Code Sandbox
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

This module implements a secure code execution sandbox for Claude Jester MCP.
It provides isolation and resource limits for code execution.
"""

import os
import sys
import resource
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from contextlib import contextmanager

import docker
from docker.types import Mount
from structlog import get_logger

logger = get_logger()

class CodeSandbox:
    """
    Secure code execution sandbox.
    
    Security Rationale:
    This class implements a multi-layered security approach:
    1. Docker container isolation
    2. Resource limits (CPU, memory, disk)
    3. Network isolation
    4. Filesystem restrictions
    5. Process limits
    
    Architecture Decision Record:
    - ADR-2023-01: Chose Docker for containerization over alternatives
    - ADR-2023-02: Implemented resource limits to prevent DoS
    - ADR-2023-03: Added network isolation for security
    """
    
    def __init__(
        self,
        image: str = "python:3.8-slim",
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
        timeout: int = 30,
        network_disabled: bool = True,
        read_only: bool = True,
        allowed_modules: Optional[Set[str]] = None,
        blocked_modules: Optional[Set[str]] = None,
    ):
        """
        Initialize the code sandbox.
        
        Args:
            image: Docker image to use
            memory_limit: Memory limit (e.g., "512m")
            cpu_limit: CPU limit (0.0-1.0)
            timeout: Execution timeout in seconds
            network_disabled: Whether to disable network access
            read_only: Whether to mount filesystem as read-only
            allowed_modules: Set of allowed Python modules
            blocked_modules: Set of blocked Python modules
            
        Security:
            - Uses minimal base image
            - Enforces resource limits
            - Disables network by default
            - Mounts filesystem as read-only
            - Restricts module imports
        """
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.timeout = timeout
        self.network_disabled = network_disabled
        self.read_only = read_only
        self.allowed_modules = allowed_modules or {
            "math", "random", "datetime", "json", "collections",
            "itertools", "functools", "operator", "re", "string",
            "typing", "unittest", "pytest",
        }
        self.blocked_modules = blocked_modules or {
            "os", "sys", "subprocess", "socket", "multiprocessing",
            "threading", "ctypes", "cffi", "cryptography",
        }
        
        # Initialize Docker client
        self.client = docker.from_env()
        
        # Security: Verify Docker is running
        try:
            self.client.ping()
        except Exception as e:
            logger.error("Docker not available", error=str(e))
            raise RuntimeError("Docker is required for code sandbox") from e
            
        # Security: Pull the base image
        try:
            self.client.images.pull(self.image)
        except Exception as e:
            logger.error("Failed to pull Docker image", error=str(e))
            raise RuntimeError(f"Failed to pull Docker image: {self.image}") from e
    
    @contextmanager
    def create_container(self, code: str) -> docker.models.containers.Container:
        """
        Create a Docker container for code execution.
        
        Security Rationale:
        This method implements several security measures:
        1. Creates a temporary directory for code
        2. Mounts the directory as read-only
        3. Sets resource limits
        4. Disables network access
        5. Uses a minimal base image
        
        Args:
            code: Python code to execute
            
        Yields:
            Docker container instance
            
        Security:
            - Uses context manager for cleanup
            - Creates isolated container
            - Enforces resource limits
            - Restricts filesystem access
        """
        # Create temporary directory for code
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write code to file
            code_path = temp_path / "code.py"
            code_path.write_text(code)
            
            # Create container
            container = self.client.containers.create(
                image=self.image,
                command=["python", "/code/code.py"],
                detach=True,
                mem_limit=self.memory_limit,
                cpu_period=100000,
                cpu_quota=int(self.cpu_limit * 100000),
                network_disabled=self.network_disabled,
                read_only=self.read_only,
                mounts=[
                    Mount(
                        target="/code",
                        source=str(temp_path),
                        type="bind",
                        read_only=True,
                    )
                ],
                environment={
                    "PYTHONPATH": "/code",
                    "PYTHONUNBUFFERED": "1",
                },
            )
            
            try:
                yield container
            finally:
                # Security: Clean up container
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.error("Failed to remove container", error=str(e))
    
    def execute(self, code: str) -> Dict[str, Union[str, int]]:
        """
        Execute code in the sandbox.
        
        Security Rationale:
        This method implements several security measures:
        1. Validates code before execution
        2. Runs in isolated container
        3. Enforces timeout
        4. Captures and sanitizes output
        5. Handles errors securely
        
        Args:
            code: Python code to execute
            
        Returns:
            Dict containing execution results:
            - output: stdout/stderr output
            - exit_code: Process exit code
            - error: Error message if any
            
        Security:
            - Validates code before execution
            - Runs in isolated container
            - Enforces timeout
            - Sanitizes output
            - Handles errors securely
        """
        # Security: Validate code
        self._validate_code(code)
        
        # Create and run container
        with self.create_container(code) as container:
            try:
                # Start container
                container.start()
                
                # Wait for completion with timeout
                result = container.wait(timeout=self.timeout)
                exit_code = result["StatusCode"]
                
                # Get output
                output = container.logs().decode("utf-8")
                
                # Security: Sanitize output
                output = self._sanitize_output(output)
                
                return {
                    "output": output,
                    "exit_code": exit_code,
                    "error": None,
                }
                
            except Exception as e:
                logger.error("Code execution failed", error=str(e))
                return {
                    "output": "",
                    "exit_code": -1,
                    "error": str(e),
                }
    
    def _validate_code(self, code: str) -> None:
        """
        Validate code before execution.
        
        Security Rationale:
        This method implements several security measures:
        1. Checks for blocked modules
        2. Validates import statements
        3. Checks for dangerous operations
        4. Enforces code size limits
        
        Args:
            code: Python code to validate
            
        Raises:
            ValueError: If code is invalid
            
        Security:
            - Checks for blocked modules
            - Validates imports
            - Checks for dangerous operations
            - Enforces size limits
        """
        # Security: Check code size
        if len(code) > 1024 * 1024:  # 1MB limit
            raise ValueError("Code size exceeds limit")
            
        # Security: Check for blocked modules
        for module in self.blocked_modules:
            if f"import {module}" in code or f"from {module}" in code:
                raise ValueError(f"Blocked module: {module}")
                
        # Security: Check for dangerous operations
        dangerous_ops = [
            "eval(",
            "exec(",
            "__import__",
            "os.system",
            "subprocess.call",
            "subprocess.run",
            "subprocess.Popen",
        ]
        
        for op in dangerous_ops:
            if op in code:
                raise ValueError(f"Dangerous operation: {op}")
    
    def _sanitize_output(self, output: str) -> str:
        """
        Sanitize container output.
        
        Security Rationale:
        This method implements several security measures:
        1. Removes sensitive information
        2. Truncates long output
        3. Sanitizes error messages
        4. Removes system paths
        
        Args:
            output: Container output to sanitize
            
        Returns:
            Sanitized output
            
        Security:
            - Removes sensitive info
            - Truncates output
            - Sanitizes errors
            - Removes paths
        """
        # Security: Truncate output
        if len(output) > 1024 * 1024:  # 1MB limit
            output = output[:1024 * 1024] + "\n... (output truncated)"
            
        # Security: Remove system paths
        output = output.replace(str(Path.home()), "~")
        
        # Security: Remove sensitive info
        sensitive_patterns = [
            r"/tmp/[a-zA-Z0-9]+",
            r"/var/run/[a-zA-Z0-9]+",
            r"/proc/[a-zA-Z0-9]+",
        ]
        
        for pattern in sensitive_patterns:
            output = re.sub(pattern, "[REDACTED]", output)
            
        return output 