# PromptTemplate

A renderable prompt template supporting both Jinja2 and Markdown formats.

## TemplateType Enum

```python
from mamba_agents.prompts import TemplateType

TemplateType.JINJA2    # Jinja2 template with {{ var }} syntax
TemplateType.MARKDOWN  # Markdown template with {var} syntax
```

## Quick Example

```python
from mamba_agents.prompts import PromptTemplate, TemplateType

# Jinja2 template (default)
jinja_template = PromptTemplate(
    name="greeting",
    version="v1",
    source="Hello, {{ name }}! You are {{ role }}.",
)

# Markdown template
md_template = PromptTemplate(
    name="greeting",
    version="v1",
    source="Hello, {name}! You are {role}.",
    template_type=TemplateType.MARKDOWN,
)

# Render with variables
prompt = jinja_template.render(name="Claude", role="helpful")
# "Hello, Claude! You are helpful."
```

## Key Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Template name |
| `version` | str | required | Template version |
| `source` | str | required | Template source code |
| `template_type` | TemplateType | `JINJA2` | Template format |

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

## Markdown Templates

Markdown templates use `{var}` syntax instead of Jinja2's `{{ var }}`:

```python
from mamba_agents.prompts import PromptTemplate, TemplateType

template = PromptTemplate(
    name="assistant",
    version="v1",
    source="You are {name}, a {role}.",
    template_type=TemplateType.MARKDOWN,
)

# Render
prompt = template.render(name="Claude", role="helpful assistant")
# "You are Claude, a helpful assistant."

# Get variables works the same way
variables = template.get_variables()
# {'name', 'role'}
```

### Escaping Braces in Markdown

Use double braces for literal output:

```python
template = PromptTemplate(
    name="example",
    version="v1",
    source="Use {{braces}} for JSON. Hello, {name}!",
    template_type=TemplateType.MARKDOWN,
)

template.render(name="World")
# "Use {braces} for JSON. Hello, World!"
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
