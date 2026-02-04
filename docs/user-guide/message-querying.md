# Message Querying & Analytics

Mamba Agents provides a query interface for filtering, analyzing, and exporting conversation histories. Access it via `agent.messages` after running any agent interaction.

## Overview

Every time you run an agent, messages are tracked automatically (when `track_context=True`, the default). The `MessageQuery` interface lets you:

- **Filter** messages by role, tool name, or content
- **Slice** into specific message ranges
- **Analyze** with statistics, tool summaries, and timelines
- **Export** to JSON, Markdown, CSV, or dict formats
- **Display** with rich formatting (see [Display Rendering](display-rendering.md))

## Quick Start

```python
from mamba_agents import Agent

agent = Agent("gpt-4o")
agent.run_sync("Hello!")
agent.run_sync("What tools do you have?")

# Access the query interface
query = agent.messages

# Get statistics
stats = query.stats()
print(stats)

# View conversation timeline
for turn in query.timeline():
    print(f"Turn {turn.index}: {turn.user_content}")

# Export as JSON
print(query.export(format="json"))
```

!!! note
    `agent.messages` returns a new `MessageQuery` instance on each access. It's stateless — all operations read from the current message history.

## Filtering Messages

Use `filter()` to search messages by role, tool name, content, or regex patterns. Multiple filters combine with AND logic.

### By Role

```python
# Get all user messages
user_msgs = query.filter(role="user")

# Get all assistant responses
assistant_msgs = query.filter(role="assistant")

# Get all tool results
tool_msgs = query.filter(role="tool")

# Get system prompts
system_msgs = query.filter(role="system")
```

### By Tool Name

```python
# Messages related to a specific tool
read_msgs = query.filter(tool_name="read_file")

# Combines assistant tool_calls and tool result messages
bash_msgs = query.filter(tool_name="run_bash")
```

### By Content

```python
# Case-insensitive text search
error_msgs = query.filter(content="error")

# Regex pattern matching
import_msgs = query.filter(content=r"import\s+\w+", regex=True)
```

### Combining Filters

```python
# Tool messages containing "success"
query.filter(role="tool", content="success")

# Assistant messages mentioning a specific tool
query.filter(role="assistant", tool_name="read_file")
```

## Slicing Messages

Access specific message ranges with Python slice semantics:

```python
# First 5 messages
first_five = query.first(n=5)

# Last 3 messages
last_three = query.last(n=3)

# Messages 10 through 19
middle = query.slice(start=10, end=20)

# All messages
all_msgs = query.all()
```

## Analytics

### Message Statistics

`stats()` returns a `MessageStats` dataclass with token and message counts:

```python
stats = query.stats()
print(f"Total messages: {stats.total_messages}")
print(f"Total tokens: {stats.total_tokens}")
print(f"Avg tokens/msg: {stats.avg_tokens_per_message:.1f}")

# Breakdown by role
for role, count in stats.messages_by_role.items():
    tokens = stats.tokens_by_role.get(role, 0)
    print(f"  {role}: {count} messages, {tokens} tokens")
```

| Field | Type | Description |
|-------|------|-------------|
| `total_messages` | `int` | Total number of messages |
| `messages_by_role` | `dict[str, int]` | Message counts by role |
| `total_tokens` | `int` | Total estimated token count |
| `tokens_by_role` | `dict[str, int]` | Token counts by role |
| `avg_tokens_per_message` | `float` | Computed average (property) |

### Tool Summary

`tool_summary()` returns a list of `ToolCallInfo` dataclasses, one per unique tool:

```python
for tool in query.tool_summary():
    print(f"{tool.tool_name}: called {tool.call_count} time(s)")
    for i, args in enumerate(tool.arguments):
        print(f"  Call {i}: {args}")
```

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Name of the tool |
| `call_count` | `int` | Number of invocations |
| `arguments` | `list[dict]` | Arguments for each call |
| `results` | `list[str]` | Result strings for each call |
| `tool_call_ids` | `list[str]` | IDs linking calls to results |

### Conversation Timeline

`timeline()` parses messages into logical `Turn` objects:

```python
for turn in query.timeline():
    if turn.user_content:
        print(f"User: {turn.user_content[:80]}")
    if turn.assistant_content:
        print(f"Assistant: {turn.assistant_content[:80]}")
    if turn.tool_interactions:
        print(f"  Tools: {len(turn.tool_interactions)} call(s)")
```

| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Zero-based position in conversation |
| `user_content` | `str \| None` | User's message content |
| `assistant_content` | `str \| None` | Assistant's text response |
| `tool_interactions` | `list[dict]` | Tool call/result pairs |
| `system_context` | `str \| None` | System prompt (first turn only) |

**Turn grouping logic:**

1. A new turn starts on each user message
2. The following assistant message is associated with that turn
3. Tool calls and results are grouped into the turn's `tool_interactions`
4. If the assistant continues after tool results, it's part of the same turn
5. System messages at the start attach to the first turn as context

## Exporting

Export messages in four formats:

```python
# JSON string (default)
json_str = query.export(format="json")

# Markdown with role headers
md_str = query.export(format="markdown")

# CSV with columns: index, role, content, tool_name, tool_call_id, token_count
csv_str = query.export(format="csv")

# List of enriched dicts with _metadata
dicts = query.export(format="dict")
```

### Export a Filtered Subset

```python
# Export only user messages
user_msgs = query.filter(role="user")
json_str = query.export(format="json", messages=user_msgs)
```

### JSON with Metadata

```python
# Include index and token_count per message
json_str = query.export(format="json", include_metadata=True)
```

## Display

The query interface includes built-in display methods that render analytics as formatted output. See [Display Rendering](display-rendering.md) for full details.

```python
# Quick display to terminal
query.print_stats()
query.print_timeline()
query.print_tools()

# With preset and format options
query.print_stats(preset="compact", format="plain")
query.print_timeline(preset="verbose", limit=5)
```

## Working Without Context Tracking

When `track_context=False`, `agent.messages` returns a `MessageQuery` over an empty list. All methods work but return empty results:

```python
agent = Agent("gpt-4o", config=AgentConfig(track_context=False))
agent.run_sync("Hello!")

query = agent.messages
print(query.stats().total_messages)  # 0
print(query.timeline())             # []
```

## Best Practices

1. **Use `agent.messages` for convenience** — it creates a fresh `MessageQuery` each time, automatically connected to the agent's token counter
2. **Filter before exporting** — narrow down to relevant messages before exporting large conversations
3. **Use `timeline()` for turn-by-turn analysis** — it handles the complexity of grouping tool calls with their parent turns
4. **Use presets for display** — `"compact"` for quick checks, `"verbose"` for debugging

## Next Steps

- [Display Rendering](display-rendering.md) — Rich, plain text, and HTML output formatting
- [Context Management](context-management.md) — How messages are tracked and compacted
- [Token Tracking](token-tracking.md) — Token counting and cost estimation
