# User Guide

This guide covers all the features of Pydantic Agent in detail.

## Core Features

<div class="grid cards" markdown>

-   :material-robot: **Agent Basics**

    ---

    Learn how to create and run agents, handle responses, and manage state.

    [:octicons-arrow-right-24: Agent Basics](agent-basics.md)

-   :material-tools: **Working with Tools**

    ---

    Use built-in tools and create custom tools for your agents.

    [:octicons-arrow-right-24: Tools](tools.md)

-   :material-chat-processing: **Context Management**

    ---

    Manage conversation context and implement compaction strategies.

    [:octicons-arrow-right-24: Context Management](context-management.md)

-   :material-counter: **Token Tracking**

    ---

    Track token usage and estimate costs across requests.

    [:octicons-arrow-right-24: Token Tracking](token-tracking.md)

</div>

## Advanced Features

<div class="grid cards" markdown>

-   :material-state-machine: **Workflows**

    ---

    Orchestrate multi-step agent execution with ReAct and custom patterns.

    [:octicons-arrow-right-24: Workflows](workflows.md)

-   :material-connection: **MCP Integration**

    ---

    Connect to Model Context Protocol servers for external tools.

    [:octicons-arrow-right-24: MCP Integration](mcp-integration.md)

-   :material-server: **Model Backends**

    ---

    Use local models with Ollama, vLLM, or LM Studio.

    [:octicons-arrow-right-24: Model Backends](model-backends.md)

-   :material-alert-circle: **Error Handling**

    ---

    Implement retry logic and circuit breaker patterns.

    [:octicons-arrow-right-24: Error Handling](error-handling.md)

-   :material-chart-timeline: **Observability**

    ---

    Set up logging, tracing, and OpenTelemetry integration.

    [:octicons-arrow-right-24: Observability](observability.md)

</div>

## Quick Reference

| Feature | Module | Primary Classes |
|---------|--------|-----------------|
| Agents | `pydantic_agent` | `Agent`, `AgentConfig`, `AgentResult` |
| Tools | `pydantic_agent.tools` | `read_file`, `run_bash`, `glob_search` |
| Context | `pydantic_agent.context` | `ContextManager`, `CompactionConfig` |
| Tokens | `pydantic_agent.tokens` | `TokenCounter`, `UsageTracker`, `CostEstimator` |
| Workflows | `pydantic_agent.workflows` | `Workflow`, `ReActWorkflow` |
| MCP | `pydantic_agent.mcp` | `MCPClientManager`, `MCPServerConfig` |
| Backends | `pydantic_agent.backends` | `OpenAICompatibleBackend` |
| Errors | `pydantic_agent.errors` | `CircuitBreaker`, `AgentError` |
| Observability | `pydantic_agent.observability` | `setup_logging`, `RequestTracer` |
