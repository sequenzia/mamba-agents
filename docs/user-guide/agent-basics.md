# Agent Basics

The `Agent` class is the core of Pydantic Agent. It wraps pydantic-ai's Agent with additional features for context management, token tracking, and more.

## Creating an Agent

### Simple Creation

```python
from pydantic_agent import Agent

# Using a model string (requires OPENAI_API_KEY env var)
agent = Agent("gpt-4o")

# With a specific provider prefix
agent = Agent("openai:gpt-4o")
agent = Agent("anthropic:claude-3-5-sonnet-20241022")
```

### Using Settings

```python
from pydantic_agent import Agent, AgentSettings

# Load settings from environment, .env, config files
settings = AgentSettings()

# Use settings for model, api_key, base_url
agent = Agent(settings=settings)

# Override model but use other settings
agent = Agent("gpt-4o-mini", settings=settings)
```

### With Custom Configuration

```python
from pydantic_agent import Agent, AgentConfig, CompactionConfig

config = AgentConfig(
    system_prompt="You are a helpful assistant.",
    max_iterations=15,
    track_context=True,
    auto_compact=True,
    context=CompactionConfig(
        strategy="hybrid",
        trigger_threshold_tokens=50000,
    ),
)

agent = Agent("gpt-4o", config=config)
```

## Running the Agent

### Synchronous Execution

```python
result = agent.run_sync("What is 2 + 2?")
print(result.output)  # "4"
```

### Asynchronous Execution

```python
import asyncio

async def main():
    result = await agent.run("What is 2 + 2?")
    print(result.output)

asyncio.run(main())
```

### Streaming Responses

```python
async def stream_example():
    async for chunk in agent.run_stream("Tell me a story"):
        print(chunk, end="", flush=True)
```

## Working with Results

The `AgentResult` wraps pydantic-ai's `RunResult` with additional metadata:

```python
result = agent.run_sync("Hello!")

# Access the output
print(result.output)  # The model's response

# Access token usage for this run
usage = result.usage()
print(f"Tokens: {usage.total_tokens}")

# Get messages from this run
new_messages = result.new_messages()

# Get all messages including history
all_messages = result.all_messages()
```

## Multi-turn Conversations

Context is maintained automatically across runs:

```python
# First turn
agent.run_sync("My name is Alice")

# Second turn - context is preserved
result = agent.run_sync("What's my name?")
print(result.output)  # "Alice"

# Third turn
result = agent.run_sync("And what did I tell you first?")
print(result.output)  # References the first message
```

## Typed Outputs

Use generics to get typed responses:

```python
from pydantic import BaseModel

class Answer(BaseModel):
    value: int
    explanation: str

# Create typed agent
agent: Agent[None, Answer] = Agent("gpt-4o", output_type=Answer)

result = agent.run_sync("What is 2 + 2?")
print(result.output.value)       # 4
print(result.output.explanation) # "Two plus two equals four"
```

## System Prompts

Set the system prompt at creation or runtime:

```python
# At creation
agent = Agent(
    "gpt-4o",
    config=AgentConfig(system_prompt="You are a Python expert."),
)

# Or use the system_prompt parameter directly
agent = Agent("gpt-4o", system_prompt="You are a Python expert.")
```

## Adding Tools

Register tools for the agent to use:

```python
from pydantic_agent import Agent
from pydantic_agent.tools import read_file, run_bash

# Pass tools at creation
agent = Agent("gpt-4o", tools=[read_file, run_bash])
```

### Using the Tool Decorator

```python
@agent.tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))

@agent.tool_plain
def get_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().isoformat()
```

## Context Management

Access and manage conversation context:

```python
# Get all tracked messages
messages = agent.get_messages()

# Get context state (token count, message count)
state = agent.get_context_state()
print(f"Tokens: {state.token_count}")
print(f"Messages: {state.message_count}")

# Check if compaction is needed
if agent.should_compact():
    result = await agent.compact()
    print(f"Compacted {result.removed_count} messages")

# Clear context for new conversation
agent.clear_context()
```

## Token and Cost Tracking

Track usage across requests:

```python
# Aggregate usage
usage = agent.get_usage()
print(f"Total tokens: {usage.total_tokens}")
print(f"Prompt tokens: {usage.prompt_tokens}")
print(f"Completion tokens: {usage.completion_tokens}")
print(f"Requests: {usage.request_count}")

# Cost estimation
cost = agent.get_cost()
print(f"Estimated cost: ${cost:.4f}")

# Detailed breakdown
breakdown = agent.get_cost_breakdown()
print(f"Prompt cost: ${breakdown.prompt_cost:.4f}")
print(f"Completion cost: ${breakdown.completion_cost:.4f}")

# Per-request history
history = agent.get_usage_history()
for record in history:
    print(f"{record.timestamp}: {record.total_tokens} tokens")

# Count tokens for text
count = agent.get_token_count("Some text to count")
```

## Reset Operations

```python
# Clear context only (keeps usage tracking)
agent.clear_context()

# Reset usage tracking only (keeps context)
agent.reset_tracking()

# Reset everything
agent.reset_all()
```

## Agent Properties

```python
# Access the underlying config
print(agent.config)

# Access settings
print(agent.settings)

# Get model name
print(agent.model_name)

# Access internal managers (advanced)
context_mgr = agent.context_manager
usage_tracker = agent.usage_tracker
cost_estimator = agent.cost_estimator
token_counter = agent.token_counter
```

## Configuration Options

### AgentConfig Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `system_prompt` | str | None | System prompt for the agent |
| `max_iterations` | int | 10 | Maximum tool-calling iterations |
| `track_context` | bool | True | Enable message tracking |
| `auto_compact` | bool | True | Auto-compact when threshold reached |
| `context` | CompactionConfig | None | Custom compaction settings |
| `tokenizer` | TokenizerConfig | None | Custom tokenizer settings |

## Next Steps

- [Working with Tools](tools.md) - Built-in tools and custom tool creation
- [Context Management](context-management.md) - Deep dive into context compaction
- [Workflows](workflows.md) - Multi-step orchestration
