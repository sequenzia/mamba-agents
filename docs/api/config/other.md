# Other Configuration Classes

Additional configuration classes.

## LoggingConfig

```python
from pydantic_agent.config import LoggingConfig

config = LoggingConfig(
    level="INFO",
    format="json",
    redact_sensitive=True,
)
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `level` | str | `"INFO"` | Log level |
| `format` | str | `"text"` | Output format |
| `redact_sensitive` | bool | True | Redact secrets |

## ErrorRecoveryConfig

```python
from pydantic_agent.config import ErrorRecoveryConfig

config = ErrorRecoveryConfig(
    retry_level=2,
    max_retries=3,
    base_wait=1.0,
)
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `retry_level` | int | 2 | Aggressiveness (1-3) |
| `max_retries` | int | 3 | Max attempts |
| `base_wait` | float | 1.0 | Initial backoff |

## ObservabilityConfig

```python
from pydantic_agent.config import ObservabilityConfig

config = ObservabilityConfig(
    enable_tracing=True,
    service_name="my-agent",
)
```

## StreamingConfig

```python
from pydantic_agent.config import StreamingConfig

config = StreamingConfig(
    enabled=True,
    chunk_size=1024,
)
```

## API Reference

::: pydantic_agent.config.logging_config.LoggingConfig
    options:
      show_root_heading: true

::: pydantic_agent.config.retry.ErrorRecoveryConfig
    options:
      show_root_heading: true

::: pydantic_agent.config.observability.ObservabilityConfig
    options:
      show_root_heading: true
