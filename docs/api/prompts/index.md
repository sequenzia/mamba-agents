# Prompts Module

Prompt template management with support for both Jinja2 (`.jinja2`) and Markdown (`.md`) templates.

## Classes

| Class | Description |
|-------|-------------|
| [PromptManager](manager.md) | Load, cache, and render templates |
| [PromptTemplate](template.md) | Renderable prompt template |
| [PromptConfig](config.md) | Manager configuration |
| [TemplateConfig](config.md) | Template reference for Agent |
| `TemplateType` | Enum: `JINJA2` or `MARKDOWN` |

## Quick Example

```python
from mamba_agents import Agent
from mamba_agents.prompts import PromptManager, TemplateConfig

# With Agent
agent = Agent(
    "gpt-4o",
    system_prompt=TemplateConfig(
        name="system/assistant",
        variables={"name": "Helper"}
    )
)

# Direct rendering (works with .jinja2 or .md files)
manager = PromptManager()
prompt = manager.render("system/assistant", name="Helper")

# Runtime registration (Jinja2 syntax)
manager.register("custom/greeting", "Hello, {{ name }}!")
result = manager.render("custom/greeting", name="World")
```

## Imports

```python
# From main package
from mamba_agents import (
    PromptConfig,
    PromptManager,
    PromptTemplate,
    TemplateConfig,
)

# From prompts module
from mamba_agents.prompts import (
    # Classes
    PromptConfig,
    PromptManager,
    PromptTemplate,
    TemplateConfig,
    TemplateType,
    # Errors
    PromptError,
    PromptNotFoundError,
    TemplateRenderError,
    TemplateValidationError,
    MarkdownParseError,
    TemplateConflictError,
)
```

## Template Directory Structure

```
prompts/
├── v1/
│   ├── system/
│   │   ├── assistant.md       # Markdown template
│   │   └── coder.jinja2       # Jinja2 template
│   └── workflow/
│       └── react.jinja2
└── v2/
    └── system/
        └── assistant.md
```

## Template Formats

### Jinja2 (`.jinja2`)

Full Jinja2 templating with `{{ var }}` syntax, conditionals, loops, and inheritance.

### Markdown (`.md`)

Simple templates with YAML frontmatter for default variables and `{var}` syntax:

```markdown
---
variables:
  name: Claude
---
Hello, {name}!
```

## Related

- [User Guide: Prompt Management](../../user-guide/prompt-management.md)
- [Agent Integration](../agent/agent.md)
