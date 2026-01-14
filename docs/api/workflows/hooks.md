# WorkflowHooks

Lifecycle callbacks for workflow observability.

## Quick Example

```python
from pydantic_agent import WorkflowHooks

def log_step(state, step):
    print(f"Step {step.step_number}: {step.description}")

hooks = WorkflowHooks(
    on_workflow_start=lambda s: print("Starting..."),
    on_workflow_complete=lambda r: print(f"Done: {r.success}"),
    on_workflow_error=lambda s, e: print(f"Error: {e}"),
    on_step_start=lambda s, n, t: print(f"Step {n}"),
    on_step_complete=log_step,
    on_step_error=lambda s, step, e: print(f"Step failed: {e}"),
    on_iteration_start=lambda s, i: print(f"Iteration {i}"),
    on_iteration_complete=lambda s, i: print(f"Iteration {i} done"),
)
```

## Available Hooks

| Hook | Parameters | Description |
|------|------------|-------------|
| `on_workflow_start` | (state) | Workflow begins |
| `on_workflow_complete` | (result) | Workflow completes |
| `on_workflow_error` | (state, error) | Workflow fails |
| `on_step_start` | (state, step_num, step_type) | Step starts |
| `on_step_complete` | (state, step) | Step completes |
| `on_step_error` | (state, step, error) | Step fails |
| `on_iteration_start` | (state, iteration) | Iteration starts |
| `on_iteration_complete` | (state, iteration) | Iteration ends |

## API Reference

::: pydantic_agent.workflows.hooks.WorkflowHooks
    options:
      show_root_heading: true
      show_source: true
