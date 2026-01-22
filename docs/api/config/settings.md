# AgentSettings

Root configuration class using Pydantic Settings.

## Quick Example

```python
from mamba_agents import AgentSettings

# Load from environment, .env, config files
settings = AgentSettings()

# Override specific values
settings = AgentSettings(
    model_backend={
        "model": "gpt-4o",
        "api_key": "sk-...",
    },
    logging={"level": "DEBUG"},
)
```

## Configuration Sections

| Section | Type | Description |
|---------|------|-------------|
| `model_backend` | ModelBackendSettings | Model connection |
| `logging` | LoggingConfig | Logging settings |
| `retry` | ErrorRecoveryConfig | Retry behavior |
| `context` | CompactionConfig | Default compaction |
| `tokenizer` | TokenizerConfig | Tokenizer settings |
| `cost_rates` | dict | Custom cost rates |

## Environment Variables

```bash
MAMBA_MODEL_BACKEND__MODEL=gpt-4o
MAMBA_MODEL_BACKEND__API_KEY=sk-...
MAMBA_LOGGING__LEVEL=INFO
MAMBA_RETRY__MAX_RETRIES=3
```

## API Reference

::: mamba_agents.config.settings.AgentSettings
    options:
      show_root_heading: true
      show_source: true
