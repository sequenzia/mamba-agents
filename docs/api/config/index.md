# Config Module

Configuration and settings classes.

## Classes

| Class | Description |
|-------|-------------|
| [AgentSettings](settings.md) | Root configuration |
| [ModelBackendSettings](model-backend.md) | Model connection |
| [Other Configs](other.md) | Logging, retry, etc. |

## Quick Example

```python
from pydantic_agent import AgentSettings

# Load from all sources
settings = AgentSettings()

# Access nested config
print(settings.model_backend.model)
print(settings.logging.level)
```

## Configuration Priority

1. Constructor arguments
2. Environment variables (`AGENTS_*`)
3. `.env` file
4. `~/agents.env`
5. `config.toml` / `config.yaml`
6. Default values

## Imports

```python
from pydantic_agent import AgentSettings
from pydantic_agent.config import (
    AgentSettings,
    ModelBackendSettings,
    LoggingConfig,
    ErrorRecoveryConfig,
    ObservabilityConfig,
    StreamingConfig,
)
```
