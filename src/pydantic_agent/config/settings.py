"""Root configuration settings for pydantic-agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from pydantic_agent.config.logging_config import LoggingConfig
from pydantic_agent.config.model_backend import ModelBackendSettings
from pydantic_agent.config.observability import ObservabilityConfig
from pydantic_agent.config.retry import ErrorRecoveryConfig
from pydantic_agent.config.streaming import StreamingConfig


class AgentSettings(BaseSettings):
    """Root configuration for the agent framework.

    Configuration is loaded from multiple sources in priority order:
    1. Constructor arguments (highest priority)
    2. Environment variables (AGENT_ prefix)
    3. .env file
    4. config.toml file
    5. Default values (lowest priority)

    Environment variables use double underscore for nesting:
    - AGENT_MODEL_BACKEND__BASE_URL -> model_backend.base_url
    - AGENT_LOGGING__LEVEL -> logging.level

    Attributes:
        model_backend: Model backend connection settings.
        logging: Logging configuration.
        observability: Observability and tracing settings.
        retry: Error recovery and retry settings.
        streaming: Streaming behavior settings.
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        toml_file="config.toml",
        extra="ignore",
        validate_default=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources to include TOML file support.

        Order determines priority (first = highest priority):
        1. init_settings (constructor args)
        2. env_settings (environment variables)
        3. dotenv_settings (.env file)
        4. toml_settings (config.toml file)
        5. file_secret_settings (secrets files)
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    model_backend: ModelBackendSettings = Field(
        default_factory=ModelBackendSettings,
        description="Model backend connection settings",
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="Observability and tracing settings",
    )
    retry: ErrorRecoveryConfig = Field(
        default_factory=ErrorRecoveryConfig,
        description="Error recovery and retry settings",
    )
    streaming: StreamingConfig = Field(
        default_factory=StreamingConfig,
        description="Streaming behavior settings",
    )

    @classmethod
    def from_file(cls, path: str | Path) -> "AgentSettings":
        """Load settings from a specific configuration file.

        Args:
            path: Path to TOML or YAML configuration file.

        Returns:
            AgentSettings instance with values from file.

        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            ValueError: If file format is not supported.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".toml":
            return cls(_env_file=None, _toml_file=path)
        elif suffix in (".yaml", ".yml"):
            # For YAML, we need to load and pass as dict
            import yaml

            with path.open() as f:
                data = yaml.safe_load(f)
            return cls(_env_file=None, **data)
        else:
            raise ValueError(f"Unsupported configuration file format: {suffix}")

    def model_dump_safe(self) -> dict[str, Any]:
        """Dump model to dict with secrets redacted.

        Returns:
            Dictionary representation with sensitive values replaced.
        """
        data = self.model_dump()

        # Redact API key if present
        if data.get("model_backend", {}).get("api_key"):
            data["model_backend"]["api_key"] = "***REDACTED***"

        return data
