# API Reference

Complete reference for all Mamba Agents classes and functions.

## Main Package

```python
from mamba_agents import (
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

    # Prompts
    PromptConfig,
    PromptManager,
    PromptTemplate,
    TemplateConfig,

    # Messages
    MessageQuery, MessageStats, ToolCallInfo, Turn,

    # Display
    DisplayPreset, MessageRenderer,
    RichRenderer, PlainTextRenderer, HtmlRenderer,
    print_stats, print_timeline, print_tools,
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
| [Prompts](prompts/index.md) | Jinja2 prompt templates |
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
from mamba_agents import Agent, AgentConfig, AgentSettings

# Tools
from mamba_agents.tools import read_file, write_file, run_bash

# Workflows
from mamba_agents.workflows import ReActWorkflow, ReActConfig

# Context (advanced)
from mamba_agents.context import ContextManager, CompactionConfig

# Prompts
from mamba_agents.prompts import PromptManager, TemplateConfig

# Messages
from mamba_agents import MessageQuery, MessageStats

# Display
from mamba_agents import print_stats, print_timeline, print_tools
from mamba_agents.agent.display import get_preset, COMPACT, DETAILED, VERBOSE

# MCP
from mamba_agents.mcp import MCPClientManager, MCPServerConfig

# Backends
from mamba_agents.backends import create_ollama_backend, get_profile
```
