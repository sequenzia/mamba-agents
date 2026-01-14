# Agent Module

The core agent module provides the main `Agent` class and related configuration.

## Classes

| Class | Description |
|-------|-------------|
| [Agent](agent.md) | Main agent class wrapping pydantic-ai |
| [AgentConfig](config.md) | Configuration for agent behavior |
| [AgentResult](result.md) | Result from agent execution |

## Quick Example

```python
from pydantic_agent import Agent, AgentConfig, AgentSettings

# Simple usage
agent = Agent("gpt-4o")
result = agent.run_sync("Hello!")

# With configuration
config = AgentConfig(
    system_prompt="You are helpful.",
    max_iterations=15,
)
agent = Agent("gpt-4o", config=config)

# With settings
settings = AgentSettings()
agent = Agent(settings=settings)
```

## Imports

```python
from pydantic_agent import Agent, AgentConfig, AgentResult
from pydantic_agent.agent import Agent, AgentConfig, AgentResult
```
