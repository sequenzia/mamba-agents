# Prompt Configuration

Configuration classes for prompt management.

## PromptConfig

Configuration for the PromptManager.

### Quick Example

```python
from pathlib import Path
from mamba_agents.prompts import PromptConfig, PromptManager

config = PromptConfig(
    prompts_dir=Path("./my_prompts"),
    default_version="v2",
    file_extension=".j2",
    enable_caching=True,
    strict_mode=False,
)

manager = PromptManager(config=config)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `prompts_dir` | Path | `"prompts"` | Directory containing templates |
| `default_version` | str | `"v1"` | Default version when not specified |
| `file_extension` | str | `".jinja2"` | Template file extension |
| `enable_caching` | bool | `True` | Cache loaded templates |
| `strict_mode` | bool | `False` | Raise on missing variables |

### API Reference

::: mamba_agents.prompts.config.PromptConfig
    options:
      show_root_heading: true
      show_source: true

---

## TemplateConfig

Reference to a prompt template for use with Agent.

### Quick Example

```python
from mamba_agents import Agent
from mamba_agents.prompts import TemplateConfig

# Basic usage
config = TemplateConfig(
    name="system/assistant",
    variables={"name": "Helper"}
)

agent = Agent("gpt-4o", system_prompt=config)

# With specific version
config = TemplateConfig(
    name="system/assistant",
    version="v2",
    variables={"name": "Helper", "tone": "professional"}
)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | str | required | Template name (e.g., `"system/assistant"`) |
| `version` | str \| None | `None` | Template version (uses default if None) |
| `variables` | dict | `{}` | Variables to pass when rendering |

### API Reference

::: mamba_agents.prompts.config.TemplateConfig
    options:
      show_root_heading: true
      show_source: true
