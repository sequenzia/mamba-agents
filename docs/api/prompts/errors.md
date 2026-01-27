# Prompt Errors

Exceptions for prompt management operations.

## Error Hierarchy

```
PromptError (base)
├── PromptNotFoundError
├── TemplateRenderError
├── TemplateValidationError
├── MarkdownParseError
└── TemplateConflictError
```

## PromptError

Base exception for all prompt-related errors.

```python
from mamba_agents.prompts import PromptError

try:
    # Any prompt operation
    pass
except PromptError as e:
    print(f"Prompt error: {e}")
```

## PromptNotFoundError

Raised when a template cannot be found.

```python
from mamba_agents.prompts import PromptManager, PromptNotFoundError

manager = PromptManager()

try:
    prompt = manager.render("nonexistent/template")
except PromptNotFoundError as e:
    print(f"Template not found: {e.name}")
    print(f"Version: {e.version}")
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Template name that was not found |
| `version` | str \| None | Version that was requested |

## TemplateRenderError

Raised when a template fails to render.

```python
from mamba_agents.prompts import PromptManager, TemplateRenderError, PromptConfig

# With strict mode
config = PromptConfig(strict_mode=True)
manager = PromptManager(config=config)
manager.register("test", "Hello {{ name }}")

try:
    # Missing required variable
    prompt = manager.render("test")
except TemplateRenderError as e:
    print(f"Render failed for: {e.name}")
    print(f"Cause: {e.cause}")
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Template name that failed to render |
| `cause` | Exception | Underlying exception |

## TemplateValidationError

Raised when a template has invalid syntax.

```python
from mamba_agents.prompts import PromptTemplate, TemplateValidationError

try:
    template = PromptTemplate(
        name="invalid",
        version="v1",
        source="{% if unclosed",  # Invalid syntax
    )
    template.render()
except TemplateValidationError as e:
    print(f"Invalid template: {e.name}")
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Template name with invalid syntax |

## MarkdownParseError

Raised when a Markdown template's YAML frontmatter is malformed.

```python
from mamba_agents.prompts import PromptManager, MarkdownParseError

manager = PromptManager()

try:
    # Template with invalid YAML frontmatter
    prompt = manager.render("system/invalid_yaml")
except MarkdownParseError as e:
    print(f"Parse failed for: {e.name}")
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Template name that failed to parse |

## TemplateConflictError

Raised when both `.jinja2` and `.md` files exist for the same template name.

```python
from mamba_agents.prompts import PromptManager, TemplateConflictError

manager = PromptManager()

try:
    # Both assistant.jinja2 and assistant.md exist in prompts/v1/system/
    prompt = manager.render("system/assistant")
except TemplateConflictError as e:
    print(f"Conflicting files for: {e.name}")
    print(f"Version: {e.version}")
    print(f"Extensions found: {e.extensions}")  # ['.jinja2', '.md']
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Template name with conflicting files |
| `version` | str | Version where conflict was found |
| `extensions` | list[str] | List of conflicting file extensions |

## API Reference

::: mamba_agents.prompts.errors
    options:
      show_root_heading: true
      show_source: true
