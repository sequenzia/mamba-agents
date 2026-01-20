"""Custom exception hierarchy for the agent framework."""

from __future__ import annotations

from typing import Any


class AgentError(Exception):
    """Base exception for all agent errors.

    All custom exceptions in this framework inherit from this class,
    allowing for easy catching of all agent-related errors.

    Attributes:
        message: Human-readable error message.
        cause: Original exception that caused this error.
        details: Additional error context as key-value pairs.
    """

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
        **details: Any,
    ) -> None:
        """Initialize the error.

        Args:
            message: Human-readable error message.
            cause: Original exception that caused this error.
            **details: Additional error context.
        """
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.details = details

    def __str__(self) -> str:
        """Return string representation."""
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class ConfigurationError(AgentError):
    """Error in agent configuration.

    Raised when configuration is invalid, missing required fields,
    or contains incompatible settings.
    """

    @property
    def config_key(self) -> str | None:
        return self.details.get("config_key")

    @property
    def expected(self) -> Any:
        return self.details.get("expected")

    @property
    def actual(self) -> Any:
        return self.details.get("actual")


class ModelBackendError(AgentError):
    """Error from the model backend.

    Raised when the underlying model API returns an error,
    times out, or is unavailable.
    """

    @property
    def model(self) -> str | None:
        return self.details.get("model")

    @property
    def status_code(self) -> int | None:
        return self.details.get("status_code")

    @property
    def response_body(self) -> str | None:
        return self.details.get("response_body")

    @property
    def retryable(self) -> bool:
        return self.details.get("retryable", False)


class ToolExecutionError(AgentError):
    """Error during tool execution.

    Raised when a tool fails to execute properly, either due to
    invalid arguments, permission issues, or runtime errors.
    """

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # Redact sensitive values in tool_args
        if tool_args:
            tool_args = {
                k: "[REDACTED]" if "key" in k.lower() or "secret" in k.lower() else v
                for k, v in tool_args.items()
            }
        super().__init__(message, tool_name=tool_name, tool_args=tool_args, **kwargs)

    @property
    def tool_name(self) -> str | None:
        return self.details.get("tool_name")

    @property
    def tool_args(self) -> dict[str, Any] | None:
        return self.details.get("tool_args")


class ContextOverflowError(AgentError):
    """Context window exceeded.

    Raised when the conversation context exceeds the model's
    maximum context window and cannot be compacted further.
    """

    @property
    def current_tokens(self) -> int | None:
        return self.details.get("current_tokens")

    @property
    def max_tokens(self) -> int | None:
        return self.details.get("max_tokens")

    @property
    def compaction_attempted(self) -> bool:
        return self.details.get("compaction_attempted", False)


class MCPError(AgentError):
    """Error from MCP server interaction.

    Raised when communication with an MCP server fails,
    the server returns an error, or authentication fails.
    """

    @property
    def server_name(self) -> str | None:
        return self.details.get("server_name")

    @property
    def server_url(self) -> str | None:
        return self.details.get("server_url")


class RateLimitError(ModelBackendError):
    """Rate limit exceeded.

    Raised when the model API rate limit is hit.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)

    @property
    def retry_after(self) -> float | None:
        return self.details.get("retry_after")


class AuthenticationError(AgentError):
    """Authentication failed.

    Raised when API authentication fails, typically due to
    invalid or expired credentials.
    """

    pass


class TimeoutError(AgentError):
    """Operation timed out.

    Raised when an operation exceeds its timeout limit.
    """

    @property
    def timeout_seconds(self) -> float | None:
        return self.details.get("timeout_seconds")

    @property
    def operation(self) -> str | None:
        return self.details.get("operation")
