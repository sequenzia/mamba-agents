# Other Configuration Classes

Additional configuration classes.

## LoggingConfig

```python
from mamba_agents.config import LoggingConfig

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
from mamba_agents.config import ErrorRecoveryConfig

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

## API Reference

::: mamba_agents.config.logging_config.LoggingConfig
    options:
      show_root_heading: true

::: mamba_agents.config.retry.ErrorRecoveryConfig
    options:
      show_root_heading: true
