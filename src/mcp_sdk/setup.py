"""
MCP SDK Setup
Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
Author: Enterprise Security Team
Version: 2.1.0

Setup configuration for the MCP SDK package.
"""

from setuptools import setup, find_packages

setup(
    name="mcp-sdk",
    version="0.1.0",
    description="MCP SDK for Claude Jester",
    author="Enterprise Security Team",
    author_email="security@company.com",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.7.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "pydantic>=2.4.2",
        "python-dotenv>=1.0.0",
        "structlog>=23.2.0",
        "prometheus-client>=0.19.0",
        "docker>=6.1.3",
        "psutil>=5.9.0",
        "aiohttp>=3.9.1",
        "cryptography>=41.0.0",
        "python-jose>=3.3.0",
        "passlib>=1.7.4",
        "bcrypt>=4.0.1",
        "argon2-cffi>=23.1.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 