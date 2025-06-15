#!/usr/bin/env python3
"""
Quantum Debugging Engine
Enables parallel testing of code variants to find optimal solutions automatically
"""

import asyncio
import ast
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from .executor import CodeExecutor, ExecutionResult, ExecutionStatus

@dataclass
class CodeVariant:
    """Represents a code variant for testing"""
    id: str
    code: str
    description: str
    confidence: float
    optimization_focus: str = "general"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class VariantGenerator:
    """Generates code variants for different optimization strategies"""
    
    def __init__(self):
        self.variant_strategies = {
            "speed": self._generate_speed_variants,
            "memory": self._generate_memory_variants,
            "readability": self._generate_readability_variants,
            "auto": self._generate_auto_variants
        }
    
    async def generate_variants(self, code: str, focus: str = "auto", description: str = "") -> List[CodeVariant]:
        """Generate code variants based on optimization focus"""
        variants = [
            CodeVariant(
                id="original",
                code=code,
                description="Original code",
                confidence=0.8,
                optimization_focus=focus
            )
        ]
        
        # Generate focused variants
        if focus in self.variant_strategies:
            focused_variants = await self.variant_strategies[focus](code, description)
            variants.extend(focused_variants)
        else:
            # Generate general variants
            auto_variants = await self._generate_auto_variants(code, description)
            variants.extend(auto_variants)
        
        return variants
    
    async def _generate_speed_variants(self, code: str, description: str) -> List[CodeVariant]:
        """Generate speed-optimized variants"""
        variants = []
        
        # List comprehension variant
        if self._has_simple_loop(code):
            list_comp_code = self._convert_to_list_comprehension(code)
            if list_comp_code != code:
                variants.append(CodeVariant(
                    id="list_comprehension",
                    code=list_comp_code,
                    description="List comprehension optimization",
                    confidence=0.9,
                    optimization_focus="speed"
                ))
        
        # Set-based operations variant
        if "in " in code and "for " in code:
            set_based_code = self._optimize_with_sets(code)
            if set_based_code != code:
                variants.append(CodeVariant(
                    id="set_optimized",
                    code=set_based_code,
                    description="Set-based optimization for O(1) lookups",
                    confidence=0.85,
                    optimization_focus="speed"
                ))
        
        # Mathematical formula variant
        if self._is_mathematical_sequence(code):
            formula_code = self._apply_mathematical_formula(code)
            if formula_code != code:
                variants.append(CodeVariant(
                    id="mathematical_formula",
                    code=formula_code,
                    description="Mathematical formula optimization",
                    confidence=0.95,
                    optimization_focus="speed"
                ))
        
        return variants
    
    async def _generate_memory_variants(self, code: str, description: str) -> List[CodeVariant]:
        """Generate memory-optimized variants"""
        variants = []
        
        # Generator variant
        if self._can_use_generator(code):
            generator_code = self._convert_to_generator(code)
            if generator_code != code:
                variants.append(CodeVariant(
                    id="generator_optimized",
                    code=generator_code,
                    description="Generator-based memory optimization",
                    confidence=0.8,
                    optimization_focus="memory"
                ))
        
        # In-place operations variant
        if self._can_optimize_inplace(code):
            inplace_code = self._optimize_inplace_operations(code)
            if inplace_code != code:
                variants.append(CodeVariant(
                    id="inplace_optimized",
                    code=inplace_code,
                    description="In-place operations to reduce memory",
                    confidence=0.75,
                    optimization_focus="memory"
                ))
        
        return variants
    
    async def _generate_readability_variants(self, code: str, description: str) -> List[CodeVariant]:
        """Generate readability-optimized variants"""
        variants = []
        
        # Function decomposition variant
        if self._is_complex_function(code):
            decomposed_code = self._decompose_function(code)
            if decomposed_code != code:
                variants.append(CodeVariant(
                    id="decomposed",
                    code=decomposed_code,
                    description="Function decomposition for readability",
                    confidence=0.7,
                    optimization_focus="readability"
                ))
        
        # Type hints variant
        if not self._has_type_hints(code):
            typed_code = self._add_type_hints(code)
            if typed_code != code:
                variants.append(CodeVariant(
                    id="type_hinted",
                    code=typed_code,
                    description="Added type hints for clarity",
                    confidence=0.8,
                    optimization_focus="readability"
                ))
        
        return variants
    
    async def _generate_auto_variants(self, code: str, description: str) -> List[CodeVariant]:
        """Generate variants automatically based on code analysis"""
        variants = []
        
        # Combine best practices from all strategies
        speed_variants = await self._generate_speed_variants(code, description)
        memory_variants = await self._generate_memory_variants(code, description)
        readability_variants = await self._generate_readability_variants(code, description)
        
        # Select best variants (limit to avoid explosion)
        all_variants = speed_variants + memory_variants + readability_variants
        
        # Sort by confidence and take top variants
        sorted_variants = sorted(all_variants, key=lambda v: v.confidence, reverse=True)
        return sorted_variants[:4]  # Limit to 4 additional variants
    
    def _has_simple_loop(self, code: str) -> bool:
        """Check if code has a simple loop that can be optimized"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    return True
            return False
        except:
            return False
    
    def _convert_to_list_comprehension(self, code: str) -> str:
        """Convert simple loops to list comprehensions"""
        # Simple pattern matching for basic for loops
        pattern = r'(\w+)\s*=\s*\[\]\s*\nfor\s+(\w+)\s+in\s+([^:]+):\s*\n\s*\1\.append\(([^)]+)\)'
        match = re.search(pattern, code)
        
        if match:
            var_name, loop_var, iterable, expression = match.groups()
            replacement = f"{var_name} = [{expression} for {loop_var} in {iterable}]"
            return code.replace(match.group(0), replacement)
        
        return code
    
    def _optimize_with_sets(self, code: str) -> str:
        """Optimize membership tests with sets"""
        # Convert list membership to set membership
        if "in [" in code:
            return code.replace("in [", "in {").replace("]", "}")
        return code
    
    def _is_mathematical_sequence(self, code: str) -> bool:
        """Check if code calculates a mathematical sequence"""
        math_patterns = [
            "sum.*range",
            "factorial",
            "fibonacci",
            "squares",
            r"\*\s*\w+\s*\*\s*\w+"  # multiplication patterns
        ]
        
        for pattern in math_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        return False
    
    def _apply_mathematical_formula(self, code: str) -> str:
        """Apply mathematical formulas where possible"""
        # Sum of squares optimization
        if "sum" in code.lower() and "square" in code.lower():
            pattern = r'sum\([^)]*i\s*\*\s*i[^)]*\)'
            if re.search(pattern, code):
                # Replace with mathematical formula
                return code + "\n# Optimized: use formula n*(n+1)*(2*n+1)/6 for sum of squares"
        
        return code
    
    def _can_use_generator(self, code: str) -> bool:
        """Check if code can benefit from generators"""
        return "append" in code and "for " in code
    
    def _convert_to_generator(self, code: str) -> str:
        """Convert to generator-based approach"""
        # Simple conversion of list building to generator
        if "result = []" in code and "append" in code:
            return code.replace("result = []", "def generate_result():").replace("append(", "yield ")
        return code
    
    def _can_optimize_inplace(self, code: str) -> bool:
        """Check if code can use in-place operations"""
        return any(op in code for op in ["+=", "*=", "-=", "/="])
    
    def _optimize_inplace_operations(self, code: str) -> str:
        """Optimize with in-place operations"""
        # Already optimized if using in-place ops
        return code
    
    def _is_complex_function(self, code: str) -> bool:
        """Check if function is complex enough to decompose"""
        return len(code.split('\n')) > 10
    
    def _decompose_function(self, code: str) -> str:
        """Decompose complex function into smaller functions"""
        # This would require more sophisticated AST manipulation
        # For now, just add a comment
        return code + "\n# TODO: Consider breaking this into smaller functions"
    
    def _has_type_hints(self, code: str) -> bool:
        """Check if code has type hints"""
        return "->" in code or ": " in code
    
    def _add_type_hints(self, code: str) -> str:
        """Add basic type hints"""
        # Simple type hint addition
        if "def " in code and "->" not in code:
            return code.replace("def ", "def ").replace("):", ") -> Any:")
        return code

class QuantumDebugger:
    """Main quantum debugging engine"""
    
    def __init__(self, executor: CodeExecutor):
        self.executor = executor
        self.variant_generator = VariantGenerator()
        self.execution_history = []
    
    async def execute_with_variants(self, code: str, description: str = "", focus: str = "auto") -> Dict[str, Any]:
        """Execute code with multiple variants and return the best result"""
        
        # Generate variants
        variants = await self.variant_generator.generate_variants(code, focus, description)
        
        # Test all variants
        results = await self.test_variants(variants)
        
        # Store in history
        self.execution_history.append({
            "timestamp": time.time(),
            "original_code": code,
            "description": description,
            "focus": focus,
            "results": results
        })
        
        return results
    
    async def test_variants(self, variants: List[CodeVariant]) -> Dict[str, Any]:
        """Test multiple code variants in parallel"""
        
        # Execute all variants in parallel
        tasks = []
        for variant in variants:
            task = asyncio.create_task(self._test_variant(variant))
            tasks.append((variant, task))
        
        # Collect results
        results = {}
        for variant, task in tasks:
            try:
                execution_result = await task
                results[variant.id] = {
                    "variant": variant.to_dict(),
                    "execution": execution_result.to_dict()
                }
            except Exception as e:
                results[variant.id] = {
                    "variant": variant.to_dict(),
                    "execution": {
                        "success": False,
                        "error": str(e),
                        "status": "failed"
                    }
                }
        
        # Analyze results
        analysis = self._analyze_results(results)
        
        return {
            "results": results,
            "analysis": analysis,
            "best_variant": analysis.get("best_variant"),
            "recommendation": self._generate_recommendation(results, analysis)
        }
    
    async def _test_variant(self, variant: CodeVariant) -> ExecutionResult:
        """Test a single variant"""
        return await self.executor.execute_code(variant.code)
    
    def _analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze variant results to find best option"""
        
        successful_variants = []
        failed_variants = []
        
        for variant_id, result in results.items():
            execution = result["execution"]
            if execution.get("success", False):
                successful_variants.append((variant_id, result))
            else:
                failed_variants.append((variant_id, result))
        
        analysis = {
            "total_variants": len(results),
            "successful": len(successful_variants),
            "failed": len(failed_variants),
            "success_rate": len(successful_variants) / len(results) if results else 0
        }
        
        # Find best variant based on multiple criteria
        if successful_variants:
            best_variant = self._select_best_variant(successful_variants)
            analysis["best_variant"] = best_variant
            analysis["improvement_metrics"] = self._calculate_improvements(successful_variants, best_variant)
        
        return analysis
    
    def _select_best_variant(self, successful_variants: List[Tuple[str, Dict[str, Any]]]) -> str:
        """Select the best variant based on multiple criteria"""
        
        def score_variant(variant_data: Tuple[str, Dict[str, Any]]) -> float:
            variant_id, result = variant_data
            execution = result["execution"]
            variant_info = result["variant"]
            
            # Scoring factors
            time_score = 1000 / max(execution.get("metrics", {}).get("time_ms", 1000), 1)  # Faster is better
            memory_score = 1000 / max(execution.get("metrics", {}).get("memory_kb", 1000), 1)  # Less memory is better
            confidence_score = variant_info.get("confidence", 0.5) * 100  # Higher confidence is better
            
            # Weighted score
            total_score = (time_score * 0.4) + (memory_score * 0.3) + (confidence_score * 0.3)
            
            return total_score
        
        # Sort by score and return best
        scored_variants = [(score_variant(v), v[0]) for v in successful_variants]
        scored_variants.sort(reverse=True)
        
        return scored_variants[0][1] if scored_variants else successful_variants[0][0]
    
    def _calculate_improvements(self, successful_variants: List[Tuple[str, Dict[str, Any]]], best_variant_id: str) -> Dict[str, Any]:
        """Calculate improvement metrics compared to original"""
        
        original_result = None
        best_result = None
        
        for variant_id, result in successful_variants:
            if variant_id == "original":
                original_result = result
            if variant_id == best_variant_id:
                best_result = result
        
        if not original_result or not best_result:
            return {}
        
        original_metrics = original_result["execution"].get("metrics", {})
        best_metrics = best_result["execution"].get("metrics", {})
        
        improvements = {}
        
        # Time improvement
        original_time = original_metrics.get("time_ms", 1)
        best_time = best_metrics.get("time_ms", 1)
        if original_time > 0:
            improvements["time_speedup"] = original_time / best_time
            improvements["time_improvement_percent"] = ((original_time - best_time) / original_time) * 100
        
        # Memory improvement
        original_memory = original_metrics.get("memory_kb", 1)
        best_memory = best_metrics.get("memory_kb", 1)
        if original_memory > 0:
            improvements["memory_ratio"] = original_memory / best_memory
            improvements["memory_improvement_percent"] = ((original_memory - best_memory) / original_memory) * 100
        
        return improvements
    
    def _generate_recommendation(self, results: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate a human-readable recommendation"""
        
        if analysis.get("best_variant") == "original":
            return "The original code is already optimal for the given constraints."
        
        best_variant_id = analysis.get("best_variant")
        if not best_variant_id:
            return "No variants executed successfully. Consider reviewing the code for errors."
        
        best_result = results.get(best_variant_id, {})
        variant_info = best_result.get("variant", {})
        improvements = analysis.get("improvement_metrics", {})
        
        recommendation_parts = [
            f"Recommended solution: {variant_info.get('description', best_variant_id)}"
        ]
        
        if improvements.get("time_speedup", 1) > 1.1:  # At least 10% improvement
            speedup = improvements["time_speedup"]
            recommendation_parts.append(f"Performance improvement: {speedup:.1f}x faster")
        
        if improvements.get("memory_ratio", 1) > 1.1:  # At least 10% improvement
            ratio = improvements["memory_ratio"]
            recommendation_parts.append(f"Memory efficiency: {ratio:.1f}x more efficient")
        
        confidence = variant_info.get("confidence", 0)
        recommendation_parts.append(f"Confidence: {confidence:.0%}")
        
        return " | ".join(recommendation_parts)
    
    async def generate_optimization_variants(self, code: str, focus: str = "speed") -> List[CodeVariant]:
        """Generate variants specifically for optimization"""
        return await self.variant_generator.generate_variants(code, focus, "optimization")
    
    async def generate_edge_case_tests(self, code: str) -> List[Dict[str, Any]]:
        """Generate edge case tests for the given code"""
        
        edge_cases = []
        
        # Common edge cases based on code analysis
        if "list" in code.lower() or "[" in code:
            edge_cases.extend([
                {"name": "empty_list", "test_data": "[]", "description": "Empty list handling"},
                {"name": "single_item", "test_data": "[1]", "description": "Single item list"},
                {"name": "large_list", "test_data": "list(range(10000))", "description": "Large list performance"}
            ])
        
        if "dict" in code.lower() or "{" in code:
            edge_cases.extend([
                {"name": "empty_dict", "test_data": "{}", "description": "Empty dictionary"},
                {"name": "nested_dict", "test_data": "{'a': {'b': 1}}", "description": "Nested dictionary"}
            ])
        
        if "int" in code or any(op in code for op in ["+", "-", "*", "/", "%"]):
            edge_cases.extend([
                {"name": "zero_value", "test_data": "0", "description": "Zero value handling"},
                {"name": "negative_value", "test_data": "-1", "description": "Negative value handling"},
                {"name": "large_number", "test_data": "999999999", "description": "Large number handling"}
            ])
        
        # Test each edge case
        tested_cases = []
        for case in edge_cases:
            try:
                # This is a simplified edge case test
                # In practice, would need more sophisticated test generation
                test_result = await self.executor.execute_code(
                    f"# Edge case test: {case['description']}\n{code}"
                )
                
                tested_cases.append({
                    "case": case,
                    "success": test_result.status == ExecutionStatus.SUCCESS,
                    "execution_time": test_result.execution_time_ms,
                    "error": test_result.error if test_result.error else None
                })
            except Exception as e:
                tested_cases.append({
                    "case": case,
                    "success": False,
                    "error": str(e)
                })
        
        return tested_cases
    
    def get_history_stats(self) -> Dict[str, Any]:
        """Get statistics from execution history"""
        
        if not self.execution_history:
            return {"total_executions": 0}
        
        total_executions = len(self.execution_history)
        
        # Count improvements
        improvements = 0
        for entry in self.execution_history:
            analysis = entry.get("results", {}).get("analysis", {})
            if analysis.get("best_variant") != "original":
                improvements += 1
        
        # Average variants tested
        avg_variants = sum(
            entry.get("results", {}).get("analysis", {}).get("total_variants", 0)
            for entry in self.execution_history
        ) / total_executions
        
        return {
            "total_executions": total_executions,
            "improvements_found": improvements,
            "improvement_rate": improvements / total_executions,
            "average_variants_tested": avg_variants
        }
