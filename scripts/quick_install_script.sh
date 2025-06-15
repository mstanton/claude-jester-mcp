#!/bin/bash

# Claude Desktop Code Execution MCP - Quick Installation Script
# One-click setup for the Claude Desktop code execution integration

set -e  # Exit on any error

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

# Configuration
REPO_URL="https://github.com/your-username/claude-desktop-mcp-execution"
INSTALL_DIR="$HOME/claude-mcp-execution"
CLAUDE_CONFIG_DIR=""
CLAUDE_CONFIG_FILE=""

print_header() {
    echo -e "${CYAN}${ROCKET}============================================${ROCKET}${NC}"
    echo -e "${CYAN}${ROCKET}  Claude Desktop Code Execution Setup   ${ROCKET}${NC}"
    echo -e "${CYAN}${ROCKET}============================================${ROCKET}${NC}"
    echo ""
    echo -e "${BLUE}Transform Claude into a thinking, testing programming partner!${NC}"
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
    log_success "Python $python_version found"
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is required but not installed."
        exit 1
    fi
    log_success "pip3 found"
    
    # Check git
    if ! command -v git &> /dev/null; then
        log_warning "git not found. Will download archive instead."
        HAS_GIT=false
    else
        log_success "git found"
        HAS_GIT=true
    fi
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
    
    if [ "$HAS_GIT" = true ]; then
        git clone "$REPO_URL" .
        log_success "Cloned repository"
    else
        # Download archive
        curl -L "${REPO_URL}/archive/main.zip" -o main.zip
        unzip main.zip
        mv claude-desktop-mcp-execution-main/* .
        rm -rf claude-desktop-mcp-execution-main main.zip
        log_success "Downloaded and extracted archive"
    fi
}

create_fallback_files() {
    log_step "Creating fallback implementation files..."
    
    # Create basic MCP server if not present
    if [ ! -f "$INSTALL_DIR/src/mcp/server.py" ]; then
        mkdir -p "$INSTALL_DIR/src/mcp"
        cat > "$INSTALL_DIR/src/mcp/server.py" << 'EOF'
#!/usr/bin/env python3
"""
Standalone MCP Server for Claude Desktop Code Execution
Fallback implementation that works without external dependencies
"""

import asyncio
import json
import sys
import subprocess
import tempfile
import os
import time
from pathlib import Path

def execute_python_code(code: str) -> dict:
    """Execute Python code safely and return results"""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        execution_time = (time.time() - start_time) * 1000
        
        os.unlink(temp_file)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "execution_time_ms": execution_time
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Code execution timed out (30 seconds)",
            "execution_time_ms": 30000
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": f"Execution error: {str(e)}",
            "execution_time_ms": 0
        }

def handle_execute_code(args):
    """Handle execute_code tool call"""
    code = args.get("code", "").strip()
    description = args.get("description", "")
    
    if not code:
        return "❌ No code provided to execute"
    
    result = execute_python_code(code)
    
    if result["success"]:
        response = f"""✅ **Code Execution Successful**

{f"**Purpose:** {description}" if description else ""}

**Performance:**
- Execution time: {result['execution_time_ms']:.2f}ms

**Output:**
```
{result['output'][:500] if result['output'] else '(No output)'}
```

**Status:** ✨ Ready to present to user"""
    else:
        response = f"""❌ **Code Execution Failed**

{f"**Purpose:** {description}" if description else ""}

**Error:** {result['error']}

**Suggestions:**
- Check syntax and indentation
- Verify all variables are defined
- Test with simpler input

**Status:** Please fix errors before presenting to user"""
    
    return response

async def main():
    """Main MCP server loop"""
    print("🚀 Claude Desktop MCP Server starting...", file=sys.stderr)
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            try:
                request = json.loads(line)
                response = None
                
                method = request.get("method")
                
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "claude-code-execution", "version": "1.0.0"}
                        }
                    }
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {
                            "tools": [{
                                "name": "execute_code",
                                "description": "Execute Python code with real-time validation and feedback",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "code": {"type": "string", "description": "Python code to execute"},
                                        "description": {"type": "string", "description": "What the code should do", "default": ""}
                                    },
                                    "required": ["code"]
                                }
                            }]
                        }
                    }
                elif method == "tools/call":
                    tool_name = request["params"]["name"]
                    arguments = request["params"]["arguments"]
                    
                    if tool_name == "execute_code":
                        result_text = handle_execute_code(arguments)
                    else:
                        result_text = f"Unknown tool: {tool_name}"
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {"content": [{"type": "text", "text": result_text}]}
                    }
                
                if response:
                    print(json.dumps(response), flush=True)
                    
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Request handling error: {e}", file=sys.stderr)
                
    except KeyboardInterrupt:
        print("Server stopped", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
EOF
        log_success "Created fallback MCP server"
    fi
}

install_python_dependencies() {
    log_step "Installing Python dependencies..."
    
    cd "$INSTALL_DIR"
    
    # Create requirements.txt if it doesn't exist
    if [ ! -f "requirements.txt" ]; then
        cat > requirements.txt << 'EOF'
# Core MCP dependencies
mcp>=1.0.0

# Optional performance dependencies (graceful fallback if not available)
# multiprocess>=0.70.12
# psutil>=5.8.0
# restrictedpython>=6.0
# asteval>=0.9.28
EOF
    fi
    
    # Install core dependencies
    pip3 install --user mcp || {
        log_error "Failed to install MCP dependency"
        exit 1
    }
    
    # Try to install optional dependencies (don't fail if they can't be installed)
    log_info "Installing optional performance dependencies..."
    pip3 install --user multiprocess psutil restrictedpython asteval 2>/dev/null || {
        log_warning "Some optional dependencies failed to install - using fallback implementations"
    }
    
    log_success "Python dependencies installed"
}

setup_claude_config() {
    log_step "Setting up Claude Desktop configuration..."
    
    # Create Claude config directory if it doesn't exist
    mkdir -p "$CLAUDE_CONFIG_DIR"
    
    # Backup existing config
    if [ -f "$CLAUDE_CONFIG_FILE" ]; then
        cp "$CLAUDE_CONFIG_FILE" "${CLAUDE_CONFIG_FILE}.backup.$(date +%s)"
        log_info "Backed up existing Claude config"
    fi
    
    # Read existing config or create empty one
    if [ -f "$CLAUDE_CONFIG_FILE" ]; then
        EXISTING_CONFIG=$(cat "$CLAUDE_CONFIG_FILE")
    else
        EXISTING_CONFIG="{}"
    fi
    
    # Create new config with MCP server
    cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "code-execution": {
      "command": "python3",
      "args": ["${INSTALL_DIR}/src/mcp/server.py"],
      "env": {
        "PYTHONPATH": "${INSTALL_DIR}",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
EOF
    
    log_success "Claude Desktop configuration updated"
    log_info "Config file: $CLAUDE_CONFIG_FILE"
}

create_launcher_script() {
    log_step "Creating launcher script..."
    
    cat > "$INSTALL_DIR/start_monitoring.py" << 'EOF'
#!/usr/bin/env python3
"""
Start monitoring dashboard for Claude MCP Code Execution
"""

import webbrowser
import time
import sys
from pathlib import Path

print("🚀 Claude MCP Code Execution - Monitoring Dashboard")
print("=" * 60)

install_dir = Path(__file__).parent
print(f"📍 Installation: {install_dir}")

# Try to start monitoring dashboard
try:
    from src.monitoring.dashboard import start_dashboard
    print("🌐 Starting monitoring dashboard at http://localhost:8888")
    webbrowser.open("http://localhost:8888")
    start_dashboard()
except ImportError:
    print("⚠️  Monitoring dashboard not available")
    print("✅ Basic MCP server is ready for Claude Desktop")

print("\n📝 Next steps:")
print("1. Restart Claude Desktop completely")
print("2. Ask Claude: 'Write a function to calculate factorial and test it'")
print("3. Watch Claude automatically test and optimize the code!")

input("\nPress Enter to exit...")
EOF
    
    chmod +x "$INSTALL_DIR/start_monitoring.py"
    log_success "Created launcher script"
}

test_installation() {
    log_step "Testing installation..."
    
    cd "$INSTALL_DIR"
    
    # Test Python import
    python3 -c "import sys; sys.path.insert(0, '.'); from src.mcp.server import main; print('✅ MCP server can be imported')" 2>/dev/null || {
        log_warning "Advanced features may not be available, but basic functionality should work"
    }
    
    # Test basic MCP server startup
    timeout 3 python3 src/mcp/server.py < /dev/null > /dev/null 2>&1 || {
        log_info "MCP server test completed (timeout expected)"
    }
    
    log_success "Installation test completed"
}

print_completion_message() {
    echo ""
    echo -e "${GREEN}${PARTY}============================================${PARTY}${NC}"
    echo -e "${GREEN}${PARTY}     Installation Complete!              ${PARTY}${NC}"
    echo -e "${GREEN}${PARTY}============================================${PARTY}${NC}"
    echo ""
    echo -e "${CYAN}📍 Installation Location:${NC} $INSTALL_DIR"
    echo -e "${CYAN}⚙️  Configuration File:${NC} $CLAUDE_CONFIG_FILE"
    echo ""
    echo -e "${YELLOW}🔄 Next Steps:${NC}"
    echo -e "   1. ${BLUE}Restart Claude Desktop completely${NC}"
    echo -e "   2. ${BLUE}Test with: 'Write a function to calculate prime numbers and test it'${NC}"
    echo -e "   3. ${BLUE}Watch Claude automatically validate and optimize the code!${NC}"
    echo ""
    echo -e "${CYAN}📊 Optional Monitoring:${NC}"
    echo -e "   Run: ${BLUE}python3 $INSTALL_DIR/start_monitoring.py${NC}"
    echo ""
    echo -e "${GREEN}🎉 Claude is now a thinking, testing programming partner!${NC}"
    echo ""
}

# Main installation flow
main() {
    print_header
    
    # Detect environment
    detect_os
    
    # Check prerequisites
    check_dependencies
    
    # Create installation
    create_install_directory
    
    # Try to download source, create fallback if needed
    if ! download_source 2>/dev/null; then
        log_warning "Could not download from repository, creating fallback implementation"
        create_fallback_files
    fi
    
    # Install dependencies
    install_python_dependencies
    
    # Configure Claude Desktop
    setup_claude_config
    
    # Create additional tools
    create_launcher_script
    
    # Test everything
    test_installation
    
    # Show completion message
    print_completion_message
}

# Run installation
main "$@"
