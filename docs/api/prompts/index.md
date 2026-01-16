# Prompts Module

Jinja2-based prompt template management.

## Classes

| Class | Description |
|-------|-------------|
| [PromptManager](manager.md) | Load, cache, and render templates |
| [PromptTemplate](template.md) | Renderable prompt template |
| [PromptConfig](config.md) | Manager configuration |
| [TemplateConfig](config.md) | Template reference for Agent |

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

# Direct rendering
manager = PromptManager()
prompt = manager.render("system/assistant", name="Helper")

# Runtime registration
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
    PromptConfig,
    PromptManager,
    PromptTemplate,
    TemplateConfig,
    PromptError,
    PromptNotFoundError,
    TemplateRenderError,
    TemplateValidationError,
)
```

## Template Directory Structure

```
prompts/
├── v1/
│   ├── system/
│   │   └── assistant.jinja2
│   └── workflow/
│       └── react.jinja2
└── v2/
    └── system/
        └── assistant.jinja2
```

## Related

- [User Guide: Prompt Management](../../user-guide/prompt-management.md)
- [Agent Integration](../agent/agent.md)
