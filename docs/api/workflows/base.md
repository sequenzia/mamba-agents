# Workflow Base Classes

Base classes for creating custom workflows.

## Classes

### Workflow

Abstract base class for workflow implementations.

```python
from pydantic_agent import Workflow, WorkflowConfig, WorkflowState

class MyWorkflow(Workflow[None, str, dict]):
    @property
    def name(self) -> str:
        return "my_workflow"

    def _create_initial_state(self, prompt: str) -> WorkflowState[dict]:
        return WorkflowState(context={"prompt": prompt})

    async def _execute(self, prompt, state, deps=None) -> str:
        # Implementation
        return "result"
```

### WorkflowState

Tracks workflow progress and execution history.

### WorkflowStep

Represents a single step in workflow execution.

### WorkflowResult

Result of workflow execution.

## API Reference

::: pydantic_agent.workflows.base.Workflow
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.workflows.base.WorkflowState
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.workflows.base.WorkflowStep
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.workflows.base.WorkflowResult
    options:
      show_root_heading: true
      show_source: true
