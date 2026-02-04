# Messages

Message querying, filtering, analytics, and export for conversation histories.

## Quick Example

```python
from mamba_agents import Agent

agent = Agent("gpt-4o")
agent.run_sync("Hello!")
agent.run_sync("What tools do you have?")

# Access the query interface
query = agent.messages

# Filter messages
user_msgs = query.filter(role="user")
tool_msgs = query.filter(tool_name="read_file")

# Get analytics
stats = query.stats()
print(f"Total: {stats.total_messages} messages, {stats.total_tokens} tokens")

# View timeline
for turn in query.timeline():
    print(f"Turn {turn.index}: {turn.user_content}")

# Export
json_str = query.export(format="json")
```

## Classes

| Class | Description |
|-------|-------------|
| `MessageQuery` | Stateless query interface for filtering and analyzing messages |
| `MessageStats` | Token and message count statistics |
| `ToolCallInfo` | Summary of a tool's usage across a conversation |
| `Turn` | A logical conversation turn grouping related messages |

## Imports

```python
from mamba_agents import MessageQuery, MessageStats, ToolCallInfo, Turn
from mamba_agents.agent.messages import MessageQuery, MessageStats, ToolCallInfo, Turn
```

## API Reference

### MessageQuery

::: mamba_agents.agent.messages.MessageQuery
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - filter
        - slice
        - first
        - last
        - all
        - stats
        - tool_summary
        - timeline
        - export
        - print_stats
        - print_timeline
        - print_tools

### MessageStats

::: mamba_agents.agent.messages.MessageStats
    options:
      show_root_heading: true
      show_source: true
      members:
        - total_messages
        - messages_by_role
        - total_tokens
        - tokens_by_role
        - avg_tokens_per_message

### ToolCallInfo

::: mamba_agents.agent.messages.ToolCallInfo
    options:
      show_root_heading: true
      show_source: true
      members:
        - tool_name
        - call_count
        - arguments
        - results
        - tool_call_ids

### Turn

::: mamba_agents.agent.messages.Turn
    options:
      show_root_heading: true
      show_source: true
      members:
        - index
        - user_content
        - assistant_content
        - tool_interactions
        - system_context
