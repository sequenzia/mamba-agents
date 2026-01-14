# WorkflowConfig

Base configuration for workflows.

## Quick Example

```python
from pydantic_agent import WorkflowConfig

config = WorkflowConfig(
    max_steps=50,
    max_iterations=10,
    timeout_seconds=300.0,
    step_timeout_seconds=30.0,
    enable_hooks=True,
    track_state=True,
)
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_steps` | int | 50 | Maximum workflow steps |
| `max_iterations` | int | 10 | Max iterations per step |
| `timeout_seconds` | float | 300.0 | Total workflow timeout |
| `step_timeout_seconds` | float | 30.0 | Per-step timeout |
| `enable_hooks` | bool | True | Enable hook callbacks |
| `track_state` | bool | True | Track detailed state |

## API Reference

::: pydantic_agent.workflows.config.WorkflowConfig
    options:
      show_root_heading: true
      show_source: true
