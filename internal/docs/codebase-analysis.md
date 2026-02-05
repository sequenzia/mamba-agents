# Codebase Analysis Report

**Analysis Context**: General codebase understanding
**Codebase Path**: `/Users/sequenzia/dev/repos/mamba-agents`
**Date**: 2026-02-05

---

## Executive Summary

Mamba Agents is a well-architected "batteries included but optional" wrapper around pydantic-ai that follows a strict hub-and-spoke facade pattern — the `Agent` class composes five subsystems (ContextManager, UsageTracker, TokenCounter, CostEstimator, PromptManager) behind a unified 30+ method API with no circular dependencies. The framework is in active early development (v0.1.7, 8 releases in ~2 weeks) with strong test coverage (68%, 1429 tests) and mature design patterns, but its **highest-priority risk is the fragile string-based type matching in `message_utils.py`** that couples it to pydantic-ai's pre-1.0 internal class names without defensive checks.

---

## Architecture Overview

The codebase layers into three tiers:

**Core Tier** — `agent`, `config`, `tokens`, `context`, `prompts` — provides the foundational agent execution loop with context tracking, token counting, cost estimation, and prompt templating baked in by default. The `Agent` class (862 lines) serves as the central hub, composing five subsystems and exposing facade methods that delegate to each.

**Extension Tier** — `tools`, `workflows`, `mcp`, `errors` — adds pluggable capabilities: built-in filesystem/shell tools with optional sandboxing, ReAct workflow orchestration, MCP server integration (stdio/SSE/streamable HTTP), and resilience patterns (tenacity retry, circuit breaker).

**Infrastructure Tier** — `observability`, `backends`, `_internal` — provides logging with sensitive data redaction, OpenAI-compatible model backend abstractions, and internal utilities. This tier is the least integrated — observability has zero test coverage and the circuit breaker is not wired into any execution path.

**Key technologies**: Python 3.12+, pydantic-ai (>=0.0.49), pydantic-settings, httpx, tiktoken, tenacity, Jinja2, Rich. Build tooling: uv, hatch-vcs, ruff, pytest.

---

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `src/mamba_agents/agent/core.py` | Central Agent facade (862 lines) | High |
| `src/mamba_agents/agent/message_utils.py` | pydantic-ai ModelMessage <-> dict conversion | High |
| `src/mamba_agents/agent/messages.py` | MessageQuery: filtering, analytics, export (1278 lines) | High |
| `src/mamba_agents/agent/config.py` | AgentConfig execution settings | High |
| `src/mamba_agents/config/settings.py` | Root AgentSettings with 6-level config hierarchy | High |
| `src/mamba_agents/context/manager.py` | ContextManager: history + compaction orchestration | High |
| `src/mamba_agents/context/compaction/base.py` | CompactionStrategy ABC (Template Method) | High |
| `src/mamba_agents/tokens/counter.py` | tiktoken wrapper with LRU caching | High |
| `src/mamba_agents/tokens/tracker.py` | Per-request and aggregate usage tracking | High |
| `src/mamba_agents/workflows/react/workflow.py` | ReAct (Thought->Action->Observation) implementation | High |
| `src/mamba_agents/mcp/client.py` | MCPClientManager: MCP toolset factory | High |

### File Details

#### `src/mamba_agents/agent/core.py`
- **Key exports**: `Agent[DepsT, OutputT]` class
- **Core logic**: `__init__()` resolves model and initializes 5 subsystems. `run()`/`run_sync()`/`run_stream()` delegate to pydantic-ai then call `_do_post_run_tracking()`. `_wrap_tool_with_graceful_errors()` converts tool exceptions to `ModelRetry`.
- **Connections**: Depends on all 5 subsystems, AgentConfig, AgentResult, message_utils. Everything else depends on Agent.

#### `src/mamba_agents/agent/message_utils.py`
- **Key exports**: `model_messages_to_dicts()`, `dicts_to_model_messages()`
- **Core logic**: Bridges pydantic-ai's typed messages and dict-based format using `type(msg).__name__` string matching — the most fragile coupling in the codebase.
- **Connections**: Called by Agent core during every run cycle. ContextManager consumes the dict output.

#### `src/mamba_agents/agent/messages.py`
- **Key exports**: `MessageQuery`, `MessageStats`, `ToolCallInfo`, `Turn`
- **Core logic**: `filter()` with AND-logic, `stats()` computes analytics, `timeline()` (530 lines) groups messages into turns with tool loop tracking, `export()` to 4 formats.
- **Connections**: Created by `Agent.messages` property. Delegates to display module for printing.

#### `src/mamba_agents/context/compaction/base.py`
- **Key exports**: `CompactionStrategy` ABC, `CompactionResult`
- **Core logic**: Template Method — `compact()` handles invariant skeleton, delegates to abstract `_do_compact()`. 5 concrete strategies.
- **Connections**: Created by ContextManager via string-to-class factory map.

#### `src/mamba_agents/workflows/react/workflow.py`
- **Key exports**: `ReActWorkflow`, `ReActConfig`, `ReActState`, `ReActHooks`
- **Core logic**: Implements Thought -> Action -> Observation loop. Registers `final_answer` tool on agent. Auto-compacts context mid-workflow.
- **Connections**: Takes Agent as constructor input; orchestrates it through multi-step execution.

---

## Patterns & Conventions

### Design Patterns

| Pattern | Where Used | Purpose |
|---------|-----------|---------|
| **Facade** | `Agent` class | Simplifies 5+ subsystems behind unified API |
| **Template Method** | `CompactionStrategy.compact()`, `Workflow.run()` | Invariant skeleton with abstract hooks |
| **Strategy** | 5 compaction strategies, 3 display renderers | Pluggable algorithms selected by config string |
| **Factory** | `create_retry_decorator()`, `MCPClientManager._create_server()` | Runtime object creation from config |
| **Circuit Breaker** | `errors/circuit_breaker.py` | CLOSED/OPEN/HALF_OPEN resilience (standalone, not yet integrated) |
| **ABC** | `ModelBackend`, `CompactionStrategy`, `Workflow`, `MessageRenderer` | Extension point contracts |

### Code Conventions

- **Pydantic BaseModel** for all configuration; **@dataclass** for all output/state types
- **Async-first** with `run_sync()` wrappers using `asyncio.run()`
- **SecretStr** for API keys — never logged, must call `.get_secret_value()`
- **Google-style docstrings** with Args/Returns/Raises on all public APIs
- **Type annotations** on all public APIs; `TYPE_CHECKING` to avoid circular imports
- **ruff** formatting at 100-char line length
- **Lazy initialization** for PromptManager and Jinja2 Environment
- Python 3.12 generics: `Agent[DepsT, OutputT]`, `Workflow[DepsT, OutputT, StateT]`

### Naming Conventions

- **Functions/Methods**: `snake_case`
- **Classes**: `PascalCase` with suffixes: `*Config`, `*Settings`, `*Result`, `*Error`, `*Strategy`
- **Private members**: `_leading_underscore`
- **Internal modules**: `_internal/`
- **Constants**: `UPPER_SNAKE_CASE`
- **Test classes**: `Test{FeatureName}` prefix
- **Test functions**: `test_{action}_{scenario}` pattern

### Project Structure

- **Source**: `src/mamba_agents/` with one directory per subsystem (14 modules)
- **Tests**: `tests/unit/` mirroring source structure, `tests/integration/` for end-to-end
- **Prompts**: `prompts/{version}/{category}/{name}.jinja2`
- **Config cascade**: constructor -> env vars -> `.env` -> `~/mamba.env` -> `config.toml` -> defaults

---

## Relationship Map

```
Agent (core.py)
  |
  |--[composes]--> ContextManager --> CompactionStrategy (5 variants)
  |                      |----------> TokenCounter
  |                      └----------> MessageHistory (internal storage)
  |
  |--[composes]--> UsageTracker
  |--[composes]--> CostEstimator
  |--[composes]--> TokenCounter
  |--[lazy init]--> PromptManager --> Jinja2 Templates
  |
  |--[delegates to]--> PydanticAgent (pydantic-ai)
  |--[converts via]--> message_utils.py (ModelMessage <-> dict)
  |--[configured by]--> AgentConfig --> AgentSettings
  |                                       |-- ModelBackendSettings --> OpenAIProvider
  |                                       |-- CompactionConfig
  |                                       |-- TokenizerConfig
  |                                       |-- PromptConfig
  |                                       |-- ErrorRecoveryConfig --> retry decorators
  |
  |--[exposes]--> MessageQuery --> Display Renderers (Rich/Plain/HTML)
  |--[wrapped by]--> AgentResult (wraps pydantic-ai RunResult)

ReActWorkflow
  |--[takes + MUTATES]--> Agent (registers final_answer tool)
  |--[extends]--> Workflow ABC (workflows/base.py)

MCPClientManager
  |--[creates]--> pydantic-ai MCP servers
  |--[passed to]--> Agent (via toolsets parameter)

Tools --> Agent (via tools parameter) --> FilesystemSecurity (optional)
```

**Data flow for `agent.run()`:**
1. Resolve message history (dicts -> ModelMessage via `dicts_to_model_messages`)
2. Delegate to `PydanticAgent.run()`
3. Post-run: record usage -> convert new messages to dicts -> store in ContextManager -> check compaction

---

## Challenges & Risks

| Challenge | Severity | Impact |
|-----------|----------|--------|
| **Message format fragility** (`message_utils.py`) | High | Uses `type(msg).__name__` string matching instead of `isinstance`. Any pydantic-ai class rename silently produces empty results rather than raising errors. |
| **Duplicate TokenCounter in CompactionStrategy** | Medium | `_count_tokens()` creates fresh `TokenCounter()` with defaults, potentially using different encoding than Agent's configured counter. Compaction decisions may be inconsistent. |
| **ReActWorkflow mutates injected Agent** | Medium | Permanently registers `final_answer` tool with no cleanup mechanism. Reusing the Agent or creating multiple workflows accumulates tools. |
| **pydantic-ai pre-1.0 version sensitivity** | Medium | `>=0.0.49` pin with no ceiling. Already handled one API migration (`input_tokens` vs `request_tokens`). More breaking changes likely before 1.0. |
| **Sync wrappers vs. event loops** | Medium | `run_sync()` uses `asyncio.run()`, which fails inside existing async contexts (Jupyter, async web frameworks). |
| **Observability module untested** | Low | 274 lines with zero coverage. `SensitiveDataFilter` regex-based redaction is security-relevant but unverified. |
| **Tools have low test coverage** | Low | glob (17%), grep (20%), bash (32%) — security-relevant tools with potential edge cases untested. |
| **Cost rates stale/simplified** | Low | Single rate per model (no input/output split). Missing GPT-4o, Claude 3.5 Sonnet, and other current models. |
| **Circuit breaker not integrated** | Low | Fully implemented but not wired into Agent or any execution path. Standalone utility only. |

---

## Recommendations

1. **Harden message_utils.py**: Replace `type(msg).__name__` string matching with `isinstance` checks against imported pydantic-ai classes. Add a `TypeError` fallback for unrecognized message types. Highest-priority defensive change.

2. **Inject TokenCounter into CompactionStrategy**: Pass the Agent's configured counter through `ContextManager._create_strategy()` to eliminate the duplicate counter inconsistency.

3. **Add ReActWorkflow cleanup**: Implement `close()`/`cleanup()` that removes the `final_answer` tool from the Agent, or create a defensive copy of the Agent's tool list to avoid mutation.

4. **Test the observability module**: The `SensitiveDataFilter` redaction is security-relevant. Add tests for redaction patterns, log formatting, and `setup_logging()` configuration.

5. **Increase tool test coverage**: Especially `run_bash` (32%) which executes arbitrary shell commands. Test timeout behavior, error handling, and edge cases.

6. **Update cost rate tables**: Add current models (GPT-4o, Claude 3.5 Sonnet, etc.) and consider splitting into input/output token rates to match actual provider pricing.

7. **Document event loop limitation**: Clearly document that `run_sync()` cannot be called from within an existing async event loop, or investigate alternative sync mechanisms.

---

## Test Health

| Metric | Value |
|--------|-------|
| Total test files | 38 |
| Total test cases | 1429 |
| Execution time | 2.31s |
| Coverage | 68.01% (target: 50%) |
| Python versions tested | 3.12, 3.13 |

### Coverage Highlights

**Well Tested (>90%)**: Agent core, display renderers, MCP integration, prompt management, workflows base, context management

**Coverage Gaps**: observability/ (0%), tools/glob.py (17%), tools/grep.py (20%), tools/bash.py (32%), tools/registry.py (43%)

---

## Analysis Methodology

- **Exploration agents**: 3 agents — (1) Core agent, entry points, user-facing API; (2) Configuration, infrastructure, shared utilities; (3) Built-in tools, testing, CI/CD
- **Synthesis**: Findings merged via opus-class synthesizer with critical files read in depth
- **Scope**: Full `src/mamba_agents/` source tree, `tests/`, CI/CD workflows, and project configuration
