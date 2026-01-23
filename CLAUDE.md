# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mamba Agents is a simple, extensible AI Agent framework built on pydantic-ai. It provides a thin wrapper around pydantic-ai that adds enterprise-grade infrastructure: configuration management, context compaction, token tracking, MCP integration, and observability.

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
uv run pytest --cov=mamba_agents

# Run specific test file
uv run pytest tests/unit/test_config.py

# Format code
uv run ruff format

# Lint code
uv run ruff check --fix

# Type check (when ty is configured)
uv run ty check

# Build package
uv build
```

## Versioning & Build System

- **Build backend**: hatchling with hatch-vcs for version management
- **Version source**: Git tags (e.g., `v0.1.0` → version `0.1.0`)
- **Version file**: `src/mamba_agents/_version.py` (auto-generated, gitignored)
- **Development versions**: Commits without tags get versions like `0.1.0.dev12`

### Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, build config, tool settings |
| `.github/workflows/ci.yml` | CI: lint, test (3.12 & 3.13), build |
| `.github/workflows/release.yml` | Release: build → TestPyPI → PyPI |
| `CHANGELOG.md` | Release history (Keep a Changelog format) |

### Release Process

1. Update `CHANGELOG.md` with release notes
2. Create annotated tag: `git tag -a v0.2.0 -m "Release v0.2.0"`
3. Push tag: `git push origin v0.2.0`
4. GitHub Actions automatically publishes to PyPI via OIDC trusted publishing

### Version Access in Code

```python
from mamba_agents import __version__
print(__version__)  # e.g., "0.1.0" or "0.1.0.dev12"
```

## Architecture

```
src/mamba_agents/
├── agent/           # Core agent (wraps pydantic-ai)
├── config/          # Configuration system (pydantic-settings)
├── tools/           # Built-in tools (filesystem, bash, glob, grep)
├── context/         # Context window management & compaction
├── tokens/          # Token counting & cost estimation
├── prompts/         # Prompt template management (Jinja2)
├── workflows/       # Agentic workflow orchestration (ReAct implemented)
├── mcp/             # Model Context Protocol integration
├── backends/        # OpenAI-compatible model backends
├── observability/   # Logging and tracing
├── errors/          # Error handling & circuit breaker
└── _internal/       # Internal utilities
```

## Key Entry Points

```python
# Main exports (context and token tracking built into Agent)
from mamba_agents import (
    Agent, AgentSettings, AgentConfig, AgentResult,
    CompactionConfig, CompactionResult, ContextState,
    TokenUsage, UsageRecord, CostBreakdown,
    PromptConfig, PromptManager, PromptTemplate, TemplateConfig,
    MCPClientManager, MCPServerConfig, MCPAuthConfig,
    Workflow, WorkflowConfig, WorkflowHooks,
    WorkflowResult, WorkflowState, WorkflowStep,
)

# Agent message utilities (for serializing/deserializing pydantic-ai messages)
from mamba_agents.agent import dicts_to_model_messages, model_messages_to_dicts

# Tools
from mamba_agents.tools import (
    read_file, write_file, append_file, delete_file, copy_file, move_file,
    list_directory, file_info,
    run_bash,
    glob_search, grep_search,
    ToolRegistry,
)

# Context management (for standalone use)
from mamba_agents.context import ContextManager, CompactionConfig

# Token tracking (for standalone use)
from mamba_agents.tokens import TokenCounter, UsageTracker, CostEstimator, TokenizerConfig

# Prompt management (for standalone use)
from mamba_agents.prompts import PromptManager, PromptTemplate, PromptConfig, TemplateConfig

# Workflows (for custom workflow implementations)
from mamba_agents.workflows import (
    Workflow, WorkflowConfig, WorkflowHooks,
    WorkflowResult, WorkflowState, WorkflowStep,
    WorkflowError, WorkflowExecutionError, WorkflowTimeoutError,
    WorkflowMaxStepsError, WorkflowMaxIterationsError,
)

# ReAct workflow (built-in implementation)
from mamba_agents.workflows import (
    ReActWorkflow, ReActConfig, ReActState, ReActHooks, ScratchpadEntry,
)

# MCP integration
from mamba_agents.mcp import (
    MCPClientManager, MCPServerConfig, MCPAuthConfig,
    load_mcp_json,  # Load from .mcp.json files
    MCPConfigError, MCPFileNotFoundError, MCPFileParseError, MCPServerValidationError,
    MCPConnectionError, MCPConnectionTimeoutError, MCPServerNotFoundError,
    MCPConnectionResult, MCPToolInfo,
)

# Model backends
from mamba_agents.backends import (
    create_ollama_backend, create_vllm_backend, create_lmstudio_backend,
    ModelBackend, ModelProfile, get_profile, register_profile,
)
```

## Configuration System

Settings use the `MAMBA_` prefix with nested settings using double underscore (`__`):

```bash
MAMBA_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1
MAMBA_MODEL_BACKEND__MODEL=llama3.2
MAMBA_LOGGING__LEVEL=DEBUG
MAMBA_RETRY__RETRY_LEVEL=2
```

Variables are loaded from (in priority order):
1. Environment variables
2. `.env` file (project-specific)
3. `~/mamba.env` (user-wide defaults)

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
| Root config class | `src/mamba_agents/config/settings.py` |
| Agent implementation | `src/mamba_agents/agent/core.py` |
| Agent config | `src/mamba_agents/agent/config.py` |
| Message conversion utils | `src/mamba_agents/agent/message_utils.py` |
| Built-in tools | `src/mamba_agents/tools/` |
| Context compaction | `src/mamba_agents/context/compaction/` |
| Prompt management | `src/mamba_agents/prompts/` |
| Prompt config | `src/mamba_agents/prompts/config.py` |
| Prompt manager | `src/mamba_agents/prompts/manager.py` |
| Workflow base classes | `src/mamba_agents/workflows/base.py` |
| Workflow config | `src/mamba_agents/workflows/config.py` |
| MCP client manager | `src/mamba_agents/mcp/client.py` |
| MCP config | `src/mamba_agents/mcp/config.py` |
| MCP auth | `src/mamba_agents/mcp/auth.py` |
| MCP env resolution | `src/mamba_agents/mcp/env.py` |
| MCP file loader | `src/mamba_agents/mcp/loader.py` |
| MCP errors | `src/mamba_agents/mcp/errors.py` |
| Test fixtures | `tests/conftest.py` |
| Example config | `config.example.toml` |

## Implementation Notes

- The `Agent` class is a wrapper around `pydantic_ai.Agent` - delegate to it for core functionality
- Agent constructor behavior:
  - `Agent(settings=s)` - uses `settings.model_backend` for model, api_key, base_url
  - `Agent("gpt-4", settings=s)` - uses "gpt-4" as model, but api_key/base_url from settings
  - `Agent("gpt-4")` - passes string directly to pydantic-ai (requires `OPENAI_API_KEY` env var)
  - `Agent(model_instance)` - uses the Model instance directly
  - `Agent("gpt-4", tools=[...])` - registers tool functions
  - `Agent("gpt-4", toolsets=[...])` - registers MCP servers (use for MCP, not `tools`)
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
- **Prompt Management** provides Jinja2-based template system:
  - `PromptManager` loads templates from files or registers them programmatically
  - `PromptTemplate` wraps Jinja2 templates with `render()`, `with_variables()`, `get_variables()`
  - `TemplateConfig` references templates by name/version with variables
  - File organization: `prompts/{version}/{category}/{name}.jinja2` (e.g., `prompts/v1/system/assistant.jinja2`)
  - Supports Jinja2 inheritance with `{% extends %}` and `{% block %}`
  - Agent accepts `system_prompt: str | TemplateConfig` (backward compatible)
  - Agent facade methods: `get_system_prompt()`, `set_system_prompt(prompt, **variables)`
  - `AgentSettings.prompts` provides default `PromptConfig`
  - ReActWorkflow supports `system_prompt_template` and `iteration_prompt_template` in config
- **MCP Integration** provides Model Context Protocol support:
  - Agent accepts `toolsets` parameter for MCP servers: `Agent("gpt-4", toolsets=[...])`
  - Use `MCPClientManager.as_toolsets()` to create servers from config (recommended)
  - pydantic-ai handles MCP server lifecycle automatically (no manual connect/disconnect)
  - Supports stdio (subprocess), SSE (HTTP), and Streamable HTTP transports
  - `MCPServerConfig` defines server: name, transport, command/url, auth, tool_prefix, env_file, env_vars, timeout, read_timeout
  - `MCPAuthConfig` handles API key auth via direct key or env var (`key_env` or `${VAR}` syntax)
  - `tool_prefix` avoids name conflicts when using multiple servers
  - `env_file` and `env_vars` configure environment for stdio servers (precedence: env_vars > env_file > system env)
  - `timeout` (default: 30s) and `read_timeout` (default: 300s) control MCP server initialization and read timeouts
  - **File-based config**: Load from `.mcp.json` files (Claude Desktop compatible format)
    - `MCPClientManager.from_mcp_json(path)` - create manager from file
    - `manager.add_from_file(path)` - add configs from file to existing manager
    - `load_mcp_json(path)` - load configs directly (returns `list[MCPServerConfig]`)
    - Supports standard fields: command, args, env, url
    - Extended fields: tool_prefix, env_file (mamba-agents additions)
    - Transport auto-detected: URLs ending with /sse → SSE, other URLs → Streamable HTTP, command → stdio
  - MCP errors: `MCPConfigError`, `MCPFileNotFoundError`, `MCPFileParseError`, `MCPServerValidationError`, `MCPConnectionError`, `MCPConnectionTimeoutError`, `MCPServerNotFoundError`
- Error recovery has 3 levels: conservative (1), balanced (2), aggressive (3)
- **Workflows** provide orchestration patterns for multi-step agent execution:
  - `Workflow` is an ABC - extend it to create custom patterns
  - Currently only ReAct is built-in; extend `Workflow` for Plan-Execute, Reflection, or other patterns
  - Workflows take agents as inputs (separate execution layer, not embedded in Agent)
  - `WorkflowState` tracks steps, iterations, and custom context (independent from ContextManager)
  - `WorkflowHooks` provides 8 callbacks: workflow start/complete/error, step start/complete/error, iteration start/complete
  - `WorkflowConfig` controls max_steps, max_iterations, timeouts, and hook enablement
  - Async-first with `run_sync()` wrapper (matches Agent pattern)
  - Extend `Workflow` by implementing: `name` property, `_create_initial_state()`, `_execute()`
- **ReActWorkflow** is a built-in implementation of the ReAct paradigm:
  - Implements Thought → Action → Observation loop until `final_answer` tool is called
  - `ReActConfig` extends `WorkflowConfig` with: expose_reasoning, prefixes, termination settings, compaction
  - `ReActState` tracks scratchpad (thoughts/actions/observations), token counts, termination status
  - `ReActHooks` extends `WorkflowHooks` with: on_thought, on_action, on_observation, on_compaction
  - Registers `final_answer` tool on the agent for termination detection
  - Auto-compacts context when threshold ratio is reached
  - Access scratchpad via `result.state.context.scratchpad` or `workflow.get_scratchpad()`
