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

# Load settings from env vars, .env, ~/agents.env, config.toml
settings = AgentSettings()

# Create agent using settings (model, api_key, base_url from settings)
agent = Agent(settings=settings)

# Or override the model while using other settings (api_key, base_url)
agent = Agent("gpt-4o", settings=settings)

# Or use a model string directly (requires OPENAI_API_KEY env var)
agent = Agent("gpt-4o")

# Run the agent - context and usage are tracked automatically
result = await agent.run("What files are in the current directory?")
print(result.output)

# Multi-turn conversation - context is maintained automatically
result2 = await agent.run("Can you list only the Python files?")
print(result2.output)

# Check usage and cost
print(agent.get_usage())  # TokenUsage(prompt_tokens=..., request_count=2)
print(agent.get_cost())   # Cost in USD

# Access context state
print(agent.get_context_state())  # ContextState(token_count=..., message_count=...)
```

## Configuration

### Environment Variables

All settings use the `AGENTS_` prefix. Variables can be set in:
- Environment variables
- `.env` file (project-specific)
- `~/agents.env` (user-wide defaults)

```bash
# Model configuration
AGENTS_MODEL_BACKEND__MODEL=gpt-4o
AGENTS_MODEL_BACKEND__API_KEY=sk-...
AGENTS_MODEL_BACKEND__BASE_URL=https://api.openai.com/v1

# Logging
AGENTS_LOGGING__LEVEL=INFO
AGENTS_LOGGING__FORMAT=json

# Retry behavior
AGENTS_RETRY__MAX_RETRIES=3
AGENTS_RETRY__RETRY_LEVEL=2
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

| Tool | Description |
|------|-------------|
| `read_file` | Read contents of a file |
| `write_file` | Write or overwrite a file |
| `append_file` | Append content to a file |
| `list_directory` | List contents of a directory with metadata |
| `file_info` | Get file or directory metadata (size, modified, created) |
| `delete_file` | Delete a file |
| `move_file` | Move or rename a file |
| `copy_file` | Copy a file |
| `glob_search` | Find files matching a glob pattern (e.g., `**/*.py`) |
| `grep_search` | Search file contents for a pattern with context lines |
| `run_bash` | Execute a shell command with timeout support |

### Usage Examples

```python
from pydantic_agent.tools import (
    read_file, write_file, list_directory,
    glob_search, grep_search, run_bash,
)

# File operations
content = read_file("config.json")
write_file("output.txt", "Hello, World!")
entries = list_directory("/project", recursive=True)

# Search for files by pattern
py_files = glob_search("**/*.py", root_dir="/project")

# Search file contents
matches = grep_search(
    pattern=r"def \w+",
    path="/project",
    file_pattern="*.py",
    context_lines=2,
)

# Run shell commands
result = run_bash("ls -la", timeout=30)
print(result.stdout)
```

### Security Sandbox

```python
from pydantic_agent.tools.filesystem import FilesystemSecurity

security = FilesystemSecurity(
    sandbox_mode=True,
    base_directory="/safe/path",
    allowed_extensions=[".txt", ".json", ".py"],
)

# Pass security context to tools
content = read_file("data.txt", security=security)
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

Context is managed automatically by the Agent. Messages are tracked across runs and auto-compacted when thresholds are reached.

### Built-in Agent Context (Recommended)

```python
from pydantic_agent import Agent, AgentConfig, CompactionConfig

# Context tracking is enabled by default
agent = Agent("gpt-4o", settings=settings)

# Run multiple turns - context is maintained automatically
agent.run_sync("Hello, I'm working on a Python project")
agent.run_sync("Can you help me refactor the main function?")

# Access context via Agent methods
messages = agent.get_messages()           # Get all tracked messages
state = agent.get_context_state()         # Get token count, message count
should_compact = agent.should_compact()   # Check if threshold reached

# Manual compaction
result = await agent.compact()
print(f"Removed {result.removed_count} messages")

# Clear context for new conversation
agent.clear_context()

# Customize compaction settings
config = AgentConfig(
    context=CompactionConfig(
        strategy="hybrid",
        trigger_threshold_tokens=50000,
        target_tokens=40000,
    ),
    auto_compact=True,  # Auto-compact when threshold reached (default)
)
agent = Agent("gpt-4o", settings=settings, config=config)

# Disable context tracking if not needed
config = AgentConfig(track_context=False)
agent = Agent("gpt-4o", settings=settings, config=config)
```

### Standalone Context Manager

For advanced use cases, you can use ContextManager directly:

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

Usage tracking and cost estimation are built into the Agent. Every run automatically records token usage.

### Built-in Agent Tracking (Recommended)

```python
from pydantic_agent import Agent

agent = Agent("gpt-4o", settings=settings)

# Run some queries
agent.run_sync("Hello!")
agent.run_sync("Tell me about Python")
agent.run_sync("What are decorators?")

# Get aggregate usage
usage = agent.get_usage()
print(f"Total tokens: {usage.total_tokens}")
print(f"Requests: {usage.request_count}")

# Get cost estimate
cost = agent.get_cost()
print(f"Estimated cost: ${cost:.4f}")

# Get detailed breakdown
breakdown = agent.get_cost_breakdown()
print(f"Prompt cost: ${breakdown.prompt_cost:.4f}")
print(f"Completion cost: ${breakdown.completion_cost:.4f}")

# Get per-request history
history = agent.get_usage_history()
for record in history:
    print(f"{record.timestamp}: {record.total_tokens} tokens")

# Reset tracking for new session
agent.reset_tracking()

# Count tokens for arbitrary text
count = agent.get_token_count("Hello, world!")
```

### Standalone Token Utilities

For advanced use cases, you can use the token utilities directly:

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
