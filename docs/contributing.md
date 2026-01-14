# Contributing

Thank you for your interest in contributing to Pydantic Agent!

## Development Setup

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) package manager

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/sequenzia/pydantic-agent.git
cd pydantic-agent

# Install dependencies
uv sync --group dev

# Verify installation
uv run pytest --version
```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=pydantic_agent

# Run specific test file
uv run pytest tests/unit/test_config.py

# Run tests matching pattern
uv run pytest -k "test_agent"
```

### Code Quality

```bash
# Format code
uv run ruff format

# Check formatting
uv run ruff format --check

# Lint code
uv run ruff check

# Auto-fix lint issues
uv run ruff check --fix

# Type checking (when configured)
uv run ty check
```

### Documentation

```bash
# Install docs dependencies
uv sync --group docs

# Serve docs locally
uv run mkdocs serve

# Build docs
uv run mkdocs build
```

## Code Standards

### Python Style

- **Python 3.12+** features are welcome
- **Type annotations** on all public APIs
- **Google-style docstrings** for documentation
- **ruff** for linting and formatting (line-length 100)

### Example Docstring

```python
def calculate_cost(tokens: int, model: str) -> float:
    """
    Calculate the cost for token usage.

    Args:
        tokens: Number of tokens used
        model: Model identifier (e.g., "gpt-4o")

    Returns:
        Estimated cost in USD

    Raises:
        ValueError: If model is not recognized

    Example:
        >>> calculate_cost(1000, "gpt-4o")
        0.0025
    """
```

### Testing Guidelines

- Use `pytest` for all tests
- Use `TestModel` from pydantic-ai for deterministic testing
- Block real model requests in tests (see `conftest.py`)
- Use `respx` for HTTP mocking
- Target 90% code coverage

```python
from pydantic_ai.models.test import TestModel
from pydantic_ai import models

# Block real requests
models.ALLOW_MODEL_REQUESTS = False

def test_agent_with_test_model():
    agent = Agent(TestModel())
    result = agent.run_sync("Hello")
    assert result.output == "test response"
```

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new compaction strategy
fix: handle empty message list
docs: update API reference
test: add workflow tests
refactor: simplify token counting
```

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/my-feature`)
3. **Make** your changes
4. **Add** tests for new functionality
5. **Run** tests and linting (`uv run pytest && uv run ruff check`)
6. **Commit** with a descriptive message
7. **Push** to your fork
8. **Open** a pull request

### PR Checklist

- [ ] Tests pass (`uv run pytest`)
- [ ] Linting passes (`uv run ruff check`)
- [ ] Coverage maintained at 90%+
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventions

## Project Structure

```
src/pydantic_agent/
├── agent/           # Core agent
├── config/          # Configuration
├── context/         # Context management
├── tokens/          # Token tracking
├── workflows/       # Workflow orchestration
├── tools/           # Built-in tools
├── mcp/             # MCP integration
├── backends/        # Model backends
├── observability/   # Logging/tracing
└── errors/          # Error handling

tests/
├── unit/            # Unit tests
├── integration/     # Integration tests
├── fixtures/        # Test fixtures
└── conftest.py      # Pytest configuration

docs/
├── getting-started/ # Getting started guides
├── user-guide/      # User guides
├── tutorials/       # Tutorials
├── concepts/        # Concept explanations
└── api/             # API reference
```

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/sequenzia/pydantic-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sequenzia/pydantic-agent/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
