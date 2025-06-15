#!/bin/bash

# Claude Desktop Code Execution MCP - Quick Installation Script
# One-click setup for the Claude Desktop code execution integration
# Security Classification: CONFIDENTIAL - Contains security enforcement mechanisms
# Author: Enterprise Security Team
# Version: 2.1.0

set -euo pipefail  # Enhanced error handling
IFS=$'\n\t'       # Safer word splitting

# Security: Ensure script is run with bash
if [ -z "${BASH_VERSION:-}" ]; then
    echo "❌ This script must be run with bash"
    exit 1
fi

# Security: Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run this script as root"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emojis for better UX
ROCKET="🚀"
CHECK="✅"
WARNING="⚠️"
ERROR="❌"
GEAR="⚙️"
PARTY="🎉"
SHIELD="🛡️"
LOCK="🔒"

# Configuration
REPO_URL="https://github.com/mstanton/claude-jester-mcp"
INSTALL_DIR="$HOME/claude-jester-mcp"
CLAUDE_CONFIG_DIR=""
CLAUDE_CONFIG_FILE=""
PYTHON_VERSION="3.8"
REQUIRED_PACKAGES=(
    "uv"           # Modern Python package manager
    "pre-commit"   # Git hooks for code quality
    "pytest"       # Testing framework
    "black"        # Code formatting
    "mypy"         # Type checking
    "bandit"       # Security linter
    "safety"       # Dependency vulnerability checker
)

print_header() {
    echo -e "${CYAN}${ROCKET}============================================${ROCKET}${NC}"
    echo -e "${CYAN}${ROCKET}  Claude Desktop Code Execution Setup   ${ROCKET}${NC}"
    echo -e "${CYAN}${ROCKET}============================================${ROCKET}${NC}"
    echo ""
    echo -e "${BLUE}Transform Claude into a thinking, testing programming partner!${NC}"
    echo -e "${YELLOW}${SHIELD} Enterprise-grade security and reliability${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}${CHECK} $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

log_error() {
    echo -e "${RED}${ERROR} $1${NC}"
}

log_step() {
    echo -e "${CYAN}${GEAR} $1${NC}"
}

log_security() {
    echo -e "${YELLOW}${SHIELD} $1${NC}"
}

detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        CLAUDE_CONFIG_DIR="$APPDATA/Claude"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
    log_info "Detected OS: $OS"
}

check_dependencies() {
    log_step "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed."
        echo "Please install Python 3.8+ and try again."
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if (( $(echo "$python_version < $PYTHON_VERSION" | bc -l) )); then
        log_error "Python $PYTHON_VERSION+ is required, but found $python_version"
        exit 1
    fi
    log_success "Python $python_version found"
    
    # Check uv (modern Python package manager)
    if ! command -v uv &> /dev/null; then
        log_warning "uv not found. Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        log_success "uv installed"
    else
        log_success "uv found"
    fi
    
    # Check git
    if ! command -v git &> /dev/null; then
        log_error "git is required but not installed."
        exit 1
    fi
    log_success "git found"
}

create_install_directory() {
    log_step "Creating installation directory..."
    
    if [ -d "$INSTALL_DIR" ]; then
        log_warning "Installation directory already exists at $INSTALL_DIR"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Installation cancelled."
            exit 0
        fi
        rm -rf "$INSTALL_DIR"
    fi
    
    mkdir -p "$INSTALL_DIR"
    log_success "Created installation directory: $INSTALL_DIR"
}

download_source() {
    log_step "Downloading source code..."
    
    cd "$INSTALL_DIR"
    
    # Security: Verify git is available
    if ! command -v git &> /dev/null; then
        log_error "git is required for secure installation"
        exit 1
    fi
    
    # Security: Clone with depth 1 for minimal attack surface
    git clone --depth 1 "$REPO_URL" .
    
    # Security: Verify repository integrity
    if [ ! -f "README.md" ] || [ ! -f "requirements.txt" ]; then
        log_error "Repository integrity check failed"
        exit 1
    fi
    
    log_success "Cloned repository"
}

setup_virtual_environment() {
    log_step "Setting up Python virtual environment..."
    
    cd "$INSTALL_DIR"
    
    # Security: Create isolated virtual environment
    uv venv .venv
    
    # Security: Activate virtual environment
    source .venv/bin/activate
    
    # Security: Install dependencies with uv for better security
    uv pip install -r requirements.txt
    
    # Security: Install development dependencies
    uv pip install -e ".[dev]"
    
    log_success "Virtual environment setup complete"
}

setup_security() {
    log_step "Setting up security features..."
    
    cd "$INSTALL_DIR"
    
    # Security: Install pre-commit hooks
    pre-commit install
    
    # Security: Run initial security checks
    log_security "Running security checks..."
    bandit -r src/
    safety check
    
    # Security: Set up secure file permissions
    find . -type f -exec chmod 644 {} \;
    find . -type d -exec chmod 755 {} \;
    chmod +x scripts/*.sh
    
    log_success "Security setup complete"
}

configure_claude() {
    log_step "Configuring Claude Desktop..."
    
    if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
        log_warning "Claude Desktop configuration directory not found"
        log_info "Please install Claude Desktop first"
        exit 1
    fi
    
    # Create backup of existing config
    if [ -f "$CLAUDE_CONFIG_FILE" ]; then
        cp "$CLAUDE_CONFIG_FILE" "${CLAUDE_CONFIG_FILE}.bak"
        log_success "Created backup of existing configuration"
    fi
    
    # Update configuration
    if [ -f "$CLAUDE_CONFIG_FILE" ]; then
        # Security: Use jq for safe JSON manipulation
        if command -v jq &> /dev/null; then
            jq '.mcpServers["code-execution"] = {
                "command": "python",
                "args": ["'"$INSTALL_DIR"'/src/mcp/server.py"],
                "env": {
                    "MCP_LOG_LEVEL": "INFO",
                    "MCP_ENABLE_LEARNING": "true",
                    "MCP_ENABLE_MONITORING": "true",
                    "MCP_RESTRICTED_MODE": "true",
                    "MCP_ALLOW_NETWORK": "false"
                }
            }' "$CLAUDE_CONFIG_FILE" > "${CLAUDE_CONFIG_FILE}.tmp"
            mv "${CLAUDE_CONFIG_FILE}.tmp" "$CLAUDE_CONFIG_FILE"
        else
            log_warning "jq not found, using basic configuration"
            echo '{
                "mcpServers": {
                    "code-execution": {
                        "command": "python",
                        "args": ["'"$INSTALL_DIR"'/src/mcp/server.py"],
                        "env": {
                            "MCP_LOG_LEVEL": "INFO",
                            "MCP_ENABLE_LEARNING": "true",
                            "MCP_ENABLE_MONITORING": "true",
                            "MCP_RESTRICTED_MODE": "true",
                            "MCP_ALLOW_NETWORK": "false"
                        }
                    }
                }
            }' > "$CLAUDE_CONFIG_FILE"
        fi
    else
        log_warning "Claude Desktop configuration file not found"
        log_info "Please install Claude Desktop first"
        exit 1
    fi
    
    log_success "Claude Desktop configured"
}

run_tests() {
    log_step "Running tests..."
    
    cd "$INSTALL_DIR"
    
    # Security: Run tests in isolated environment
    source .venv/bin/activate
    pytest tests/
    
    log_success "Tests completed successfully"
}

print_success() {
    echo -e "\n${GREEN}${PARTY} Installation Complete! ${PARTY}${NC}"
    echo -e "\n${BLUE}Next steps:${NC}"
    echo "1. Restart Claude Desktop"
    echo "2. Try the example: 'Write a function to calculate factorial and test it'"
    echo "3. Check the dashboard at http://localhost:8888"
    echo -e "\n${YELLOW}${SHIELD} Security Features Enabled:${NC}"
    echo "- Restricted execution mode"
    echo "- Network isolation"
    echo "- Code validation"
    echo "- Security linting"
    echo -e "\n${CYAN}${LOCK} Your development environment is now secure and ready!${NC}"
}

main() {
    print_header
    detect_os
    check_dependencies
    create_install_directory
    download_source
    setup_virtual_environment
    setup_security
    configure_claude
    run_tests
    print_success
}

# Security: Run main function with error handling
if ! main; then
    log_error "Installation failed"
    exit 1
fi
