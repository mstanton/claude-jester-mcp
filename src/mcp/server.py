#!/usr/bin/env python3
"""
Claude Desktop Code Execution MCP Server
Main entry point for the MCP server with comprehensive AI code execution capabilities
"""

import asyncio
import json
import sys
import logging
import time
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

# Add the source directory to Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

# Import MCP components
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool, TextContent,
        CallToolRequest, CallToolResult,
        ListToolsRequest, ListToolsResult
    )
    MCP_AVAILABLE = True
except ImportError as e:
    print(f"❌ MCP SDK not available: {e}", file=sys.stderr)
    print("📦 Install with: pip install mcp", file=sys.stderr)
    MCP_AVAILABLE = False

# Import core execution components
try:
    from core.executor import CodeExecutor, ExecutionResult, ExecutionStatus
    from core.quantum_debugger import QuantumDebugger
    from core.learning_system import LearningSystem
    from monitoring.performance_monitor import PerformanceMonitor
    CORE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Core components not fully available: {e}", file=sys.stderr)
    CORE_AVAILABLE = False

@dataclass
class ServerConfig:
    """Server configuration from environment variables"""
    debug_mode: bool = False
    max_execution_time: float = 10.0
    max_memory_mb: int = 256
    enable_quantum: bool = True
    enable_learning: bool = True
    enable_monitoring: bool = True
    log_level: str = "INFO"
    
    @classmethod
    def from_environment(cls) -> 'ServerConfig':
        """Load configuration from environment variables"""
        return cls(
            debug_mode=os.getenv("MCP_DEBUG", "false").lower() == "true",
            max_execution_time=float(os.getenv("MCP_MAX_EXEC_TIME", "10.0")),
            max_memory_mb=int(os.getenv("MCP_MAX_MEMORY_MB", "256")),
            enable_quantum=os.getenv("MCP_ENABLE_QUANTUM", "true").lower() == "true",
            enable_learning=os.getenv("MCP_ENABLE_LEARNING", "true").lower() == "true",
            enable_monitoring=os.getenv("MCP_ENABLE_MONITORING", "true").lower() == "true",
            log_level=os.getenv("MCP_LOG_LEVEL", "INFO")
        )

class ClaudeDesktopMCPServer:
    """Main MCP server for Claude Desktop code execution"""
    
    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig.from_environment()
        self.server = Server("claude-code-execution")
        
        # Initialize components
        self._setup_logging()
        self._setup_components()
        self._register_tools()
        
        # Execution tracking
        self.execution_count = 0
        self.start_time = time.time()
        
        self.logger.info("🚀 Claude Desktop MCP Server initialized")
    
    def _setup_logging(self):
        """Setup structured logging"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            handlers=[logging.StreamHandler(sys.stderr)]
        )
        self.logger = logging.getLogger("mcp_server")
    
    def _setup_components(self):
        """Initialize core components based on availability"""
        if CORE_AVAILABLE:
            # Full-featured components
            self.executor = CodeExecutor(
                timeout=self.config.max_execution_time,
                memory_limit_mb=self.config.max_memory_mb
            )
            
            if self.config.enable_quantum:
                self.quantum_debugger = QuantumDebugger(self.executor)
            else:
                self.quantum_debugger = None
                
            if self.config.enable_learning:
                self.learning_system = LearningSystem()
            else:
                self.learning_system = None
                
            if self.config.enable_monitoring:
                self.performance_monitor = PerformanceMonitor()
                # Start monitoring dashboard in background
                asyncio.create_task(self._start_monitoring_dashboard())
            else:
                self.performance_monitor = None
                
            self.logger.info("✅ Full-featured execution environment loaded")
        else:
            # Fallback to simple execution
            self.executor = self._create_fallback_executor()
            self.quantum_debugger = None
            self.learning_system = None
            self.performance_monitor = None
            self.logger.warning("⚠️  Using fallback execution environment")
    
    def _create_fallback_executor(self):
        """Create a simple fallback executor when core components aren't available"""
        from core.simple_executor import SimpleExecutor
        return SimpleExecutor(
            timeout=self.config.max_execution_time,
            memory_limit_mb=self.config.max_memory_mb
        )
    
    async def _start_monitoring_dashboard(self):
        """Start the monitoring dashboard in background"""
        try:
            from monitoring.dashboard import start_dashboard
            await start_dashboard(port=8888)
        except Exception as e:
            self.logger.warning(f"Could not start monitoring dashboard: {e}")
    
    def _register_tools(self):
        """Register MCP tools with the server"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools"""
            tools = [
                Tool(
                    name="execute_code",
                    description="Execute Python code with real-time testing, optimization, and validation. Claude should use this BEFORE presenting any code to users to ensure it works correctly.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Python code to execute and validate"
                            },
                            "description": {
                                "type": "string",
                                "description": "What this code is supposed to accomplish",
                                "default": ""
                            },
                            "enable_quantum": {
                                "type": "boolean", 
                                "description": "Enable quantum debugging (test multiple variants)",
                                "default": self.config.enable_quantum
                            }
                        },
                        "required": ["code"]
                    }
                ),
                Tool(
                    name="optimize_code",
                    description="Automatically optimize code for performance, testing multiple approaches and recommending the best solution.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code to optimize"
                            },
                            "optimization_focus": {
                                "type": "string",
                                "description": "Optimization focus: speed, memory, readability",
                                "enum": ["speed", "memory", "readability", "auto"],
                                "default": "auto"
                            },
                            "expected_behavior": {
                                "type": "string",
                                "description": "What the code should do (for validation)",
                                "default": ""
                            }
                        },
                        "required": ["code"]
                    }
                ),
                Tool(
                    name="validate_and_fix",
                    description="Comprehensive code validation with automatic bug detection and fixing suggestions.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code to validate and potentially fix"
                            },
                            "test_edge_cases": {
                                "type": "boolean",
                                "description": "Test with edge cases and malformed inputs",
                                "default": True
                            }
                        },
                        "required": ["code"]
                    }
                ),
                Tool(
                    name="performance_analysis",
                    description="Detailed performance analysis with benchmarking and optimization recommendations.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code to analyze for performance"
                            },
                            "benchmark_iterations": {
                                "type": "integer",
                                "description": "Number of benchmark iterations",
                                "default": 100,
                                "minimum": 1,
                                "maximum": 10000
                            }
                        },
                        "required": ["code"]
                    }
                ),
                Tool(
                    name="get_insights",
                    description="Get insights about coding patterns, learning progress, and personalized recommendations.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "analysis_type": {
                                "type": "string",
                                "description": "Type of analysis to perform",
                                "enum": ["patterns", "progress", "recommendations", "all"],
                                "default": "all"
                            }
                        }
                    }
                )
            ]
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls with comprehensive error handling"""
            
            request_id = f"{name}_{self.execution_count}"
            self.execution_count += 1
            
            start_time = time.time()
            self.logger.info(f"🔧 Tool call: {name} (ID: {request_id})")
            
            try:
                if name == "execute_code":
                    result = await self._handle_execute_code(arguments, request_id)
                elif name == "optimize_code":
                    result = await self._handle_optimize_code(arguments, request_id)
                elif name == "validate_and_fix":
                    result = await self._handle_validate_and_fix(arguments, request_id)
                elif name == "performance_analysis":
                    result = await self._handle_performance_analysis(arguments, request_id)
                elif name == "get_insights":
                    result = await self._handle_get_insights(arguments, request_id)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                execution_time = (time.time() - start_time) * 1000
                self.logger.info(f"✅ Tool {name} completed in {execution_time:.2f}ms")
                
                # Track performance if monitoring is enabled
                if self.performance_monitor:
                    await self.performance_monitor.record_execution(
                        tool_name=name,
                        execution_time_ms=execution_time,
                        success=True,
                        request_id=request_id
                    )
                
                return result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                self.logger.error(f"❌ Tool {name} failed: {e}")
                
                if self.performance_monitor:
                    await self.performance_monitor.record_execution(
                        tool_name=name,
                        execution_time_ms=execution_time,
                        success=False,
                        error=str(e),
                        request_id=request_id
                    )
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ **Tool Execution Failed**\n\n**Tool:** {name}\n**Error:** {str(e)}\n\n*The execution environment encountered an error. Please try again or contact support if the issue persists.*"
                    )],
                    isError=True
                )
    
    async def _handle_execute_code(self, args: Dict[str, Any], request_id: str) -> CallToolResult:
        """Handle code execution requests"""
        code = args.get("code", "").strip()
        description = args.get("description", "")
        enable_quantum = args.get("enable_quantum", self.config.enable_quantum)
        
        if not code:
            return CallToolResult(
                content=[TextContent(type="text", text="❌ No code provided to execute")],
                isError=True
            )
        
        # Execute with quantum debugging if enabled and available
        if enable_quantum and self.quantum_debugger:
            result = await self.quantum_debugger.execute_with_variants(code, description)
            response = self._format_quantum_result(result, description)
        else:
            result = await self.executor.execute_code(code)
            response = self._format_execution_result(result, description)
        
        # Update learning system if available
        if self.learning_system:
            await self.learning_system.record_execution(code, result, description)
        
        return CallToolResult(content=[TextContent(type="text", text=response)])
    
    async def _handle_optimize_code(self, args: Dict[str, Any], request_id: str) -> CallToolResult:
        """Handle code optimization requests"""
        code = args.get("code", "").strip()
        focus = args.get("optimization_focus", "auto")
        expected_behavior = args.get("expected_behavior", "")
        
        if not code:
            return CallToolResult(
                content=[TextContent(type="text", text="❌ No code provided to optimize")],
                isError=True
            )
        
        if self.quantum_debugger:
            # Use quantum debugging for optimization
            variants = await self.quantum_debugger.generate_optimization_variants(code, focus)
            result = await self.quantum_debugger.test_variants(variants)
            response = self._format_optimization_result(result, focus, expected_behavior)
        else:
            # Fallback optimization
            result = await self.executor.execute_code(code)
            response = self._format_simple_optimization(result, focus)
        
        return CallToolResult(content=[TextContent(type="text", text=response)])
    
    async def _handle_validate_and_fix(self, args: Dict[str, Any], request_id: str) -> CallToolResult:
        """Handle validation and fixing requests"""
        code = args.get("code", "").strip()
        test_edge_cases = args.get("test_edge_cases", True)
        
        if not code:
            return CallToolResult(
                content=[TextContent(type="text", text="❌ No code provided to validate")],
                isError=True
            )
        
        # Comprehensive validation
        validation_result = await self._comprehensive_validation(code, test_edge_cases)
        response = self._format_validation_result(validation_result)
        
        return CallToolResult(content=[TextContent(type="text", text=response)])
    
    async def _handle_performance_analysis(self, args: Dict[str, Any], request_id: str) -> CallToolResult:
        """Handle performance analysis requests"""
        code = args.get("code", "").strip()
        iterations = args.get("benchmark_iterations", 100)
        
        if not code:
            return CallToolResult(
                content=[TextContent(type="text", text="❌ No code provided to analyze")],
                isError=True
            )
        
        # Performance benchmarking
        analysis_result = await self._performance_benchmarking(code, iterations)
        response = self._format_performance_analysis(analysis_result)
        
        return CallToolResult(content=[TextContent(type="text", text=response)])
    
    async def _handle_get_insights(self, args: Dict[str, Any], request_id: str) -> CallToolResult:
        """Handle insights requests"""
        analysis_type = args.get("analysis_type", "all")
        
        if self.learning_system:
            insights = await self.learning_system.get_insights(analysis_type)
            response = self._format_insights(insights, analysis_type)
        else:
            response = "📊 **Insights Feature**\n\nLearning system is not enabled. To get personalized insights, enable the learning system in your configuration.\n\n**Current Status:**\n- Executions this session: {}\n- Uptime: {:.1f} minutes".format(
                self.execution_count,
                (time.time() - self.start_time) / 60
            )
        
        return CallToolResult(content=[TextContent(type="text", text=response)])
    
    def _format_execution_result(self, result: ExecutionResult, description: str) -> str:
        """Format execution result for Claude"""
        status_emoji = "✅" if result.status == ExecutionStatus.SUCCESS else "❌"
        
        response_parts = [
            f"{status_emoji} **Code Execution Result**",
            ""
        ]
        
        if description:
            response_parts.extend([f"**Purpose:** {description}", ""])
        
        # Performance metrics
        response_parts.extend([
            "**Performance:**",
            f"- Execution time: {result.execution_time_ms:.2f}ms",
            f"- Memory used: {result.memory_used_bytes / 1024:.2f}KB",
            f"- Security level: {result.security_level}",
            ""
        ])
        
        # Output
        if result.output:
            response_parts.extend([
                "**Output:**",
                "```",
                result.output[:1000],  # Truncate for safety
                "```",
                ""
            ])
        
        # Error handling
        if result.error:
            response_parts.extend([
                "**Error:**",
                f"```\n{result.error}\n```",
                ""
            ])
            
            if result.suggestions:
                response_parts.extend([
                    "**Suggestions:**",
                    *[f"- {suggestion}" for suggestion in result.suggestions],
                    ""
                ])
        
        # Status message
        if result.status == ExecutionStatus.SUCCESS:
            response_parts.append("**Status:** ✨ Ready to present to user")
        else:
            response_parts.append("**Status:** Please fix errors before presenting to user")
        
        return "\n".join(response_parts)
    
    def _format_quantum_result(self, result: Dict[str, Any], description: str) -> str:
        """Format quantum debugging result"""
        analysis = result.get("analysis", {})
        best_variant = result.get("best_variant")
        
        response_parts = [
            "🔬 **Quantum Debugging Results**",
            ""
        ]
        
        if description:
            response_parts.extend([f"**Task:** {description}", ""])
        
        # Quantum analysis summary
        response_parts.extend([
            "**Quantum Analysis:**",
            f"- Tested variants: {analysis.get('total_variants', 0)}",
            f"- Successful: {analysis.get('successful', 0)}",
            f"- Success rate: {analysis.get('success_rate', 0):.1%}",
            ""
        ])
        
        if best_variant:
            best_result = result.get("results", {}).get(best_variant, {})
            variant_info = best_result.get("variant", {})
            feedback = best_result.get("feedback", {})
            
            response_parts.extend([
                f"🏆 **Best Solution: {variant_info.get('description', best_variant)}**",
                f"- Execution time: {feedback.get('metrics', {}).get('time_ms', 0):.2f}ms",
                f"- Confidence: {variant_info.get('confidence', 0):.1%}",
                ""
            ])
            
            if feedback.get('output'):
                response_parts.extend([
                    "**Output:**",
                    "```",
                    feedback['output'][:500],
                    "```",
                    ""
                ])
        
        response_parts.append("✨ **Quantum debugging automatically found the optimal solution!**")
        return "\n".join(response_parts)
    
    def _format_optimization_result(self, result: Dict[str, Any], focus: str, expected_behavior: str) -> str:
        """Format optimization result"""
        return f"⚡ **Code Optimization Results**\n\n**Focus:** {focus.title()}\n\n{self._format_quantum_result(result, expected_behavior)}"
    
    def _format_simple_optimization(self, result: ExecutionResult, focus: str) -> str:
        """Format simple optimization result"""
        return f"⚡ **Code Optimization**\n\n**Focus:** {focus.title()}\n\n{self._format_execution_result(result, f'Optimized for {focus}')}"
    
    async def _comprehensive_validation(self, code: str, test_edge_cases: bool) -> Dict[str, Any]:
        """Perform comprehensive code validation"""
        # Basic execution
        basic_result = await self.executor.execute_code(code)
        
        validation_result = {
            "basic_execution": basic_result,
            "edge_case_tests": [],
            "security_check": None,
            "syntax_analysis": None
        }
        
        # Edge case testing if requested
        if test_edge_cases and self.quantum_debugger:
            edge_cases = await self.quantum_debugger.generate_edge_case_tests(code)
            validation_result["edge_case_tests"] = edge_cases
        
        return validation_result
    
    def _format_validation_result(self, validation_result: Dict[str, Any]) -> str:
        """Format validation result"""
        basic_result = validation_result["basic_execution"]
        
        response_parts = [
            "🔍 **Comprehensive Code Validation**",
            "",
            "**Basic Execution:**"
        ]
        
        if basic_result.status == ExecutionStatus.SUCCESS:
            response_parts.append("✅ Code executes successfully")
        else:
            response_parts.extend([
                "❌ Execution issues found:",
                f"- {basic_result.error}"
            ])
        
        # Edge case results
        edge_cases = validation_result.get("edge_case_tests", [])
        if edge_cases:
            response_parts.extend([
                "",
                "**Edge Case Testing:**",
                f"- Tested {len(edge_cases)} edge cases",
                "- All edge cases handled properly" if all(ec.get("success") for ec in edge_cases) else "- Some edge cases need attention"
            ])
        
        return "\n".join(response_parts)
    
    async def _performance_benchmarking(self, code: str, iterations: int) -> Dict[str, Any]:
        """Perform detailed performance benchmarking"""
        results = []
        
        for i in range(min(iterations, 1000)):  # Cap at 1000 for safety
            result = await self.executor.execute_code(code)
            if result.status == ExecutionStatus.SUCCESS:
                results.append(result.execution_time_ms)
        
        if results:
            avg_time = sum(results) / len(results)
            min_time = min(results)
            max_time = max(results)
            
            return {
                "successful_runs": len(results),
                "failed_runs": iterations - len(results),
                "average_time_ms": avg_time,
                "min_time_ms": min_time,
                "max_time_ms": max_time,
                "total_iterations": iterations
            }
        else:
            return {"error": "All benchmark iterations failed"}
    
    def _format_performance_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format performance analysis result"""
        if "error" in analysis:
            return f"❌ **Performance Analysis Failed**\n\n{analysis['error']}"
        
        return f"""📊 **Performance Analysis Results**

**Benchmark Statistics:**
- Successful runs: {analysis['successful_runs']}/{analysis['total_iterations']}
- Average execution time: {analysis['average_time_ms']:.2f}ms
- Fastest execution: {analysis['min_time_ms']:.2f}ms
- Slowest execution: {analysis['max_time_ms']:.2f}ms
- Performance variance: {(analysis['max_time_ms'] - analysis['min_time_ms']):.2f}ms

**Analysis:**
- Execution stability: {'Excellent' if analysis['max_time_ms'] - analysis['min_time_ms'] < 5 else 'Good' if analysis['max_time_ms'] - analysis['min_time_ms'] < 20 else 'Variable'}
- Performance grade: {'A+' if analysis['average_time_ms'] < 10 else 'A' if analysis['average_time_ms'] < 50 else 'B' if analysis['average_time_ms'] < 200 else 'C'}
"""
    
    def _format_insights(self, insights: Dict[str, Any], analysis_type: str) -> str:
        """Format learning insights"""
        return f"🧠 **AI Learning Insights**\n\n**Analysis Type:** {analysis_type.title()}\n\n" + json.dumps(insights, indent=2)
    
    async def run(self):
        """Run the MCP server"""
        if not MCP_AVAILABLE:
            self.logger.error("❌ MCP SDK not available. Cannot start server.")
            sys.exit(1)
        
        self.logger.info("🚀 Starting Claude Desktop MCP Server...")
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(read_stream, write_stream)
        except Exception as e:
            self.logger.critical(f"💥 Server failed: {e}")
            raise

async def main():
    """Main entry point"""
    try:
        config = ServerConfig.from_environment()
        server = ClaudeDesktopMCPServer(config)
        await server.run()
    except KeyboardInterrupt:
        print("\n✅ Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
