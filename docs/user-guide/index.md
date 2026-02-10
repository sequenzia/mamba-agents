# User Guide

This guide covers all the features of Mamba Agents in detail.

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

-   :material-magnify: **Message Querying**

    ---

    Filter, analyze, and export conversation histories with rich analytics.

    [:octicons-arrow-right-24: Message Querying](message-querying.md)

-   :material-monitor: **Display Rendering**

    ---

    Render analytics as Rich tables, plain text, or HTML for Jupyter.

    [:octicons-arrow-right-24: Display Rendering](display-rendering.md)

-   :material-text-box-edit: **Prompt Management**

    ---

    Create and manage Jinja2-based prompt templates with versioning.

    [:octicons-arrow-right-24: Prompt Management](prompt-management.md)

</div>

## Extensions

<div class="grid cards" markdown>

-   :material-puzzle: **Skills** :material-flask-outline:{ title="Experimental" }

    ---

    Define reusable agent capabilities as SKILL.md files with discovery, trust, and testing.

    [:octicons-arrow-right-24: Skills](skills.md)

-   :material-account-group: **Subagents** :material-flask-outline:{ title="Experimental" }

    ---

    Delegate tasks to isolated child agents with usage tracking and three delegation patterns.

    [:octicons-arrow-right-24: Subagents](subagents.md)

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
| Agents | `mamba_agents` | `Agent`, `AgentConfig`, `AgentResult` |
| Tools | `mamba_agents.tools` | `read_file`, `run_bash`, `glob_search` |
| Context | `mamba_agents.context` | `ContextManager`, `CompactionConfig` |
| Tokens | `mamba_agents.tokens` | `TokenCounter`, `UsageTracker`, `CostEstimator` |
| Messages | `mamba_agents` | `MessageQuery`, `MessageStats`, `Turn` |
| Display | `mamba_agents.agent.display` | `DisplayPreset`, `print_stats`, `RichRenderer` |
| Prompts | `mamba_agents.prompts` | `PromptManager`, `PromptTemplate`, `TemplateConfig` |
| Skills | `mamba_agents.skills` | `SkillManager`, `Skill`, `SkillConfig` |
| Subagents | `mamba_agents.subagents` | `SubagentManager`, `SubagentConfig`, `SubagentResult` |
| Workflows | `mamba_agents.workflows` | `Workflow`, `ReActWorkflow` |
| MCP | `mamba_agents.mcp` | `MCPClientManager`, `MCPServerConfig` |
| Backends | `mamba_agents.backends` | `OpenAICompatibleBackend` |
| Errors | `mamba_agents.errors` | `CircuitBreaker`, `AgentError` |
| Observability | `mamba_agents.observability` | `setup_logging`, `RequestTracer` |
