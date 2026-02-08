# Configuration

!!! warning "Experimental"
    The subagents subsystem is experimental. Public API may change in minor versions.

Data models for subagent configuration, results, and async delegation handles.

## SubagentConfig

Defines how a subagent is created and what capabilities it has. This is a Pydantic
`BaseModel`, so all fields are validated at construction time.

```python
from mamba_agents.subagents import SubagentConfig

config = SubagentConfig(
    name="researcher",
    description="Research and summarize documents",
    model="gpt-4o",
    tools=["read_file", "grep_search"],
    system_prompt="You are a research assistant.",
    max_turns=30,
)
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | *required* | Unique subagent identifier |
| `description` | `str` | *required* | When to delegate to this subagent |
| `model` | `str \| None` | `None` | Model override (`None` = inherit from parent) |
| `tools` | `list[str \| Callable] \| None` | `None` | Explicit tool allowlist |
| `disallowed_tools` | `list[str] \| None` | `None` | Tools to deny even if in allowlist |
| `system_prompt` | `str \| TemplateConfig \| None` | `None` | Custom system prompt or template |
| `skills` | `list[str] \| None` | `None` | Skills to pre-load at startup |
| `max_turns` | `int` | `50` | Maximum conversation turns before termination |
| `config` | `AgentConfig \| None` | `None` | Full agent config override |

!!! danger "Tool Isolation: `tools=None` means NO tools"
    Unlike some frameworks where `None` means "inherit everything", setting
    `tools=None` (the default) gives the subagent **no tools at all**. This is a
    deliberate isolation design -- subagents start with a clean slate.

    To grant tools, you must explicitly list them:

    ```python
    # No tools (default) -- subagent can only respond with text
    SubagentConfig(name="writer", description="...", tools=None)

    # Specific tools from parent
    SubagentConfig(name="reader", description="...", tools=["read_file", "list_directory"])

    # Empty list -- also no tools (explicit)
    SubagentConfig(name="thinker", description="...", tools=[])
    ```

    Tool names in the `tools` list are resolved against the parent agent's registered
    tools. You can also pass callable functions directly.

### Model Inheritance

When `model` is `None`, the subagent inherits the parent agent's model:

```python
parent = Agent("gpt-4o")

# This subagent will use gpt-4o (inherited)
config = SubagentConfig(name="helper", description="...", model=None)

# This subagent will use gpt-4o-mini (overridden)
config = SubagentConfig(name="cheap-helper", description="...", model="gpt-4o-mini")
```

### System Prompt

The system prompt can be a plain string or a `TemplateConfig` for Jinja2 templates.
When loading from a markdown file, the body below the YAML frontmatter becomes the
system prompt:

```python
# Plain string
SubagentConfig(name="helper", description="...", system_prompt="You are helpful.")

# Template config
from mamba_agents.prompts import TemplateConfig
SubagentConfig(
    name="helper",
    description="...",
    system_prompt=TemplateConfig(name="assistant", version="v1"),
)
```

### Skill Pre-loading

Skills listed in the `skills` field are loaded from the parent's `SkillRegistry`
and injected into the subagent's system prompt at spawn time:

```python
SubagentConfig(
    name="analyzer",
    description="Analyze code with specific skills",
    skills=["code-review", "security-audit"],
)
```

!!! note
    Referenced skills must already be registered in the parent agent's `SkillManager`.
    A `SkillNotFoundError` is raised at spawn time if a skill is missing.

---

## SubagentResult

Returned from all delegation methods. Contains the subagent's output, token usage,
timing, and success/failure status.

```python
result = await manager.delegate("helper", "Summarize this")

if result.success:
    print(result.output)
    print(f"Completed in {result.duration:.2f}s using {result.usage.total_tokens} tokens")
else:
    print(f"Delegation failed: {result.error}")
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `output` | `str` | Subagent's final response text (empty string on failure) |
| `agent_result` | `AgentResult` | Full pydantic-ai result wrapper |
| `usage` | `TokenUsage` | Token usage for this delegation |
| `duration` | `float` | Execution time in seconds |
| `subagent_name` | `str` | Name of the subagent that handled the task |
| `success` | `bool` | Whether delegation completed successfully |
| `error` | `str \| None` | Error message if `success` is `False`, `None` otherwise |

!!! info "Error Capture"
    Most delegation errors are captured into `SubagentResult(success=False, error="...")`
    rather than raised as exceptions. This makes delegation fault-tolerant -- callers
    always get a result object and can check `result.success`. Only `SubagentConfigError`
    is re-raised because it indicates an unrecoverable configuration problem.

---

## DelegationHandle

Returned by `delegate_async()` for fire-and-forget delegation. Wraps an `asyncio.Task`
with a convenient API for checking status, awaiting results, and cancelling.

```python
handle = await manager.delegate_async("helper", "Long analysis task")

# Check without blocking
if not handle.is_complete:
    print(f"Subagent '{handle.subagent_name}' is still working on: {handle.task}")

# Await when ready
result = await handle.result()

# Or cancel
handle.cancel()
```

### Fields and Properties

| Member | Type | Description |
|--------|------|-------------|
| `subagent_name` | `str` | Name of the subagent handling the task |
| `task` | `str` | The task description that was delegated |
| `is_complete` | `bool` (property) | `True` if done or no task assigned |
| `result()` | `async -> SubagentResult` | Await the delegation result |
| `cancel()` | `-> None` | Cancel the running delegation (no-op if already done) |

!!! note
    When using `delegate_async()` through the `SubagentManager`, the returned handle
    is a `_UsageTrackingHandle` that automatically aggregates token usage to the
    parent's `UsageTracker` when `result()` is awaited.

---

## API Reference

::: mamba_agents.subagents.config.SubagentConfig
    options:
      show_root_heading: true
      show_source: true

::: mamba_agents.subagents.config.SubagentResult
    options:
      show_root_heading: true
      show_source: true

::: mamba_agents.subagents.config.DelegationHandle
    options:
      show_root_heading: true
      show_source: true
