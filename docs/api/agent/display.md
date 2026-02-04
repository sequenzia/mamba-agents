# Display Module

Formatted rendering of message analytics data with Rich, plain text, and HTML output.

## Quick Example

```python
from mamba_agents import Agent

agent = Agent("gpt-4o")
agent.run_sync("Hello!")

# Via the query interface (easiest)
agent.messages.print_stats()
agent.messages.print_timeline()
agent.messages.print_tools()

# Standalone functions
from mamba_agents.agent.display import print_stats, print_timeline, print_tools

stats = agent.messages.stats()
print_stats(stats, preset="compact", format="rich")
```

## Classes

| Class | Description | Reference |
|-------|-------------|-----------|
| `MessageRenderer` | ABC for format-specific renderers | [Renderers](display-renderers.md) |
| `RichRenderer` | Rich Console output (tables, panels) | [Renderers](display-renderers.md) |
| `PlainTextRenderer` | ASCII text output (aligned columns) | [Renderers](display-renderers.md) |
| `HtmlRenderer` | HTML output (Jupyter notebooks) | [Renderers](display-renderers.md) |
| `DisplayPreset` | Controls display detail level | [Presets & Functions](display-presets.md) |

## Functions

| Function | Description | Reference |
|----------|-------------|-----------|
| `get_preset()` | Retrieve named preset with overrides | [Presets & Functions](display-presets.md) |
| `print_stats()` | Render message statistics | [Presets & Functions](display-presets.md) |
| `print_timeline()` | Render conversation timeline | [Presets & Functions](display-presets.md) |
| `print_tools()` | Render tool usage summary | [Presets & Functions](display-presets.md) |

## Named Presets

| Preset | Description |
|--------|-------------|
| `COMPACT` | Minimal output: counts only, short truncation |
| `DETAILED` | Balanced output: full tables, moderate truncation *(default)* |
| `VERBOSE` | Maximum output: expanded content, full tool details |

## Imports

```python
# Top-level convenience imports
from mamba_agents import (
    DisplayPreset, MessageRenderer,
    RichRenderer, PlainTextRenderer, HtmlRenderer,
    print_stats, print_timeline, print_tools,
)

# Direct module imports
from mamba_agents.agent.display import (
    DisplayPreset, MessageRenderer,
    RichRenderer, PlainTextRenderer, HtmlRenderer,
    get_preset, COMPACT, DETAILED, VERBOSE,
    print_stats, print_timeline, print_tools,
)
```
