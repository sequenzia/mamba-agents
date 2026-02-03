# Agent Messages Enhancements PRD

**Version**: 1.0
**Author**: —
**Date**: 2026-02-02
**Status**: Draft
**Spec Type**: New Feature
**Spec Depth**: Detailed Specifications
**Description**: Enhance the Agent's message history capabilities with filtering, analytics, timeline views, and multi-format export to improve developer debugging and analysis workflows.

---

## 1. Executive Summary

The mamba-agents `Agent` class tracks all messages exchanged with the LLM during agent runs, but the only retrieval method is `get_messages()` which returns a flat list of dicts. This spec defines a `MessageQuery` helper accessible via `agent.messages` that provides filtering, conversation analytics, structured timeline views, and multi-format export — enabling developers to efficiently debug and analyze complex agent interactions.

## 2. Problem Statement

### 2.1 The Problem

Developers building agent-based applications with mamba-agents need to understand what happened during an agent run — what was said, which tools were called, how tokens were consumed, and where things went wrong. The current `get_messages()` method returns the entire conversation as a flat list of OpenAI-compatible dicts with no filtering, analytics, or structured views. For complex interactions involving multiple tool calls, developers must manually scan through potentially hundreds of messages.

### 2.2 Current State

The Agent stores messages as `list[dict[str, Any]]` in a `ContextManager`. The dict format follows OpenAI conventions:

```python
{"role": "user", "content": "..."}
{"role": "assistant", "content": "...", "tool_calls": [...]}
{"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}
{"role": "system", "content": "..."}
```

Current API surface for message access:

| Method | Returns | Purpose |
|--------|---------|---------|
| `agent.get_messages()` | `list[dict]` | All messages (flat list) |
| `agent.get_context_state()` | `ContextState` | Token count, message count |
| `agent.clear_context()` | `None` | Wipe all messages |

There is no way to filter messages, compute per-message statistics, view conversation structure, or export in readable formats.

### 2.3 Impact Analysis

Without these capabilities, developers resort to:
- Writing ad-hoc loops to filter messages by role or tool name
- Manually counting tool calls or computing token estimates
- Printing raw dicts and visually scanning for patterns
- Building one-off export scripts for each project

This slows down debugging cycles and makes it harder to understand agent behavior in complex multi-tool scenarios.

### 2.4 Business Value

As a developer-facing framework, mamba-agents' value proposition includes making agent development easier. Enhanced message introspection:
- Reduces debugging time for developers using the framework
- Provides built-in tooling that competes with features in other agent frameworks
- Enables better observability without requiring external tools
- Supports the "batteries included but optional" design philosophy

## 3. Goals & Success Metrics

### 3.1 Primary Goals

1. Enable developers to quickly find specific messages, tool calls, or errors without scanning the full message list
2. Provide conversation analytics (token usage, tool call summaries) for debugging and performance analysis
3. Support structured export of conversations in JSON, Markdown, CSV, and dict formats

### 3.2 Success Metrics

| Metric | Current Baseline | Target | Measurement Method |
|--------|------------------|--------|--------------------|
| Lines of code to filter messages by role | ~5 (manual loop) | 1 (method call) | API simplicity |
| Formats available for export | 0 (raw dicts only) | 4 (JSON, MD, CSV, dict) | Feature count |
| Steps to get tool call summary | Manual iteration + counting | 1 method call | API simplicity |
| Test coverage for new module | N/A | 90%+ | pytest --cov |

### 3.3 Non-Goals

- Replacing or deprecating the existing `agent.get_messages()` method
- Providing a visual UI or web-based conversation viewer
- Automatic persistence of messages to disk or database
- Real-time streaming hooks or event-based message callbacks
- Message editing, mutation, or deletion capabilities

## 4. User Research

### 4.1 Target Users

#### Primary Persona: Agent Developer

- **Role/Description**: Software engineer building applications using mamba-agents, creating agents with tools, prompts, and multi-turn conversations
- **Goals**: Understand agent behavior, debug tool call sequences, optimize token usage, produce reports of agent runs
- **Pain Points**: Raw message dicts are hard to read; no way to filter or search; must write boilerplate to analyze conversations; no structured export for sharing with teammates
- **Context**: During development and testing, iterating on agent prompts and tool configurations; may also use in production logging pipelines

### 4.2 User Journey Map

```
[Agent run completes] --> [Developer wants to understand what happened]
    --> [Filters messages by tool name to find failed calls]
    --> [Views timeline to understand conversation flow]
    --> [Checks token stats to understand costs]
    --> [Exports to Markdown for a bug report or PR description]
```

## 5. Functional Requirements

### 5.1 Feature: Message Filtering & Querying

**Priority**: P0 (Critical)

#### User Stories

**US-001**: As a developer, I want to filter messages by role so that I can quickly see only assistant responses or only tool results.

**US-002**: As a developer, I want to filter messages by tool name so that I can trace all invocations and results of a specific tool.

**US-003**: As a developer, I want to search message content for keywords so that I can find messages related to a specific topic or error.

**US-004**: As a developer, I want to get messages by index or range so that I can inspect a specific portion of the conversation.

**US-005**: As a developer, I want to combine multiple filters so that I can make precise queries like "all tool results from read_file".

#### Acceptance Criteria

- [ ] `agent.messages.filter(role="tool")` returns only messages with the specified role
- [ ] `agent.messages.filter(tool_name="read_file")` returns tool call messages and their corresponding tool result messages for the specified tool
- [ ] `agent.messages.filter(content="error")` returns messages whose content contains the search string (case-insensitive)
- [ ] `agent.messages.filter(content="error")` supports regex patterns when prefixed (e.g., `content=r"Error:\s+\d+"` or via a `regex=True` parameter)
- [ ] `agent.messages.slice(start=5, end=10)` returns messages at indices 5 through 9
- [ ] `agent.messages.last(n=5)` returns the last 5 messages
- [ ] `agent.messages.first(n=5)` returns the first 5 messages
- [ ] Filters are combinable: `agent.messages.filter(role="tool", tool_name="read_file")` applies both criteria (AND logic)
- [ ] `agent.messages.filter()` with no arguments returns all messages (equivalent to `get_messages()`)
- [ ] All filter methods return `list[dict[str, Any]]` to maintain consistency with the existing format
- [ ] Filtering on an empty message list returns an empty list without errors
- [ ] Invalid role values (e.g., `role="invalid"`) return an empty list without raising exceptions

#### Edge Cases

- **Empty message history**: All filter/query methods return empty lists gracefully
- **No matches**: Filter returns empty list, not None or error
- **Tool messages without tool_name**: `tool_name` filter checks both `tool_calls[].function.name` on assistant messages and `name` on tool result messages
- **Content search on messages with no content field**: Skip messages without content, don't error

---

### 5.2 Feature: Conversation Analytics

**Priority**: P1 (High)

#### User Stories

**US-006**: As a developer, I want to see token usage per message so that I can identify which messages consume the most tokens.

**US-007**: As a developer, I want a summary of all tool calls so that I can understand which tools were used, how often, and with what arguments.

**US-008**: As a developer, I want a structured timeline of the conversation so that I can understand the flow of turns including tool call sequences.

#### Acceptance Criteria

**Token Statistics (`agent.messages.stats()`)**:
- [ ] Returns a `MessageStats` dataclass/model with total messages, messages by role, total tokens (computed via `TokenCounter`), and tokens by role
- [ ] Token counts are computed on demand using the Agent's configured `TokenCounter` (not a fresh default instance)
- [ ] Includes `avg_tokens_per_message` computed field
- [ ] Has a `__str__` method that renders a readable summary

**Tool Call Summary (`agent.messages.tool_summary()`)**:
- [ ] Returns a list of `ToolCallInfo` objects, each containing: tool_name, call_count, list of argument sets used, and list of result summaries
- [ ] Groups tool calls by tool name
- [ ] Includes the tool_call_id linking calls to their results
- [ ] Has a `__str__` method for readable output

**Conversation Timeline (`agent.messages.timeline()`)**:
- [ ] Returns a list of `Turn` objects, each grouping a logical turn: user prompt, assistant response, and any tool call/result pairs
- [ ] `Turn` has fields: `index`, `user_content`, `assistant_content`, `tool_interactions` (list of tool call + result pairs)
- [ ] `Turn` has a `__str__` method that renders a readable timeline entry
- [ ] The timeline list has a `render()` function or the return type has `__str__` that renders the full timeline
- [ ] Handles conversations that start with system prompts (system prompt appears as context on the first turn, not as a separate turn)
- [ ] Handles assistant messages with multiple tool calls in a single response

#### Edge Cases

- **No messages**: Stats returns zeroes, timeline returns empty list, tool summary returns empty list
- **Messages without tool calls**: Timeline shows turns without tool_interactions
- **Consecutive assistant messages**: Each gets its own turn (may happen with compacted histories)
- **Token counting consistency**: Uses the same `TokenCounter` instance as the Agent to avoid discrepancies with the known duplicate-counter issue in compaction

---

### 5.3 Feature: Message Export

**Priority**: P2 (Medium)

#### User Stories

**US-009**: As a developer, I want to export the conversation as JSON so that I can process it with external tools or store it for later analysis.

**US-010**: As a developer, I want to export the conversation as Markdown so that I can include it in bug reports, documentation, or PR descriptions.

**US-011**: As a developer, I want to export the conversation as CSV so that I can analyze it in spreadsheets.

**US-012**: As a developer, I want to export with the current dict format but with computed metadata so that I can get enhanced data without changing my existing processing code.

#### Acceptance Criteria

**JSON Export (`agent.messages.export(format="json")`)**:
- [ ] Returns a JSON string containing all messages with their full structure
- [ ] Includes optional metadata when `include_metadata=True`: message index, computed token count, timestamp placeholder
- [ ] Output is valid JSON parseable by `json.loads()`
- [ ] Supports `indent` parameter for pretty-printing (default: 2)

**Markdown Export (`agent.messages.export(format="markdown")`)**:
- [ ] Returns a formatted Markdown string with clear visual separation between messages
- [ ] User messages rendered under `### User` headers
- [ ] Assistant messages rendered under `### Assistant` headers
- [ ] Tool calls rendered with tool name, arguments (formatted), and results in code blocks
- [ ] System messages rendered under `### System` headers (if present)

**CSV Export (`agent.messages.export(format="csv")`)**:
- [ ] Returns a CSV string with columns: index, role, content (truncated if >500 chars), tool_name (if applicable), tool_call_id (if applicable), token_count
- [ ] Handles content with commas, newlines, and quotes properly (uses stdlib `csv` module)
- [ ] First row is a header row

**Enhanced Dict Export (`agent.messages.export(format="dict")`)**:
- [ ] Returns `list[dict]` (same as `get_messages()`) but each dict has an added `_metadata` key
- [ ] `_metadata` contains: `index` (int), `token_count` (int), `role` (str, normalized)
- [ ] Original message fields are untouched — `_metadata` is additive only

**General Export**:
- [ ] All export formats accept an optional `messages` parameter to export a filtered subset (default: all messages)
- [ ] Invalid format string raises `ValueError` with list of valid formats

#### Edge Cases

- **Large messages in CSV**: Content truncated with `...` suffix at 500 chars by default, configurable via `max_content_length` parameter
- **Tool call arguments in Markdown**: Rendered as formatted JSON in code blocks
- **Empty conversation**: Each format returns valid empty output (empty JSON array, empty Markdown with header, CSV with header row only, empty list)
- **Special characters**: JSON handles Unicode properly; CSV handles commas/newlines; Markdown escapes code block delimiters in content

## 6. Non-Functional Requirements

### 6.1 Performance

- Filtering should be O(n) where n is the number of messages — simple linear scan is acceptable for typical conversation sizes (< 1000 messages)
- Token counting in stats/export computes on demand but should cache results within a single `stats()` or `export()` call (not across calls)
- No persistent indexing or caching between calls — keep implementation simple

### 6.2 Security

- No new security concerns — this feature operates on in-memory message data already accessible to the developer
- Export methods should not inadvertently expose `SecretStr` values if any exist in message content (unlikely but worth a defensive check)

### 6.3 Compatibility

- Python 3.12+ required (consistent with project)
- No new dependencies — stdlib only (json, csv, re, dataclasses)
- Backward compatible: `agent.get_messages()` behavior unchanged
- The `agent.messages` property should not interfere with `ContextManager` operations

## 7. Technical Considerations

### 7.1 Architecture Overview

A new `MessageQuery` class will be introduced in `src/mamba_agents/agent/messages.py`. The `Agent` class gains a single `messages` property that lazily constructs a `MessageQuery` instance with access to the current message list and the Agent's `TokenCounter`.

```
Agent
  ├── get_messages()          # Existing, unchanged
  ├── messages (property)     # NEW: returns MessageQuery
  │     ├── filter()
  │     ├── slice() / first() / last()
  │     ├── stats()
  │     ├── tool_summary()
  │     ├── timeline()
  │     ├── export()
  │     └── all()
  └── (existing subsystems unchanged)
```

`MessageQuery` is stateless — it reads from the Agent's `ContextManager` on each call, ensuring it always reflects current state. No message data is copied or cached between calls.

### 7.2 Tech Stack

- **Language**: Python 3.12+
- **Data Models**: `dataclasses` for `MessageStats`, `ToolCallInfo`, `Turn` (or Pydantic models if consistency with project is preferred)
- **Export**: `json` (stdlib), `csv` (stdlib), string formatting for Markdown
- **Search**: `re` module for regex content search

### 7.3 Integration Points

| System | Integration Type | Purpose |
|--------|-----------------|---------|
| `Agent` (core.py) | Property | `messages` property returns `MessageQuery` instance |
| `ContextManager` | Read-only | `MessageQuery` reads messages via `get_messages()` |
| `TokenCounter` | Computation | Used for on-demand token counting in stats and export |
| `message_utils.py` | Reference | Dict format conventions are shared |

### 7.4 Technical Constraints

- Must work with the existing `list[dict[str, Any]]` message format — no changes to storage
- Must not require `track_context=True` to be set for all features (filtering on explicitly-provided message lists should work)
- Must use the Agent's configured `TokenCounter` for consistency (avoid the known duplicate-counter issue)
- `MessageQuery` should be importable standalone for use outside the Agent facade (e.g., `from mamba_agents.agent import MessageQuery`)

## 8. Scope Definition

### 8.1 In Scope

- `MessageQuery` class with filtering, analytics, timeline, and export methods
- `agent.messages` property on the `Agent` class
- Data models: `MessageStats`, `ToolCallInfo`, `Turn`
- Four export formats: JSON, Markdown, CSV, enhanced dict
- Combinable filter criteria with AND logic
- Content search with plain text and regex support
- Unit tests with 90%+ coverage for the new module
- Public API exports in `__init__.py`

### 8.2 Out of Scope

- **Message persistence to disk/DB**: Users can use `export(format="json")` and write to file themselves
- **Real-time message streaming hooks**: Event-based callbacks as messages are added
- **Message editing/mutation**: Modifying or deleting individual messages
- **Visual UI/dashboard**: Web-based conversation viewer
- **Per-run message isolation**: Filtering by run ID (no run tracking exists currently)
- **Async variants**: All methods are synchronous (token counting is CPU-bound, not I/O)

### 8.3 Future Considerations

- **Run tracking**: Adding run IDs to messages would enable per-run analysis (requires metadata changes)
- **Message persistence**: A `save()` / `load()` pair that writes/reads JSON export to/from file
- **Streaming hooks**: `on_message_added` callback for real-time debugging
- **Rich terminal output**: Using `rich` library for colored terminal rendering of timelines
- **Plugin system**: Allow custom export formats via registered formatters

## 9. Implementation Plan

### 9.1 Phase 1: Filtering — Foundation

**Completion Criteria**: Developers can filter and query messages by role, tool name, content, and index range using combinable criteria.

| Deliverable | Description | Dependencies |
|-------------|-------------|--------------|
| `MessageQuery` class | Core class with `filter()`, `slice()`, `first()`, `last()`, `all()` methods | None |
| `agent.messages` property | Property on Agent that returns `MessageQuery` | `MessageQuery` class |
| Filter by role | `filter(role="tool")` returns messages matching role | `MessageQuery` |
| Filter by tool name | `filter(tool_name="read_file")` returns matching tool calls and results | `MessageQuery` |
| Filter by content | `filter(content="error")` with plain text and regex support | `MessageQuery` |
| Combinable filters | Multiple kwargs combine with AND logic | All filter types |
| Public exports | Add `MessageQuery` to `__init__.py` | `MessageQuery` |
| Unit tests | 90%+ coverage for filtering, edge cases, empty lists | All deliverables |

**Checkpoint Gate**: Review API design and filter behavior before proceeding to analytics.

---

### 9.2 Phase 2: Analytics — Conversation Intelligence

**Completion Criteria**: Developers can get token statistics, tool call summaries, and structured conversation timelines.

| Deliverable | Description | Dependencies |
|-------------|-------------|--------------|
| `MessageStats` model | Dataclass with total messages, by-role counts, token counts, averages | Phase 1 |
| `stats()` method | Computes and returns `MessageStats` using Agent's `TokenCounter` | `MessageStats` |
| `ToolCallInfo` model | Dataclass with tool_name, call_count, arguments, results, call IDs | Phase 1 |
| `tool_summary()` method | Groups tool calls by name, returns list of `ToolCallInfo` | `ToolCallInfo` |
| `Turn` model | Dataclass grouping user prompt + assistant response + tool interactions | Phase 1 |
| `timeline()` method | Parses message list into ordered `Turn` objects | `Turn` |
| `__str__` methods | Readable string rendering for all models | All models |
| Unit tests | 90%+ coverage including edge cases (no tools, consecutive messages, empty history) | All deliverables |

**Checkpoint Gate**: Review data models and `__str__` output formatting before proceeding to export.

---

### 9.3 Phase 3: Export — Multi-Format Output

**Completion Criteria**: Developers can export conversations in JSON, Markdown, CSV, and enhanced dict formats.

| Deliverable | Description | Dependencies |
|-------------|-------------|--------------|
| `export()` method | Dispatch method accepting `format` parameter | Phase 1 |
| JSON exporter | Structured JSON output with optional metadata, configurable indent | `export()` |
| Markdown exporter | Formatted Markdown with role headers, tool call code blocks | `export()` |
| CSV exporter | Tabular output with configurable content truncation | `export()` |
| Enhanced dict exporter | Original dicts with `_metadata` field added | `export()` |
| Filtered export | All formats accept optional `messages` parameter for exporting subsets | Phase 1 filters |
| Unit tests | 90%+ coverage including format validation, edge cases, special characters | All deliverables |

## 10. Dependencies

### 10.1 Technical Dependencies

| Dependency | Status | Risk if Delayed |
|------------|--------|-----------------|
| Existing `ContextManager.get_messages()` API | Stable | Low — already in use |
| Existing `TokenCounter.count_messages()` API | Stable | Low — already in use |
| Dict message format conventions | Stable (documented) | Low — no planned changes |
| pydantic-ai message types (indirect) | Pre-1.0 library | Medium — type changes could affect dict format |

### 10.2 Cross-Team Dependencies

None — this feature is self-contained within the mamba-agents codebase.

## 11. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| API surface bloat on Agent | Medium | Low | Mitigated by `MessageQuery` helper pattern — only 1 property added to Agent |
| Maintenance burden of 4 export formats | Medium | Medium | Use stdlib only; keep formatters simple and independent; phased delivery |
| Message dict format changes upstream | High | Low | Dict format is controlled by `message_utils.py` which we own; add format validation |
| Performance on large histories (1000+ messages) | Low | Low | Linear scan is O(n) and sufficient; no premature optimization needed |
| TokenCounter inconsistency | Medium | Medium | Pass Agent's configured counter to `MessageQuery`; don't create new instances |
| pydantic-ai breaking changes to message types | Medium | Medium | Existing `message_utils.py` fragility is a known issue; new code should validate dict structure defensively |

## 12. Open Questions

| # | Question | Resolution |
|---|----------|------------|
| 1 | Should `MessageQuery` use Pydantic models or dataclasses for `MessageStats`, `ToolCallInfo`, `Turn`? | Recommend dataclasses for simplicity since these are read-only output types, but Pydantic would be consistent with the rest of the project. Decide during Phase 2 implementation. |
| 2 | Should `filter()` return a new `MessageQuery` for chaining (e.g., `agent.messages.filter(role="tool").filter(tool_name="read_file")`) or just return `list[dict]`? | Returning `list[dict]` is simpler and consistent with `get_messages()`. Chaining adds complexity. Recommend `list[dict]` for Phase 1, consider chaining as future enhancement. |

## 13. Appendix

### 13.1 Glossary

| Term | Definition |
|------|------------|
| Message | A single dict in OpenAI-compatible format with `role` and `content` keys |
| Turn | A logical grouping of messages forming one exchange: user prompt + assistant response + tool interactions |
| Tool call | An assistant message containing a `tool_calls` array with function invocations |
| Tool result | A message with `role: "tool"` containing the output of a tool execution |
| MessageQuery | The new helper class providing filtering, analytics, and export capabilities |
| ContextManager | Existing subsystem that stores and manages the Agent's message history |

### 13.2 References

- Existing implementation: `src/mamba_agents/agent/core.py` (Agent class)
- Message format: `src/mamba_agents/agent/message_utils.py` (conversion utilities)
- Context management: `src/mamba_agents/context/manager.py` (ContextManager)
- Token counting: `src/mamba_agents/tokens/counter.py` (TokenCounter)
- Project CLAUDE.md (architecture documentation and known fragility points)

### 13.3 Agent Recommendations (Accepted)

The following recommendation was suggested based on analysis of the codebase and accepted during the interview:

1. **API Design**: Use `agent.messages` property returning a `MessageQuery` helper object instead of adding methods directly to the Agent facade.
   - **Rationale**: The Agent class is already a large facade over 5+ subsystems. Adding 8-10 new methods would worsen the API surface bloat concern. A single `messages` property keeps Agent clean, makes the new features independently testable, and follows patterns used in other Python frameworks (e.g., Django querysets).
   - **Applies to**: Overall API architecture for all three phases.

---

*Document generated by SDD Tools*
