"""Error recovery and retry configuration."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field, field_validator


def _coerce_retry_level(v: int | str) -> int:
    """Coerce retry level to int."""
    if isinstance(v, str):
        return int(v)
    return v


RetryLevel = Annotated[int, BeforeValidator(_coerce_retry_level)]


# Retry configuration per level
_TOOL_RETRIES = {1: 1, 2: 2, 3: 3}
_MODEL_RETRIES = {1: 2, 2: 3, 3: 5}
_BACKOFF_MULTIPLIERS = {1: 2.0, 2: 1.5, 3: 1.2}


class ErrorRecoveryConfig(BaseModel):
    """Configuration for error recovery and retry behavior.

    Error recovery aggressiveness is configurable on a scale of 1-3:
    - Level 1 (Conservative): Minimal retries, fail fast
    - Level 2 (Balanced): Default behavior
    - Level 3 (Aggressive): Maximum retry attempts

    Attributes:
        retry_level: Aggressiveness level (1-3).
        tool_max_retries: Override for tool retry count.
        model_max_retries: Override for model retry count.
        initial_backoff_seconds: Initial wait before retry.
        max_backoff_seconds: Maximum wait between retries.
        circuit_breaker_threshold: Failures before circuit opens.
        circuit_breaker_timeout: Seconds before retry after circuit opens.
        retryable_tool_errors: Tool error types that trigger retry.
        retryable_model_errors: Model error types that trigger retry.
    """

    retry_level: RetryLevel = Field(
        default=2,
        description="Retry aggressiveness level (1=conservative, 2=balanced, 3=aggressive)",
    )
    tool_max_retries: int | None = Field(
        default=None,
        ge=0,
        description="Override for tool retry count",
    )
    model_max_retries: int | None = Field(
        default=None,
        ge=0,
        description="Override for model retry count",
    )
    initial_backoff_seconds: float = Field(
        default=1.0,
        gt=0,
        description="Initial wait before retry",
    )
    max_backoff_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Maximum wait between retries",
    )
    circuit_breaker_threshold: int = Field(
        default=5,
        gt=0,
        description="Failures before circuit opens",
    )
    circuit_breaker_timeout: float = Field(
        default=30.0,
        gt=0,
        description="Seconds before retry after circuit opens",
    )
    retryable_tool_errors: list[str] = Field(
        default_factory=lambda: ["TimeoutError", "ConnectionError", "TemporaryFailure"],
        description="Tool error types that trigger retry",
    )
    retryable_model_errors: list[str] = Field(
        default_factory=lambda: ["RateLimitError", "ServiceUnavailable", "Timeout"],
        description="Model error types that trigger retry",
    )

    @field_validator("retry_level")
    @classmethod
    def validate_retry_level(cls, v: int) -> int:
        """Validate retry level is in range 1-3."""
        if v not in (1, 2, 3):
            raise ValueError("retry_level must be 1, 2, or 3")
        return v

    def get_tool_retries(self) -> int:
        """Get tool retry count based on configuration.

        Returns:
            Number of retries for tool calls.
        """
        if self.tool_max_retries is not None:
            return self.tool_max_retries
        return _TOOL_RETRIES[self.retry_level]

    def get_model_retries(self) -> int:
        """Get model retry count based on configuration.

        Returns:
            Number of retries for model calls.
        """
        if self.model_max_retries is not None:
            return self.model_max_retries
        return _MODEL_RETRIES[self.retry_level]

    def get_backoff_multiplier(self) -> float:
        """Get exponential backoff multiplier based on retry level.

        Returns:
            Backoff multiplier for exponential backoff.
        """
        return _BACKOFF_MULTIPLIERS[self.retry_level]
