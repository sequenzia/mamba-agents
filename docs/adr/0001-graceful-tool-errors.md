# ADR 0001: Graceful Tool Error Handling

## Status

Accepted

## Context

When an Agent's tool call fails (e.g., `FileNotFoundError` when reading a non-existent file), the exception propagates up and crashes the agent loop. This prevents the LLM from receiving feedback about the error and potentially trying alternative approaches.

For example, if an LLM asks to read `/tmp/data.txt` and the file doesn't exist, the entire agent run fails instead of letting the LLM know about the error so it can try a different path or ask the user for clarification.

pydantic-ai provides a `ModelRetry` exception that, when raised from a tool, sends the error message back to the LLM as a retry prompt. This allows the LLM to receive error feedback and adjust its approach.

## Decision

We will implement graceful tool error handling that:

1. **Converts tool exceptions to `ModelRetry`** by default, so the LLM receives error messages
2. **Enables this behavior by default** via `AgentConfig.graceful_tool_errors = True`
3. **Allows per-tool control** via `graceful_errors` parameter on `@agent.tool()` and `@agent.tool_plain()`
4. **Passes through `ModelRetry` unchanged** to avoid double-wrapping
5. **Preserves exception chains** using `raise ModelRetry(msg) from exc`

### Configuration

**Agent-level (default):**
```python
# Enabled by default
agent = Agent("openai:gpt-4")

# Explicitly disable for all tools
config = AgentConfig(graceful_tool_errors=False)
agent = Agent("openai:gpt-4", config=config)
```

**Per-tool override:**
```python
# Opt out for critical tools that should fail loudly
@agent.tool_plain(graceful_errors=False)
def critical_tool(data: str) -> str:
    raise ValueError("Must not be silently converted")

# Opt in when agent default is disabled
@agent.tool_plain(graceful_errors=True)
def lenient_tool(data: str) -> str:
    raise IOError("Can be retried")
```

### Implementation

The wrapper function:
- Catches all exceptions except `ModelRetry`
- Formats the error as `"ExceptionType: message"`
- Logs at DEBUG level for debugging
- Raises `ModelRetry(error_msg) from exc` to preserve the exception chain
- Handles both sync and async functions using `inspect.iscoroutinefunction`
- Preserves function metadata with `@functools.wraps`

## Consequences

### Positive

- **Improved agent resilience**: Tools can fail without crashing the entire agent loop
- **Better LLM feedback**: The LLM receives error context and can attempt recovery
- **Backward compatible**: Enabled by default, but can be disabled for existing behavior
- **Fine-grained control**: Per-tool override allows critical tools to fail loudly
- **Debuggable**: Exception chains preserved, DEBUG logging available

### Negative

- **Potential infinite loops**: If an LLM keeps retrying a fundamentally broken tool, it may exhaust retries. This is mitigated by pydantic-ai's retry limits.
- **Hidden errors**: Errors that should be visible might be silently converted. The per-tool `graceful_errors=False` option addresses this.
- **Slight overhead**: Additional function wrapping, though minimal

### Neutral

- **Retry exhaustion behavior**: When retries are exhausted, pydantic-ai raises `UnexpectedModelBehavior`. This is standard pydantic-ai behavior and we do not change it.

## Alternatives Considered

### 1. Always propagate exceptions (current behavior)
Rejected because it provides poor UX for agent-based workflows where tools may fail transiently.

### 2. Return error strings instead of raising
Rejected because it changes the tool's return type and doesn't integrate with pydantic-ai's retry mechanism.

### 3. Custom exception class instead of ModelRetry
Rejected because ModelRetry is the standard pydantic-ai mechanism and provides built-in retry prompt support.

### 4. Disabled by default
Rejected because graceful error handling provides better default behavior for most agent use cases. Users who want strict error propagation can opt out.

## References

- [pydantic-ai ModelRetry documentation](https://ai.pydantic.dev/tools/#retrying)
- [pydantic-ai tools documentation](https://ai.pydantic.dev/tools/)
