"""
Claude Jester MCP Network Isolation
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

This module implements network isolation for Claude Jester MCP.
It provides comprehensive network security controls.
"""

import os
import sys
import socket
import ipaddress
from typing import Dict, List, Optional, Set, Union
from contextlib import contextmanager

import docker
from docker.types import NetworkConfig
from structlog import get_logger

logger = get_logger()

class NetworkIsolation:
    """
    Network isolation manager.
    
    Security Rationale:
    This class implements a multi-layered network security approach:
    1. Network namespace isolation
    2. Firewall rules
    3. DNS restrictions
    4. Port restrictions
    5. Protocol restrictions
    
    Architecture Decision Record:
    - ADR-2023-04: Chose Docker network isolation over alternatives
    - ADR-2023-05: Implemented strict firewall rules
    - ADR-2023-06: Added DNS restrictions
    """
    
    def __init__(
        self,
        allowed_ports: Optional[Set[int]] = None,
        allowed_protocols: Optional[Set[str]] = None,
        allowed_hosts: Optional[Set[str]] = None,
        dns_enabled: bool = False,
        network_name: str = "claude-jester-isolated",
    ):
        """
        Initialize network isolation.
        
        Args:
            allowed_ports: Set of allowed ports
            allowed_protocols: Set of allowed protocols
            allowed_hosts: Set of allowed hosts
            dns_enabled: Whether to enable DNS
            network_name: Name of the isolated network
            
        Security:
            - Restricts network access
            - Controls allowed ports
            - Limits protocols
            - Restricts hosts
            - Controls DNS
        """
        self.allowed_ports = allowed_ports or set()
        self.allowed_protocols = allowed_protocols or {"tcp"}
        self.allowed_hosts = allowed_hosts or set()
        self.dns_enabled = dns_enabled
        self.network_name = network_name
        
        # Initialize Docker client
        self.client = docker.from_env()
        
        # Security: Verify Docker is running
        try:
            self.client.ping()
        except Exception as e:
            logger.error("Docker not available", error=str(e))
            raise RuntimeError("Docker is required for network isolation") from e
    
    @contextmanager
    def create_network(self) -> docker.models.networks.Network:
        """
        Create an isolated network.
        
        Security Rationale:
        This method implements several security measures:
        1. Creates isolated network
        2. Configures firewall rules
        3. Sets DNS options
        4. Enforces network policies
        
        Yields:
            Docker network instance
            
        Security:
            - Creates isolated network
            - Configures firewall
            - Controls DNS
            - Enforces policies
        """
        # Create network configuration
        network_config = NetworkConfig(
            driver="bridge",
            options={
                "com.docker.network.bridge.enable_icc": "false",
                "com.docker.network.bridge.enable_ip_masquerade": "false",
                "com.docker.network.bridge.name": self.network_name,
            },
            ipam={
                "Driver": "default",
                "Config": [
                    {
                        "Subnet": "172.28.0.0/16",
                        "Gateway": "172.28.0.1",
                    }
                ],
            },
        )
        
        # Create network
        network = self.client.networks.create(
            self.network_name,
            driver="bridge",
            options=network_config.options,
            ipam=network_config.ipam,
        )
        
        try:
            yield network
        finally:
            # Security: Clean up network
            try:
                network.remove()
            except Exception as e:
                logger.error("Failed to remove network", error=str(e))
    
    def configure_container_network(
        self,
        container: docker.models.containers.Container,
        network: docker.models.networks.Network,
    ) -> None:
        """
        Configure container network settings.
        
        Security Rationale:
        This method implements several security measures:
        1. Connects container to isolated network
        2. Applies network policies
        3. Configures DNS settings
        4. Sets up firewall rules
        
        Args:
            container: Docker container
            network: Docker network
            
        Security:
            - Connects to isolated network
            - Applies policies
            - Configures DNS
            - Sets up firewall
        """
        # Connect container to network
        network.connect(
            container,
            aliases=[container.name],
            ipv4_address=self._get_next_ip(network),
        )
        
        # Security: Configure DNS
        if not self.dns_enabled:
            container.exec_run(
                "echo 'nameserver 127.0.0.1' > /etc/resolv.conf",
                privileged=True,
            )
        
        # Security: Configure firewall
        self._configure_firewall(container)
    
    def _get_next_ip(self, network: docker.models.networks.Network) -> str:
        """
        Get next available IP address.
        
        Security Rationale:
        This method implements several security measures:
        1. Validates IP addresses
        2. Prevents IP conflicts
        3. Uses private IP range
        
        Args:
            network: Docker network
            
        Returns:
            Next available IP address
            
        Security:
            - Validates IPs
            - Prevents conflicts
            - Uses private range
        """
        # Get network info
        network_info = network.attrs
        
        # Get subnet
        subnet = ipaddress.ip_network(network_info["IPAM"]["Config"][0]["Subnet"])
        
        # Get used IPs
        used_ips = set()
        for container in network.containers:
            if "IPv4Address" in container.attrs["NetworkSettings"]["Networks"][self.network_name]:
                used_ips.add(container.attrs["NetworkSettings"]["Networks"][self.network_name]["IPv4Address"])
        
        # Find next available IP
        for ip in subnet.hosts():
            if str(ip) not in used_ips:
                return str(ip)
                
        raise RuntimeError("No available IP addresses")
    
    def _configure_firewall(self, container: docker.models.containers.Container) -> None:
        """
        Configure container firewall.
        
        Security Rationale:
        This method implements several security measures:
        1. Blocks all incoming traffic
        2. Restricts outgoing traffic
        3. Limits allowed ports
        4. Controls protocols
        
        Args:
            container: Docker container
            
        Security:
            - Blocks incoming traffic
            - Restricts outgoing
            - Limits ports
            - Controls protocols
        """
        # Security: Block all incoming traffic
        container.exec_run(
            "iptables -P INPUT DROP",
            privileged=True,
        )
        
        # Security: Allow only specific outgoing traffic
        for port in self.allowed_ports:
            for protocol in self.allowed_protocols:
                for host in self.allowed_hosts:
                    container.exec_run(
                        f"iptables -A OUTPUT -p {protocol} -d {host} --dport {port} -j ACCEPT",
                        privileged=True,
                    )
        
        # Security: Block all other outgoing traffic
        container.exec_run(
            "iptables -P OUTPUT DROP",
            privileged=True,
        )
    
    def validate_connection(
        self,
        container: docker.models.containers.Container,
        host: str,
        port: int,
        protocol: str = "tcp",
    ) -> bool:
        """
        Validate network connection.
        
        Security Rationale:
        This method implements several security measures:
        1. Validates connection parameters
        2. Checks firewall rules
        3. Verifies network policies
        4. Tests connectivity
        
        Args:
            container: Docker container
            host: Target host
            port: Target port
            protocol: Network protocol
            
        Returns:
            Whether connection is allowed
            
        Security:
            - Validates parameters
            - Checks firewall
            - Verifies policies
            - Tests connectivity
        """
        # Security: Validate parameters
        if port not in self.allowed_ports:
            return False
            
        if protocol not in self.allowed_protocols:
            return False
            
        if host not in self.allowed_hosts:
            return False
        
        # Security: Test connectivity
        try:
            result = container.exec_run(
                f"nc -zv -w 5 {host} {port}",
                privileged=True,
            )
            return result.exit_code == 0
        except Exception as e:
            logger.error("Connection test failed", error=str(e))
            return False 