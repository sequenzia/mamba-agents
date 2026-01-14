# Token Tracking

Pydantic Agent automatically tracks token usage and estimates costs across all agent runs.

## Overview

Every time you run an agent, token usage is recorded:

- **Prompt tokens** - Tokens in the input (messages + system prompt)
- **Completion tokens** - Tokens in the model's response
- **Total tokens** - Combined count
- **Request count** - Number of API calls

## Built-in Tracking

Token tracking is always enabled:

```python
from pydantic_agent import Agent

agent = Agent("gpt-4o")

# Run some queries
agent.run_sync("Hello!")
agent.run_sync("Tell me about Python")
agent.run_sync("What are decorators?")

# Get aggregate usage
usage = agent.get_usage()
print(f"Total tokens: {usage.total_tokens}")
print(f"Prompt tokens: {usage.prompt_tokens}")
print(f"Completion tokens: {usage.completion_tokens}")
print(f"Requests: {usage.request_count}")
```

## Cost Estimation

Get estimated costs based on model pricing:

```python
# Get total cost
cost = agent.get_cost()
print(f"Estimated cost: ${cost:.4f}")

# Get detailed breakdown
breakdown = agent.get_cost_breakdown()
print(f"Prompt cost: ${breakdown.prompt_cost:.4f}")
print(f"Completion cost: ${breakdown.completion_cost:.4f}")
print(f"Total cost: ${breakdown.total_cost:.4f}")
print(f"Model: {breakdown.model}")
```

### Default Pricing

Pydantic Agent includes default pricing for common models:

| Model | Input (per 1M) | Output (per 1M) |
|-------|----------------|-----------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |
| claude-3-5-sonnet | $3.00 | $15.00 |
| claude-3-opus | $15.00 | $75.00 |
| Local models | $0.00 | $0.00 |

### Custom Cost Rates

Set custom rates via settings:

```python
from pydantic_agent import AgentSettings

settings = AgentSettings(
    cost_rates={
        "my-custom-model": 0.001,  # Per 1000 tokens
    }
)
```

Or via environment:

```bash
AGENTS_COST_RATES__MY_MODEL=0.001
```

## Usage History

Get per-request usage details:

```python
history = agent.get_usage_history()

for record in history:
    print(f"Time: {record.timestamp}")
    print(f"Prompt tokens: {record.prompt_tokens}")
    print(f"Completion tokens: {record.completion_tokens}")
    print(f"Total: {record.total_tokens}")
    print(f"Model: {record.model}")
    if record.tool_name:
        print(f"Tool: {record.tool_name}")
    print("---")
```

## Token Counting

Count tokens for arbitrary text:

```python
# Count tokens in text
count = agent.get_token_count("Hello, how are you today?")
print(f"Tokens: {count}")

# Count current context
context_tokens = agent.get_token_count()  # No argument = current context
print(f"Context tokens: {context_tokens}")
```

## Reset Tracking

```python
# Reset usage tracking (keeps context)
agent.reset_tracking()

# Reset everything (context + tracking)
agent.reset_all()
```

## Standalone Token Utilities

For advanced use cases, use the token modules directly:

### TokenCounter

```python
from pydantic_agent.tokens import TokenCounter

counter = TokenCounter(encoding="cl100k_base")

# Count tokens in text
count = counter.count("Hello, world!")

# Count tokens in messages
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"},
]
count = counter.count_messages(messages)
```

### UsageTracker

```python
from pydantic_agent.tokens import UsageTracker

tracker = UsageTracker()

# Record usage
tracker.record_usage(
    input_tokens=100,
    output_tokens=50,
    model="gpt-4o",
)

# Get summary
summary = tracker.get_summary()
print(f"Total: {summary.total_tokens}")

# Get history
history = tracker.get_history()

# Reset
tracker.reset()
```

### CostEstimator

```python
from pydantic_agent.tokens import CostEstimator

estimator = CostEstimator()

# Estimate cost
cost = estimator.estimate(
    input_tokens=1000,
    output_tokens=500,
    model="gpt-4o",
)
print(f"Cost: ${cost.total_cost:.4f}")

# Get rate for a model
rate = estimator.get_rate("gpt-4o")

# Set custom rate
estimator.set_rate("my-model", 0.002)

# Get all rates
all_rates = estimator.get_all_rates()
```

## Integration with Workflows

Workflows track usage through the agent:

```python
from pydantic_agent import Agent
from pydantic_agent.workflows import ReActWorkflow

agent = Agent("gpt-4o")
workflow = ReActWorkflow(agent=agent)

result = await workflow.run("Research Python best practices")

# Access usage through workflow
usage = workflow.get_token_usage()
cost = workflow.get_cost()
print(f"Workflow cost: ${cost:.4f}")
```

## Monitoring Usage

### Logging Usage

```python
import logging

logging.basicConfig(level=logging.INFO)

agent = Agent("gpt-4o")
agent.run_sync("Hello")

# Usage is logged automatically
# INFO: Request completed: 45 tokens, $0.0001
```

### Usage Callbacks

Monitor usage in real-time with hooks:

```python
from pydantic_agent import WorkflowHooks

def log_usage(state, step):
    usage = state.context.get("usage", {})
    print(f"Step {step.step_number} used {usage.get('tokens', 0)} tokens")

hooks = WorkflowHooks(on_step_complete=log_usage)
```

## Best Practices

### 1. Monitor Costs in Production

```python
# After each run
result = agent.run_sync(query)
cost = agent.get_cost()

if cost > budget_limit:
    logger.warning(f"Cost ${cost:.4f} exceeded budget ${budget_limit}")
```

### 2. Reset Tracking Periodically

```python
# Per-session tracking
def handle_session(user_id):
    agent.reset_tracking()

    # Process requests...

    # Log session usage
    usage = agent.get_usage()
    log_user_usage(user_id, usage)
```

### 3. Use Cheaper Models for High Volume

```python
# Route based on task complexity
if is_simple_task(query):
    agent = Agent("gpt-4o-mini")  # Cheaper
else:
    agent = Agent("gpt-4o")  # More capable
```

## Next Steps

- [Context Management](context-management.md) - Manage token usage with compaction
- [Cost Estimation API](../api/tokens/cost.md) - Full reference
- [UsageTracker API](../api/tokens/tracker.md) - Detailed tracking
