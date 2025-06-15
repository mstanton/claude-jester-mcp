# Contributing to Claude Desktop MCP Execution

Thank you for your interest in contributing to the Claude Desktop MCP Execution project! This document provides guidelines and information for contributors.

## 🌟 Vision & Mission

We're building the future of AI-assisted programming by transforming Claude from a code generator into a **thinking, testing, optimizing programming partner**. Every contribution helps make AI programming safer, more effective, and more accessible to developers worldwide.

## 🚀 Quick Start for Contributors

### 1. Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/your-username/claude-desktop-mcp-execution.git
cd claude-desktop-mcp-execution

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev,all]"

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest
```

### 2. Create Development Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Make Your Changes

- Write code following our style guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 4. Submit Pull Request

```bash
git add .
git commit -m "feat: descriptive commit message"
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## 📋 Types of Contributions

### 🐛 Bug Reports
- Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md)
- Include reproduction steps and environment details
- Add logs, screenshots, or error messages

### ✨ Feature Requests
- Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)
- Explain the problem you're trying to solve
- Describe your proposed solution
- Consider implementation complexity

### 🔧 Code Contributions
- **Core Execution Engine**: Improve safety, performance, or compatibility
- **Quantum Debugging**: Enhance variant generation and optimization
- **Learning System**: Improve pattern recognition and adaptation
- **Monitoring & Analytics**: Better insights and visualizations
- **Security**: Strengthen sandboxing and validation
- **Documentation**: Improve guides, examples, and API docs

### 📚 Documentation
- Fix typos, unclear explanations, or outdated information
- Add examples and tutorials
- Improve API documentation
- Translate documentation (if applicable)

### 🧪 Testing
- Add unit tests for uncovered code
- Create integration tests
- Develop performance benchmarks
- Write security tests

## 🎯 Contribution Guidelines

### Code Style

We use automated formatting and linting:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/

# Run security checks
bandit -r src/
safety check
```

**Style Preferences:**
- **Python**: Follow PEP 8, use type hints, prefer descriptive names
- **Line Length**: 88 characters (Black default)
- **Imports**: Use isort for consistent import ordering
- **Comments**: Write clear docstrings, explain complex logic
- **Error Handling**: Use appropriate exceptions, provide helpful messages

### Testing Standards

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/claude_mcp --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m security      # Security tests only
pytest -m performance   # Performance benchmarks
```

**Testing Requirements:**
- **Unit Tests**: All new functions and classes
- **Integration Tests**: End-to-end functionality
- **Security Tests**: Sandbox escapes, injection attacks
- **Performance Tests**: Benchmark critical paths
- **Minimum Coverage**: 80% for new code

### Security Considerations

**Critical Areas:**
- **Code Execution**: All execution paths must be sandboxed
- **Input Validation**: Sanitize all user inputs
- **Resource Limits**: Prevent resource exhaustion
- **Dependency Security**: Regular vulnerability scans
- **Secrets Management**: Never commit credentials

**Security Review Process:**
1. All execution-related PRs require security review
2. Run security tests: `pytest -m security`
3. Security scan: `bandit -r src/`
4. Dependency check: `safety check`

### Performance Standards

**Benchmarks to Maintain:**
- **Code Execution**: < 10 seconds timeout
- **Variant Generation**: < 5 variants per request
- **Memory Usage**: < 256MB per execution
- **Startup Time**: < 3 seconds MCP server start
- **Response Time**: < 2 seconds for simple code

```bash
# Run performance tests
pytest -m performance

# Profile code execution
python -m cProfile -s tottime scripts/profile_execution.py
```

## 🏗️ Development Workflow

### Branch Naming Convention

- `feature/description` - New features
- `fix/issue-description` - Bug fixes
- `docs/topic` - Documentation updates
- `refactor/component` - Code refactoring
- `test/coverage-area` - Test improvements
- `security/vulnerability-type` - Security fixes

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Maintenance tasks
- `security`: Security improvements
- `perf`: Performance improvements

**Examples:**
```
feat(quantum): add parallel variant execution
fix(security): prevent code injection in executor
docs(api): update installation guide
test(core): add unit tests for SafeExecutor
```

### Pull Request Process

1. **Pre-PR Checklist:**
   - [ ] Tests pass locally
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] Security considerations addressed
   - [ ] Performance impact assessed

2. **PR Description Template:**
   ```markdown
   ## Summary
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Performance improvement
   - [ ] Security enhancement

   ## Testing
   - [ ] Unit tests added/updated
   - [ ] Integration tests pass
   - [ ] Security tests pass
   - [ ] Performance benchmarks run

   ## Documentation
   - [ ] Code comments updated
   - [ ] API documentation updated
   - [ ] User guides updated

   ## Security
   - [ ] Security review completed
   - [ ] No sensitive data exposed
   - [ ] Input validation implemented
   ```

3. **Review Process:**
   - Automated checks must pass
   - At least one maintainer review required
   - Security review for execution-related changes
   - Performance review for optimization changes

## 🧪 Testing Your Contributions

### Local Testing

```bash
# Full test suite
pytest

# Test specific components
pytest tests/core/test_executor.py
pytest tests/mcp/test_server.py
pytest tests/security/

# Integration testing with Claude Desktop
python scripts/test_mcp_integration.py
```

### Manual Testing

1. **MCP Server Testing:**
   ```bash
   # Start server manually
   python src/mcp/server.py
   
   # Test with sample requests
   echo '{"method": "tools/list", "id": 1}' | python src/mcp/server.py
   ```

2. **Code Execution Testing:**
   ```python
   from src.core.executor import CodeExecutor
   
   executor = CodeExecutor()
   result = await executor.execute_code("print('Hello, World!')")
   assert result.status == ExecutionStatus.SUCCESS
   ```

3. **Claude Desktop Integration:**
   - Install your changes locally
   - Test with Claude Desktop
   - Verify all tools work correctly

## 📖 Documentation Standards

### Code Documentation

```python
def execute_code(self, code: str, description: str = "") -> ExecutionResult:
    """Execute Python code with comprehensive safety checks.
    
    Args:
        code: Python code to execute
        description: Optional description of what the code should do
        
    Returns:
        ExecutionResult containing output, errors, and metadata
        
    Raises:
        SecurityError: If code contains dangerous patterns
        TimeoutError: If execution exceeds timeout limit
        
    Example:
        >>> executor = CodeExecutor()
        >>> result = await executor.execute_code("print('hello')")
        >>> assert result.status == ExecutionStatus.SUCCESS
    """
```

### User Documentation

- **Clear Examples**: Show actual usage patterns
- **Step-by-Step Guides**: Break complex processes down
- **Troubleshooting**: Address common issues
- **Screenshots**: Visual guides where helpful
- **Cross-References**: Link related sections

### API Documentation

- **Complete Coverage**: Document all public APIs
- **Parameter Details**: Types, defaults, constraints
- **Return Values**: Structure and meaning
- **Error Conditions**: When and why failures occur
- **Usage Examples**: Real-world scenarios

## 🔒 Security & Safety

### Security Review Requirements

**High-Risk Changes** (require security review):
- Code execution modifications
- Sandbox implementations
- Input validation changes
- Authentication/authorization
- Network communication
- File system access

**Security Testing:**
```bash
# Run security test suite
pytest -m security

# Static security analysis
bandit -r src/

# Dependency vulnerability check
safety check

# Container security (if applicable)
docker run --rm -v $(pwd):/app clair-scanner
```

### Responsible Disclosure

If you discover a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. **DO** email security@example.com with details
3. **DO** wait for acknowledgment before disclosure
4. **DO** provide PoC if possible (safely)

See [SECURITY.md](SECURITY.md) for full details.

## 🎉 Recognition & Community

### Contributor Recognition

- Contributors are listed in [AUTHORS.md](AUTHORS.md)
- Significant contributions highlighted in releases
- Annual contributor awards for outstanding work
- Speaking opportunities at conferences

### Community Guidelines

**Be Respectful:**
- Welcome newcomers and help them get started
- Provide constructive feedback
- Respect different perspectives and experiences
- Follow our [Code of Conduct](CODE_OF_CONDUCT.md)

**Be Collaborative:**
- Share knowledge and best practices
- Help review others' contributions
- Participate in discussions and planning
- Mentor new contributors

**Be Innovative:**
- Think creatively about AI-assisted programming
- Experiment with new approaches
- Share research and insights
- Push the boundaries of what's possible

## 📞 Getting Help

### Development Support

- **Discord**: [Join our dev community](https://discord.gg/claude-mcp-dev)
- **GitHub Discussions**: [Ask questions](https://github.com/your-username/claude-desktop-mcp-execution/discussions)
- **Email**: dev-support@example.com

### Mentorship Program

New contributors can request mentorship:
- Pair programming sessions
- Code review guidance
- Architecture discussions
- Career development advice

## 🗺️ Roadmap & Priorities

### Current Priorities

1. **Stability & Reliability**
   - Improve error handling
   - Enhance testing coverage
   - Performance optimization

2. **Security Enhancements**
   - Advanced sandboxing
   - Better input validation
   - Security monitoring

3. **Feature Expansion**
   - Multi-language support
   - Cloud execution
   - Team collaboration

### Long-term Vision

- **Universal AI Programming Assistant**
- **Advanced Learning & Adaptation**
- **Enterprise-grade Security**
- **Global Developer Community**

## 🙏 Thank You

Every contribution, no matter how small, helps build the future of AI-assisted programming. Whether you're fixing typos, implementing features, or sharing ideas, you're part of something revolutionary.

**Together, we're transforming how humans and AI collaborate to write better code.**

---

For questions about contributing, please reach out via:
- GitHub Issues for technical questions
- Discord for real-time discussions
- Email for private matters

**Happy coding!** 🚀✨
