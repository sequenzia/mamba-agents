# Codebase Analysis Report

> **Generated:** 2026-01-25
> **Scope:** /Users/sequenzia/dev/repos/mamba-agents
> **Version:** 0.1.x (Alpha)

---

## Executive Summary

Mamba Agents is a Python framework designed to simplify building AI agents with Large Language Model (LLM) capabilities. It provides a thin but powerful wrapper around the `pydantic-ai` library, adding enterprise-grade infrastructure that developers would otherwise need to build themselves: configuration management, context window management with automatic compaction, token usage tracking and cost estimation, Model Context Protocol (MCP) integration, and workflow orchestration.

The architecture follows a **Modular Monolith** pattern with clear layered boundaries. The central `Agent` class acts as a facade, presenting a simple API while coordinating five internal subsystems (context management, token tracking, prompt templates, configuration, and error handling). This design achieves an excellent balance between ease of use for simple cases and extensibility for advanced scenarios.

Overall, the codebase demonstrates strong software engineering practices: comprehensive type annotations, consistent use of Pydantic models for validation, clear separation of concerns, and thoughtful API design. The framework is well-positioned for production use, though some areas (notably test coverage and workflow implementations) could benefit from additional attention.

---

## Project Overview

| Attribute | Value |
|-----------|-------|
| **Project Name** | Mamba Agents |
| **Primary Language** | Python 3.12+ |
| **Core Framework** | pydantic-ai |
| **Repository Type** | Library/Framework |
| **License** | MIT |
| **Lines of Code** | ~10,418 |
| **Python Files** | ~80 |

### Purpose

Mamba Agents fills the gap between raw LLM API access and full-featured agent frameworks. While `pydantic-ai` provides excellent primitives for building agents (type-safe tool calling, structured outputs, model abstraction), it deliberately remains minimal. Mamba Agents adds the operational infrastructure needed for production deployments:

- **Configuration Management** - Multi-source settings with clear precedence rules
- **Context Window Management** - Automatic tracking and compaction to prevent token overflow
- **Token Tracking & Cost Estimation** - Usage monitoring and cost projections
- **MCP Integration** - Connect to external tool servers via the Model Context Protocol
- **Workflow Orchestration** - Multi-step reasoning patterns like ReAct

---

## Architecture

### Architecture Style

**Primary Pattern:** Modular Monolith with Layered Architecture

The codebase is organized as a modular monolith where each top-level directory under `src/mamba_agents/` represents a distinct module with its own responsibilities. Modules communicate through well-defined interfaces, making it possible to use components independently or replace them with custom implementations.

The layered architecture manifests in how the `Agent` class serves as the primary entry point, delegating to specialized subsystems for specific functionality. This approach keeps the core simple while allowing sophisticated behavior through composition.

**Secondary Patterns:**
- **Facade Pattern** - The `Agent` class wraps `pydantic-ai` plus five internal subsystems
- **Strategy Pattern** - Five interchangeable compaction algorithms
- **Template Method** - Abstract base classes define skeleton algorithms (`Workflow._execute()`, `CompactionStrategy.compact()`)
- **Observer Pattern** - `WorkflowHooks` provides eight callback points for monitoring
- **Factory Pattern** - Model backend creators (`create_ollama_backend()`, etc.)
- **Registry Pattern** - `ToolRegistry` for dynamic tool management
- **Circuit Breaker** - Error recovery with configurable thresholds

### System Diagram

```
+-----------------------------------------------------------------------------------+
|                              Mamba Agents Framework                               |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|    +-------------------------------------------------------------------------+   |
|    |                         Agent (Facade Layer)                            |   |
|    |                                                                         |   |
|    |  +-----------+  +-----------+  +-----------+  +-----------+            |   |
|    |  |  run()    |  | run_sync()|  | stream()  |  | tools     |            |   |
|    |  +-----------+  +-----------+  +-----------+  +-----------+            |   |
|    +-------------------------------------------------------------------------+   |
|                |                    |                    |                       |
|                v                    v                    v                       |
|    +-------------------+  +------------------+  +------------------+             |
|    |  Context Manager  |  |  Usage Tracker   |  |  Prompt Manager  |             |
|    |  +--------------+ |  | +--------------+ |  | +--------------+ |             |
|    |  | Messages     | |  | | Token Count  | |  | | Templates    | |             |
|    |  | Compaction   | |  | | Cost Estimate| |  | | Jinja2       | |             |
|    |  +--------------+ |  | +--------------+ |  | +--------------+ |             |
|    +-------------------+  +------------------+  +------------------+             |
|                |                                                                 |
|                v                                                                 |
|    +-------------------------------------------------------------------------+   |
|    |                      pydantic-ai Agent (Core)                           |   |
|    +-------------------------------------------------------------------------+   |
|                |                    |                    |                       |
|                v                    v                    v                       |
|    +-------------------+  +------------------+  +------------------+             |
|    |   LLM Backends    |  |   MCP Servers    |  |   Built-in Tools |             |
|    |  +-------------+  |  | +-------------+  |  | +-------------+  |             |
|    |  | OpenAI      |  |  | | stdio       |  |  | | read_file   |  |             |
|    |  | Ollama      |  |  | | SSE         |  |  | | write_file  |  |             |
|    |  | vLLM        |  |  | | HTTP        |  |  | | run_bash    |  |             |
|    |  | LM Studio   |  |  | +-------------+  |  | | glob/grep   |  |             |
|    |  +-------------+  |  +------------------+  | +-------------+  |             |
|    +-------------------+                        +------------------+             |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Workflow Architecture

```
+-----------------------------------------------------------------------------------+
|                            Workflow Orchestration                                 |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|    +-------------------------------------------------------------------------+   |
|    |                      Workflow (Abstract Base)                           |   |
|    |                                                                         |   |
|    |  +-------------------+  +-------------------+  +-------------------+    |   |
|    |  | WorkflowConfig    |  | WorkflowState     |  | WorkflowHooks     |    |   |
|    |  | - max_steps       |  | - steps[]         |  | - on_start        |    |   |
|    |  | - max_iterations  |  | - iteration       |  | - on_complete     |    |   |
|    |  | - timeout         |  | - context{}       |  | - on_step_*       |    |   |
|    |  +-------------------+  +-------------------+  +-------------------+    |   |
|    +-------------------------------------------------------------------------+   |
|                                      |                                           |
|                                      v                                           |
|    +-------------------------------------------------------------------------+   |
|    |                      ReActWorkflow (Implementation)                     |   |
|    |                                                                         |   |
|    |      +------------+     +------------+     +-------------+              |   |
|    |      |  Thought   | --> |   Action   | --> | Observation | --+         |   |
|    |      +------------+     +------------+     +-------------+   |         |   |
|    |           ^                                                  |         |   |
|    |           +--------------------------------------------------+         |   |
|    |                          (loop until final_answer)                     |   |
|    +-------------------------------------------------------------------------+   |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Key Modules

| Module | Purpose | Location |
|--------|---------|----------|
| Agent | Core wrapper around pydantic-ai Agent | `src/mamba_agents/agent/` |
| Config | Settings management with pydantic-settings | `src/mamba_agents/config/` |
| Context | Context window tracking and compaction | `src/mamba_agents/context/` |
| Tokens | Token counting, usage tracking, cost estimation | `src/mamba_agents/tokens/` |
| Workflows | Multi-step agent orchestration patterns | `src/mamba_agents/workflows/` |
| MCP | Model Context Protocol integration | `src/mamba_agents/mcp/` |
| Prompts | Jinja2 template management | `src/mamba_agents/prompts/` |
| Tools | Built-in filesystem, bash, search tools | `src/mamba_agents/tools/` |
| Backends | OpenAI-compatible model adapters | `src/mamba_agents/backends/` |
| Errors | Error hierarchy, retry logic, circuit breaker | `src/mamba_agents/errors/` |

---

#### Agent Module

**Purpose:** Provides the primary interface for interacting with LLMs. Wraps `pydantic-ai.Agent` and coordinates internal subsystems.

**Key Components:**
- `Agent` - Main class with `run()`, `run_sync()`, and `stream()` methods
- `AgentConfig` - Execution configuration (context tracking, auto-compaction)
- `AgentResult` - Typed result wrapper with usage information
- `message_utils` - Serialization/deserialization of pydantic-ai messages

**Relationships:** Depends on Context, Tokens, Prompts, and Config modules. Used by Workflows module.

---

#### Config Module

**Purpose:** Centralized configuration management with multi-source loading.

**Key Components:**
- `AgentSettings` - Root configuration class using pydantic-settings
- Model backend configuration (base URL, API key, model selection)
- Logging, retry, and subsystem-specific settings

**Configuration Precedence:**
1. Constructor arguments (highest priority)
2. Environment variables (`MAMBA_*` prefix)
3. `.env` file (project-specific)
4. `config.toml` / `config.yaml`
5. `~/mamba.env` (user-wide defaults)
6. Default values (lowest priority)

---

#### Context Module

**Purpose:** Tracks conversation history and prevents token overflow through intelligent compaction.

**Key Components:**
- `ContextManager` - Message history tracking
- `CompactionConfig` - Strategy and threshold configuration
- Five compaction strategies:
  - `sliding_window` - Keep most recent N messages
  - `summarize_older` - LLM-based summarization of older context
  - `selective_pruning` - Remove less important messages
  - `importance_scoring` - Rank and retain by importance
  - `hybrid` - Combined approach

---

#### Tokens Module

**Purpose:** Accurate token counting and cost estimation for LLM usage.

**Key Components:**
- `TokenCounter` - Count tokens using tiktoken
- `UsageTracker` - Track usage across runs
- `CostEstimator` - Calculate costs based on model pricing
- `TokenizerConfig` - Tokenizer configuration

---

#### Workflows Module

**Purpose:** Orchestrate multi-step agent execution with monitoring and control.

**Key Components:**
- `Workflow` - Abstract base class for workflow patterns
- `WorkflowConfig` - Execution limits (steps, iterations, timeout)
- `WorkflowState` - Tracks execution progress
- `WorkflowHooks` - Eight callback points for observability
- `ReActWorkflow` - Built-in Thought-Action-Observation loop

---

#### MCP Module

**Purpose:** Connect to external tool servers via Model Context Protocol.

**Key Components:**
- `MCPClientManager` - Manage multiple MCP server connections
- `MCPServerConfig` - Server configuration (transport, auth, timeouts)
- `MCPAuthConfig` - API key handling with env var support
- File loader for `.mcp.json` files (Claude Desktop compatible)

**Supported Transports:**
- `stdio` - Subprocess communication
- `sse` - Server-Sent Events over HTTP
- `http` - Streamable HTTP

---

## Technology Stack

### Languages & Frameworks

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Primary language |
| pydantic-ai | >=0.0.49 | Core agent framework |
| pydantic | >=2.0 | Data validation |
| pydantic-settings | >=2.0 | Configuration management |

### Dependencies

#### Production Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic-ai` | Core agent framework with tool calling and structured outputs |
| `pydantic` | Data validation and serialization |
| `pydantic-settings` | Environment-aware configuration |
| `httpx` | Async HTTP client for API calls |
| `tenacity` | Retry logic with exponential backoff |
| `tiktoken` | OpenAI-compatible token counting |
| `python-dotenv` | Environment file loading |
| `pyyaml` | YAML configuration file support |
| `jinja2` | Template rendering for prompts |

#### Development Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-asyncio` | Async test support |
| `pytest-cov` | Coverage reporting |
| `respx` | Mock HTTP requests |
| `dirty-equals` | Flexible test assertions |
| `ruff` | Linting and formatting |

#### Optional Dependencies

| Package | Purpose |
|---------|---------|
| `opentelemetry-api` | Distributed tracing (optional) |
| `opentelemetry-sdk` | Tracing implementation (optional) |

### Build & Tooling

| Tool | Purpose |
|------|---------|
| `uv` | Fast Python package manager |
| `hatchling` | Build backend |
| `hatch-vcs` | Git-tag based versioning |
| `ruff` | Linting and code formatting |
| `GitHub Actions` | CI/CD pipelines |

---

## Code Organization

### Directory Structure

```
mamba-agents/
├── src/
│   └── mamba_agents/
│       ├── __init__.py          # Public API exports
│       ├── _version.py          # Auto-generated version (gitignored)
│       ├── agent/               # Core Agent wrapper
│       │   ├── __init__.py
│       │   ├── core.py          # Agent class implementation
│       │   ├── config.py        # AgentConfig model
│       │   ├── result.py        # AgentResult wrapper
│       │   └── message_utils.py # Message serialization
│       ├── config/              # Configuration system
│       │   ├── __init__.py
│       │   └── settings.py      # AgentSettings (root config)
│       ├── context/             # Context management
│       │   ├── __init__.py
│       │   ├── manager.py       # ContextManager
│       │   ├── config.py        # CompactionConfig
│       │   └── compaction/      # Compaction strategies
│       ├── tokens/              # Token tracking
│       │   ├── __init__.py
│       │   ├── counter.py       # TokenCounter
│       │   ├── tracker.py       # UsageTracker
│       │   └── cost.py          # CostEstimator
│       ├── prompts/             # Prompt templates
│       │   ├── __init__.py
│       │   ├── manager.py       # PromptManager
│       │   ├── template.py      # PromptTemplate
│       │   └── config.py        # PromptConfig, TemplateConfig
│       ├── workflows/           # Workflow orchestration
│       │   ├── __init__.py
│       │   ├── base.py          # Workflow ABC
│       │   ├── config.py        # WorkflowConfig
│       │   └── react.py         # ReActWorkflow
│       ├── mcp/                 # MCP integration
│       │   ├── __init__.py
│       │   ├── client.py        # MCPClientManager
│       │   ├── config.py        # MCPServerConfig
│       │   ├── auth.py          # MCPAuthConfig
│       │   ├── env.py           # Environment resolution
│       │   ├── loader.py        # .mcp.json file loader
│       │   └── errors.py        # MCP-specific errors
│       ├── tools/               # Built-in tools
│       │   ├── __init__.py
│       │   ├── filesystem.py    # File operations
│       │   ├── bash.py          # Shell command execution
│       │   ├── search.py        # glob and grep
│       │   └── registry.py      # ToolRegistry
│       ├── backends/            # Model backends
│       │   ├── __init__.py
│       │   └── openai_compat.py # OpenAI-compatible adapters
│       ├── errors/              # Error handling
│       │   ├── __init__.py
│       │   └── recovery.py      # Retry and circuit breaker
│       ├── observability/       # Logging and tracing
│       │   └── __init__.py
│       └── _internal/           # Internal utilities
│           └── __init__.py
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
├── examples/                    # Example scripts
├── docs/                        # Documentation source
├── internal/                    # Internal tools and reports
├── pyproject.toml               # Package metadata and config
├── CHANGELOG.md                 # Release history
├── CLAUDE.md                    # AI assistant instructions
└── README.md                    # Project overview
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Files | snake_case | `context_manager.py` |
| Classes | PascalCase | `AgentConfig` |
| Functions | snake_case | `run_bash()` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT` |
| Type Variables | PascalCase with suffix | `DepsT`, `OutputT` |
| Private | Leading underscore | `_internal/`, `_execute()` |

### Code Patterns

The codebase consistently uses these patterns:

1. **Pydantic Models for Configuration**
   - Where: All config classes (`AgentConfig`, `CompactionConfig`, `WorkflowConfig`)
   - How: Immutable models with validation, defaults, and clear field descriptions

2. **Async-First with Sync Wrappers**
   - Where: `Agent.run()` / `Agent.run_sync()`, `Workflow.run()` / `Workflow.run_sync()`
   - How: Core logic is async; sync methods create event loops for convenience

3. **Generic Type Parameters**
   - Where: `Agent[DepsT, OutputT]`, `Workflow[StateT]`
   - How: Python 3.12+ generic syntax for type-safe dependencies and outputs

4. **SecretStr for Sensitive Data**
   - Where: API keys in configuration
   - How: Pydantic's `SecretStr` prevents accidental logging of secrets

5. **Factory Functions for Backends**
   - Where: `backends/` module
   - How: `create_ollama_backend()`, `create_vllm_backend()` simplify setup

---

## Entry Points

| Entry Point | Type | Location | Purpose |
|-------------|------|----------|---------|
| `Agent.run()` | Async Method | `src/mamba_agents/agent/core.py` | Primary async entry point |
| `Agent.run_sync()` | Sync Method | `src/mamba_agents/agent/core.py` | Synchronous convenience wrapper |
| `Agent.stream()` | Async Method | `src/mamba_agents/agent/core.py` | Streaming response generation |
| `Workflow.run()` | Async Method | `src/mamba_agents/workflows/base.py` | Multi-step workflow execution |
| `ReActWorkflow.run()` | Async Method | `src/mamba_agents/workflows/react.py` | ReAct reasoning loop |

### Primary Entry Point

The main way users interact with Mamba Agents is through the `Agent` class:

```python
from mamba_agents import Agent

# Simple usage
agent = Agent("openai:gpt-4o")
result = agent.run_sync("What is the capital of France?")
print(result.output)

# With tools
from mamba_agents.tools import read_file, run_bash
agent = Agent("openai:gpt-4o", tools=[read_file, run_bash])

# With configuration
from mamba_agents import AgentSettings
settings = AgentSettings()  # Loads from env, .env, config files
agent = Agent(settings=settings)
```

---

## Data Flow

```
                                    Configuration
                                         |
                                         v
+--------+     +-----------+     +---------------+     +-------------+
| User   | --> |  Agent    | --> | pydantic-ai   | --> | LLM Backend |
| Prompt |     |  Facade   |     | Agent         |     | (API Call)  |
+--------+     +-----------+     +---------------+     +-------------+
                    |                   |                     |
                    v                   v                     v
              +-----------+       +-----------+         +-----------+
              | Context   |       | Tools     |         | Response  |
              | Manager   |       | (MCP/     |         | Stream    |
              |           |       |  Built-in)|         |           |
              +-----------+       +-----------+         +-----------+
                    |                                        |
                    v                                        v
              +-----------+                            +-----------+
              | Usage     |                            | Agent     |
              | Tracker   |                            | Result    |
              +-----------+                            +-----------+
```

### Request Lifecycle

1. **Entry:** User calls `agent.run(prompt)` or `agent.run_sync(prompt)`

2. **Configuration:** Settings are resolved from multiple sources with precedence:
   - Constructor args > env vars > .env > config files > defaults

3. **Context Preparation:**
   - Message history is retrieved from `ContextManager` (if tracking enabled)
   - System prompt is rendered from template (if using `TemplateConfig`)

4. **Execution:**
   - Prompt and history passed to wrapped `pydantic_ai.Agent`
   - LLM generates response, potentially calling tools
   - Tool results are processed and fed back to LLM

5. **Post-Processing:**
   - Response messages added to `ContextManager`
   - Token usage recorded in `UsageTracker`
   - Auto-compaction triggered if threshold reached

6. **Response:** `AgentResult` returned with output, usage, and metadata

---

## External Integrations

| Integration | Type | Purpose | Configuration |
|-------------|------|---------|---------------|
| OpenAI API | LLM Backend | Default LLM provider | `OPENAI_API_KEY` env var |
| Ollama | LLM Backend | Local LLM serving | `create_ollama_backend()` |
| vLLM | LLM Backend | High-performance local serving | `create_vllm_backend()` |
| LM Studio | LLM Backend | Local model management | `create_lmstudio_backend()` |
| MCP Servers | Tool Protocol | External tool integration | `.mcp.json` or `MCPServerConfig` |
| OpenTelemetry | Observability | Distributed tracing | Optional `[otel]` dependency |

### OpenAI API

The default backend uses OpenAI's API. Configuration is straightforward:

```python
# Via environment variable
export OPENAI_API_KEY=sk-...

# Or via settings
from mamba_agents import AgentSettings
settings = AgentSettings(
    model_backend={"api_key": "sk-...", "model": "gpt-4o"}
)
```

### Local LLM Backends

For local deployment, use the factory functions:

```python
from mamba_agents.backends import create_ollama_backend

model = create_ollama_backend(model="llama3.2")
agent = Agent(model)
```

### MCP Server Integration

Connect to external tool servers:

```python
from mamba_agents.mcp import MCPClientManager

# From .mcp.json file
manager = MCPClientManager.from_mcp_json(".mcp.json")

# Or programmatic configuration
manager = MCPClientManager()
manager.add_server(MCPServerConfig(
    name="filesystem",
    transport="stdio",
    command="uvx",
    args=["mcp-server-filesystem", "/path/to/workspace"]
))

agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
```

---

## Testing

### Test Framework

- **Unit Testing:** pytest with pytest-asyncio
- **Integration Testing:** pytest with respx for HTTP mocking
- **Coverage:** pytest-cov with 50% threshold (target: 90%)

### Test Organization

```
tests/
├── conftest.py           # Shared fixtures (TestModel, tmp_sandbox)
├── unit/                 # Unit tests
│   ├── test_config.py
│   ├── test_agent.py
│   ├── test_context.py
│   ├── test_tokens.py
│   └── ...
└── integration/          # Integration tests
    └── ...
```

### Key Testing Patterns

```python
# Use TestModel for deterministic LLM testing
from pydantic_ai.models.test import TestModel

# Block real model requests (set in conftest.py)
from pydantic_ai import models
models.ALLOW_MODEL_REQUESTS = False

# Use respx for HTTP mocking
import respx

# Use tmp_sandbox fixture for filesystem tests
def test_file_ops(tmp_sandbox: Path):
    ...
```

### Coverage Areas

| Area | Coverage | Notes |
|------|----------|-------|
| Agent Core | Good | Core functionality well-tested |
| Configuration | Good | Multi-source loading tested |
| Context Management | Partial | Basic compaction tested |
| Token Tracking | Good | Counter and tracker tested |
| Workflows | Partial | ReAct has basic coverage |
| MCP Integration | Partial | Config loading tested, connections mocked |
| Tools | Good | Built-in tools have coverage |

---

## Recommendations

### Strengths

These aspects of the codebase are well-executed:

1. **Clean Facade Pattern**

   The `Agent` class provides a simple, intuitive API while hiding the complexity of five internal subsystems. New users can start with `Agent("gpt-4o").run_sync("Hello")` and gradually adopt advanced features as needed.

2. **Excellent Configuration System**

   The six-level configuration precedence (constructor > env > .env > config files > defaults) follows the principle of least surprise. The `MAMBA_` prefix and nested `__` syntax are consistent and predictable.

3. **Extensible Architecture**

   Clear patterns for extension exist throughout: custom compaction strategies implement `CompactionStrategy`, new workflows extend `Workflow`, custom backends follow the model interface. The registry and factory patterns make extension points discoverable.

4. **Type Safety**

   Generic type parameters (`Agent[DepsT, OutputT]`), comprehensive Pydantic models, and consistent type annotations enable excellent IDE support and catch errors early. The codebase fully embraces Python 3.12+ type features.

5. **Security-Conscious Design**

   API keys use `SecretStr` to prevent accidental logging. The filesystem tools include path traversal protection. MCP authentication supports both direct keys and environment variable references.

6. **Modern Python Practices**

   The project uses Python 3.12+, async-first design, `uv` for package management, `ruff` for linting, and git-tag versioning. These choices reduce friction and align with current best practices.

### Areas for Improvement

These areas could benefit from attention:

1. **Test Coverage Gap**

   - **Issue:** Current threshold is 50%, but the documented target is 90%
   - **Impact:** Reduced confidence in refactoring; edge cases may be untested
   - **Suggestion:** Prioritize coverage for context compaction strategies and workflow edge cases. Add integration tests for MCP server connections.

2. **Limited Workflow Implementations**

   - **Issue:** Only ReAct workflow is built-in
   - **Impact:** Users needing Plan-Execute, Reflection, or other patterns must build from scratch
   - **Suggestion:** Add at least one additional workflow (e.g., Plan-Execute) to demonstrate the extension pattern and provide more out-of-box value.

3. **No Persistent Storage**

   - **Issue:** Context and usage history exist only in memory
   - **Impact:** Long-running conversations are lost on restart; no audit trail
   - **Suggestion:** Add optional persistence layer with pluggable backends (SQLite, Redis, filesystem). Consider event sourcing for full replay capability.

4. **OpenTelemetry Integration Depth**

   - **Issue:** OTel is an optional dependency but not deeply integrated
   - **Impact:** Production observability requires custom instrumentation
   - **Suggestion:** Add span creation around key operations (LLM calls, tool execution, compaction). Provide correlation ID propagation through workflows.

5. **Sync Wrapper Overhead**

   - **Issue:** `run_sync()` creates a new event loop per call
   - **Impact:** Performance overhead in high-frequency sync usage; potential issues with nested event loops
   - **Suggestion:** Document the async-first design clearly. Consider using `anyio` for better event loop handling in sync contexts.

### Suggested Next Steps

For developers new to this codebase:

1. **Start with the Agent class** (`src/mamba_agents/agent/core.py`) - understand how it wraps pydantic-ai and coordinates subsystems

2. **Explore the examples directory** - runnable scripts demonstrate common patterns and configuration options

3. **Run the tests** (`uv run pytest`) - see how components are tested and what fixtures are available

4. **Read the configuration system** (`src/mamba_agents/config/settings.py`) - understand the multi-source settings cascade

5. **Try extending a component** - implement a custom compaction strategy or workflow to understand the extension points

---

## Appendix: Quick Reference

### Common Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=mamba_agents

# Format code
uv run ruff format

# Lint code
uv run ruff check --fix

# Build package
uv build
```

### Environment Variables

```bash
# Model configuration
MAMBA_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1
MAMBA_MODEL_BACKEND__MODEL=llama3.2
MAMBA_MODEL_BACKEND__API_KEY=sk-...

# Logging
MAMBA_LOGGING__LEVEL=DEBUG

# Retry behavior
MAMBA_RETRY__RETRY_LEVEL=2
```

### Key Imports

```python
# Core
from mamba_agents import Agent, AgentSettings, AgentConfig, AgentResult

# Context
from mamba_agents import CompactionConfig, ContextState

# Tokens
from mamba_agents import TokenUsage, CostBreakdown

# Prompts
from mamba_agents import PromptManager, PromptTemplate, TemplateConfig

# MCP
from mamba_agents import MCPClientManager, MCPServerConfig

# Workflows
from mamba_agents import Workflow, WorkflowConfig, ReActWorkflow

# Tools
from mamba_agents.tools import read_file, write_file, run_bash, glob_search, grep_search
```

---

*Report generated by Codebase Analysis Workflow*
