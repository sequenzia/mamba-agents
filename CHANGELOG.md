# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-01-22

### Added

- Add Streamable HTTP transport support for MCP servers (auto-detected from URL when not ending in `/sse`)
- Add connection testing methods to `MCPClientManager`: `test_connection()`, `test_all_connections()`, and sync variants
- Add `get_server()` method to `MCPClientManager` for retrieving individual server instances
- Add `MCPToolInfo` and `MCPConnectionResult` models for connection testing results
- Add new MCP errors: `MCPConnectionError`, `MCPConnectionTimeoutError`, `MCPServerNotFoundError`

### Fixed

- Fix deprecated `get_event_loop().run_until_complete()` usage in MCP client (now uses `asyncio.run()`)

## [0.1.2] - 2026-01-22

### Added

- Add graceful tool error handling that converts tool exceptions to `ModelRetry`, allowing the LLM to receive error messages and attempt recovery instead of crashing the agent loop
- Add `graceful_tool_errors` config option to `AgentConfig` (default: `True`)
- Add `graceful_errors` parameter to `tool()` and `tool_plain()` decorators for per-tool override

## [0.1.1] - 2026-01-21

### Changed

- Simplify codebase by consolidating duplicate patterns across agent, workflows, and compaction strategies (net ~180 lines reduced)

### Removed

- Remove unused placeholder configs `ObservabilityConfig` and `StreamingConfig` from `mamba_agents.config` submodule

### Fixed

- Fix incorrect MCP API documentation in README (`get_toolsets()` -> `as_toolsets()`)

## [0.1.0] - 2025-01-20

### Added

- Initial release of Mamba Agents framework
- Core `Agent` class wrapping pydantic-ai with built-in context and token tracking
- Configuration system with `AgentSettings` supporting environment variables, `.env` files, and TOML/YAML
- Context window management with 5 compaction strategies:
  - sliding_window
  - summarize_older
  - selective_pruning
  - importance_scoring
  - hybrid
- Token counting and cost estimation with `TokenCounter`, `UsageTracker`, `CostEstimator`
- Prompt template management with Jinja2 support via `PromptManager` and `PromptTemplate`
- MCP (Model Context Protocol) integration:
  - `MCPClientManager` for managing MCP servers
  - Support for stdio and SSE transports
  - File-based config loading from `.mcp.json` files
- Workflow orchestration framework:
  - Base `Workflow` class for custom implementations
  - Built-in `ReActWorkflow` (Thought-Action-Observation loop)
  - Configurable hooks for workflow events
- Built-in tools for filesystem, glob, grep, and bash operations
- Model backends for Ollama and vLLM (OpenAI-compatible)
- Comprehensive error handling with retry logic and circuit breaker pattern
- Observability with logging and optional OpenTelemetry tracing

[Unreleased]: https://github.com/sequenzia/mamba-agents/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/sequenzia/mamba-agents/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/sequenzia/mamba-agents/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/sequenzia/mamba-agents/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/sequenzia/mamba-agents/releases/tag/v0.1.0
