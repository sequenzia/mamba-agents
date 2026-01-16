# PromptTemplate

A renderable prompt template wrapping Jinja2.

## Quick Example

```python
from mamba_agents.prompts import PromptTemplate

# Create template directly
template = PromptTemplate(
    name="greeting",
    version="v1",
    source="Hello, {{ name }}! You are {{ role }}.",
)

# Render with variables
prompt = template.render(name="Claude", role="helpful")
# "Hello, Claude! You are helpful."
```

## Key Methods

| Method | Description |
|--------|-------------|
| `render(**vars)` | Render template with variables |
| `with_variables(**vars)` | Create template with default variables |
| `get_variables()` | Get set of variable names in template |

## Rendering

```python
from mamba_agents.prompts import PromptManager

manager = PromptManager()
template = manager.get("system/assistant")

# Basic rendering
prompt = template.render(name="Helper", tone="friendly")

# Get required variables
variables = template.get_variables()
print(variables)  # {'name', 'tone', 'expertise'}
```

## Partial Application

Pre-fill some variables to create a specialized template:

```python
template = PromptTemplate(
    name="sys",
    version="v1",
    source="Hello {{ name }}, you are {{ role }} with {{ tone }} style.",
)

# Create partially applied template
helper = template.with_variables(name="Claude", tone="friendly")

# Render with remaining variables
prompt = helper.render(role="an assistant")
# "Hello Claude, you are an assistant with friendly style."
```

## Template Compilation

Templates are compiled lazily on first render:

```python
template = PromptTemplate(
    name="test",
    version="v1",
    source="{{ greeting }}, {{ name }}!",
)

# Template not compiled yet
prompt = template.render(greeting="Hello", name="World")  # Compiles here

# Subsequent renders reuse compiled template
prompt2 = template.render(greeting="Hi", name="User")  # Uses cached
```

## API Reference

::: mamba_agents.prompts.template.PromptTemplate
    options:
      show_root_heading: true
      show_source: true
