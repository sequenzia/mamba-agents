# AgentResult

Result from agent execution, wrapping pydantic-ai's RunResult.

## Quick Example

```python
from pydantic_agent import Agent

agent = Agent("gpt-4o")
result = await agent.run("What is 2 + 2?")

# Access output
print(result.output)  # "4"

# Access usage
usage = result.usage()
print(f"Tokens: {usage.total_tokens}")

# Access messages
new_msgs = result.new_messages()
all_msgs = result.all_messages()
```

## Properties and Methods

| Member | Type | Description |
|--------|------|-------------|
| `output` | OutputT | The typed output from the agent |
| `data` | OutputT | Alias for output |
| `usage()` | TokenUsage | Token usage for this run |
| `new_messages()` | list | Messages from this run only |
| `all_messages()` | list | Complete message history |

## API Reference

::: pydantic_agent.agent.result.AgentResult
    options:
      show_root_heading: true
      show_source: true
