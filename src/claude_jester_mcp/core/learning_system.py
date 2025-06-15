#!/usr/bin/env python3
"""
Adaptive Learning System
Learns from user coding patterns and execution outcomes to personalize AI assistance
"""

import asyncio
import json
import time
import hashlib
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta
import re
import ast

from .executor import ExecutionResult, ExecutionStatus

@dataclass
class CodingPattern:
    """Represents a learned coding pattern"""
    pattern_id: str
    pattern_type: str  # style, error, preference, optimization
    description: str
    code_examples: List[str]
    frequency: int
    confidence: float
    last_seen: datetime
    success_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['last_seen'] = self.last_seen.isoformat()
        return result

@dataclass
class UserPreference:
    """User coding preferences learned over time"""
    preference_type: str
    value: Any
    confidence: float
    evidence_count: int
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['last_updated'] = self.last_updated.isoformat()
        return result

class PatternExtractor:
    """Extracts patterns from code and execution results"""
    
    def extract_code_patterns(self, code: str) -> List[Dict[str, Any]]:
        """Extract patterns from code structure and style"""
        patterns = []
        
        try:
            tree = ast.parse(code)
            
            # Function definition patterns
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    patterns.append({
                        "type": "function_style",
                        "name": node.name,
                        "has_docstring": bool(ast.get_docstring(node)),
                        "has_type_hints": any(arg.annotation for arg in node.args.args),
                        "arg_count": len(node.args.args)
                    })
                
                elif isinstance(node, ast.For):
                    # Loop patterns
                    patterns.append({
                        "type": "loop_style",
                        "uses_enumerate": self._uses_enumerate(node),
                        "nested": self._is_nested_loop(node, tree)
                    })
                
                elif isinstance(node, ast.ListComp):
                    patterns.append({
                        "type": "comprehension_usage",
                        "complexity": self._get_comprehension_complexity(node)
                    })
                
                elif isinstance(node, ast.Try):
                    patterns.append({
                        "type": "error_handling",
                        "has_finally": bool(node.finalbody),
                        "exception_count": len(node.handlers),
                        "specific_exceptions": self._get_exception_types(node)
                    })
        
        except SyntaxError:
            # If code has syntax errors, extract basic patterns
            patterns.extend(self._extract_text_patterns(code))
        
        return patterns
    
    def extract_style_preferences(self, code: str) -> Dict[str, Any]:
        """Extract coding style preferences"""
        preferences = {}
        
        # Indentation preference
        lines = code.split('\n')
        indented_lines = [line for line in lines if line.startswith((' ', '\t'))]
        if indented_lines:
            spaces = sum(1 for line in indented_lines if line.startswith('    '))
            tabs = sum(1 for line in indented_lines if line.startswith('\t'))
            preferences['indentation'] = 'spaces' if spaces > tabs else 'tabs'
            if spaces > 0:
                # Detect space count
                space_counts = []
                for line in indented_lines:
                    if line.startswith(' '):
                        count = len(line) - len(line.lstrip(' '))
                        space_counts.append(count)
                if space_counts:
                    preferences['spaces_per_indent'] = max(set(space_counts), key=space_counts.count)
        
        # Naming conventions
        function_names = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
        variable_names = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=', code)
        
        if function_names:
            snake_case = sum(1 for name in function_names if '_' in name and name.islower())
            camel_case = sum(1 for name in function_names if any(c.isupper() for c in name[1:]))
            preferences['function_naming'] = 'snake_case' if snake_case > camel_case else 'camelCase'
        
        # String quote preference
        single_quotes = code.count("'")
        double_quotes = code.count('"')
        if single_quotes + double_quotes > 0:
            preferences['quote_style'] = 'single' if single_quotes > double_quotes else 'double'
        
        # Line length preference
        max_line_length = max(len(line) for line in lines) if lines else 0
        preferences['max_line_length'] = max_line_length
        
        return preferences
    
    def extract_error_patterns(self, code: str, error: str) -> List[Dict[str, Any]]:
        """Extract patterns from errors to help prevent similar issues"""
        patterns = []
        
        if "NameError" in error:
            # Extract undefined variables
            match = re.search(r"name '([^']+)' is not defined", error)
            if match:
                var_name = match.group(1)
                patterns.append({
                    "type": "undefined_variable",
                    "variable": var_name,
                    "likely_typo": self._check_typo_candidates(var_name, code)
                })
        
        elif "IndentationError" in error:
            patterns.append({
                "type": "indentation_error",
                "inconsistent_indentation": "inconsistent" in error.lower(),
                "expected_indent": "expected an indented block" in error.lower()
            })
        
        elif "SyntaxError" in error:
            patterns.append({
                "type": "syntax_error",
                "missing_colon": "invalid syntax" in error and any(keyword in code for keyword in ["if", "for", "while", "def", "class"]),
                "unmatched_parentheses": "(" in code and ")" in code and code.count("(") != code.count(")")
            })
        
        elif "TypeError" in error:
            patterns.append({
                "type": "type_error",
                "operation_mismatch": True,
                "error_detail": error
            })
        
        return patterns
    
    def _uses_enumerate(self, for_node: ast.For) -> bool:
        """Check if for loop uses enumerate"""
        if isinstance(for_node.iter, ast.Call):
            if isinstance(for_node.iter.func, ast.Name):
                return for_node.iter.func.id == 'enumerate'
        return False
    
    def _is_nested_loop(self, for_node: ast.For, tree: ast.AST) -> bool:
        """Check if for loop is nested inside another loop"""
        for parent in ast.walk(tree):
            if isinstance(parent, (ast.For, ast.While)) and parent != for_node:
                for child in ast.walk(parent):
                    if child == for_node:
                        return True
        return False
    
    def _get_comprehension_complexity(self, comp_node: ast.ListComp) -> str:
        """Assess list comprehension complexity"""
        if len(comp_node.generators) > 1:
            return "multiple_generators"
        elif any(comp_node.generators[0].ifs):
            return "with_conditions"
        else:
            return "simple"
    
    def _get_exception_types(self, try_node: ast.Try) -> List[str]:
        """Get specific exception types from try block"""
        exception_types = []
        for handler in try_node.handlers:
            if handler.type:
                if isinstance(handler.type, ast.Name):
                    exception_types.append(handler.type.id)
        return exception_types
    
    def _extract_text_patterns(self, code: str) -> List[Dict[str, Any]]:
        """Extract patterns from code text when AST parsing fails"""
        patterns = []
        
        # Import patterns
        import_lines = [line.strip() for line in code.split('\n') if line.strip().startswith('import') or line.strip().startswith('from')]
        if import_lines:
            patterns.append({
                "type": "import_style",
                "import_count": len(import_lines),
                "uses_from_import": any(line.startswith('from') for line in import_lines)
            })
        
        return patterns
    
    def _check_typo_candidates(self, undefined_var: str, code: str) -> List[str]:
        """Find potential typo candidates for undefined variables"""
        # Extract all defined variables
        defined_vars = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=', code)
        
        candidates = []
        for var in defined_vars:
            if self._is_similar(undefined_var, var):
                candidates.append(var)
        
        return candidates[:3]  # Return top 3 candidates
    
    def _is_similar(self, str1: str, str2: str) -> bool:
        """Check if two strings are similar (simple edit distance)"""
        if abs(len(str1) - len(str2)) > 2:
            return False
        
        # Simple character-by-character comparison
        differences = sum(1 for a, b in zip(str1, str2) if a != b)
        return differences <= 2

class LearningSystem:
    """Main learning system that adapts to user patterns"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".claude_mcp" / "learning"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.pattern_extractor = PatternExtractor()
        
        # Learning data structures
        self.coding_patterns: Dict[str, CodingPattern] = {}
        self.user_preferences: Dict[str, UserPreference] = {}
        self.execution_history = deque(maxlen=1000)
        self.error_history = deque(maxlen=500)
        
        # Load existing data
        self._load_learning_data()
        
        # Learning configuration
        self.min_pattern_frequency = 3
        self.confidence_threshold = 0.7
        self.decay_factor = 0.95  # How much old patterns decay over time
        
    async def record_execution(self, code: str, result: ExecutionResult, description: str = ""):
        """Record a code execution for learning"""
        
        execution_record = {
            "timestamp": datetime.now(),
            "code": code,
            "code_hash": hashlib.md5(code.encode()).hexdigest(),
            "result": result.to_dict(),
            "description": description,
            "success": result.status == ExecutionStatus.SUCCESS
        }
        
        self.execution_history.append(execution_record)
        
        # Extract and update patterns
        await self._update_patterns(code, result)
        
        # Update preferences
        self._update_preferences(code, result)
        
        # Save learning data periodically
        if len(self.execution_history) % 10 == 0:
            await self._save_learning_data()
    
    async def _update_patterns(self, code: str, result: ExecutionResult):
        """Update learned patterns based on execution"""
        
        # Extract code patterns
        code_patterns = self.pattern_extractor.extract_code_patterns(code)
        
        for pattern_data in code_patterns:
            pattern_id = self._generate_pattern_id(pattern_data)
            
            if pattern_id in self.coding_patterns:
                # Update existing pattern
                pattern = self.coding_patterns[pattern_id]
                pattern.frequency += 1
                pattern.last_seen = datetime.now()
                
                # Update success rate
                if result.status == ExecutionStatus.SUCCESS:
                    pattern.success_rate = (pattern.success_rate * (pattern.frequency - 1) + 1.0) / pattern.frequency
                else:
                    pattern.success_rate = (pattern.success_rate * (pattern.frequency - 1) + 0.0) / pattern.frequency
                
                # Update confidence based on frequency and success rate
                pattern.confidence = min(0.95, pattern.frequency / 10 * pattern.success_rate)
                
            else:
                # Create new pattern
                pattern = CodingPattern(
                    pattern_id=pattern_id,
                    pattern_type=pattern_data["type"],
                    description=self._generate_pattern_description(pattern_data),
                    code_examples=[code[:200]],  # Store snippet
                    frequency=1,
                    confidence=0.1,  # Start with low confidence
                    last_seen=datetime.now(),
                    success_rate=1.0 if result.status == ExecutionStatus.SUCCESS else 0.0
                )
                self.coding_patterns[pattern_id] = pattern
        
        # Handle error patterns
        if result.status != ExecutionStatus.SUCCESS:
            error_patterns = self.pattern_extractor.extract_error_patterns(code, result.error)
            for pattern_data in error_patterns:
                self.error_history.append({
                    "timestamp": datetime.now(),
                    "code": code,
                    "error": result.error,
                    "pattern": pattern_data
                })
    
    def _update_preferences(self, code: str, result: ExecutionResult):
        """Update user preferences based on successful code patterns"""
        
        if result.status != ExecutionStatus.SUCCESS:
            return  # Only learn from successful code
        
        style_prefs = self.pattern_extractor.extract_style_preferences(code)
        
        for pref_type, value in style_prefs.items():
            if pref_type in self.user_preferences:
                # Update existing preference
                pref = self.user_preferences[pref_type]
                if pref.value == value:
                    pref.evidence_count += 1
                    pref.confidence = min(0.95, pref.evidence_count / 20)  # Cap at 95%
                    pref.last_updated = datetime.now()
                else:
                    # Conflicting preference - reduce confidence
                    pref.confidence *= 0.9
            else:
                # New preference
                self.user_preferences[pref_type] = UserPreference(
                    preference_type=pref_type,
                    value=value,
                    confidence=0.1,
                    evidence_count=1,
                    last_updated=datetime.now()
                )
    
    async def get_insights(self, analysis_type: str = "all") -> Dict[str, Any]:
        """Get learning insights and recommendations"""
        
        insights = {}
        
        if analysis_type in ["patterns", "all"]:
            insights["patterns"] = await self._analyze_patterns()
        
        if analysis_type in ["progress", "all"]:
            insights["progress"] = self._analyze_progress()
        
        if analysis_type in ["recommendations", "all"]:
            insights["recommendations"] = await self._generate_recommendations()
        
        return insights
    
    async def _analyze_patterns(self) -> Dict[str, Any]:
        """Analyze learned coding patterns"""
        
        # Group patterns by type
        pattern_types = defaultdict(list)
        for pattern in self.coding_patterns.values():
            pattern_types[pattern.pattern_type].append(pattern)
        
        # Find dominant patterns
        dominant_patterns = {}
        for pattern_type, patterns in pattern_types.items():
            # Sort by frequency and confidence
            sorted_patterns = sorted(
                patterns, 
                key=lambda p: p.frequency * p.confidence, 
                reverse=True
            )
            if sorted_patterns:
                dominant_patterns[pattern_type] = sorted_patterns[0].to_dict()
        
        # Calculate pattern diversity
        total_patterns = len(self.coding_patterns)
        type_counts = {ptype: len(patterns) for ptype, patterns in pattern_types.items()}
        
        return {
            "total_patterns": total_patterns,
            "pattern_types": dict(type_counts),
            "dominant_patterns": dominant_patterns,
            "pattern_diversity": len(pattern_types) / max(total_patterns, 1)
        }
    
    def _analyze_progress(self) -> Dict[str, Any]:
        """Analyze learning progress over time"""
        
        if not self.execution_history:
            return {"message": "No execution history available"}
        
        # Calculate success rate over time
        recent_executions = list(self.execution_history)[-50:]  # Last 50 executions
        older_executions = list(self.execution_history)[-100:-50]  # Previous 50
        
        recent_success_rate = sum(1 for ex in recent_executions if ex["success"]) / len(recent_executions)
        older_success_rate = sum(1 for ex in older_executions if ex["success"]) / len(older_executions) if older_executions else 0
        
        # Calculate learning velocity
        confidence_sum = sum(p.confidence for p in self.coding_patterns.values())
        avg_confidence = confidence_sum / len(self.coding_patterns) if self.coding_patterns else 0
        
        # Error reduction analysis
        recent_errors = [ex for ex in recent_executions if not ex["success"]]
        older_errors = [ex for ex in older_executions if not ex["success"]]
        
        return {
            "total_executions": len(self.execution_history),
            "recent_success_rate": recent_success_rate,
            "older_success_rate": older_success_rate,
            "success_improvement": recent_success_rate - older_success_rate,
            "average_pattern_confidence": avg_confidence,
            "recent_error_count": len(recent_errors),
            "older_error_count": len(older_errors),
            "learning_velocity": avg_confidence * len(self.coding_patterns)
        }
    
    async def _generate_recommendations(self) -> Dict[str, Any]:
        """Generate personalized recommendations"""
        
        recommendations = {
            "style_suggestions": [],
            "error_prevention": [],
            "optimization_opportunities": [],
            "learning_focus": []
        }
        
        # Style recommendations based on preferences
        for pref_type, pref in self.user_preferences.items():
            if pref.confidence > self.confidence_threshold:
                if pref_type == "indentation" and pref.value == "tabs":
                    recommendations["style_suggestions"].append(
                        "Consider using 4 spaces instead of tabs for better cross-platform compatibility"
                    )
                elif pref_type == "max_line_length" and pref.value > 100:
                    recommendations["style_suggestions"].append(
                        "Consider keeping lines under 88 characters for better readability"
                    )
        
        # Error prevention based on common patterns
        error_types = defaultdict(int)
        for error_record in self.error_history:
            if error_record["pattern"]:
                error_types[error_record["pattern"]["type"]] += 1
        
        if error_types:
            most_common_error = max(error_types, key=error_types.get)
            if most_common_error == "undefined_variable":
                recommendations["error_prevention"].append(
                    "Use an IDE with variable name checking to catch undefined variables early"
                )
            elif most_common_error == "indentation_error":
                recommendations["error_prevention"].append(
                    "Configure your editor to show whitespace characters and use consistent indentation"
                )
        
        # Learning focus areas
        pattern_strengths = defaultdict(float)
        for pattern in self.coding_patterns.values():
            pattern_strengths[pattern.pattern_type] += pattern.confidence
        
        weak_areas = [ptype for ptype, strength in pattern_strengths.items() if strength < 2.0]
        if weak_areas:
            recommendations["learning_focus"].extend([
                f"Practice {area.replace('_', ' ')} patterns to improve consistency"
                for area in weak_areas[:3]
            ])
        
        return recommendations
    
    def get_user_coding_dna(self) -> Dict[str, Any]:
        """Generate a comprehensive 'Coding DNA' profile"""
        
        dna = {
            "style_profile": {},
            "strength_areas": [],
            "improvement_areas": [],
            "coding_personality": "",
            "experience_level": "",
            "preferences": {}
        }
        
        # Build style profile
        for pref_type, pref in self.user_preferences.items():
            if pref.confidence > 0.5:
                dna["style_profile"][pref_type] = pref.value
                dna["preferences"][pref_type] = {
                    "value": pref.value,
                    "confidence": f"{pref.confidence:.0%}"
                }
        
        # Identify strengths (patterns with high success rates)
        strengths = []
        for pattern in self.coding_patterns.values():
            if pattern.success_rate > 0.8 and pattern.frequency >= self.min_pattern_frequency:
                strengths.append(pattern.pattern_type.replace('_', ' ').title())
        dna["strength_areas"] = strengths[:5]
        
        # Identify improvement areas (frequent error patterns)
        error_counts = defaultdict(int)
        for error_record in self.error_history:
            if error_record["pattern"]:
                error_counts[error_record["pattern"]["type"]] += 1
        
        improvement_areas = [
            error_type.replace('_', ' ').title()
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        ]
        dna["improvement_areas"] = improvement_areas
        
        # Determine coding personality
        personality_traits = []
        if any("error_handling" in p.pattern_type for p in self.coding_patterns.values() if p.confidence > 0.7):
            personality_traits.append("Defensive Programmer")
        if any("comprehension" in p.pattern_type for p in self.coding_patterns.values() if p.confidence > 0.7):
            personality_traits.append("Pythonic")
        if any("optimization" in p.pattern_type for p in self.coding_patterns.values() if p.confidence > 0.7):
            personality_traits.append("Performance-Focused")
        
        dna["coding_personality"] = " & ".join(personality_traits) if personality_traits else "Developing Style"
        
        # Estimate experience level
        total_executions = len(self.execution_history)
        avg_confidence = sum(p.confidence for p in self.coding_patterns.values()) / len(self.coding_patterns) if self.coding_patterns else 0
        
        if total_executions < 20 or avg_confidence < 0.3:
            dna["experience_level"] = "Beginner"
        elif total_executions < 100 or avg_confidence < 0.6:
            dna["experience_level"] = "Intermediate"
        else:
            dna["experience_level"] = "Advanced"
        
        return dna
    
    def _generate_pattern_id(self, pattern_data: Dict[str, Any]) -> str:
        """Generate a unique ID for a pattern"""
        pattern_str = json.dumps(pattern_data, sort_keys=True)
        return hashlib.md5(pattern_str.encode()).hexdigest()[:16]
    
    def _generate_pattern_description(self, pattern_data: Dict[str, Any]) -> str:
        """Generate a human-readable description for a pattern"""
        pattern_type = pattern_data["type"]
        
        if pattern_type == "function_style":
            parts = []
            if pattern_data.get("has_docstring"):
                parts.append("with docstrings")
            if pattern_data.get("has_type_hints"):
                parts.append("with type hints")
            return f"Function definition {' and '.join(parts)}" if parts else "Basic function definition"
        
        elif pattern_type == "loop_style":
            if pattern_data.get("uses_enumerate"):
                return "For loop using enumerate"
            elif pattern_data.get("nested"):
                return "Nested loop structure"
            else:
                return "Basic for loop"
        
        elif pattern_type == "comprehension_usage":
            complexity = pattern_data.get("complexity", "simple")
            return f"List comprehension ({complexity})"
        
        elif pattern_type == "error_handling":
            parts = []
            if pattern_data.get("has_finally"):
                parts.append("with finally block")
            exc_count = pattern_data.get("exception_count", 0)
            if exc_count > 1:
                parts.append(f"handling {exc_count} exception types")
            return f"Try-except block {' '.join(parts)}".strip()
        
        else:
            return pattern_type.replace('_', ' ').title()
    
    async def _save_learning_data(self):
        """Save learning data to disk"""
        try:
            # Save patterns
            patterns_file = self.data_dir / "patterns.json"
            patterns_data = {pid: pattern.to_dict() for pid, pattern in self.coding_patterns.items()}
            with open(patterns_file, 'w') as f:
                json.dump(patterns_data, f, indent=2)
            
            # Save preferences
            prefs_file = self.data_dir / "preferences.json"
            prefs_data = {ptype: pref.to_dict() for ptype, pref in self.user_preferences.items()}
            with open(prefs_file, 'w') as f:
                json.dump(prefs_data, f, indent=2)
            
            # Save execution history (recent subset)
            history_file = self.data_dir / "execution_history.json"
            recent_history = [
                {
                    "timestamp": record["timestamp"].isoformat(),
                    "code_hash": record["code_hash"],
                    "success": record["success"],
                    "description": record["description"]
                }
                for record in list(self.execution_history)[-100:]  # Keep last 100
            ]
            with open(history_file, 'w') as f:
                json.dump(recent_history, f, indent=2)
        
        except Exception as e:
            # Silently handle save errors to not disrupt operation
            pass
    
    def _load_learning_data(self):
        """Load learning data from disk"""
        try:
            # Load patterns
            patterns_file = self.data_dir / "patterns.json"
            if patterns_file.exists():
                with open(patterns_file, 'r') as f:
                    patterns_data = json.load(f)
                
                for pid, pattern_dict in patterns_data.items():
                    pattern_dict['last_seen'] = datetime.fromisoformat(pattern_dict['last_seen'])
                    self.coding_patterns[pid] = CodingPattern(**pattern_dict)
            
            # Load preferences
            prefs_file = self.data_dir / "preferences.json"
            if prefs_file.exists():
                with open(prefs_file, 'r') as f:
                    prefs_data = json.load(f)
                
                for ptype, pref_dict in prefs_data.items():
                    pref_dict['last_updated'] = datetime.fromisoformat(pref_dict['last_updated'])
                    self.user_preferences[ptype] = UserPreference(**pref_dict)
        
        except Exception as e:
            # Start fresh if loading fails
            pass
    
    def decay_old_patterns(self, days_threshold: int = 30):
        """Decay confidence of old patterns to keep learning current"""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        for pattern in self.coding_patterns.values():
            if pattern.last_seen < cutoff_date:
                pattern.confidence *= self.decay_factor
                
        # Remove very low confidence patterns
        to_remove = [
            pid for pid, pattern in self.coding_patterns.items() 
            if pattern.confidence < 0.1
        ]
        for pid in to_remove:
            del self.coding_patterns[pid]
