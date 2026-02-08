# Configuration

Mamba Agents uses a layered configuration system that loads settings from multiple sources.

## Configuration Sources

Settings are loaded in the following priority order (highest to lowest):

1. **Constructor arguments** - Passed directly when creating an Agent
2. **Environment variables** - Using the `MAMBA_` prefix
3. **`.env` file** - Project-specific settings
4. **`~/mamba.env`** - User-wide defaults
5. **`config.toml` / `config.yaml`** - Configuration files
6. **Default values** - Built-in defaults

## Environment Variables

All settings use the `MAMBA_` prefix. Use double underscore (`__`) for nested settings:

```bash
# Model configuration
MAMBA_MODEL_BACKEND__MODEL=gpt-4o
MAMBA_MODEL_BACKEND__API_KEY=sk-...
MAMBA_MODEL_BACKEND__BASE_URL=https://api.openai.com/v1
MAMBA_MODEL_BACKEND__TEMPERATURE=0.7

# Logging
MAMBA_LOGGING__LEVEL=INFO
MAMBA_LOGGING__FORMAT=json

# Retry behavior
MAMBA_RETRY__MAX_RETRIES=3
MAMBA_RETRY__RETRY_LEVEL=2

# Context compaction
MAMBA_CONTEXT__STRATEGY=hybrid
MAMBA_CONTEXT__TRIGGER_THRESHOLD_TOKENS=100000
MAMBA_CONTEXT__TARGET_TOKENS=80000
```

## .env Files

Create a `.env` file in your project directory:

```bash
# .env
MAMBA_MODEL_BACKEND__MODEL=gpt-4o
MAMBA_MODEL_BACKEND__API_KEY=sk-your-api-key-here

MAMBA_LOGGING__LEVEL=DEBUG
```

For user-wide defaults, create `~/mamba.env`:

```bash
# ~/mamba.env
MAMBA_MODEL_BACKEND__API_KEY=sk-default-api-key
MAMBA_LOGGING__LEVEL=INFO
```

## TOML Configuration

Create a `config.toml` file in your project:

```toml
[model_backend]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
temperature = 0.7
max_tokens = 4096
timeout = 30.0

[logging]
level = "INFO"
format = "json"
redact_sensitive = true

[retry]
max_retries = 3
retry_level = 2

[context]
strategy = "hybrid"
trigger_threshold_tokens = 100000
target_tokens = 80000
preserve_recent_turns = 10
preserve_system_prompt = true

[streaming]
enabled = true
chunk_size = 1024
```

## YAML Configuration

Alternatively, use `config.yaml`:

```yaml
model_backend:
  model: gpt-4o
  base_url: https://api.openai.com/v1
  temperature: 0.7

logging:
  level: INFO
  format: json

retry:
  max_retries: 3
  retry_level: 2

context:
  strategy: hybrid
  trigger_threshold_tokens: 100000
  target_tokens: 80000
```

## Using AgentSettings

Load settings programmatically:

```python
from mamba_agents import AgentSettings, Agent

# Load from all sources (env, .env, config files)
settings = AgentSettings()

# Access settings
print(f"Model: {settings.model_backend.model}")
print(f"Log level: {settings.logging.level}")

# Create agent with settings
agent = Agent(settings=settings)
```

## Settings Reference

### ModelBackendSettings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `model` | str | `"llama3.2"` | Model identifier |
| `api_key` | SecretStr | None | API key (never logged) |
| `base_url` | str | `"http://localhost:11434/v1"` | API endpoint |
| `temperature` | float | `0.7` | Sampling temperature (0.0-2.0) |
| `max_tokens` | int | None | Max tokens to generate |
| `timeout` | float | `30.0` | Request timeout in seconds |
| `max_retries` | int | `3` | Retry attempts |

### LoggingConfig

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `level` | str | `"INFO"` | Log level |
| `format` | str | `"text"` | Output format (`text`, `json`) |
| `redact_sensitive` | bool | `true` | Redact API keys from logs |

### ErrorRecoveryConfig

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `max_retries` | int | `3` | Maximum retry attempts |
| `retry_level` | int | `2` | Retry aggressiveness (1-3) |
| `base_wait` | float | `1.0` | Base wait time for backoff |

### CompactionConfig

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `strategy` | str | `"sliding_window"` | Compaction strategy |
| `trigger_threshold_tokens` | int | `100000` | Token count to trigger compaction |
| `target_tokens` | int | `80000` | Target token count after compaction |
| `preserve_recent_turns` | int | `10` | Recent turns to always preserve |
| `preserve_system_prompt` | bool | `true` | Always keep system prompt |

### SkillConfig

!!! warning "Experimental"
    The skills configuration is experimental and may change in minor versions.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `skills_dirs` | list[Path] | `[".mamba/skills"]` | Project-level skill directories |
| `user_skills_dir` | Path | `~/.mamba/skills` | User-level skills directory |
| `custom_paths` | list[Path] | `[]` | Additional search paths |
| `auto_discover` | bool | `true` | Auto-discover skills on startup |
| `namespace_tools` | bool | `true` | Prefix tool names with skill name |
| `trusted_paths` | list[Path] | `[]` | Custom paths treated as trusted |

```bash
# Environment variables
MAMBA_SKILLS__AUTO_DISCOVER=true
MAMBA_SKILLS__NAMESPACE_TOOLS=true
MAMBA_SKILLS__SKILLS_DIRS='[".mamba/skills", "extra/skills"]'
```

```toml
# config.toml
[skills]
auto_discover = true
namespace_tools = true
custom_paths = ["/shared/skills"]
trusted_paths = ["/shared/skills"]
```

!!! note "Subagent Configuration"
    Subagent configs are loaded from `.mamba/agents/{name}.md` markdown files (not via environment variables). See the [Subagents guide](../user-guide/subagents.md) for details.

## Override Settings in Code

You can override settings when creating an agent:

```python
from mamba_agents import Agent, AgentSettings, AgentConfig, CompactionConfig

settings = AgentSettings()

# Override model while using settings for api_key, base_url
agent = Agent("gpt-4o-mini", settings=settings)

# Override with custom config
config = AgentConfig(
    system_prompt="You are helpful.",
    context=CompactionConfig(
        strategy="summarize_older",
        trigger_threshold_tokens=50000,
    ),
)
agent = Agent("gpt-4o", settings=settings, config=config)
```

## Secrets Handling

!!! warning "Security"
    API keys are stored as `SecretStr` and are never logged or serialized to plain text.

```python
# API key is protected
settings = AgentSettings()
print(settings.model_backend.api_key)  # SecretStr('**********')

# Access the actual value when needed (carefully!)
actual_key = settings.model_backend.api_key.get_secret_value()
```

## Next Steps

- [Agent Basics](../user-guide/agent-basics.md) - Learn the Agent API
- [Model Backends](../user-guide/model-backends.md) - Configure local models
- [AgentSettings API](../api/config/settings.md) - Full settings reference
