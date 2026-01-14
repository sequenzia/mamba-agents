# Workflows

Workflows provide orchestration patterns for multi-step agent execution. The built-in ReAct workflow implements the Reasoning and Acting paradigm.

## Overview

Workflows extend agent capabilities beyond single-turn interactions:

- **Multi-step execution** - Chain multiple agent calls
- **Iterative refinement** - Loop until goals are achieved
- **Structured reasoning** - Thought-Action-Observation patterns
- **State tracking** - Monitor progress and intermediate results
- **Hooks** - Observability callbacks for monitoring

## ReAct Workflow

The ReAct (Reasoning and Acting) workflow implements an iterative loop:

1. **Thought** - Agent reasons about the current state
2. **Action** - Agent calls a tool
3. **Observation** - Tool result is added to context
4. **Repeat** until `final_answer` is called

### Basic Usage

```python
from pydantic_agent import Agent
from pydantic_agent.workflows import ReActWorkflow, ReActConfig
from pydantic_agent.tools import read_file, run_bash, grep_search

# Create agent with tools
agent = Agent(
    "gpt-4o",
    tools=[read_file, run_bash, grep_search],
)

# Create workflow
workflow = ReActWorkflow(agent=agent)

# Run the workflow
result = await workflow.run("Find and explain the bug in src/utils.py")

print(f"Success: {result.success}")
print(f"Answer: {result.output}")
print(f"Iterations: {result.total_iterations}")
```

### Synchronous Usage

```python
result = workflow.run_sync("Analyze the codebase structure")
```

### Accessing the Reasoning Trace

```python
result = await workflow.run("Research Python decorators")

# Get scratchpad entries
for entry in result.state.context.scratchpad:
    print(f"[{entry.entry_type.upper()}] {entry.content}")

# Or use convenience method
print(workflow.get_reasoning_trace())
```

### ReAct Configuration

```python
from pydantic_agent.workflows import ReActConfig

config = ReActConfig(
    # Iteration limits
    max_iterations=15,
    max_steps=50,

    # Timeouts
    timeout_seconds=300.0,
    step_timeout_seconds=30.0,

    # Reasoning visibility
    expose_reasoning=True,
    reasoning_prefix="Thought: ",
    action_prefix="Action: ",
    observation_prefix="Observation: ",

    # Termination
    final_answer_tool_name="final_answer",

    # Context management
    auto_compact_in_workflow=True,
    compact_threshold_ratio=0.8,

    # Behavior tuning
    max_consecutive_thoughts=3,  # Force action after 3 thoughts
    tool_retry_count=2,
)

workflow = ReActWorkflow(agent=agent, config=config)
```

### ReAct Hooks

Monitor workflow execution with hooks:

```python
from pydantic_agent.workflows import ReActHooks

def on_thought(state, thought):
    print(f"Thinking: {thought[:100]}...")

def on_action(state, tool_name, tool_args):
    print(f"Acting: {tool_name}({tool_args})")

def on_observation(state, content, is_error):
    status = "ERROR" if is_error else "OK"
    print(f"Observed [{status}]: {content[:100]}...")

hooks = ReActHooks(
    # ReAct-specific hooks
    on_thought=on_thought,
    on_action=on_action,
    on_observation=on_observation,
    on_compaction=lambda r: print(f"Compacted: {r.removed_count} messages"),

    # Base workflow hooks
    on_workflow_start=lambda s: print("Starting..."),
    on_workflow_complete=lambda r: print(f"Done: {r.success}"),
    on_iteration_start=lambda s, i: print(f"Iteration {i}"),
)

workflow = ReActWorkflow(agent=agent, hooks=hooks)
```

## Custom Workflows

Create custom workflows by extending the `Workflow` base class:

```python
from pydantic_agent import Agent, Workflow, WorkflowConfig, WorkflowState, WorkflowResult

class PlanExecuteWorkflow(Workflow[None, str, dict]):
    """A Plan-and-Execute workflow pattern."""

    def __init__(
        self,
        planner: Agent,
        executor: Agent,
        config: WorkflowConfig | None = None,
    ):
        super().__init__(config=config)
        self.planner = planner
        self.executor = executor

    @property
    def name(self) -> str:
        return "plan_execute"

    def _create_initial_state(self, prompt: str) -> WorkflowState[dict]:
        return WorkflowState(context={
            "prompt": prompt,
            "plan": [],
            "results": [],
        })

    async def _execute(
        self,
        prompt: str,
        state: WorkflowState[dict],
        deps=None,
    ) -> str:
        # Step 1: Create a plan
        plan_result = await self.planner.run(
            f"Create a step-by-step plan to: {prompt}"
        )
        state.context["plan"] = plan_result.output.split("\n")

        # Step 2: Execute each step
        for i, step in enumerate(state.context["plan"]):
            if not step.strip():
                continue

            state.iteration_count += 1
            if state.iteration_count > self._config.max_iterations:
                break

            result = await self.executor.run(step)
            state.context["results"].append(result.output)

        # Step 3: Synthesize results
        synthesis = await self.planner.run(
            f"Summarize these results: {state.context['results']}"
        )

        return synthesis.output
```

### Using Custom Workflows

```python
planner = Agent("gpt-4o", system_prompt="You create detailed plans.")
executor = Agent("gpt-4o", tools=[read_file, run_bash])

workflow = PlanExecuteWorkflow(
    planner=planner,
    executor=executor,
    config=WorkflowConfig(max_iterations=20),
)

result = await workflow.run("Refactor the authentication module")
```

## Workflow Configuration

### WorkflowConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_steps` | int | 50 | Maximum workflow steps |
| `max_iterations` | int | 10 | Maximum iterations per step |
| `timeout_seconds` | float | 300.0 | Total workflow timeout |
| `step_timeout_seconds` | float | 30.0 | Per-step timeout |
| `enable_hooks` | bool | True | Enable hook callbacks |
| `track_state` | bool | True | Track detailed state history |

### ReActConfig Additional Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `expose_reasoning` | bool | True | Include thoughts in output |
| `reasoning_prefix` | str | `"Thought: "` | Prefix for thoughts |
| `action_prefix` | str | `"Action: "` | Prefix for actions |
| `observation_prefix` | str | `"Observation: "` | Prefix for observations |
| `final_answer_tool_name` | str | `"final_answer"` | Termination tool |
| `auto_compact_in_workflow` | bool | True | Auto-compact context |
| `compact_threshold_ratio` | float | 0.8 | Compaction trigger ratio |
| `max_consecutive_thoughts` | int | 3 | Max thoughts before action |
| `tool_retry_count` | int | 2 | Retries for failed tools |

## Workflow Hooks

All 8 base hooks:

```python
from pydantic_agent import WorkflowHooks

hooks = WorkflowHooks(
    # Workflow lifecycle
    on_workflow_start=lambda state: ...,
    on_workflow_complete=lambda result: ...,
    on_workflow_error=lambda state, error: ...,

    # Step lifecycle
    on_step_start=lambda state, step_num, step_type: ...,
    on_step_complete=lambda state, step: ...,
    on_step_error=lambda state, step, error: ...,

    # Iteration lifecycle
    on_iteration_start=lambda state, iteration: ...,
    on_iteration_complete=lambda state, iteration: ...,
)
```

## Workflow Results

```python
result = await workflow.run("task")

# Check success
if result.success:
    print(f"Output: {result.output}")
else:
    print(f"Error: {result.error}")

# Access state
print(f"Steps: {result.total_steps}")
print(f"Iterations: {result.total_iterations}")
print(f"Duration: {result.duration_seconds}s")
print(f"Termination: {result.termination_reason}")

# Access detailed state
state = result.state
for step in state.steps:
    print(f"Step {step.step_number}: {step.description}")
    print(f"  Duration: {step.duration_seconds}s")
    print(f"  Success: {step.success}")
```

## Best Practices

### 1. Set Appropriate Limits

```python
config = ReActConfig(
    max_iterations=10,  # Prevent infinite loops
    timeout_seconds=120.0,  # Overall timeout
    step_timeout_seconds=20.0,  # Per-step timeout
)
```

### 2. Use Hooks for Monitoring

```python
def monitor_cost(state, step):
    # Track cost per step
    logger.info(f"Step {step.step_number} cost: ${step.metadata.get('cost', 0):.4f}")

hooks = WorkflowHooks(on_step_complete=monitor_cost)
```

### 3. Handle Failures Gracefully

```python
result = await workflow.run("complex task")

if not result.success:
    if result.termination_reason == "max_iterations":
        # Try with more iterations or simpler task
        pass
    elif result.termination_reason == "timeout":
        # Task too complex
        pass
```

## Next Steps

- [ReAct Tutorial](../tutorials/react-workflow.md) - Deep dive into ReAct
- [Workflow Patterns](../concepts/workflow-patterns.md) - Design patterns
- [ReActWorkflow API](../api/workflows/react.md) - Full reference
