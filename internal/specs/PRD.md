# AI Agent Framework - Core Requirements Document

## 1. Overview

### 1.1 Purpose

This document defines the requirements for a simple, extensible AI Agent framework. The framework enables developers to build production-grade autonomous agents capable of tool use while maintaining observability and control over execution.

### 1.2 Scope

The framework provides:

- A simple agent that calls tools in a loop until task completion
- Built-in tooling for common operations (filesystem, search, shell execution)
- Integration points for custom tools and Model Context Protocol (MCP) servers
- Comprehensive context window and token management
- Compatibility with locally hosted models exposing OpenAI-compatible APIs

### 1.3 Target Users

- ML Engineers building custom agent applications
- Developers integrating agentic capabilities into existing systems

---

## 2. Goals and Non-Goals

### 2.1 Goals

- Provide a simple foundation for building tool-calling agents
- Enable seamless integration with local LLM deployments (Ollama, vLLM, llama.cpp, etc.)
- Offer first-class support for tool use, including dynamic tool registration and MCP server integration
- Maintain full observability into agent state, token consumption, and context evolution

### 2.2 Non-Goals

- This framework will not provide pre-built, domain-specific agents (e.g., coding assistants, research agents)
- This framework will not include a graphical user interface for agent management
- This framework will not handle model hosting or deployment
- This framework will not provide built-in vector storage or RAG capabilities (these can be added via tools)

---

## 3. Core Framework Components

The framework consists of the following core components:

| Component | Description |
|-----------|-------------|
| Project Structure | UV workspace setup, dependency management, package configuration |
| Configuration System | Pydantic Settings integration, environment variable handling, config file support |
| Model Backend Layer | OpenAI-compatible API adapter, connection management, streaming support |
| Tool System | Tool registration, execution engine, built-in tools (filesystem, bash, web search) |
| MCP Integration | MCP client implementation, server lifecycle management, tool discovery |
| Token Management | Token counting with tiktoken, usage tracking, cost estimation |
| Context Management | Message history, context window tracking, compaction strategy interface |
| Logging & Observability | Structured logging, request tracing, OpenTelemetry hooks |
| Error Handling | Retry logic with tenacity, circuit breakers, error classification |

### 3.1 Deliverables

- Fully functional core framework with all infrastructure components
- Comprehensive test suite for core components (90%+ coverage)
- API documentation for all public interfaces
- Clean ty/mypy checks on all modules

---

## 4. Technology Stack

| Component | Tool | Purpose | Documentation |
|:----------|:-----|:--------|:--------------|
| **LLM Agent Framework & Interface** | `pydantic-ai` | LLM Interface, agent orchestration, tool definitions, structured outputs | [Pydantic AI](https://ai.pydantic.dev/) |
| **Validation** | `pydantic` | Runtime data validation, automatic error parsing, and strict schema enforcement | [Pydantic](https://docs.pydantic.dev/latest/) |
| **Configuration** | `pydantic-settings` | Type-safe configuration management (environment variables, `.env` files) | [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings) |
| **Environment Files** | `python-dotenv` | Loads key-value pairs from a `.env` file into environment variables so your Python code can access configuration and secrets without hardcoding them | [python-dotenv](https://saurabh-kumar.com/python-dotenv/) |
| **HTTP Client** | `httpx` | Native async support, HTTP/2, strictly typed, and broadly compatible with `requests` API | [HTTPX](https://www.python-httpx.org/) |
| **Retries** | `tenacity` | Decorator-based retry logic with composable stop/wait conditions | [Tenacity](https://tenacity.readthedocs.io/en/latest/) |
| **Tokenizer** | `tiktoken` | Token counting and context window management | [tiktoken](https://github.com/openai/tiktoken) |
| **Testing** | `respx` | Specifically designed to mock `httpx` requests; superior to standard `unittest.mock` | [RESPX](https://lundberg.github.io/respx/) |
| **Package Manager** | `uv` | Fast Python package installer and resolver | [UV](https://docs.astral.sh/uv/) |
| **Formatter & Linter** | `ruff` | Extremely fast Python linter and formatter written in Rust | [Ruff](https://docs.astral.sh/ruff/) |
| **Type Checker** | `ty` | Extremely fast Python type checker and language server written in Rust | [ty](https://docs.astral.sh/ty/) |

---

## 5. Functional Requirements

### 5.1 Agent Execution Loop

The agent operates as a simple tool-calling loop:

1. Receive task/message from user
2. Send message history to LLM with available tools
3. If LLM returns tool call(s) → execute tool(s) → append results → go to step 2
4. If LLM returns final response → return to user
5. Stop on: final response, `max_iterations` reached, or error

#### 5.1.1 Agent Configuration

```python
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """Configuration for agent execution."""
    max_iterations: int = 10  # Maximum tool-calling iterations
    system_prompt: str = ""   # System prompt for the agent
```

#### 5.1.2 Execution Flow

```
┌─────────────┐
│  User Task  │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Send to LLM     │◄────────────────┐
│  with tools      │                 │
└──────┬───────────┘                 │
       │                             │
       ▼                             │
   ┌───────────┐                     │
   │ Tool Call?│──── Yes ──► Execute │
   └───────────┘             Tool(s) │
       │                       │     │
       No                      └─────┘
       │
       ▼
┌──────────────┐
│ Return Final │
│   Response   │
└──────────────┘
```

### 5.2 Project and Dependency Management

| Requirement | Specification |
|-------------|---------------|
| Package Manager | UV (astral-sh/uv) |
| Project Structure | UV workspace support for monorepo compatibility |
| Python Version | 3.12+ |
| Lock File | `uv.lock` for reproducible builds |
| Dependency Groups | Separate groups for core, dev, and optional integrations |

### 5.3 Model Backend Compatibility

The framework must work with any model backend exposing an OpenAI-compatible API:

- **Required Compatibility**: `/v1/chat/completions` endpoint
- **Configuration Options**:
  - Base URL (required)
  - API key (optional, for authenticated endpoints)
  - Model identifier
  - Default generation parameters (temperature, max_tokens, top_p, etc.)
- **Tested Backends**: Ollama, vLLM, llama.cpp server, LM Studio, LocalAI
- **Streaming Support**: Must support both streaming and non-streaming responses for model outputs and tool results

#### 5.3.1 Streaming Configuration

| Component | Streamable | Description |
|-----------|------------|-------------|
| Model responses | Yes | Token-by-token streaming of LLM output |
| Tool results | Yes | Streaming output from long-running tools (e.g., bash commands, file reads) |
| Final response | Yes | Complete agent response stream |

**Streaming Configuration**:
```python
StreamingConfig(
    stream_model_responses=True,    # Stream LLM token output
    stream_tool_results=True,       # Stream tool execution output
    chunk_size=1024,                # Bytes per chunk for tool streaming
)
```

### 5.4 Built-in Tools

All built-in tools must follow Pydantic AI's tool definition patterns and include comprehensive error handling.

#### 5.4.1 Filesystem Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `read_file` | Read contents of a file | `path: str`, `encoding: str = "utf-8"` |
| `write_file` | Write or overwrite a file | `path: str`, `content: str`, `encoding: str = "utf-8"` |
| `append_file` | Append content to a file | `path: str`, `content: str` |
| `list_directory` | List contents of a directory | `path: str`, `recursive: bool = False`, `max_depth: int = 2` |
| `file_info` | Get file metadata | `path: str` |
| `delete_file` | Delete a file | `path: str`, `require_confirmation: bool = True` |
| `move_file` | Move or rename a file | `source: str`, `destination: str` |
| `copy_file` | Copy a file | `source: str`, `destination: str` |

**Security Requirements**:
- Configurable base directory restriction (sandbox mode)
- Path traversal prevention
- Optional file size limits for read operations
- Configurable allowed/denied file extensions

#### 5.4.2 Glob Tool

| Tool | Description | Parameters |
|------|-------------|------------|
| `glob_search` | Find files matching a pattern | `pattern: str`, `root_dir: str = "."`, `recursive: bool = True` |

**Requirements**:
- Support standard glob syntax (`*`, `**`, `?`, `[...]`)
- Return relative or absolute paths (configurable)
- Configurable result limit
- Respect gitignore patterns (optional)

#### 5.4.3 Grep Tool

| Tool | Description | Parameters |
|------|-------------|------------|
| `grep_search` | Search file contents | `pattern: str`, `path: str`, `recursive: bool = True`, `file_pattern: str = "*"`, `context_lines: int = 0`, `ignore_case: bool = False`, `regex: bool = True` |

**Requirements**:
- Support both literal string and regex patterns
- Return matched lines with file paths and line numbers
- Configurable context lines (before/after matches)
- Binary file detection and skipping
- Configurable result limit

#### 5.4.4 Bash Tool

| Tool | Description | Parameters |
|------|-------------|------------|
| `run_bash` | Execute a shell command | `command: str`, `working_dir: str = "."`, `timeout: int = 30`, `env: dict = None` |

**Requirements**:
- Capture stdout, stderr, and return code
- Configurable timeout with graceful termination
- Environment variable injection
- Working directory specification
- Optional command allowlist/denylist for security

**Security Requirements**:
- Configurable restricted mode (limit to specific commands)
- Shell injection prevention guidance in documentation
- Optional confirmation requirement for destructive commands

#### 5.4.5 Web Search Tool

| Tool | Description | Parameters |
|------|-------------|------------|
| `web_search` | Search the web | `query: str`, `num_results: int = 10`, `search_type: str = "general"` |

**Requirements**:
- Pluggable search backend (default implementation required)
- Supported backends: SearXNG (self-hosted), Tavily API, Brave Search API, SerpAPI
- Return structured results (title, URL, snippet)
- Rate limiting support
- Result caching (optional, configurable TTL)

### 5.5 Custom Tool Support

#### 5.5.1 Tool Registration

- Tools defined as decorated Python functions (following Pydantic AI patterns)
- Tools defined as Pydantic models with `__call__` method
- Dynamic tool registration at runtime
- Tool enable/disable without removal
- Tool grouping and namespacing

#### 5.5.2 MCP Server Integration

| Requirement | Specification |
|-------------|---------------|
| Transport | stdio and HTTP/SSE transports |
| Discovery | Automatic tool discovery from MCP server capabilities |
| Lifecycle | Managed server lifecycle (start, health check, shutdown) |
| Configuration | YAML or JSON configuration for server definitions |
| Multiple Servers | Support for connecting to multiple MCP servers simultaneously |
| Authentication | API key authentication for secured MCP servers |

**MCP Configuration Example**:
```yaml
mcp_servers:
  - name: filesystem
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed"]
    transport: stdio
  - name: custom-api
    url: http://localhost:8080/mcp
    transport: sse
    auth:
      type: api_key
      key_env: MCP_CUSTOM_API_KEY  # Environment variable containing the API key
      header: X-API-Key            # Header name for the API key (default: Authorization)
  - name: secured-service
    url: https://api.example.com/mcp
    transport: sse
    auth:
      type: api_key
      key: ${SECURED_SERVICE_KEY}  # Direct reference to environment variable
```

**Authentication Configuration**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | `str` | Authentication type (`api_key`) |
| `key_env` | `str` | Environment variable name containing the API key |
| `key` | `str` | Direct key value or environment variable reference (`${VAR_NAME}`) |
| `header` | `str` | HTTP header name for the key (default: `Authorization` with `Bearer` prefix) |

### 5.6 Token Usage Tracking

#### 5.6.1 Token Counting Implementation

Token counting uses **tiktoken** for approximate token estimation. This provides fast, local token counting without requiring model backend calls.

| Configuration | Description |
|---------------|-------------|
| `tokenizer` | Tiktoken encoding to use (default: `cl100k_base` for GPT-4 compatibility) |
| `fallback_encoding` | Fallback if model-specific encoding unavailable |
| `count_special_tokens` | Include special tokens in count (default: `True`) |

**Tokenizer Configuration**:
```python
TokenizerConfig(
    encoding="cl100k_base",      # Default tiktoken encoding
    model_mapping={              # Optional model-specific encodings
        "llama": "cl100k_base",
        "mistral": "cl100k_base",
    },
    cache_tokenizer=True,        # Cache tokenizer instance for performance
)
```

**Note**: Token counts are approximate and may vary slightly from actual model tokenization. For context window management, counts include a configurable safety margin (default: 5%) to prevent overflow.

#### 5.6.2 Metrics Captured

| Metric | Description |
|--------|-------------|
| `prompt_tokens` | Tokens in the prompt/context |
| `completion_tokens` | Tokens in the model response |
| `total_tokens` | Sum of prompt and completion tokens |
| `cached_tokens` | Tokens served from cache (if applicable) |

#### 5.6.3 Tracking Granularity

- Per-request token counts
- Per-agent cumulative totals
- Per-tool-call attribution (when identifiable)
- Session-level aggregates

#### 5.6.4 Cost Estimation

- Configurable cost-per-token rates
- Estimated cost calculation per request and cumulative
- Cost alerts/limits (optional)

### 5.7 Context Window Management

#### 5.7.1 State Tracking

| Component | Description |
|-----------|-------------|
| System Prompt | Tracked separately, always preserved |
| Message History | Full conversation history with roles |
| Tool Definitions | Current tool schemas |
| Pending Tool Results | Tool calls awaiting results |

#### 5.7.2 Context Compaction Strategies

The framework must support configurable compaction strategies triggered by token thresholds:

| Strategy | Description |
|----------|-------------|
| `sliding_window` | Remove oldest messages beyond a count threshold |
| `summarize_older` | Summarize messages older than N turns, keep recent verbatim |
| `selective_pruning` | Remove tool call/result pairs for completed operations |
| `importance_scoring` | LLM-based importance scoring, prune lowest scored messages |
| `hybrid` | Combination of strategies with configurable weights |

#### 5.7.3 Compaction Configuration

```python
# Example configuration structure
CompactionConfig(
    strategy="summarize_older",
    trigger_threshold_tokens=100000,
    target_tokens=80000,
    preserve_recent_turns=10,
    preserve_system_prompt=True,
    summarization_model="same"  # or specify different model
)
```

### 5.8 Helper Functions and Observability

#### 5.8.1 Context Inspection

| Function | Returns |
|----------|---------|
| `get_context_state()` | Current messages, token counts, compaction history |
| `get_message_history()` | Full or filtered message list |
| `get_system_prompt()` | Current system prompt |
| `get_active_tools()` | List of currently enabled tools |

#### 5.8.2 Token Usage Inspection

| Function | Returns |
|----------|---------|
| `get_token_usage()` | Current session token metrics |
| `get_token_breakdown()` | Per-component token attribution |
| `get_cost_estimate()` | Estimated cost based on configured rates |
| `get_usage_history()` | Time-series of token usage |

#### 5.8.3 Agent State Inspection

| Function | Returns |
|----------|---------|
| `get_agent_state()` | Current execution state, pending actions |
| `get_execution_trace()` | Full trace of tool calls and results |

---

## 6. Developer Experience

### 6.1 Type Hints

- Complete type annotations for all public APIs
- Support for type checkers (mypy, pyright, pyrefly, ty)
- Generic types for flexibility with Pydantic models
- Typed dictionaries for complex parameter objects
- `py.typed` marker file for PEP 561 compliance

### 6.2 Logging

Integration with Python's standard logging module with optional structured logging support.

#### 6.2.1 Log Levels

| Level | Events |
|-------|--------|
| **DEBUG** | Full request/response details (headers, body samples) |
| **INFO** | Request method, URL, and response status |
| **WARNING** | Retries, slow responses, deprecation notices |
| **ERROR** | Fatal errors, connection failures |

#### 6.2.2 Log Configuration

```python
LoggingConfig(
    level="INFO",                          # Default log level
    structured=False,                      # Enable JSON format logging
    include_request_body=False,            # Opt-in request body logging
    include_response_body=False,           # Opt-in response body logging
    body_size_limit=1024,                  # Max bytes to log for bodies
    include_correlation_id=True,           # Include correlation IDs
    
    # Sensitive data redaction
    redact_authorization=True,             # Redact auth headers (default)
    redact_api_keys=True,                  # Redact API keys in query params
    sensitive_patterns=[                   # Custom regex patterns to redact
        r"password=\S+",
        r"secret=\S+",
    ],
)
```

### 6.3 Observability

Built-in observability features for monitoring and debugging agent behavior.

| Feature | Description |
|---------|-------------|
| Request ID Generation | Automatic ID generation (configurable: UUID4, ULID) |
| Trace Context Propagation | Support for `traceparent`, `tracestate`, `X-Request-ID` headers |
| OpenTelemetry Integration | Optional instrumentation hooks (separate dependency) |
| Correlation IDs | Structured logging with correlation ID inclusion |
| Duration Metrics | Request duration exposure via hooks |
| Custom Collectors | Support for custom metrics collectors |

#### 6.3.1 Observability Configuration

```python
ObservabilityConfig(
    request_id_format="uuid4",             # "uuid4" or "ulid"
    propagate_trace_context=True,          # Propagate trace headers
    enable_otel_instrumentation=False,     # OpenTelemetry hooks
    metrics_enabled=True,                  # Expose duration metrics
    custom_collectors=[],                  # Custom metrics collectors
)
```

### 6.4 Configuration Management

Type-safe configuration management using Pydantic Settings with support for multiple configuration sources.

#### 6.4.1 Configuration Sources

Configuration values are loaded from multiple sources in the following priority order (highest to lowest):

| Priority | Source | Description |
|----------|--------|-------------|
| 1 | Constructor arguments | Explicitly passed values |
| 2 | Environment variables | `MAMBA_` prefixed variables |
| 3 | `.env` file | Project-specific environment file |
| 4 | `~/agents.env` file | User-wide defaults |
| 5 | `config.toml` / `config.yaml` | Project configuration file |
| 6 | Default values | Defined in settings models |

#### 6.4.2 Environment Variable Mapping

All settings support environment variable configuration with the `MAMBA_` prefix:

| Setting | Environment Variable | Example |
|---------|---------------------|---------|
| `model_backend.base_url` | `MAMBA_MODEL_BACKEND__BASE_URL` | `http://localhost:11434/v1` |
| `model_backend.api_key` | `MAMBA_MODEL_BACKEND__API_KEY` | `sk-...` |
| `logging.level` | `MAMBA_LOGGING__LEVEL` | `DEBUG` |
| `retry.max_attempts` | `MAMBA_RETRY__MAX_ATTEMPTS` | `3` |

Note: Nested settings use double underscore (`__`) as separator.

#### 6.4.3 Settings Models

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class AgentSettings(BaseSettings):
    """Root configuration for the agent framework."""
    
    model_config = SettingsConfigDict(
        env_prefix="MAMBA_",
        env_nested_delimiter="__",
        env_file=(".env", Path.home() / "agents.env"),
        env_file_encoding="utf-8",
        toml_file="config.toml",
        extra="ignore",
    )
    
    # Model backend configuration
    model_backend: ModelBackendSettings = Field(default_factory=ModelBackendSettings)
    
    # Logging configuration
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Observability configuration
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    
    # Retry configuration
    retry: ErrorRecoveryConfig = Field(default_factory=ErrorRecoveryConfig)
    
    # Token tracking configuration
    token_tracking: TokenizerConfig = Field(default_factory=TokenizerConfig)
    
    # Context management configuration
    context: CompactionConfig = Field(default_factory=CompactionConfig)


class ModelBackendSettings(BaseSettings):
    """Configuration for the model backend connection."""
    
    base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL for the OpenAI-compatible API endpoint"
    )
    api_key: str | None = Field(
        default=None,
        description="API key for authenticated endpoints"
    )
    model: str = Field(
        default="llama3.2",
        description="Model identifier to use"
    )
    timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for failed requests"
    )
```

#### 6.4.4 Configuration File Formats

**TOML Configuration** (`config.toml`):

```toml
[model_backend]
base_url = "http://localhost:11434/v1"
model = "llama3.2"
timeout = 30.0

[logging]
level = "INFO"
structured = true

[retry]
retry_level = 2
initial_backoff_seconds = 1.0

[context]
strategy = "summarize_older"
trigger_threshold_tokens = 100000
```

**YAML Configuration** (`config.yaml`):

```yaml
model_backend:
  base_url: http://localhost:11434/v1
  model: llama3.2
  timeout: 30.0

logging:
  level: INFO
  structured: true

retry:
  retry_level: 2
  initial_backoff_seconds: 1.0

context:
  strategy: summarize_older
  trigger_threshold_tokens: 100000
```

#### 6.4.5 Configuration Loading

```python
from agent_framework import AgentSettings, Agent

# Load from default sources (env vars, .env, config files)
settings = AgentSettings()

# Override specific values
settings = AgentSettings(
    model_backend={"base_url": "http://custom:8080/v1"}
)

# Load from specific file
settings = AgentSettings(_env_file="production.env")

# Create agent with settings
agent = Agent.from_settings(settings)
```

#### 6.4.6 Secrets Management

Sensitive configuration values are handled securely:

| Feature | Description |
|---------|-------------|
| `SecretStr` type | API keys use Pydantic's `SecretStr` to prevent accidental logging |
| Environment precedence | Secrets should be provided via environment variables, not config files |
| Redaction | Secret values are automatically redacted in logs and `repr()` output |
| Validation | Secrets are validated but never exposed in error messages |

```python
from pydantic import SecretStr

class ModelBackendSettings(BaseSettings):
    api_key: SecretStr | None = Field(default=None)
    
    def get_headers(self) -> dict[str, str]:
        headers = {}
        if self.api_key:
            # Access secret value only when needed
            headers["Authorization"] = f"Bearer {self.api_key.get_secret_value()}"
        return headers
```

#### 6.4.7 Configuration Validation

All configuration is validated at load time using Pydantic:

- Type coercion (strings to integers, booleans, etc.)
- Range validation (e.g., `retry_level` must be 1-3)
- URL validation for endpoints
- Path existence validation for file paths (optional)
- Custom validators for complex constraints

```python
from pydantic import field_validator

class AgentSettings(BaseSettings):
    @field_validator("retry")
    @classmethod
    def validate_retry_level(cls, v: ErrorRecoveryConfig) -> ErrorRecoveryConfig:
        if v.retry_level not in (1, 2, 3):
            raise ValueError("retry_level must be 1, 2, or 3")
        return v
```

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Requirement | Target |
|-------------|--------|
| Tool execution overhead | < 10ms excluding actual tool runtime |
| Context serialization | < 100ms for 100k token context |
| Subagent spawn time | < 50ms |
| Memory per agent | < 50MB base, scaling with context size |

### 7.2 Reliability

- Graceful handling of model backend unavailability
- Automatic retry with exponential backoff for transient failures
- Tool execution timeout enforcement
- State recovery after unexpected termination (checkpoint support)

#### 7.2.1 Error Recovery Configuration

Error recovery aggressiveness is configurable on a scale of 1-3, with different retry behaviors for tool failures vs. model failures.

| Level | Description | Tool Retries | Model Retries | Backoff |
|-------|-------------|--------------|---------------|---------|
| `1` (Conservative) | Minimal retries, fail fast | 1 | 2 | Aggressive (2x multiplier) |
| `2` (Balanced) | Default behavior | 2 | 3 | Standard (1.5x multiplier) |
| `3` (Aggressive) | Maximum retry attempts | 3 | 5 | Gentle (1.2x multiplier) |

**Error Recovery Configuration**:
```python
ErrorRecoveryConfig(
    retry_level=2,                    # 1=conservative, 2=balanced (default), 3=aggressive
    
    # Fine-grained overrides (optional)
    tool_max_retries=None,            # Override tool retry count
    model_max_retries=None,           # Override model retry count
    
    # Backoff configuration
    initial_backoff_seconds=1.0,      # Initial wait before retry
    max_backoff_seconds=60.0,         # Maximum wait between retries
    
    # Error classification
    retryable_tool_errors=[           # Tool errors that trigger retry
        "TimeoutError",
        "ConnectionError",
        "TemporaryFailure",
    ],
    retryable_model_errors=[          # Model errors that trigger retry
        "RateLimitError",
        "ServiceUnavailable",
        "Timeout",
    ],
    
    # Circuit breaker
    circuit_breaker_threshold=5,      # Failures before circuit opens
    circuit_breaker_timeout=30.0,     # Seconds before retry after circuit opens
)
```

### 7.3 Security

- No execution of untrusted code without explicit sandbox configuration
- Secrets management (API keys not logged, not included in traces)
- Input sanitization for shell and filesystem operations
- Audit logging for security-sensitive operations

### 7.4 Extensibility

- Plugin architecture for custom compaction strategies
- Custom tool base classes for specialized tool categories
- Event hooks throughout agent lifecycle
- Custom serialization for state persistence

### 7.5 Testing and Quality Control

#### 7.5.1 Testability

- Design for easy mocking and testing
- Provide test utilities for common scenarios (mock server, fixtures)
- Support for request/response recording and playback
- Integration with respx for httpx mocking
- Example test patterns in documentation

#### 7.5.2 Code Quality

| Requirement | Standard |
|-------------|----------|
| Style | PEP 8 compliance enforced via ruff |
| Type Checking | Static analysis with ty |
| Formatting | Consistent formatting with ruff |
| Coverage | Minimum 90% code coverage target |
| API Testing | All public APIs must have tests |
| Integration | Integration tests against real HTTP servers |

#### 7.5.3 Test Infrastructure

- Unit test coverage target: 90%+
- Integration tests for each agent workflow
- Mock model backend for deterministic testing
- Tool testing utilities included
- Agent workflow test harnesses

### 7.6 Documentation

#### 7.6.1 Code Documentation

- Comprehensive docstrings for all public APIs following Google style
- Type hints integrated with documentation
- Code examples in docstrings
- Sphinx-compatible documentation with autodoc support

#### 7.6.2 External Documentation

| Document | Description |
|----------|-------------|
| API Reference | All public interfaces with examples |
| Workflow Guides | Implementation guides for each agent workflow |
| Tool Development | Guide for creating custom tools |
| MCP Integration | Tutorial for MCP server integration |
| Migration Guide | Guides from LangChain, AutoGen, and requests |
| Tutorials | Step-by-step guides for common use cases |

---

## 8. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Framework                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Tool Registry  │  │ Context Manager │  │ Token Tracking  │  │
│  │  ────────────   │  │ ─────────────── │  │ ──────────────  │  │
│  │  • Built-in     │  │ • State Track   │  │ • Usage Count   │  │
│  │  • Custom       │  │ • Compaction    │  │ • Cost Estimate │  │
│  │  • MCP Bridge   │  │ • History       │  │                 │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│           └────────────────────┼────────────────────┘           │
│                                │                                │
│  ┌─────────────────────────────┴─────────────────────────────┐  │
│  │                      Core Agent Engine                     │  │
│  │       (Tool-calling loop, Pydantic AI integration)         │  │
│  └─────────────────────────────┬─────────────────────────────┘  │
│                                │                                │
│  ┌─────────────────────────────┴─────────────────────────────┐  │
│  │                     Model Backend Layer                    │  │
│  │              (OpenAI-compatible API adapter)               │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│           Local Model Backends (Ollama, vLLM, etc.)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. API Design Principles

### 9.1 Consistency

- All configuration via Pydantic models
- Consistent naming conventions (snake_case for Python, following Pydantic AI patterns)
- Predictable return types (always return structured objects, not raw dicts)

### 9.2 Composability

- Agent workflows implementable via mixins or composition
- Tools usable independently of agents
- Context manager usable as standalone utility
- Method chaining where appropriate

### 9.3 Sensible Defaults

- Zero-configuration startup for simple use cases
- Progressive disclosure: simple things simple, complex things possible
- Fail-safe defaults (e.g., sandbox mode on by default for filesystem tools)
- Minimal configuration required for common use cases

### 9.4 Pythonic Interface

- Intuitive interface following established Python conventions
- Consistent naming conventions aligned with httpx where applicable
- Clear separation between configuration and runtime behavior
- Predictable behavior matching developer expectations

---

## 10. Example Usage

### 10.1 Basic Agent with Tools

```python
from agent_framework import Agent
from agent_framework.tools import read_file, run_bash
from agent_framework.backends import LocalModelBackend

backend = LocalModelBackend(
    base_url="http://localhost:11434/v1",
    model="llama3.2"
)

agent = Agent(
    backend=backend,
    tools=[read_file, run_bash],
    system_prompt="You are a helpful assistant.",
    max_iterations=10
)

result = await agent.run("List all Python files in the current directory")
```

---

## 11. Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Tool Reliability | Built-in tools pass 100% of integration tests |
| Token Accuracy | Token counts within 5% of actual model tokenization |
| Local Model Compat | Verified working with Ollama, vLLM, llama.cpp |
| MCP Integration | Successfully connects to reference MCP servers |
| Documentation | All public APIs documented with examples |

---

## 12. Future Considerations

These items are explicitly out of scope for initial release but should inform architectural decisions:

- **Persistent Memory**: Long-term memory storage and retrieval across sessions
- **Evaluation Framework**: Built-in benchmarking and evaluation harness
- **Distributed Execution**: Multi-process or multi-node agent execution
- **Visual Workflow Builder**: Graph-based agent composition UI
- **Prompt Versioning**: Track and rollback system prompt changes
- **A/B Testing**: Compare agent configurations in production

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| Compaction | The process of reducing context size while preserving relevant information |
| MCP | Model Context Protocol, a standard for tool/resource integration |
| Tool | A function the agent can call to perform actions (e.g., read files, run commands) |

---

## Appendix B: References

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [UV Package Manager](https://github.com/astral-sh/uv)
