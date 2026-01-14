# ReAct Workflow Deep Dive

Master the ReAct (Reasoning and Acting) workflow pattern for complex multi-step tasks.

## What You'll Learn

- How ReAct works (Thought-Action-Observation loop)
- Configuring ReAct behavior
- Using hooks for observability
- Accessing the reasoning trace
- Handling workflow completion

## Prerequisites

- Python 3.12+
- Pydantic Agent installed
- Familiarity with basic agent concepts

## Understanding ReAct

ReAct implements an iterative reasoning loop:

```
1. THOUGHT: Agent reasons about current state
2. ACTION: Agent calls a tool
3. OBSERVATION: Tool result is recorded
4. REPEAT until final_answer is called
```

## Step 1: Basic ReAct Setup

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

# Run
result = await workflow.run("Find all TODO comments in the codebase")

print(f"Success: {result.success}")
print(f"Answer: {result.output}")
```

## Step 2: Custom Configuration

```python
config = ReActConfig(
    # Iteration limits
    max_iterations=15,
    max_steps=50,

    # Timeouts
    timeout_seconds=300.0,
    step_timeout_seconds=30.0,

    # Reasoning trace
    expose_reasoning=True,
    reasoning_prefix="Thought: ",
    action_prefix="Action: ",
    observation_prefix="Observation: ",

    # Termination
    final_answer_tool_name="final_answer",

    # Context management
    auto_compact_in_workflow=True,
    compact_threshold_ratio=0.8,

    # Behavior
    max_consecutive_thoughts=3,
    tool_retry_count=2,
)

workflow = ReActWorkflow(agent=agent, config=config)
```

## Step 3: Adding Hooks for Observability

```python
from pydantic_agent.workflows import ReActHooks

def on_thought(state, thought):
    print(f"\n[THOUGHT] {thought[:100]}...")

def on_action(state, tool_name, tool_args):
    print(f"[ACTION] {tool_name}({tool_args})")

def on_observation(state, content, is_error):
    status = "ERROR" if is_error else "OK"
    preview = content[:100] if len(content) > 100 else content
    print(f"[OBSERVATION:{status}] {preview}...")

def on_iteration(state, iteration):
    print(f"\n--- Iteration {iteration} ---")

hooks = ReActHooks(
    # ReAct-specific hooks
    on_thought=on_thought,
    on_action=on_action,
    on_observation=on_observation,

    # Workflow lifecycle hooks
    on_workflow_start=lambda s: print("Starting ReAct workflow..."),
    on_workflow_complete=lambda r: print(f"\nCompleted: {r.success}"),
    on_iteration_start=on_iteration,
)

workflow = ReActWorkflow(agent=agent, config=config, hooks=hooks)
```

## Step 4: Accessing the Reasoning Trace

```python
result = await workflow.run("Analyze the authentication module")

# Access the scratchpad
for entry in result.state.context.scratchpad:
    print(f"[{entry.entry_type.upper()}]")
    print(f"  {entry.content}")
    print(f"  Tokens: {entry.token_count}")
    print()

# Or use convenience method
print(workflow.get_reasoning_trace())
```

## Step 5: Handling Results

```python
result = await workflow.run("Debug the login flow")

if result.success:
    print(f"Answer: {result.output}")
else:
    print(f"Failed: {result.error}")
    print(f"Reason: {result.termination_reason}")

# Detailed metrics
print(f"Iterations: {result.total_iterations}")
print(f"Duration: {result.duration_seconds}s")
print(f"Steps: {result.total_steps}")

# Access ReAct-specific state
react_state = result.state.context
print(f"Total tokens: {react_state.total_tokens_used}")
print(f"Compactions: {react_state.compaction_count}")
```

## Step 6: Token and Cost Tracking

```python
# Through workflow
usage = workflow.get_token_usage()
print(f"Tokens: {usage.total_tokens}")

cost = workflow.get_cost()
print(f"Cost: ${cost:.4f}")

# Per-iteration tracking
for i, count in enumerate(result.state.context.iteration_token_counts):
    print(f"Iteration {i+1}: {count} tokens")
```

## Complete Example

```python
import asyncio
from pydantic_agent import Agent
from pydantic_agent.workflows import ReActWorkflow, ReActConfig, ReActHooks
from pydantic_agent.tools import read_file, list_directory, grep_search, run_bash


async def main():
    # Create agent with tools
    agent = Agent(
        "gpt-4o",
        tools=[read_file, list_directory, grep_search, run_bash],
        system_prompt="You are a code analyst. Be thorough but concise.",
    )

    # Configure ReAct
    config = ReActConfig(
        max_iterations=10,
        expose_reasoning=True,
        auto_compact_in_workflow=True,
    )

    # Add hooks for visibility
    hooks = ReActHooks(
        on_thought=lambda s, t: print(f"Thinking: {t[:80]}..."),
        on_action=lambda s, tool, args: print(f"Acting: {tool}"),
        on_observation=lambda s, o, e: print(f"Observed: {len(o)} chars"),
        on_workflow_complete=lambda r: print(f"Done: {r.termination_reason}"),
    )

    # Create workflow
    workflow = ReActWorkflow(agent=agent, config=config, hooks=hooks)

    # Run analysis
    print("Starting code analysis...\n")
    result = await workflow.run(
        "Analyze the project structure and identify the main entry points"
    )

    # Print results
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)

    if result.success:
        print(f"\nAnswer:\n{result.output}")
    else:
        print(f"\nFailed: {result.error}")

    print(f"\nMetrics:")
    print(f"  Iterations: {result.total_iterations}")
    print(f"  Duration: {result.duration_seconds:.1f}s")
    print(f"  Cost: ${workflow.get_cost():.4f}")

    # Show reasoning trace
    print("\nReasoning Trace:")
    print("-" * 40)
    for entry in result.state.context.scratchpad[-5:]:  # Last 5 entries
        print(f"[{entry.entry_type}] {entry.content[:100]}...")


if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced: Custom Termination

The workflow terminates when `final_answer` is called:

```python
# The agent automatically gets a final_answer tool
# When it calls final_answer(answer="..."), the workflow ends

# You can customize the tool name
config = ReActConfig(
    final_answer_tool_name="submit_response",
)
```

## Advanced: Manual Context Management

```python
# Access agent's context during workflow
messages = workflow.agent.get_messages()
state = workflow.agent.get_context_state()

# Manual compaction if needed
if workflow.agent.should_compact():
    await workflow.agent.compact()
```

## Troubleshooting

### Workflow Never Terminates

```python
# Increase max_iterations or check your task complexity
config = ReActConfig(
    max_iterations=20,  # Increase limit
    max_consecutive_thoughts=5,  # Allow more reasoning
)
```

### Too Many Tokens Used

```python
# Enable auto-compaction
config = ReActConfig(
    auto_compact_in_workflow=True,
    compact_threshold_ratio=0.7,  # Compact earlier
)
```

### Model Not Using Tools

Ensure your system prompt encourages tool use:

```python
agent = Agent(
    "gpt-4o",
    tools=[...],
    system_prompt="""You have access to tools. Use them to gather information
before answering. Don't guess - use tools to verify.""",
)
```

## Next Steps

- [Workflows Guide](../user-guide/workflows.md) - More workflow patterns
- [Workflow Patterns](../concepts/workflow-patterns.md) - Design patterns
- [ReActWorkflow API](../api/workflows/react.md) - Full reference
