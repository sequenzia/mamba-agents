# Renderers

Format-specific renderer implementations for message analytics display.

## Quick Example

```python
from mamba_agents.agent.display import RichRenderer, PlainTextRenderer, HtmlRenderer
from mamba_agents.agent.display import DETAILED

renderer = RichRenderer()
output = renderer.render_stats(stats, DETAILED)

# Plain text for logs
plain = PlainTextRenderer()
output = plain.render_stats(stats, DETAILED)

# HTML for Jupyter notebooks
html = HtmlRenderer()
output = html.render_stats(stats, DETAILED)
```

## Renderer Comparison

| Renderer | Output | Use Case |
|----------|--------|----------|
| `RichRenderer` | Rich Console tables and panels | Terminal display |
| `PlainTextRenderer` | ASCII text with aligned columns | Log files, CI output |
| `HtmlRenderer` | Semantic HTML tables and sections | Jupyter notebooks |

## API Reference

### MessageRenderer (ABC)

::: mamba_agents.agent.display.renderer.MessageRenderer
    options:
      show_root_heading: true
      show_source: true
      members:
        - render_stats
        - render_timeline
        - render_tools

### RichRenderer

::: mamba_agents.agent.display.rich_renderer.RichRenderer
    options:
      show_root_heading: true
      show_source: true
      members:
        - render_stats
        - render_timeline
        - render_tools
        - render_stats_renderables
        - render_tools_renderables
        - render_turn_renderable

### PlainTextRenderer

::: mamba_agents.agent.display.plain_renderer.PlainTextRenderer
    options:
      show_root_heading: true
      show_source: true
      members:
        - render_stats
        - render_timeline
        - render_tools

### HtmlRenderer

::: mamba_agents.agent.display.html_renderer.HtmlRenderer
    options:
      show_root_heading: true
      show_source: true
      members:
        - render_stats
        - render_timeline
        - render_tools
