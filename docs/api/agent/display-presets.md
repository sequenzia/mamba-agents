# Presets & Functions

Display presets control detail level, and standalone functions render analytics data.

## Quick Example

```python
from mamba_agents.agent.display import print_stats, get_preset

# Use a named preset
output = print_stats(stats, preset="compact")

# Customize a preset
preset = get_preset("detailed", show_tokens=False)
output = print_stats(stats, preset="detailed", show_tokens=False)

# Use different output formats
print_stats(stats, format="rich")   # Rich terminal tables
print_stats(stats, format="plain")  # ASCII text
print_stats(stats, format="html")   # HTML for Jupyter
```

## Preset Comparison

| Setting | Compact | Detailed | Verbose |
|---------|---------|----------|---------|
| `show_tokens` | False | True | True |
| `max_content_length` | 100 | 300 | None (unlimited) |
| `expand` | False | False | True |
| `show_tool_details` | False | False | True |
| `max_tool_arg_length` | 50 | 200 | 500 |
| `limit` | None | None | None |

## Named Preset Instances

```python
from mamba_agents.agent.display import COMPACT, DETAILED, VERBOSE
```

- **`COMPACT`** — Minimal output: counts only, short truncation, no tool details.
- **`DETAILED`** — Balanced output: full tables, moderate truncation, no tool details. *(default)*
- **`VERBOSE`** — Maximum output: expanded content, no truncation, full tool args/results.

## API Reference

### DisplayPreset

::: mamba_agents.agent.display.presets.DisplayPreset
    options:
      show_root_heading: true
      show_source: true

### get_preset

::: mamba_agents.agent.display.presets.get_preset
    options:
      show_root_heading: true
      show_source: true

### print_stats

::: mamba_agents.agent.display.functions.print_stats
    options:
      show_root_heading: true
      show_source: true

### print_timeline

::: mamba_agents.agent.display.functions.print_timeline
    options:
      show_root_heading: true
      show_source: true

### print_tools

::: mamba_agents.agent.display.functions.print_tools
    options:
      show_root_heading: true
      show_source: true
