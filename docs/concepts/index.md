# Concepts

Deep dives into the architecture and design of Pydantic Agent.

## Overview

<div class="grid cards" markdown>

-   :material-sitemap: **Architecture Overview**

    ---

    Understand how all the components fit together.

    [:octicons-arrow-right-24: Architecture](architecture.md)

-   :material-reload: **Agent Execution Loop**

    ---

    How agents process messages and call tools.

    [:octicons-arrow-right-24: Execution Loop](execution-loop.md)

-   :material-compress: **Context Compaction Strategies**

    ---

    Deep dive into the 5 compaction strategies.

    [:octicons-arrow-right-24: Compaction Strategies](compaction-strategies.md)

-   :material-state-machine: **Workflow Patterns**

    ---

    ReAct, Plan-Execute, and other orchestration patterns.

    [:octicons-arrow-right-24: Workflow Patterns](workflow-patterns.md)

</div>

## Key Concepts

### Agent as a Thin Wrapper

Pydantic Agent wraps [pydantic-ai](https://ai.pydantic.dev/) with additional infrastructure:

```
┌─────────────────────────────────────────────────────┐
│                  Pydantic Agent                      │
│  ┌─────────────────────────────────────────────┐    │
│  │              pydantic-ai Agent               │    │
│  └─────────────────────────────────────────────┘    │
│  + Context Management (message tracking, compaction)│
│  + Token Tracking (usage, cost estimation)          │
│  + Configuration (settings, env vars, files)        │
│  + Observability (logging, tracing, OTel)          │
│  + Error Handling (retry, circuit breaker)          │
└─────────────────────────────────────────────────────┘
```

### Configuration Priority

Settings load from multiple sources:

```
1. Constructor arguments     (highest priority)
2. Environment variables     AGENTS_*
3. .env file                 project-specific
4. ~/agents.env              user-wide defaults
5. config.toml / config.yaml file-based config
6. Default values            (lowest priority)
```

### Built-in vs. Standalone Components

Most features work both integrated and standalone:

| Feature | Built-in (Agent) | Standalone |
|---------|------------------|------------|
| Context | `agent.get_messages()` | `ContextManager` |
| Tokens | `agent.get_usage()` | `TokenCounter`, `UsageTracker` |
| Cost | `agent.get_cost()` | `CostEstimator` |
| Logging | Automatic | `setup_logging()` |

### Workflows vs. Agent Runs

| Aspect | Agent Run | Workflow |
|--------|-----------|----------|
| Scope | Single request | Multi-step task |
| State | Context maintained | Full state tracking |
| Control | Limited | Fine-grained |
| Use case | Chat, Q&A | Research, analysis |
