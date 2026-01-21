"""Custom exception hierarchy for the agent framework."""

from __future__ import annotations

from typing import Any, ClassVar


class AgentError(Exception):
    """Base exception for all agent errors.

    All custom exceptions in this framework inherit from this class,
    allowing for easy catching of all agent-related errors.

    Attributes:
        message: Human-readable error message.
        cause: Original exception that caused this error.
        details: Additional error context as key-value pairs.

    Details can be accessed as attributes (e.g., error.config_key).
    """

    # Map attribute names to default values when not in details
    _defaults: ClassVar[dict[str, Any]] = {}

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

    def __getattr__(self, name: str) -> Any:
        """Access details as attributes."""
        if name in self.details:
            return self.details[name]
        if name in self._defaults:
            return self._defaults[name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __str__(self) -> str:
        """Return string representation."""
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class ConfigurationError(AgentError):
    """Error in agent configuration.

    Raised when configuration is invalid, missing required fields,
    or contains incompatible settings.

    Attributes from details: config_key, expected, actual.
    """


class ModelBackendError(AgentError):
    """Error from the model backend.

    Raised when the underlying model API returns an error,
    times out, or is unavailable.

    Attributes from details: model, status_code, response_body, retryable (default: False).
    """

    _defaults: ClassVar[dict[str, Any]] = {"retryable": False}


class ToolExecutionError(AgentError):
    """Error during tool execution.

    Raised when a tool fails to execute properly, either due to
    invalid arguments, permission issues, or runtime errors.

    Attributes from details: tool_name, tool_args.
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


class ContextOverflowError(AgentError):
    """Context window exceeded.

    Raised when the conversation context exceeds the model's
    maximum context window and cannot be compacted further.

    Attributes from details: current_tokens, max_tokens, compaction_attempted (default: False).
    """

    _defaults: ClassVar[dict[str, Any]] = {"compaction_attempted": False}


class MCPError(AgentError):
    """Error from MCP server interaction.

    Raised when communication with an MCP server fails,
    the server returns an error, or authentication fails.

    Attributes from details: server_name, server_url.
    """


class RateLimitError(ModelBackendError):
    """Rate limit exceeded.

    Raised when the model API rate limit is hit.

    Attributes from details: retry_after.
    """

    _defaults: ClassVar[dict[str, Any]] = {"retryable": True}

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class AuthenticationError(AgentError):
    """Authentication failed.

    Raised when API authentication fails, typically due to
    invalid or expired credentials.
    """

    pass


class TimeoutError(AgentError):
    """Operation timed out.

    Raised when an operation exceeds its timeout limit.

    Attributes from details: timeout_seconds, operation.
    """
