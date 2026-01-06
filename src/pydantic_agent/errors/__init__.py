"""Error handling and recovery."""

from pydantic_agent.errors.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    CircuitStats,
)
from pydantic_agent.errors.exceptions import (
    AgentError,
    AuthenticationError,
    ConfigurationError,
    ContextOverflowError,
    MCPError,
    ModelBackendError,
    RateLimitError,
    TimeoutError,
    ToolExecutionError,
)
from pydantic_agent.errors.retry import (
    RetryContext,
    create_model_retry_decorator,
    create_retry_decorator,
)

__all__ = [
    # Exceptions
    "AgentError",
    "ConfigurationError",
    "ModelBackendError",
    "ToolExecutionError",
    "ContextOverflowError",
    "MCPError",
    "RateLimitError",
    "AuthenticationError",
    "TimeoutError",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "CircuitState",
    "CircuitStats",
    # Retry
    "create_retry_decorator",
    "create_model_retry_decorator",
    "RetryContext",
]
