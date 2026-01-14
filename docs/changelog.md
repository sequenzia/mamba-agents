# Changelog

All notable changes to Pydantic Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Documentation website with MkDocs Material theme
- Comprehensive API reference with mkdocstrings
- User guides and tutorials
- Architecture and concepts documentation

## [0.1.0] - 2024-XX-XX

### Added

#### Core
- `Agent` class wrapping pydantic-ai with enterprise features
- `AgentConfig` for agent behavior configuration
- `AgentResult` wrapper for run results
- Automatic context tracking across runs
- Built-in token counting and usage tracking
- Cost estimation for API calls

#### Configuration
- `AgentSettings` with multi-source configuration loading
- Environment variable support (`AGENTS_*` prefix)
- `.env` file support (project and user-wide)
- TOML and YAML configuration file support
- `ModelBackendSettings` for model connection
- `LoggingConfig`, `ErrorRecoveryConfig`, etc.

#### Context Management
- `ContextManager` for conversation context
- `CompactionConfig` for compaction settings
- 5 compaction strategies:
  - `sliding_window` - Remove oldest messages
  - `summarize_older` - LLM summarization
  - `selective_pruning` - Remove tool pairs
  - `importance_scoring` - LLM-based scoring
  - `hybrid` - Combined strategies
- Auto-compaction when thresholds reached

#### Token Tracking
- `TokenCounter` using tiktoken
- `UsageTracker` for per-request tracking
- `CostEstimator` with default model pricing
- `TokenUsage`, `UsageRecord`, `CostBreakdown` data classes

#### Workflows
- `Workflow` abstract base class
- `WorkflowConfig` for workflow settings
- `WorkflowHooks` for lifecycle callbacks
- `WorkflowState`, `WorkflowStep`, `WorkflowResult`
- `ReActWorkflow` implementation:
  - Thought-Action-Observation loop
  - `ReActConfig` with reasoning settings
  - `ReActState` with scratchpad
  - `ReActHooks` for ReAct-specific callbacks

#### Built-in Tools
- Filesystem: `read_file`, `write_file`, `list_directory`, etc.
- Search: `glob_search`, `grep_search`
- Shell: `run_bash`
- `FilesystemSecurity` for sandboxing
- `ToolRegistry` for tool management

#### MCP Integration
- `MCPClientManager` for server connections
- `MCPServerConfig` for server configuration
- `MCPAuthConfig` for authentication
- Stdio and SSE transport support

#### Model Backends
- `OpenAICompatibleBackend` for OpenAI-compatible APIs
- Factory functions: `create_ollama_backend`, `create_vllm_backend`, `create_lmstudio_backend`
- `ModelProfile` for model capabilities
- `get_profile()` for model info lookup

#### Error Handling
- Custom exception hierarchy (`AgentError`, `ModelBackendError`, etc.)
- `CircuitBreaker` for preventing cascading failures
- `create_retry_decorator` for retry logic
- `ErrorRecoveryConfig` with retry levels

#### Observability
- `setup_logging` with text/JSON formats
- `AgentLogger` with sensitive data redaction
- `RequestTracer` for request tracing
- `OTelIntegration` for OpenTelemetry support

### Dependencies
- pydantic-ai >= 0.0.49
- pydantic >= 2.0
- pydantic-settings >= 2.0
- httpx >= 0.27
- tenacity >= 8.0
- tiktoken >= 0.7
- Optional: OpenTelemetry packages
