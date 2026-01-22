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
from mamba_agents import AgentSettings

# Load from all sources
settings = AgentSettings()

# Access nested config
print(settings.model_backend.model)
print(settings.logging.level)
```

## Configuration Priority

1. Constructor arguments
2. Environment variables (`MAMBA_*`)
3. `.env` file
4. `~/mamba.env`
5. `config.toml` / `config.yaml`
6. Default values

## Imports

```python
from mamba_agents import AgentSettings
from mamba_agents.config import (
    AgentSettings,
    ModelBackendSettings,
    LoggingConfig,
    ErrorRecoveryConfig,
)
```
