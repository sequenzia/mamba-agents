# Mamba Agents

[![PyPI version](https://img.shields.io/pypi/v/mamba-agents.svg)](https://pypi.org/project/mamba-agents/)
[![Python Version](https://img.shields.io/pypi/pyversions/mamba-agents.svg)](https://pypi.org/project/mamba-agents/)
[![CI](https://github.com/sequenzia/mamba-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/sequenzia/mamba-agents/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://sequenzia.github.io/mamba-agents)

A simple, extensible AI Agent framework built on [pydantic-ai](https://ai.pydantic.dev/).

Mamba Agents provides a thin wrapper around pydantic-ai that adds production-ready infrastructure for building AI agents. It handles the operational complexity—context window management, token tracking, cost estimation, and observability—so you can focus on your agent's logic.

**Why Mamba Agents?**
- **Context that scales** - Automatic compaction keeps conversations within token limits using 5 different strategies
- **Cost visibility** - Track token usage and estimate costs across all your agent interactions
- **Tool ecosystem** - Built-in filesystem, bash, glob, and grep tools with security sandboxing
- **MCP ready** - Connect to Model Context Protocol servers for extended capabilities
- **Flexible prompts** - Jinja2 templates with versioning and inheritance
- **Local model support** - Works with Ollama, vLLM, and LM Studio out of the box

## Features

- **Simple Agent Loop** - Thin wrapper around pydantic-ai with tool-calling support
- **Built-in Tools** - Filesystem, glob, grep, and bash operations with security controls
- **MCP Integration** - Connect to Model Context Protocol servers (stdio, SSE, and Streamable HTTP transports)
- **Token Management** - Track usage with tiktoken, estimate costs
- **Context Compaction** - 5 strategies to manage long conversations
- **Prompt Management** - Jinja2-based templates with versioning and inheritance
- **Workflows** - Orchestration patterns for multi-step execution (ReAct built-in, extensible for custom patterns)
- **Model Backends** - OpenAI-compatible adapter for Ollama, vLLM, LM Studio
- **Observability** - Structured logging, tracing, and OpenTelemetry hooks
- **Error Handling** - Retry logic with tenacity, circuit breaker pattern

## Architecture Overview

```
                        ┌─────────────────┐
                        │      Agent      │
                        │  (pydantic-ai)  │
                        └────────┬────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Context     │    │     Token       │    │     Prompt      │
│    Management   │    │    Tracking     │    │    Management   │
└────────┬────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│   Compaction    │  (5 strategies: sliding_window, summarize_older,
│   Strategies    │   selective_pruning, importance_scoring, hybrid)
└─────────────────┘

External Integrations:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  MCP Servers    │    │ Model Backends  │    │  Observability  │
│(stdio/SSE/HTTP) │    │ (Ollama, vLLM)  │    │ (OTEL, logging) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Agent Patterns](#agent-patterns)
- [Configuration](#configuration)
- [Built-in Tools](#built-in-tools)
- [MCP Integration](#mcp-integration)
- [Context Management](#context-management)
- [Prompt Management](#prompt-management)
- [Token Management](#token-management)
- [Workflows](#workflows)
- [Model Backends](#model-backends)
- [Error Handling](#error-handling)
- [Observability](#observability)
- [Development](#development)
- [License](#license)

## Requirements

- **Python 3.12+** required
- An API key for your model provider (OpenAI, Anthropic, etc.) or a local model server (Ollama, vLLM, LM Studio)

## Installation

Install from [PyPI](https://pypi.org/project/mamba-agents/):

```bash
# Using uv (recommended)
uv add mamba-agents

# Using pip
pip install mamba-agents
```

## Quick Start

### Synchronous Usage (Simplest)

```python
from mamba_agents import Agent, AgentSettings

# Load settings from env vars, .env, ~/mamba.env, config.toml
settings = AgentSettings()

# Create agent
agent = Agent("gpt-4o", settings=settings)

# Run a query
result = agent.run_sync("What is 2 + 2?")
print(result.output)

# Multi-turn conversation (context maintained automatically)
agent.run_sync("Remember my name is Alice")
result = agent.run_sync("What's my name?")
print(result.output)  # "Alice"

# Check usage and cost
print(f"Tokens used: {agent.get_usage().total_tokens}")
print(f"Estimated cost: ${agent.get_cost():.4f}")
```

### Async Usage

```python
import asyncio
from mamba_agents import Agent, AgentSettings

async def main():
    settings = AgentSettings()
    agent = Agent("gpt-4o", settings=settings)

    # Run async queries
    result = await agent.run("What files are in the current directory?")
    print(result.output)

    # Multi-turn conversation
    result2 = await agent.run("Can you list only the Python files?")
    print(result2.output)

    # Access context state
    state = agent.get_context_state()
    print(f"Messages: {state.message_count}, Tokens: {state.token_count}")

asyncio.run(main())
```

## Agent Patterns

The `Agent` class supports multiple initialization patterns:

### Using Settings (Recommended)

```python
from mamba_agents import Agent, AgentSettings

# Load from env vars, .env, ~/mamba.env, config.toml
settings = AgentSettings()

# Uses model, api_key, and base_url from settings.model_backend
agent = Agent(settings=settings)

# Override model but use api_key/base_url from settings
agent = Agent("gpt-4o-mini", settings=settings)
```

### Direct Model String

```python
# Requires OPENAI_API_KEY environment variable
agent = Agent("gpt-4o")
```

### With a Model Instance

```python
from pydantic_ai.models.openai import OpenAIModel

model = OpenAIModel("gpt-4o")
agent = Agent(model)
```

### With Tools

```python
from mamba_agents.tools import read_file, run_bash, grep_search

agent = Agent("gpt-4o", tools=[read_file, run_bash, grep_search], settings=settings)
```

### With MCP Toolsets

```python
from mamba_agents.mcp import MCPClientManager

# Load MCP servers from .mcp.json file
manager = MCPClientManager.from_mcp_json(".mcp.json")

# Pass toolsets to Agent (pydantic-ai manages server lifecycle)
agent = Agent("gpt-4o", toolsets=manager.as_toolsets(), settings=settings)
```

> **Security Note:** API keys are stored using Pydantic's `SecretStr` and are never logged or exposed in error messages.

## Configuration

### Environment Variables

All settings use the `MAMBA_` prefix. Variables can be set in:
- Environment variables
- `.env` file (project-specific)
- `~/mamba.env` (user-wide defaults)

```bash
# Model configuration
MAMBA_MODEL_BACKEND__MODEL=gpt-4o
MAMBA_MODEL_BACKEND__API_KEY=sk-...
MAMBA_MODEL_BACKEND__BASE_URL=https://api.openai.com/v1

# Logging
MAMBA_LOGGING__LEVEL=INFO
MAMBA_LOGGING__FORMAT=json

# Retry behavior
MAMBA_RETRY__MAX_RETRIES=3
MAMBA_RETRY__RETRY_LEVEL=2
```

### TOML Configuration

Create a `config.toml` file:

```toml
[model_backend]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"

[logging]
level = "INFO"
format = "json"
redact_sensitive = true

[retry]
max_retries = 3
retry_level = 2

[context]
strategy = "hybrid"
trigger_threshold_tokens = 100000
target_tokens = 80000
```

## Built-in Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read contents of a file |
| `write_file` | Write or overwrite a file |
| `append_file` | Append content to a file |
| `list_directory` | List contents of a directory with metadata |
| `file_info` | Get file or directory metadata (size, modified, created) |
| `delete_file` | Delete a file |
| `move_file` | Move or rename a file |
| `copy_file` | Copy a file |
| `glob_search` | Find files matching a glob pattern (e.g., `**/*.py`) |
| `grep_search` | Search file contents for a pattern with context lines |
| `run_bash` | Execute a shell command with timeout support |

### Usage Examples

```python
from mamba_agents.tools import (
    read_file, write_file, list_directory,
    glob_search, grep_search, run_bash,
)

# File operations
content = read_file("config.json")
write_file("output.txt", "Hello, World!")
entries = list_directory("/project", recursive=True)

# Search for files by pattern
py_files = glob_search("**/*.py", root_dir="/project")

# Search file contents
matches = grep_search(
    pattern=r"def \w+",
    path="/project",
    file_pattern="*.py",
    context_lines=2,
)

# Run shell commands
result = run_bash("ls -la", timeout=30)
print(result.stdout)
```

### Security Sandbox

```python
from mamba_agents.tools.filesystem import FilesystemSecurity

security = FilesystemSecurity(
    sandbox_mode=True,
    base_directory="/safe/path",
    allowed_extensions=[".txt", ".json", ".py"],
)

# Pass security context to tools
content = read_file("data.txt", security=security)
```

## MCP Integration

Connect to Model Context Protocol servers for extended tool capabilities.

### Basic Usage with Agent

```python
from mamba_agents import Agent
from mamba_agents.mcp import MCPClientManager, MCPServerConfig

# Configure MCP servers
configs = [
    MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/project"],
        tool_prefix="fs",  # Tools become fs_read, fs_write, etc.
    ),
]

# Create manager and pass to Agent via toolsets parameter
manager = MCPClientManager(configs)
agent = Agent("gpt-4o", toolsets=manager.as_toolsets(), settings=settings)

# pydantic-ai handles server lifecycle automatically
result = agent.run_sync("List the files in /project")
```

### Loading from .mcp.json Files

Compatible with Claude Desktop configuration format:

```python
from mamba_agents import Agent
from mamba_agents.mcp import MCPClientManager, load_mcp_json

# Create manager directly from file
manager = MCPClientManager.from_mcp_json(".mcp.json")

# Or load and merge multiple files
manager = MCPClientManager()
manager.add_from_file("project/.mcp.json")
manager.add_from_file("~/.mcp.json")  # User defaults

agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
```

Example `.mcp.json` file:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/project"],
      "tool_prefix": "fs"
    },
    "web": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

### SSE Transport with Authentication

```python
from mamba_agents.mcp import MCPServerConfig, MCPAuthConfig

config = MCPServerConfig(
    name="api-server",
    transport="sse",
    url="https://api.example.com/mcp/sse",
    auth=MCPAuthConfig(key_env="MCP_API_KEY"),  # Read from environment
    timeout=60,        # Connection timeout (seconds)
    read_timeout=300,  # Read timeout for long operations
)
```

### Streamable HTTP Transport (v0.1.3+)

For modern MCP servers using the Streamable HTTP protocol:

```python
from mamba_agents.mcp import MCPServerConfig, MCPAuthConfig

config = MCPServerConfig(
    name="api-server",
    transport="streamable_http",
    url="https://api.example.com/mcp",
    auth=MCPAuthConfig(key_env="MCP_API_KEY"),
    timeout=60,
    read_timeout=300,
)
```

> **Note:** Transport is auto-detected from URL when loading `.mcp.json` files:
> URLs ending in `/sse` use SSE transport; other URLs use Streamable HTTP.

### Testing MCP Connections (v0.1.3+)

Verify MCP server connectivity before running agents:

```python
from mamba_agents.mcp import MCPClientManager

manager = MCPClientManager.from_mcp_json(".mcp.json")

# Test a single server
result = manager.test_connection_sync("filesystem")
if result.success:
    print(f"Connected! {result.tool_count} tools available")
    for tool in result.tools:
        print(f"  - {tool.name}: {tool.description}")
else:
    print(f"Failed: {result.error}")

# Test all servers
results = manager.test_all_connections_sync()
for name, result in results.items():
    status = "OK" if result.success else f"FAILED: {result.error}"
    print(f"{name}: {status}")
```

## Context Management

Context is managed automatically by the Agent. Messages are tracked across runs and auto-compacted when thresholds are reached.

### Built-in Agent Context (Recommended)

```python
from mamba_agents import Agent, AgentConfig, CompactionConfig

# Context tracking is enabled by default
agent = Agent("gpt-4o", settings=settings)

# Run multiple turns - context is maintained automatically
agent.run_sync("Hello, I'm working on a Python project")
agent.run_sync("Can you help me refactor the main function?")

# Access context via Agent methods
messages = agent.get_messages()           # Get all tracked messages
state = agent.get_context_state()         # Get token count, message count
should_compact = agent.should_compact()   # Check if threshold reached

# Manual compaction
result = await agent.compact()
print(f"Removed {result.removed_count} messages")

# Clear context for new conversation
agent.clear_context()

# Customize compaction settings
config = AgentConfig(
    context=CompactionConfig(
        strategy="hybrid",
        trigger_threshold_tokens=50000,
        target_tokens=40000,
    ),
    auto_compact=True,  # Auto-compact when threshold reached (default)
)
agent = Agent("gpt-4o", settings=settings, config=config)

# Disable context tracking if not needed
config = AgentConfig(track_context=False)
agent = Agent("gpt-4o", settings=settings, config=config)
```

### Standalone Context Manager

For advanced use cases, you can use ContextManager directly:

```python
from mamba_agents.context import (
    ContextManager,
    CompactionConfig,
    SlidingWindowStrategy,
    SummarizeOlderStrategy,
    HybridStrategy,
)

# Configure compaction
config = CompactionConfig(
    strategy="hybrid",  # or sliding_window, summarize_older, etc.
    trigger_threshold_tokens=100000,
    target_tokens=80000,
    preserve_recent_turns=5,
)

manager = ContextManager(config=config)

# Add messages
manager.add_messages([
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"},
])

# Check if compaction is needed
if manager.should_compact():
    result = await manager.compact()
    print(f"Removed {result.removed_count} messages")
```

### Available Strategies

| Strategy | Description |
|----------|-------------|
| `sliding_window` | Remove oldest messages beyond threshold |
| `summarize_older` | LLM-based summarization of older messages |
| `selective_pruning` | Remove completed tool call/result pairs |
| `importance_scoring` | LLM-based scoring, prune lowest importance |
| `hybrid` | Combine multiple strategies in sequence |

## Prompt Management

Manage system prompts with Jinja2 templates, versioning, and inheritance.

### Using Templates with Agents

```python
from mamba_agents import Agent
from mamba_agents.prompts import TemplateConfig, PromptManager

# Option 1: String prompt (backward compatible)
agent = Agent("gpt-4o", system_prompt="You are a helpful assistant.")

# Option 2: Template config (loads from file)
agent = Agent(
    "gpt-4o",
    system_prompt=TemplateConfig(
        name="system/assistant",
        variables={"name": "Code Helper", "expertise": "Python"}
    )
)

# Option 3: Pre-render template
manager = PromptManager()
prompt = manager.render("system/assistant", name="Code Helper")
agent = Agent("gpt-4o", system_prompt=prompt)

# Runtime prompt switching
agent.set_system_prompt(TemplateConfig(
    name="system/coder",
    variables={"language": "Python"}
))

# Get current prompt
print(agent.get_system_prompt())
```

### File-Based Templates

Organize templates in a versioned directory structure:

```
prompts/
├── v1/
│   ├── base/
│   │   └── base.jinja2
│   ├── system/
│   │   ├── assistant.jinja2
│   │   └── coder.jinja2
│   └── workflow/
│       └── react.jinja2
└── v2/
    └── system/
        └── assistant.jinja2
```

Example base template (`prompts/v1/base/base.jinja2`):

```jinja2
{% block persona %}You are a helpful AI assistant.{% endblock %}

{% block instructions %}{% endblock %}

{% block constraints %}{% endblock %}
```

Example child template (`prompts/v1/system/coder.jinja2`):

```jinja2
{% extends "v1/base/base.jinja2" %}

{% block persona %}
You are an expert {{ language | default("Python") }} developer.
{% endblock %}

{% block instructions %}
Help the user write clean, efficient code.
{% endblock %}
```

### Standalone PromptManager

```python
from mamba_agents.prompts import PromptManager, PromptConfig

# Configure prompts directory
config = PromptConfig(
    prompts_dir="./prompts",
    default_version="v1",
    enable_caching=True,
    strict_mode=False,  # Raise on missing variables
)
manager = PromptManager(config)

# Load and render template
template = manager.get("system/assistant")
prompt = template.render(name="Helper", role="coding assistant")

# Or render directly
prompt = manager.render("system/assistant", name="Helper")

# List available templates
templates = manager.list_prompts(category="system")
versions = manager.list_versions("system/assistant")

# Register templates programmatically (useful for testing)
manager.register("test/greeting", "Hello, {{ name }}!")
result = manager.render("test/greeting", name="World")
```

### Workflow Integration

```python
from mamba_agents.workflows import ReActWorkflow, ReActConfig
from mamba_agents.prompts import TemplateConfig

config = ReActConfig(
    system_prompt_template=TemplateConfig(name="workflow/react_system"),
    iteration_prompt_template=TemplateConfig(name="workflow/react_iteration"),
)
workflow = ReActWorkflow(agent, config=config)
```

## Token Management

Usage tracking and cost estimation are built into the Agent. Every run automatically records token usage.

### Built-in Agent Tracking (Recommended)

```python
from mamba_agents import Agent

agent = Agent("gpt-4o", settings=settings)

# Run some queries
agent.run_sync("Hello!")
agent.run_sync("Tell me about Python")
agent.run_sync("What are decorators?")

# Get aggregate usage
usage = agent.get_usage()
print(f"Total tokens: {usage.total_tokens}")
print(f"Requests: {usage.request_count}")

# Get cost estimate
cost = agent.get_cost()
print(f"Estimated cost: ${cost:.4f}")

# Get detailed breakdown
breakdown = agent.get_cost_breakdown()
print(f"Prompt cost: ${breakdown.prompt_cost:.4f}")
print(f"Completion cost: ${breakdown.completion_cost:.4f}")

# Get per-request history
history = agent.get_usage_history()
for record in history:
    print(f"{record.timestamp}: {record.total_tokens} tokens")

# Reset tracking for new session
agent.reset_tracking()

# Count tokens for arbitrary text
count = agent.get_token_count("Hello, world!")
```

### Standalone Token Utilities

For advanced use cases, you can use the token utilities directly:

```python
from mamba_agents.tokens import TokenCounter, UsageTracker, CostEstimator

# Count tokens
counter = TokenCounter(encoding="cl100k_base")
count = counter.count("Hello, world!")
msg_count = counter.count_messages([{"role": "user", "content": "Hi"}])

# Track usage across requests
tracker = UsageTracker()
tracker.record_usage(input_tokens=100, output_tokens=50, model="gpt-4o")
summary = tracker.get_summary()

# Estimate costs
estimator = CostEstimator()
cost = estimator.estimate(input_tokens=1000, output_tokens=500, model="gpt-4o")
```

## Workflows

Workflows provide orchestration patterns for multi-step agent execution.

### ReAct Workflow (Built-in)

The ReAct (Reasoning and Acting) workflow implements an iterative Thought → Action → Observation loop:

```python
from mamba_agents import Agent
from mamba_agents.workflows import ReActWorkflow, ReActConfig
from mamba_agents.tools import read_file, run_bash, grep_search

# Create agent with tools
agent = Agent(
    "gpt-4o",
    settings=settings,
    tools=[read_file, run_bash, grep_search],
)

# Create ReAct workflow
workflow = ReActWorkflow(
    agent=agent,
    config=ReActConfig(
        max_iterations=15,
        expose_reasoning=True,  # Include thoughts in output
    ),
)

# Run the workflow
result = await workflow.run("Find and explain the bug in src/utils.py")

print(f"Success: {result.success}")
print(f"Answer: {result.output}")
print(f"Iterations: {result.state.iteration_count}")

# Access the reasoning trace
for entry in result.state.context.scratchpad:
    print(f"{entry.entry_type}: {entry.content}")

# Or use convenience methods
print(workflow.get_reasoning_trace())
print(f"Cost: ${workflow.get_cost():.4f}")
```

### Custom Workflows

Create custom workflows by extending the `Workflow` base class:

```python
from mamba_agents import Agent, Workflow, WorkflowConfig, WorkflowState, WorkflowHooks

# Create a custom workflow by extending Workflow
class MyWorkflow(Workflow[None, str, dict]):
    def __init__(self, agent: Agent, config: WorkflowConfig | None = None):
        super().__init__(config=config)
        self.agent = agent

    @property
    def name(self) -> str:
        return "my_workflow"

    def _create_initial_state(self, prompt: str) -> WorkflowState[dict]:
        return WorkflowState(context={"prompt": prompt, "observations": []})

    async def _execute(self, prompt: str, state: WorkflowState[dict], deps=None) -> str:
        # Implement your workflow logic
        while state.iteration_count < self._config.max_iterations:
            state.iteration_count += 1
            result = await self.agent.run(prompt)
            if self._is_complete(result):
                return result.output
        return "Max iterations reached"

# Run the workflow
agent = Agent("gpt-4o", settings=settings)
workflow = MyWorkflow(agent, config=WorkflowConfig(max_iterations=5))

result = await workflow.run("Research and summarize recent AI papers")
print(f"Success: {result.success}")
print(f"Output: {result.output}")
print(f"Steps: {result.total_steps}")
```

> **Note:** Currently only ReAct is built-in. Create custom workflows by extending the `Workflow` base class for patterns like Plan-Execute, Reflection, or Tree of Thoughts.

### Workflow Configuration

```python
from mamba_agents import WorkflowConfig
from mamba_agents.workflows import ReActConfig

# Base workflow configuration
config = WorkflowConfig(
    max_steps=50,              # Maximum workflow steps
    max_iterations=10,         # Maximum iterations per step
    timeout_seconds=300.0,     # Total workflow timeout
    step_timeout_seconds=30.0, # Per-step timeout
    enable_hooks=True,         # Enable hook callbacks
    track_state=True,          # Track detailed state history
)

# ReAct-specific configuration (extends WorkflowConfig)
react_config = ReActConfig(
    max_iterations=15,
    expose_reasoning=True,           # Include thoughts in scratchpad
    reasoning_prefix="Thought: ",    # Prefix for thoughts
    action_prefix="Action: ",        # Prefix for actions
    observation_prefix="Observation: ",  # Prefix for observations
    final_answer_tool_name="final_answer",  # Termination tool name
    auto_compact_in_workflow=True,   # Auto-compact context
    compact_threshold_ratio=0.8,     # Compact at 80% of threshold
    max_consecutive_thoughts=3,      # Force action after N thoughts
    tool_retry_count=2,              # Retry failed tool calls
)
```

### Workflow Hooks

Add observability with lifecycle hooks:

```python
from mamba_agents import WorkflowHooks
from mamba_agents.workflows import ReActHooks

# Base workflow hooks
def on_step_complete(state, step):
    print(f"Step {step.step_number} completed: {step.description}")

hooks = WorkflowHooks(
    on_workflow_start=lambda state: print("Workflow started"),
    on_workflow_complete=lambda result: print(f"Done: {result.success}"),
    on_workflow_error=lambda state, err: print(f"Error: {err}"),
    on_step_start=lambda state, num, type_: print(f"Step {num}: {type_}"),
    on_step_complete=on_step_complete,
    on_step_error=lambda state, step, err: print(f"Step failed: {err}"),
    on_iteration_start=lambda state, i: print(f"Iteration {i}"),
    on_iteration_complete=lambda state, i: print(f"Iteration {i} done"),
)

# ReAct-specific hooks (extends WorkflowHooks)
react_hooks = ReActHooks(
    on_thought=lambda state, thought: print(f"Thought: {thought}"),
    on_action=lambda state, tool, args: print(f"Action: {tool}({args})"),
    on_observation=lambda state, obs, err: print(f"Observation: {obs}"),
    on_compaction=lambda result: print(f"Compacted: removed {result.removed_count}"),
    # Plus all base WorkflowHooks callbacks...
)

workflow = ReActWorkflow(agent, config=react_config, hooks=react_hooks)
```

## Model Backends

Use local models with OpenAI-compatible APIs:

```python
from mamba_agents.backends import (
    OpenAICompatibleBackend,
    create_ollama_backend,
    create_vllm_backend,
    create_lmstudio_backend,
    get_profile,
)

# Ollama
backend = create_ollama_backend("llama3.2")

# vLLM
backend = create_vllm_backend("meta-llama/Llama-3.2-3B-Instruct")

# LM Studio
backend = create_lmstudio_backend()

# Custom OpenAI-compatible
backend = OpenAICompatibleBackend(
    model="my-model",
    base_url="http://localhost:8000/v1",
    api_key="optional-key",
)

# Check model capabilities
profile = get_profile("gpt-4o")
print(f"Context window: {profile.context_window}")
print(f"Supports tools: {profile.supports_tools}")
```

## Error Handling

Robust error handling with retry and circuit breaker:

```python
from mamba_agents.errors import (
    AgentError,
    ModelBackendError,
    RateLimitError,
    CircuitBreaker,
    create_retry_decorator,
)

# Custom retry decorator
@create_retry_decorator(max_attempts=3, base_wait=1.0)
async def call_api():
    ...

# Circuit breaker for external services
breaker = CircuitBreaker("model-api", failure_threshold=5, timeout=30.0)

async with breaker:
    result = await model.complete(messages)
```

## Observability

Structured logging and tracing:

```python
from mamba_agents.observability import (
    setup_logging,
    RequestTracer,
    get_otel_integration,
)
from mamba_agents.config import LoggingConfig

# Configure logging
config = LoggingConfig(
    level="INFO",
    format="json",
    redact_sensitive=True,
)
logger = setup_logging(config)

# Request tracing
tracer = RequestTracer()
tracer.start_trace()

with tracer.start_span("agent.run") as span:
    span.set_attribute("prompt_length", len(prompt))
    result = await agent.run(prompt)

trace = tracer.end_trace()

# OpenTelemetry (optional)
otel = get_otel_integration()
if otel.initialize():
    with otel.trace_agent_run(prompt, model="gpt-4o"):
        result = await agent.run(prompt)
```

## Development

```bash
# Clone the repository
git clone https://github.com/sequenzia/mamba-agents.git
cd mamba-agents

# Install dependencies
uv sync

# Run tests
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

## Versioning & Releases

This project uses [Semantic Versioning](https://semver.org/) with git tag-based version management via [hatch-vcs](https://github.com/ofek/hatch-vcs).

- **Version source**: Git tags (e.g., `v0.1.0` → version `0.1.0`)
- **Development versions**: Commits without tags get versions like `0.1.0.dev12`
- **CI/CD**: GitHub Actions for testing and PyPI publishing

### Creating a Release

```bash
# Create and push a version tag
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

This triggers the release workflow which:
1. Builds the package
2. Publishes to TestPyPI
3. Publishes to PyPI

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Documentation

The documentation is built with [MkDocs](https://www.mkdocs.org/) and the [Material theme](https://squidfunk.github.io/mkdocs-material/).

```bash
# Serve docs locally (with hot reload)
uv run mkdocs serve

# Build static site
uv run mkdocs build

# Deploy to GitHub Pages
uv run mkdocs gh-deploy
```

View the live documentation at [sequenzia.github.io/mamba-agents](https://sequenzia.github.io/mamba-agents).

## License

MIT
