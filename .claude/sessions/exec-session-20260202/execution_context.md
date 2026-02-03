# Execution Context

## Project Patterns
- Output/data types use `@dataclass` (not Pydantic BaseModel). Examples: `AgentResult`, `ContextState`, `CompactionResult`, `UsageRecord`, `TokenUsage`, `CostBreakdown`.
- Configuration types use `pydantic.BaseModel` (e.g., `AgentConfig`, `CompactionConfig`).
- All modules use `from __future__ import annotations` at the top.
- Google-style docstrings on all public classes and methods.
- Dataclass fields with mutable defaults use `field(default_factory=...)`.
- Test files use class-based test organization (`class TestX:`) with `-> None` return annotations.
- Tests import directly from the module being tested, not from top-level `__init__.py`.
- Line length is 100 chars (ruff config).

## Key Decisions
- Task 1: Used dataclasses (not Pydantic) for `MessageStats`, `ToolCallInfo`, `Turn` -- consistent with project convention for read-only output types.
- `avg_tokens_per_message` implemented as a `@property` (computed, not stored) to always reflect current values.
- Task 2: `MessageQuery` is a regular class (not dataclass) since it encapsulates behaviour. Constructor takes `messages` and optional `token_counter`. All filter methods return `list[dict]` (not chained `MessageQuery`). `filter()` uses keyword-only args.
- Task 10: `export()` uses format validation against `_VALID_FORMATS` tuple and dispatch dict for extensibility. Invalid formats raise `ValueError`; valid-but-unimplemented formats raise `NotImplementedError`. JSON exporter uses `ensure_ascii=False` for proper Unicode. Metadata enrichment creates shallow copies (`dict(msg)`) to avoid mutating originals. `_count_message_tokens()` helper is shared by export and will be reused by analytics methods.
- Task 6: `stats()` does NOT reuse `_count_message_tokens()` because stats requires different None-counter behavior (return 0s vs word-count fallback). Stats calls `self._token_counter.count_messages([msg])` directly with try/except for graceful error handling. Analytics section added between `all()` and Export section.
- Task 13: `_export_dict()` does NOT reuse `_count_message_tokens()` because dict export needs 0 when no counter (like stats), not the word-count fallback. When messages already have `_metadata`, it falls back to `_export_metadata` key to avoid conflicts. All four export formats are now wired into the dispatch dict.

## Known Issues
- No runtime type validation on dataclass fields (by design -- project uses dataclasses for output types, not input validation).

## File Map
- `src/mamba_agents/agent/messages.py` - MessageQuery data models (MessageStats, ToolCallInfo, Turn) + MessageQuery class
- `src/mamba_agents/agent/__init__.py` - Agent module exports (MessageQuery, MessageStats, ToolCallInfo, Turn added in Task 4)
- `src/mamba_agents/__init__.py` - Top-level package exports (MessageQuery, MessageStats, ToolCallInfo, Turn added in Task 4)
- `tests/unit/test_message_exports.py` - Import verification tests for MessageQuery public exports
- `src/mamba_agents/agent/core.py` - Main Agent class
- `src/mamba_agents/agent/config.py` - AgentConfig (Pydantic BaseModel)
- `src/mamba_agents/agent/result.py` - AgentResult dataclass
- `src/mamba_agents/agent/message_utils.py` - Dict/ModelMessage conversion
- `src/mamba_agents/context/manager.py` - ContextManager with get_messages()
- `src/mamba_agents/tokens/counter.py` - TokenCounter
- `src/mamba_agents/tokens/tracker.py` - UsageTracker, UsageRecord, TokenUsage dataclasses
- `tests/conftest.py` - Shared fixtures including sample_messages
- `tests/unit/test_messages.py` - Unit tests for message data models + MessageQuery filter/slice/first/last/all + export + stats + tool_summary + timeline
- `tests/unit/test_agent_messages_property.py` - Unit + integration tests for Agent.messages property

## Task History
### Task [1]: Create MessageQuery data models - PASS
- Files modified: `src/mamba_agents/agent/messages.py` (created), `tests/unit/test_messages.py` (created)
- Key learnings: Project uses dataclasses for output types, Pydantic for config. Test pattern is class-based with descriptive method names.
- Issues encountered: None. Clean implementation, all 28 tests pass, full suite (483 tests) passes.

### Task [2]: Create MessageQuery class with filter methods - PASS
- Files modified: `src/mamba_agents/agent/messages.py` (appended MessageQuery class), `tests/unit/test_messages.py` (added 50 tests)
- Key learnings: MessageQuery is a regular class (not dataclass) since it has behaviour, not just data. `TokenCounter` import uses TYPE_CHECKING guard to avoid import-time dependency. Tool result messages use `name` field (not `tool_name`) per `message_utils.py` convention. Ruff SIM102/SIM103 rules require merging nested ifs and inlining simple boolean returns. The `filter()` method uses keyword-only args (`*`) to enforce named parameters.
- Issues encountered: Two ruff lint issues (SIM102 nested if, SIM103 return-bool) -- fixed by combining conditions and returning expression directly. No test failures.

### Task [10]: Implement export() dispatch and JSON exporter - PASS
- Files modified: `src/mamba_agents/agent/messages.py` (added `export()`, `_export_json()`, `_count_message_tokens()` methods and `_VALID_FORMATS` class variable), `tests/unit/test_messages.py` (added 21 tests in 3 test classes)
- Key learnings: Export dispatch uses a dict mapping format names to exporter methods -- extensible for tasks #11, #12, #13 to add their format handlers. Unimplemented formats pass validation but raise `NotImplementedError` to distinguish from invalid formats. `_count_message_tokens()` helper uses `TokenCounter` when available, falls back to word-count estimate. `json.dumps(ensure_ascii=False)` preserves Unicode characters. `dict(msg)` creates shallow copy to avoid mutating original message dicts when adding metadata. Ruff B905 requires `strict=True` on `zip()` calls. Ruff RUF100 catches unused `noqa` directives (A002 for `format` parameter name is not enabled in this project). Ruff RUF043 requires raw strings in `pytest.raises(match=...)` when patterns contain metacharacters.
- Issues encountered: Three ruff lint issues in tests (B905 zip strict, RUF043 raw match string) and one in source (RUF100 unused noqa) -- all fixed. No test failures.

### Task [6]: Implement stats() method on MessageQuery - PASS
- Files modified: `src/mamba_agents/agent/messages.py` (added `stats()` method and `logging` import with module-level logger), `tests/unit/test_messages.py` (added 20 tests in 4 test classes)
- Key learnings: The `stats()` method differs from `_count_message_tokens()` in export: when `TokenCounter` is None, stats returns 0s for all token fields (no word-count fallback), while export's `_count_message_tokens` uses word-count fallback. This is intentional -- stats is analytics-focused and needs real token counts or nothing, while export metadata just needs a rough estimate. Token counts are cached within the single stats() call by computing per-message then aggregating (each message counted exactly once). Error handling uses broad `except Exception` with `logger.debug` to gracefully handle any TokenCounter failure. The `logging` module was added as a new import for error handling.
- Issues encountered: None. Clean implementation, all 119 message tests pass (91 previous + 28 new), full suite (574 tests) passes.

### Task [7]: Implement tool_summary() method on MessageQuery - PASS
- Files modified: `src/mamba_agents/agent/messages.py` (added `tool_summary()` method), `tests/unit/test_messages.py` (added 24 tests in 6 test classes)
- Key learnings: The `tool_summary()` method uses a three-pass approach: (1) build a lookup of tool results by `tool_call_id`, (2) scan assistant messages for tool calls and group by name, (3) handle orphaned tool results without matching calls. Arguments are parsed from JSON strings via `json.loads()`; non-JSON falls back to raw string which gets stored as empty dict since `arguments` field expects `list[dict]`. Orphaned calls (no result) are still counted but have no entry in `results` list. Orphaned results (no matching call) are detected by tracking which call_ids were matched and adding unmatched tool role messages as separate entries. The existing `ToolCallInfo.__str__` from Task 1 handles rendering correctly with mismatched list lengths. The method uses `dict[str, ToolCallInfo]` ordered by insertion to preserve deterministic output order.
- Issues encountered: Minor ruff formatting issue in tests -- fixed automatically by `ruff format`. No lint errors, no test failures. All 143 message tests pass, full suite (598 tests) passes.

### Task [8]: Implement timeline() method on MessageQuery - PASS
- Files modified: `src/mamba_agents/agent/messages.py` (added `timeline()` method, added `system_context` field to `Turn` dataclass, updated `Turn.__str__` to render system context), `tests/unit/test_messages.py` (added 25 tests in 8 test classes)
- Key learnings: The `timeline()` method uses a state-machine approach with an `in_tool_loop` flag to track when an assistant message following tool results should continue the same turn rather than starting a new one. The key challenge was distinguishing consecutive assistant messages (which each get their own turn) from assistant messages that follow tool results as part of a tool loop (which continue the same turn). The `Turn` dataclass was extended with a `system_context: str | None = None` field for system prompts -- this field is attached only to the first turn. System messages are collected before any turns are created, then attached once the first turn is formed. Tool results are pre-indexed in a `result_by_call_id` lookup dict for O(1) pairing with tool calls. The `in_tool_loop` flag is set after consuming tool results and reset when a new user message or a non-tool-loop assistant message arrives. Malformed messages (missing role, missing content, malformed tool_calls) are all handled gracefully by skipping invalid entries.
- Issues encountered: First implementation failed 4 tests because the tool loop continuation logic was incorrect -- an assistant message after tool results was creating a new turn instead of continuing the same turn. The condition `current_turn.assistant_content is not None` was always true for continuations. Fixed by adding the `in_tool_loop` boolean flag to track whether the next assistant message should continue the current turn. Ruff reformatted one multi-line `while` condition. All 168 message tests pass (143 previous + 25 new), full suite (623 tests) passes.

### Task [3]: Add agent.messages property to Agent class - PASS
- Files modified: `src/mamba_agents/agent/core.py` (added `messages` property and `MessageQuery` import), `tests/unit/test_agent_messages_property.py` (created, 13 tests in 4 test classes)
- Key learnings: The `messages` property is placed between `context_manager` and `model_name` properties for logical grouping. It reads directly from `self._context_manager.get_messages()` (not `self.get_messages()`) to avoid the `_ensure_context_enabled()` RuntimeError when `track_context=False`. The Agent always initializes `_token_counter` (line 168), so there is no case where the counter is None. The property creates a new `MessageQuery` each access (stateless by design). Test file imports from `mamba_agents` (top-level) for `Agent` and `AgentConfig`, and from `mamba_agents.agent.messages` for `MessageQuery` (matching the module-level import convention for tests).
- Issues encountered: Three unused import lint errors in the initial test file (typing.Any, pytest, TokenCounter) -- fixed by removing them. Ruff reformatted one long line. No test failures. All 13 new tests pass, full suite (636 tests) passes.

### Task [11]: Implement Markdown exporter - PASS
- Files modified: `src/mamba_agents/agent/messages.py` (added `_export_markdown()` method and 4 Markdown rendering helper methods, wired into export dispatch), `tests/unit/test_messages.py` (added 29 tests in 8 test classes)
- Key learnings: The Markdown exporter uses a helper-method decomposition: `_export_markdown()` orchestrates, `_md_render_text_message()` handles simple role messages (user/system), `_md_render_assistant()` handles assistant messages with optional tool calls, `_md_render_tool_call()` handles individual tool call entries. Tool result messages (role="tool") are rendered inline under the preceding assistant's tool call section via a pre-indexed `result_by_call_id` lookup, not as standalone entries. Code fence escaping uses zero-width spaces (`\u200b`) between backticks to prevent triple-backtick sequences from breaking fenced code blocks. Non-JSON arguments fall through to `str()` representation rather than raising. Messages are separated by `\n\n---\n\n` (horizontal rules) for visual separation. Empty conversations return empty string (not a header-only template). The `@classmethod` decorator is used for helpers that don't need instance state but need to call other class methods (like `_md_escape_code_fence`). `@staticmethod` is used for `_md_escape_code_fence` which is pure utility.
- Issues encountered: Ruff reformatted one long test line. No lint errors, no test failures. All 197 message tests pass (168 previous + 29 new), full suite (665 tests) passes.

### Task [12]: Implement CSV exporter - PASS
- Files modified: `src/mamba_agents/agent/messages.py` (added `_export_csv()` method, `_csv_extract_tool_name()` static helper, `_CSV_COLUMNS` class variable, `csv` and `io` imports, wired into export dispatch), `tests/unit/test_messages.py` (added 30 tests in 6 test classes, added `csv` and `io` imports)
- Key learnings: The CSV exporter uses stdlib `csv.writer` on a `StringIO` buffer for proper escaping of commas, newlines, and quotes. Content truncation uses a simple `len(content) > max_content_length` check with `...` suffix (exactly at limit is NOT truncated, only strictly above). Tool name extraction is handled by a dedicated `_csv_extract_tool_name()` static method that checks tool result messages (`name` field) and assistant messages (first tool_call's function name). Token counts reuse the existing `_count_message_tokens()` helper. The `_CSV_COLUMNS` tuple is a class variable for the 6 column headers. Ruff required one auto-format pass on test file. All fields use `.get()` with empty string defaults so missing/None fields produce empty CSV cells gracefully.
- Issues encountered: Minor ruff format adjustment on test file. No lint errors, no test failures. All 227 message tests pass (197 previous + 30 new), full suite (695 tests) passes.

### Task [13]: Implement enhanced dict exporter - PASS
- Files modified: `src/mamba_agents/agent/messages.py` (added `_export_dict()` method, wired into export dispatch), `tests/unit/test_messages.py` (added 22 tests in 6 test classes)
- Key learnings: The dict exporter differs from JSON's `include_metadata` in that: (1) metadata is namespaced under a `_metadata` key instead of being top-level, (2) when no TokenCounter is available, `token_count` defaults to 0 (not word-count fallback), (3) it returns `list[dict]` directly (not a string). The `_metadata` key conflict is handled by scanning all messages before export -- if any message has `_metadata`, the alternate key `_export_metadata` is used for the entire batch for consistency. Shallow copies via `dict(msg)` prevent mutation of originals. Error handling wraps `TokenCounter.count_messages()` in try/except with `logger.debug` for graceful fallback to 0. All four export format handlers are now registered in the dispatch dict (json, markdown, csv, dict).
- Issues encountered: Minor ruff format adjustment on test file. No lint errors, no test failures. All 249 message tests pass (227 previous + 22 new), full suite (717 tests) passes.

### Task [4]: Add MessageQuery public exports to __init__.py - PASS
- Files modified: `src/mamba_agents/agent/__init__.py` (added import and __all__ entries for MessageQuery, MessageStats, ToolCallInfo, Turn), `src/mamba_agents/__init__.py` (added import and __all__ entries for MessageQuery, MessageStats, ToolCallInfo, Turn), `tests/unit/test_message_exports.py` (created, 18 tests in 4 test classes)
- Key learnings: Both `__init__.py` files use alphabetical ordering in `__all__`. The top-level `__init__.py` groups imports by section with comments (Core agent exports, Context management, etc.) -- new message imports were added under "Core agent exports". The `agent/__init__.py` imports are also alphabetical by module name. Identity tests (`is` comparisons) confirm that all three import paths (top-level, agent module, messages module) resolve to the exact same class objects.
- Issues encountered: None. Clean implementation, all 18 new tests pass, full suite (735 tests) passes.

### Task [5]: Add unit tests for message filtering and querying - PASS
- Files modified: `tests/unit/test_messages.py` (added 68 tests in 11 test classes, plus `conversation_fixture` fixture)
- Key learnings: The existing `rich_messages` fixture from Task 2 covers basic scenarios well. The new `conversation_fixture` provides a richer 19-message conversation with multi-tool-call messages, None content, empty content, missing content field, unicode, and special regex characters. Fixture message counts must be carefully tracked -- the initial assertion values were off by 1 for assistant (8 not 7) and tool (6 not 5) counts. Coverage for `messages.py` reached 96% (exceeding 90% target). The `--cov=mamba_agents.agent.messages` dotted-path syntax fails with MCP import errors during collection; using `--cov` (project-wide) with `--cov-report=term-missing` works. The `_matches_tool_name` static method gracefully handles non-dict entries in tool_calls, empty tool_calls lists, and missing function keys.
- Issues encountered: Initial test run had 3 failures due to incorrect message count assertions (undercounted assistant and tool messages in the fixture). Fixed by recounting indices carefully. No issues after correction. All 317 message tests pass, full suite (803 tests) passes.

### Task [9]: Add unit tests for conversation analytics - PASS
- Files modified: `tests/unit/test_messages.py` (added 56 tests in 15 test classes)
- Key learnings: The `conversation_fixture` provides excellent integration-style coverage for analytics methods -- it exercises multi-tool-call messages, tool loop continuations, None/empty content, unicode, and varying roles. The `timeline()` method on the conversation_fixture produces 5 turns (4 user-initiated + 1 trailing assistant-only), which requires careful tracing through the state machine logic to predict. Cross-method consistency tests (stats vs tool_summary vs timeline) are effective at catching data model disagreements. ToolCallInfo `__str__` iterates over `tool_call_ids` only, so extra entries in `results` beyond `tool_call_ids` length are never rendered. Coverage for `messages.py` reached 97% (up from 96%, well above 90% target). The `--cov` project-wide approach continues to work around the MCP import error with dotted-path syntax.
- Issues encountered: None. Clean implementation, all 373 message tests pass (317 previous + 56 new), full suite (859 tests) passes.

### Task [14]: Add unit tests for message export - PASS
- Files modified: `tests/unit/test_messages.py` (added 66 tests in 16 test classes, plus `_MockTokenCounter` and `_FailingTokenCounter` helper classes)
- Key learnings: Coverage was already 97% before this task. The new tests focused on cross-format consistency (verifying all 4 formats agree on message counts and roles), integration-style tests using `conversation_fixture` for each format, mock TokenCounter for deterministic results, and edge cases for uncovered code paths. The `_MockTokenCounter` returns word_count + 4 overhead for deterministic assertions. The `_FailingTokenCounter` always raises RuntimeError to exercise exception-handling paths in `_export_dict()`. The Markdown unknown role path (line 749) was exercised by using `role="moderator"` which renders as `### Moderator`. The dict export TokenCounter exception path (lines 1022-1027) was exercised by the `_FailingTokenCounter`. Remaining uncovered lines (557, 566-567, 597-598) are in `timeline()` method, not export code. Export-specific code has 100% coverage. Overall messages.py coverage reached 98%.
- Issues encountered: None. Clean implementation, all 439 message tests pass (373 previous + 66 new), full suite (925 tests) passes.
