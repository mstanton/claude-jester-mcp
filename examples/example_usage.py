#!/usr/bin/env python3
"""
Basic Usage Examples for Claude Desktop MCP Execution
Demonstrates how to use the code execution system effectively
"""

import asyncio
import sys
from pathlib import Path

# Add the source directory to Python path for imports
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from core.executor import CodeExecutor, ExecutionStatus
from core.quantum_debugger import QuantumDebugger
from core.learning_system import LearningSystem

async def basic_execution_example():
    """Example 1: Basic code execution"""
    print("🔧 Example 1: Basic Code Execution")
    print("=" * 50)
    
    executor = CodeExecutor(timeout=5.0)
    
    # Simple code execution
    code = """
def greet(name):
    return f"Hello, {name}!"

result = greet("Claude")
print(result)
"""
    
    result = await executor.execute_code(code)
    
    print(f"Status: {result.status.value}")
    print(f"Output: {result.output}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print(f"Security level: {result.security_level}")
    
    if result.suggestions:
        print(f"Suggestions: {', '.join(result.suggestions)}")
    
    print("\n")

async def error_handling_example():
    """Example 2: Error handling and suggestions"""
    print("🐛 Example 2: Error Handling")
    print("=" * 50)
    
    executor = CodeExecutor()
    
    # Code with an error
    buggy_code = """
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbres)  # Typo: 'numbres' instead of 'numbers'

result = calculate_average([1, 2, 3, 4, 5])
print(f"Average: {result}")
"""
    
    result = await executor.execute_code(buggy_code)
    
    print(f"Status: {result.status.value}")
    print(f"Error: {result.error}")
    print("Suggestions:")
    for suggestion in result.suggestions:
        print(f"  - {suggestion}")
    
    print("\n")

async def quantum_debugging_example():
    """Example 3: Quantum debugging with multiple variants"""
    print("🔬 Example 3: Quantum Debugging")
    print("=" * 50)
    
    executor = CodeExecutor()
    quantum_debugger = QuantumDebugger(executor)
    
    # Code that can be optimized in multiple ways
    code = """
def find_duplicates(numbers):
    duplicates = []
    for i, num in enumerate(numbers):
        for j in range(i + 1, len(numbers)):
            if num == numbers[j] and num not in duplicates:
                duplicates.append(num)
    return duplicates

test_list = [1, 2, 3, 2, 4, 5, 3, 6, 1]
result = find_duplicates(test_list)
print(f"Duplicates: {result}")
"""
    
    # Test with quantum debugging
    quantum_result = await quantum_debugger.execute_with_variants(
        code, 
        description="Find duplicates in a list",
        focus="speed"
    )
    
    analysis = quantum_result["analysis"]
    print(f"Tested variants: {analysis['total_variants']}")
    print(f"Successful: {analysis['successful']}")
    print(f"Best variant: {analysis.get('best_variant', 'None')}")
    print(f"Recommendation: {quantum_result.get('recommendation', 'No recommendation')}")
    
    print("\n")

async def learning_system_example():
    """Example 4: Learning system adaptation"""
    print("🧠 Example 4: Learning System")
    print("=" * 50)
    
    executor = CodeExecutor()
    learning_system = LearningSystem()
    
    # Simulate multiple executions to build patterns
    code_examples = [
        """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))
""",
        """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

print(fibonacci(10))
""",
        """
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

print(is_prime(17))
"""
    ]
    
    print("Recording executions to build learning patterns...")
    for i, code in enumerate(code_examples):
        result = await executor.execute_code(code)
        await learning_system.record_execution(code, result, f"Example {i+1}")
        print(f"  Recorded execution {i+1}: {result.status.value}")
    
    # Get insights
    insights = await learning_system.get_insights()
    print("\nLearning Insights:")
    
    if "patterns" in insights:
        patterns = insights["patterns"]
        print(f"  Total patterns learned: {patterns['total_patterns']}")
        print(f"  Pattern types: {list(patterns['pattern_types'].keys())}")
    
    if "progress" in insights:
        progress = insights["progress"]
        print(f"  Success rate: {progress.get('recent_success_rate', 0):.1%}")
        print(f"  Average pattern confidence: {progress.get('average_pattern_confidence', 0):.1%}")
    
    # Get coding DNA
    coding_dna = learning_system.get_user_coding_dna()
    print(f"\nCoding DNA:")
    print(f"  Experience level: {coding_dna['experience_level']}")
    print(f"  Coding personality: {coding_dna['coding_personality']}")
    print(f"  Strength areas: {', '.join(coding_dna['strength_areas'])}")
    
    print("\n")

async def performance_benchmarking_example():
    """Example 5: Performance benchmarking"""
    print("⚡ Example 5: Performance Benchmarking")
    print("=" * 50)
    
    executor = CodeExecutor()
    
    # Different approaches to sum a list
    approaches = {
        "builtin_sum": "result = sum(range(1000))",
        "manual_loop": """
result = 0
for i in range(1000):
    result += i
""",
        "list_comprehension": "result = sum([i for i in range(1000)])",
        "generator_expression": "result = sum(i for i in range(1000))"
    }
    
    print("Benchmarking different approaches to sum 1000 numbers:")
    
    performance_results = {}
    for name, code in approaches.items():
        # Run multiple times for better average
        times = []
        for _ in range(5):
            result = await executor.execute_code(code)
            if result.status == ExecutionStatus.SUCCESS:
                times.append(result.execution_time_ms)
        
        if times:
            avg_time = sum(times) / len(times)
            performance_results[name] = avg_time
            print(f"  {name}: {avg_time:.2f}ms (avg of {len(times)} runs)")
    
    # Find the fastest approach
    if performance_results:
        fastest = min(performance_results, key=performance_results.get)
        print(f"\n🏆 Fastest approach: {fastest} ({performance_results[fastest]:.2f}ms)")
    
    print("\n")

async def security_demonstration():
    """Example 6: Security features demonstration"""
    print("🛡️ Example 6: Security Features")
    print("=" * 50)
    
    executor = CodeExecutor()
    
    # Demonstrate security restrictions
    dangerous_codes = [
        "import os; os.system('ls')",
        "open('/etc/passwd', 'r').read()",
        "eval('print(\"hello\")')",
        "exec('x = 1')"
    ]
    
    print("Testing security restrictions:")
    
    for i, dangerous_code in enumerate(dangerous_codes, 1):
        print(f"\nTest {i}: {dangerous_code}")
        result = await executor.execute_code(dangerous_code)
        
        if result.status == ExecutionStatus.SECURITY_VIOLATION:
            print(f"  ✅ Security violation detected: {result.error}")
        elif result.status == ExecutionStatus.FAILURE:
            print(f"  ✅ Execution blocked: {result.error}")
        else:
            print(f"  ⚠️  Code executed (security level: {result.security_level})")
    
    print("\n")

async def complex_algorithm_example():
    """Example 7: Complex algorithm with optimization"""
    print("🧮 Example 7: Complex Algorithm Optimization")
    print("=" * 50)
    
    executor = CodeExecutor()
    quantum_debugger = QuantumDebugger(executor)
    
    # A more complex algorithm that can benefit from optimization
    algorithm_code = """
def matrix_multiply(A, B):
    \"\"\"Multiply two matrices\"\"\"
    rows_A, cols_A = len(A), len(A[0])
    rows_B, cols_B = len(B), len(B[0])
    
    if cols_A != rows_B:
        raise ValueError("Cannot multiply matrices: incompatible dimensions")
    
    # Initialize result matrix
    result = [[0 for _ in range(cols_B)] for _ in range(rows_A)]
    
    # Perform multiplication
    for i in range(rows_A):
        for j in range(cols_B):
            for k in range(cols_A):
                result[i][j] += A[i][k] * B[k][j]
    
    return result

# Test with small matrices
A = [[1, 2], [3, 4]]
B = [[5, 6], [7, 8]]

result = matrix_multiply(A, B)
print("Matrix multiplication result:")
for row in result:
    print(row)
"""
    
    print("Testing matrix multiplication algorithm...")
    
    # First, test the original
    original_result = await executor.execute_code(algorithm_code)
    print(f"Original execution: {original_result.status.value}")
    print(f"Original time: {original_result.execution_time_ms:.2f}ms")
    
    if original_result.status == ExecutionStatus.SUCCESS:
        print(f"Output:\n{original_result.output}")
    
    # Then use quantum debugging to find optimizations
    print("\nTesting with quantum debugging for optimizations...")
    quantum_result = await quantum_debugger.execute_with_variants(
        algorithm_code,
        description="Matrix multiplication algorithm",
        focus="speed"
    )
    
    best_variant = quantum_result.get("best_variant")
    if best_variant and best_variant != "original":
        print(f"Quantum debugging found better approach: {best_variant}")
        print(f"Recommendation: {quantum_result.get('recommendation')}")
    else:
        print("Original algorithm was already optimal for this use case")
    
    print("\n")

async def main():
    """Run all examples"""
    print("🚀 Claude Desktop MCP Execution - Usage Examples")
    print("=" * 60)
    print()
    
    examples = [
        basic_execution_example,
        error_handling_example,
        quantum_debugging_example,
        learning_system_example,
        performance_benchmarking_example,
        security_demonstration,
        complex_algorithm_example
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"❌ Example failed: {e}")
            print()
    
    print("🎉 All examples completed!")
    print("\n💡 Tips for using Claude Desktop MCP:")
    print("  • Ask Claude to 'test this code' before using it")
    print("  • Request 'optimization suggestions' for performance-critical code")
    print("  • Use 'validate with edge cases' for production code")
    print("  • Try 'show me multiple approaches' for learning different solutions")

if __name__ == "__main__":
    asyncio.run(main())
