# Context Management

Pydantic Agent automatically tracks conversation context and provides strategies to manage long conversations.

## Overview

As conversations grow, the context window can exceed model limits. The context management system:

1. **Tracks messages** across agent runs
2. **Counts tokens** to monitor usage
3. **Compacts context** when thresholds are reached
4. **Preserves important** messages during compaction

## Built-in Agent Context

Context tracking is enabled by default:

```python
from pydantic_agent import Agent

agent = Agent("gpt-4o")

# Run multiple turns - context is maintained automatically
agent.run_sync("My name is Alice")
agent.run_sync("I'm working on a Python project")
result = agent.run_sync("What's my name and what am I working on?")
# Agent remembers both pieces of information
```

### Checking Context State

```python
# Get all tracked messages
messages = agent.get_messages()
print(f"Total messages: {len(messages)}")

# Get context state
state = agent.get_context_state()
print(f"Token count: {state.token_count}")
print(f"Message count: {state.message_count}")
print(f"Compaction history: {len(state.compaction_history)}")
```

### Manual Compaction

```python
# Check if compaction is needed
if agent.should_compact():
    result = await agent.compact()
    print(f"Removed {result.removed_count} messages")
    print(f"Tokens before: {result.tokens_before}")
    print(f"Tokens after: {result.tokens_after}")
```

### Auto-compaction

By default, context is automatically compacted when thresholds are reached:

```python
from pydantic_agent import Agent, AgentConfig, CompactionConfig

config = AgentConfig(
    auto_compact=True,  # Enabled by default
    context=CompactionConfig(
        trigger_threshold_tokens=100000,  # Compact at 100k tokens
        target_tokens=80000,              # Target 80k after compaction
    ),
)

agent = Agent("gpt-4o", config=config)

# Compaction happens automatically when threshold is reached
for i in range(100):
    agent.run_sync(f"Message {i}: Tell me about topic {i}")
```

### Disabling Context Tracking

```python
config = AgentConfig(track_context=False)
agent = Agent("gpt-4o", config=config)

# No context is maintained between runs
```

## Compaction Strategies

Five strategies are available for compacting context:

### 1. Sliding Window

Removes oldest messages beyond a threshold:

```python
config = CompactionConfig(
    strategy="sliding_window",
    preserve_recent_turns=10,  # Keep last 10 exchanges
)
```

**Best for:** Simple conversations where recent context is most important.

### 2. Summarize Older

Uses an LLM to summarize older messages:

```python
config = CompactionConfig(
    strategy="summarize_older",
    preserve_recent_turns=5,
    summarization_model="gpt-4o-mini",  # Model for summarization
)
```

**Best for:** Long conversations where historical context matters.

### 3. Selective Pruning

Removes completed tool call/result pairs:

```python
config = CompactionConfig(
    strategy="selective_pruning",
)
```

**Best for:** Tool-heavy workflows where tool results are no longer needed.

### 4. Importance Scoring

Uses LLM to score and prune least important messages:

```python
config = CompactionConfig(
    strategy="importance_scoring",
    preserve_recent_turns=3,
)
```

**Best for:** Complex conversations with varying importance levels.

### 5. Hybrid

Combines multiple strategies in sequence:

```python
config = CompactionConfig(
    strategy="hybrid",
    preserve_recent_turns=5,
)
```

**Best for:** General-purpose use with good balance.

## Configuration Reference

### CompactionConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `strategy` | str | `"sliding_window"` | Compaction strategy |
| `trigger_threshold_tokens` | int | `100000` | Token count triggering compaction |
| `target_tokens` | int | `80000` | Target tokens after compaction |
| `preserve_recent_turns` | int | `10` | Recent turns to always preserve |
| `preserve_system_prompt` | bool | `True` | Always keep system prompt |
| `summarization_model` | str | `"same"` | Model for summarization (`"same"` uses current) |

## Standalone Context Manager

For advanced use cases, use ContextManager directly:

```python
from pydantic_agent.context import ContextManager, CompactionConfig

# Create manager with config
config = CompactionConfig(
    strategy="hybrid",
    trigger_threshold_tokens=50000,
    target_tokens=40000,
)
manager = ContextManager(config=config)

# Add messages
manager.add_messages([
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"},
])

# Set system prompt
manager.set_system_prompt("You are helpful.")

# Get messages
messages = manager.get_messages()

# Check and compact
if manager.should_compact():
    result = await manager.compact()

# Get state
state = manager.get_context_state()

# Clear all
manager.clear()
```

## Working with Message History

### Message Format

Messages follow the pydantic-ai format:

```python
messages = agent.get_messages()

for msg in messages:
    print(f"Role: {msg['role']}")
    print(f"Content: {msg['content']}")
    if 'tool_calls' in msg:
        print(f"Tool calls: {msg['tool_calls']}")
```

### Preserving Specific Messages

The system prompt is always preserved:

```python
config = CompactionConfig(
    preserve_system_prompt=True,  # Default
    preserve_recent_turns=5,
)
```

## Best Practices

### 1. Choose the Right Strategy

| Use Case | Recommended Strategy |
|----------|---------------------|
| Chat applications | `sliding_window` |
| Research/analysis | `summarize_older` |
| Tool-heavy workflows | `selective_pruning` or `hybrid` |
| Long-running agents | `hybrid` |

### 2. Set Appropriate Thresholds

Consider your model's context window:

| Model | Context Window | Suggested Threshold |
|-------|---------------|---------------------|
| GPT-4o | 128k | 100k |
| GPT-4o-mini | 128k | 100k |
| Claude 3.5 | 200k | 150k |
| Llama 3.2 | 8k-128k | 75% of limit |

### 3. Monitor Compaction

```python
state = agent.get_context_state()
for compaction in state.compaction_history:
    print(f"Strategy: {compaction.strategy}")
    print(f"Removed: {compaction.removed_count}")
```

## Next Steps

- [Token Tracking](token-tracking.md) - Monitor token usage
- [Compaction Strategies Explained](../concepts/compaction-strategies.md) - Deep dive
- [ContextManager API](../api/context/manager.md) - Full reference
