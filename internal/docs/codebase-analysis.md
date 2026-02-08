# Codebase Analysis Report

**Analysis Context**: General codebase understanding of mamba-agents framework
**Codebase Path**: `/Users/sequenzia/dev/repos/mamba-agents`
**Date**: 2026-02-07

---

## Executive Summary

Mamba Agents is a well-architected **thin wrapper around pydantic-ai** that follows a hub-and-spoke facade design, composing 7 subsystems behind a unified `Agent` API. The framework's "batteries included but optional" philosophy is executed consistently — context tracking, token counting, and cost estimation work out of the box but can be disabled. The **highest risk** is the `>=0.0.49` dependency on pre-1.0 pydantic-ai, where string-based type matching in `message_utils.py` will silently break on upstream renames. The most impactful recommendation is to harden that conversion layer with `isinstance()` checks before pydantic-ai reaches 1.0.

---

## Architecture Overview

The codebase layers into three tiers with strict downward dependencies:

**Core Tier** — `agent/`, `config/`, `tokens/`, `context/`, `prompts/` — Foundational agent execution. The most mature and well-tested tier (>90% coverage). Handles context tracking, token counting, cost estimation, and prompt templating.

**Extension Tier** — `tools/`, `workflows/`, `mcp/`, `skills/`, `subagents/`, `errors/` — Pluggable capabilities that extend the agent. Skills and subagents are marked **experimental** with unstable APIs. MCP integration supports stdio/SSE/streamable HTTP transports.

**Infrastructure Tier** — `observability/`, `backends/`, `_internal/` — Logging with redaction, model backend abstractions, and internal utilities. The **least integrated** tier — observability has 0% test coverage and the circuit breaker isn't wired into the Agent.

The design philosophy is **"batteries included but optional"**: auto-compaction and context tracking default to enabled, but every feature can be disabled via configuration. The `Agent` class (1,145 lines) is the central hub composing `ContextManager`, `UsageTracker`, `TokenCounter`, `CostEstimator`, `PromptManager`, `SkillManager`, and `SubagentManager` behind ~30 facade methods.

The configuration system uses **pydantic-settings** with a 5-source priority chain: constructor args > env vars (`MAMBA_` prefix) > `.env` files > `config.toml` > defaults.

**Key technologies**: Python 3.12+, pydantic-ai (>=0.0.49), pydantic-settings, httpx, tiktoken, tenacity, Jinja2, Rich. Build tooling: uv, hatch-vcs, ruff, pytest.

---

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `agent/core.py` | Central Agent hub composing 7 subsystems | **Critical** |
| `config/settings.py` | Root `AgentSettings` with 5-source config loading | **High** |
| `agent/message_utils.py` | ModelMessage <-> dict conversion (fragile string matching) | **High** |
| `agent/config.py` | `AgentConfig` — per-instance execution settings | **High** |
| `context/manager.py` | Context window tracking + compaction orchestration | **High** |
| `tokens/tracker.py` | Usage tracking with subagent aggregation | **High** |
| `skills/manager.py` | SkillManager facade (loader, registry, validator, discovery, invocation) | **High** |
| `subagents/manager.py` | SubagentManager facade (spawner, delegation, loader) | **High** |
| `skills/integration.py` | Bi-directional skills <-> subagents bridge | **High** |
| `mcp/client.py` | MCPClientManager — MCP server lifecycle | **Medium** |
| `context/compaction/base.py` | CompactionStrategy ABC (5 strategies) | **Medium** |
| `workflows/base.py` | Workflow ABC — template method for orchestration | **Medium** |

### File Details

#### `agent/core.py`
- **Key exports**: `Agent`, `AgentResult`
- **Core logic**: Constructor handles 5 initialization paths for model resolution. Post-run hooks orchestrate usage recording, message tracking, and auto-compaction. Lazy initialization for skills/subagents via `@property`.
- **Connections**: Imports from config, context, tokens, prompts. Lazy imports skills, subagents. Wraps `pydantic_ai.Agent`.

#### `agent/message_utils.py`
- **Key exports**: `dicts_to_model_messages()`, `model_messages_to_dicts()`
- **Core logic**: Bidirectional conversion between pydantic-ai `ModelMessage` objects and plain dicts for serialization. Uses `type(msg).__name__` string matching.
- **Connections**: Used by `core.py` for every `run()` call and by `delegation.py` for subagent results.

#### `skills/integration.py`
- **Key exports**: `activate_with_fork()`, `detect_circular_skill_subagent()`
- **Core logic**: Bridge for fork-mode skills. Handles trust check -> cycle detection -> content prep -> subagent delegation. Uses `ThreadPoolExecutor` workaround for sync/async impedance.
- **Connections**: Called by `SkillManager.activate()`; delegates to `SubagentManager`.

#### `config/settings.py`
- **Key exports**: `AgentSettings`
- **Core logic**: Root pydantic-settings `BaseSettings` class. `settings_customise_sources()` adds TOML support. `model_dump_safe()` redacts secrets. Composes `ModelBackendSettings`, `LoggingConfig`, `ErrorRecoveryConfig`, `CompactionConfig`, `PromptConfig`, `SkillConfig`.
- **Connections**: Used by `Agent.__init__()` as single source of truth for all subsystem configs.

#### `tokens/tracker.py`
- **Key exports**: `UsageTracker`, `TokenUsage`, `UsageRecord`
- **Core logic**: Aggregate + per-subagent tracking. `record_usage()` handles pydantic-ai API migration (`input_tokens` vs `request_tokens`). `_subagent_totals` dict for subagent breakdown.
- **Connections**: Used by `Agent.run()` post-hook. Directly mutated by `SubagentManager._aggregate_usage()`.

---

## Patterns & Conventions

### Code Patterns
- **Facade Pattern** (dominant): `Agent`, `SkillManager`, `SubagentManager`, `MCPClientManager` — compose internal components behind unified APIs
- **Template Method**: `CompactionStrategy.compact()` -> abstract `_do_compact()`; `Workflow.run()` -> abstract `_execute()`
- **Strategy Pattern**: 5 compaction strategies and 3 display renderers selected by config strings
- **Progressive Disclosure**: Skills use 3-tier loading (metadata -> full body -> references) for performance
- **Pipeline Pattern**: Skill/subagent loaders: `_read_file()` -> `_split_frontmatter()` -> `_parse_yaml()` -> `_validate_*()` -> `_map_fields()`
- **Registry Pattern**: `SkillRegistry` (async-safe), `ToolRegistry` with enable/disable/grouping
- **No-Nesting Guard**: Subagents cannot spawn sub-subagents via `AgentConfig._is_subagent` flag
- **Lazy Initialization**: Skills/Subagents managers created on first `@property` access; constructor stores `_pending_*` queues

### Naming Conventions
- Python 3.12+ with snake_case throughout
- **Pydantic BaseModel** for all configuration types; **`@dataclass`** for output/data types
- Module naming: `config.py` (Pydantic models), `errors.py` (domain exceptions), `manager.py` (facades)
- YAML frontmatter: hyphenated keys mapped to Python via `_FIELD_MAP`
- Async-first with sync wrappers: `run()` + `run_sync()`, `delegate()` + `delegate_sync()`

### Project Structure
- Source code in `src/mamba_agents/` (src layout)
- One `__init__.py` per module with explicit `__all__` exports
- Top-level `__init__.py` exports 60+ symbols organized by subsystem
- Tests in `tests/unit/` mirroring source structure with `test_` prefix
- Config: `pyproject.toml` for build (hatchling + hatch-vcs), ruff, pytest

---

## Relationship Map

### Component Connections
- `Agent` -> composes -> `ContextManager`, `UsageTracker`, `TokenCounter`, `CostEstimator`, `PromptManager`
- `Agent` -> lazy-creates -> `SkillManager`, `SubagentManager`
- `SkillManager` <-> `SubagentManager` (bi-directional via post-construction setter)
- `ContextManager` -> delegates to -> `CompactionStrategy` (5 pluggable strategies)
- `SubagentManager._aggregate_usage()` -> mutates -> `UsageTracker._subagent_totals`
- `Agent.run()` -> wraps -> `PydanticAgent.run()` with pre/post hooks
- `MCPClientManager.as_toolsets()` -> creates -> `pydantic_ai.mcp.MCPServer*` instances
- `Workflow` ABC -> accepts -> `Agent` instances as inputs (independent execution layer)
- `ReActWorkflow.__init__()` -> permanently registers -> `final_answer` tool on Agent

### Data Flow for `agent.run()`
1. `ContextManager.get_messages()` -> `dicts_to_model_messages()` -> `list[ModelMessage]`
2. Delegate to `PydanticAgent.run()` with resolved history
3. Wrap result in `AgentResult`
4. Post-run: `UsageTracker.record_usage()` with pydantic-ai Usage object
5. Post-run: `model_messages_to_dicts(result.new_messages())` -> `ContextManager.add_messages()`
6. Post-run: Check `should_compact()` -> auto-compact if threshold reached

---

## Challenges & Risks

| Challenge | Severity | Impact |
|-----------|----------|--------|
| **pydantic-ai pre-1.0 dependency** | High | `>=0.0.49` pin on rapidly evolving library. String-based type matching in `message_utils.py` will silently break on type renames. `tracker.py` already has `getattr` fallback for one API migration. |
| **SubagentManager mutates parent internals** | Medium | `_aggregate_usage()` directly writes to `parent_agent.usage_tracker._subagent_totals`, coupling to UsageTracker's private state. Any refactor of UsageTracker internals breaks this. |
| **CompactionStrategy orphan TokenCounter** | Medium | `compaction/base.py` creates `TokenCounter()` with defaults on every `_count_tokens()` call. May use different tokenizer settings than Agent's configured counter. |
| **ReActWorkflow mutates injected Agent** | Medium | Permanently registers `final_answer` tool during `__init__()`. No cleanup mechanism. Agents shared across workflows accumulate tools. |
| **skills/integration.py async workaround** | Medium | `activate_with_fork()` uses `ThreadPoolExecutor` + `asyncio.run()` for sync-in-async bridging. Fragile with nested event loops; could deadlock. |
| **Observability at 0% test coverage** | Medium | 274 lines untested including security-relevant `SensitiveDataFilter` for API key redaction. |
| **Tools low test coverage** | Low | `glob.py` (17%), `grep.py` (20%), `bash.py` (32%) — user-facing utilities with thin coverage. |
| **Circuit breaker not integrated** | Low | Full CLOSED/OPEN/HALF_OPEN implementation exists but isn't wired into Agent. Risk of code rot. |

---

## Recommendations

1. **Harden `message_utils.py`**: Replace `type(msg).__name__` string matching with `isinstance()` checks. The `dicts_to_model_messages()` function already imports the actual types — apply the same pattern to `model_messages_to_dicts()`.

2. **Fix CompactionStrategy TokenCounter**: Pass the Agent's configured `TokenCounter` instance to compaction strategies instead of creating a fresh one with defaults.

3. **Add UsageTracker public API for subagent aggregation**: Replace direct `_subagent_totals` mutation with a public method like `record_subagent_usage(name, usage)`.

4. **Add observability tests**: The `SensitiveDataFilter` is security-relevant. Basic unit tests would validate that API keys and tokens are actually redacted from logs.

5. **Pin pydantic-ai upper bound**: Consider `pydantic-ai>=0.0.49,<1.0` to prevent silent breakage. Add a CI job testing against latest pydantic-ai.

6. **Add ReActWorkflow cleanup**: Implement a `cleanup()` method that removes the `final_answer` tool, or use a context manager pattern.

7. **Improve tools test coverage**: Focus on edge cases for `bash.py`, `glob.py`, `grep.py`: permission errors, timeouts, malformed patterns.

---

## Open Questions

- The `observability/` module exports tracing and OTel integration but these are not wired into the Agent execution loop. Is this intentional scaffolding for future work, or abandoned code?
- The `errors/circuit_breaker.py` implements a full CLOSED/OPEN/HALF_OPEN circuit breaker but is not integrated into the Agent. Should this be wired into retry logic or is it an independent utility?
- The `backends/` module provides `OpenAICompatibleBackend` and factory functions, but the Agent constructor directly uses `pydantic_ai.models.openai.OpenAIChatModel`. Are the backend classes redundant, or intended for standalone use?
- Skills with `execution_mode: "fork"` use a complex sync/async bridging pattern. Has this been tested under production async workloads (e.g., inside FastAPI)?

---

## Analysis Methodology

- **Exploration agents**: 3 Sonnet agents with focus areas: (1) core structure & entry points, (2) configuration & infrastructure, (3) extensions & cross-cutting concerns
- **Synthesis**: 1 Opus agent merged findings, resolved cross-explorer conflicts, produced unified analysis
- **Deep analyst**: Available on-demand for complex investigations (Opus with Bash access)
- **Peer collaboration**: Explorers shared discoveries with each other during exploration phase
- **Scope**: Full `src/mamba_agents/` source tree, `tests/` structure, configuration files
- **Excluded**: CI/CD pipeline details, release automation, documentation site
