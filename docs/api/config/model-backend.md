# ModelBackendSettings

Model connection configuration.

## Quick Example

```python
from pydantic_agent.config import ModelBackendSettings

# Via AgentSettings
from pydantic_agent import AgentSettings
settings = AgentSettings(
    model_backend={
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "temperature": 0.7,
    }
)
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `model` | str | `"llama3.2"` | Model identifier |
| `base_url` | str | `"http://localhost:11434/v1"` | API endpoint |
| `api_key` | SecretStr | None | API key |
| `temperature` | float | 0.7 | Sampling temperature |
| `max_tokens` | int | None | Max output tokens |
| `timeout` | float | 30.0 | Request timeout |
| `max_retries` | int | 3 | Retry attempts |

## Environment Variables

```bash
AGENTS_MODEL_BACKEND__BASE_URL=https://api.openai.com/v1
AGENTS_MODEL_BACKEND__MODEL=gpt-4o
AGENTS_MODEL_BACKEND__API_KEY=sk-...
AGENTS_MODEL_BACKEND__TEMPERATURE=0.7
```

## API Reference

::: pydantic_agent.config.model_backend.ModelBackendSettings
    options:
      show_root_heading: true
      show_source: true
