# API Reference

Complete reference for all Pydantic Agent classes and functions.

## Main Package

```python
from pydantic_agent import (
    # Core
    Agent,
    AgentConfig,
    AgentResult,
    AgentSettings,

    # Context
    CompactionConfig,
    CompactionResult,
    ContextState,

    # Tokens
    CostBreakdown,
    TokenUsage,
    UsageRecord,

    # Workflows
    Workflow,
    WorkflowConfig,
    WorkflowHooks,
    WorkflowResult,
    WorkflowState,
    WorkflowStep,
)
```

## Module Reference

### Core

| Module | Description |
|--------|-------------|
| [Agent](agent/index.md) | Core agent class and configuration |
| [Config](config/index.md) | Settings and configuration classes |

### Features

| Module | Description |
|--------|-------------|
| [Context](context/index.md) | Context management and compaction |
| [Tokens](tokens/index.md) | Token counting and cost estimation |
| [Workflows](workflows/index.md) | Workflow orchestration |
| [Tools](tools/index.md) | Built-in tools |

### Integration

| Module | Description |
|--------|-------------|
| [MCP](mcp/index.md) | Model Context Protocol integration |
| [Backends](backends/index.md) | Model backend adapters |

### Infrastructure

| Module | Description |
|--------|-------------|
| [Errors](errors/index.md) | Exceptions and error handling |
| [Observability](observability/index.md) | Logging and tracing |

## Import Patterns

### Recommended Imports

```python
# Core functionality
from pydantic_agent import Agent, AgentConfig, AgentSettings

# Tools
from pydantic_agent.tools import read_file, write_file, run_bash

# Workflows
from pydantic_agent.workflows import ReActWorkflow, ReActConfig

# Context (advanced)
from pydantic_agent.context import ContextManager, CompactionConfig

# MCP
from pydantic_agent.mcp import MCPClientManager, MCPServerConfig

# Backends
from pydantic_agent.backends import create_ollama_backend, get_profile
```
