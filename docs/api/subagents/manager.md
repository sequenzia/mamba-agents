# SubagentManager

!!! warning "Experimental"
    The subagents subsystem is experimental. Public API may change in minor versions.

Main facade for the subagent subsystem. Composes spawning, delegation, discovery,
and usage tracking behind a single unified API.

## Quick Example

```python
from mamba_agents.subagents import SubagentManager, SubagentConfig

manager = SubagentManager(parent_agent=agent)
manager.register(SubagentConfig(name="helper", description="A helper agent"))
result = await manager.delegate("helper", "Summarize this document")
print(result.output)
```

## Using via Agent Facade

Most users interact with the `SubagentManager` through the `Agent` facade methods
rather than constructing the manager directly:

```python
from mamba_agents import Agent, SubagentConfig

agent = Agent("gpt-4o")

# Register subagents
agent.register_subagent(SubagentConfig(
    name="writer",
    description="Write polished content from rough notes",
    system_prompt="You are a professional technical writer.",
))

# Delegate tasks
result = agent.delegate_sync("writer", "Polish these release notes: ...")
print(result.output)

# List registered subagents
for config in agent.list_subagents():
    print(f"  {config.name}: {config.description}")
```

!!! tip "Lazy Initialization"
    The `Agent.subagent_manager` property creates the `SubagentManager` on first
    access. To check if it has been initialized without triggering creation, use
    `agent._subagent_manager is not None`.

## Delegation Patterns

### Async Delegation (await result)

```python
result = await manager.delegate("helper", "Analyze this data")
if result.success:
    print(result.output)
else:
    print(f"Failed: {result.error}")
```

### Sync Delegation (blocking)

```python
result = manager.delegate_sync("helper", "Analyze this data")
print(result.output)
```

### Fire-and-Forget (background task)

```python
handle = await manager.delegate_async("helper", "Long-running analysis")

# Do other work...
print(f"Still running: {not handle.is_complete}")

# Await when ready
result = await handle.result()
print(result.output)

# Or cancel if no longer needed
handle.cancel()
```

### Dynamic Subagents (one-off, unregistered)

```python
config = SubagentConfig(
    name="ad-hoc",
    description="Temporary subagent for a one-off task",
    model="gpt-4o-mini",
)
result = await manager.spawn_dynamic(config, "Quick classification task")
```

## Passing Context

Delegation methods accept additional keyword arguments that are forwarded to the
underlying delegation function:

```python
# Pass a context string (appended to the task prompt)
result = await manager.delegate(
    "helper",
    "Summarize the following",
    context="The full text of the document goes here...",
)

# Pass conversation history as context messages
result = await manager.delegate(
    "helper",
    "Continue this conversation",
    context_messages=agent.get_messages(),
)
```

## Discovery

Subagent configs can be auto-discovered from markdown files:

```python
# Discover from .mamba/agents/ and ~/.mamba/agents/
newly_found = manager.discover()
print(f"Found {len(newly_found)} new subagent configs")
```

Each `.md` file in the discovery directories uses YAML frontmatter:

```markdown title=".mamba/agents/researcher.md"
---
name: researcher
description: Research and gather information
model: gpt-4o
tools: [read_file, grep_search]
skills: [web-search]
max-turns: 30
---

You are a research assistant. Focus on finding accurate, well-sourced information.
```

!!! note
    Discovery does not overwrite existing configs. If a config named `researcher`
    is already registered, the discovered file is skipped.

## Usage Tracking

Token usage from all delegations is automatically aggregated to the parent agent's
`UsageTracker` and tracked per-subagent within the manager:

```python
# Per-subagent breakdown
breakdown = manager.get_usage_breakdown()
for name, usage in breakdown.items():
    print(f"{name}: {usage.total_tokens} tokens across {usage.request_count} requests")
```

## API Reference

::: mamba_agents.subagents.manager.SubagentManager
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - register
        - deregister
        - get
        - list
        - delegate
        - delegate_sync
        - delegate_async
        - spawn_dynamic
        - discover
        - get_active_delegations
        - get_usage_breakdown
