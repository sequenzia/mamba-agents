"""Tests for the configuration system."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from pydantic_agent.config import (
    AgentSettings,
    ErrorRecoveryConfig,
    LoggingConfig,
    ModelBackendSettings,
    ObservabilityConfig,
    StreamingConfig,
)


class TestModelBackendSettings:
    """Tests for ModelBackendSettings."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        settings = ModelBackendSettings()

        assert settings.base_url == "http://localhost:11434/v1"
        assert settings.model == "llama3.2"
        assert settings.api_key is None
        assert settings.timeout == 30.0
        assert settings.max_retries == 3
        assert settings.temperature == 0.7
        assert settings.max_tokens is None

    def test_custom_values(self) -> None:
        """Test custom values can be set."""
        settings = ModelBackendSettings(
            base_url="http://custom:8080/v1",
            model="gpt-4",
            api_key="secret-key",
            timeout=60.0,
            max_retries=5,
            temperature=0.5,
            max_tokens=4096,
        )

        assert settings.base_url == "http://custom:8080/v1"
        assert settings.model == "gpt-4"
        assert settings.api_key is not None
        assert settings.api_key.get_secret_value() == "secret-key"
        assert settings.timeout == 60.0
        assert settings.max_retries == 5
        assert settings.temperature == 0.5
        assert settings.max_tokens == 4096

    def test_api_key_is_secret(self) -> None:
        """Test that API key is properly treated as a secret."""
        settings = ModelBackendSettings(api_key="super-secret")

        # Should not expose secret in string representation
        assert "super-secret" not in str(settings)
        assert "super-secret" not in repr(settings)

        # But should be accessible via get_secret_value
        assert settings.api_key is not None
        assert settings.api_key.get_secret_value() == "super-secret"

    def test_from_env_variables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading from environment variables."""
        monkeypatch.setenv("AGENT_MODEL_BACKEND__BASE_URL", "http://env:9000/v1")
        monkeypatch.setenv("AGENT_MODEL_BACKEND__MODEL", "env-model")
        monkeypatch.setenv("AGENT_MODEL_BACKEND__API_KEY", "env-key")

        # Need to instantiate via AgentSettings for env prefix to work
        settings = AgentSettings()

        assert settings.model_backend.base_url == "http://env:9000/v1"
        assert settings.model_backend.model == "env-model"
        assert settings.model_backend.api_key is not None
        assert settings.model_backend.api_key.get_secret_value() == "env-key"


class TestLoggingConfig:
    """Tests for LoggingConfig."""

    def test_default_values(self) -> None:
        """Test default logging configuration."""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert config.structured is False
        assert config.include_request_body is False
        assert config.include_response_body is False
        assert config.body_size_limit == 1024
        assert config.include_correlation_id is True
        assert config.redact_authorization is True
        assert config.redact_api_keys is True
        assert config.sensitive_patterns == []

    def test_custom_values(self) -> None:
        """Test custom logging configuration."""
        config = LoggingConfig(
            level="DEBUG",
            structured=True,
            include_request_body=True,
            sensitive_patterns=[r"password=\S+"],
        )

        assert config.level == "DEBUG"
        assert config.structured is True
        assert config.include_request_body is True
        assert config.sensitive_patterns == [r"password=\S+"]

    def test_level_validation(self) -> None:
        """Test that log level is validated."""
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level


class TestObservabilityConfig:
    """Tests for ObservabilityConfig."""

    def test_default_values(self) -> None:
        """Test default observability configuration."""
        config = ObservabilityConfig()

        assert config.request_id_format == "uuid4"
        assert config.propagate_trace_context is True
        assert config.enable_otel_instrumentation is False
        assert config.metrics_enabled is True

    def test_request_id_format_options(self) -> None:
        """Test request ID format options."""
        config_uuid = ObservabilityConfig(request_id_format="uuid4")
        assert config_uuid.request_id_format == "uuid4"

        config_ulid = ObservabilityConfig(request_id_format="ulid")
        assert config_ulid.request_id_format == "ulid"


class TestErrorRecoveryConfig:
    """Tests for ErrorRecoveryConfig."""

    def test_default_values(self) -> None:
        """Test default error recovery configuration."""
        config = ErrorRecoveryConfig()

        assert config.retry_level == 2
        assert config.initial_backoff_seconds == 1.0
        assert config.max_backoff_seconds == 60.0
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout == 30.0

    def test_retry_level_boundaries(self) -> None:
        """Test retry level boundaries (1-3)."""
        config1 = ErrorRecoveryConfig(retry_level=1)
        assert config1.retry_level == 1

        config3 = ErrorRecoveryConfig(retry_level=3)
        assert config3.retry_level == 3

    def test_get_tool_retries(self) -> None:
        """Test getting tool retry count based on retry level."""
        config1 = ErrorRecoveryConfig(retry_level=1)
        assert config1.get_tool_retries() == 1

        config2 = ErrorRecoveryConfig(retry_level=2)
        assert config2.get_tool_retries() == 2

        config3 = ErrorRecoveryConfig(retry_level=3)
        assert config3.get_tool_retries() == 3

    def test_get_model_retries(self) -> None:
        """Test getting model retry count based on retry level."""
        config1 = ErrorRecoveryConfig(retry_level=1)
        assert config1.get_model_retries() == 2

        config2 = ErrorRecoveryConfig(retry_level=2)
        assert config2.get_model_retries() == 3

        config3 = ErrorRecoveryConfig(retry_level=3)
        assert config3.get_model_retries() == 5

    def test_get_backoff_multiplier(self) -> None:
        """Test getting backoff multiplier based on retry level."""
        config1 = ErrorRecoveryConfig(retry_level=1)
        assert config1.get_backoff_multiplier() == 2.0

        config2 = ErrorRecoveryConfig(retry_level=2)
        assert config2.get_backoff_multiplier() == 1.5

        config3 = ErrorRecoveryConfig(retry_level=3)
        assert config3.get_backoff_multiplier() == 1.2

    def test_custom_retries_override(self) -> None:
        """Test that custom retry overrides work."""
        config = ErrorRecoveryConfig(
            retry_level=2,
            tool_max_retries=5,
            model_max_retries=10,
        )

        assert config.get_tool_retries() == 5
        assert config.get_model_retries() == 10


class TestStreamingConfig:
    """Tests for StreamingConfig."""

    def test_default_values(self) -> None:
        """Test default streaming configuration."""
        config = StreamingConfig()

        assert config.stream_model_responses is True
        assert config.stream_tool_results is True
        assert config.chunk_size == 1024


class TestAgentSettings:
    """Tests for AgentSettings (root configuration)."""

    def test_default_values(self) -> None:
        """Test that all defaults are set correctly."""
        settings = AgentSettings()

        assert isinstance(settings.model_backend, ModelBackendSettings)
        assert isinstance(settings.logging, LoggingConfig)
        assert isinstance(settings.observability, ObservabilityConfig)
        assert isinstance(settings.retry, ErrorRecoveryConfig)
        assert isinstance(settings.streaming, StreamingConfig)

    def test_nested_env_variables(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test loading nested settings from environment variables."""
        # Change to a temp directory to avoid loading any existing config files
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AGENT_MODEL_BACKEND__BASE_URL", "http://nested:8080/v1")
        monkeypatch.setenv("AGENT_LOGGING__LEVEL", "DEBUG")
        monkeypatch.setenv("AGENT_RETRY__RETRY_LEVEL", "3")

        settings = AgentSettings(_env_file=None)

        assert settings.model_backend.base_url == "http://nested:8080/v1"
        assert settings.logging.level == "DEBUG"
        assert settings.retry.retry_level == 3

    def test_load_from_toml(self, config_toml_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading configuration from TOML file."""
        # Change to temp directory so config.toml is found
        monkeypatch.chdir(config_toml_file.parent)

        settings = AgentSettings(_env_file=None)

        assert settings.model_backend.base_url == "http://localhost:11434/v1"
        assert settings.model_backend.model == "llama3.2"
        assert settings.logging.level == "INFO"
        assert settings.logging.structured is True

    def test_env_overrides_file(
        self, config_toml_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variables override file configuration."""
        monkeypatch.chdir(config_toml_file.parent)
        monkeypatch.setenv("AGENT_LOGGING__LEVEL", "ERROR")

        settings = AgentSettings(_env_file=None)

        # Env should override TOML
        assert settings.logging.level == "ERROR"
        # But other TOML values should still be loaded
        assert settings.model_backend.model == "llama3.2"

    def test_model_dump_excludes_secrets(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that model dump properly handles secrets."""
        monkeypatch.chdir(tmp_path)
        settings = AgentSettings(_env_file=None)
        settings.model_backend.api_key = SecretStr("secret-value")

        dumped = settings.model_dump()

        # API key should be in dump but as SecretStr
        assert "api_key" in dumped["model_backend"]
        # The secret value should not appear in plain text when serialized for logging
        assert "secret-value" not in str(dumped)
