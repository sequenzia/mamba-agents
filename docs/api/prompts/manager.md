# PromptManager

Manages prompt templates with loading, caching, and rendering. Supports both Jinja2 (`.jinja2`) and Markdown (`.md`) templates.

## Quick Example

```python
from mamba_agents.prompts import PromptManager

manager = PromptManager()

# Load and render a template (works with .jinja2 or .md)
prompt = manager.render("system/assistant", name="Helper", tone="friendly")

# Get template object
template = manager.get("system/assistant")
variables = template.get_variables()

# Check template type
print(template.template_type)  # TemplateType.JINJA2 or TemplateType.MARKDOWN

# Register runtime template (Jinja2 syntax)
manager.register("test/greeting", "Hello, {{ name }}!")
```

## Key Methods

| Method | Description |
|--------|-------------|
| `get(name, version)` | Get a PromptTemplate by name |
| `render(name, **vars)` | Render template with variables |
| `render_config(config)` | Render from TemplateConfig |
| `register(name, template)` | Register template at runtime |
| `list_prompts(category)` | List available templates |
| `list_versions(name)` | List versions for a template |
| `exists(name, version)` | Check if template exists |
| `clear_cache()` | Clear the template cache |

## Caching Behavior

Templates are cached after first load (when `enable_caching=True`):

```python
from mamba_agents.prompts import PromptManager, PromptConfig

# Caching enabled (default)
manager = PromptManager()
template1 = manager.get("system/assistant")  # Loads from file
template2 = manager.get("system/assistant")  # Returns cached

# Clear cache to reload
manager.clear_cache()

# Disable caching
config = PromptConfig(enable_caching=False)
manager = PromptManager(config=config)
```

## Registered Templates

Runtime-registered templates take precedence over file-based templates:

```python
manager = PromptManager()

# Register for testing
manager.register("system/assistant", "Test prompt: {{ name }}")

# This returns the registered template, not the file
prompt = manager.render("system/assistant", name="Test")
```

## API Reference

::: mamba_agents.prompts.manager.PromptManager
    options:
      show_root_heading: true
      show_source: true
