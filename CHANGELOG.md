# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add skills system for discoverable, reusable agent capabilities:
  - `SKILL.md` loader and parser with YAML frontmatter metadata extraction
  - Skill discovery from directories with three-level priority resolution
  - `SkillRegistry` for registering, deregistering, and querying skills
  - Skill validation with structured `ValidationResult` (non-throwing pattern)
  - Skill invocation with argument parsing and substitution
  - Trust level enforcement (`trusted`/`untrusted`) with configurable restrictions
  - Skill tool namespace prefixing to avoid name conflicts
  - `SkillManager` facade with progressive disclosure loading (metadata-first, full on demand)
  - `SkillTestHarness` testing utility with `skill_harness` pytest fixture
- Add subagents system for delegating work to child agents:
  - `SubagentConfig` for declarative subagent configuration (model, tools, constraints)
  - Subagent spawning with system prompt building, tool resolution, and nesting prevention
  - Synchronous delegation via `delegate_sync()` and async delegation via `delegate()` and `delegate_async()`
  - `SubagentManager` facade with registration, delegation, and dynamic spawning
  - Per-subagent token usage tracking and aggregation via `UsageTracker`
  - Subagent config loading from markdown files with `discover_subagents()`
- Add skills and subagents bi-directional integration:
  - `activate_with_fork()` for skill activation with context forking to subagents
  - Circular skill-subagent dependency detection
  - `SkillManager.subagent_manager` property for post-construction wiring
- Add Agent facade methods for skills:
  - `skills` and `skill_dirs` constructor parameters with lazy `SkillManager` initialization
  - `register_skill()`, `get_skill()`, `list_skills()`, `invoke_skill()` facade methods
- Add Agent facade methods for subagents:
  - `subagents` constructor parameter with lazy `SubagentManager` initialization
  - `delegate()`, `delegate_sync()`, `delegate_async()`, `register_subagent()`, `list_subagents()` facade methods
- Add `_is_subagent` private attribute to `AgentConfig` for nesting prevention
- Add `skills` field to `AgentSettings` for default skill configuration
- Add `source` field to `UsageRecord` and `get_subagent_usage()` method to `UsageTracker`

## [0.1.7] - 2026-02-03

### Added

- Add comprehensive display rendering system for agent messages:
  - `MessageRenderer` ABC with `RichRenderer`, `PlainTextRenderer`, and `HtmlRenderer` implementations
  - `DisplayPreset` system with `COMPACT`, `DETAILED`, and `VERBOSE` presets (accessible via `get_preset()`)
  - Standalone `print_stats()`, `print_timeline()`, `print_tools()` functions for standalone message visualization
  - `MessageQuery.print_stats()`, `print_timeline()`, `print_tools()` convenience methods
  - Rich `__rich_console__` protocol support for direct Rich console rendering of message analytics

### Fixed

- Fix ruff formatting issues and remove unused GitHub Actions workflows

## [0.1.6] - 2026-02-02

### Added

- Add `MessageQuery` class for comprehensive message filtering, analytics, and export:
  - Filter messages by role, tool_name, content (with regex support), and slice operations
  - Analytics methods: `stats()` (message counts and token statistics), `tool_summary()` (tool call analytics), `timeline()` (conversation turns)
  - Multi-format export: JSON, Markdown, CSV, and dict formats
  - `Agent.messages` property returns `MessageQuery` for stateless, on-demand access to conversation history
  - Works with or without context tracking and token counting
- Add `MessageStats`, `ToolCallInfo`, and `Turn` data models for message analytics

## [0.1.5] - 2026-02-02

### Fixed

- Fix graceful error handling not being applied to tools passed directly to `Agent(..., tools=[...])`; constructor tools are now wrapped with error handler when `graceful_tool_errors` is enabled (default behavior)

## [0.1.4] - 2026-01-26

### Added

- Add markdown template support with YAML frontmatter as alternative to Jinja2 templates
- Add `TemplateType` enum to distinguish between JINJA2 and MARKDOWN template types
- Add `MarkdownParseError` for markdown template parsing failures
- Add `TemplateConflictError` when both `.md` and `.jinja2` templates exist for same name
- Add `file_extensions` config option (replaces `file_extension` with backward compatibility)
- Add `examples/` directory with runnable scripts demonstrating all major features
- Add enhanced module docstrings with usage examples and cross-references

### Fixed

- Fix MCP `test_connection` using incorrect snake_case attribute `input_schema` instead of camelCase `inputSchema`

### Changed

- Update documentation with v0.1.3 MCP features (Streamable HTTP transport, connection testing)
- Update README and MCP user guide with new transport types and connection testing API
- Update `config.example.toml` with `[prompts]` section and Streamable HTTP MCP example

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

[Unreleased]: https://github.com/sequenzia/mamba-agents/compare/v0.1.7...HEAD
[0.1.7]: https://github.com/sequenzia/mamba-agents/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/sequenzia/mamba-agents/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/sequenzia/mamba-agents/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/sequenzia/mamba-agents/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/sequenzia/mamba-agents/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/sequenzia/mamba-agents/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/sequenzia/mamba-agents/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/sequenzia/mamba-agents/releases/tag/v0.1.0
