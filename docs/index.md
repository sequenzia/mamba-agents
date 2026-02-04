# Mamba Agents

A simple, extensible AI Agent framework built on [pydantic-ai](https://ai.pydantic.dev/).

## Installation

=== "uv (recommended)"

    ```bash
    uv add mamba-agents
    ```

=== "pip"

    ```bash
    pip install mamba-agents
    ```

## Quick Start

```python
from mamba_agents import Agent, AgentSettings

# Load settings from env vars, .env, ~/mamba.env, config.toml
settings = AgentSettings()

# Create agent using settings
agent = Agent(settings=settings)

# Run the agent - context and usage are tracked automatically
result = await agent.run("What files are in the current directory?")
print(result.output)

# Check usage and cost
print(agent.get_usage())  # TokenUsage(prompt_tokens=..., request_count=1)
print(agent.get_cost())   # Cost in USD
```

## Features

<div class="grid cards" markdown>

-   :material-robot: **Agent Basics**

    ---

    Thin wrapper around pydantic-ai with tool-calling support and automatic context management.

    [:octicons-arrow-right-24: Learn more](user-guide/agent-basics.md)

-   :material-tools: **Built-in Tools**

    ---

    Filesystem, glob, grep, and bash operations with security controls.

    [:octicons-arrow-right-24: Explore tools](user-guide/tools.md)

-   :material-connection: **MCP Integration**

    ---

    Connect to Model Context Protocol servers (stdio and SSE transports).

    [:octicons-arrow-right-24: Setup MCP](user-guide/mcp-integration.md)

-   :material-counter: **Token Tracking**

    ---

    Track usage with tiktoken, estimate costs automatically.

    [:octicons-arrow-right-24: Track usage](user-guide/token-tracking.md)

-   :material-magnify: **Message Analytics**

    ---

    Query, filter, export, and visualize conversation history with rich formatting.

    [:octicons-arrow-right-24: Message analytics](user-guide/message-querying.md)

-   :material-chat-processing: **Context Compaction**

    ---

    5 strategies to manage long conversations without losing important context.

    [:octicons-arrow-right-24: Manage context](user-guide/context-management.md)

-   :material-state-machine: **Workflows**

    ---

    Orchestration patterns for multi-step execution (ReAct, Plan-Execute, etc.).

    [:octicons-arrow-right-24: Build workflows](user-guide/workflows.md)

-   :material-server: **Model Backends**

    ---

    OpenAI-compatible adapter for Ollama, vLLM, LM Studio.

    [:octicons-arrow-right-24: Use local models](user-guide/model-backends.md)

-   :material-chart-timeline: **Observability**

    ---

    Structured logging, tracing, and OpenTelemetry hooks.

    [:octicons-arrow-right-24: Add observability](user-guide/observability.md)

</div>

## Choose Your Path

<div class="grid cards" markdown>

-   :material-rocket-launch: **New to Mamba Agents?**

    ---

    Get up and running in under 5 minutes with the quick start guide.

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart.md)

-   :material-laptop: **Want to use local models?**

    ---

    Set up Ollama, vLLM, or LM Studio for offline inference.

    [:octicons-arrow-right-24: Local LLM Setup](tutorials/local-llm-setup.md)

-   :material-code-braces: **Building a code assistant?**

    ---

    Step-by-step tutorial for building an AI coding assistant.

    [:octicons-arrow-right-24: Code Assistant Tutorial](tutorials/code-assistant.md)

-   :material-sync: **Need multi-step workflows?**

    ---

    Learn the ReAct pattern for complex reasoning tasks.

    [:octicons-arrow-right-24: ReAct Workflow](tutorials/react-workflow.md)

</div>

## Quick Reference

| Use Case | Import |
|----------|--------|
| Basic agent | `from mamba_agents import Agent` |
| With settings | `from mamba_agents import Agent, AgentSettings` |
| Built-in tools | `from mamba_agents.tools import read_file, run_bash, glob_search` |
| ReAct workflow | `from mamba_agents.workflows import ReActWorkflow, ReActConfig` |
| Token tracking | `from mamba_agents.tokens import TokenCounter, CostEstimator` |
| Message analytics | `from mamba_agents import MessageQuery, print_stats` |
| MCP servers | `from mamba_agents.mcp import MCPClientManager, MCPServerConfig` |

## Explore the Docs

<div class="grid cards" markdown>

-   :material-rocket-launch: **Getting Started**

    ---

    Install the package and configure your environment.

    [:octicons-arrow-right-24: Get started](getting-started/index.md)

-   :material-book-open-variant: **User Guide**

    ---

    Learn how to use all the features of Mamba Agents.

    [:octicons-arrow-right-24: User Guide](user-guide/index.md)

-   :material-school: **Tutorials**

    ---

    Step-by-step guides for common use cases.

    [:octicons-arrow-right-24: Tutorials](tutorials/index.md)

-   :material-lightbulb: **Concepts**

    ---

    Understand the architecture and design patterns.

    [:octicons-arrow-right-24: Concepts](concepts/index.md)

-   :material-api: **API Reference**

    ---

    Complete reference for all classes and functions.

    [:octicons-arrow-right-24: API Reference](api/index.md)

</div>
