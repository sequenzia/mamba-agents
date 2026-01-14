# ContextManager

Manages conversation context and compaction.

## Quick Example

```python
from pydantic_agent.context import ContextManager, CompactionConfig

manager = ContextManager(config=CompactionConfig(strategy="hybrid"))

# Add messages
manager.add_messages([
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"},
])

# Get messages
messages = manager.get_messages()

# Check state
state = manager.get_context_state()
print(f"Tokens: {state.token_count}")

# Compact if needed
if manager.should_compact():
    result = await manager.compact()
```

## API Reference

::: pydantic_agent.context.manager.ContextManager
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.context.manager.ContextState
    options:
      show_root_heading: true
      show_source: true
