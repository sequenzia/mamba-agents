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
- `rich` - Terminal formatting (display renderers)

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

**Philosophy**: Hub-and-spoke design. The `Agent` class is the central hub composing seven subsystems (`ContextManager`, `UsageTracker`, `TokenCounter`, `CostEstimator`, `PromptManager`, `SkillManager`, `SubagentManager`) behind a facade API. Dependencies flow strictly downward — no circular dependencies between modules. Design is "batteries included but optional": context tracking and auto-compaction default to enabled, but every feature can be disabled.

**Three-tier breakdown**:
- **Core Tier** (`agent`, `config`, `tokens`, `context`, `prompts`) — foundational agent execution with context tracking, token counting, cost estimation, and prompt templating
- **Extension Tier** (`tools`, `workflows`, `mcp`, `skills`, `subagents`, `errors`) — pluggable capabilities: filesystem/shell tools, ReAct workflow, MCP integration, skill management, subagent delegation, retry/circuit breaker
- **Infrastructure Tier** (`observability`, `backends`, `_internal`) — logging with redaction, model backend abstractions, internal utilities. Least integrated tier (observability has zero test coverage, circuit breaker not wired into Agent)

```
src/mamba_agents/
├── agent/           # Core agent (wraps pydantic-ai)
│   └── display/     # Message display & rendering (Rich, Plain, HTML)
├── config/          # Configuration system (pydantic-settings)
├── tools/           # Built-in tools (filesystem, bash, glob, grep)
├── context/         # Context window management & compaction
├── tokens/          # Token counting & cost estimation
├── prompts/         # Prompt template management (Jinja2)
├── skills/          # Skill discovery, loading, validation & invocation
├── subagents/       # Subagent spawning, delegation & lifecycle
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
    MessageQuery, MessageStats, ToolCallInfo, Turn,
    DisplayPreset, MessageRenderer, RichRenderer, PlainTextRenderer, HtmlRenderer,
    print_stats, print_timeline, print_tools,
    # Skills
    SkillManager, Skill, SkillInfo, SkillConfig, SkillScope, TrustLevel,
    ValidationResult, SkillError, SkillNotFoundError, SkillParseError,
    SkillValidationError, SkillLoadError, SkillConflictError,
    # Subagents
    SubagentManager, SubagentConfig, SubagentResult, DelegationHandle,
    SubagentError, SubagentConfigError, SubagentNotFoundError,
    SubagentNestingError, SubagentDelegationError, SubagentTimeoutError,
)

# Agent message utilities (for serializing/deserializing pydantic-ai messages)
from mamba_agents.agent import dicts_to_model_messages, model_messages_to_dicts

# Message querying and analytics
from mamba_agents.agent.messages import MessageQuery, MessageStats, ToolCallInfo, Turn

# Display rendering (for standalone use)
from mamba_agents.agent.display import (
    DisplayPreset, MessageRenderer, RichRenderer, PlainTextRenderer, HtmlRenderer,
    print_stats, print_timeline, print_tools,
)

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

# Skills subsystem
from mamba_agents.skills import (
    SkillManager, Skill, SkillInfo, SkillConfig, SkillScope, TrustLevel,
    ValidationResult,
    SkillError, SkillNotFoundError, SkillParseError,
    SkillValidationError, SkillLoadError, SkillConflictError,
)

# Skills testing utilities
from mamba_agents.skills.testing import SkillTestHarness, skill_harness

# Subagents subsystem
from mamba_agents.subagents import (
    SubagentManager, SubagentConfig, SubagentResult, DelegationHandle,
    SubagentError, SubagentConfigError, SubagentNotFoundError,
    SubagentNestingError, SubagentDelegationError, SubagentTimeoutError,
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
- **50% test coverage** target enforced (configured in `pyproject.toml` `fail_under`); actual coverage is ~68%
- **Experimental APIs**: Skills and subagents subsystems are experimental. Public API may change in minor versions

## Test Coverage Gaps

Well tested (>90%): agent core, display renderers, MCP integration, prompt management, workflows base, context management.

Low coverage modules that need attention:
- `observability/` — 0% (274 lines, includes security-relevant `SensitiveDataFilter`)
- `tools/glob.py` — 17%
- `tools/grep.py` — 20%
- `tools/bash.py` — 32%
- `tools/registry.py` — 43%
- `tools/base.py` — 0% (20 lines)

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
| Message querying & analytics | `src/mamba_agents/agent/messages.py` |
| Display renderers | `src/mamba_agents/agent/display/` |
| Display presets | `src/mamba_agents/agent/display/presets.py` |
| Display functions | `src/mamba_agents/agent/display/functions.py` |
| Snapshot golden files | `tests/unit/snapshots/display/` |
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
| Skill manager facade | `src/mamba_agents/skills/manager.py` |
| Skill data models & enums | `src/mamba_agents/skills/config.py` |
| Skill errors | `src/mamba_agents/skills/errors.py` |
| Skill SKILL.md loader | `src/mamba_agents/skills/loader.py` |
| Skill registry | `src/mamba_agents/skills/registry.py` |
| Skill validator | `src/mamba_agents/skills/validator.py` |
| Skill discovery | `src/mamba_agents/skills/discovery.py` |
| Skill invocation | `src/mamba_agents/skills/invocation.py` |
| Skill-subagent integration | `src/mamba_agents/skills/integration.py` |
| Skill testing harness | `src/mamba_agents/skills/testing.py` |
| Subagent manager facade | `src/mamba_agents/subagents/manager.py` |
| Subagent data models | `src/mamba_agents/subagents/config.py` |
| Subagent errors | `src/mamba_agents/subagents/errors.py` |
| Subagent spawner | `src/mamba_agents/subagents/spawner.py` |
| Subagent delegation | `src/mamba_agents/subagents/delegation.py` |
| Subagent config loader | `src/mamba_agents/subagents/loader.py` |
| Test fixtures | `tests/conftest.py` |
| Example config | `config.example.toml` |

## Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Facade** | `agent/core.py` (`Agent`) | Simplifies 7 subsystems behind unified API |
| **Template Method** | `context/compaction/base.py`, `workflows/base.py` | Invariant skeleton with abstract `_do_compact()` / `_execute()` hooks |
| **Strategy** | `context/compaction/` (5 strategies) | Pluggable compaction algorithms selected by config string |
| **Factory** | `errors/retry.py`, `mcp/client.py` | `create_retry_decorator()`, `MCPClientManager._create_server()` |
| **Circuit Breaker** | `errors/circuit_breaker.py` | CLOSED/OPEN/HALF_OPEN resilience with sliding window |
| **ABC** | `backends/base.py`, `context/compaction/base.py`, `workflows/base.py`, `agent/display/renderer.py` | Extension point contracts for backends, strategies, workflows, renderers |
| **Strategy** | `agent/display/` (3 renderers) | Pluggable Rich/Plain/HTML rendering selected by format string |
| **Facade** | `skills/manager.py` (`SkillManager`) | Composes loader, registry, validator, discovery, invocation behind unified API |
| **Facade** | `subagents/manager.py` (`SubagentManager`) | Composes spawner, delegation, loader behind unified API |
| **Registry** | `skills/registry.py` (`SkillRegistry`) | In-memory skill storage with async-safe register/get/list/deregister |
| **Lazy Loading** | `skills/loader.py` (`load_metadata`/`load_full`) | Progressive disclosure: Tier 1 metadata-only, Tier 2 full body |
| **Pipeline** | `skills/loader.py`, `subagents/loader.py` | `_read_file()` -> `_split_*()` -> `_parse_*()` -> `_validate_*()` -> `_map_*()` |
| **No-Nesting Guard** | `subagents/spawner.py` (`_enforce_no_nesting`) | Prevents subagents from spawning sub-subagents via `_is_subagent` flag |

## Known Fragility Points

- **`agent/message_utils.py`**: Uses type-name string matching (`msg_type == "ModelRequest"`) to convert pydantic-ai `ModelMessage` objects to dicts. Upstream message type renames could produce silently incorrect results. When modifying, add defensive checks.
- **ReActWorkflow mutates injected Agent**: `ReActWorkflow.__init__()` permanently registers a `final_answer` tool on the agent. Reusing the same Agent instance elsewhere will retain this tool. No cleanup mechanism exists.
- **Duplicate TokenCounter in CompactionStrategy**: `CompactionStrategy._count_tokens()` creates a fresh `TokenCounter()` with defaults, potentially inconsistent with the Agent's configured counter.
- **pydantic-ai version sensitivity**: The `>=0.0.49` pin targets a pre-1.0 library. `tracker.py` already handles an `input_tokens`/`request_tokens` API migration. Watch for breaking changes in message types, Model API, and toolset interfaces.
- **Skills-Subagents circular initialization**: `SkillManager` and `SubagentManager` reference each other. Post-construction wiring via `SkillManager.subagent_manager` setter avoids circular init, but the wiring order matters.
- **SubagentManager mutates parent UsageTracker**: `_aggregate_usage()` directly writes to `parent_agent.usage_tracker._subagent_totals`, coupling to internal state. Changes to `UsageTracker` internals could break subagent usage tracking.

## Implementation Notes

- **Data flow for `agent.run()`**:
  1. Resolve message history from ContextManager (dicts -> ModelMessage via `dicts_to_model_messages`)
  2. Delegate to `PydanticAgent.run()` with resolved history
  3. Wrap result in `AgentResult`
  4. Post-run: record usage via `UsageTracker.record_usage()`
  5. Post-run: convert new messages via `model_messages_to_dicts()` and store in ContextManager
  6. Post-run: check `should_compact()` and auto-compact if threshold reached
- The `Agent` class is a wrapper around `pydantic_ai.Agent` - delegate to it for core functionality
- Agent constructor behavior:
  - `Agent(settings=s)` - uses `settings.model_backend` for model, api_key, base_url
  - `Agent("gpt-4", settings=s)` - uses "gpt-4" as model, but api_key/base_url from settings
  - `Agent("gpt-4")` - passes string directly to pydantic-ai (requires `OPENAI_API_KEY` env var)
  - `Agent(model_instance)` - uses the Model instance directly
  - `Agent("gpt-4", tools=[...])` - registers tool functions
  - `Agent("gpt-4", toolsets=[...])` - registers MCP servers (use for MCP, not `tools`)
  - `Agent("gpt-4", skills=[...])` - registers skills (Skill instances, string paths, or Path objects)
  - `Agent("gpt-4", skill_dirs=[...])` - discovers and registers skills from directories
  - `Agent("gpt-4", subagents=[...])` - registers subagent configs (SubagentConfig instances)
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
  - Messages: `messages` property returns `MessageQuery` for filtering, analytics, and export
  - Skills: `skill_manager` (lazy property), `register_skill()`, `get_skill()`, `list_skills()`, `invoke_skill()`
  - Subagents: `subagent_manager` (lazy property), `delegate()`, `delegate_sync()`, `delegate_async()`, `register_subagent()`, `list_subagents()`
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
- **Message Querying & Analytics** provides filtering, analytics, and export for conversation history:
  - `agent.messages` returns a `MessageQuery` instance (new instance each access, stateless)
  - `MessageQuery` is constructed with `messages: list[dict]` and optional `TokenCounter`
  - **Filtering**: `filter(role=, tool_name=, content=, regex=)` with AND logic, `slice()`, `first()`, `last()`, `all()`
  - **Analytics**: `stats()` returns `MessageStats`, `tool_summary()` returns `list[ToolCallInfo]`, `timeline()` returns `list[Turn]`
  - **Export**: `export(format=)` supports "json", "markdown", "csv", "dict" formats
  - Data models (`MessageStats`, `ToolCallInfo`, `Turn`) use `@dataclass` (project convention for output types)
  - Works when `track_context=False` (returns empty results) and when `TokenCounter` is None (token counts are 0)
  - **Display**: `print_stats()`, `print_timeline()`, `print_tools()` convenience methods delegate to standalone functions via lazy import
- **Display Rendering** provides Rich/Plain/HTML output for message analytics:
  - `MessageRenderer` is an ABC with `render_stats()`, `render_timeline()`, `render_tools()` methods
  - Three renderers: `RichRenderer` (Rich Console), `PlainTextRenderer` (ASCII), `HtmlRenderer` (semantic HTML)
  - Three presets: `COMPACT`, `DETAILED`, `VERBOSE` — access via `get_preset("name", **overrides)`
  - `DisplayPreset` is `@dataclass(frozen=True)` with fields: show_role_breakdown, show_token_info, show_tool_args, show_tool_results, max_content_length
  - Standalone functions: `print_stats(data, preset, format, **options)`, `print_timeline(...)`, `print_tools(...)`
  - `MessageQuery` delegates to standalone functions: `query.print_stats()`, `query.print_timeline()`, `query.print_tools()`
  - Rich `__rich_console__` protocol on `MessageStats`, `ToolCallInfo`, `Turn` for `console.print(stats)` usage
  - Snapshot tests in `tests/unit/test_display_snapshots.py` with golden files in `tests/unit/snapshots/display/`; regenerate with `UPDATE_SNAPSHOTS=1`
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
- **Skills System** provides modular, discoverable agent capabilities (experimental):
  - `SkillManager` is the top-level facade composing loader, registry, validator, discovery, and invocation
  - Skills follow the SKILL.md open standard: YAML frontmatter + markdown body
  - **Progressive disclosure** (three tiers):
    - Tier 1: `load_metadata(path)` returns `SkillInfo` (frontmatter only, loaded eagerly at discovery)
    - Tier 2: `load_full(path)` returns `Skill` (frontmatter + body, loaded lazily on first activation)
    - Tier 3: `get_references(name)` / `load_reference(name, ref)` loads supplemental files on demand
  - **Discovery** scans three-level directory hierarchy with priority: project (`.mamba/skills/`) > user (`~/.mamba/skills/`) > custom paths
  - **Trust levels**: `TrustLevel.TRUSTED` (full access) and `TrustLevel.UNTRUSTED` (restricted capabilities). Project/user scopes default to trusted; custom paths configurable via `SkillConfig.trusted_paths`
  - **Invocation lifecycle**: permission check -> lazy body load -> argument substitution -> activation state management -> tool registration
  - `InvocationSource` enum: `MODEL`, `USER`, `CODE` -- controls permission gates (e.g., `user_invocable=False` blocks user invocations)
  - Agent accepts `skills` and `skill_dirs` constructor params for eager registration
  - Agent facade: `skill_manager` (lazy property), `register_skill()`, `get_skill()`, `list_skills()`, `invoke_skill()`
  - `SkillConfig` configures: `skills_dirs`, `user_skills_dir`, `custom_paths`, `auto_discover`, `namespace_tools`, `trusted_paths`
  - `AgentSettings.skills` provides default `SkillConfig`
  - `SkillTestHarness` enables testing skills without a full Agent instance; `skill_harness` pytest fixture for convenience
  - Lazy initialization: `_pending_skills`/`_pending_skill_dirs` stored in constructor, `skill_manager` property creates `SkillManager` on first access
  - TYPE_CHECKING imports used for skill types in `core.py` to avoid circular imports; runtime imports are lazy inside methods
- **Subagents System** provides task delegation to isolated child agents (experimental):
  - `SubagentManager` is the top-level facade composing spawner, delegation, and loader
  - Subagents are isolated `Agent` instances with their own `ContextManager`, `UsageTracker`, etc.
  - **No-nesting rule**: subagents cannot spawn sub-subagents (enforced via `AgentConfig._is_subagent` private attribute)
  - **Spawning**: `spawn()` creates a new Agent from `SubagentConfig`, inheriting model/tools from parent unless overridden
  - **Delegation**: three patterns -- `delegate()` (async), `delegate_sync()` (sync wrapper), `delegate_async()` (fire-and-forget with `DelegationHandle`)
  - Token usage automatically aggregated to parent's `UsageTracker` with per-subagent breakdown via `_subagent_totals`
  - **Config loading**: markdown files in `.mamba/agents/{name}.md` with YAML frontmatter + optional system prompt body
  - `SubagentConfig` fields: `name`, `description`, `model`, `tools`, `disallowed_tools`, `system_prompt`, `skills` (pre-load list), `max_turns`, `config`
  - Agent accepts `subagents` constructor param for eager registration
  - Agent facade: `subagent_manager` (lazy property), `delegate()`, `delegate_sync()`, `delegate_async()`, `register_subagent()`, `list_subagents()`
  - `_UsageTrackingHandle` extends `DelegationHandle` to aggregate usage on async result completion
  - `spawn_dynamic()` creates one-off subagents from runtime configs without registering
- **Skills-Subagents Integration** enables bi-directional wiring:
  - Skills with `execution_mode: "fork"` delegate to a subagent instead of returning content directly
  - `activate_with_fork()` in `skills/integration.py` handles: trust check -> circular detection -> content preparation -> subagent delegation
  - `detect_circular_skill_subagent()` traces skill -> agent -> pre-loaded skills chains to prevent cycles
  - `SkillManager.subagent_manager` is a settable property for post-construction wiring (avoids circular initialization)
  - Untrusted skills cannot use fork execution mode
  - Named subagent configs (`agent` field) must exist in the `SubagentManager`; unnamed forks create temporary subagents via `spawn_dynamic()`
