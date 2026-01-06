# Pydantic Agent

A simple, extensible AI Agent framework built on [pydantic-ai](https://ai.pydantic.dev/).

## Features

- **Simple Agent Loop** - Thin wrapper around pydantic-ai with tool-calling support
- **Built-in Tools** - Filesystem, glob, grep, and bash operations with security controls
- **MCP Integration** - Connect to Model Context Protocol servers (stdio and SSE transports)
- **Token Management** - Track usage with tiktoken, estimate costs
- **Context Compaction** - 5 strategies to manage long conversations
- **Model Backends** - OpenAI-compatible adapter for Ollama, vLLM, LM Studio
- **Observability** - Structured logging, tracing, and OpenTelemetry hooks
- **Error Handling** - Retry logic with tenacity, circuit breaker pattern

## Installation

```bash
# Using uv (recommended)
uv add pydantic-agent

# Using pip
pip install pydantic-agent
```

## Quick Start

```python
from pydantic_agent import Agent, AgentSettings

# Create an agent with default settings
agent = Agent(model="gpt-4o")

# Or load from configuration
settings = AgentSettings()  # Reads from env vars, .env, config.toml
agent = Agent.from_settings(settings)

# Run the agent
result = await agent.run("What files are in the current directory?")
print(result.output)
```

## Configuration

### Environment Variables

All settings use the `AGENT_` prefix:

```bash
# Model configuration
AGENT_MODEL_BACKEND__MODEL=gpt-4o
AGENT_MODEL_BACKEND__API_KEY=sk-...
AGENT_MODEL_BACKEND__BASE_URL=https://api.openai.com/v1

# Logging
AGENT_LOGGING__LEVEL=INFO
AGENT_LOGGING__FORMAT=json

# Retry behavior
AGENT_RETRY__MAX_RETRIES=3
AGENT_RETRY__RETRY_LEVEL=2
```

### TOML Configuration

Create a `config.toml` file:

```toml
[model_backend]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"

[logging]
level = "INFO"
format = "json"
redact_sensitive = true

[retry]
max_retries = 3
retry_level = 2

[context]
strategy = "hybrid"
trigger_threshold_tokens = 100000
target_tokens = 80000
```

## Built-in Tools

### Filesystem Tools

```python
from pydantic_agent.tools.filesystem import (
    read_file,
    write_file,
    append_file,
    list_directory,
    file_info,
    delete_file,
    move_file,
    copy_file,
)

# Tools are automatically registered when using the agent
agent = Agent(model="gpt-4o")

# With security sandbox
from pydantic_agent.tools.filesystem import FilesystemSecurity

security = FilesystemSecurity(
    sandbox_mode=True,
    base_directory="/safe/path",
    allowed_extensions=[".txt", ".json", ".py"],
)
```

### Glob and Grep

```python
from pydantic_agent.tools import glob_search, grep_search

# Search for files
files = await glob_search("**/*.py", base_path="/project")

# Search file contents
matches = await grep_search(
    pattern=r"def \w+",
    path="/project",
    file_pattern="*.py",
    max_results=100,
)
```

### Bash Tool

```python
from pydantic_agent.tools import run_bash

result = await run_bash(
    command="ls -la",
    timeout=30.0,
    allowed_commands=["ls", "cat", "echo"],
)
```

## MCP Integration

Connect to Model Context Protocol servers:

```python
from pydantic_agent.mcp import MCPServerConfig, MCPClientManager

# Configure MCP servers
servers = [
    MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    ),
    MCPServerConfig(
        name="web",
        transport="sse",
        url="http://localhost:8080/sse",
    ),
]

# Connect and get tools
async with MCPClientManager(servers) as manager:
    toolsets = manager.get_toolsets()
    # Use tools in your agent
```

## Context Management

Manage long conversations with compaction strategies:

```python
from pydantic_agent.context import (
    ContextManager,
    CompactionConfig,
    SlidingWindowStrategy,
    SummarizeOlderStrategy,
    HybridStrategy,
)

# Configure compaction
config = CompactionConfig(
    strategy="hybrid",  # or sliding_window, summarize_older, etc.
    trigger_threshold_tokens=100000,
    target_tokens=80000,
    preserve_recent_turns=5,
)

manager = ContextManager(config=config)

# Add messages
manager.add_messages([
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"},
])

# Check if compaction is needed
if manager.should_compact():
    result = await manager.compact()
    print(f"Removed {result.removed_count} messages")
```

### Available Strategies

| Strategy | Description |
|----------|-------------|
| `sliding_window` | Remove oldest messages beyond threshold |
| `summarize_older` | LLM-based summarization of older messages |
| `selective_pruning` | Remove completed tool call/result pairs |
| `importance_scoring` | LLM-based scoring, prune lowest importance |
| `hybrid` | Combine multiple strategies in sequence |

## Token Management

Track token usage and estimate costs:

```python
from pydantic_agent.tokens import TokenCounter, UsageTracker, CostEstimator

# Count tokens
counter = TokenCounter(encoding="cl100k_base")
count = counter.count("Hello, world!")
msg_count = counter.count_messages([{"role": "user", "content": "Hi"}])

# Track usage across requests
tracker = UsageTracker()
tracker.record_usage(input_tokens=100, output_tokens=50, model="gpt-4o")
summary = tracker.get_summary()

# Estimate costs
estimator = CostEstimator()
cost = estimator.estimate(input_tokens=1000, output_tokens=500, model="gpt-4o")
```

## Model Backends

Use local models with OpenAI-compatible APIs:

```python
from pydantic_agent.backends import (
    OpenAICompatibleBackend,
    create_ollama_backend,
    create_vllm_backend,
    create_lmstudio_backend,
    get_profile,
)

# Ollama
backend = create_ollama_backend("llama3.2")

# vLLM
backend = create_vllm_backend("meta-llama/Llama-3.2-3B-Instruct")

# LM Studio
backend = create_lmstudio_backend()

# Custom OpenAI-compatible
backend = OpenAICompatibleBackend(
    model="my-model",
    base_url="http://localhost:8000/v1",
    api_key="optional-key",
)

# Check model capabilities
profile = get_profile("gpt-4o")
print(f"Context window: {profile.context_window}")
print(f"Supports tools: {profile.supports_tools}")
```

## Error Handling

Robust error handling with retry and circuit breaker:

```python
from pydantic_agent.errors import (
    AgentError,
    ModelBackendError,
    RateLimitError,
    CircuitBreaker,
    create_retry_decorator,
)

# Custom retry decorator
@create_retry_decorator(max_attempts=3, base_wait=1.0)
async def call_api():
    ...

# Circuit breaker for external services
breaker = CircuitBreaker("model-api", failure_threshold=5, timeout=30.0)

async with breaker:
    result = await model.complete(messages)
```

## Observability

Structured logging and tracing:

```python
from pydantic_agent.observability import (
    setup_logging,
    RequestTracer,
    get_otel_integration,
)
from pydantic_agent.config import LoggingConfig

# Configure logging
config = LoggingConfig(
    level="INFO",
    format="json",
    redact_sensitive=True,
)
logger = setup_logging(config)

# Request tracing
tracer = RequestTracer()
tracer.start_trace()

with tracer.start_span("agent.run") as span:
    span.set_attribute("prompt_length", len(prompt))
    result = await agent.run(prompt)

trace = tracer.end_trace()

# OpenTelemetry (optional)
otel = get_otel_integration()
if otel.initialize():
    with otel.trace_agent_run(prompt, model="gpt-4o"):
        result = await agent.run(prompt)
```

## Development

```bash
# Clone the repository
git clone https://github.com/sequenzia/pydantic-agent.git
cd pydantic-agent

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=pydantic_agent

# Format code
uv run ruff format

# Lint code
uv run ruff check --fix
```

## License

MIT
