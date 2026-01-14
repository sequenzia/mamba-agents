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
├── workflows/       # Agentic workflow orchestration (ReAct, Plan-Execute, etc.)
├── mcp/             # Model Context Protocol integration
├── backends/        # OpenAI-compatible model backends
├── observability/   # Logging and tracing
├── errors/          # Error handling & circuit breaker
└── _internal/       # Internal utilities
```

## Key Entry Points

```python
# Main exports (context and token tracking built into Agent)
from pydantic_agent import (
    Agent, AgentSettings, AgentConfig, AgentResult,
    CompactionConfig, CompactionResult, ContextState,
    TokenUsage, UsageRecord, CostBreakdown,
    Workflow, WorkflowConfig, WorkflowHooks,
    WorkflowResult, WorkflowState, WorkflowStep,
)

# Tools
from pydantic_agent.tools import read_file, write_file, run_bash, glob_search, grep_search

# Context management (for standalone use)
from pydantic_agent.context import ContextManager, CompactionConfig

# Token tracking (for standalone use)
from pydantic_agent.tokens import TokenCounter, UsageTracker, CostEstimator

# Workflows (for custom workflow implementations)
from pydantic_agent.workflows import Workflow, WorkflowConfig, WorkflowHooks

# MCP integration
from pydantic_agent.mcp import MCPClientManager, MCPServerConfig

# Model backends
from pydantic_agent.backends import create_ollama_backend, create_vllm_backend
```

## Configuration System

Settings use the `AGENTS_` prefix with nested settings using double underscore (`__`):

```bash
AGENTS_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1
AGENTS_MODEL_BACKEND__MODEL=llama3.2
AGENTS_LOGGING__LEVEL=DEBUG
AGENTS_RETRY__RETRY_LEVEL=2
```

Variables are loaded from (in priority order):
1. Environment variables
2. `.env` file (project-specific)
3. `~/agents.env` (user-wide defaults)

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
| Agent config | `src/pydantic_agent/agent/config.py` |
| Message conversion utils | `src/pydantic_agent/agent/message_utils.py` |
| Built-in tools | `src/pydantic_agent/tools/` |
| Context compaction | `src/pydantic_agent/context/compaction/` |
| Workflow base classes | `src/pydantic_agent/workflows/base.py` |
| Workflow config | `src/pydantic_agent/workflows/config.py` |
| Test fixtures | `tests/conftest.py` |
| Example config | `config.example.toml` |

## Implementation Notes

- The `Agent` class is a wrapper around `pydantic_ai.Agent` - delegate to it for core functionality
- Agent constructor behavior:
  - `Agent(settings=s)` - uses `settings.model_backend` for model, api_key, base_url
  - `Agent("gpt-4", settings=s)` - uses "gpt-4" as model, but api_key/base_url from settings
  - `Agent("gpt-4")` - passes string directly to pydantic-ai (requires `OPENAI_API_KEY` env var)
  - `Agent(model_instance)` - uses the Model instance directly
- **Agent manages context and token tracking directly** (no separate instantiation needed):
  - Context tracking enabled by default (`AgentConfig.track_context=True`)
  - Auto-compaction when threshold reached (`AgentConfig.auto_compact=True`)
  - Usage tracking always on - accessible via `agent.get_usage()`, `agent.get_cost()`
  - Messages tracked across runs - accessible via `agent.get_messages()`
  - Advanced users can access internals: `agent.context_manager`, `agent.usage_tracker`
- AgentConfig options for context/tracking:
  - `track_context: bool = True` - enable/disable internal message tracking
  - `auto_compact: bool = True` - enable/disable auto-compaction
  - `context: CompactionConfig | None` - custom compaction config (uses settings default if None)
  - `tokenizer: TokenizerConfig | None` - custom tokenizer config (uses settings default if None)
- Agent facade methods:
  - Token counting: `get_token_count(text=None)`
  - Usage: `get_usage()`, `get_usage_history()`
  - Cost: `get_cost()`, `get_cost_breakdown()`
  - Context: `get_messages()`, `should_compact()`, `compact()`, `get_context_state()`
  - Reset: `clear_context()`, `reset_tracking()`, `reset_all()`
- Context compaction has 5 strategies: sliding_window, summarize_older, selective_pruning, importance_scoring, hybrid
- MCP supports stdio and SSE transports with optional API key authentication
- Error recovery has 3 levels: conservative (1), balanced (2), aggressive (3)
- **Workflows** provide orchestration patterns for multi-step agent execution:
  - `Workflow` is an ABC - extend it to create custom patterns (ReAct, Plan-Execute, Reflection)
  - Workflows take agents as inputs (separate execution layer, not embedded in Agent)
  - `WorkflowState` tracks steps, iterations, and custom context (independent from ContextManager)
  - `WorkflowHooks` provides 8 callbacks: workflow start/complete/error, step start/complete/error, iteration start/complete
  - `WorkflowConfig` controls max_steps, max_iterations, timeouts, and hook enablement
  - Async-first with `run_sync()` wrapper (matches Agent pattern)
  - Extend `Workflow` by implementing: `name` property, `_create_initial_state()`, `_execute()`
