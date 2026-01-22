# Error Handling

Mamba Agents provides robust error handling with retry logic and circuit breaker patterns.

## Overview

The error handling system includes:

- **Custom exceptions** - Typed errors for different failure modes
- **Retry decorators** - Automatic retries with exponential backoff
- **Circuit breaker** - Prevent cascading failures
- **Configurable levels** - Conservative to aggressive retry strategies

## Exception Hierarchy

```
AgentError (base)
├── ConfigurationError - Invalid configuration
├── ModelBackendError - Model API failures
│   ├── RateLimitError - Rate limit exceeded
│   ├── AuthenticationError - Invalid credentials
│   └── ModelNotFoundError - Model unavailable
├── ToolError - Tool execution failures
├── ContextError - Context management errors
├── WorkflowError - Workflow execution failures
└── MCPError - MCP server errors
```

## Handling Exceptions

```python
from mamba_agents import Agent
from mamba_agents.errors import (
    AgentError,
    ModelBackendError,
    RateLimitError,
    AuthenticationError,
    ToolError,
)

agent = Agent("gpt-4o")

try:
    result = await agent.run("Hello")
except RateLimitError as e:
    print(f"Rate limited, retry after: {e.retry_after}s")
except AuthenticationError:
    print("Invalid API key")
except ModelBackendError as e:
    print(f"Model error: {e}")
except ToolError as e:
    print(f"Tool failed: {e.tool_name} - {e}")
except AgentError as e:
    print(f"Agent error: {e}")
```

## Retry Configuration

### Retry Levels

Three preset levels control retry aggressiveness:

| Level | Max Retries | Base Wait | Max Wait | Description |
|-------|-------------|-----------|----------|-------------|
| 1 (Conservative) | 2 | 1.0s | 10s | Few retries, quick failure |
| 2 (Balanced) | 3 | 1.0s | 30s | Default, good balance |
| 3 (Aggressive) | 5 | 0.5s | 60s | Many retries, persistent |

### Setting Retry Level

```python
from mamba_agents import AgentSettings

# Via settings
settings = AgentSettings(
    retry={"retry_level": 2, "max_retries": 3}
)

# Via environment
# MAMBA_RETRY__RETRY_LEVEL=2
# MAMBA_RETRY__MAX_RETRIES=3
```

### ErrorRecoveryConfig

```python
from mamba_agents.config import ErrorRecoveryConfig

config = ErrorRecoveryConfig(
    retry_level=2,
    max_retries=3,
    base_wait=1.0,
    max_wait=30.0,
    exponential_base=2.0,
    jitter=True,
)
```

## Retry Decorators

### Using the Decorator

```python
from mamba_agents.errors import create_retry_decorator

@create_retry_decorator(max_attempts=3, base_wait=1.0)
async def call_external_api():
    # This function will retry on failure
    response = await httpx.get("https://api.example.com")
    return response.json()
```

### Custom Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def my_function():
    ...
```

## Circuit Breaker

The circuit breaker pattern prevents cascading failures:

### Basic Usage

```python
from mamba_agents.errors import CircuitBreaker

breaker = CircuitBreaker(
    name="model-api",
    failure_threshold=5,  # Open after 5 failures
    timeout=30.0,  # Stay open for 30 seconds
)

async with breaker:
    result = await model.complete(messages)
```

### Circuit States

1. **Closed** - Normal operation, requests pass through
2. **Open** - Too many failures, requests rejected immediately
3. **Half-Open** - Testing if service recovered

### Manual Control

```python
# Check state
if breaker.is_open:
    print("Circuit is open, service unavailable")

# Get stats
stats = breaker.get_stats()
print(f"Failures: {stats.failure_count}")
print(f"Successes: {stats.success_count}")
print(f"State: {stats.state}")

# Manual reset
breaker.reset()
```

### Multiple Services

```python
# Separate breakers for different services
model_breaker = CircuitBreaker("model-api", failure_threshold=5)
mcp_breaker = CircuitBreaker("mcp-server", failure_threshold=3)

async def call_model():
    async with model_breaker:
        return await model.complete(messages)

async def call_mcp():
    async with mcp_breaker:
        return await mcp_client.call_tool(tool_name)
```

## Error Recovery Strategies

### 1. Graceful Degradation

```python
from mamba_agents.errors import ModelBackendError

async def get_response(query: str) -> str:
    try:
        # Try primary model
        result = await primary_agent.run(query)
        return result.output
    except ModelBackendError:
        # Fall back to simpler model
        result = await fallback_agent.run(query)
        return result.output
```

### 2. Retry with Backoff

```python
import asyncio
from mamba_agents.errors import RateLimitError

async def resilient_call(agent, query):
    for attempt in range(3):
        try:
            return await agent.run(query)
        except RateLimitError as e:
            if attempt < 2:
                await asyncio.sleep(e.retry_after or 1.0)
            else:
                raise
```

### 3. Circuit Breaker with Fallback

```python
from mamba_agents.errors import CircuitBreaker

breaker = CircuitBreaker("api", failure_threshold=3)

async def call_with_fallback(query):
    try:
        async with breaker:
            return await primary_api(query)
    except Exception:
        if breaker.is_open:
            return await cached_response(query)
        raise
```

## Graceful Tool Error Handling

By default, tool exceptions are automatically converted to `ModelRetry`, allowing the LLM to receive error feedback and attempt recovery instead of crashing the agent loop.

### How It Works

When a tool raises an exception:

1. The exception is caught by the agent
2. The error is formatted as `"ExceptionType: message"`
3. A `ModelRetry` is raised with this error message
4. The LLM receives the error and can retry with different parameters

```python
@agent.tool_plain
def read_file(path: str) -> str:
    """Read a file's contents."""
    return Path(path).read_text()  # FileNotFoundError handled automatically
```

If the LLM calls `read_file("missing.txt")`, it receives:
```
FileNotFoundError: [Errno 2] No such file or directory: 'missing.txt'
```

The LLM can then try a different path or ask the user for clarification.

### Configuration

Graceful error handling is enabled by default via `AgentConfig.graceful_tool_errors=True`.

```python
from mamba_agents import Agent, AgentConfig

# Default: graceful errors enabled
agent = Agent("gpt-4o")

# Disable globally for all tools
config = AgentConfig(graceful_tool_errors=False)
agent = Agent("gpt-4o", config=config)
```

### Per-Tool Override

Override the global setting for individual tools using the `graceful_errors` parameter:

```python
# This tool uses graceful errors (default)
@agent.tool_plain
def search_files(pattern: str) -> list[str]:
    """Search for files matching a pattern."""
    return glob.glob(pattern)

# This tool propagates exceptions (opt-out)
@agent.tool_plain(graceful_errors=False)
def delete_file(path: str) -> str:
    """Delete a file - failures should stop execution."""
    Path(path).unlink()
    return f"Deleted {path}"
```

### When to Disable Graceful Errors

Disable graceful error handling for tools where:

- **Failures indicate critical problems** that should stop execution
- **Side effects have already occurred** and recovery is dangerous
- **You need detailed exception information** for debugging
- **The tool is part of a transaction** that must be atomic

```python
@agent.tool_plain(graceful_errors=False)
def commit_transaction(tx_id: str) -> str:
    """Commit a database transaction - must not silently fail."""
    db.commit(tx_id)
    return "Committed"
```

### Exception Chain Preservation

When graceful error handling converts an exception, the original exception is preserved in the chain. This is useful for debugging:

```python
try:
    result = await agent.run("Read the config file")
except ModelRetry as e:
    # Access the original exception
    original = e.__cause__
    print(f"Original error: {original}")
```

## Configuration Reference

### ErrorRecoveryConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `retry_level` | int | 2 | Retry aggressiveness (1-3) |
| `max_retries` | int | 3 | Maximum retry attempts |
| `base_wait` | float | 1.0 | Initial wait between retries |
| `max_wait` | float | 30.0 | Maximum wait between retries |
| `exponential_base` | float | 2.0 | Exponential backoff base |
| `jitter` | bool | True | Add random jitter to waits |

### CircuitBreaker Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | str | Required | Unique breaker identifier |
| `failure_threshold` | int | 5 | Failures before opening |
| `timeout` | float | 30.0 | Seconds to stay open |
| `success_threshold` | int | 2 | Successes to close from half-open |

## Best Practices

### 1. Use Specific Exceptions

```python
# Good - handle specific errors
try:
    result = await agent.run(query)
except RateLimitError:
    await asyncio.sleep(60)
except AuthenticationError:
    refresh_token()
except ModelBackendError:
    use_fallback()

# Avoid - catching everything
try:
    result = await agent.run(query)
except Exception:
    pass  # Don't do this
```

### 2. Log Errors for Debugging

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = await agent.run(query)
except AgentError as e:
    logger.error(f"Agent error: {e}", exc_info=True)
    raise
```

### 3. Set Appropriate Timeouts

```python
settings = AgentSettings(
    model_backend={
        "timeout": 30.0,  # Request timeout
    },
    retry={
        "max_wait": 60.0,  # Max backoff wait
    },
)
```

## Next Steps

- [Observability](observability.md) - Monitor errors and performance
- [CircuitBreaker API](../api/errors/circuit-breaker.md) - Full reference
- [Exceptions API](../api/errors/exceptions.md) - All exception types
