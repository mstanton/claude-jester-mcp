#!/usr/bin/env python3
"""
Core Code Execution Engine
Handles safe, monitored Python code execution with multiple security strategies
"""

import asyncio
import ast
import time
import json
import hashlib
import multiprocess as mp
import traceback
import sys
import io
import os
import signal
import resource
import psutil
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from pathlib import Path

# Try to import optional dependencies
try:
    from RestrictedPython import compile_restricted, safe_globals
    HAS_RESTRICTED_PYTHON = True
except ImportError:
    HAS_RESTRICTED_PYTHON = False

try:
    from asteval import Interpreter
    HAS_ASTEVAL = True
except ImportError:
    HAS_ASTEVAL = False

class ExecutionStatus(Enum):
    """Execution result status"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    MEMORY_EXCEEDED = "memory_exceeded"
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMITED = "rate_limited"

@dataclass
class ExecutionResult:
    """Comprehensive execution result with metadata"""
    status: ExecutionStatus
    output: str
    error: str
    execution_time_ms: float
    memory_used_bytes: int
    cpu_percent: float
    suggestions: List[str]
    security_level: str
    code_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.status == ExecutionStatus.SUCCESS,
            "status": self.status.value,
            "output": self.output[:1000] if self.output else "",
            "error": self.error[:1000] if self.error else "",
            "metrics": {
                "time_ms": round(self.execution_time_ms, 2),
                "memory_kb": round(self.memory_used_bytes / 1024, 2),
                "cpu_percent": round(self.cpu_percent, 2)
            },
            "suggestions": self.suggestions[:5],
            "security_level": self.security_level,
            "code_hash": self.code_hash[:8]
        }

class SecurityStrategy:
    """Base class for security strategies"""
    
    def can_handle(self, code: str) -> bool:
        """Check if this strategy can handle the given code"""
        raise NotImplementedError
    
    def get_security_level(self) -> str:
        """Get the security level name"""
        raise NotImplementedError
    
    async def execute(self, code: str, timeout: float) -> Tuple[str, str, bool]:
        """Execute code and return (output, error, success)"""
        raise NotImplementedError

class RestrictedPythonStrategy(SecurityStrategy):
    """RestrictedPython-based execution strategy"""
    
    def can_handle(self, code: str) -> bool:
        """Check if RestrictedPython is available and code is suitable"""
        return HAS_RESTRICTED_PYTHON and self._is_safe_for_restricted(code)
    
    def get_security_level(self) -> str:
        return "restricted_python"
    
    def _is_safe_for_restricted(self, code: str) -> bool:
        """Check if code is suitable for RestrictedPython"""
        try:
            ast.parse(code)
            # Check for dangerous operations
            dangerous_patterns = ['import os', 'import sys', 'open(', 'file(']
            return not any(pattern in code for pattern in dangerous_patterns)
        except:
            return False
    
    async def execute(self, code: str, timeout: float) -> Tuple[str, str, bool]:
        """Execute using RestrictedPython"""
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()
        
        try:
            # Compile with restrictions
            compiled = compile_restricted(code, '<string>', 'exec')
            
            if compiled.errors:
                return "", str(compiled.errors), False
            
            # Create safe environment
            restricted_globals = safe_globals.copy()
            restricted_globals['__builtins__']['print'] = lambda *args, **kwargs: print(*args, **kwargs, file=output_buffer)
            
            # Execute with timeout
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                exec(compiled.code, restricted_globals)
            
            return output_buffer.getvalue(), error_buffer.getvalue(), True
            
        except Exception as e:
            return output_buffer.getvalue(), f"{type(e).__name__}: {str(e)}", False

class ASTEvalStrategy(SecurityStrategy):
    """ASTeval-based execution strategy for mathematical operations"""
    
    def can_handle(self, code: str) -> bool:
        """Check if ASTeval is available and code is mathematical"""
        return HAS_ASTEVAL and self._is_mathematical(code)
    
    def get_security_level(self) -> str:
        return "asteval"
    
    def _is_mathematical(self, code: str) -> bool:
        """Check if code is primarily mathematical"""
        try:
            tree = ast.parse(code)
            # Simple heuristic: no imports, function definitions, or classes
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
                    return False
            return True
        except:
            return False
    
    async def execute(self, code: str, timeout: float) -> Tuple[str, str, bool]:
        """Execute using ASTeval"""
        output_buffer = io.StringIO()
        
        try:
            # Create interpreter with restrictions
            aeval = Interpreter(
                use_numpy=False,
                max_time=timeout,
                writer=output_buffer
            )
            
            # Add safe print function
            def safe_print(*args, **kwargs):
                print(*args, **kwargs, file=output_buffer)
            
            aeval.symtable['print'] = safe_print
            
            # Execute
            aeval(code)
            
            if aeval.error:
                return output_buffer.getvalue(), str(aeval.error), False
            
            return output_buffer.getvalue(), "", True
            
        except Exception as e:
            return output_buffer.getvalue(), str(e), False

class SubprocessStrategy(SecurityStrategy):
    """Subprocess-based execution with maximum isolation"""
    
    def can_handle(self, code: str) -> bool:
        """Subprocess can handle any code"""
        return True
    
    def get_security_level(self) -> str:
        return "subprocess"
    
    async def execute(self, code: str, timeout: float) -> Tuple[str, str, bool]:
        """Execute in isolated subprocess"""
        
        def run_code_isolated(code_str: str, queue: mp.Queue):
            """Run code in isolated process"""
            try:
                # Set resource limits
                max_memory = 256 * 1024 * 1024  # 256MB
                resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
                resource.setrlimit(resource.RLIMIT_CPU, (int(timeout), int(timeout)))
                
                # Capture output
                output_buffer = io.StringIO()
                error_buffer = io.StringIO()
                
                with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                    # Create restricted globals
                    restricted_globals = {
                        '__builtins__': {
                            'print': print,
                            'len': len,
                            'range': range,
                            'str': str,
                            'int': int,
                            'float': float,
                            'list': list,
                            'dict': dict,
                            'tuple': tuple,
                            'set': set,
                            'min': min,
                            'max': max,
                            'sum': sum,
                            'abs': abs,
                            'round': round,
                            'sorted': sorted,
                            'enumerate': enumerate,
                            'zip': zip,
                            'map': map,
                            'filter': filter,
                            'True': True,
                            'False': False,
                            'None': None,
                        }
                    }
                    
                    exec(code_str, restricted_globals)
                
                queue.put({
                    'success': True,
                    'output': output_buffer.getvalue(),
                    'error': error_buffer.getvalue()
                })
                
            except Exception as e:
                queue.put({
                    'success': False,
                    'output': '',
                    'error': f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                })
        
        # Create queue for communication
        queue = mp.Queue()
        
        # Create and start process
        process = mp.Process(target=run_code_isolated, args=(code, queue))
        process.start()
        
        # Wait for completion with timeout
        process.join(timeout=timeout)
        
        if process.is_alive():
            # Timeout occurred
            process.terminate()
            process.join()
            return "", f"Code execution timed out after {timeout} seconds", False
        
        # Get result
        try:
            result = queue.get_nowait()
            return result['output'], result['error'], result['success']
        except:
            return "", "Failed to retrieve execution result", False

class BasicSandboxStrategy(SecurityStrategy):
    """Basic sandboxed execution for simple code"""
    
    def can_handle(self, code: str) -> bool:
        """Basic sandbox can handle simple code"""
        return self._is_simple_code(code)
    
    def get_security_level(self) -> str:
        return "basic"
    
    def _is_simple_code(self, code: str) -> bool:
        """Check if code is simple enough for basic sandbox"""
        try:
            tree = ast.parse(code)
            # Allow only basic operations
            allowed_nodes = (
                ast.Expression, ast.Assign, ast.AugAssign, ast.For, ast.While, ast.If,
                ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Name, ast.Constant,
                ast.List, ast.Dict, ast.Tuple, ast.Set
            )
            for node in ast.walk(tree):
                if not isinstance(node, allowed_nodes):
                    return False
            return True
        except:
            return False
    
    async def execute(self, code: str, timeout: float) -> Tuple[str, str, bool]:
        """Execute in basic sandbox"""
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()
        
        try:
            # Create minimal safe environment
            safe_builtins = {
                'print': lambda *args, **kwargs: print(*args, **kwargs, file=output_buffer),
                'len': len,
                'range': range,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'True': True,
                'False': False,
                'None': None,
            }
            
            safe_globals = {'__builtins__': safe_builtins}
            
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                exec(code, safe_globals)
            
            return output_buffer.getvalue(), error_buffer.getvalue(), True
            
        except Exception as e:
            return output_buffer.getvalue(), f"{type(e).__name__}: {str(e)}", False

class CodeExecutor:
    """Main code executor with multiple security strategies"""
    
    def __init__(self, timeout: float = 10.0, memory_limit_mb: int = 256):
        self.timeout = timeout
        self.memory_limit = memory_limit_mb * 1024 * 1024
        self.execution_cache = {}
        
        # Initialize security strategies in order of preference
        self.strategies = [
            RestrictedPythonStrategy(),
            ASTEvalStrategy(), 
            BasicSandboxStrategy(),
            SubprocessStrategy()  # Fallback strategy
        ]
        
        # Filter available strategies
        self.available_strategies = [s for s in self.strategies if self._test_strategy(s)]
        
        if not self.available_strategies:
            raise RuntimeError("No execution strategies available")
    
    def _test_strategy(self, strategy: SecurityStrategy) -> bool:
        """Test if a strategy is available and working"""
        try:
            # Test with simple code
            test_code = "print('test')"
            if hasattr(strategy, 'can_handle') and strategy.can_handle(test_code):
                return True
            return False
        except:
            return False
    
    async def execute_code(self, code: str, description: str = "") -> ExecutionResult:
        """Execute code with comprehensive safety checks and monitoring"""
        
        # Input validation
        if not code or not isinstance(code, str):
            return self._create_error_result("Invalid code input", "INVALID_INPUT")
        
        if len(code) > 50_000:  # 50KB limit
            return self._create_error_result("Code too large", "CODE_TOO_LARGE")
        
        # Generate cache key
        code_hash = hashlib.md5(code.encode()).hexdigest()
        cache_key = f"exec_{code_hash}_{self.timeout}"
        
        # Check cache first
        if cache_key in self.execution_cache:
            cached_result = self.execution_cache[cache_key]
            # Update timestamp but keep other data
            cached_result.code_hash = code_hash
            return cached_result
        
        # Security checks
        security_issues = self._security_check(code)
        if security_issues:
            return self._create_error_result(
                f"Security violation: {'; '.join(security_issues)}",
                "SECURITY_VIOLATION"
            )
        
        # Choose execution strategy
        strategy = self._choose_strategy(code)
        
        # Execute with monitoring
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            output, error, success = await asyncio.wait_for(
                strategy.execute(code, self.timeout),
                timeout=self.timeout
            )
            
            execution_time = (time.time() - start_time) * 1000
            memory_used = self._get_memory_usage() - start_memory
            cpu_percent = self._get_cpu_percent()
            
            status = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILURE
            suggestions = self._generate_suggestions(error, code) if error else []
            
            result = ExecutionResult(
                status=status,
                output=output,
                error=error,
                execution_time_ms=execution_time,
                memory_used_bytes=max(0, memory_used),
                cpu_percent=cpu_percent,
                suggestions=suggestions,
                security_level=strategy.get_security_level(),
                code_hash=code_hash
            )
            
            # Cache successful results
            if status == ExecutionStatus.SUCCESS:
                self.execution_cache[cache_key] = result
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = (time.time() - start_time) * 1000
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                output="",
                error=f"Execution timed out after {self.timeout} seconds",
                execution_time_ms=execution_time,
                memory_used_bytes=0,
                cpu_percent=0,
                suggestions=["Optimize loops or reduce iteration count", "Check for infinite loops"],
                security_level=strategy.get_security_level(),
                code_hash=code_hash
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                output="",
                error=f"Execution failed: {str(e)}",
                execution_time_ms=execution_time,
                memory_used_bytes=0,
                cpu_percent=0,
                suggestions=self._generate_suggestions(str(e), code),
                security_level=strategy.get_security_level(),
                code_hash=code_hash
            )
    
    def _choose_strategy(self, code: str) -> SecurityStrategy:
        """Choose the best execution strategy for the given code"""
        for strategy in self.available_strategies:
            if strategy.can_handle(code):
                return strategy
        
        # Fallback to subprocess (should always be available)
        return self.available_strategies[-1]
    
    def _security_check(self, code: str) -> List[str]:
        """Perform security checks on code"""
        issues = []
        
        # Basic security patterns
        dangerous_patterns = [
            ('import os', 'File system access'),
            ('import sys', 'System access'),
            ('import subprocess', 'Process execution'),
            ('import socket', 'Network access'),
            ('open(', 'File operations'),
            ('eval(', 'Code evaluation'),
            ('exec(', 'Code execution'),
            ('__import__', 'Dynamic imports'),
            ('getattr(', 'Attribute access'),
            ('setattr(', 'Attribute modification'),
            ('globals()', 'Global namespace access'),
            ('locals()', 'Local namespace access'),
        ]
        
        for pattern, description in dangerous_patterns:
            if pattern in code:
                issues.append(f"{description} ({pattern})")
        
        return issues
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes"""
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except:
            return 0
    
    def _get_cpu_percent(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0
    
    def _generate_suggestions(self, error: str, code: str) -> List[str]:
        """Generate helpful suggestions based on error and code"""
        suggestions = []
        
        if "NameError" in error:
            suggestions.append("Check for typos in variable names")
            suggestions.append("Ensure all variables are defined before use")
        elif "SyntaxError" in error:
            suggestions.append("Check syntax: parentheses, colons, and indentation")
            suggestions.append("Verify all strings are properly quoted")
        elif "IndentationError" in error:
            suggestions.append("Use consistent indentation (4 spaces recommended)")
        elif "TypeError" in error:
            suggestions.append("Check that operations match data types")
            suggestions.append("Verify function arguments are correct")
        elif "IndexError" in error:
            suggestions.append("Check list/array bounds before accessing")
            suggestions.append("Verify the container is not empty")
        elif "KeyError" in error:
            suggestions.append("Check dictionary keys exist before accessing")
            suggestions.append("Consider using .get() method with default values")
        elif "ZeroDivisionError" in error:
            suggestions.append("Add checks to prevent division by zero")
        elif "timeout" in error.lower():
            suggestions.append("Optimize loops or reduce iteration count")
            suggestions.append("Check for infinite loops")
        elif "memory" in error.lower():
            suggestions.append("Reduce data size or use generators")
            suggestions.append("Consider processing data in chunks")
        
        # Code-specific suggestions
        if "for" in code and "while" in code:
            suggestions.append("Consider combining or optimizing nested loops")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _create_error_result(self, error_message: str, error_code: str) -> ExecutionResult:
        """Create an error result"""
        return ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output="",
            error=error_message,
            execution_time_ms=0,
            memory_used_bytes=0,
            cpu_percent=0,
            suggestions=[f"Error: {error_code}"],
            security_level="error",
            code_hash=""
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            "available_strategies": [s.get_security_level() for s in self.available_strategies],
            "cache_size": len(self.execution_cache),
            "memory_limit_mb": self.memory_limit / 1024 / 1024,
            "timeout_seconds": self.timeout
        }

# Simple executor for fallback when core components aren't available
class SimpleExecutor:
    """Simplified executor for when advanced features aren't available"""
    
    def __init__(self, timeout: float = 10.0, memory_limit_mb: int = 256):
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb
    
    async def execute_code(self, code: str, description: str = "") -> ExecutionResult:
        """Simple code execution"""
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()
        start_time = time.time()
        
        try:
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                # Create safe globals
                safe_globals = {
                    '__builtins__': {
                        'print': print,
                        'len': len,
                        'range': range,
                        'str': str,
                        'int': int,
                        'float': float,
                        'list': list,
                        'dict': dict,
                        'True': True,
                        'False': False,
                        'None': None,
                    }
                }
                
                exec(code, safe_globals)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=output_buffer.getvalue(),
                error=error_buffer.getvalue(),
                execution_time_ms=execution_time,
                memory_used_bytes=1024,  # Dummy value
                cpu_percent=0.1,  # Dummy value
                suggestions=[],
                security_level="simple",
                code_hash=hashlib.md5(code.encode()).hexdigest()
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                output=output_buffer.getvalue(),
                error=str(e),
                execution_time_ms=execution_time,
                memory_used_bytes=1024,
                cpu_percent=0.1,
                suggestions=["Check syntax and logic"],
                security_level="simple",
                code_hash=hashlib.md5(code.encode()).hexdigest()
            )
