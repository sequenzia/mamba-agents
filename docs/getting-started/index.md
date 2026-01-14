# Getting Started

Welcome to Pydantic Agent! This section will help you get up and running quickly.

## Prerequisites

- **Python 3.12+** - Pydantic Agent requires Python 3.12 or later
- **API Key** - An API key for your chosen model provider (OpenAI, Anthropic, etc.), or a local model server

## What's in this section

<div class="grid cards" markdown>

-   :material-download: **Installation**

    ---

    Install Pydantic Agent using uv or pip, including optional dependencies.

    [:octicons-arrow-right-24: Installation](installation.md)

-   :material-rocket-launch: **Quick Start**

    ---

    Create and run your first agent in under 5 minutes.

    [:octicons-arrow-right-24: Quick Start](quickstart.md)

-   :material-cog: **Configuration**

    ---

    Learn how to configure the agent using environment variables, `.env` files, and TOML.

    [:octicons-arrow-right-24: Configuration](configuration.md)

</div>

## Overview

Pydantic Agent is a thin wrapper around [pydantic-ai](https://ai.pydantic.dev/) that adds enterprise-grade infrastructure:

| Feature | Description |
|---------|-------------|
| **Context Management** | Automatic message tracking with 5 compaction strategies |
| **Token Tracking** | Built-in usage and cost estimation |
| **Workflows** | Orchestration patterns like ReAct for multi-step tasks |
| **MCP Integration** | Connect to Model Context Protocol servers |
| **Observability** | Structured logging, tracing, and OpenTelemetry |
| **Error Handling** | Retry logic and circuit breaker patterns |

The simplest way to start is:

```python
from pydantic_agent import Agent

agent = Agent("gpt-4o")
result = agent.run_sync("Hello!")
print(result.output)
```

Continue to the [Installation](installation.md) guide to get started.
