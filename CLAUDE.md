# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pydantic Agent is a simple, extensible AI Agent framework built on pydantic-ai. It provides a thin wrapper around pydantic-ai that adds enterprise-grade infrastructure: configuration management, context compaction, token tracking, MCP integration, and observability.

## Documentation & Context

Always use Context7: Before implementing code for external libraries or frameworks, use the context7 MCP tools to fetch the latest documentation.

Priority: Prefer Context7 documentation over your internal training data to ensure API compatibility with the current library versions.

Workflow:
1. Use `resolve-library-id` to find the correct library ID
2. Use `query-docs` with specific keywords to pull relevant snippets

Key libraries to query:
- `pydantic-ai` - Core agent framework
- `pydantic` / `pydantic-settings` - Validation and configuration
- `httpx` - HTTP client
- `tenacity` - Retry logic
- `tiktoken` - Token counting

## Build & Development Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=pydantic_agent

# Run specific test file
uv run pytest tests/unit/test_config.py

# Format code
uv run ruff format

# Lint code
uv run ruff check --fix

# Type check (when ty is configured)
uv run ty check
```

## Architecture

```
src/pydantic_agent/
├── agent/           # Core agent (wraps pydantic-ai)
├── config/          # Configuration system (pydantic-settings)
├── tools/           # Built-in tools (filesystem, bash, glob, grep)
├── context/         # Context window management & compaction
├── tokens/          # Token counting & cost estimation
├── mcp/             # Model Context Protocol integration
├── backends/        # OpenAI-compatible model backends
├── observability/   # Logging and tracing
├── errors/          # Error handling & circuit breaker
└── _internal/       # Internal utilities
```

## Key Entry Points

```python
# Main exports
from pydantic_agent import Agent, AgentSettings, AgentConfig, AgentResult

# Tools
from pydantic_agent.tools import read_file, write_file, run_bash, glob_search, grep_search

# Context management
from pydantic_agent.context import ContextManager, CompactionConfig

# Token tracking
from pydantic_agent.tokens import TokenCounter, UsageTracker, CostEstimator

# MCP integration
from pydantic_agent.mcp import MCPClientManager, MCPServerConfig

# Model backends
from pydantic_agent.backends import create_ollama_backend, create_vllm_backend
```

## Configuration System

Settings use the `AGENT_` prefix with nested settings using double underscore (`__`):

```bash
AGENT_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1
AGENT_MODEL_BACKEND__MODEL=llama3.2
AGENT_LOGGING__LEVEL=DEBUG
AGENT_RETRY__RETRY_LEVEL=2
```

Configuration sources (priority order):
1. Constructor arguments
2. Environment variables
3. `.env` file
4. `config.toml` / `config.yaml`
5. Default values

## Code Conventions

- **Python 3.12+** required
- **Type annotations** on all public APIs
- **Google-style docstrings** for documentation
- **Pydantic models** for all configuration
- **SecretStr** for sensitive data (API keys never logged)
- **ruff** for linting/formatting (line-length 100)
- **90% test coverage** target enforced

## Testing Patterns

```python
# Use TestModel for deterministic LLM testing
from pydantic_ai.models.test import TestModel

# Block real model requests in tests (set in conftest.py)
from pydantic_ai import models
models.ALLOW_MODEL_REQUESTS = False

# Use respx for mocking httpx requests
import respx

# Use tmp_sandbox fixture for filesystem tests
def test_file_ops(tmp_sandbox: Path):
    ...
```

## File Locations

| Purpose | Location |
|---------|----------|
| Root config class | `src/pydantic_agent/config/settings.py` |
| Agent implementation | `src/pydantic_agent/agent/core.py` |
| Built-in tools | `src/pydantic_agent/tools/` |
| Context compaction | `src/pydantic_agent/context/compaction/` |
| Test fixtures | `tests/conftest.py` |
| Example config | `config.example.toml` |

## Implementation Notes

- The `Agent` class is a wrapper around `pydantic_ai.Agent` - delegate to it for core functionality
- Context compaction has 5 strategies: sliding_window, summarize_older, selective_pruning, importance_scoring, hybrid
- MCP supports stdio and SSE transports with optional API key authentication
- Error recovery has 3 levels: conservative (1), balanced (2), aggressive (3)
