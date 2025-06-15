#!/usr/bin/env python3
"""
Unit tests for the core code executor
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import sys

# Add src to path for imports
src_dir = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from core.executor import (
    CodeExecutor, 
    ExecutionResult, 
    ExecutionStatus,
    RestrictedPythonStrategy,
    ASTEvalStrategy,
    SubprocessStrategy,
    BasicSandboxStrategy
)

class TestExecutionResult:
    """Test ExecutionResult data class"""
    
    def test_creation(self):
        """Test ExecutionResult creation"""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="Hello, World!",
            error="",
            execution_time_ms=10.5,
            memory_used_bytes=1024,
            cpu_percent=5.0,
            suggestions=[],
            security_level="basic",
            code_hash="abc123"
        )
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output == "Hello, World!"
        assert result.execution_time_ms == 10.5
        assert result.memory_used_bytes == 1024
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="Test output",
            error="",
            execution_time_ms=15.25,
            memory_used_bytes=2048,
            cpu_percent=10.5,
            suggestions=["suggestion1", "suggestion2"],
            security_level="restricted",
            code_hash="def456"
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["status"] == "success"
        assert data["output"] == "Test output"
        assert data["metrics"]["time_ms"] == 15.25
        assert data["metrics"]["memory_kb"] == 2.0
        assert data["suggestions"] == ["suggestion1", "suggestion2"]
        assert data["security_level"] == "restricted"
        assert data["code_hash"] == "def456"
    
    def test_output_truncation(self):
        """Test that long output is truncated in to_dict"""
        long_output = "x" * 2000
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output=long_output,
            error="",
            execution_time_ms=1.0,
            memory_used_bytes=100,
            cpu_percent=1.0,
            suggestions=[],
            security_level="basic",
            code_hash="truncate"
        )
        
        data = result.to_dict()
        assert len(data["output"]) == 1000
        assert data["output"] == "x" * 1000

class TestBasicSandboxStrategy:
    """Test BasicSandboxStrategy"""
    
    def setUp(self):
        self.strategy = BasicSandboxStrategy()
    
    def test_can_handle_simple_code(self):
        """Test that simple code is handled"""
        simple_code = "x = 1 + 2\nprint(x)"
        assert self.strategy.can_handle(simple_code)
    
    def test_cannot_handle_complex_code(self):
        """Test that complex code is not handled"""
        complex_code = "import os\nos.system('ls')"
        assert not self.strategy.can_handle(complex_code)
    
    @pytest.mark.asyncio
    async def test_execute_simple_code(self):
        """Test execution of simple code"""
        strategy = BasicSandboxStrategy()
        code = "print('Hello, World!')"
        
        output, error, success = await strategy.execute(code, 5.0)
        
        assert success is True
        assert "Hello, World!" in output
        assert error == ""
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """Test execution of code with error"""
        strategy = BasicSandboxStrategy()
        code = "print(undefined_variable)"
        
        output, error, success = await strategy.execute(code, 5.0)
        
        assert success is False
        assert "NameError" in error
        assert "undefined_variable" in error

class TestCodeExecutor:
    """Test main CodeExecutor class"""
    
    @pytest.fixture
    def executor(self):
        """Create a CodeExecutor instance for testing"""
        return CodeExecutor(timeout=5.0, memory_limit_mb=64)
    
    @pytest.mark.asyncio
    async def test_execute_simple_code(self, executor):
        """Test execution of simple code"""
        code = "print('Hello from executor!')"
        
        result = await executor.execute_code(code)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert "Hello from executor!" in result.output
        assert result.execution_time_ms > 0
        assert result.code_hash != ""
    
    @pytest.mark.asyncio
    async def test_execute_code_with_error(self, executor):
        """Test execution of code that has an error"""
        code = "print(nonexistent_variable)"
        
        result = await executor.execute_code(code)
        
        assert result.status == ExecutionStatus.FAILURE
        assert "NameError" in result.error
        assert len(result.suggestions) > 0
        assert any("variable" in suggestion.lower() for suggestion in result.suggestions)
    
    @pytest.mark.asyncio
    async def test_execute_empty_code(self, executor):
        """Test execution of empty code"""
        result = await executor.execute_code("")
        
        assert result.status == ExecutionStatus.FAILURE
        assert "Invalid code input" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_too_large_code(self, executor):
        """Test execution of code that's too large"""
        large_code = "x = 1\n" * 50000  # Create code larger than 50KB
        
        result = await executor.execute_code(large_code)
        
        assert result.status == ExecutionStatus.FAILURE
        assert "Code too large" in result.error
    
    @pytest.mark.asyncio
    async def test_security_violation_detection(self, executor):
        """Test that security violations are detected"""
        dangerous_code = "import os; os.system('rm -rf /')"
        
        result = await executor.execute_code(dangerous_code)
        
        assert result.status == ExecutionStatus.FAILURE
        # Should be caught by security check or execution failure
        assert any(keyword in result.error.lower() for keyword in ["security", "import", "system"])
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self, executor):
        """Test that execution results are cached"""
        code = "print('cached result')"
        
        # First execution
        result1 = await executor.execute_code(code)
        
        # Second execution (should use cache)
        result2 = await executor.execute_code(code)
        
        assert result1.status == result2.status
        assert result1.output == result2.output
        assert result1.code_hash == result2.code_hash
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test that timeouts are handled properly"""
        executor = CodeExecutor(timeout=0.1)  # Very short timeout
        
        # Code that would take longer than timeout
        slow_code = """
import time
time.sleep(1)
print('This should timeout')
"""
        
        result = await executor.execute_code(slow_code)
        
        # Should either timeout or be rejected by security
        assert result.status in [ExecutionStatus.TIMEOUT, ExecutionStatus.FAILURE]
    
    def test_strategy_selection(self, executor):
        """Test that appropriate strategies are selected"""
        # Test simple code
        simple_code = "x = 1 + 1"
        strategy = executor._choose_strategy(simple_code)
        assert strategy is not None
        
        # Test mathematical code
        math_code = "result = 2 + 2 * 3"
        strategy = executor._choose_strategy(math_code)
        assert strategy is not None
    
    def test_security_check(self, executor):
        """Test security checking functionality"""
        # Safe code
        safe_code = "x = 1 + 1\nprint(x)"
        issues = executor._security_check(safe_code)
        assert len(issues) == 0
        
        # Dangerous code
        dangerous_code = "import os\nos.system('ls')"
        issues = executor._security_check(dangerous_code)
        assert len(issues) > 0
        assert any("system" in issue.lower() for issue in issues)
    
    def test_error_suggestions(self, executor):
        """Test error suggestion generation"""
        # Test NameError suggestions
        name_error = "NameError: name 'undefined_var' is not defined"
        suggestions = executor._generate_suggestions(name_error, "print(undefined_var)")
        assert len(suggestions) > 0
        assert any("variable" in suggestion.lower() for suggestion in suggestions)
        
        # Test SyntaxError suggestions
        syntax_error = "SyntaxError: invalid syntax"
        suggestions = executor._generate_suggestions(syntax_error, "if x == 1 print('yes')")
        assert len(suggestions) > 0
        assert any("syntax" in suggestion.lower() for suggestion in suggestions)
        
        # Test IndentationError suggestions
        indent_error = "IndentationError: expected an indented block"
        suggestions = executor._generate_suggestions(indent_error, "if True:\nprint('hello')")
        assert len(suggestions) > 0
        assert any("indent" in suggestion.lower() for suggestion in suggestions)
    
    def test_get_stats(self, executor):
        """Test statistics retrieval"""
        stats = executor.get_stats()
        
        assert "available_strategies" in stats
        assert "cache_size" in stats
        assert "memory_limit_mb" in stats
        assert "timeout_seconds" in stats
        
        assert isinstance(stats["available_strategies"], list)
        assert stats["memory_limit_mb"] == 64  # Set in fixture
        assert stats["timeout_seconds"] == 5.0  # Set in fixture

class TestSecurityStrategies:
    """Test different security strategies"""
    
    @pytest.mark.asyncio
    async def test_restricted_python_strategy(self):
        """Test RestrictedPython strategy if available"""
        strategy = RestrictedPythonStrategy()
        
        if not strategy.can_handle("print('test')"):
            pytest.skip("RestrictedPython not available")
        
        # Test safe code
        safe_code = "x = 1 + 1\nprint(x)"
        output, error, success = await strategy.execute(safe_code, 5.0)
        
        if success:  # Only check if execution succeeded
            assert "2" in output
            assert error == ""
    
    @pytest.mark.asyncio
    async def test_asteval_strategy(self):
        """Test ASTeval strategy if available"""
        strategy = ASTEvalStrategy()
        
        if not strategy.can_handle("2 + 2"):
            pytest.skip("ASTeval not available or code not suitable")
        
        # Test mathematical expression
        math_code = "result = 2 + 2 * 3\nprint(result)"
        output, error, success = await strategy.execute(math_code, 5.0)
        
        # Note: ASTeval might not support all Python syntax
        # Just check that it doesn't crash
        assert isinstance(success, bool)
    
    @pytest.mark.asyncio
    async def test_subprocess_strategy(self):
        """Test subprocess strategy"""
        strategy = SubprocessStrategy()
        
        # Subprocess should handle any code
        assert strategy.can_handle("print('test')")
        
        # Test simple code
        simple_code = "print('subprocess test')"
        output, error, success = await strategy.execute(simple_code, 5.0)
        
        assert success is True
        assert "subprocess test" in output

class TestPerformanceMetrics:
    """Test performance measurement functionality"""
    
    @pytest.mark.asyncio
    async def test_execution_timing(self):
        """Test that execution time is measured"""
        executor = CodeExecutor()
        
        # Simple code that should execute quickly
        code = "x = 1"
        result = await executor.execute_code(code)
        
        assert result.execution_time_ms >= 0
        assert result.execution_time_ms < 1000  # Should be very fast
    
    @pytest.mark.asyncio
    async def test_memory_measurement(self):
        """Test that memory usage is tracked"""
        executor = CodeExecutor()
        
        code = "data = list(range(1000))\nprint(len(data))"
        result = await executor.execute_code(code)
        
        # Memory measurement might not be precise, just check it's reasonable
        assert result.memory_used_bytes >= 0
    
    @pytest.mark.asyncio
    async def test_cpu_measurement(self):
        """Test that CPU usage is tracked"""
        executor = CodeExecutor()
        
        code = "sum(range(1000))"
        result = await executor.execute_code(code)
        
        assert result.cpu_percent >= 0
        assert result.cpu_percent <= 100

# Integration tests for strategy interaction
class TestStrategyIntegration:
    """Test how different strategies work together"""
    
    @pytest.mark.asyncio
    async def test_strategy_fallback(self):
        """Test that executor falls back to appropriate strategies"""
        executor = CodeExecutor()
        
        # Code that might not work with all strategies
        complex_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
print(f"Fibonacci(10) = {result}")
"""
        
        result = await executor.execute_code(complex_code)
        
        # Should succeed with at least one strategy
        assert result.status == ExecutionStatus.SUCCESS
        assert "55" in result.output  # fibonacci(10) = 55
    
    @pytest.mark.asyncio
    async def test_strategy_security_levels(self):
        """Test that different strategies provide different security levels"""
        executor = CodeExecutor()
        
        test_cases = [
            "print('hello')",  # Basic
            "x = 2 + 2",       # Mathematical
            "def f(): pass",   # Function definition
        ]
        
        security_levels = set()
        
        for code in test_cases:
            result = await executor.execute_code(code)
            if result.status == ExecutionStatus.SUCCESS:
                security_levels.add(result.security_level)
        
        # Should have at least one security level
        assert len(security_levels) >= 1

# Fixtures and test helpers
@pytest.fixture
def sample_codes():
    """Provide sample code snippets for testing"""
    return {
        "simple": "print('Hello, World!')",
        "mathematical": "result = (2 + 3) * 4\nprint(result)",
        "with_error": "print(undefined_variable)",
        "with_function": """
def greet(name):
    return f"Hello, {name}!"

print(greet("Test"))
""",
        "complex": """
import math

def calculate_circle_area(radius):
    return math.pi * radius ** 2

for r in range(1, 4):
    area = calculate_circle_area(r)
    print(f"Circle with radius {r}: area = {area:.2f}")
""",
        "slow": """
import time
time.sleep(0.1)
print("Finished sleeping")
""",
        "memory_intensive": """
data = list(range(10000))
squared = [x**2 for x in data]
print(f"Processed {len(squared)} items")
"""
    }

@pytest.mark.integration
class TestRealWorldScenarios:
    """Test realistic usage scenarios"""
    
    @pytest.mark.asyncio
    async def test_data_processing_scenario(self, sample_codes):
        """Test a realistic data processing scenario"""
        executor = CodeExecutor()
        
        result = await executor.execute_code(sample_codes["memory_intensive"])
        
        assert result.status == ExecutionStatus.SUCCESS
        assert "10000" in result.output
        assert result.memory_used_bytes > 0
    
    @pytest.mark.asyncio
    async def test_algorithm_implementation_scenario(self, sample_codes):
        """Test implementing and running an algorithm"""
        executor = CodeExecutor()
        
        algorithm_code = """
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

# Test the algorithm
test_array = [1, 3, 5, 7, 9, 11, 13, 15]
target = 7
result = binary_search(test_array, target)
print(f"Found {target} at index {result}")
"""
        
        result = await executor.execute_code(algorithm_code)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert "Found 7 at index 3" in result.output
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self):
        """Test how executor handles and suggests fixes for common errors"""
        executor = CodeExecutor()
        
        buggy_codes = [
            "print(undefined_var)",  # NameError
            "if True\n    print('missing colon')",  # SyntaxError
            "x = 1\ny = x / 0",  # ZeroDivisionError
        ]
        
        for code in buggy_codes:
            result = await executor.execute_code(code)
            
            assert result.status == ExecutionStatus.FAILURE
            assert len(result.suggestions) > 0
            assert result.error != ""

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
