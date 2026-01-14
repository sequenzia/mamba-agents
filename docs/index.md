# Pydantic Agent

A simple, extensible AI Agent framework built on [pydantic-ai](https://ai.pydantic.dev/).

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### Simple Agent Loop
Thin wrapper around pydantic-ai with tool-calling support and automatic context management.
</div>

<div class="feature-card" markdown>
### Built-in Tools
Filesystem, glob, grep, and bash operations with security controls.
</div>

<div class="feature-card" markdown>
### MCP Integration
Connect to Model Context Protocol servers (stdio and SSE transports).
</div>

<div class="feature-card" markdown>
### Token Management
Track usage with tiktoken, estimate costs automatically.
</div>

<div class="feature-card" markdown>
### Context Compaction
5 strategies to manage long conversations without losing important context.
</div>

<div class="feature-card" markdown>
### Workflows
Orchestration patterns for multi-step execution (ReAct, Plan-Execute, etc.).
</div>

<div class="feature-card" markdown>
### Model Backends
OpenAI-compatible adapter for Ollama, vLLM, LM Studio.
</div>

<div class="feature-card" markdown>
### Observability
Structured logging, tracing, and OpenTelemetry hooks.
</div>

</div>

## Quick Start

```python
from pydantic_agent import Agent, AgentSettings

# Load settings from env vars, .env, ~/agents.env, config.toml
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

## Installation

=== "uv (recommended)"

    ```bash
    uv add pydantic-agent
    ```

=== "pip"

    ```bash
    pip install pydantic-agent
    ```

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch: **Getting Started**

    ---

    Install the package and run your first agent in under 5 minutes.

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart.md)

-   :material-book-open-variant: **User Guide**

    ---

    Learn how to use all the features of Pydantic Agent.

    [:octicons-arrow-right-24: User Guide](user-guide/index.md)

-   :material-school: **Tutorials**

    ---

    Step-by-step guides for common use cases.

    [:octicons-arrow-right-24: Tutorials](tutorials/index.md)

-   :material-api: **API Reference**

    ---

    Complete reference for all classes and functions.

    [:octicons-arrow-right-24: API Reference](api/index.md)

</div>
