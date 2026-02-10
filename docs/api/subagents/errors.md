# Subagent Errors

!!! warning "Experimental"
    The subagents subsystem is experimental. Public API may change in minor versions.

Exception classes for the subagent subsystem. All exceptions inherit from
`SubagentError`, allowing callers to catch the entire hierarchy with a single handler.

## Error Hierarchy

```
SubagentError (base)
├── SubagentConfigError(name, detail)
├── SubagentNotFoundError(config_name, available)
├── SubagentNestingError(name, parent_name)
├── SubagentDelegationError(name, task, cause)
└── SubagentTimeoutError(name, max_turns, turns_used)
```

## Quick Example

```python
from mamba_agents.subagents import (
    SubagentManager,
    SubagentConfig,
    SubagentError,
    SubagentNotFoundError,
    SubagentConfigError,
)

manager = SubagentManager(parent_agent=agent)

try:
    result = manager.delegate_sync("nonexistent", "Do something")
except SubagentNotFoundError as e:
    print(f"Not found: {e.config_name}")
    print(f"Available: {e.available}")
except SubagentError as e:
    print(f"Subagent error: {e.message}")
```

## Error Handling Philosophy

The subagent subsystem follows a fault-tolerant delegation model:

- **Most delegation errors are captured**, not raised. When a subagent fails during
  execution (model errors, timeout, unexpected exceptions), the error is recorded in
  `SubagentResult(success=False, error="...")`. Callers always receive a result object.
- **`SubagentConfigError` is the exception** -- it is re-raised because it indicates
  an unrecoverable configuration problem that the caller must address.
- **Pre-delegation errors are raised normally.** Errors that occur *before* the
  subagent starts running (e.g., config not found, nesting violation) are raised
  as exceptions since there is no `SubagentResult` to capture them in.

```python
# Typical error handling pattern
try:
    result = manager.delegate_sync("helper", "Analyze this data")
except SubagentNotFoundError:
    # Config not registered -- fix your setup
    raise
except SubagentConfigError:
    # Invalid config -- fix your config
    raise

# Execution errors are in the result, not raised
if not result.success:
    print(f"Delegation failed: {result.error}")
```

## When Raised

| Exception | Typical Trigger |
|-----------|-----------------|
| `SubagentError` | Base class; catch-all for any subagent error |
| `SubagentConfigError` | Empty subagent name, invalid frontmatter in `.md` config file, Pydantic validation failure on `SubagentConfig` fields |
| `SubagentNotFoundError` | Calling `delegate()`, `delegate_sync()`, `delegate_async()`, or `deregister()` with a name that is not registered |
| `SubagentNestingError` | A subagent (with `_is_subagent=True`) attempts to spawn another subagent via `spawn()` |
| `SubagentDelegationError` | Unrecoverable error during the delegation handoff (distinct from execution errors captured in `SubagentResult`) |
| `SubagentTimeoutError` | Subagent exceeds `max_turns` (detected via pydantic-ai's `UsageLimitExceeded`; captured into `SubagentResult.error` as `"Max turns exceeded"`) |

## Exceptions

### SubagentError

Base exception for all subagent-related errors. Catch this to handle any error from
the subagent subsystem.

```python
from mamba_agents.subagents import SubagentError

try:
    result = manager.delegate_sync("helper", "task")
except SubagentError as e:
    print(f"Something went wrong: {e.message}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable error message |

### SubagentConfigError

Raised when subagent configuration is invalid. This includes empty names, invalid
YAML frontmatter in discovery files, and Pydantic validation failures.

```python
from mamba_agents.subagents import SubagentConfig, SubagentConfigError

try:
    manager.register(SubagentConfig(name="", description="bad config"))
except SubagentConfigError as e:
    print(f"Config for '{e.name}': {e.detail}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Subagent name with the invalid configuration |
| `detail` | `str` | Description of the configuration problem |

### SubagentNotFoundError

Raised when a referenced subagent config name is not registered. The `available`
attribute lists registered config names to help with debugging typos.

```python
from mamba_agents.subagents import SubagentNotFoundError

try:
    result = manager.delegate_sync("helpre", "task")  # typo
except SubagentNotFoundError as e:
    print(f"'{e.config_name}' not found. Did you mean one of: {e.available}?")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `config_name` | `str` | Name that was not found |
| `available` | `list[str] \| None` | List of registered config names |

### SubagentNestingError

Raised when a subagent attempts to spawn a sub-subagent. The no-nesting constraint
prevents unbounded depth and resource exhaustion.

```python
from mamba_agents.subagents import SubagentNestingError

try:
    subagent_manager.delegate_sync("child-of-child", "task")
except SubagentNestingError as e:
    print(f"'{e.name}' cannot nest under '{e.parent_name}'")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Name of the subagent that attempted nesting |
| `parent_name` | `str` | Name of the parent that originally spawned this subagent |

### SubagentDelegationError

Raised when an error occurs during the delegation handoff to a subagent. The `cause`
attribute holds the underlying exception for debugging.

```python
from mamba_agents.subagents import SubagentDelegationError

try:
    result = manager.delegate_sync("helper", "task")
except SubagentDelegationError as e:
    print(f"Delegation to '{e.name}' failed for task: {e.task!r}")
    if e.cause:
        print(f"Caused by: {e.cause}")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Name of the subagent that failed |
| `task` | `str` | The task description that was being delegated |
| `cause` | `Exception \| None` | The underlying exception |

### SubagentTimeoutError

Raised when a subagent exceeds its maximum allowed turns. In practice, this is
typically detected via pydantic-ai's `UsageLimitExceeded` exception and captured
into `SubagentResult.error` as `"Max turns exceeded"` rather than raised directly.

```python
from mamba_agents.subagents import SubagentTimeoutError

try:
    result = manager.delegate_sync("helper", "very complex task")
except SubagentTimeoutError as e:
    print(f"'{e.name}' hit the {e.max_turns}-turn limit (used {e.turns_used})")
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Name of the subagent that timed out |
| `max_turns` | `int` | The maximum number of turns allowed |
| `turns_used` | `int \| None` | The number of turns actually used |

## API Reference

::: mamba_agents.subagents.errors.SubagentError
    options:
      show_root_heading: true

::: mamba_agents.subagents.errors.SubagentConfigError
    options:
      show_root_heading: true

::: mamba_agents.subagents.errors.SubagentNotFoundError
    options:
      show_root_heading: true

::: mamba_agents.subagents.errors.SubagentNestingError
    options:
      show_root_heading: true

::: mamba_agents.subagents.errors.SubagentDelegationError
    options:
      show_root_heading: true

::: mamba_agents.subagents.errors.SubagentTimeoutError
    options:
      show_root_heading: true
