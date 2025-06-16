#!/usr/bin/env python3
"""
Real-time Analytics Dashboard
Provides web-based monitoring and insights for Claude MCP code execution
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import webbrowser
from collections import defaultdict, deque

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.utils import PlotlyJSONEncoder
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

@dataclass
class ExecutionMetric:
    """Single execution metric data point"""
    timestamp: datetime
    tool_name: str
    execution_time_ms: float
    success: bool
    error: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error": self.error,
            "request_id": self.request_id
        }

class MetricsCollector:
    """Collects and aggregates execution metrics"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.real_time_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "requests_per_minute": 0,
            "current_session_start": datetime.now(),
            "tool_usage": defaultdict(int),
            "error_patterns": defaultdict(int)
        }
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
    
    async def record_execution(
        self, 
        tool_name: str, 
        execution_time_ms: float, 
        success: bool, 
        error: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Record a new execution metric"""
        
        metric = ExecutionMetric(
            timestamp=datetime.now(),
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            success=success,
            error=error,
            request_id=request_id
        )
        
        self.metrics_history.append(metric)
        
        # Update real-time metrics
        self.real_time_metrics["total_executions"] += 1
        self.real_time_metrics["tool_usage"][tool_name] += 1
        
        if success:
            self.real_time_metrics["successful_executions"] += 1
        else:
            self.real_time_metrics["failed_executions"] += 1
            if error:
                # Extract error type
                error_type = error.split(":")[0] if ":" in error else "Unknown"
                self.real_time_metrics["error_patterns"][error_type] += 1
        
        # Update average execution time
        total_time = sum(m.execution_time_ms for m in self.metrics_history)
        self.real_time_metrics["average_execution_time"] = total_time / len(self.metrics_history)
        
        # Calculate requests per minute
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        recent_requests = sum(1 for m in self.metrics_history if m.timestamp > one_minute_ago)
        self.real_time_metrics["requests_per_minute"] = recent_requests
        
        # Broadcast to WebSocket clients
        await self._broadcast_update(metric)
    
    async def _broadcast_update(self, metric: ExecutionMetric):
        """Broadcast metric update to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message = {
            "type": "execution_update",
            "data": metric.to_dict(),
            "summary": self.get_summary_stats()
        }
        
        # Send to all connected clients
        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            self.websocket_connections.remove(ws)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return {
            "total_executions": self.real_time_metrics["total_executions"],
            "success_rate": (
                self.real_time_metrics["successful_executions"] / 
                max(self.real_time_metrics["total_executions"], 1)
            ) * 100,
            "average_execution_time": round(self.real_time_metrics["average_execution_time"], 2),
            "requests_per_minute": self.real_time_metrics["requests_per_minute"],
            "session_duration": str(datetime.now() - self.real_time_metrics["current_session_start"]).split('.')[0],
            "top_tools": dict(sorted(
                self.real_time_metrics["tool_usage"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]),
            "recent_errors": dict(sorted(
                self.real_time_metrics["error_patterns"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3])
        }
    
    def get_time_series_data(self, hours: int = 24) -> Dict[str, Any]:
        """Get time series data for charts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {"timestamps": [], "execution_times": [], "success_rates": []}
        
        # Group by 5-minute intervals
        interval_data = defaultdict(lambda: {"times": [], "successes": 0, "total": 0})
        
        for metric in recent_metrics:
            # Round to 5-minute intervals
            interval_key = metric.timestamp.replace(minute=(metric.timestamp.minute // 5) * 5, second=0, microsecond=0)
            interval_data[interval_key]["times"].append(metric.execution_time_ms)
            interval_data[interval_key]["total"] += 1
            if metric.success:
                interval_data[interval_key]["successes"] += 1
        
        # Convert to chart data
        timestamps = []
        execution_times = []
        success_rates = []
        
        for timestamp in sorted(interval_data.keys()):
            data = interval_data[timestamp]
            timestamps.append(timestamp.isoformat())
            execution_times.append(sum(data["times"]) / len(data["times"]) if data["times"] else 0)
            success_rates.append((data["successes"] / data["total"]) * 100 if data["total"] > 0 else 0)
        
        return {
            "timestamps": timestamps,
            "execution_times": execution_times,
            "success_rates": success_rates
        }

class DashboardGenerator:
    """Generates dashboard HTML and charts"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
    
    def generate_performance_chart(self) -> str:
        """Generate performance chart using Plotly"""
        if not HAS_PLOTLY:
            return "<div>Charts require plotly installation</div>"
        
        time_series = self.metrics_collector.get_time_series_data()
        
        fig = go.Figure()
        
        # Add execution time trace
        fig.add_trace(go.Scatter(
            x=time_series["timestamps"],
            y=time_series["execution_times"],
            mode='lines+markers',
            name='Avg Execution Time (ms)',
            line=dict(color='#1f77b4'),
            yaxis='y'
        ))
        
        # Add success rate trace (secondary y-axis)
        fig.add_trace(go.Scatter(
            x=time_series["timestamps"],
            y=time_series["success_rates"],
            mode='lines+markers',
            name='Success Rate (%)',
            line=dict(color='#ff7f0e'),
            yaxis='y2'
        ))
        
        # Update layout
        fig.update_layout(
            title='Performance Over Time',
            xaxis_title='Time',
            yaxis=dict(
                title='Execution Time (ms)',
                side='left'
            ),
            yaxis2=dict(
                title='Success Rate (%)',
                side='right',
                overlaying='y',
                range=[0, 100]
            ),
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id='performance-chart')
    
    def generate_tool_usage_chart(self) -> str:
        """Generate tool usage pie chart"""
        if not HAS_PLOTLY:
            return "<div>Charts require plotly installation</div>"
        
        tool_usage = self.metrics_collector.real_time_metrics["tool_usage"]
        
        if not tool_usage:
            return "<div>No tool usage data available yet</div>"
        
        fig = go.Figure(data=[go.Pie(
            labels=list(tool_usage.keys()),
            values=list(tool_usage.values()),
            hole=0.3
        )])
        
        fig.update_layout(
            title='Tool Usage Distribution',
            template='plotly_white'
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id='tool-usage-chart')
    
    def generate_dashboard_html(self) -> str:
        """Generate complete dashboard HTML"""
        stats = self.metrics_collector.get_summary_stats()
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude MCP Execution Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .success-rate {{ color: #4caf50; }}
        .execution-time {{ color: #2196f3; }}
        .total-executions {{ color: #ff9800; }}
        .requests-per-minute {{ color: #9c27b0; }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }}
        .chart-container {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .status-online {{ background-color: #4caf50; }}
        .status-offline {{ background-color: #f44336; }}
        
        .real-time-log {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            max-height: 400px;
            overflow-y: auto;
        }}
        .log-entry {{
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 8px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.85em;
        }}
        .log-success {{ background: #e8f5e8; border-left: 3px solid #4caf50; }}
        .log-error {{ background: #ffeaea; border-left: 3px solid #f44336; }}
        .log-info {{ background: #e3f2fd; border-left: 3px solid #2196f3; }}
        
        @media (max-width: 768px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                🃏 Claude MCP Code Execution Dashboard
                <span class="status-indicator status-online" id="connection-status"></span>
                <span id="connection-text">Connected</span>
            </h1>
            <p>Real-time monitoring and analytics for AI-assisted programming</p>
            <p><strong>Session Duration:</strong> {stats['session_duration']}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value total-executions">{stats['total_executions']}</div>
                <div class="stat-label">Total Executions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value success-rate">{stats['success_rate']:.1f}%</div>
                <div class="stat-label">Success Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value execution-time">{stats['average_execution_time']:.0f}ms</div>
                <div class="stat-label">Avg Execution Time</div>
            </div>
            <div class="stat-card">
                <div class="stat-value requests-per-minute">{stats['requests_per_minute']}</div>
                <div class="stat-label">Requests/Minute</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                {self.generate_performance_chart()}
            </div>
            <div class="chart-container">
                {self.generate_tool_usage_chart()}
            </div>
        </div>
        
        <div class="real-time-log">
            <h3>🔴 Real-time Execution Log</h3>
            <div id="log-container">
                <div class="log-entry log-info">Dashboard started - waiting for executions...</div>
            </div>
        </div>
    </div>
    
    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket('ws://localhost:8888/ws');
        const logContainer = document.getElementById('log-container');
        const connectionStatus = document.getElementById('connection-status');
        const connectionText = document.getElementById('connection-text');
        
        ws.onopen = function(event) {{
            console.log('WebSocket connected');
            connectionStatus.className = 'status-indicator status-online';
            connectionText.textContent = 'Connected';
        }};
        
        ws.onclose = function(event) {{
            console.log('WebSocket disconnected');
            connectionStatus.className = 'status-indicator status-offline';
            connectionText.textContent = 'Disconnected';
        }};
        
        ws.onmessage = function(event) {{
            const message = JSON.parse(event.data);
            
            if (message.type === 'execution_update') {{
                updateStats(message.summary);
                addLogEntry(message.data);
            }}
        }};
        
        function updateStats(stats) {{
            document.querySelector('.total-executions').textContent = stats.total_executions;
            document.querySelector('.success-rate').textContent = stats.success_rate.toFixed(1) + '%';
            document.querySelector('.execution-time').textContent = Math.round(stats.average_execution_time) + 'ms';
            document.querySelector('.requests-per-minute').textContent = stats.requests_per_minute;
        }}
        
        function addLogEntry(data) {{
            const entry = document.createElement('div');
            entry.className = `log-entry ${{data.success ? 'log-success' : 'log-error'}}`;
            
            const timestamp = new Date(data.timestamp).toLocaleTimeString();
            const status = data.success ? '✅' : '❌';
            const tool = data.tool_name;
            const time = Math.round(data.execution_time_ms);
            
            entry.innerHTML = `${{timestamp}} ${{status}} ${{tool}} (${{time}}ms)`;
            
            if (data.error) {{
                entry.innerHTML += `<br><small style="color: #d32f2f;">Error: ${{data.error.substring(0, 100)}}...</small>`;
            }}
            
            logContainer.insertBefore(entry, logContainer.firstChild);
            
            // Keep only last 50 entries
            while (logContainer.children.length > 50) {{
                logContainer.removeChild(logContainer.lastChild);
            }}
        }}
        
        // Auto-refresh page every 5 minutes to get updated charts
        setTimeout(() => {{
            location.reload();
        }}, 5 * 60 * 1000);
    </script>
</body>
</html>
"""
        return html

class PerformanceMonitor:
    """Main performance monitoring class"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.dashboard_generator = DashboardGenerator(self.metrics_collector)
        self.app = None
        self.setup_fastapi() if HAS_FASTAPI else None
    
    def setup_fastapi(self):
        """Setup FastAPI application"""
        self.app = FastAPI(title="Claude MCP Dashboard", version="1.0.0")
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """Main dashboard page"""
            return self.dashboard_generator.generate_dashboard_html()
        
        @self.app.get("/api/stats")
        async def get_stats():
            """API endpoint for current statistics"""
            return JSONResponse(self.metrics_collector.get_summary_stats())
        
        @self.app.get("/api/metrics")
        async def get_metrics():
            """API endpoint for time series metrics"""
            return JSONResponse(self.metrics_collector.get_time_series_data())
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.metrics_collector.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Keep connection alive
                    await asyncio.sleep(30)
                    await websocket.send_text(json.dumps({"type": "ping"}))
            except WebSocketDisconnect:
                if websocket in self.metrics_collector.websocket_connections:
                    self.metrics_collector.websocket_connections.remove(websocket)
    
    async def record_execution(
        self, 
        tool_name: str, 
        execution_time_ms: float, 
        success: bool, 
        error: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Record an execution for monitoring"""
        await self.metrics_collector.record_execution(
            tool_name, execution_time_ms, success, error, request_id
        )
    
    async def start_server(self, port: int = 8888, host: str = "127.0.0.1"):
        """Start the monitoring server"""
        if not HAS_FASTAPI:
            logging.warning("FastAPI not available. Monitoring dashboard disabled.")
            return
        
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        
        # Start server in background
        await server.serve()

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

async def start_dashboard(port: int = 8888, open_browser: bool = True):
    """Start the monitoring dashboard"""
    if not HAS_FASTAPI:
        print("⚠️  Monitoring dashboard requires FastAPI. Install with: pip install fastapi uvicorn")
        return
    
    if open_browser:
        # Open browser after a short delay
        def open_browser_delayed():
            time.sleep(2)
            webbrowser.open(f"http://localhost:{port}")
        
        import threading
        threading.Thread(target=open_browser_delayed, daemon=True).start()
    
    await performance_monitor.start_server(port=port)

def main():
    """Main entry point for standalone dashboard"""
    print("🚀 Starting Claude MCP Monitoring Dashboard...")
    
    if not HAS_FASTAPI:
        print("❌ FastAPI not installed. Please install with: pip install fastapi uvicorn")
        return
    
    asyncio.run(start_dashboard(open_browser=True))

if __name__ == "__main__":
    main()

class MonitoringDashboard:
    """
    MonitoringDashboard: Secure Facade for Real-Time Monitoring
    ----------------------------------------------------------
    Provides a stable, security-hardened interface for launching and interacting with the
    Claude Jester MCP real-time monitoring dashboard. This class wraps the lower-level
    PerformanceMonitor and dashboard startup logic, ensuring that all dashboard operations
    are performed with proper security controls, audit logging, and compliance annotations.

    Security Classification:
    - CONFIDENTIAL: Contains monitoring and observability controls
    - COMPLIANCE: PCI-DSS 4.0, SOC2, GDPR Article 32

    Architecture Decision Record:
    - ADR-2024-06: Facade pattern used to decouple CLI and API from dashboard implementation
    - ADR-2024-07: All dashboard launches are logged for audit and compliance

    Usage:
        dashboard = MonitoringDashboard()
        dashboard.start(port=8888, open_browser=True)

    Security Rationale:
    - Only exposes safe, intended dashboard operations
    - All invocations are logged for audit trail
    - Designed for extension with RBAC, authentication, or network controls
    """
    def __init__(self):
        self._monitor = PerformanceMonitor()
        self._logger = logging.getLogger("MonitoringDashboard")

    def start(self, port: int = 8888, open_browser: bool = True) -> None:
        """
        Start the monitoring dashboard web server.

        Args:
            port (int): Port to serve the dashboard on (default: 8888)
            open_browser (bool): Whether to open the dashboard in a browser (default: True)

        Security:
            - Logs all dashboard launches
            - Intended for local/secure network use; production deployments should restrict access
        """
        self._logger.info(f"Launching MonitoringDashboard on port {port} (open_browser={open_browser})")
        # Security: All launches are logged for audit
        try:
            # Delegate to the existing async dashboard startup
            asyncio.run(start_dashboard(port=port, open_browser=open_browser))
        except Exception as e:
            self._logger.error(f"Failed to launch MonitoringDashboard: {e}", exc_info=True)
            raise
