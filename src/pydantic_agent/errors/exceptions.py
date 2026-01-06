"""Custom exception hierarchy for the agent framework."""

from __future__ import annotations

from typing import Any


class AgentError(Exception):
    """Base exception for all agent errors.

    All custom exceptions in this framework inherit from this class,
    allowing for easy catching of all agent-related errors.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            message: Human-readable error message.
            details: Additional error context.
            cause: Original exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

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

    def __init__(
        self,
        message: str,
        *,
        config_key: str | None = None,
        expected: Any = None,
        actual: Any = None,
        **kwargs: Any,
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Error message.
            config_key: The configuration key that caused the error.
            expected: Expected value or type.
            actual: Actual value received.
            **kwargs: Additional arguments passed to AgentError.
        """
        details = kwargs.pop("details", {})
        if config_key:
            details["config_key"] = config_key
        if expected is not None:
            details["expected"] = expected
        if actual is not None:
            details["actual"] = actual

        super().__init__(message, details=details, **kwargs)
        self.config_key = config_key
        self.expected = expected
        self.actual = actual


class ModelBackendError(AgentError):
    """Error from the model backend.

    Raised when the underlying model API returns an error,
    times out, or is unavailable.
    """

    def __init__(
        self,
        message: str,
        *,
        model: str | None = None,
        status_code: int | None = None,
        response_body: str | None = None,
        retryable: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize model backend error.

        Args:
            message: Error message.
            model: Model that caused the error.
            status_code: HTTP status code if applicable.
            response_body: Response body from the API.
            retryable: Whether this error can be retried.
            **kwargs: Additional arguments passed to AgentError.
        """
        details = kwargs.pop("details", {})
        if model:
            details["model"] = model
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body
        details["retryable"] = retryable

        super().__init__(message, details=details, **kwargs)
        self.model = model
        self.status_code = status_code
        self.response_body = response_body
        self.retryable = retryable


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
        """Initialize tool execution error.

        Args:
            message: Error message.
            tool_name: Name of the tool that failed.
            tool_args: Arguments passed to the tool.
            **kwargs: Additional arguments passed to AgentError.
        """
        details = kwargs.pop("details", {})
        if tool_name:
            details["tool_name"] = tool_name
        if tool_args:
            # Redact potentially sensitive values
            details["tool_args"] = {
                k: "[REDACTED]" if "key" in k.lower() or "secret" in k.lower() else v
                for k, v in tool_args.items()
            }

        super().__init__(message, details=details, **kwargs)
        self.tool_name = tool_name
        self.tool_args = tool_args


class ContextOverflowError(AgentError):
    """Context window exceeded.

    Raised when the conversation context exceeds the model's
    maximum context window and cannot be compacted further.
    """

    def __init__(
        self,
        message: str,
        *,
        current_tokens: int | None = None,
        max_tokens: int | None = None,
        compaction_attempted: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize context overflow error.

        Args:
            message: Error message.
            current_tokens: Current token count.
            max_tokens: Maximum allowed tokens.
            compaction_attempted: Whether compaction was tried.
            **kwargs: Additional arguments passed to AgentError.
        """
        details = kwargs.pop("details", {})
        if current_tokens:
            details["current_tokens"] = current_tokens
        if max_tokens:
            details["max_tokens"] = max_tokens
        details["compaction_attempted"] = compaction_attempted

        super().__init__(message, details=details, **kwargs)
        self.current_tokens = current_tokens
        self.max_tokens = max_tokens
        self.compaction_attempted = compaction_attempted


class MCPError(AgentError):
    """Error from MCP server interaction.

    Raised when communication with an MCP server fails,
    the server returns an error, or authentication fails.
    """

    def __init__(
        self,
        message: str,
        *,
        server_name: str | None = None,
        server_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize MCP error.

        Args:
            message: Error message.
            server_name: Name of the MCP server.
            server_url: URL of the MCP server.
            **kwargs: Additional arguments passed to AgentError.
        """
        details = kwargs.pop("details", {})
        if server_name:
            details["server_name"] = server_name
        if server_url:
            details["server_url"] = server_url

        super().__init__(message, details=details, **kwargs)
        self.server_name = server_name
        self.server_url = server_url


class RateLimitError(ModelBackendError):
    """Rate limit exceeded.

    Raised when the model API rate limit is hit.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message.
            retry_after: Seconds to wait before retrying.
            **kwargs: Additional arguments passed to ModelBackendError.
        """
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after"] = retry_after


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

    def __init__(
        self,
        message: str,
        *,
        timeout_seconds: float | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize timeout error.

        Args:
            message: Error message.
            timeout_seconds: The timeout that was exceeded.
            operation: Name of the operation that timed out.
            **kwargs: Additional arguments passed to AgentError.
        """
        details = kwargs.pop("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        if operation:
            details["operation"] = operation

        super().__init__(message, details=details, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.operation = operation
