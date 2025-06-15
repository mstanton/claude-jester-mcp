# Claude Desktop MCP Execution - Docker Configuration
# Multi-stage build for optimized production container

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Add metadata
LABEL org.opencontainers.image.title="Claude Desktop MCP Execution"
LABEL org.opencontainers.image.description="AI-powered code execution environment for Claude Desktop"
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.revision=${VCS_REF}
LABEL org.opencontainers.image.source="https://github.com/your-username/claude-desktop-mcp-execution"
LABEL org.opencontainers.image.documentation="https://claude-mcp-docs.example.com"
LABEL org.opencontainers.image.vendor="Claude MCP Project"
LABEL maintainer="Claude MCP Team <team@claude-mcp-project.org>"

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt pyproject.toml ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip wheel setuptools

# Install Python dependencies
RUN pip install -r requirements.txt

# Install the package
RUN pip install -e .

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"

# MCP Server default configuration
ENV MCP_LOG_LEVEL=INFO
ENV MCP_RESTRICTED_MODE=true
ENV MCP_MAX_EXEC_TIME=10.0
ENV MCP_MAX_MEMORY_MB=256
ENV MCP_ENABLE_MONITORING=true
ENV MCP_ENABLE_QUANTUM=true
ENV MCP_ENABLE_LEARNING=true

# Create non-root user for security
RUN groupadd -r claude && useradd -r -g claude claude

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set work directory
WORKDIR /app

# Copy application code
COPY --from=builder /app/src ./src
COPY --from=builder /app/requirements.txt ./

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/cache /app/monitoring && \
    chown -R claude:claude /app

# Copy health check script
COPY docker/healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod +x /usr/local/bin/healthcheck.py

# Copy entrypoint script
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set up health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python /usr/local/bin/healthcheck.py

# Switch to non-root user
USER claude

# Expose ports
EXPOSE 8888

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command
CMD ["mcp-server"]

# Development stage (for local development)
FROM production as development

USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    mypy \
    bandit \
    safety \
    ipython \
    jupyter

# Development environment settings
ENV MCP_DEBUG=true
ENV MCP_LOG_LEVEL=DEBUG

# Create development directories
RUN mkdir -p /app/tests /app/docs /app/examples && \
    chown -R claude:claude /app

USER claude

# Default command for development
CMD ["python", "-m", "src.mcp.server"]

# Testing stage
FROM development as testing

USER root

# Install additional testing tools
RUN pip install \
    pytest-xdist \
    pytest-benchmark \
    pytest-mock \
    coverage \
    tox

# Copy test files
COPY tests/ ./tests/

# Set permissions
RUN chown -R claude:claude /app

USER claude

# Run tests by default
CMD ["pytest", "tests/", "-v", "--cov=src/claude_mcp", "--cov-report=html"]

# Monitoring stage (includes monitoring dashboard)
FROM production as monitoring

USER root

# Install monitoring dependencies
RUN pip install \
    fastapi \
    uvicorn \
    websockets \
    plotly \
    prometheus-client \
    grafana-client

# Install monitoring tools
RUN apt-get update && apt-get install -y \
    htop \
    iotop \
    nethogs \
    && rm -rf /var/lib/apt/lists/*

# Copy monitoring configuration
COPY docker/monitoring/ ./monitoring/

USER claude

# Expose monitoring ports
EXPOSE 8888 9090

# Start with monitoring enabled
CMD ["mcp-server", "--enable-monitoring"]

# Security-hardened stage
FROM production as secure

USER root

# Remove unnecessary packages and clean up
RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Security hardening
RUN echo "claude:!::0:::::" >> /etc/shadow

# Restrict permissions
RUN chmod 750 /app && \
    find /app -type f -exec chmod 640 {} \; && \
    find /app -type d -exec chmod 750 {} \;

# Security-focused environment
ENV MCP_RESTRICTED_MODE=true
ENV MCP_ALLOW_NETWORK=false
ENV MCP_MAX_EXEC_TIME=5.0
ENV MCP_MAX_MEMORY_MB=128
ENV MCP_ENABLE_LEARNING=false

USER claude

# Minimal attack surface
CMD ["python", "-m", "src.mcp.server", "--security-mode=maximum"]

# Multi-architecture build stage
FROM --platform=$BUILDPLATFORM python:3.11-slim as multi-arch

ARG TARGETPLATFORM
ARG BUILDPLATFORM

RUN echo "Building for $TARGETPLATFORM on $BUILDPLATFORM"

# Platform-specific optimizations
RUN if [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        echo "Optimizing for ARM64"; \
        export CFLAGS="-march=armv8-a"; \
    elif [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
        echo "Optimizing for AMD64"; \
        export CFLAGS="-march=x86-64"; \
    fi

# Continue with production build...
COPY --from=production /opt/venv /opt/venv
COPY --from=production /app /app

USER claude
CMD ["python", "-m", "src.mcp.server"]
