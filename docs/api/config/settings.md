# AgentSettings

Root configuration class using Pydantic Settings.

## Quick Example

```python
from pydantic_agent import AgentSettings

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
| `observability` | ObservabilityConfig | Tracing settings |
| `retry` | ErrorRecoveryConfig | Retry behavior |
| `streaming` | StreamingConfig | Streaming options |
| `context` | CompactionConfig | Default compaction |
| `tokenizer` | TokenizerConfig | Tokenizer settings |
| `cost_rates` | dict | Custom cost rates |

## Environment Variables

```bash
AGENTS_MODEL_BACKEND__MODEL=gpt-4o
AGENTS_MODEL_BACKEND__API_KEY=sk-...
AGENTS_LOGGING__LEVEL=INFO
AGENTS_RETRY__MAX_RETRIES=3
```

## API Reference

::: pydantic_agent.config.settings.AgentSettings
    options:
      show_root_heading: true
      show_source: true
