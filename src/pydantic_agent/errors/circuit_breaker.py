"""Circuit breaker pattern implementation."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """States for the circuit breaker."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for the circuit breaker.

    Attributes:
        failure_threshold: Number of failures before opening circuit.
        success_threshold: Successes needed in half-open to close.
        timeout: Seconds before attempting half-open from open.
        window_size: Time window in seconds for counting failures.
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 30.0
    window_size: float = 60.0


@dataclass
class CircuitStats:
    """Statistics for circuit breaker operation.

    Attributes:
        total_calls: Total number of calls.
        successful_calls: Number of successful calls.
        failed_calls: Number of failed calls.
        rejected_calls: Number of calls rejected due to open circuit.
        state_changes: Number of state changes.
    """

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0


@dataclass
class FailureRecord:
    """Record of a single failure."""

    timestamp: float
    exception: Exception


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and rejecting calls."""

    def __init__(self, circuit_name: str, time_until_retry: float) -> None:
        """Initialize the error.

        Args:
            circuit_name: Name of the circuit breaker.
            time_until_retry: Seconds until retry is allowed.
        """
        self.circuit_name = circuit_name
        self.time_until_retry = time_until_retry
        super().__init__(
            f"Circuit '{circuit_name}' is open. "
            f"Retry in {time_until_retry:.1f} seconds."
        )


class CircuitBreaker(Generic[T]):
    """Circuit breaker for protecting against cascading failures.

    The circuit breaker monitors calls to a service and trips
    (opens) when failures exceed a threshold, preventing further
    calls until a timeout elapses.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Failures exceeded threshold, calls are rejected
    - HALF_OPEN: Testing recovery, limited calls allowed

    Example:
        breaker = CircuitBreaker("model-api")

        async def call_api():
            async with breaker:
                return await api.call()

        # Or manually:
        if breaker.allow_request():
            try:
                result = await api.call()
                breaker.record_success()
            except Exception as e:
                breaker.record_failure(e)
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize the circuit breaker.

        Args:
            name: Name for this circuit breaker.
            config: Circuit breaker configuration.
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failures: deque[FailureRecord] = deque()
        self._last_failure_time: float | None = None
        self._half_open_successes = 0
        self._stats = CircuitStats()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, transitioning if needed."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit breaker statistics."""
        return self._stats

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open."""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.config.timeout

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._stats.state_changes += 1

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_successes = 0

        logger.info(
            "Circuit '%s' transitioned from %s to %s",
            self.name,
            old_state.value,
            new_state.value,
            extra={
                "circuit": self.name,
                "old_state": old_state.value,
                "new_state": new_state.value,
            },
        )

    def _clean_old_failures(self) -> None:
        """Remove failures outside the time window."""
        now = time.time()
        window_start = now - self.config.window_size
        while self._failures and self._failures[0].timestamp < window_start:
            self._failures.popleft()

    def _count_recent_failures(self) -> int:
        """Count failures within the time window."""
        self._clean_old_failures()
        return len(self._failures)

    def allow_request(self) -> bool:
        """Check if a request should be allowed.

        Returns:
            True if the request should proceed.
        """
        current_state = self.state  # This may trigger transition

        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open
            return True
        else:  # OPEN
            return False

    def record_success(self) -> None:
        """Record a successful call."""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
                self._failures.clear()

    def record_failure(self, exception: Exception) -> None:
        """Record a failed call.

        Args:
            exception: The exception that occurred.
        """
        self._stats.total_calls += 1
        self._stats.failed_calls += 1

        now = time.time()
        self._failures.append(FailureRecord(timestamp=now, exception=exception))
        self._last_failure_time = now

        if self._state == CircuitState.HALF_OPEN:
            # Immediate trip back to open on failure in half-open
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            if self._count_recent_failures() >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def get_time_until_retry(self) -> float:
        """Get seconds until retry is allowed.

        Returns:
            Seconds until retry, 0 if allowed now.
        """
        if self._state != CircuitState.OPEN:
            return 0.0

        if self._last_failure_time is None:
            return 0.0

        elapsed = time.time() - self._last_failure_time
        remaining = self.config.timeout - elapsed
        return max(0.0, remaining)

    def reset(self) -> None:
        """Force reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failures.clear()
        self._last_failure_time = None
        self._half_open_successes = 0

    async def __aenter__(self) -> CircuitBreaker[T]:
        """Async context manager entry."""
        if not self.allow_request():
            self._stats.rejected_calls += 1
            raise CircuitBreakerOpenError(
                self.name,
                self.get_time_until_retry(),
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        if exc_val is None:
            self.record_success()
        elif isinstance(exc_val, Exception):
            self.record_failure(exc_val)

    def __enter__(self) -> CircuitBreaker[T]:
        """Sync context manager entry."""
        if not self.allow_request():
            self._stats.rejected_calls += 1
            raise CircuitBreakerOpenError(
                self.name,
                self.get_time_until_retry(),
            )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Sync context manager exit."""
        if exc_val is None:
            self.record_success()
        elif isinstance(exc_val, Exception):
            self.record_failure(exc_val)
