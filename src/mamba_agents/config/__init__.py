"""Configuration system for mamba-agents.

Main exports:
- AgentSettings: Root configuration class
- ModelBackendSettings: Model backend connection settings
- LoggingConfig: Logging configuration
- ErrorRecoveryConfig: Retry and recovery settings

Extensibility configs (not yet integrated into core agent):
- ObservabilityConfig: Tracing and metrics settings (placeholder for future use)
- StreamingConfig: Streaming behavior settings (placeholder for future use)
"""

from mamba_agents.config.logging_config import LoggingConfig
from mamba_agents.config.model_backend import ModelBackendSettings

# Extensibility configs - available in AgentSettings but not actively used by core
from mamba_agents.config.observability import ObservabilityConfig
from mamba_agents.config.retry import ErrorRecoveryConfig
from mamba_agents.config.settings import AgentSettings
from mamba_agents.config.streaming import StreamingConfig

__all__ = [
    # Main exports
    "AgentSettings",
    "ErrorRecoveryConfig",
    "LoggingConfig",
    "ModelBackendSettings",
    # Extensibility
    "ObservabilityConfig",
    "StreamingConfig",
]
