# ToolRegistry

Registry for organizing and managing tools.

## Quick Example

```python
from pydantic_agent.tools import ToolRegistry
from pydantic_agent.tools import read_file, write_file

registry = ToolRegistry()

# Register tools
registry.register(read_file)
registry.register(write_file)

# Get all tools
all_tools = registry.get_all()

# Use with agent
from pydantic_agent import Agent
agent = Agent("gpt-4o", tools=all_tools)
```

## API Reference

::: pydantic_agent.tools.registry.ToolRegistry
    options:
      show_root_heading: true
      show_source: true
