# Printing Agent Messages PRD

**Version**: 1.0
**Author**: Stephen Sequenzia
**Date**: 2026-02-03
**Status**: Draft
**Spec Type**: New feature
**Spec Depth**: Detailed specifications
**Description**: New functionality within messages analytics that allows users to print visually appealing outputs of message data using Rich, with support for terminal, plain text, and HTML output formats.

---

## 1. Executive Summary

Add a display/printing layer to the existing `MessageQuery` analytics system that produces visually appealing, formatted output of conversation data. The feature provides Rich-powered terminal tables, plain text fallback, and HTML rendering for notebooks — all accessible via one-call defaults on `MessageQuery` or standalone helper functions, with preset-based customization.

## 2. Problem Statement

### 2.1 The Problem

Developers debugging agent conversations lack a quick, visually structured way to inspect message data. The existing `__str__` methods on `MessageStats`, `ToolCallInfo`, and `Turn` produce plain, unstructured text output. There is no consolidated "print everything nicely" workflow — developers must manually format output each time they want to understand what happened in a conversation.

### 2.2 Current State

- `MessageStats.__str__()` outputs a basic multi-line text summary with indentation
- `ToolCallInfo.__str__()` outputs tool name, call count, and args/results as indented text
- `Turn.__str__()` outputs a simple turn-by-turn text dump
- `MessageQuery.export()` supports JSON, Markdown, CSV, and dict formats — but these are for data export, not visual presentation
- No tables, no color, no visual hierarchy, no consolidated view

### 2.3 Impact Analysis

Without this feature, developers spend unnecessary time parsing raw message dumps during debugging. Each developer must write their own formatting code or mentally parse unstructured text, slowing down the debug-iterate cycle that is core to agent development.

### 2.4 Business Value

Improved developer experience is a key differentiator for mamba-agents. A polished display layer demonstrates that the framework values the developer's time and makes the analytics capabilities (which already exist) actually useful in practice. This feature makes the existing `MessageQuery` system significantly more accessible.

## 3. Goals & Success Metrics

### 3.1 Primary Goals

1. Provide one-call formatted output for stats, timeline, and tool summary data
2. Support three output formats: Rich terminal, plain text, and HTML
3. Offer preset-based customization with individual option overrides

### 3.2 Success Metrics

| Metric | Current Baseline | Target | Measurement Method | Timeline |
|--------|------------------|--------|-------------------|----------|
| Lines of code to get formatted output | ~10-20 (manual formatting) | 1 (single method call) | Code comparison | v1 release |
| Output formats supported | 0 (manual only) | 3 (Rich, plain text, HTML) | Feature count | v1 release |
| Test coverage for display module | N/A | ≥50% (project standard) | pytest --cov | v1 release |

### 3.3 Non-Goals

- Interactive terminal UI (TUI) with scrolling, expanding, or user interaction
- File saving/writing capabilities (the existing `export()` method handles this)
- Real-time streaming display of messages as they arrive
- Replacing the existing `export()` system — this is a complementary display layer

## 4. User Research

### 4.1 Target Users

#### Primary Persona: Agent Developer

- **Role/Description**: A developer building AI agents using mamba-agents, debugging conversations during development and testing
- **Goals**: Quickly understand what happened in an agent conversation — what the user said, what the assistant responded, which tools were called, token usage
- **Pain Points**: Raw message dicts are hard to read; existing `__str__` output lacks visual structure; must write custom formatting each time
- **Context**: Terminal during development, Jupyter notebooks during experimentation, CI logs for test debugging

### 4.2 User Journey Map

```
[Run agent conversation] --> [Want to inspect results] --> [Call print method] --> [See formatted output] --> [Identify issue/confirm behavior]
```

**Current flow**: Run conversation → call `agent.messages.stats()` → get plain text → squint at output → maybe write custom formatting → understand data

**Target flow**: Run conversation → call `agent.messages.print_stats()` → see formatted Rich table → immediately understand data

## 5. Functional Requirements

### 5.1 Feature: Stats Printing

**Priority**: P0 (Critical)

#### User Stories

**US-001**: As a developer, I want to print a formatted summary of message statistics so that I can quickly see message counts, token usage, and role distribution.

**Acceptance Criteria**:
- [ ] `agent.messages.print_stats()` outputs a Rich table to the terminal with message count by role, token count by role, totals, and averages
- [ ] Standalone `print_stats(stats: MessageStats)` function produces the same output
- [ ] Plain text format produces readable ASCII table when Rich is not desired
- [ ] HTML format produces an HTML table suitable for Jupyter notebook display
- [ ] Empty `MessageStats` shows graceful "No messages recorded" message

**Edge Cases**:
- Empty message history: Display "No messages recorded" instead of an empty table
- Missing token counter (all token values are 0): Display the table with token columns showing 0, no errors
- Very large token counts: Numbers should be formatted with thousands separators

---

### 5.2 Feature: Timeline Printing

**Priority**: P0 (Critical)

#### User Stories

**US-002**: As a developer, I want to print a formatted conversation timeline so that I can follow the turn-by-turn exchange between user, assistant, and tools.

**Acceptance Criteria**:
- [ ] `agent.messages.print_timeline()` outputs each turn with role labels, content, and tool interactions
- [ ] Standalone `print_timeline(turns: list[Turn])` function produces the same output
- [ ] User messages, assistant messages, system prompts, and tool interactions are visually distinct
- [ ] Long message content is truncated by default with configurable `max_content_length`
- [ ] Full content is shown when `expand=True` or `max_content_length=None`
- [ ] Tool interactions within turns show tool name and call count in collapsed/summary view by default
- [ ] Empty timeline shows graceful "No conversation turns found" message

**Edge Cases**:
- Turns with only system context (no user/assistant): Display system context label
- Turns with many tool interactions (10+): Show summary count, collapsed by default
- Very long assistant responses: Truncate with "... (N more characters)" indicator
- Tool results containing code/JSON: No syntax highlighting needed in collapsed view

---

### 5.3 Feature: Tool Summary Printing

**Priority**: P0 (Critical)

#### User Stories

**US-003**: As a developer, I want to print a formatted tool usage summary so that I can see which tools were called, how many times, and at a glance.

**Acceptance Criteria**:
- [ ] `agent.messages.print_tools()` outputs a table of tool names and call counts
- [ ] Standalone `print_tools(tools: list[ToolCallInfo])` function produces the same output
- [ ] Default view shows tool name and call count only (collapsed)
- [ ] Detailed view option shows args and results per call (configurable)
- [ ] Args/results are truncated in detailed view with configurable length
- [ ] Empty tool summary shows graceful "No tool calls recorded" message

**Edge Cases**:
- No tool calls in conversation: Display "No tool calls recorded"
- Tool with 0 results but non-zero calls: Display call count, note missing results
- Very large argument dicts: Truncate JSON representation

---

### 5.4 Feature: Preset System

**Priority**: P1 (High)

#### User Stories

**US-004**: As a developer, I want to choose between compact, detailed, and verbose presets so that I can control how much information is displayed with a single parameter.

**Acceptance Criteria**:
- [ ] `compact` preset: Minimal output — counts and summaries only, short truncation limits
- [ ] `detailed` preset (default): Balanced output — full tables with moderate content truncation
- [ ] `verbose` preset: Maximum output — expanded content, full tool args/results
- [ ] Presets can be overridden with individual keyword arguments (e.g., `print_stats(preset="compact", show_tokens=True)`)
- [ ] Preset configuration is defined as a dataclass or similar structured type

**Edge Cases**:
- Invalid preset name: Raise `ValueError` with list of valid presets
- Conflicting options (e.g., `preset="compact"` with `expand=True`): Explicit options override preset values

---

### 5.5 Feature: Renderer Abstraction

**Priority**: P0 (Critical)

#### User Stories

**US-005**: As a developer, I want to choose between Rich, plain text, and HTML output formats so that I can use the display feature in terminals, logs, and notebooks.

**Acceptance Criteria**:
- [ ] `MessageRenderer` protocol/ABC defines `render_stats()`, `render_timeline()`, `render_tools()` methods
- [ ] `RichRenderer` implementation produces Rich Console output with tables
- [ ] `PlainTextRenderer` implementation produces clean ASCII text (no Rich dependency in output)
- [ ] `HtmlRenderer` implementation produces HTML tables/markup for notebook display
- [ ] Format is selectable via `format="rich"` / `format="plain"` / `format="html"` parameter on print methods
- [ ] Default format is `"rich"` for terminal output

**Edge Cases**:
- Unknown format string: Raise `ValueError` with list of valid formats
- Rich console not available in non-terminal context: Should still work (Rich handles this internally)

---

### 5.6 Feature: Rich Protocol Integration

**Priority**: P1 (High)

#### User Stories

**US-006**: As a developer using Rich, I want `MessageStats`, `ToolCallInfo`, and `Turn` objects to render beautifully when passed to `rich.print()` so that I get formatted output without calling a separate method.

**Acceptance Criteria**:
- [ ] `MessageStats` implements `__rich_console__` protocol, rendering as a Rich table
- [ ] `ToolCallInfo` implements `__rich_console__` protocol, rendering as a compact tool summary
- [ ] `Turn` implements `__rich_console__` protocol, rendering as a formatted turn display
- [ ] `rich.print(stats)` produces the same output as `agent.messages.print_stats()` with default preset
- [ ] The `__rich_console__` methods use the `detailed` preset by default

**Edge Cases**:
- Rich not imported by user: Protocol methods exist but are never called — no impact
- Passing to `rich.print()` vs `console.print()`: Both should work identically

---

### 5.7 Feature: Standalone Helper Functions

**Priority**: P1 (High)

#### User Stories

**US-007**: As a developer, I want standalone print functions so that I can format message data without needing a `MessageQuery` instance.

**Acceptance Criteria**:
- [ ] `print_stats(stats: MessageStats, *, preset: str = "detailed", format: str = "rich", **options)` available as a public function
- [ ] `print_timeline(turns: list[Turn], *, preset: str = "detailed", format: str = "rich", **options)` available as a public function
- [ ] `print_tools(tools: list[ToolCallInfo], *, preset: str = "detailed", format: str = "rich", **options)` available as a public function
- [ ] All standalone functions produce identical output to their `MessageQuery` method counterparts
- [ ] Functions are importable from the display module's public API

**Edge Cases**:
- Passing empty list/default dataclass: Handled with graceful empty states (same as methods)

## 6. Non-Functional Requirements

### 6.1 Performance

- Rendering should add negligible overhead to the analytics computation (< 50ms for typical conversations of 100 messages)
- Rendering large conversations (1000+ messages) should complete without blocking for extended periods
- HTML output should be generated as a string without requiring a web server or browser

### 6.2 Security

- No security-sensitive data is involved in display formatting
- Content truncation must not inadvertently hide security-relevant information in tool results (the full data remains accessible via the underlying data models)

### 6.3 Scalability

- Display should handle conversations with up to 1000 turns gracefully
- For very large conversations, the timeline printer should support pagination or limiting (e.g., `print_timeline(limit=50)`)

### 6.4 Accessibility

- Plain text output serves as the accessible format for screen readers and non-visual contexts
- HTML output should use semantic table markup (`<table>`, `<th>`, `<td>`) for screen reader compatibility

## 7. Technical Considerations

### 7.1 Architecture Overview

The display system follows a **Renderer abstraction pattern** (Strategy pattern) with three implementations:

```
agent.messages.print_stats()
        │
        ▼
  MessageQuery (print methods)
        │
        ▼
  Standalone functions (print_stats, print_timeline, print_tools)
        │
        ▼
  Renderer selection (format parameter)
        │
        ├── RichRenderer     → Rich Console output
        ├── PlainTextRenderer → ASCII text output
        └── HtmlRenderer      → HTML string output
```

Each renderer implements the `MessageRenderer` protocol with `render_stats()`, `render_timeline()`, `render_tools()` methods. Print methods on `MessageQuery` delegate to the standalone functions, which select the appropriate renderer.

### 7.2 Tech Stack

- **Rich**: Primary formatting library for terminal output (required dependency)
- **Python stdlib**: Plain text rendering (no additional dependencies)
- **Rich HTML export or manual HTML**: HTML rendering for notebooks

### 7.3 Integration Points

| System | Integration Type | Purpose |
|--------|-----------------|---------|
| `MessageQuery` (agent/messages.py) | Method addition | `print_stats()`, `print_timeline()`, `print_tools()` convenience methods |
| `MessageStats` dataclass | Protocol addition | `__rich_console__` for idiomatic Rich rendering |
| `ToolCallInfo` dataclass | Protocol addition | `__rich_console__` for idiomatic Rich rendering |
| `Turn` dataclass | Protocol addition | `__rich_console__` for idiomatic Rich rendering |
| `agent/__init__.py` | Export addition | New public API surface for display functions |
| `pyproject.toml` | Dependency addition | Add `rich` to required dependencies |

### 7.4 Technical Constraints

- Python 3.12+ required (matches project minimum)
- Rich must be a required dependency (not optional)
- Must follow project conventions: ruff formatting, Google-style docstrings, type annotations on all public APIs
- Must maintain backwards compatibility with existing `__str__` methods (don't replace them)
- The `__rich_console__` protocol additions to dataclasses must not affect their behavior when Rich is not used

## 8. Scope Definition

### 8.1 In Scope

- Rich-powered table rendering for MessageStats, ToolCallInfo, Turn
- Plain text rendering (no Rich dependency in output)
- HTML rendering for Jupyter notebooks
- Preset system (compact, detailed, verbose) with option overrides
- Methods on MessageQuery for convenience access
- Standalone print functions for flexibility
- `__rich_console__` protocol on data models
- Graceful empty state handling
- Content truncation with expand option
- Snapshot testing for rendered output

### 8.2 Out of Scope

- **Interactive TUI**: No scrollable, expandable, or interactive terminal interface — output is static
- **File saving**: No write-to-file functionality — the existing `export()` method handles serialization
- **Streaming display**: No real-time rendering as messages arrive during agent execution
- **Replacing export()**: The display layer is complementary to, not a replacement for, the existing export system
- **Custom themes/colors**: No user-definable color schemes in v1 — rely on Rich defaults

### 8.3 Future Considerations

- Custom color themes and style configuration
- Interactive TUI mode with expandable sections (Rich Live/Panel)
- Streaming display integration for real-time agent monitoring
- Additional renderers (e.g., Slack markdown, Discord formatting)
- Integration with observability (display formatted output in log collectors)

## 9. Implementation Plan

### 9.1 Phase 1: Foundation — Renderer Abstraction & Preset System

**Completion Criteria**: Renderer protocol defined, preset configuration established, Rich added as dependency

| Deliverable | Description | Dependencies |
|-------------|-------------|--------------|
| `MessageRenderer` protocol/ABC | Define `render_stats()`, `render_timeline()`, `render_tools()` interface | None |
| Preset configuration | Dataclass defining compact/detailed/verbose preset values | None |
| `rich` dependency | Add Rich to `pyproject.toml` required dependencies | None |
| Module structure | Create display module with `__init__.py` and renderer files | None |

**Checkpoint Gate**: Review renderer interface design and preset definitions before implementing renderers

---

### 9.2 Phase 2: Core Renderers — Rich, Plain Text, HTML

**Completion Criteria**: All three renderers produce formatted output for stats, timeline, and tool summary

| Deliverable | Description | Dependencies |
|-------------|-------------|--------------|
| `RichRenderer` | Rich table implementation for all three data types | Phase 1 |
| `PlainTextRenderer` | ASCII text implementation for all three data types | Phase 1 |
| `HtmlRenderer` | HTML table implementation for all three data types | Phase 1 |
| Standalone functions | `print_stats()`, `print_timeline()`, `print_tools()` with format selection | Phase 1 |
| Empty state handling | Graceful messages for empty data in all renderers | Phase 1 |

**Checkpoint Gate**: Visual review of rendered output across all formats and presets

---

### 9.3 Phase 3: Integration — MessageQuery Methods & Rich Protocol

**Completion Criteria**: Full API surface available via MessageQuery and standalone functions, Rich protocol working

| Deliverable | Description | Dependencies |
|-------------|-------------|--------------|
| `MessageQuery` print methods | `print_stats()`, `print_timeline()`, `print_tools()` on MessageQuery | Phase 2 |
| `__rich_console__` on `MessageStats` | Rich protocol implementation | Phase 2 |
| `__rich_console__` on `ToolCallInfo` | Rich protocol implementation | Phase 2 |
| `__rich_console__` on `Turn` | Rich protocol implementation | Phase 2 |
| Public API exports | Update `__init__.py` files with new public surface | Phase 2 |
| Snapshot tests | Golden file tests for all renderers and presets | Phase 2 |
| Unit tests | Standard unit tests for renderers, presets, and integration | Phase 2 |

## 10. Dependencies

### 10.1 Technical Dependencies

| Dependency | Owner | Status | Risk if Delayed |
|------------|-------|--------|-----------------|
| `rich` library | Will McGugan / Textualize | Stable (v13+) | Low — mature library |
| `MessageQuery` system | mamba-agents | Complete (v0.1.6) | None — already shipped |
| `MessageStats`, `ToolCallInfo`, `Turn` dataclasses | mamba-agents | Complete (v0.1.6) | None — already shipped |

### 10.2 Cross-Team Dependencies

No cross-team dependencies. This is a self-contained feature within mamba-agents.

## 11. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation Strategy | Owner |
|------|--------|------------|--------------------|----- |
| Rich version compatibility breaks | Medium | Low | Pin to `rich>=13.0` with upper bound if needed; test in CI against latest | Developer |
| HTML rendering doesn't match terminal quality | Medium | Medium | Use Rich's built-in HTML export where possible; test in Jupyter notebooks | Developer |
| Performance with very large conversations (1000+ turns) | Low | Low | Add `limit` parameter to timeline printer; lazy rendering if needed | Developer |
| `__rich_console__` protocol changes in future Rich versions | Low | Low | Protocol is stable and well-documented; monitor Rich changelog | Developer |

## 12. Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| 1 | Should the display module live under `agent/display.py` or as a new top-level `display/` package? | Developer | Phase 1 | To be determined during implementation based on code size |
| 2 | Should `print_*` methods return the rendered string in addition to printing? | Developer | Phase 1 | Recommendation: yes, return the string for testing and further use |
| 3 | Should the Rich console instance be configurable (e.g., custom Console with specific width)? | Developer | Phase 2 | Recommendation: accept optional `console` parameter with sensible default |

## 13. Appendix

### 13.1 Glossary

| Term | Definition |
|------|------------|
| MessageQuery | Stateless query interface for filtering and analyzing message histories |
| MessageStats | Dataclass holding token and message count statistics |
| ToolCallInfo | Dataclass summarizing a tool's usage across a conversation |
| Turn | Dataclass representing a logical conversation turn (user → assistant → tools) |
| Renderer | Implementation of a specific output format (Rich, plain text, HTML) |
| Preset | Named configuration bundle controlling display detail level |
| `__rich_console__` | Rich library protocol allowing objects to define their own Rich rendering |

### 13.2 References

- [Rich documentation](https://rich.readthedocs.io/)
- [Rich Console Protocol](https://rich.readthedocs.io/en/latest/protocol.html)
- Existing code: `src/mamba_agents/agent/messages.py`
- Existing code: `src/mamba_agents/agent/core.py` (Agent.messages property)

### 13.3 Agent Recommendations (Accepted)

*The following recommendations were suggested based on industry best practices and accepted during the interview:*

1. **Architecture — Renderer abstraction pattern**: Use a `MessageRenderer` protocol/ABC with format-specific implementations (`RichRenderer`, `PlainTextRenderer`, `HtmlRenderer`). This keeps each format isolated, makes testing straightforward, and makes adding new formats (e.g., Slack) trivial.

2. **API Design — `__rich_console__` protocol**: Add Rich's console protocol to `MessageStats`, `ToolCallInfo`, and `Turn` so that `rich.print(stats)` produces beautiful output automatically. This follows Rich's idiomatic patterns and integrates with the broader Rich ecosystem.

3. **Testing — Snapshot testing**: Use golden file comparisons for rendered output. Formatting code is fragile and small changes can break visual output in subtle ways that unit tests on data alone would miss.

---

*Document generated by SDD Tools*
