# Display Rendering

Mamba Agents provides formatted rendering for message analytics data with three output formats: Rich (terminal), Plain Text (ASCII), and HTML (Jupyter notebooks).

## Overview

The display system renders three types of analytics data:

- **Stats** — Message and token count tables
- **Timeline** — Turn-by-turn conversation view
- **Tools** — Tool usage summary tables

Each can be rendered in three formats with three detail levels (presets).

## Quick Start

The easiest way to display analytics is through the `MessageQuery` methods:

```python
from mamba_agents import Agent

agent = Agent("gpt-4o")
agent.run_sync("Hello!")

# Display via agent.messages
agent.messages.print_stats()      # Rich table to terminal
agent.messages.print_timeline()   # Rich panels to terminal
agent.messages.print_tools()      # Rich table to terminal
```

Or use standalone functions directly:

```python
from mamba_agents.agent.display import print_stats, print_timeline, print_tools

stats = agent.messages.stats()
turns = agent.messages.timeline()
tools = agent.messages.tool_summary()

print_stats(stats)
print_timeline(turns)
print_tools(tools)
```

## Output Formats

### Rich (Terminal)

The default format. Uses Rich tables, panels, and styled text with color and formatting.

```python
agent.messages.print_stats(format="rich")
```

### Plain Text (ASCII)

Clean ASCII output with aligned columns. No Rich dependency in the output — suitable for log files and CI.

```python
agent.messages.print_stats(format="plain")
```

### HTML

Semantic HTML tables and sections. Designed for Jupyter notebooks via `IPython.display.HTML`.

```python
html_str = agent.messages.print_stats(format="html")

# In Jupyter
from IPython.display import HTML
HTML(html_str)
```

## Presets

Presets control how much detail renderers include. Three named presets are available:

| Setting | Compact | Detailed | Verbose |
|---------|---------|----------|---------|
| `show_tokens` | No | Yes | Yes |
| `max_content_length` | 100 chars | 300 chars | Unlimited |
| `expand` | No | No | Yes |
| `show_tool_details` | No | No | Yes |
| `max_tool_arg_length` | 50 chars | 200 chars | 500 chars |
| `limit` | None | None | None |

### Using Presets

```python
# Use a named preset
agent.messages.print_stats(preset="compact")
agent.messages.print_stats(preset="detailed")  # default
agent.messages.print_stats(preset="verbose")
```

### Customizing Presets

Override individual fields on any preset:

```python
# Compact but with token counts
agent.messages.print_stats(preset="compact", show_tokens=True)

# Detailed with limited turns
agent.messages.print_timeline(preset="detailed", limit=5)

# Verbose with shorter tool args
agent.messages.print_tools(preset="verbose", max_tool_arg_length=100)
```

### Using `get_preset()` Directly

```python
from mamba_agents.agent.display import get_preset

# Get the default preset
preset = get_preset()  # returns "detailed"

# Get with overrides
preset = get_preset("compact", show_tokens=True)
print(preset.show_tokens)  # True
print(preset.max_content_length)  # 100 (from compact)
```

## Rendering Stats

Displays a table of message counts and token usage by role:

```python
# Via query interface
agent.messages.print_stats()

# Standalone
from mamba_agents.agent.display import print_stats

stats = agent.messages.stats()
print_stats(stats, preset="detailed", format="rich")
```

## Rendering Timeline

Displays each conversation turn with role-labelled content:

```python
# Via query interface
agent.messages.print_timeline()

# Limit to first N turns
agent.messages.print_timeline(preset="detailed", limit=5)

# Show full tool details
agent.messages.print_timeline(preset="verbose")
```

## Rendering Tool Summary

Displays a table of tool names and call counts:

```python
# Via query interface
agent.messages.print_tools()

# Show arguments and results
agent.messages.print_tools(preset="verbose")
```

## Rich Console Protocol

The data models (`MessageStats`, `ToolCallInfo`, `Turn`) implement Rich's `__rich_console__` protocol. You can pass them directly to `rich.print()` or `Console.print()`:

```python
from rich import print as rprint

stats = agent.messages.stats()
rprint(stats)  # Renders as a Rich table

tools = agent.messages.tool_summary()
for tool in tools:
    rprint(tool)  # Each renders as a Rich table

turns = agent.messages.timeline()
for turn in turns:
    rprint(turn)  # Each renders as a Rich panel
```

## Custom Renderers

Create custom renderers by extending the `MessageRenderer` ABC:

```python
from mamba_agents.agent.display import MessageRenderer, DisplayPreset
from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn


class JsonRenderer(MessageRenderer):
    """Renders analytics as JSON strings."""

    def render_stats(self, stats: MessageStats, preset: DisplayPreset) -> str:
        import json
        return json.dumps({
            "total_messages": stats.total_messages,
            "total_tokens": stats.total_tokens,
            "messages_by_role": stats.messages_by_role,
        }, indent=2)

    def render_timeline(self, turns: list[Turn], preset: DisplayPreset) -> str:
        import json
        return json.dumps([
            {"index": t.index, "user": t.user_content, "assistant": t.assistant_content}
            for t in turns
        ], indent=2)

    def render_tools(self, tools: list[ToolCallInfo], preset: DisplayPreset) -> str:
        import json
        return json.dumps([
            {"tool": t.tool_name, "calls": t.call_count}
            for t in tools
        ], indent=2)
```

## Best Practices

1. **Start with `agent.messages.print_stats()`** — the simplest way to see conversation analytics
2. **Use `"compact"` for quick checks**, `"detailed"` for debugging, `"verbose"` for full inspection
3. **Use `format="plain"` for logging** — no ANSI escape codes, clean for file output
4. **Use `format="html"` in Jupyter** — renders natively with `IPython.display.HTML`
5. **Override individual preset fields** rather than creating `DisplayPreset` instances from scratch

## Next Steps

- [Message Querying](message-querying.md) — Filtering, analytics, and export
- [Token Tracking](token-tracking.md) — Token counting and cost estimation
- [API Reference: Presets & Functions](../api/agent/display-presets.md) — Full API details
- [API Reference: Renderers](../api/agent/display-renderers.md) — Renderer class details
