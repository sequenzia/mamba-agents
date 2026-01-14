# Errors Module

Exception classes and error handling utilities.

## Classes

| Class | Description |
|-------|-------------|
| [Exceptions](exceptions.md) | Exception hierarchy |
| [CircuitBreaker](circuit-breaker.md) | Circuit breaker pattern |
| [Retry](retry.md) | Retry decorators |

## Quick Example

```python
from pydantic_agent.errors import (
    AgentError,
    ModelBackendError,
    RateLimitError,
    CircuitBreaker,
    create_retry_decorator,
)

# Handle exceptions
try:
    result = await agent.run(query)
except RateLimitError as e:
    await asyncio.sleep(e.retry_after)
except ModelBackendError:
    use_fallback()

# Circuit breaker
breaker = CircuitBreaker("api", failure_threshold=5)
async with breaker:
    result = await call_api()
```

## Imports

```python
from pydantic_agent.errors import (
    AgentError,
    ModelBackendError,
    RateLimitError,
    AuthenticationError,
    ToolError,
    CircuitBreaker,
    create_retry_decorator,
)
```
