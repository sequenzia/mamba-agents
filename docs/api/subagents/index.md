# Subagents Module

!!! warning "Experimental"
    The subagents subsystem is experimental. Public API may change in minor versions.

Task delegation to isolated child agents. The subagents subsystem allows a parent agent
to spawn lightweight, isolated `Agent` instances for focused sub-tasks. Each subagent gets
its own context manager, usage tracker, and configuration -- ensuring complete isolation
from the parent while still aggregating token usage back for unified tracking.

## Pages

| Page | Description |
|------|-------------|
| [SubagentManager](manager.md) | Main facade for registering, delegating, and tracking subagents |
| [Configuration](config.md) | `SubagentConfig`, `SubagentResult`, and `DelegationHandle` data models |
| [Errors](errors.md) | Subagent exception hierarchy |

## Quick Example

```python
from mamba_agents import Agent, SubagentConfig

agent = Agent("gpt-4o")

# Register a subagent via the Agent facade
agent.register_subagent(SubagentConfig(
    name="researcher",
    description="Research and summarize documents",
))

# Delegate a task (sync)
result = agent.delegate_sync("researcher", "Summarize this article about AI safety")
print(result.output)
print(f"Tokens used: {result.usage.total_tokens}")
```

## Key Concepts

- **Isolation**: Each subagent is a full `Agent` with its own context and tracking
- **No nesting**: Subagents cannot spawn sub-subagents (enforced at runtime)
- **Usage aggregation**: Token usage automatically flows back to the parent's `UsageTracker`
- **Fault tolerance**: Delegation errors are captured into `SubagentResult(success=False)` rather than raised
- **Discovery**: Subagent configs can be defined in `.mamba/agents/{name}.md` markdown files

## Imports

```python
from mamba_agents import (
    # Manager
    SubagentManager,
    # Data models
    SubagentConfig,
    SubagentResult,
    DelegationHandle,
    # Exceptions
    SubagentError,
    SubagentConfigError,
    SubagentNotFoundError,
    SubagentNestingError,
    SubagentDelegationError,
    SubagentTimeoutError,
)
```

Or import directly from the subagents module:

```python
from mamba_agents.subagents import (
    SubagentManager,
    SubagentConfig,
    SubagentResult,
    DelegationHandle,
    SubagentError,
    SubagentConfigError,
    SubagentNotFoundError,
    SubagentNestingError,
    SubagentDelegationError,
    SubagentTimeoutError,
)
```
