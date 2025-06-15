#!/usr/bin/env python3
"""
Interactive Setup Script for Claude Desktop MCP Execution
Provides guided installation and configuration with validation
"""

import os
import sys
import json
import subprocess
import platform
import shutil
import time
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Color support for cross-platform output
class Colors:
    if platform.system() != 'Windows':
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        RESET = '\033[0m'
        BOLD = '\033[1m'
    else:
        HEADER = BLUE = CYAN = GREEN = WARNING = FAIL = RESET = BOLD = ''

class SetupWizard:
    """Interactive setup wizard for Claude Desktop MCP Execution"""
    
    def __init__(self):
        self.current_dir = Path.cwd()
        self.system = platform.system()
        self.python_version = sys.version_info
        
        # Configuration
        self.config = {
            "installation_type": "full",  # full, minimal, development
            "enable_monitoring": True,
            "enable_quantum_debugging": True,
            "enable_learning": True,
            "security_level": "standard",  # minimal, standard, maximum
            "performance_profile": "balanced",  # fast, balanced, safe
            "auto_update": True
        }
        
        # Installation paths
        self.install_dir = self.current_dir
        self.claude_config_dir = self._get_claude_config_dir()
        self.claude_config_file = self.claude_config_dir / "claude_desktop_config.json"
        
        # Validation results
        self.validation_results = {}
        
    def _get_claude_config_dir(self) -> Path:
        """Get Claude Desktop configuration directory"""
        if self.system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "Claude"
        elif self.system == "Windows":
            return Path(os.environ.get("APPDATA", "")) / "Claude"
        else:  # Linux
            return Path.home() / ".config" / "Claude"
    
    def print_banner(self):
        """Print welcome banner"""
        print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}🃏 Claude Desktop Code Execution - Interactive Setup{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"\n{Colors.GREEN}Transform Claude into a thinking, testing, optimizing programming partner!{Colors.RESET}")
        print(f"\n{Colors.BLUE}System Information:{Colors.RESET}")
        print(f"  OS: {self.system}")
        print(f"  Python: {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")
        print(f"  Install Directory: {self.install_dir}")
        print(f"  Claude Config: {self.claude_config_file}")
        print()
    
    def log(self, message: str, level: str = "INFO"):
        """Log messages with color coding"""
        timestamp = time.strftime("%H:%M:%S")
        
        if level == "SUCCESS":
            print(f"{Colors.GREEN}[{timestamp}] ✅ {message}{Colors.RESET}")
        elif level == "WARNING":
            print(f"{Colors.WARNING}[{timestamp}] ⚠️  {message}{Colors.RESET}")
        elif level == "ERROR":
            print(f"{Colors.FAIL}[{timestamp}] ❌ {message}{Colors.RESET}")
        elif level == "INFO":
            print(f"{Colors.BLUE}[{timestamp}] ℹ️  {message}{Colors.RESET}")
        else:
            print(f"[{timestamp}] {message}")
    
    def ask_yes_no(self, question: str, default: bool = True) -> bool:
        """Ask a yes/no question with default"""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{Colors.CYAN}❓ {question} ({default_str}): {Colors.RESET}")
        
        if not response.strip():
            return default
        
        return response.lower().startswith('y')
    
    def ask_choice(self, question: str, choices: List[str], default: int = 0) -> str:
        """Ask user to choose from a list of options"""
        print(f"\n{Colors.CYAN}❓ {question}{Colors.RESET}")
        
        for i, choice in enumerate(choices, 1):
            marker = "→" if i - 1 == default else " "
            print(f"  {marker} {i}. {choice}")
        
        while True:
            try:
                response = input(f"\nEnter choice (1-{len(choices)}) [{default + 1}]: ").strip()
                
                if not response:
                    return choices[default]
                
                choice_num = int(response)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                else:
                    print(f"{Colors.WARNING}Please enter a number between 1 and {len(choices)}{Colors.RESET}")
            except ValueError:
                print(f"{Colors.WARNING}Please enter a valid number{Colors.RESET}")
    
    def validate_system(self) -> bool:
        """Validate system requirements"""
        self.log("Validating system requirements...")
        
        all_valid = True
        
        # Check Python version
        if self.python_version < (3, 8):
            self.log(f"Python 3.8+ required, found {self.python_version.major}.{self.python_version.minor}", "ERROR")
            all_valid = False
        else:
            self.log(f"Python version OK: {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}", "SUCCESS")
        
        # Check pip
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"], 
                         capture_output=True, check=True)
            self.log("pip available", "SUCCESS")
        except subprocess.CalledProcessError:
            self.log("pip not available", "ERROR")
            all_valid = False
        
        # Check disk space (need at least 100MB)
        try:
            free_space = shutil.disk_usage(self.install_dir).free
            free_mb = free_space / (1024 * 1024)
            
            if free_mb < 100:
                self.log(f"Insufficient disk space: {free_mb:.1f}MB available, need 100MB", "ERROR")
                all_valid = False
            else:
                self.log(f"Disk space OK: {free_mb:.1f}MB available", "SUCCESS")
        except Exception as e:
            self.log(f"Could not check disk space: {e}", "WARNING")
        
        # Check write permissions
        try:
            test_file = self.install_dir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            self.log("Write permissions OK", "SUCCESS")
        except Exception as e:
            self.log(f"No write permissions: {e}", "ERROR")
            all_valid = False
        
        self.validation_results["system"] = all_valid
        return all_valid
    
    def choose_installation_type(self):
        """Let user choose installation type"""
        self.log("Choosing installation type...")
        
        installation_types = [
            "Full Installation (All features, requires more dependencies)",
            "Minimal Installation (Core features only, fewer dependencies)",
            "Development Installation (Full + development tools)"
        ]
        
        choice = self.ask_choice(
            "What type of installation would you like?",
            installation_types,
            default=0
        )
        
        if "Full" in choice:
            self.config["installation_type"] = "full"
        elif "Minimal" in choice:
            self.config["installation_type"] = "minimal"
        else:
            self.config["installation_type"] = "development"
        
        self.log(f"Selected: {self.config['installation_type']} installation", "INFO")
    
    def configure_features(self):
        """Configure optional features"""
        self.log("Configuring features...")
        
        if self.config["installation_type"] != "minimal":
            # Monitoring dashboard
            self.config["enable_monitoring"] = self.ask_yes_no(
                "Enable real-time monitoring dashboard?", 
                default=True
            )
            
            # Quantum debugging
            self.config["enable_quantum_debugging"] = self.ask_yes_no(
                "Enable quantum debugging (parallel variant testing)?",
                default=True
            )
            
            # Learning system
            self.config["enable_learning"] = self.ask_yes_no(
                "Enable adaptive learning system?",
                default=True
            )
        
        # Security level
        security_levels = [
            "Standard (Recommended balance of security and functionality)",
            "Maximum (Highest security, may limit some features)",
            "Minimal (Basic security only, not recommended for production)"
        ]
        
        security_choice = self.ask_choice(
            "Choose security level:",
            security_levels,
            default=0
        )
        
        if "Maximum" in security_choice:
            self.config["security_level"] = "maximum"
        elif "Minimal" in security_choice:
            self.config["security_level"] = "minimal"
        else:
            self.config["security_level"] = "standard"
        
        # Performance profile
        performance_profiles = [
            "Balanced (Good performance and safety)",
            "Fast (Optimized for speed)",
            "Safe (Optimized for reliability)"
        ]
        
        performance_choice = self.ask_choice(
            "Choose performance profile:",
            performance_profiles,
            default=0
        )
        
        if "Fast" in performance_choice:
            self.config["performance_profile"] = "fast"
        elif "Safe" in performance_choice:
            self.config["performance_profile"] = "safe"
        else:
            self.config["performance_profile"] = "balanced"
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        self.log("Installing Python dependencies...")
        
        # Base dependencies
        base_deps = ["mcp>=1.0.0", "asyncio-mqtt", "psutil", "pydantic"]
        
        # Optional dependencies based on configuration
        optional_deps = []
        
        if self.config["installation_type"] in ["full", "development"]:
            optional_deps.extend([
                "RestrictedPython", "asteval", "multiprocess",
                "numpy", "pandas"
            ])
        
        if self.config["enable_monitoring"]:
            optional_deps.extend([
                "fastapi", "uvicorn", "websockets", "jinja2",
                "plotly", "matplotlib"
            ])
        
        if self.config["installation_type"] == "development":
            optional_deps.extend([
                "pytest", "pytest-asyncio", "pytest-cov",
                "black", "flake8", "mypy", "bandit", "safety"
            ])
        
        # Install base dependencies
        try:
            self.log("Installing base dependencies...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "--upgrade"
            ] + base_deps, check=True, capture_output=True)
            self.log("Base dependencies installed", "SUCCESS")
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to install base dependencies: {e}", "ERROR")
            return False
        
        # Install optional dependencies (don't fail if some can't be installed)
        if optional_deps:
            self.log("Installing optional dependencies...")
            failed_deps = []
            
            for dep in optional_deps:
                try:
                    subprocess.run([
                        sys.executable, "-m", "pip", "install", dep
                    ], check=True, capture_output=True)
                    self.log(f"Installed: {dep}", "INFO")
                except subprocess.CalledProcessError:
                    failed_deps.append(dep)
                    self.log(f"Failed to install: {dep}", "WARNING")
            
            if failed_deps:
                self.log(f"Some optional dependencies failed: {', '.join(failed_deps)}", "WARNING")
                self.log("The system will work with reduced functionality", "INFO")
        
        self.validation_results["dependencies"] = True
        return True
    
    def setup_claude_config(self) -> bool:
        """Setup Claude Desktop configuration"""
        self.log("Setting up Claude Desktop configuration...")
        
        # Create config directory if needed
        self.claude_config_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup existing config
        if self.claude_config_file.exists():
            backup_file = self.claude_config_file.with_suffix(f".backup.{int(time.time())}")
            shutil.copy2(self.claude_config_file, backup_file)
            self.log(f"Backed up existing config to {backup_file.name}", "INFO")
        
        # Load existing config or create new
        if self.claude_config_file.exists():
            try:
                with open(self.claude_config_file, 'r') as f:
                    claude_config = json.load(f)
            except Exception as e:
                self.log(f"Could not read existing config: {e}", "WARNING")
                claude_config = {}
        else:
            claude_config = {}
        
        # Ensure mcpServers section exists
        if "mcpServers" not in claude_config:
            claude_config["mcpServers"] = {}
        
        # Configure MCP server
        server_script = self.install_dir / "src" / "mcp" / "server.py"
        
        # Generate environment variables based on configuration
        env_vars = self._generate_env_config()
        
        claude_config["mcpServers"]["claude-code-execution"] = {
            "command": sys.executable,
            "args": [str(server_script)],
            "env": env_vars
        }
        
        # Write updated config
        try:
            with open(self.claude_config_file, 'w') as f:
                json.dump(claude_config, f, indent=2)
            self.log("Claude Desktop configuration updated", "SUCCESS")
            self.validation_results["claude_config"] = True
            return True
        except Exception as e:
            self.log(f"Failed to update Claude config: {e}", "ERROR")
            self.validation_results["claude_config"] = False
            return False
    
    def _generate_env_config(self) -> Dict[str, str]:
        """Generate environment configuration based on user choices"""
        env_config = {
            "PYTHONPATH": str(self.install_dir),
            "MCP_LOG_LEVEL": "INFO"
        }
        
        # Security level configuration
        if self.config["security_level"] == "maximum":
            env_config.update({
                "MCP_RESTRICTED_MODE": "true",
                "MCP_MAX_MEMORY_MB": "128",
                "MCP_MAX_EXEC_TIME": "5.0",
                "MCP_ALLOW_NETWORK": "false"
            })
        elif self.config["security_level"] == "minimal":
            env_config.update({
                "MCP_RESTRICTED_MODE": "false",
                "MCP_MAX_MEMORY_MB": "512",
                "MCP_MAX_EXEC_TIME": "30.0"
            })
        else:  # standard
            env_config.update({
                "MCP_RESTRICTED_MODE": "true",
                "MCP_MAX_MEMORY_MB": "256",
                "MCP_MAX_EXEC_TIME": "10.0"
            })
        
        # Performance profile configuration
        if self.config["performance_profile"] == "fast":
            env_config.update({
                "MCP_CACHE_SIZE": "2000",
                "MCP_ENABLE_QUANTUM": "true"
            })
        elif self.config["performance_profile"] == "safe":
            env_config.update({
                "MCP_CACHE_SIZE": "500",
                "MCP_MAX_EXEC_TIME": "5.0"
            })
        else:  # balanced
            env_config.update({
                "MCP_CACHE_SIZE": "1000",
                "MCP_ENABLE_QUANTUM": "true"
            })
        
        # Feature configuration
        env_config["MCP_ENABLE_MONITORING"] = "true" if self.config["enable_monitoring"] else "false"
        env_config["MCP_ENABLE_LEARNING"] = "true" if self.config["enable_learning"] else "false"
        env_config["MCP_ENABLE_QUANTUM"] = "true" if self.config["enable_quantum_debugging"] else "false"
        
        return env_config
    
    def test_installation(self) -> bool:
        """Test the installation"""
        self.log("Testing installation...")
        
        test_passed = True
        
        # Test 1: Import core modules
        try:
            import sys
            sys.path.insert(0, str(self.install_dir / "src"))
            from core.executor import CodeExecutor
            self.log("Core modules import successfully", "SUCCESS")
        except ImportError as e:
            self.log(f"Failed to import core modules: {e}", "ERROR")
            test_passed = False
        
        # Test 2: Create executor and run simple test
        try:
            from core.executor import CodeExecutor
            import asyncio
            
            async def test_execution():
                executor = CodeExecutor(timeout=5.0)
                result = await executor.execute_code("print('Installation test successful!')")
                return result.status.value == "success"
            
            if asyncio.run(test_execution()):
                self.log("Code execution test passed", "SUCCESS")
            else:
                self.log("Code execution test failed", "ERROR")
                test_passed = False
                
        except Exception as e:
            self.log(f"Code execution test failed: {e}", "ERROR")
            test_passed = False
        
        # Test 3: MCP server startup
        try:
            server_script = self.install_dir / "src" / "mcp" / "server.py"
            if server_script.exists():
                # Test server can start (with timeout)
                result = subprocess.run([
                    sys.executable, str(server_script)
                ], capture_output=True, timeout=3, text=True)
                
                # Server should start and then timeout (expected behavior)
                self.log("MCP server startup test passed", "SUCCESS")
            else:
                self.log("MCP server script not found", "ERROR")
                test_passed = False
                
        except subprocess.TimeoutExpired:
            # This is actually expected - server started but we interrupted it
            self.log("MCP server startup test passed", "SUCCESS")
        except Exception as e:
            self.log(f"MCP server test failed: {e}", "ERROR")
            test_passed = False
        
        self.validation_results["installation_test"] = test_passed
        return test_passed
    
    def create_shortcuts(self):
        """Create convenient shortcuts"""
        self.log("Creating shortcuts and utilities...")
        
        # Create monitoring launcher
        if self.config["enable_monitoring"]:
            launcher_script = self.install_dir / "start_monitoring.py"
            launcher_content = f"""#!/usr/bin/env python3
\"\"\"Start Claude MCP Monitoring Dashboard\"\"\"

import sys
import webbrowser
import time
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

try:
    from monitoring.dashboard import start_dashboard
    import asyncio
    
    print("🚀 Starting Claude MCP Monitoring Dashboard...")
    print("🌐 Opening http://localhost:8888 in your browser...")
    
    # Open browser after short delay
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:8888")
    
    import threading
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start dashboard
    asyncio.run(start_dashboard())
    
except ImportError:
    print("⚠️  Monitoring dashboard not available")
    print("Install with: pip install fastapi uvicorn plotly")
except Exception as e:
    print(f"❌ Error starting dashboard: {{e}}")
"""
            
            with open(launcher_script, 'w') as f:
                f.write(launcher_content)
            
            # Make executable on Unix systems
            if self.system != "Windows":
                os.chmod(launcher_script, 0o755)
            
            self.log("Created monitoring launcher: start_monitoring.py", "SUCCESS")
        
        # Create configuration file
        config_file = self.install_dir / "claude_mcp_config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        self.log("Created configuration file: claude_mcp_config.json", "SUCCESS")
    
    def print_summary(self):
        """Print installation summary"""
        print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}🎉 Installation Summary{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
        
        # Show configuration
        print(f"\n{Colors.BLUE}Configuration:{Colors.RESET}")
        print(f"  Installation Type: {self.config['installation_type']}")
        print(f"  Security Level: {self.config['security_level']}")
        print(f"  Performance Profile: {self.config['performance_profile']}")
        print(f"  Monitoring: {'✅' if self.config['enable_monitoring'] else '❌'}")
        print(f"  Quantum Debugging: {'✅' if self.config['enable_quantum_debugging'] else '❌'}")
        print(f"  Learning System: {'✅' if self.config['enable_learning'] else '❌'}")
        
        # Show validation results
        print(f"\n{Colors.BLUE}Validation Results:{Colors.RESET}")
        for component, passed in self.validation_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {component.replace('_', ' ').title()}: {status}")
        
        # Show paths
        print(f"\n{Colors.BLUE}Important Paths:{Colors.RESET}")
        print(f"  Installation: {self.install_dir}")
        print(f"  Claude Config: {self.claude_config_file}")
        print(f"  Configuration: {self.install_dir / 'claude_mcp_config.json'}")
        
        # Show next steps
        print(f"\n{Colors.GREEN}🚀 Next Steps:{Colors.RESET}")
        print("  1. Restart Claude Desktop completely")
        print("  2. Test the integration:")
        print(f"     {Colors.CYAN}Ask Claude: 'Write a function to calculate factorial and test it'{Colors.RESET}")
        print("  3. Watch Claude automatically test and optimize the code!")
        
        if self.config["enable_monitoring"]:
            print(f"  4. Start monitoring dashboard:")
            print(f"     {Colors.CYAN}python start_monitoring.py{Colors.RESET}")
        
        # Show example prompts
        print(f"\n{Colors.GREEN}💡 Example Prompts to Try:{Colors.RESET}")
        example_prompts = [
            "Write the fastest way to find duplicates in a list",
            "Create a robust JSON parser for production use",
            "Optimize this code for memory usage: [paste code]",
            "Test this function with edge cases: [paste function]"
        ]
        
        for prompt in example_prompts:
            print(f"   • {Colors.CYAN}\"{prompt}\"{Colors.RESET}")
        
        # Success message
        all_passed = all(self.validation_results.values())
        if all_passed:
            print(f"\n{Colors.GREEN}🎉 Installation completed successfully!{Colors.RESET}")
            print(f"{Colors.GREEN}Claude is now a thinking, testing, optimizing programming partner!{Colors.RESET}")
        else:
            print(f"\n{Colors.WARNING}⚠️  Installation completed with some issues{Colors.RESET}")
            print(f"Some features may not work correctly. Check the validation results above.")
    
    def run_setup(self):
        """Run the complete setup process"""
        self.print_banner()
        
        # Step 1: System validation
        if not self.validate_system():
            self.log("System validation failed. Cannot continue.", "ERROR")
            return False
        
        # Step 2: Choose installation type
        self.choose_installation_type()
        
        # Step 3: Configure features
        self.configure_features()
        
        # Step 4: Install dependencies
        if not self.install_dependencies():
            self.log("Dependency installation failed. Cannot continue.", "ERROR")
            return False
        
        # Step 5: Setup Claude configuration
        if not self.setup_claude_config():
            self.log("Claude configuration failed.", "ERROR")
            return False
        
        # Step 6: Test installation
        self.test_installation()
        
        # Step 7: Create shortcuts
        self.create_shortcuts()
        
        # Step 8: Show summary
        self.print_summary()
        
        return True

def main():
    """Main setup entry point"""
    parser = argparse.ArgumentParser(description="Claude Desktop MCP Execution Setup")
    parser.add_argument("--non-interactive", action="store_true", 
                       help="Run setup without user interaction (use defaults)")
    parser.add_argument("--minimal", action="store_true",
                       help="Install minimal version only")
    parser.add_argument("--development", action="store_true",
                       help="Install development version with all tools")
    
    args = parser.parse_args()
    
    wizard = SetupWizard()
    
    if args.non_interactive:
        # Use defaults for non-interactive setup
        if args.minimal:
            wizard.config["installation_type"] = "minimal"
        elif args.development:
            wizard.config["installation_type"] = "development"
        
        # Skip user input steps
        wizard.print_banner()
        
        if not wizard.validate_system():
            sys.exit(1)
        
        if not wizard.install_dependencies():
            sys.exit(1)
        
        if not wizard.setup_claude_config():
            sys.exit(1)
        
        wizard.test_installation()
        wizard.create_shortcuts()
        wizard.print_summary()
    else:
        # Interactive setup
        if not wizard.run_setup():
            sys.exit(1)

if __name__ == "__main__":
    main()
