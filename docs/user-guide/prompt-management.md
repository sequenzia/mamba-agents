# Prompt Management

Mamba Agents provides a flexible prompt template system for creating reusable, versioned prompts. It supports both **Jinja2** templates (`.jinja2`) for complex logic and **Markdown** templates (`.md`) for simpler prompts with YAML frontmatter.

## Overview

The prompt management system provides:

1. **Dual format support** - Jinja2 for complex templates, Markdown for simple ones
2. **Directory-based versioning** - Organize prompts by version (v1, v2, etc.)
3. **Template caching** - Efficient loading with automatic caching
4. **Agent integration** - Use templates directly with `system_prompt`
5. **YAML frontmatter** - Default variables in Markdown templates

## Quick Start

### With Agent

The simplest way to use templates is with the Agent's `system_prompt` parameter:

```python
from mamba_agents import Agent
from mamba_agents.prompts import TemplateConfig

agent = Agent(
    "gpt-4o",
    system_prompt=TemplateConfig(
        name="system/assistant",
        variables={"name": "Code Helper", "language": "Python"}
    )
)

result = agent.run_sync("Help me write a function")
```

### Direct Rendering

For more control, use the PromptManager directly:

```python
from mamba_agents.prompts import PromptManager

manager = PromptManager()

# Render a template with variables
prompt = manager.render("system/assistant", name="Code Helper")
print(prompt)
```

## Template Files

### Directory Structure

Templates are organized by version and category:

```
prompts/
├── v1/
│   ├── system/
│   │   ├── assistant.md        # Markdown template
│   │   └── coder.jinja2        # Jinja2 template
│   ├── workflow/
│   │   └── react.jinja2
│   └── base/
│       └── base.jinja2
└── v2/
    └── system/
        └── assistant.md
```

### Naming Conventions

- **Directory**: `prompts/{version}/{category}/`
- **File extensions**: `.jinja2` or `.md` (both supported by default)
- **Template name**: `{category}/{filename}` (e.g., `system/assistant`)

!!! warning "Avoid Conflicts"
    Do not create both `template.jinja2` and `template.md` for the same template name. This will raise a `TemplateConflictError`.

### Example Template

Create a file at `prompts/v1/system/assistant.jinja2`:

```jinja2
You are {{ name }}, a helpful AI assistant.

{% if expertise %}
Your areas of expertise include:
{% for area in expertise %}
- {{ area }}
{% endfor %}
{% endif %}

{% if tone %}
Respond in a {{ tone }} tone.
{% endif %}
```

## Rendering Templates

### Direct Rendering

```python
from mamba_agents.prompts import PromptManager

manager = PromptManager()

# Basic rendering
prompt = manager.render(
    "system/assistant",
    name="Claude",
    expertise=["Python", "Machine Learning"],
    tone="friendly"
)
```

### Using TemplateConfig

For structured configuration:

```python
from mamba_agents.prompts import TemplateConfig

config = TemplateConfig(
    name="system/assistant",
    version="v1",  # Optional, uses default if not specified
    variables={
        "name": "Claude",
        "expertise": ["Python", "ML"],
    }
)

# Render from config
prompt = manager.render_config(config)
```

### Version Selection

```python
# Use specific version
prompt = manager.render("system/assistant", version="v2", name="Claude")

# List available versions
versions = manager.list_versions("system/assistant")
print(versions)  # ['v1', 'v2']
```

## Template Features

### Variables

Basic variable substitution:

```jinja2
Hello, {{ name }}! Welcome to {{ project }}.
```

### Filters

Apply transformations to variables:

```jinja2
{{ name | upper }}           {# CLAUDE #}
{{ name | lower }}           {# claude #}
{{ name | title }}           {# Claude #}
{{ text | truncate(50) }}    {# Truncated text... #}
{{ items | join(", ") }}     {# item1, item2, item3 #}
{{ value | default("N/A") }} {# Fallback if undefined #}
```

### Conditionals

```jinja2
{% if verbose %}
Include detailed explanations in your responses.
{% else %}
Be concise.
{% endif %}

{% if role == "developer" %}
You are helping a software developer.
{% elif role == "analyst" %}
You are helping a data analyst.
{% endif %}
```

### Loops

```jinja2
Your capabilities include:
{% for capability in capabilities %}
- {{ capability }}
{% endfor %}

{% for key, value in settings.items() %}
{{ key }}: {{ value }}
{% endfor %}
```

### Template Inheritance

Create a base template (`base/base.jinja2`):

```jinja2
{% block header %}
You are an AI assistant.
{% endblock %}

{% block instructions %}
Follow the user's instructions carefully.
{% endblock %}

{% block footer %}
{% endblock %}
```

Extend it (`system/coder.jinja2`):

```jinja2
{% extends "v1/base/base.jinja2" %}

{% block header %}
You are {{ name }}, an expert programmer.
{% endblock %}

{% block instructions %}
{{ super() }}
Focus on writing clean, efficient code.
{% endblock %}
```

## Markdown Templates

For simpler prompts that don't need Jinja2's advanced features, you can use Markdown templates with YAML frontmatter.

### Format

Markdown templates use:

- **YAML frontmatter** for metadata and default variables
- **`{var}` syntax** for variable substitution (simpler than Jinja2's `{{ var }}`)

### Example Markdown Template

Create a file at `prompts/v1/system/assistant.md`:

```markdown
---
description: System prompt for AI assistant
variables:
  assistant_name: Claude
  tone: professional
---

You are {assistant_name}, a helpful AI assistant.

Your tone should be {tone} and clear.

Always be helpful and accurate.
```

### Using Markdown Templates

```python
from mamba_agents.prompts import PromptManager

manager = PromptManager()

# Load the template (automatically detects .md extension)
template = manager.get("system/assistant")

# Render with frontmatter defaults
prompt = template.render()
# "You are Claude, a helpful AI assistant..."

# Override defaults
prompt = template.render(assistant_name="Helper", tone="casual")
# "You are Helper, a helpful AI assistant..."
```

### Default Variables

Variables defined in the YAML frontmatter serve as defaults:

```markdown
---
variables:
  name: Default Name
  role: assistant
  language: English
---

You are {name}, a {role}. Respond in {language}.
```

```python
# Uses all defaults
template.render()
# "You are Default Name, a assistant. Respond in English."

# Override some variables
template.render(name="Claude", language="Spanish")
# "You are Claude, a assistant. Respond in Spanish."
```

### Escaping Braces

To include literal braces in output, double them:

```markdown
---
variables:
  name: Claude
---

Hello, {name}!

Use {{curly braces}} for JSON examples.
```

Renders to:

```
Hello, Claude!

Use {curly braces} for JSON examples.
```

### Strict Mode

In strict mode, missing variables raise an error:

```python
from mamba_agents.prompts import PromptConfig, PromptManager

config = PromptConfig(strict_mode=True)
manager = PromptManager(config)

# This will raise TemplateRenderError if 'custom_var' is not in frontmatter
template = manager.get("system/assistant")
template.render()  # Error: missing 'custom_var' (if template uses {custom_var})
```

### When to Use Markdown vs Jinja2

| Use Case | Recommended Format |
|----------|-------------------|
| Simple variable substitution | Markdown (`.md`) |
| Default variable values | Markdown (`.md`) |
| Conditionals (`{% if %}`) | Jinja2 (`.jinja2`) |
| Loops (`{% for %}`) | Jinja2 (`.jinja2`) |
| Template inheritance | Jinja2 (`.jinja2`) |
| Filters and transformations | Jinja2 (`.jinja2`) |

## Agent Integration

### System Prompt

Use templates for agent system prompts:

```python
from mamba_agents import Agent
from mamba_agents.prompts import TemplateConfig

# With TemplateConfig
agent = Agent(
    "gpt-4o",
    system_prompt=TemplateConfig(
        name="system/coder",
        variables={"name": "CodeBot", "language": "Python"}
    )
)

# Or use a plain string (still works)
agent = Agent(
    "gpt-4o",
    system_prompt="You are a helpful assistant."
)
```

### Dynamic System Prompt

Change the system prompt at runtime:

```python
# Get current prompt
current = agent.get_system_prompt()

# Set new prompt from template
agent.set_system_prompt(
    TemplateConfig(
        name="system/assistant",
        variables={"name": "Helper"}
    )
)

# Or set with additional variables
agent.set_system_prompt(
    TemplateConfig(name="system/assistant"),
    name="Helper",
    tone="professional"
)
```

## Workflow Integration

Use templates with ReActWorkflow:

```python
from mamba_agents import Agent
from mamba_agents.workflows import ReActWorkflow, ReActConfig
from mamba_agents.prompts import TemplateConfig

agent = Agent("gpt-4o")

workflow = ReActWorkflow(
    agent=agent,
    config=ReActConfig(
        system_prompt_template=TemplateConfig(
            name="workflow/react",
            variables={"task_type": "research"}
        ),
    )
)

result = await workflow.run("Research Python best practices")
```

## Runtime Registration

Register templates programmatically for testing or dynamic use:

```python
from mamba_agents.prompts import PromptManager

manager = PromptManager()

# Register a template
manager.register(
    "test/greeting",
    "Hello, {{ name }}! Today is {{ day }}."
)

# Use it
prompt = manager.render("test/greeting", name="World", day="Monday")
# "Hello, World! Today is Monday."

# Register with specific version
manager.register("test/greeting", "Hi {{ name }}!", version="v2")
```

## Configuration

### PromptConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `prompts_dir` | Path | `"prompts"` | Directory containing templates |
| `default_version` | str | `"v1"` | Default version when not specified |
| `file_extensions` | list[str] | `[".jinja2", ".md"]` | Supported template file extensions |
| `enable_caching` | bool | `True` | Cache loaded templates |
| `strict_mode` | bool | `False` | Raise on missing variables |

!!! note "Backward Compatibility"
    The `file_extension` property is still available for reading (returns the first extension in the list).

### Custom Configuration

```python
from pathlib import Path
from mamba_agents.prompts import PromptManager, PromptConfig

config = PromptConfig(
    prompts_dir=Path("./my_prompts"),
    default_version="v2",
    file_extensions=[".j2", ".md"],  # Custom extensions
    enable_caching=True,
    strict_mode=True,  # Raise errors for missing variables
)

manager = PromptManager(config=config)
```

### Environment Variables

Configure via environment:

```bash
MAMBA_PROMPTS__PROMPTS_DIR=./my_prompts
MAMBA_PROMPTS__DEFAULT_VERSION=v2
MAMBA_PROMPTS__ENABLE_CACHING=true
MAMBA_PROMPTS__STRICT_MODE=false
```

## Template Utilities

### Get Template Variables

Find what variables a template expects:

```python
template = manager.get("system/assistant")
variables = template.get_variables()
print(variables)  # {'name', 'expertise', 'tone'}
```

### Partial Application

Pre-fill some variables:

```python
template = manager.get("system/assistant")

# Create a partially applied template
coder_template = template.with_variables(
    name="CodeBot",
    expertise=["Python", "TypeScript"]
)

# Render with remaining variables
prompt = coder_template.render(tone="professional")
```

### List Available Templates

```python
# List all templates
all_prompts = manager.list_prompts()

# List by category
system_prompts = manager.list_prompts(category="system")
workflow_prompts = manager.list_prompts(category="workflow")
```

### Check Template Existence

```python
if manager.exists("system/assistant"):
    prompt = manager.render("system/assistant", name="Helper")
else:
    prompt = "Default system prompt"
```

## Error Handling

```python
from mamba_agents.prompts import (
    PromptManager,
    PromptNotFoundError,
    TemplateRenderError,
    TemplateConflictError,
    MarkdownParseError,
)

manager = PromptManager()

try:
    prompt = manager.render("system/nonexistent", name="Test")
except PromptNotFoundError as e:
    print(f"Template not found: {e.name}")

try:
    # Missing required variable in strict mode
    prompt = manager.render("system/assistant")
except TemplateRenderError as e:
    print(f"Render failed: {e}")

try:
    # Both assistant.md and assistant.jinja2 exist
    prompt = manager.render("system/assistant")
except TemplateConflictError as e:
    print(f"Conflicting files for: {e.name}")
    print(f"Extensions found: {e.extensions}")

try:
    # Invalid YAML in markdown frontmatter
    prompt = manager.render("system/invalid")
except MarkdownParseError as e:
    print(f"Failed to parse markdown: {e.name}")
```

## Best Practices

### 1. Version Your Prompts

Use versioning for backward compatibility:

```
prompts/
├── v1/  # Original prompts
├── v2/  # Improved prompts
└── v3/  # Latest iteration
```

### 2. Organize by Category

Group related prompts together:

```
prompts/v1/
├── system/      # System prompts
├── workflow/    # Workflow-specific prompts
├── tools/       # Tool descriptions
└── base/        # Base templates for inheritance
```

### 3. Use Template Inheritance

Create base templates for common patterns:

```jinja2
{# base/assistant.jinja2 #}
{% block persona %}You are a helpful assistant.{% endblock %}

{% block instructions %}
Follow these guidelines:
- Be concise
- Be accurate
{% endblock %}

{% block constraints %}{% endblock %}
```

### 4. Test Your Templates

```python
def test_assistant_template():
    manager = PromptManager()

    # Register test template
    manager.register("test/assistant", "Hello {{ name }}")

    # Verify rendering
    result = manager.render("test/assistant", name="Test")
    assert result == "Hello Test"

    # Verify variables
    template = manager.get("test/assistant")
    assert "name" in template.get_variables()
```

### 5. Document Variables

Include comments in your templates:

```jinja2
{#
  Template: system/assistant
  Variables:
    - name (str): The assistant's name
    - expertise (list[str], optional): Areas of expertise
    - tone (str, optional): Response tone (friendly, professional, etc.)
#}
You are {{ name }}...
```

## Next Steps

- [PromptManager API](../api/prompts/manager.md) - Full reference
- [TemplateConfig API](../api/prompts/config.md) - Configuration options
- [Agent Basics](agent-basics.md) - Agent fundamentals
- [Workflows](workflows.md) - Using prompts with workflows
