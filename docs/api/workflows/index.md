# Workflows Module

Workflow orchestration for multi-step agent execution.

## Classes

| Class | Description |
|-------|-------------|
| [Workflow](base.md) | Abstract base class for workflows |
| [ReActWorkflow](react.md) | Built-in ReAct implementation |
| [WorkflowConfig](config.md) | Base workflow configuration |
| [WorkflowHooks](hooks.md) | Lifecycle callbacks |

## Quick Example

```python
from pydantic_agent import Agent
from pydantic_agent.workflows import ReActWorkflow, ReActConfig

agent = Agent("gpt-4o", tools=[read_file, run_bash])
workflow = ReActWorkflow(agent=agent, config=ReActConfig(max_iterations=10))

result = await workflow.run("Find bugs in the code")
print(result.output)
```

## Imports

```python
# Main exports
from pydantic_agent import (
    Workflow,
    WorkflowConfig,
    WorkflowHooks,
    WorkflowResult,
    WorkflowState,
    WorkflowStep,
)

# ReAct workflow
from pydantic_agent.workflows import (
    ReActWorkflow,
    ReActConfig,
    ReActState,
    ReActHooks,
)
```
