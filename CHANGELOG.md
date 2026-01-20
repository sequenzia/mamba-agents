# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/sequenzia/mamba-agents/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sequenzia/mamba-agents/releases/tag/v0.1.0
