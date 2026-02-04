# Agent Module

The core agent module provides the main `Agent` class and related configuration.

## Classes

| Class | Description |
|-------|-------------|
| [Agent](agent.md) | Main agent class wrapping pydantic-ai |
| [AgentConfig](config.md) | Configuration for agent behavior |
| [AgentResult](result.md) | Result from agent execution |
| [Messages](messages.md) | Message querying and analytics |
| [Display](display.md) | Display rendering for analytics |

## Quick Example

```python
from mamba_agents import Agent, AgentConfig, AgentSettings

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
from mamba_agents import Agent, AgentConfig, AgentResult
from mamba_agents import MessageQuery, MessageStats, ToolCallInfo, Turn
from mamba_agents.agent.display import (
    DisplayPreset, MessageRenderer,
    RichRenderer, PlainTextRenderer, HtmlRenderer,
    get_preset, print_stats, print_timeline, print_tools,
)
```
