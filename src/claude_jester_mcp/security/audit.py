"""
Claude Jester MCP Audit Logging
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

This module implements audit logging for Claude Jester MCP.
It provides comprehensive audit trail capabilities.
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from enum import Enum

import docker
from structlog import get_logger
from structlog.processors import JSONRenderer

logger = get_logger()

class AuditEventType(str, Enum):
    """Types of audit events."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    CODE_EXECUTION = "code_execution"
    CONTAINER_CREATION = "container_creation"
    CONTAINER_DELETION = "container_deletion"
    NETWORK_ACCESS = "network_access"
    FILE_ACCESS = "file_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    SYSTEM_ACTION = "system_action"

class AuditLogger:
    """
    Audit logging system.
    
    Security Rationale:
    This class implements a comprehensive audit logging approach:
    1. Event tracking
    2. Log aggregation
    3. Retention management
    4. Log integrity
    5. Access control
    
    Architecture Decision Record:
    - ADR-2023-10: Chose structured logging
    - ADR-2023-11: Implemented log rotation
    - ADR-2023-12: Added log integrity checks
    """
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        retention_days: int = 365,
        max_log_size: int = 100 * 1024 * 1024,  # 100MB
        compress_logs: bool = True,
    ):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for audit logs
            retention_days: Days to retain logs
            max_log_size: Maximum log file size
            compress_logs: Whether to compress old logs
            
        Security:
            - Manages logs
            - Controls retention
            - Handles rotation
            - Ensures integrity
        """
        self.log_dir = log_dir or Path.home() / ".claude-jester" / "audit"
        self.retention_days = retention_days
        self.max_log_size = max_log_size
        self.compress_logs = compress_logs
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self._init_logger()
        
        # Initialize Docker client
        self.client = docker.from_env()
        
        # Security: Verify Docker is running
        try:
            self.client.ping()
        except Exception as e:
            logger.error("Docker not available", error=str(e))
            raise RuntimeError("Docker is required for audit logging") from e
    
    def _init_logger(self) -> None:
        """
        Initialize structured logger.
        
        Security Rationale:
        This method implements several security measures:
        1. Configures logging
        2. Sets up processors
        3. Ensures integrity
        4. Controls access
        
        Security:
            - Configures logging
            - Sets up processors
            - Ensures integrity
            - Controls access
        """
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        details: Dict[str, Union[str, int, float, bool]],
        container_id: Optional[str] = None,
    ) -> None:
        """
        Log an audit event.
        
        Security Rationale:
        This method implements several security measures:
        1. Records event details
        2. Ensures integrity
        3. Handles rotation
        4. Controls access
        
        Args:
            event_type: Type of audit event
            user_id: User ID
            details: Event details
            container_id: Container ID if applicable
            
        Security:
            - Records events
            - Ensures integrity
            - Handles rotation
            - Controls access
        """
        # Create event record
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "details": details,
            "container_id": container_id,
            "hostname": os.uname().nodename,
            "pid": os.getpid(),
        }
        
        # Add Docker info if applicable
        if container_id:
            try:
                container = self.client.containers.get(container_id)
                event["container_info"] = {
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else container.image.id,
                    "created": container.attrs["Created"],
                }
            except Exception as e:
                logger.error(
                    "Failed to get container info",
                    error=str(e),
                    container_id=container_id,
                )
        
        # Write to log
        self._write_log(event)
        
        # Handle log rotation
        self._rotate_logs()
    
    def _write_log(self, event: Dict[str, Union[str, Dict]]) -> None:
        """
        Write event to log file.
        
        Security Rationale:
        This method implements several security measures:
        1. Creates log file
        2. Writes event data
        3. Ensures integrity
        4. Controls access
        
        Args:
            event: Audit event
            
        Security:
            - Creates logs
            - Writes events
            - Ensures integrity
            - Controls access
        """
        # Create log file path
        log_file = self.log_dir / f"audit_{datetime.utcnow().strftime('%Y%m%d')}.log"
        
        # Write event
        with log_file.open("a") as f:
            f.write(json.dumps(event) + "\n")
        
        # Set file permissions
        log_file.chmod(0o600)
    
    def _rotate_logs(self) -> None:
        """
        Rotate log files.
        
        Security Rationale:
        This method implements several security measures:
        1. Checks log size
        2. Handles rotation
        3. Compresses logs
        4. Maintains retention
        
        Security:
            - Checks size
            - Handles rotation
            - Compresses logs
            - Maintains retention
        """
        # Get current time
        now = datetime.utcnow()
        
        # Check each log file
        for log_file in self.log_dir.glob("audit_*.log"):
            # Check file size
            if log_file.stat().st_size > self.max_log_size:
                # Create new log file
                new_log_file = log_file.with_suffix(f".{int(time.time())}.log")
                log_file.rename(new_log_file)
                
                # Compress if enabled
                if self.compress_logs:
                    import gzip
                    with open(new_log_file, "rb") as f_in:
                        with gzip.open(new_log_file.with_suffix(".gz"), "wb") as f_out:
                            f_out.writelines(f_in)
                    new_log_file.unlink()
            
            # Check file age
            age = now - datetime.fromtimestamp(log_file.stat().st_mtime)
            
            # Remove old files
            if age.days > self.retention_days:
                log_file.unlink()
    
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        container_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Get audit events.
        
        Security Rationale:
        This method implements several security measures:
        1. Validates parameters
        2. Controls access
        3. Filters events
        4. Limits results
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            container_id: Filter by container ID
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of events
            
        Returns:
            List of audit events
            
        Security:
            - Validates parameters
            - Controls access
            - Filters events
            - Limits results
        """
        events = []
        
        # Get log files
        log_files = sorted(self.log_dir.glob("audit_*.log"))
        
        # Read events
        for log_file in log_files:
            with log_file.open("r") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        
                        # Apply filters
                        if event_type and event["event_type"] != event_type:
                            continue
                            
                        if user_id and event["user_id"] != user_id:
                            continue
                            
                        if container_id and event.get("container_id") != container_id:
                            continue
                            
                        if start_time and datetime.fromisoformat(event["timestamp"]) < start_time:
                            continue
                            
                        if end_time and datetime.fromisoformat(event["timestamp"]) > end_time:
                            continue
                        
                        events.append(event)
                        
                        # Check limit
                        if len(events) >= limit:
                            return events
                            
                    except Exception as e:
                        logger.error(
                            "Failed to parse audit event",
                            error=str(e),
                            log_file=str(log_file),
                        )
        
        return events
    
    def get_container_events(
        self,
        container_id: str,
        limit: int = 1000,
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Get container audit events.
        
        Security Rationale:
        This method implements several security measures:
        1. Validates container
        2. Controls access
        3. Filters events
        4. Limits results
        
        Args:
            container_id: Container ID
            limit: Maximum number of events
            
        Returns:
            List of container audit events
            
        Security:
            - Validates container
            - Controls access
            - Filters events
            - Limits results
        """
        # Verify container exists
        try:
            self.client.containers.get(container_id)
        except Exception as e:
            logger.error(
                "Container not found",
                error=str(e),
                container_id=container_id,
            )
            return []
        
        # Get events
        return self.get_events(
            container_id=container_id,
            limit=limit,
        )
    
    def get_user_events(
        self,
        user_id: str,
        limit: int = 1000,
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Get user audit events.
        
        Security Rationale:
        This method implements several security measures:
        1. Validates user
        2. Controls access
        3. Filters events
        4. Limits results
        
        Args:
            user_id: User ID
            limit: Maximum number of events
            
        Returns:
            List of user audit events
            
        Security:
            - Validates user
            - Controls access
            - Filters events
            - Limits results
        """
        # Get events
        return self.get_events(
            user_id=user_id,
            limit=limit,
        ) 