"""Retry logic using tenacity."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
)

from pydantic_agent.config.retry import ErrorRecoveryConfig
from pydantic_agent.errors.exceptions import (
    AgentError,
    ModelBackendError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log retry attempt.

    Args:
        retry_state: Current retry state.
    """
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Retry attempt %d failed: %s",
        retry_state.attempt_number,
        str(exception) if exception else "Unknown error",
        extra={
            "attempt": retry_state.attempt_number,
            "exception": str(exception) if exception else None,
        },
    )


def _should_retry(exception: BaseException) -> bool:
    """Determine if an exception should trigger a retry.

    Args:
        exception: The exception to check.

    Returns:
        True if the exception should trigger a retry.
    """
    # Always retry rate limit errors
    if isinstance(exception, RateLimitError):
        return True

    # Retry ModelBackendError if marked as retryable
    if isinstance(exception, ModelBackendError):
        return exception.retryable

    # Don't retry other AgentErrors by default
    if isinstance(exception, AgentError):
        return False

    # Retry connection and timeout errors
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True

    return False


def create_retry_decorator(
    config: ErrorRecoveryConfig | None = None,
    *,
    max_attempts: int | None = None,
    base_wait: float | None = None,
    max_wait: float | None = None,
    retry_exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a retry decorator with the given configuration.

    Args:
        config: Error recovery configuration.
        max_attempts: Override max retry attempts.
        base_wait: Override base wait time in seconds.
        max_wait: Override max wait time in seconds.
        retry_exceptions: Override exceptions to retry on.

    Returns:
        Retry decorator.
    """
    if config is None:
        config = ErrorRecoveryConfig()

    # Use overrides or config values
    attempts = max_attempts if max_attempts is not None else config.max_retries + 1
    wait_base = base_wait if base_wait is not None else config.base_retry_delay
    wait_max = max_wait if max_wait is not None else config.max_retry_delay

    # Default retry exceptions if not specified
    if retry_exceptions is None:
        retry_exceptions = (RateLimitError, ConnectionError, TimeoutError)

    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=wait_base, max=wait_max),
        retry=retry_if_exception_type(retry_exceptions),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )


def create_model_retry_decorator(
    config: ErrorRecoveryConfig | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a retry decorator specifically for model API calls.

    Uses random exponential backoff to avoid thundering herd problems.

    Args:
        config: Error recovery configuration.

    Returns:
        Retry decorator for model calls.
    """
    if config is None:
        config = ErrorRecoveryConfig()

    def retry_predicate(retry_state: RetryCallState) -> bool:
        """Check if we should retry based on the exception."""
        if retry_state.outcome is None:
            return False
        exception = retry_state.outcome.exception()
        if exception is None:
            return False
        return _should_retry(exception)

    return retry(
        stop=stop_after_attempt(config.max_retries + 1),
        wait=wait_random_exponential(
            multiplier=config.base_retry_delay,
            max=config.max_retry_delay,
        ),
        retry=retry_predicate,
        before_sleep=_log_retry_attempt,
        reraise=True,
    )


class RetryContext:
    """Context manager for retry operations with metrics."""

    def __init__(
        self,
        operation_name: str,
        config: ErrorRecoveryConfig | None = None,
    ) -> None:
        """Initialize retry context.

        Args:
            operation_name: Name of the operation being retried.
            config: Error recovery configuration.
        """
        self.operation_name = operation_name
        self.config = config or ErrorRecoveryConfig()
        self.attempts = 0
        self.last_exception: Exception | None = None

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Async function to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Function result.

        Raises:
            Exception: If all retries are exhausted.
        """
        decorator = create_retry_decorator(self.config)

        @decorator
        async def wrapped() -> Any:
            self.attempts += 1
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.last_exception = e
                raise

        return await wrapped()

    def __enter__(self) -> RetryContext:
        """Enter context."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context, logging metrics."""
        if self.attempts > 1:
            logger.info(
                "Operation '%s' completed after %d attempts",
                self.operation_name,
                self.attempts,
                extra={
                    "operation": self.operation_name,
                    "attempts": self.attempts,
                    "success": exc_val is None,
                },
            )
