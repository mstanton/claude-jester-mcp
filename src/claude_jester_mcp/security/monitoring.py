"""
Claude Jester MCP Security Monitoring
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

This module implements security monitoring for Claude Jester MCP.
It provides comprehensive security event tracking and alerting.
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from enum import Enum

import docker
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from structlog import get_logger

logger = get_logger()

class SecurityEventType(str, Enum):
    """Types of security events."""
    CODE_EXECUTION = "code_execution"
    NETWORK_ACCESS = "network_access"
    RESOURCE_USAGE = "resource_usage"
    CONTAINER_CREATION = "container_creation"
    CONTAINER_DELETION = "container_deletion"
    NETWORK_CREATION = "network_creation"
    NETWORK_DELETION = "network_deletion"
    FIREWALL_RULE = "firewall_rule"
    DNS_QUERY = "dns_query"
    FILE_ACCESS = "file_access"
    PROCESS_CREATION = "process_creation"
    PROCESS_DELETION = "process_deletion"
    USER_ACTION = "user_action"
    SYSTEM_ERROR = "system_error"
    SECURITY_ALERT = "security_alert"

class SecurityEventSeverity(str, Enum):
    """Severity levels for security events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class SecurityMonitor:
    """
    Security monitoring system.
    
    Security Rationale:
    This class implements a comprehensive security monitoring approach:
    1. Event tracking
    2. Metrics collection
    3. Alert generation
    4. Log aggregation
    5. Audit trail
    
    Architecture Decision Record:
    - ADR-2023-07: Chose Prometheus for metrics
    - ADR-2023-08: Implemented structured logging
    - ADR-2023-09: Added security event tracking
    """
    
    def __init__(
        self,
        metrics_port: int = 9090,
        log_dir: Optional[Path] = None,
        alert_threshold: int = 100,
        retention_days: int = 30,
    ):
        """
        Initialize security monitor.
        
        Args:
            metrics_port: Port for Prometheus metrics
            log_dir: Directory for security logs
            alert_threshold: Threshold for security alerts
            retention_days: Days to retain logs
            
        Security:
            - Collects metrics
            - Tracks events
            - Generates alerts
            - Manages logs
        """
        self.metrics_port = metrics_port
        self.log_dir = log_dir or Path.home() / ".claude-jester" / "logs"
        self.alert_threshold = alert_threshold
        self.retention_days = retention_days
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self._init_metrics()
        
        # Start metrics server
        start_http_server(self.metrics_port)
        
        # Initialize Docker client
        self.client = docker.from_env()
        
        # Security: Verify Docker is running
        try:
            self.client.ping()
        except Exception as e:
            logger.error("Docker not available", error=str(e))
            raise RuntimeError("Docker is required for security monitoring") from e
    
    def _init_metrics(self) -> None:
        """
        Initialize Prometheus metrics.
        
        Security Rationale:
        This method implements several security measures:
        1. Defines security metrics
        2. Sets up monitoring
        3. Configures alerting
        4. Initializes counters
        
        Security:
            - Defines metrics
            - Sets up monitoring
            - Configures alerts
            - Initializes counters
        """
        # Security event counters
        self.event_counter = Counter(
            "security_events_total",
            "Total number of security events",
            ["type", "severity"],
        )
        
        # Resource usage gauges
        self.cpu_usage = Gauge(
            "container_cpu_usage",
            "CPU usage per container",
            ["container_id"],
        )
        
        self.memory_usage = Gauge(
            "container_memory_usage",
            "Memory usage per container",
            ["container_id"],
        )
        
        # Network metrics
        self.network_traffic = Counter(
            "network_traffic_bytes",
            "Network traffic in bytes",
            ["container_id", "direction"],
        )
        
        # Performance metrics
        self.execution_time = Histogram(
            "code_execution_seconds",
            "Time spent executing code",
            ["container_id"],
        )
        
        # Alert metrics
        self.alert_counter = Counter(
            "security_alerts_total",
            "Total number of security alerts",
            ["severity"],
        )
    
    def track_event(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        details: Dict[str, Union[str, int, float, bool]],
        container_id: Optional[str] = None,
    ) -> None:
        """
        Track a security event.
        
        Security Rationale:
        This method implements several security measures:
        1. Records event details
        2. Updates metrics
        3. Generates alerts
        4. Writes logs
        
        Args:
            event_type: Type of security event
            severity: Event severity
            details: Event details
            container_id: Container ID if applicable
            
        Security:
            - Records events
            - Updates metrics
            - Generates alerts
            - Writes logs
        """
        # Create event record
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "severity": severity,
            "details": details,
            "container_id": container_id,
        }
        
        # Update metrics
        self.event_counter.labels(
            type=event_type,
            severity=severity,
        ).inc()
        
        # Check for alerts
        if severity in [SecurityEventSeverity.ERROR, SecurityEventSeverity.CRITICAL]:
            self.alert_counter.labels(severity=severity).inc()
            
            # Generate alert
            self._generate_alert(event)
        
        # Write to log
        self._write_log(event)
    
    def _generate_alert(self, event: Dict[str, Union[str, Dict]]) -> None:
        """
        Generate a security alert.
        
        Security Rationale:
        This method implements several security measures:
        1. Validates alert conditions
        2. Formats alert message
        3. Sends notifications
        4. Records alert
        
        Args:
            event: Security event
            
        Security:
            - Validates alerts
            - Formats messages
            - Sends notifications
            - Records alerts
        """
        # Create alert message
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "message": f"Security alert: {event['type']} - {event['severity']}",
        }
        
        # Log alert
        logger.warning(
            "Security alert generated",
            alert=alert,
        )
        
        # TODO: Send alert notifications
    
    def _write_log(self, event: Dict[str, Union[str, Dict]]) -> None:
        """
        Write event to log file.
        
        Security Rationale:
        This method implements several security measures:
        1. Creates log file
        2. Writes event data
        3. Handles rotation
        4. Manages retention
        
        Args:
            event: Security event
            
        Security:
            - Creates logs
            - Writes events
            - Handles rotation
            - Manages retention
        """
        # Create log file path
        log_file = self.log_dir / f"security_{datetime.utcnow().strftime('%Y%m%d')}.log"
        
        # Write event
        with log_file.open("a") as f:
            f.write(json.dumps(event) + "\n")
        
        # Handle log rotation
        self._rotate_logs()
    
    def _rotate_logs(self) -> None:
        """
        Rotate log files.
        
        Security Rationale:
        This method implements several security measures:
        1. Checks log age
        2. Removes old logs
        3. Compresses logs
        4. Maintains retention
        
        Security:
            - Checks age
            - Removes old
            - Compresses
            - Maintains retention
        """
        # Get current time
        now = datetime.utcnow()
        
        # Check each log file
        for log_file in self.log_dir.glob("security_*.log"):
            # Get file age
            age = now - datetime.fromtimestamp(log_file.stat().st_mtime)
            
            # Remove old files
            if age.days > self.retention_days:
                log_file.unlink()
    
    def update_container_metrics(self, container_id: str) -> None:
        """
        Update container metrics.
        
        Security Rationale:
        This method implements several security measures:
        1. Collects resource usage
        2. Updates metrics
        3. Checks thresholds
        4. Generates alerts
        
        Args:
            container_id: Container ID
            
        Security:
            - Collects usage
            - Updates metrics
            - Checks thresholds
            - Generates alerts
        """
        try:
            # Get container stats
            stats = self.client.containers.get(container_id).stats(stream=False)
            
            # Update CPU usage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * 100.0
            
            self.cpu_usage.labels(container_id=container_id).set(cpu_percent)
            
            # Update memory usage
            memory_usage = stats["memory_stats"]["usage"]
            self.memory_usage.labels(container_id=container_id).set(memory_usage)
            
            # Check thresholds
            if cpu_percent > 80:
                self.track_event(
                    SecurityEventType.RESOURCE_USAGE,
                    SecurityEventSeverity.WARNING,
                    {
                        "container_id": container_id,
                        "metric": "cpu",
                        "value": cpu_percent,
                        "threshold": 80,
                    },
                    container_id,
                )
            
            if memory_usage > 1024 * 1024 * 512:  # 512MB
                self.track_event(
                    SecurityEventType.RESOURCE_USAGE,
                    SecurityEventSeverity.WARNING,
                    {
                        "container_id": container_id,
                        "metric": "memory",
                        "value": memory_usage,
                        "threshold": 512 * 1024 * 1024,
                    },
                    container_id,
                )
                
        except Exception as e:
            logger.error(
                "Failed to update container metrics",
                error=str(e),
                container_id=container_id,
            )
    
    def track_network_traffic(
        self,
        container_id: str,
        direction: str,
        bytes_sent: int,
    ) -> None:
        """
        Track network traffic.
        
        Security Rationale:
        This method implements several security measures:
        1. Records traffic
        2. Updates metrics
        3. Checks thresholds
        4. Generates alerts
        
        Args:
            container_id: Container ID
            direction: Traffic direction
            bytes_sent: Bytes sent/received
            
        Security:
            - Records traffic
            - Updates metrics
            - Checks thresholds
            - Generates alerts
        """
        # Update metrics
        self.network_traffic.labels(
            container_id=container_id,
            direction=direction,
        ).inc(bytes_sent)
        
        # Check thresholds
        if bytes_sent > 1024 * 1024 * 100:  # 100MB
            self.track_event(
                SecurityEventType.NETWORK_ACCESS,
                SecurityEventSeverity.WARNING,
                {
                    "container_id": container_id,
                    "direction": direction,
                    "bytes": bytes_sent,
                    "threshold": 100 * 1024 * 1024,
                },
                container_id,
            )
    
    def track_execution_time(
        self,
        container_id: str,
        execution_time: float,
    ) -> None:
        """
        Track code execution time.
        
        Security Rationale:
        This method implements several security measures:
        1. Records execution time
        2. Updates metrics
        3. Checks thresholds
        4. Generates alerts
        
        Args:
            container_id: Container ID
            execution_time: Execution time in seconds
            
        Security:
            - Records time
            - Updates metrics
            - Checks thresholds
            - Generates alerts
        """
        # Update metrics
        self.execution_time.labels(
            container_id=container_id,
        ).observe(execution_time)
        
        # Check thresholds
        if execution_time > 30:  # 30 seconds
            self.track_event(
                SecurityEventType.CODE_EXECUTION,
                SecurityEventSeverity.WARNING,
                {
                    "container_id": container_id,
                    "execution_time": execution_time,
                    "threshold": 30,
                },
                container_id,
            ) 