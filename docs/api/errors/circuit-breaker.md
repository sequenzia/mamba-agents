# CircuitBreaker

Circuit breaker pattern for preventing cascading failures.

## Quick Example

```python
from pydantic_agent.errors import CircuitBreaker

breaker = CircuitBreaker(
    name="model-api",
    failure_threshold=5,
    timeout=30.0,
)

# Use as context manager
async with breaker:
    result = await call_api()

# Check state
if breaker.is_open:
    print("Circuit is open")

# Get stats
stats = breaker.get_stats()
print(f"Failures: {stats.failure_count}")

# Manual reset
breaker.reset()
```

## States

1. **Closed** - Normal, requests pass through
2. **Open** - Too many failures, requests rejected
3. **Half-Open** - Testing if service recovered

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | str | Required | Unique identifier |
| `failure_threshold` | int | 5 | Failures to open |
| `timeout` | float | 30.0 | Seconds to stay open |
| `success_threshold` | int | 2 | Successes to close |

## API Reference

::: pydantic_agent.errors.circuit_breaker.CircuitBreaker
    options:
      show_root_heading: true
      show_source: true
