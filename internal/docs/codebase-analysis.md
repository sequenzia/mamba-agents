# Codebase Analysis Report

**Analysis Context**: General codebase understanding
**Codebase Path**: `/Users/sequenzia/dev/repos/mamba-agents`
**Date**: 2026-02-02

---

## Executive Summary

Mamba Agents is a well-architected facade layer over pydantic-ai that adds enterprise infrastructure — configuration management, context window tracking with auto-compaction, token/cost tracking, prompt templates, MCP integration, and workflow orchestration. The most significant architectural insight is the hub-and-spoke design where `Agent` composes five independent subsystems behind a simplified API. The primary risk is tight coupling to pydantic-ai's pre-1.0 internal message format via a string-matching bridge in `message_utils.py`, which could break silently on upstream changes.

---

## Architecture Overview

The project follows a **hub-and-spoke** design. The `Agent` class acts as the central hub, internally composing `ContextManager`, `UsageTracker`, `TokenCounter`, `CostEstimator`, and `PromptManager` while exposing a simplified facade API. Each subsystem is independently usable but wired together automatically through the Agent constructor.

The dependency graph flows strictly downward: `Agent` depends on `config`, `context`, `tokens`, and `prompts`; `Workflow` depends on `Agent`; `MCP` is injected laterally via the `toolsets` parameter. No circular dependencies exist between modules. The design philosophy is "batteries included but optional" — context tracking and auto-compaction default to enabled, but every feature can be disabled or overridden.

The codebase is organized into **14 top-level modules** across **81 Python source files** and **32 test files**. Core technologies: Python 3.12+, pydantic-ai, pydantic/pydantic-settings, tiktoken, Jinja2, tenacity, httpx. Build system uses hatchling with hatch-vcs for git-tag-based versioning.

---

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `src/mamba_agents/agent/core.py` | Central Agent facade (841 lines) | High |
| `src/mamba_agents/agent/config.py` | AgentConfig execution settings | High |
| `src/mamba_agents/agent/message_utils.py` | ModelMessage <-> dict conversion bridge | High |
| `src/mamba_agents/config/settings.py` | Root AgentSettings (pydantic-settings) | High |
| `src/mamba_agents/context/manager.py` | ContextManager for message tracking | High |
| `src/mamba_agents/context/compaction/base.py` | CompactionStrategy ABC + Template Method | High |
| `src/mamba_agents/tokens/counter.py` | TokenCounter (tiktoken wrapper) | High |
| `src/mamba_agents/tokens/tracker.py` | UsageTracker for session aggregation | High |
| `src/mamba_agents/workflows/base.py` | Workflow ABC, WorkflowState, WorkflowResult | High |
| `src/mamba_agents/workflows/react/workflow.py` | ReActWorkflow implementation (448 lines) | High |

### File Details

#### `src/mamba_agents/agent/core.py`
- **Key exports**: `Agent[DepsT, OutputT]`
- **Core logic**: Composes 5 internal subsystems in constructor. Provides `run()`, `run_sync()`, `run_stream()` that delegate to pydantic-ai then perform post-run tracking (context + usage). Graceful error wrapping converts tool exceptions to `ModelRetry`.
- **Connections**: Imports from `config`, `context`, `tokens`, `prompts`. Consumed by `workflows`.

#### `src/mamba_agents/agent/message_utils.py`
- **Key exports**: `model_messages_to_dicts()`, `dicts_to_model_messages()`
- **Core logic**: Bridges pydantic-ai's typed `ModelMessage` objects and dict-based format used by `ContextManager`. Uses type-name string matching rather than isinstance checks.
- **Connections**: Critical bridge between Agent and ContextManager. Fragile dependency on pydantic-ai internals.

#### `src/mamba_agents/config/settings.py`
- **Key exports**: `AgentSettings`
- **Core logic**: Root configuration aggregating `ModelBackendSettings`, `LoggingConfig`, `ErrorRecoveryConfig`, `CompactionConfig`, `TokenizerConfig`, `PromptConfig`. Multi-source loading with `MAMBA_` prefix.
- **Connections**: Used by Agent constructor; nested configs flow to all subsystems.

#### `src/mamba_agents/workflows/react/workflow.py`
- **Key exports**: `ReActWorkflow`, `ReActConfig`, `ReActState`, `ReActHooks`
- **Core logic**: Implements Thought -> Action -> Observation loop. Registers `final_answer` tool on agent. Auto-compacts context mid-workflow.
- **Connections**: Takes Agent as constructor input; orchestrates it through multi-step execution.

---

## Patterns & Conventions

### Code Patterns

| Pattern | Where Used | Purpose |
|---------|-----------|---------|
| **Facade** | `Agent` class | Simplifies 5+ subsystems behind unified API |
| **Template Method** | `CompactionStrategy.compact()`, `Workflow.run()` | Invariant skeleton with abstract hooks |
| **Strategy** | 5 compaction strategies | Pluggable algorithms selected by config |
| **Factory** | `create_retry_decorator()`, `MCPClientManager._create_server()` | Runtime object creation |
| **Circuit Breaker** | `errors/circuit_breaker.py` | CLOSED/OPEN/HALF_OPEN resilience |
| **ABC** | `ModelBackend`, `CompactionStrategy`, `Workflow` | Extension point contracts |

### Naming Conventions

- **Functions/Methods**: `snake_case`
- **Classes**: `PascalCase` with suffixes: `*Config`, `*Settings`, `*Result`, `*Error`
- **Private members**: `_leading_underscore`
- **Internal modules**: `_internal/`
- **Constants**: `UPPER_SNAKE_CASE`

### Project Structure

- **Source**: `src/mamba_agents/` with one directory per subsystem (14 modules)
- **Tests**: `tests/unit/` mirroring source structure, `tests/integration/` for end-to-end
- **Prompts**: `prompts/{version}/{category}/{name}.jinja2`
- **Config cascade**: constructor -> env vars -> `.env` -> `config.toml` -> defaults

### Code Style

- Async-first with `run_sync()` wrappers throughout
- Google-style docstrings on all public APIs
- Python 3.12 generics (`Agent[DepsT, OutputT]`)
- Full type annotations; `TYPE_CHECKING` to avoid circular imports
- `SecretStr` for all sensitive data; never logged

---

## Relationship Map

```
User Code
    |
    v
Agent (core.py) ------> pydantic-ai Agent (delegated execution)
    |                         |
    |-- AgentSettings         |-- runs LLM calls
    |     |-- ModelBackendSettings --> OpenAIProvider
    |     |-- CompactionConfig ------> ContextManager
    |     |-- TokenizerConfig -------> TokenCounter
    |     |-- PromptConfig ----------> PromptManager
    |     |-- ErrorRecoveryConfig ---> retry decorators
    |
    |-- TokenCounter (tiktoken) <---- also used by CompactionStrategy
    |-- UsageTracker <-- records Usage after each run()
    |-- CostEstimator <-- reads from UsageTracker
    |-- ContextManager
    |     |-- MessageHistory (storage)
    |     |-- CompactionStrategy (5 interchangeable)
    |     |-- message_utils.py (dict <-> ModelMessage bridge)
    |
    |-- PromptManager (lazy-loaded)
          |-- PromptTemplate (Jinja2 wrapper)
          |-- TemplateConfig (name/version/variables)

ReActWorkflow
    |-- Agent (injected, modified with final_answer tool)
    |-- calls Agent.run() in Thought->Action->Observation loop

MCPClientManager
    |-- MCPServerConfig[] -> creates MCPServer* instances
    |-- output passed to Agent(toolsets=...)
```

---

## Challenges & Risks

| Challenge | Severity | Impact |
|-----------|----------|--------|
| Message format bridge fragility | Medium | `message_utils.py` uses string-matching on pydantic-ai type names. Upstream message type changes could produce silently incorrect dict conversions rather than failing loudly. |
| ReActWorkflow mutates injected Agent | Medium | `__init__()` permanently registers `final_answer` tool on the agent. Reusing the agent elsewhere retains this tool unexpectedly. No cleanup mechanism exists. |
| pydantic-ai version coupling | Medium | `>=0.0.49` pins to a pre-1.0 library actively changing its API. `tracker.py` already handles an `input_tokens`/`request_tokens` migration. |
| Sync wrappers use `asyncio.run()` | Medium | `run_sync()` fails inside existing event loops (Jupyter, async web frameworks). |
| LLM-dependent compaction strategies | Medium | `summarize_older` and `importance_scoring` need LLM calls but are instantiated without a model reference. May be incomplete. |
| Test coverage target is 50% | Medium | Low for infrastructure code. Error handling, backends, and several compaction strategies appear to lack dedicated tests. |
| Cost estimation uses uniform token rate | Low | Same rate applied to prompt and completion tokens; most providers charge 3-5x more for output tokens. |
| Duplicate TokenCounter instantiation | Low | `CompactionStrategy._count_tokens()` creates a fresh counter with defaults, potentially inconsistent with Agent's configured counter. |

---

## Recommendations

1. **Add integration tests for message round-tripping**: Create tests that convert pydantic-ai `ModelMessage` objects to dicts and back, asserting structural fidelity. This catches pydantic-ai format changes early and hardens the most fragile bridge in the codebase.

2. **Differentiate input/output token rates in CostEstimator**: Change `CostBreakdown` to use separate prompt and completion rates. Most providers charge significantly different rates, making current estimates inaccurate for cloud models.

3. **Make ReActWorkflow's tool registration reversible**: Either document the permanent agent mutation clearly, create an internal copy of the agent, or provide a cleanup/unregister mechanism to avoid surprising side effects.

4. **Inject TokenCounter into CompactionStrategy**: Pass the same `TokenCounter` instance that `ContextManager` uses to ensure consistent token counting across the compaction pipeline.

5. **Add a pydantic-ai compatibility test matrix**: Given tight coupling to a pre-1.0 dependency, testing against multiple pydantic-ai versions in CI would prevent surprise breakages during upstream evolution.

---

## Analysis Methodology

- **Exploration agents**: 2 agents — (1) Application structure, entry points, core logic; (2) Configuration, infrastructure, testing
- **Synthesis**: Findings merged via opus-level synthesizer with deep file reads on critical components
- **Scope**: Full source tree analyzed. Excludes runtime behavior analysis and performance profiling.
