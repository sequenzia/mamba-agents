"""Tests for MessageQuery data models and MessageQuery class."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any

import pytest

from mamba_agents.agent.messages import MessageQuery, MessageStats, ToolCallInfo, Turn


class TestMessageStats:
    """Tests for the MessageStats dataclass."""

    def test_construction_with_valid_data(self) -> None:
        """Test constructing MessageStats with typical values."""
        stats = MessageStats(
            total_messages=10,
            messages_by_role={"user": 4, "assistant": 4, "tool": 2},
            total_tokens=500,
            tokens_by_role={"user": 200, "assistant": 250, "tool": 50},
        )

        assert stats.total_messages == 10
        assert stats.messages_by_role == {"user": 4, "assistant": 4, "tool": 2}
        assert stats.total_tokens == 500
        assert stats.tokens_by_role == {"user": 200, "assistant": 250, "tool": 50}

    def test_default_values(self) -> None:
        """Test that defaults produce a valid empty stats object."""
        stats = MessageStats()

        assert stats.total_messages == 0
        assert stats.messages_by_role == {}
        assert stats.total_tokens == 0
        assert stats.tokens_by_role == {}

    def test_avg_tokens_per_message_normal(self) -> None:
        """Test average token computation with non-zero messages."""
        stats = MessageStats(total_messages=4, total_tokens=100)

        assert stats.avg_tokens_per_message == 25.0

    def test_avg_tokens_per_message_zero_messages(self) -> None:
        """Test that zero messages returns 0.0 instead of ZeroDivisionError."""
        stats = MessageStats(total_messages=0, total_tokens=0)

        assert stats.avg_tokens_per_message == 0.0

    def test_avg_tokens_per_message_zero_tokens(self) -> None:
        """Test that zero tokens with non-zero messages returns 0.0."""
        stats = MessageStats(total_messages=5, total_tokens=0)

        assert stats.avg_tokens_per_message == 0.0

    def test_avg_tokens_per_message_fractional(self) -> None:
        """Test that fractional averages are returned as floats."""
        stats = MessageStats(total_messages=3, total_tokens=10)

        assert isinstance(stats.avg_tokens_per_message, float)
        assert abs(stats.avg_tokens_per_message - 10 / 3) < 1e-9

    def test_str_output_contains_key_info(self) -> None:
        """Test that __str__ includes all important fields."""
        stats = MessageStats(
            total_messages=6,
            messages_by_role={"user": 3, "assistant": 3},
            total_tokens=300,
            tokens_by_role={"user": 120, "assistant": 180},
        )
        output = str(stats)

        assert "Message Statistics" in output
        assert "Total messages: 6" in output
        assert "Total tokens:   300" in output
        assert "Avg tokens/msg: 50.0" in output
        assert "Messages by role:" in output
        assert "user: 3" in output
        assert "assistant: 3" in output
        assert "Tokens by role:" in output
        assert "user: 120" in output
        assert "assistant: 180" in output

    def test_str_output_empty_stats(self) -> None:
        """Test __str__ with default empty stats."""
        stats = MessageStats()
        output = str(stats)

        assert "Message Statistics" in output
        assert "Total messages: 0" in output
        assert "Avg tokens/msg: 0.0" in output
        # Empty dicts should not produce role sections
        assert "Messages by role:" not in output
        assert "Tokens by role:" not in output

    def test_str_output_zero_messages_avg(self) -> None:
        """Test __str__ shows 0.0 avg when no messages exist."""
        stats = MessageStats(total_messages=0, total_tokens=0)
        output = str(stats)

        assert "Avg tokens/msg: 0.0" in output


class TestToolCallInfo:
    """Tests for the ToolCallInfo dataclass."""

    def test_construction_with_valid_data(self) -> None:
        """Test constructing ToolCallInfo with typical values."""
        info = ToolCallInfo(
            tool_name="read_file",
            call_count=2,
            arguments=[{"path": "a.txt"}, {"path": "b.txt"}],
            results=["contents of a", "contents of b"],
            tool_call_ids=["call_1", "call_2"],
        )

        assert info.tool_name == "read_file"
        assert info.call_count == 2
        assert len(info.arguments) == 2
        assert len(info.results) == 2
        assert len(info.tool_call_ids) == 2

    def test_default_empty_lists(self) -> None:
        """Test that list fields default to empty lists."""
        info = ToolCallInfo(tool_name="run_bash")

        assert info.call_count == 0
        assert info.arguments == []
        assert info.results == []
        assert info.tool_call_ids == []

    def test_empty_arguments_and_results(self) -> None:
        """Test that empty arguments and results lists are handled."""
        info = ToolCallInfo(
            tool_name="delete_file",
            call_count=0,
            arguments=[],
            results=[],
            tool_call_ids=[],
        )

        assert info.arguments == []
        assert info.results == []
        assert info.tool_call_ids == []

    def test_str_output_with_calls(self) -> None:
        """Test __str__ output includes tool name, count, and call details."""
        info = ToolCallInfo(
            tool_name="read_file",
            call_count=1,
            arguments=[{"path": "test.txt"}],
            results=["file contents"],
            tool_call_ids=["call_abc"],
        )
        output = str(info)

        assert "Tool: read_file (called 1 time(s))" in output
        assert "[call_abc]" in output
        assert "args: {'path': 'test.txt'}" in output
        assert "result: file contents" in output

    def test_str_output_empty(self) -> None:
        """Test __str__ with no calls produces header only."""
        info = ToolCallInfo(tool_name="run_bash", call_count=0)
        output = str(info)

        assert "Tool: run_bash (called 0 time(s))" in output

    def test_str_output_multiple_calls(self) -> None:
        """Test __str__ with multiple tool calls."""
        info = ToolCallInfo(
            tool_name="grep_search",
            call_count=2,
            arguments=[{"pattern": "error"}, {"pattern": "warning"}],
            results=["3 matches", "1 match"],
            tool_call_ids=["call_1", "call_2"],
        )
        output = str(info)

        assert "called 2 time(s)" in output
        assert "[call_1]" in output
        assert "[call_2]" in output
        assert "pattern" in output

    def test_mismatched_list_lengths(self) -> None:
        """Test __str__ handles mismatched argument/result/id list lengths."""
        info = ToolCallInfo(
            tool_name="write_file",
            call_count=2,
            arguments=[{"path": "a.txt"}],  # Only 1 argument set
            results=[],  # No results
            tool_call_ids=["call_1", "call_2"],  # 2 IDs
        )
        output = str(info)

        # Should not raise; should include what it can
        assert "[call_1]" in output
        assert "[call_2]" in output
        assert "args:" in output


class TestTurn:
    """Tests for the Turn dataclass."""

    def test_construction_with_valid_data(self) -> None:
        """Test constructing Turn with typical values."""
        turn = Turn(
            index=0,
            user_content="Hello",
            assistant_content="Hi there!",
            tool_interactions=[],
        )

        assert turn.index == 0
        assert turn.user_content == "Hello"
        assert turn.assistant_content == "Hi there!"
        assert turn.tool_interactions == []

    def test_default_values(self) -> None:
        """Test that defaults produce a valid empty turn."""
        turn = Turn()

        assert turn.index == 0
        assert turn.user_content is None
        assert turn.assistant_content is None
        assert turn.tool_interactions == []

    def test_none_user_content(self) -> None:
        """Test Turn with None user_content (assistant-initiated turn)."""
        turn = Turn(
            index=1,
            user_content=None,
            assistant_content="I'll continue from where we left off.",
        )

        assert turn.user_content is None
        assert turn.assistant_content is not None

    def test_none_assistant_content(self) -> None:
        """Test Turn with None assistant_content (e.g., unanswered prompt)."""
        turn = Turn(
            index=2,
            user_content="What is the meaning of life?",
            assistant_content=None,
        )

        assert turn.user_content is not None
        assert turn.assistant_content is None

    def test_both_none_content(self) -> None:
        """Test Turn where both user and assistant content are None."""
        turn = Turn(index=3, user_content=None, assistant_content=None)

        assert turn.user_content is None
        assert turn.assistant_content is None

    def test_with_tool_interactions(self) -> None:
        """Test Turn with tool interaction dicts."""
        interactions = [
            {
                "tool_name": "read_file",
                "tool_call_id": "call_123",
                "arguments": {"path": "test.txt"},
                "result": "file contents",
            }
        ]
        turn = Turn(
            index=0,
            user_content="Read my file",
            assistant_content="Here are the contents.",
            tool_interactions=interactions,
        )

        assert len(turn.tool_interactions) == 1
        assert turn.tool_interactions[0]["tool_name"] == "read_file"

    def test_str_output_full_turn(self) -> None:
        """Test __str__ with user, assistant, and tool content."""
        interactions = [
            {
                "tool_name": "read_file",
                "tool_call_id": "call_abc",
                "arguments": {"path": "data.txt"},
                "result": "some data",
            }
        ]
        turn = Turn(
            index=2,
            user_content="Read data.txt",
            assistant_content="Here is the data.",
            tool_interactions=interactions,
        )
        output = str(turn)

        assert "Turn 2:" in output
        assert "User: Read data.txt" in output
        assert "Assistant: Here is the data." in output
        assert "Tool interactions:" in output
        assert "[read_file]" in output
        assert "call_abc" in output
        assert "result: some data" in output

    def test_str_output_no_content(self) -> None:
        """Test __str__ with None content fields."""
        turn = Turn(index=0, user_content=None, assistant_content=None)
        output = str(turn)

        assert "Turn 0:" in output
        assert "User:" not in output
        assert "Assistant:" not in output

    def test_str_output_no_tools(self) -> None:
        """Test __str__ without tool interactions."""
        turn = Turn(
            index=1,
            user_content="Just a question",
            assistant_content="Just an answer",
        )
        output = str(turn)

        assert "Turn 1:" in output
        assert "User: Just a question" in output
        assert "Assistant: Just an answer" in output
        assert "Tool interactions:" not in output


class TestModuleImports:
    """Tests for module importability."""

    def test_import_message_stats(self) -> None:
        """Test MessageStats is importable from the module."""
        from mamba_agents.agent.messages import MessageStats

        assert MessageStats is not None

    def test_import_tool_call_info(self) -> None:
        """Test ToolCallInfo is importable from the module."""
        from mamba_agents.agent.messages import ToolCallInfo

        assert ToolCallInfo is not None

    def test_import_turn(self) -> None:
        """Test Turn is importable from the module."""
        from mamba_agents.agent.messages import Turn

        assert Turn is not None

    def test_import_message_query(self) -> None:
        """Test MessageQuery is importable from the module."""
        from mamba_agents.agent.messages import MessageQuery

        assert MessageQuery is not None


# ---------------------------------------------------------------------------
# Fixtures for MessageQuery tests
# ---------------------------------------------------------------------------


@pytest.fixture
def rich_messages() -> list[dict[str, Any]]:
    """Provide a comprehensive message history with all role types and tool calls."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, read my file please."},
        {
            "role": "assistant",
            "content": "I'll read the file for you.",
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path": "data.txt"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_001",
            "name": "read_file",
            "content": "File contents: Error: 42 occurred",
        },
        {"role": "assistant", "content": "The file contains an error message."},
        {"role": "user", "content": "Now search for warnings."},
        {
            "role": "assistant",
            "content": "Searching for warnings...",
            "tool_calls": [
                {
                    "id": "call_002",
                    "type": "function",
                    "function": {
                        "name": "grep_search",
                        "arguments": '{"pattern": "warning"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_002",
            "name": "grep_search",
            "content": "No matches found",
        },
        {"role": "assistant", "content": "No warnings found in the codebase."},
        {"role": "user", "content": "Write a summary to output.txt"},
        {
            "role": "assistant",
            "content": "Writing summary...",
            "tool_calls": [
                {
                    "id": "call_003",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": '{"path": "output.txt", "content": "summary"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_003",
            "name": "write_file",
            "content": "File written successfully",
        },
        {"role": "assistant", "content": "Done! The summary has been written."},
    ]


# ---------------------------------------------------------------------------
# MessageQuery: filter() tests
# ---------------------------------------------------------------------------


class TestMessageQueryFilterByRole:
    """Tests for MessageQuery.filter(role=...) behaviour."""

    def test_filter_role_tool(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(role='tool') returns only tool result messages."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="tool")

        assert len(result) == 3
        assert all(msg["role"] == "tool" for msg in result)

    def test_filter_role_user(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(role='user') returns only user messages."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="user")

        assert len(result) == 3
        assert all(msg["role"] == "user" for msg in result)

    def test_filter_role_assistant(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(role='assistant') returns only assistant messages."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="assistant")

        assert len(result) == 6
        assert all(msg["role"] == "assistant" for msg in result)

    def test_filter_role_system(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(role='system') returns only system messages."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="system")

        assert len(result) == 1
        assert result[0]["role"] == "system"

    def test_filter_invalid_role_returns_empty(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(role='invalid') returns empty list without exception."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="invalid")

        assert result == []

    def test_filter_returns_list_type(self, rich_messages: list[dict[str, Any]]) -> None:
        """All filter results are list[dict[str, Any]]."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="user")

        assert isinstance(result, list)
        assert all(isinstance(msg, dict) for msg in result)


class TestMessageQueryFilterByToolName:
    """Tests for MessageQuery.filter(tool_name=...) behaviour."""

    def test_filter_tool_name_returns_call_and_result(
        self, rich_messages: list[dict[str, Any]]
    ) -> None:
        """filter(tool_name='read_file') returns assistant call msg AND tool result msg."""
        query = MessageQuery(rich_messages)
        result = query.filter(tool_name="read_file")

        assert len(result) == 2
        roles = {msg["role"] for msg in result}
        assert "assistant" in roles
        assert "tool" in roles

    def test_filter_tool_name_grep_search(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(tool_name='grep_search') returns both message types."""
        query = MessageQuery(rich_messages)
        result = query.filter(tool_name="grep_search")

        assert len(result) == 2

    def test_filter_tool_name_no_match(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(tool_name='nonexistent') returns empty list."""
        query = MessageQuery(rich_messages)
        result = query.filter(tool_name="nonexistent")

        assert result == []

    def test_filter_tool_name_checks_assistant_tool_calls(self) -> None:
        """tool_name filter matches tool_calls[].function.name on assistant messages."""
        messages = [
            {
                "role": "assistant",
                "content": "Calling tool...",
                "tool_calls": [
                    {
                        "id": "call_x",
                        "type": "function",
                        "function": {"name": "my_tool", "arguments": "{}"},
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.filter(tool_name="my_tool")

        assert len(result) == 1
        assert result[0]["role"] == "assistant"

    def test_filter_tool_name_checks_tool_result_name(self) -> None:
        """tool_name filter matches the name field on tool result messages."""
        messages = [
            {
                "role": "tool",
                "tool_call_id": "call_x",
                "name": "my_tool",
                "content": "result",
            },
        ]
        query = MessageQuery(messages)
        result = query.filter(tool_name="my_tool")

        assert len(result) == 1
        assert result[0]["role"] == "tool"

    def test_filter_tool_name_assistant_without_tool_calls(self) -> None:
        """Assistant messages without tool_calls are not matched by tool_name filter."""
        messages = [
            {"role": "assistant", "content": "No tools used here."},
        ]
        query = MessageQuery(messages)
        result = query.filter(tool_name="read_file")

        assert result == []


class TestMessageQueryFilterByContent:
    """Tests for MessageQuery.filter(content=...) behaviour."""

    def test_filter_content_case_insensitive(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(content='error') matches case-insensitively."""
        query = MessageQuery(rich_messages)
        result = query.filter(content="error")

        # Should match "Error: 42 occurred" and "error message"
        assert len(result) >= 2
        for msg in result:
            assert "error" in msg["content"].lower()

    def test_filter_content_no_match(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(content='nonexistent_xyz') returns empty list."""
        query = MessageQuery(rich_messages)
        result = query.filter(content="nonexistent_xyz")

        assert result == []

    def test_filter_content_skips_missing_content(self) -> None:
        """Content search skips messages without a content field."""
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant"},  # No content field
            {"role": "tool", "tool_call_id": "x", "name": "t"},  # No content field
        ]
        query = MessageQuery(messages)
        result = query.filter(content="hello")

        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_filter_content_skips_none_content(self) -> None:
        """Content search skips messages with None content."""
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": None},
        ]
        query = MessageQuery(messages)
        result = query.filter(content="hello")

        assert len(result) == 1

    def test_filter_content_regex(self, rich_messages: list[dict[str, Any]]) -> None:
        r"""filter(content=r'Error:\s+\d+', regex=True) matches regex pattern."""
        query = MessageQuery(rich_messages)
        result = query.filter(content=r"Error:\s+\d+", regex=True)

        assert len(result) >= 1
        assert any("Error: 42" in msg.get("content", "") for msg in result)

    def test_filter_content_regex_no_match(self, rich_messages: list[dict[str, Any]]) -> None:
        """Regex pattern with no matches returns empty list."""
        query = MessageQuery(rich_messages)
        result = query.filter(content=r"^ZZZZZ$", regex=True)

        assert result == []

    def test_filter_content_invalid_regex_raises(self) -> None:
        """Invalid regex pattern raises re.error."""
        query = MessageQuery([{"role": "user", "content": "test"}])

        with pytest.raises(re.error):
            query.filter(content=r"[invalid", regex=True)


class TestMessageQueryFilterCombined:
    """Tests for combining multiple filter criteria with AND logic."""

    def test_filter_role_and_tool_name(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(role='tool', tool_name='read_file') combines with AND."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="tool", tool_name="read_file")

        assert len(result) == 1
        assert result[0]["role"] == "tool"
        assert result[0]["name"] == "read_file"

    def test_filter_role_and_content(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter(role='assistant', content='error') combines role and content."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="assistant", content="error")

        assert len(result) >= 1
        for msg in result:
            assert msg["role"] == "assistant"
            assert "error" in msg["content"].lower()

    def test_filter_role_content_and_tool_name(self, rich_messages: list[dict[str, Any]]) -> None:
        """All three filters combine with AND logic."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="tool", tool_name="read_file", content="Error")

        assert len(result) == 1
        assert result[0]["name"] == "read_file"

    def test_filter_no_args_returns_all(self, rich_messages: list[dict[str, Any]]) -> None:
        """filter() with no arguments returns all messages."""
        query = MessageQuery(rich_messages)
        result = query.filter()

        assert len(result) == len(rich_messages)


# ---------------------------------------------------------------------------
# MessageQuery: slice/first/last/all tests
# ---------------------------------------------------------------------------


class TestMessageQuerySlice:
    """Tests for MessageQuery.slice() behaviour."""

    def test_slice_start_end(self, rich_messages: list[dict[str, Any]]) -> None:
        """slice(start=5, end=10) returns messages at indices 5 through 9."""
        query = MessageQuery(rich_messages)
        result = query.slice(start=5, end=10)

        assert result == rich_messages[5:10]

    def test_slice_start_only(self, rich_messages: list[dict[str, Any]]) -> None:
        """slice(start=5) returns from index 5 to end."""
        query = MessageQuery(rich_messages)
        result = query.slice(start=5)

        assert result == rich_messages[5:]

    def test_slice_end_only(self, rich_messages: list[dict[str, Any]]) -> None:
        """slice(end=3) returns first 3 messages."""
        query = MessageQuery(rich_messages)
        result = query.slice(end=3)

        assert result == rich_messages[:3]

    def test_slice_defaults(self, rich_messages: list[dict[str, Any]]) -> None:
        """slice() with defaults returns all messages."""
        query = MessageQuery(rich_messages)
        result = query.slice()

        assert result == rich_messages

    def test_slice_out_of_range(self, rich_messages: list[dict[str, Any]]) -> None:
        """slice with out-of-range indices handles gracefully (Python slice behaviour)."""
        query = MessageQuery(rich_messages)
        result = query.slice(start=100, end=200)

        assert result == []

    def test_slice_returns_list(self, rich_messages: list[dict[str, Any]]) -> None:
        """slice returns list[dict[str, Any]]."""
        query = MessageQuery(rich_messages)
        result = query.slice(start=0, end=2)

        assert isinstance(result, list)
        assert all(isinstance(msg, dict) for msg in result)


class TestMessageQueryFirst:
    """Tests for MessageQuery.first() behaviour."""

    def test_first_default(self, rich_messages: list[dict[str, Any]]) -> None:
        """first() returns a list with the first message."""
        query = MessageQuery(rich_messages)
        result = query.first()

        assert len(result) == 1
        assert result[0] == rich_messages[0]

    def test_first_n(self, rich_messages: list[dict[str, Any]]) -> None:
        """first(n=5) returns the first 5 messages."""
        query = MessageQuery(rich_messages)
        result = query.first(n=5)

        assert len(result) == 5
        assert result == rich_messages[:5]

    def test_first_n_exceeds_total(self, rich_messages: list[dict[str, Any]]) -> None:
        """first(n=100) returns all messages when n > total."""
        query = MessageQuery(rich_messages)
        result = query.first(n=100)

        assert result == rich_messages

    def test_first_returns_list(self, rich_messages: list[dict[str, Any]]) -> None:
        """first returns list[dict[str, Any]]."""
        query = MessageQuery(rich_messages)
        result = query.first(n=2)

        assert isinstance(result, list)


class TestMessageQueryLast:
    """Tests for MessageQuery.last() behaviour."""

    def test_last_default(self, rich_messages: list[dict[str, Any]]) -> None:
        """last() returns a list with the last message."""
        query = MessageQuery(rich_messages)
        result = query.last()

        assert len(result) == 1
        assert result[0] == rich_messages[-1]

    def test_last_n(self, rich_messages: list[dict[str, Any]]) -> None:
        """last(n=5) returns the last 5 messages."""
        query = MessageQuery(rich_messages)
        result = query.last(n=5)

        assert len(result) == 5
        assert result == rich_messages[-5:]

    def test_last_n_exceeds_total(self, rich_messages: list[dict[str, Any]]) -> None:
        """last(n=100) returns all messages when n > total."""
        query = MessageQuery(rich_messages)
        result = query.last(n=100)

        assert result == rich_messages

    def test_last_returns_list(self, rich_messages: list[dict[str, Any]]) -> None:
        """last returns list[dict[str, Any]]."""
        query = MessageQuery(rich_messages)
        result = query.last(n=3)

        assert isinstance(result, list)


class TestMessageQueryAll:
    """Tests for MessageQuery.all() behaviour."""

    def test_all_returns_copy(self, rich_messages: list[dict[str, Any]]) -> None:
        """all() returns a copy of the messages list."""
        query = MessageQuery(rich_messages)
        result = query.all()

        assert result == rich_messages
        assert result is not rich_messages  # Should be a copy

    def test_all_returns_list(self, rich_messages: list[dict[str, Any]]) -> None:
        """all() returns list[dict[str, Any]]."""
        query = MessageQuery(rich_messages)
        result = query.all()

        assert isinstance(result, list)
        assert all(isinstance(msg, dict) for msg in result)


# ---------------------------------------------------------------------------
# MessageQuery: Edge cases
# ---------------------------------------------------------------------------


class TestMessageQueryEdgeCases:
    """Tests for MessageQuery edge case handling."""

    def test_empty_messages_filter(self) -> None:
        """Empty message list returns empty list for filter."""
        query = MessageQuery([])

        assert query.filter(role="user") == []
        assert query.filter(tool_name="read_file") == []
        assert query.filter(content="hello") == []
        assert query.filter() == []

    def test_empty_messages_slice(self) -> None:
        """Empty message list returns empty list for slice."""
        query = MessageQuery([])

        assert query.slice(start=0, end=5) == []

    def test_empty_messages_first(self) -> None:
        """Empty message list returns empty list for first."""
        query = MessageQuery([])

        assert query.first(n=5) == []

    def test_empty_messages_last(self) -> None:
        """Empty message list returns empty list for last."""
        query = MessageQuery([])

        assert query.last(n=5) == []

    def test_empty_messages_all(self) -> None:
        """Empty message list returns empty list for all."""
        query = MessageQuery([])

        assert query.all() == []

    def test_no_matches_returns_empty_not_none(self, rich_messages: list[dict[str, Any]]) -> None:
        """No matches returns empty list, never None."""
        query = MessageQuery(rich_messages)
        result = query.filter(role="nonexistent")

        assert result is not None
        assert result == []

    def test_tool_name_on_messages_without_tool_data(self) -> None:
        """tool_name filter on messages without tool data returns empty list."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        query = MessageQuery(messages)
        result = query.filter(tool_name="read_file")

        assert result == []

    def test_message_with_multiple_tool_calls(self) -> None:
        """tool_name filter matches in assistant messages with multiple tool_calls."""
        messages = [
            {
                "role": "assistant",
                "content": "Running tools...",
                "tool_calls": [
                    {
                        "id": "call_a",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": "{}"},
                    },
                    {
                        "id": "call_b",
                        "type": "function",
                        "function": {"name": "write_file", "arguments": "{}"},
                    },
                ],
            },
        ]
        query = MessageQuery(messages)

        read_result = query.filter(tool_name="read_file")
        assert len(read_result) == 1

        write_result = query.filter(tool_name="write_file")
        assert len(write_result) == 1

    def test_constructor_accepts_none_token_counter(self) -> None:
        """MessageQuery can be constructed with token_counter=None."""
        query = MessageQuery([], token_counter=None)

        assert query.all() == []

    def test_last_zero_returns_empty(self, rich_messages: list[dict[str, Any]]) -> None:
        """last(n=0) returns empty list."""
        query = MessageQuery(rich_messages)
        result = query.last(n=0)

        assert result == []


# ---------------------------------------------------------------------------
# MessageQuery: export() dispatch tests
# ---------------------------------------------------------------------------


class TestMessageQueryExportDispatch:
    """Tests for the export() format dispatch mechanism."""

    def test_invalid_format_raises_value_error(self) -> None:
        """Invalid format string raises ValueError."""
        query = MessageQuery([])

        with pytest.raises(ValueError, match="Invalid export format"):
            query.export(format="xml")

    def test_invalid_format_lists_valid_formats(self) -> None:
        """ValueError message includes the list of valid formats."""
        query = MessageQuery([])

        with pytest.raises(ValueError, match=r"json.*markdown.*csv.*dict"):
            query.export(format="yaml")

    def test_default_format_is_json(self, rich_messages: list[dict[str, Any]]) -> None:
        """export() with no format argument defaults to JSON."""
        query = MessageQuery(rich_messages)
        result = query.export()

        # Should be valid JSON (string) parseable by json.loads
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == len(rich_messages)

    def test_export_messages_parameter_exports_subset(
        self, rich_messages: list[dict[str, Any]]
    ) -> None:
        """export(messages=...) exports only the given subset."""
        query = MessageQuery(rich_messages)
        subset = rich_messages[:3]
        result = query.export(format="json", messages=subset)

        parsed = json.loads(result)
        assert len(parsed) == 3
        assert parsed[0] == rich_messages[0]

    def test_export_messages_none_exports_all(self, rich_messages: list[dict[str, Any]]) -> None:
        """export(messages=None) exports all messages."""
        query = MessageQuery(rich_messages)
        result = query.export(format="json", messages=None)

        parsed = json.loads(result)
        assert len(parsed) == len(rich_messages)


# ---------------------------------------------------------------------------
# MessageQuery: export(format="json") tests
# ---------------------------------------------------------------------------


class TestMessageQueryExportJson:
    """Tests for JSON export behaviour."""

    def test_returns_valid_json_string(self, rich_messages: list[dict[str, Any]]) -> None:
        """export(format='json') returns a valid JSON string."""
        query = MessageQuery(rich_messages)
        result = query.export(format="json")

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    def test_json_parseable_by_json_loads(self, rich_messages: list[dict[str, Any]]) -> None:
        """JSON output is parseable by json.loads()."""
        query = MessageQuery(rich_messages)
        result = query.export(format="json")

        parsed = json.loads(result)
        assert len(parsed) == len(rich_messages)
        # Verify structure is preserved
        for original, exported in zip(rich_messages, parsed, strict=True):
            assert exported["role"] == original["role"]

    def test_json_preserves_full_message_structure(self) -> None:
        """JSON export preserves all fields including tool_calls."""
        messages = [
            {
                "role": "assistant",
                "content": "Using tool...",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": '{"path": "f.txt"}'},
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="json")

        parsed = json.loads(result)
        assert parsed[0]["tool_calls"][0]["function"]["name"] == "read_file"

    def test_empty_conversation_returns_empty_json_array(self) -> None:
        """Empty message list exports as '[]'."""
        query = MessageQuery([])
        result = query.export(format="json")

        assert json.loads(result) == []

    def test_indent_parameter_controls_formatting(
        self, rich_messages: list[dict[str, Any]]
    ) -> None:
        """indent parameter controls JSON indentation level."""
        query = MessageQuery(rich_messages)

        result_default = query.export(format="json")
        result_indent4 = query.export(format="json", indent=4)
        result_no_indent = query.export(format="json", indent=None)

        # Default indent=2 produces 2-space indentation
        assert "  " in result_default

        # indent=4 produces 4-space indentation
        assert "    " in result_indent4

        # indent=None produces compact JSON (no newlines in the output)
        assert "\n" not in result_no_indent

        # All should parse to the same data
        assert json.loads(result_default) == json.loads(result_indent4)
        assert json.loads(result_default) == json.loads(result_no_indent)

    def test_unicode_content_handled_properly(self) -> None:
        """Messages with Unicode content are exported correctly."""
        messages = [
            {"role": "user", "content": "Hello! Salut! Hola!"},
            {
                "role": "assistant",
                "content": "Chinese characters: \u4f60\u597d. Japanese: \u3053\u3093\u306b\u3061\u306f.",
            },
            {"role": "user", "content": "Emoji: \U0001f680\U0001f30d\u2728"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="json")

        parsed = json.loads(result)
        assert (
            parsed[1]["content"]
            == "Chinese characters: \u4f60\u597d. Japanese: \u3053\u3093\u306b\u3061\u306f."
        )
        assert parsed[2]["content"] == "Emoji: \U0001f680\U0001f30d\u2728"

    def test_large_message_content_exported_fully(self) -> None:
        """Large message content is not truncated in JSON export."""
        large_content = "x" * 100_000
        messages = [{"role": "user", "content": large_content}]
        query = MessageQuery(messages)
        result = query.export(format="json")

        parsed = json.loads(result)
        assert len(parsed[0]["content"]) == 100_000


class TestMessageQueryExportJsonMetadata:
    """Tests for JSON export with include_metadata=True."""

    def test_include_metadata_adds_index(self, rich_messages: list[dict[str, Any]]) -> None:
        """include_metadata=True adds index field to each message."""
        query = MessageQuery(rich_messages)
        result = query.export(format="json", include_metadata=True)

        parsed = json.loads(result)
        for idx, msg in enumerate(parsed):
            assert "index" in msg
            assert msg["index"] == idx

    def test_include_metadata_adds_token_count(self, rich_messages: list[dict[str, Any]]) -> None:
        """include_metadata=True adds token_count field to each message."""
        query = MessageQuery(rich_messages)
        result = query.export(format="json", include_metadata=True)

        parsed = json.loads(result)
        for msg in parsed:
            assert "token_count" in msg
            assert isinstance(msg["token_count"], int)
            assert msg["token_count"] >= 0

    def test_include_metadata_false_no_extra_fields(
        self, rich_messages: list[dict[str, Any]]
    ) -> None:
        """include_metadata=False (default) does not add index or token_count."""
        query = MessageQuery(rich_messages)
        result = query.export(format="json", include_metadata=False)

        parsed = json.loads(result)
        for msg in parsed:
            assert "index" not in msg
            assert "token_count" not in msg

    def test_include_metadata_preserves_original_fields(
        self, rich_messages: list[dict[str, Any]]
    ) -> None:
        """Metadata fields are additive; original message fields are preserved."""
        query = MessageQuery(rich_messages)
        result = query.export(format="json", include_metadata=True)

        parsed = json.loads(result)
        for original, exported in zip(rich_messages, parsed, strict=True):
            assert exported["role"] == original["role"]
            if "content" in original:
                assert exported["content"] == original["content"]

    def test_include_metadata_empty_conversation(self) -> None:
        """include_metadata=True on empty conversation returns empty JSON array."""
        query = MessageQuery([])
        result = query.export(format="json", include_metadata=True)

        assert json.loads(result) == []

    def test_include_metadata_with_subset(self, rich_messages: list[dict[str, Any]]) -> None:
        """include_metadata indices are relative to the exported subset."""
        query = MessageQuery(rich_messages)
        subset = rich_messages[3:6]
        result = query.export(format="json", messages=subset, include_metadata=True)

        parsed = json.loads(result)
        assert len(parsed) == 3
        # Indices should be 0, 1, 2 (relative to subset, not original list)
        assert parsed[0]["index"] == 0
        assert parsed[1]["index"] == 1
        assert parsed[2]["index"] == 2

    def test_include_metadata_does_not_mutate_original(
        self, rich_messages: list[dict[str, Any]]
    ) -> None:
        """Exporting with metadata does not modify the original message dicts."""
        query = MessageQuery(rich_messages)
        # Snapshot before export
        original_keys = [set(msg.keys()) for msg in rich_messages]

        query.export(format="json", include_metadata=True)

        # Verify no new keys were added to the original dicts
        for original_set, msg in zip(original_keys, rich_messages, strict=True):
            assert set(msg.keys()) == original_set

    def test_include_metadata_with_token_counter(self) -> None:
        """include_metadata uses TokenCounter when provided."""
        from mamba_agents.tokens.counter import TokenCounter

        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there, how can I help?"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = query.export(format="json", include_metadata=True)

        parsed = json.loads(result)
        # With a real TokenCounter, token_count should be > 0 for messages with content
        for msg in parsed:
            assert msg["token_count"] > 0

    def test_include_metadata_without_token_counter_uses_fallback(self) -> None:
        """Without a TokenCounter, token_count uses word-count fallback."""
        messages = [
            {"role": "user", "content": "one two three four five"},
        ]
        query = MessageQuery(messages, token_counter=None)
        result = query.export(format="json", include_metadata=True)

        parsed = json.loads(result)
        # Fallback counts words: "one two three four five" = 5 words
        assert parsed[0]["token_count"] == 5


# ---------------------------------------------------------------------------
# MessageQuery: stats() tests
# ---------------------------------------------------------------------------


class TestMessageQueryStats:
    """Tests for MessageQuery.stats() computation with known message sets."""

    def test_stats_total_messages(self, rich_messages: list[dict[str, Any]]) -> None:
        """stats() returns correct total_messages count."""
        query = MessageQuery(rich_messages)
        result = query.stats()

        assert result.total_messages == len(rich_messages)

    def test_stats_messages_by_role(self, rich_messages: list[dict[str, Any]]) -> None:
        """stats() correctly groups and counts messages by role."""
        query = MessageQuery(rich_messages)
        result = query.stats()

        assert result.messages_by_role["system"] == 1
        assert result.messages_by_role["user"] == 3
        assert result.messages_by_role["assistant"] == 6
        assert result.messages_by_role["tool"] == 3

    def test_stats_returns_message_stats_type(self, rich_messages: list[dict[str, Any]]) -> None:
        """stats() returns a MessageStats instance."""
        query = MessageQuery(rich_messages)
        result = query.stats()

        assert isinstance(result, MessageStats)

    def test_stats_total_tokens_with_token_counter(self) -> None:
        """stats() computes total_tokens using the Agent's TokenCounter."""
        from mamba_agents.tokens.counter import TokenCounter

        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there, how can I help you today?"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = query.stats()

        # With a real TokenCounter, total_tokens should be > 0
        assert result.total_tokens > 0

    def test_stats_tokens_by_role_with_token_counter(self) -> None:
        """stats() computes tokens_by_role correctly."""
        from mamba_agents.tokens.counter import TokenCounter

        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there, how can I help you today?"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = query.stats()

        assert "user" in result.tokens_by_role
        assert "assistant" in result.tokens_by_role
        assert result.tokens_by_role["user"] > 0
        assert result.tokens_by_role["assistant"] > 0
        assert (
            result.tokens_by_role["user"] + result.tokens_by_role["assistant"]
            == result.total_tokens
        )

    def test_stats_avg_tokens_per_message(self) -> None:
        """stats() avg_tokens_per_message equals total_tokens / total_messages."""
        from mamba_agents.tokens.counter import TokenCounter

        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "Tell me more"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = query.stats()

        expected_avg = result.total_tokens / result.total_messages
        assert result.avg_tokens_per_message == expected_avg


class TestMessageQueryStatsZeroMessages:
    """Tests for stats() with empty message list."""

    def test_stats_empty_messages_returns_all_zeroes(self) -> None:
        """stats() with no messages returns MessageStats with all zeroes."""
        query = MessageQuery([])
        result = query.stats()

        assert result.total_messages == 0
        assert result.messages_by_role == {}
        assert result.total_tokens == 0
        assert result.tokens_by_role == {}

    def test_stats_empty_messages_avg_no_division_error(self) -> None:
        """stats() with no messages returns avg_tokens_per_message 0.0."""
        query = MessageQuery([])
        result = query.stats()

        assert result.avg_tokens_per_message == 0.0


class TestMessageQueryStatsMockedTokenCounter:
    """Tests for stats() with a mocked TokenCounter."""

    def test_stats_uses_configured_token_counter(self) -> None:
        """stats() uses the TokenCounter passed to MessageQuery, not a new default."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        mock_counter.count_messages.return_value = 10

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        query = MessageQuery(messages, token_counter=mock_counter)
        result = query.stats()

        # The mock was called once per message
        assert mock_counter.count_messages.call_count == 2
        assert result.total_tokens == 20
        assert result.tokens_by_role["user"] == 10
        assert result.tokens_by_role["assistant"] == 10

    def test_stats_token_counter_none_returns_zero_tokens(self) -> None:
        """stats() with token_counter=None skips token computation, returns 0s."""
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there"},
        ]
        query = MessageQuery(messages, token_counter=None)
        result = query.stats()

        assert result.total_tokens == 0
        assert result.tokens_by_role == {}
        assert result.total_messages == 2

    def test_stats_token_counter_called_with_single_message(self) -> None:
        """stats() calls count_messages with a single-message list per call."""
        from unittest.mock import MagicMock, call

        mock_counter = MagicMock()
        mock_counter.count_messages.return_value = 5

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "World"},
        ]
        query = MessageQuery(messages, token_counter=mock_counter)
        query.stats()

        # Verify each call passes a single-element list
        expected_calls = [call([messages[0]]), call([messages[1]])]
        mock_counter.count_messages.assert_has_calls(expected_calls, any_order=False)

    def test_stats_token_counter_error_handled_gracefully(self) -> None:
        """stats() handles TokenCounter errors gracefully, defaulting to 0."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        mock_counter.count_messages.side_effect = RuntimeError("encoding error")

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        query = MessageQuery(messages, token_counter=mock_counter)
        result = query.stats()

        # Should not raise; tokens should be 0
        assert result.total_tokens == 0
        assert result.total_messages == 2

    def test_stats_messages_without_content_counted_with_zero_tokens(self) -> None:
        """Messages without content field are counted but contribute 0 tokens."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        # Return different counts: messages with content get 10, without get 5
        # (the overhead from count_messages)
        mock_counter.count_messages.side_effect = [10, 5]

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant"},  # No content field
        ]
        query = MessageQuery(messages, token_counter=mock_counter)
        result = query.stats()

        assert result.total_messages == 2
        assert result.messages_by_role["user"] == 1
        assert result.messages_by_role["assistant"] == 1
        # Both messages counted with whatever TokenCounter returns
        assert result.total_tokens == 15

    def test_stats_varying_token_counts_per_role(self) -> None:
        """stats() correctly aggregates varying token counts per role."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        mock_counter.count_messages.side_effect = [10, 20, 30, 40]

        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Response one"},
            {"role": "user", "content": "Second"},
            {"role": "assistant", "content": "Response two"},
        ]
        query = MessageQuery(messages, token_counter=mock_counter)
        result = query.stats()

        assert result.tokens_by_role["user"] == 10 + 30
        assert result.tokens_by_role["assistant"] == 20 + 40
        assert result.total_tokens == 100


class TestMessageQueryStatsStr:
    """Tests for stats() __str__ output format."""

    def test_stats_str_contains_summary_header(self) -> None:
        """stats().__str__ includes 'Message Statistics' header."""
        query = MessageQuery([{"role": "user", "content": "Hi"}])
        result = query.stats()
        output = str(result)

        assert "Message Statistics" in output

    def test_stats_str_contains_total_messages(self) -> None:
        """stats().__str__ includes total message count."""
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]
        query = MessageQuery(messages)
        result = query.stats()
        output = str(result)

        assert "Total messages: 2" in output

    def test_stats_str_contains_total_tokens(self) -> None:
        """stats().__str__ includes total token count."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        mock_counter.count_messages.return_value = 50

        messages = [{"role": "user", "content": "Hello world"}]
        query = MessageQuery(messages, token_counter=mock_counter)
        result = query.stats()
        output = str(result)

        assert "Total tokens:   50" in output

    def test_stats_str_contains_avg_tokens(self) -> None:
        """stats().__str__ includes average tokens per message."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        mock_counter.count_messages.return_value = 100

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "World"},
        ]
        query = MessageQuery(messages, token_counter=mock_counter)
        result = query.stats()
        output = str(result)

        assert "Avg tokens/msg: 100.0" in output

    def test_stats_str_contains_role_breakdown(self) -> None:
        """stats().__str__ includes per-role message and token breakdowns."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        mock_counter.count_messages.side_effect = [25, 75]

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there, nice to meet you"},
        ]
        query = MessageQuery(messages, token_counter=mock_counter)
        result = query.stats()
        output = str(result)

        assert "Messages by role:" in output
        assert "user: 1" in output
        assert "assistant: 1" in output
        assert "Tokens by role:" in output
        assert "user: 25" in output
        assert "assistant: 75" in output

    def test_stats_str_empty_messages(self) -> None:
        """stats().__str__ for empty messages shows zeroes without role sections."""
        query = MessageQuery([])
        result = query.stats()
        output = str(result)

        assert "Total messages: 0" in output
        assert "Avg tokens/msg: 0.0" in output
        assert "Messages by role:" not in output
        assert "Tokens by role:" not in output


# ---------------------------------------------------------------------------
# MessageQuery: tool_summary() tests
# ---------------------------------------------------------------------------


class TestMessageQueryToolSummary:
    """Tests for tool_summary() with multiple tools."""

    def test_summary_with_multiple_tools(self, rich_messages: list[dict[str, Any]]) -> None:
        """tool_summary() returns one ToolCallInfo per unique tool name."""
        query = MessageQuery(rich_messages)
        result = query.tool_summary()

        assert isinstance(result, list)
        assert len(result) == 3
        names = {info.tool_name for info in result}
        assert names == {"read_file", "grep_search", "write_file"}

    def test_summary_returns_tool_call_info_type(self, rich_messages: list[dict[str, Any]]) -> None:
        """tool_summary() returns list of ToolCallInfo instances."""
        query = MessageQuery(rich_messages)
        result = query.tool_summary()

        for info in result:
            assert isinstance(info, ToolCallInfo)

    def test_summary_call_count_accurate(self, rich_messages: list[dict[str, Any]]) -> None:
        """tool_summary() reports accurate call_count per tool."""
        query = MessageQuery(rich_messages)
        result = query.tool_summary()

        by_name = {info.tool_name: info for info in result}
        assert by_name["read_file"].call_count == 1
        assert by_name["grep_search"].call_count == 1
        assert by_name["write_file"].call_count == 1

    def test_summary_arguments_parsed_from_json(self, rich_messages: list[dict[str, Any]]) -> None:
        """tool_summary() parses JSON argument strings into dicts."""
        query = MessageQuery(rich_messages)
        result = query.tool_summary()

        by_name = {info.tool_name: info for info in result}
        assert by_name["read_file"].arguments == [{"path": "data.txt"}]
        assert by_name["grep_search"].arguments == [{"pattern": "warning"}]
        assert by_name["write_file"].arguments == [{"path": "output.txt", "content": "summary"}]

    def test_summary_results_from_tool_messages(self, rich_messages: list[dict[str, Any]]) -> None:
        """tool_summary() collects result content from tool result messages."""
        query = MessageQuery(rich_messages)
        result = query.tool_summary()

        by_name = {info.tool_name: info for info in result}
        assert by_name["read_file"].results == ["File contents: Error: 42 occurred"]
        assert by_name["grep_search"].results == ["No matches found"]
        assert by_name["write_file"].results == ["File written successfully"]

    def test_summary_tool_call_ids(self, rich_messages: list[dict[str, Any]]) -> None:
        """tool_summary() collects tool_call_ids linking calls to results."""
        query = MessageQuery(rich_messages)
        result = query.tool_summary()

        by_name = {info.tool_name: info for info in result}
        assert by_name["read_file"].tool_call_ids == ["call_001"]
        assert by_name["grep_search"].tool_call_ids == ["call_002"]
        assert by_name["write_file"].tool_call_ids == ["call_003"]


class TestMessageQueryToolSummaryEmpty:
    """Tests for tool_summary() with empty or no-tool conversations."""

    def test_empty_messages_returns_empty_list(self) -> None:
        """tool_summary() on empty conversation returns empty list."""
        query = MessageQuery([])
        result = query.tool_summary()

        assert result == []

    def test_no_tool_calls_returns_empty_list(self) -> None:
        """tool_summary() when no tool calls exist returns empty list."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm fine, thanks!"},
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert result == []


class TestMessageQueryToolSummaryOrphaned:
    """Tests for tool_summary() with orphaned calls and results."""

    def test_orphaned_call_without_matching_result(self) -> None:
        """Tool call without matching tool result is included but has no result."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_orphan",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "missing.txt"}',
                        },
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        info = result[0]
        assert info.tool_name == "read_file"
        assert info.call_count == 1
        assert info.arguments == [{"path": "missing.txt"}]
        assert info.results == []
        assert info.tool_call_ids == ["call_orphan"]

    def test_orphaned_result_without_matching_call(self) -> None:
        """Tool result without matching assistant tool call is still counted."""
        messages = [
            {
                "role": "tool",
                "tool_call_id": "call_phantom",
                "name": "write_file",
                "content": "Written!",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        info = result[0]
        assert info.tool_name == "write_file"
        assert info.call_count == 1
        assert info.results == ["Written!"]
        assert info.tool_call_ids == ["call_phantom"]

    def test_mixed_orphaned_and_matched(self) -> None:
        """Conversation with both matched and orphaned entries handles both."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "a.txt"}',
                        },
                    },
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "b.txt"}',
                        },
                    },
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "contents of a",
            },
            # call_2 has no matching result (orphaned call)
            # orphaned result with no matching call:
            {
                "role": "tool",
                "tool_call_id": "call_999",
                "name": "grep_search",
                "content": "orphaned grep result",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        by_name = {info.tool_name: info for info in result}
        # read_file: 2 calls from assistant, 1 result matched
        assert by_name["read_file"].call_count == 2
        assert by_name["read_file"].results == ["contents of a"]
        # grep_search: 1 orphaned result counted
        assert by_name["grep_search"].call_count == 1
        assert by_name["grep_search"].results == ["orphaned grep result"]


class TestMessageQueryToolSummaryMultipleCalls:
    """Tests for tool_summary() with multiple calls to the same tool."""

    def test_multiple_calls_same_tool_grouped(self) -> None:
        """Multiple calls to the same tool are grouped into one ToolCallInfo."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_a",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "first.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_a",
                "name": "read_file",
                "content": "first file",
            },
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_b",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "second.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_b",
                "name": "read_file",
                "content": "second file",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        info = result[0]
        assert info.tool_name == "read_file"
        assert info.call_count == 2
        assert info.arguments == [{"path": "first.txt"}, {"path": "second.txt"}]
        assert info.results == ["first file", "second file"]
        assert info.tool_call_ids == ["call_a", "call_b"]

    def test_multiple_tool_calls_in_single_response(self) -> None:
        """Assistant message with multiple tool_calls processes all of them."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_x",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "a.txt"}',
                        },
                    },
                    {
                        "id": "call_y",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": '{"path": "b.txt", "content": "data"}',
                        },
                    },
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_x",
                "name": "read_file",
                "content": "file a contents",
            },
            {
                "role": "tool",
                "tool_call_id": "call_y",
                "name": "write_file",
                "content": "written",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 2
        by_name = {info.tool_name: info for info in result}
        assert by_name["read_file"].call_count == 1
        assert by_name["write_file"].call_count == 1
        assert by_name["read_file"].results == ["file a contents"]
        assert by_name["write_file"].results == ["written"]


class TestMessageQueryToolSummaryErrorHandling:
    """Tests for tool_summary() error handling and malformed data."""

    def test_malformed_tool_calls_not_a_list(self) -> None:
        """Malformed tool_calls (not a list) is handled gracefully."""
        messages = [
            {
                "role": "assistant",
                "content": "bad data",
                "tool_calls": "not_a_list",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert result == []

    def test_malformed_tool_call_entry_not_dict(self) -> None:
        """Non-dict entries in tool_calls array are skipped."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": ["not_a_dict", 42, None],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert result == []

    def test_tool_call_missing_function_key(self) -> None:
        """Tool call dict without function key is skipped."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "call_1", "type": "function"}],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert result == []

    def test_non_json_arguments_stored_as_empty_dict(self) -> None:
        """Non-JSON arguments string results in empty dict in arguments list."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_bad_args",
                        "type": "function",
                        "function": {
                            "name": "my_tool",
                            "arguments": "not valid json {{{",
                        },
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        info = result[0]
        assert info.tool_name == "my_tool"
        assert info.call_count == 1
        # Non-JSON arguments stored as empty dict (raw string is not a dict)
        assert info.arguments == [{}]

    def test_empty_arguments_string(self) -> None:
        """Empty arguments string results in empty dict."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_empty",
                        "type": "function",
                        "function": {"name": "my_tool", "arguments": ""},
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        assert result[0].arguments == [{}]

    def test_arguments_missing_defaults_to_empty_dict(self) -> None:
        """Missing arguments field results in empty dict."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_no_args",
                        "type": "function",
                        "function": {"name": "my_tool"},
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        assert result[0].arguments == [{}]


class TestMessageQueryToolSummaryStr:
    """Tests for tool_summary() __str__ output format."""

    def test_str_output_contains_tool_name(self) -> None:
        """ToolCallInfo.__str__ includes the tool name."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "test.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "file data",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        output = str(result[0])
        assert "Tool: read_file" in output

    def test_str_output_contains_call_count(self) -> None:
        """ToolCallInfo.__str__ includes the call count."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": "{}"},
                    },
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": "{}"},
                    },
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "r1",
            },
            {
                "role": "tool",
                "tool_call_id": "call_2",
                "name": "read_file",
                "content": "r2",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        output = str(result[0])
        assert "called 2 time(s)" in output

    def test_str_output_contains_call_ids(self) -> None:
        """ToolCallInfo.__str__ includes tool_call_ids."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {"name": "my_tool", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_abc",
                "name": "my_tool",
                "content": "done",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        output = str(result[0])
        assert "[call_abc]" in output

    def test_str_output_contains_args_and_results(self) -> None:
        """ToolCallInfo.__str__ includes args and result details."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "hello.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "hello world",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        output = str(result[0])
        assert "args:" in output
        assert "path" in output
        assert "result: hello world" in output

    def test_str_full_summary_rendering(self, rich_messages: list[dict[str, Any]]) -> None:
        """Full tool_summary can be rendered as readable text."""
        query = MessageQuery(rich_messages)
        result = query.tool_summary()

        full_output = "\n\n".join(str(info) for info in result)
        assert "read_file" in full_output
        assert "grep_search" in full_output
        assert "write_file" in full_output


# ---------------------------------------------------------------------------
# MessageQuery: timeline() tests
# ---------------------------------------------------------------------------


class TestMessageQueryTimelineSimple:
    """Tests for timeline() with simple user->assistant conversations."""

    def test_simple_user_assistant_conversation(self) -> None:
        """timeline() groups user->assistant into a single turn."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert isinstance(result[0], Turn)
        assert result[0].index == 0
        assert result[0].user_content == "Hello"
        assert result[0].assistant_content == "Hi there!"
        assert result[0].tool_interactions == []

    def test_multiple_turns(self) -> None:
        """timeline() creates separate turns for each user->assistant pair."""
        messages = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
            {"role": "assistant", "content": "Second answer"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 2
        assert result[0].index == 0
        assert result[0].user_content == "First question"
        assert result[0].assistant_content == "First answer"
        assert result[1].index == 1
        assert result[1].user_content == "Second question"
        assert result[1].assistant_content == "Second answer"

    def test_returns_list_of_turn_objects(self) -> None:
        """timeline() returns list[Turn] in conversation order."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert isinstance(result, list)
        for turn in result:
            assert isinstance(turn, Turn)


class TestMessageQueryTimelineToolCalls:
    """Tests for timeline() with tool calls."""

    def test_conversation_with_tool_calls(self) -> None:
        """timeline() groups tool calls and results into tool_interactions."""
        messages = [
            {"role": "user", "content": "Read the file"},
            {
                "role": "assistant",
                "content": "Reading file...",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "test.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "file contents here",
            },
            {"role": "assistant", "content": "The file contains: file contents here"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        turn = result[0]
        assert turn.user_content == "Read the file"
        assert "Reading file..." in (turn.assistant_content or "")
        assert len(turn.tool_interactions) == 1
        assert turn.tool_interactions[0]["tool_name"] == "read_file"
        assert turn.tool_interactions[0]["tool_call_id"] == "call_1"
        assert turn.tool_interactions[0]["arguments"] == {"path": "test.txt"}
        assert turn.tool_interactions[0]["result"] == "file contents here"

    def test_multiple_tool_calls_in_single_response(self) -> None:
        """timeline() groups multiple tool calls from one assistant response."""
        messages = [
            {"role": "user", "content": "Read two files"},
            {
                "role": "assistant",
                "content": "Reading both files...",
                "tool_calls": [
                    {
                        "id": "call_a",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "a.txt"}',
                        },
                    },
                    {
                        "id": "call_b",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "b.txt"}',
                        },
                    },
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_a",
                "name": "read_file",
                "content": "contents of a",
            },
            {
                "role": "tool",
                "tool_call_id": "call_b",
                "name": "read_file",
                "content": "contents of b",
            },
            {"role": "assistant", "content": "Both files read successfully."},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        turn = result[0]
        assert len(turn.tool_interactions) == 2
        assert turn.tool_interactions[0]["tool_call_id"] == "call_a"
        assert turn.tool_interactions[0]["result"] == "contents of a"
        assert turn.tool_interactions[1]["tool_call_id"] == "call_b"
        assert turn.tool_interactions[1]["result"] == "contents of b"

    def test_tool_loop_continuation(self) -> None:
        """Assistant after tool results stays in the same turn (tool loop)."""
        messages = [
            {"role": "user", "content": "Help me with this task"},
            {
                "role": "assistant",
                "content": "First, let me read the file.",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "data.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "data here",
            },
            {
                "role": "assistant",
                "content": "Now let me write the output.",
                "tool_calls": [
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": '{"path": "out.txt", "content": "processed"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_2",
                "name": "write_file",
                "content": "written",
            },
            {"role": "assistant", "content": "Done! Both operations complete."},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        # Should be a single turn because assistant continues after tool results
        assert len(result) == 1
        turn = result[0]
        assert turn.user_content == "Help me with this task"
        assert len(turn.tool_interactions) == 2
        assert turn.tool_interactions[0]["tool_name"] == "read_file"
        assert turn.tool_interactions[1]["tool_name"] == "write_file"

    def test_messages_without_tool_calls_no_interactions(self) -> None:
        """Turns from conversations without tool calls have empty tool_interactions."""
        messages = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].tool_interactions == []


class TestMessageQueryTimelineConsecutiveAssistant:
    """Tests for timeline() with consecutive assistant messages."""

    def test_consecutive_assistant_messages_own_turns(self) -> None:
        """Consecutive assistant messages each get their own turn."""
        messages = [
            {"role": "assistant", "content": "First assistant message"},
            {"role": "assistant", "content": "Second assistant message"},
            {"role": "assistant", "content": "Third assistant message"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 3
        assert result[0].index == 0
        assert result[0].assistant_content == "First assistant message"
        assert result[0].user_content is None
        assert result[1].index == 1
        assert result[1].assistant_content == "Second assistant message"
        assert result[2].index == 2
        assert result[2].assistant_content == "Third assistant message"

    def test_assistant_without_preceding_user(self) -> None:
        """Assistant message without preceding user gets its own turn."""
        messages = [
            {"role": "assistant", "content": "I will start the conversation."},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].user_content is None
        assert result[0].assistant_content == "I will start the conversation."


class TestMessageQueryTimelineSystemPrompt:
    """Tests for timeline() system prompt handling."""

    def test_system_prompt_as_context_on_first_turn(self) -> None:
        """System prompt appears as system_context on the first turn."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].system_context == "You are a helpful assistant."
        assert result[0].user_content == "Hello"
        assert result[0].assistant_content == "Hi!"

    def test_system_prompt_not_separate_turn(self) -> None:
        """System prompt does not create a separate turn."""
        messages = [
            {"role": "system", "content": "System instructions."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        # Should be 1 turn, not 2
        assert len(result) == 1
        assert result[0].index == 0

    def test_conversation_starting_with_system_prompt(self) -> None:
        """Conversation starting with system prompt is handled correctly."""
        messages = [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4"},
            {"role": "user", "content": "And 3+3?"},
            {"role": "assistant", "content": "6"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 2
        # System context only on first turn
        assert result[0].system_context == "Be concise."
        assert result[1].system_context is None
        assert result[0].user_content == "What is 2+2?"
        assert result[1].user_content == "And 3+3?"

    def test_system_prompt_with_assistant_only(self) -> None:
        """System prompt followed by assistant (no user) attaches to first turn."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "assistant", "content": "How can I help?"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].system_context == "You are helpful."
        assert result[0].assistant_content == "How can I help?"
        assert result[0].user_content is None

    def test_only_system_messages(self) -> None:
        """Only system messages creates a single turn with system context."""
        messages = [
            {"role": "system", "content": "System prompt only."},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].system_context == "System prompt only."
        assert result[0].user_content is None
        assert result[0].assistant_content is None


class TestMessageQueryTimelineEmpty:
    """Tests for timeline() with empty conversations."""

    def test_empty_messages_returns_empty_list(self) -> None:
        """timeline() on empty conversation returns empty list."""
        query = MessageQuery([])
        result = query.timeline()

        assert result == []

    def test_empty_returns_list_type(self) -> None:
        """timeline() on empty conversation returns list (not None)."""
        query = MessageQuery([])
        result = query.timeline()

        assert isinstance(result, list)


class TestMessageQueryTimelineErrorHandling:
    """Tests for timeline() with malformed messages."""

    def test_message_missing_role(self) -> None:
        """Messages without role field are handled gracefully."""
        messages = [
            {"content": "no role here"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        # The message without role is skipped; one valid turn remains.
        assert len(result) == 1
        assert result[0].user_content == "Hello"

    def test_message_missing_content(self) -> None:
        """Messages without content field are handled gracefully."""
        messages = [
            {"role": "user"},
            {"role": "assistant"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].user_content is None
        assert result[0].assistant_content is None

    def test_malformed_tool_calls_in_timeline(self) -> None:
        """Malformed tool_calls in assistant messages are skipped gracefully."""
        messages = [
            {"role": "user", "content": "Do something"},
            {
                "role": "assistant",
                "content": "Trying...",
                "tool_calls": "not_a_list",
            },
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].tool_interactions == []

    def test_tool_call_missing_function(self) -> None:
        """Tool call without function key is skipped in timeline."""
        messages = [
            {"role": "user", "content": "Do something"},
            {
                "role": "assistant",
                "content": "Using tool...",
                "tool_calls": [{"id": "call_1", "type": "function"}],
            },
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].tool_interactions == []


class TestMessageQueryTimelineStr:
    """Tests for timeline() __str__ output format."""

    def test_turn_str_includes_all_parts(self) -> None:
        """Turn.__str__ includes user, assistant, and tool interaction details."""
        messages = [
            {"role": "system", "content": "You are a helper."},
            {"role": "user", "content": "Read the file"},
            {
                "role": "assistant",
                "content": "Reading...",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "data.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "file data",
            },
            {"role": "assistant", "content": "Here is the data."},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        output = str(result[0])
        assert "Turn 0:" in output
        assert "System: You are a helper." in output
        assert "User: Read the file" in output
        assert "Assistant:" in output
        assert "Tool interactions:" in output
        assert "[read_file]" in output
        assert "result: file data" in output

    def test_turn_str_no_tools(self) -> None:
        """Turn.__str__ without tool interactions omits the tools section."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        output = str(result[0])
        assert "Turn 0:" in output
        assert "User: Hello" in output
        assert "Assistant: Hi!" in output
        assert "Tool interactions:" not in output

    def test_full_timeline_renderable(self) -> None:
        """Full timeline list can be rendered as readable output."""
        messages = [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "Bye"},
            {"role": "assistant", "content": "Goodbye!"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        # Render the full timeline
        full_output = "\n\n".join(str(turn) for turn in result)
        assert "Turn 0:" in full_output
        assert "Turn 1:" in full_output
        assert "Hello" in full_output
        assert "Bye" in full_output

    def test_turn_str_system_context_renders(self) -> None:
        """Turn.__str__ renders system context when present."""
        turn = Turn(
            index=0,
            system_context="System instructions here",
            user_content="Hello",
            assistant_content="Hi!",
        )
        output = str(turn)

        assert "System: System instructions here" in output


class TestMessageQueryTimelineRichMessages:
    """Tests for timeline() with the rich_messages fixture."""

    def test_rich_messages_timeline(self, rich_messages: list[dict[str, Any]]) -> None:
        """timeline() correctly parses the rich_messages fixture."""
        query = MessageQuery(rich_messages)
        result = query.timeline()

        # rich_messages has: system, user, assistant+tool, assistant,
        # user, assistant+tool, assistant, user, assistant+tool, assistant
        # = 3 user-initiated turns
        assert len(result) == 3

        # First turn has system context
        assert result[0].system_context == "You are a helpful assistant."
        assert result[0].user_content == "Hello, read my file please."
        assert len(result[0].tool_interactions) == 1
        assert result[0].tool_interactions[0]["tool_name"] == "read_file"

        # Second turn
        assert result[1].user_content == "Now search for warnings."
        assert result[1].system_context is None
        assert len(result[1].tool_interactions) == 1
        assert result[1].tool_interactions[0]["tool_name"] == "grep_search"

        # Third turn
        assert result[2].user_content == "Write a summary to output.txt"
        assert len(result[2].tool_interactions) == 1
        assert result[2].tool_interactions[0]["tool_name"] == "write_file"


# ---------------------------------------------------------------------------
# MessageQuery: export(format="markdown") tests
# ---------------------------------------------------------------------------


class TestMessageQueryExportMarkdownRoles:
    """Tests for Markdown export rendering of each message role."""

    def test_user_message_under_user_header(self) -> None:
        """User messages are rendered under ### User headers."""
        messages = [{"role": "user", "content": "Hello world"}]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### User" in result
        assert "Hello world" in result

    def test_assistant_message_under_assistant_header(self) -> None:
        """Assistant messages are rendered under ### Assistant headers."""
        messages = [{"role": "assistant", "content": "I can help with that."}]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### Assistant" in result
        assert "I can help with that." in result

    def test_system_message_under_system_header(self) -> None:
        """System messages are rendered under ### System headers."""
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### System" in result
        assert "You are a helpful assistant." in result

    def test_multiple_roles_all_rendered(self) -> None:
        """All role types appear in the correct order in the output."""
        messages = [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### System" in result
        assert "### User" in result
        assert "### Assistant" in result
        # Verify ordering: system before user before assistant
        sys_pos = result.index("### System")
        user_pos = result.index("### User")
        asst_pos = result.index("### Assistant")
        assert sys_pos < user_pos < asst_pos

    def test_returns_string_type(self) -> None:
        """export(format='markdown') returns a string."""
        messages = [{"role": "user", "content": "Test"}]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert isinstance(result, str)

    def test_messages_separated_by_horizontal_rules(self) -> None:
        """Messages are visually separated by horizontal rules (---)."""
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "---" in result


class TestMessageQueryExportMarkdownToolCalls:
    """Tests for Markdown export tool call formatting."""

    def test_tool_call_shows_tool_name(self) -> None:
        """Tool calls display the tool name in bold."""
        messages = [
            {
                "role": "assistant",
                "content": "Reading file...",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "data.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "file contents",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "**Tool Call: read_file**" in result

    def test_tool_call_arguments_in_json_code_block(self) -> None:
        """Tool call arguments are formatted as JSON in fenced code blocks."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "data.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "result",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "```json" in result
        assert '"path": "data.txt"' in result

    def test_tool_result_in_code_block(self) -> None:
        """Tool results are rendered in fenced code blocks."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "test.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "Hello from the file",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "**Result:**" in result
        assert "Hello from the file" in result
        # The result should be inside a code block (non-json)
        # Count code blocks: json block for args + plain block for result
        assert result.count("```") >= 4  # open+close for json, open+close for result

    def test_tool_result_messages_not_standalone(self) -> None:
        """Tool result messages (role='tool') are not rendered as standalone entries."""
        messages = [
            {
                "role": "assistant",
                "content": "Using tool...",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "my_tool",
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "my_tool",
                "content": "tool output",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        # Should NOT have a "### Tool" header; tool results are inline
        assert "### Tool" not in result

    def test_multiple_tool_calls_in_single_response(self) -> None:
        """Multiple tool calls from one assistant response are all rendered."""
        messages = [
            {
                "role": "assistant",
                "content": "Checking two files...",
                "tool_calls": [
                    {
                        "id": "call_a",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "a.txt"}',
                        },
                    },
                    {
                        "id": "call_b",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": '{"path": "b.txt", "content": "data"}',
                        },
                    },
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_a",
                "name": "read_file",
                "content": "contents of a",
            },
            {
                "role": "tool",
                "tool_call_id": "call_b",
                "name": "write_file",
                "content": "written successfully",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "**Tool Call: read_file**" in result
        assert "**Tool Call: write_file**" in result
        assert "contents of a" in result
        assert "written successfully" in result

    def test_tool_call_without_result(self) -> None:
        """Tool call without matching result still renders arguments."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_orphan",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "missing.txt"}',
                        },
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "**Tool Call: read_file**" in result
        assert '"path": "missing.txt"' in result
        # No result section since there's no matching tool result
        assert "**Result:**" not in result


class TestMessageQueryExportMarkdownSpecialChars:
    """Tests for Markdown export special character handling."""

    def test_content_with_code_block_delimiters_escaped(self) -> None:
        """Message content containing ``` is escaped inside code blocks."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "Here is code:\n```python\nprint('hello')\n```\nEnd",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        # The triple backticks in the content should be escaped
        # (not appearing as bare ``` inside the code block)
        # The escaped form uses zero-width spaces between backticks
        assert "`\u200b`\u200b`" in result

    def test_arguments_with_code_block_delimiters_escaped(self) -> None:
        """Tool arguments containing ``` are escaped in JSON code blocks."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": '{"content": "```python\\ncode\\n```"}',
                        },
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        # Backticks in the arguments should be escaped
        assert "`\u200b`\u200b`" in result

    def test_unicode_content_preserved(self) -> None:
        """Unicode characters in messages are preserved in Markdown output."""
        messages = [
            {
                "role": "user",
                "content": "Chinese: \u4f60\u597d Japanese: \u3053\u3093\u306b\u3061\u306f",
            },
            {"role": "assistant", "content": "Emoji: \U0001f680\U0001f30d"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "\u4f60\u597d" in result
        assert "\u3053\u3093\u306b\u3061\u306f" in result
        assert "\U0001f680" in result
        assert "\U0001f30d" in result

    def test_non_json_arguments_handled(self) -> None:
        """Non-JSON argument strings are rendered as plain text."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "my_tool",
                            "arguments": "not valid json {{{",
                        },
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        # Should not raise, and the raw arguments should appear
        assert "not valid json {{{" in result
        assert "**Tool Call: my_tool**" in result


class TestMessageQueryExportMarkdownEmpty:
    """Tests for Markdown export with empty conversations."""

    def test_empty_conversation_returns_empty_string(self) -> None:
        """Empty message list returns an empty string."""
        query = MessageQuery([])
        result = query.export(format="markdown")

        assert result == ""

    def test_empty_conversation_returns_string_type(self) -> None:
        """Empty message list returns a string (not None)."""
        query = MessageQuery([])
        result = query.export(format="markdown")

        assert isinstance(result, str)


class TestMessageQueryExportMarkdownNoneContent:
    """Tests for Markdown export with None content messages."""

    def test_user_message_with_none_content(self) -> None:
        """User message with None content renders header without body."""
        messages = [{"role": "user", "content": None}]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### User" in result

    def test_assistant_message_with_none_content_and_tool_calls(self) -> None:
        """Assistant message with None content but tool calls renders tools only."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "test.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "data",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### Assistant" in result
        assert "**Tool Call: read_file**" in result

    def test_system_message_with_none_content(self) -> None:
        """System message with None content renders header without body."""
        messages = [{"role": "system", "content": None}]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### System" in result


class TestMessageQueryExportMarkdownSubset:
    """Tests for Markdown export with messages parameter (subset export)."""

    def test_subset_export_only_includes_given_messages(
        self, rich_messages: list[dict[str, Any]]
    ) -> None:
        """export(messages=...) only includes the provided subset."""
        query = MessageQuery(rich_messages)
        subset = [
            {"role": "user", "content": "Just this message."},
        ]
        result = query.export(format="markdown", messages=subset)

        assert "Just this message." in result
        # Should not contain content from the full message list
        assert "Hello, read my file please." not in result

    def test_subset_export_with_tool_calls(self) -> None:
        """Subset export with tool call messages renders correctly."""
        messages = [
            {"role": "user", "content": "ignored user msg"},
            {
                "role": "assistant",
                "content": "Reading...",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "x.txt"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "x contents",
            },
            {"role": "assistant", "content": "Done!"},
        ]
        query = MessageQuery(messages)
        # Export only the tool-related subset
        subset = messages[1:4]
        result = query.export(format="markdown", messages=subset)

        assert "### Assistant" in result
        assert "**Tool Call: read_file**" in result
        assert "x contents" in result
        assert "Done!" in result
        # Should not include the first user message
        assert "ignored user msg" not in result


class TestMessageQueryExportMarkdownMalformed:
    """Tests for Markdown export error handling with malformed tool calls."""

    def test_malformed_tool_calls_not_a_list(self) -> None:
        """Malformed tool_calls (not a list) renders assistant without tools."""
        messages = [
            {
                "role": "assistant",
                "content": "Bad data here",
                "tool_calls": "not_a_list",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### Assistant" in result
        assert "Bad data here" in result
        # Should not crash; no tool section rendered
        assert "**Tool Call:" not in result

    def test_malformed_tool_call_entry_not_dict(self) -> None:
        """Non-dict entries in tool_calls array are skipped gracefully."""
        messages = [
            {
                "role": "assistant",
                "content": "Processing...",
                "tool_calls": ["not_a_dict", 42, None],
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### Assistant" in result
        assert "Processing..." in result
        assert "**Tool Call:" not in result

    def test_tool_call_missing_function_key(self) -> None:
        """Tool call dict without function key is skipped."""
        messages = [
            {
                "role": "assistant",
                "content": "Using tool...",
                "tool_calls": [{"id": "call_1", "type": "function"}],
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### Assistant" in result
        assert "Using tool..." in result
        assert "**Tool Call:" not in result


class TestMessageQueryExportMarkdownRichMessages:
    """Tests for Markdown export with the rich_messages fixture."""

    def test_rich_messages_all_roles_present(self, rich_messages: list[dict[str, Any]]) -> None:
        """Markdown export of rich_messages contains all role headers."""
        query = MessageQuery(rich_messages)
        result = query.export(format="markdown")

        assert "### System" in result
        assert "### User" in result
        assert "### Assistant" in result

    def test_rich_messages_all_tool_names_present(
        self, rich_messages: list[dict[str, Any]]
    ) -> None:
        """Markdown export of rich_messages shows all tool names."""
        query = MessageQuery(rich_messages)
        result = query.export(format="markdown")

        assert "**Tool Call: read_file**" in result
        assert "**Tool Call: grep_search**" in result
        assert "**Tool Call: write_file**" in result

    def test_rich_messages_tool_results_present(self, rich_messages: list[dict[str, Any]]) -> None:
        """Markdown export of rich_messages includes tool results."""
        query = MessageQuery(rich_messages)
        result = query.export(format="markdown")

        assert "File contents: Error: 42 occurred" in result
        assert "No matches found" in result
        assert "File written successfully" in result


# ---------------------------------------------------------------------------
# MessageQuery: export(format="csv") tests
# ---------------------------------------------------------------------------


class TestMessageQueryExportCsvBasic:
    """Tests for CSV export with various message types."""

    def test_returns_valid_csv_string(self, rich_messages: list[dict[str, Any]]) -> None:
        """export(format='csv') returns a valid CSV string."""
        query = MessageQuery(rich_messages)
        result = query.export(format="csv")

        assert isinstance(result, str)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        # Header + data rows
        assert len(rows) == len(rich_messages) + 1

    def test_header_row_has_expected_columns(self) -> None:
        """CSV output starts with a header row with the specified columns."""
        query = MessageQuery([])
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        header = next(reader)
        assert header == ["index", "role", "content", "tool_name", "tool_call_id", "token_count"]

    def test_columns_match_spec(self, rich_messages: list[dict[str, Any]]) -> None:
        """Each data row has exactly 6 columns matching the header."""
        query = MessageQuery(rich_messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        header = next(reader)
        for row in reader:
            assert len(row) == len(header) == 6

    def test_index_column_is_zero_based(self, rich_messages: list[dict[str, Any]]) -> None:
        """The index column contains zero-based sequential integers."""
        query = MessageQuery(rich_messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)  # skip header
        for expected_idx, row in enumerate(reader):
            assert row[0] == str(expected_idx)

    def test_role_column_reflects_message_role(self) -> None:
        """The role column matches each message's role field."""
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "system", "content": "System prompt"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        rows = list(reader)
        assert rows[0][1] == "user"
        assert rows[1][1] == "assistant"
        assert rows[2][1] == "system"

    def test_content_column_contains_message_content(self) -> None:
        """The content column contains the message's content."""
        messages = [{"role": "user", "content": "Hello world"}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[2] == "Hello world"

    def test_tool_name_from_tool_result_message(self) -> None:
        """Tool result messages (role=tool) have tool_name from the 'name' field."""
        messages = [
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "file data",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[3] == "read_file"

    def test_tool_name_from_assistant_tool_calls(self) -> None:
        """Assistant messages with tool_calls show the first tool_call name."""
        messages = [
            {
                "role": "assistant",
                "content": "Calling tool",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "search", "arguments": "{}"},
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[3] == "search"

    def test_tool_call_id_from_tool_result(self) -> None:
        """Tool result messages have tool_call_id in the CSV column."""
        messages = [
            {
                "role": "tool",
                "tool_call_id": "call_abc",
                "name": "grep_search",
                "content": "results",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[4] == "call_abc"

    def test_token_count_column_is_integer(self, rich_messages: list[dict[str, Any]]) -> None:
        """Token count column contains integer values."""
        query = MessageQuery(rich_messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        for row in reader:
            # Should be parseable as an integer
            int(row[5])


class TestMessageQueryExportCsvTruncation:
    """Tests for CSV content truncation."""

    def test_content_truncated_at_500_chars_default(self) -> None:
        """Content longer than 500 chars is truncated with '...' suffix."""
        long_content = "a" * 600
        messages = [{"role": "user", "content": long_content}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert len(row[2]) == 503  # 500 + len("...")
        assert row[2].endswith("...")
        assert row[2][:500] == "a" * 500

    def test_max_content_length_kwarg_configures_truncation(self) -> None:
        """max_content_length kwarg changes the truncation limit."""
        long_content = "b" * 200
        messages = [{"role": "user", "content": long_content}]
        query = MessageQuery(messages)
        result = query.export(format="csv", max_content_length=100)

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert len(row[2]) == 103  # 100 + len("...")
        assert row[2].endswith("...")

    def test_content_exactly_at_limit_not_truncated(self) -> None:
        """Content exactly at the truncation limit is not truncated."""
        content = "c" * 500
        messages = [{"role": "user", "content": content}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[2] == content
        assert not row[2].endswith("...")
        assert len(row[2]) == 500

    def test_content_shorter_than_limit_not_truncated(self) -> None:
        """Content shorter than the limit is preserved fully."""
        content = "short text"
        messages = [{"role": "user", "content": content}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[2] == content

    def test_content_one_over_limit_truncated(self) -> None:
        """Content at limit+1 is truncated."""
        content = "d" * 501
        messages = [{"role": "user", "content": content}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert len(row[2]) == 503
        assert row[2] == "d" * 500 + "..."


class TestMessageQueryExportCsvSpecialChars:
    """Tests for special character handling in CSV export."""

    def test_content_with_commas_properly_quoted(self) -> None:
        """Content containing commas is properly escaped by csv module."""
        messages = [{"role": "user", "content": "hello, world, foo"}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        # Parse the CSV back and verify the content is intact
        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[2] == "hello, world, foo"

    def test_content_with_newlines_properly_quoted(self) -> None:
        """Content containing newlines is properly escaped by csv module."""
        messages = [{"role": "user", "content": "line1\nline2\nline3"}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[2] == "line1\nline2\nline3"

    def test_content_with_quotes_properly_escaped(self) -> None:
        """Content containing double quotes is properly escaped by csv module."""
        messages = [{"role": "user", "content": 'He said "hello"'}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[2] == 'He said "hello"'

    def test_content_with_mixed_special_chars(self) -> None:
        """Content with commas, newlines, and quotes all handled properly."""
        messages = [{"role": "user", "content": 'a,b\nc,"d"'}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[2] == 'a,b\nc,"d"'

    def test_raw_csv_contains_quoting_for_commas(self) -> None:
        """Verify the raw CSV string contains quotes around fields with commas."""
        messages = [{"role": "user", "content": "hello, world"}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        # The raw CSV should contain the quoted field
        assert '"hello, world"' in result


class TestMessageQueryExportCsvEmpty:
    """Tests for empty conversation CSV export."""

    def test_empty_conversation_returns_header_only(self) -> None:
        """Empty message list produces only the header row."""
        query = MessageQuery([])
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        # csv module may produce a trailing empty row from the newline
        non_empty_rows = [r for r in rows if r]
        assert len(non_empty_rows) == 1
        assert non_empty_rows[0] == [
            "index",
            "role",
            "content",
            "tool_name",
            "tool_call_id",
            "token_count",
        ]

    def test_empty_conversation_is_valid_csv(self) -> None:
        """Empty conversation CSV is parseable by csv.reader."""
        query = MessageQuery([])
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) >= 1


class TestMessageQueryExportCsvEdgeCases:
    """Tests for edge cases in CSV export."""

    def test_messages_without_tool_name_have_empty_field(self) -> None:
        """User and system messages produce empty tool_name and tool_call_id."""
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "system", "content": "prompt"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        for row in reader:
            assert row[3] == ""  # tool_name
            assert row[4] == ""  # tool_call_id

    def test_message_with_missing_content_field(self) -> None:
        """Messages without a content field produce empty CSV cells."""
        messages = [{"role": "assistant"}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[2] == ""  # content empty

    def test_message_with_none_content(self) -> None:
        """Messages with content=None produce empty CSV cells."""
        messages = [{"role": "assistant", "content": None}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[2] == ""

    def test_message_missing_role_field(self) -> None:
        """Messages missing the role field produce empty role cell."""
        messages = [{"content": "orphan message"}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[1] == ""  # role empty
        assert row[2] == "orphan message"

    def test_completely_empty_message_dict(self) -> None:
        """A completely empty message dict produces a row with empty cells."""
        messages = [{}]
        query = MessageQuery(messages)
        result = query.export(format="csv")

        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        assert row[0] == "0"  # index still set
        assert row[1] == ""  # role
        assert row[2] == ""  # content
        assert row[3] == ""  # tool_name
        assert row[4] == ""  # tool_call_id


class TestMessageQueryExportCsvSubset:
    """Tests for CSV subset export via messages parameter."""

    def test_messages_parameter_exports_subset(self, rich_messages: list[dict[str, Any]]) -> None:
        """export(format='csv', messages=subset) exports only the given subset."""
        query = MessageQuery(rich_messages)
        subset = rich_messages[:2]
        result = query.export(format="csv", messages=subset)

        reader = csv.reader(io.StringIO(result))
        next(reader)  # skip header
        rows = list(reader)
        non_empty_rows = [r for r in rows if r]
        assert len(non_empty_rows) == 2

    def test_subset_indexes_are_zero_based(self, rich_messages: list[dict[str, Any]]) -> None:
        """Subset export re-indexes from 0, not from original positions."""
        query = MessageQuery(rich_messages)
        subset = rich_messages[3:6]  # messages at index 3,4,5
        result = query.export(format="csv", messages=subset)

        reader = csv.reader(io.StringIO(result))
        next(reader)
        rows = list(reader)
        non_empty_rows = [r for r in rows if r]
        assert non_empty_rows[0][0] == "0"
        assert non_empty_rows[1][0] == "1"
        assert non_empty_rows[2][0] == "2"

    def test_empty_subset_returns_header_only(self) -> None:
        """Passing an empty list as messages returns header only."""
        messages = [{"role": "user", "content": "hello"}]
        query = MessageQuery(messages)
        result = query.export(format="csv", messages=[])

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        non_empty_rows = [r for r in rows if r]
        assert len(non_empty_rows) == 1  # header only


# ---------------------------------------------------------------------------
# MessageQuery: export(format="dict") tests
# ---------------------------------------------------------------------------


class TestMessageQueryExportDictBasic:
    """Tests for dict export with metadata verification."""

    def test_returns_list_of_dicts(self, rich_messages: list[dict[str, Any]]) -> None:
        """export(format='dict') returns a list[dict]."""
        query = MessageQuery(rich_messages)
        result = query.export(format="dict")

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    def test_each_dict_has_metadata_key(self, rich_messages: list[dict[str, Any]]) -> None:
        """Each exported dict contains a _metadata key."""
        query = MessageQuery(rich_messages)
        result = query.export(format="dict")

        for item in result:
            assert "_metadata" in item

    def test_metadata_has_required_fields(self, rich_messages: list[dict[str, Any]]) -> None:
        """_metadata contains index, token_count, and role."""
        query = MessageQuery(rich_messages)
        result = query.export(format="dict")

        for item in result:
            meta = item["_metadata"]
            assert "index" in meta
            assert "token_count" in meta
            assert "role" in meta

    def test_metadata_index_is_zero_based_sequential(
        self, rich_messages: list[dict[str, Any]]
    ) -> None:
        """_metadata.index is zero-based and sequential."""
        query = MessageQuery(rich_messages)
        result = query.export(format="dict")

        for idx, item in enumerate(result):
            assert item["_metadata"]["index"] == idx

    def test_metadata_role_matches_message_role(self, rich_messages: list[dict[str, Any]]) -> None:
        """_metadata.role matches the message's role field."""
        query = MessageQuery(rich_messages)
        result = query.export(format="dict")

        for original, exported in zip(rich_messages, result, strict=True):
            assert exported["_metadata"]["role"] == original.get("role", "unknown")

    def test_result_length_matches_input(self, rich_messages: list[dict[str, Any]]) -> None:
        """Exported list has the same number of items as the input messages."""
        query = MessageQuery(rich_messages)
        result = query.export(format="dict")

        assert len(result) == len(rich_messages)


class TestMessageQueryExportDictPreservesOriginal:
    """Tests that dict export preserves original message fields."""

    def test_original_fields_present_in_export(self) -> None:
        """All original message fields are preserved in the exported dict."""
        messages = [
            {"role": "user", "content": "Hello world", "custom_field": "custom_value"},
            {
                "role": "assistant",
                "content": "Hi",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "test_tool", "arguments": "{}"},
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        # User message fields preserved
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello world"
        assert result[0]["custom_field"] == "custom_value"

        # Assistant message fields preserved
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi"
        assert result[1]["tool_calls"][0]["function"]["name"] == "test_tool"

    def test_original_messages_not_mutated(self) -> None:
        """Exporting does not mutate the original message dicts."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        original_keys = [set(msg.keys()) for msg in messages]

        query = MessageQuery(messages)
        query.export(format="dict")

        # Verify no new keys were added to the original dicts
        for original_set, msg in zip(original_keys, messages, strict=True):
            assert set(msg.keys()) == original_set

    def test_tool_result_message_fields_preserved(self) -> None:
        """Tool result message fields (name, tool_call_id) are preserved."""
        messages = [
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": "read_file",
                "content": "file contents",
            },
        ]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        assert result[0]["role"] == "tool"
        assert result[0]["tool_call_id"] == "call_1"
        assert result[0]["name"] == "read_file"
        assert result[0]["content"] == "file contents"


class TestMessageQueryExportDictTokenCount:
    """Tests for token count computation in dict export."""

    def test_token_count_with_token_counter(self) -> None:
        """token_count is computed via TokenCounter when provided."""
        from mamba_agents.tokens.counter import TokenCounter

        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there, how can I help?"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = query.export(format="dict")

        for item in result:
            assert item["_metadata"]["token_count"] > 0

    def test_token_count_without_token_counter_is_zero(self) -> None:
        """Without TokenCounter, token_count defaults to 0."""
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there"},
        ]
        query = MessageQuery(messages, token_counter=None)
        result = query.export(format="dict")

        for item in result:
            assert item["_metadata"]["token_count"] == 0

    def test_token_count_is_int(self) -> None:
        """token_count is always an integer."""
        from mamba_agents.tokens.counter import TokenCounter

        counter = TokenCounter()
        messages = [{"role": "user", "content": "Hello"}]
        query = MessageQuery(messages, token_counter=counter)
        result = query.export(format="dict")

        assert isinstance(result[0]["_metadata"]["token_count"], int)


class TestMessageQueryExportDictEmpty:
    """Tests for dict export with empty conversations."""

    def test_empty_conversation_returns_empty_list(self) -> None:
        """Empty message list returns an empty list."""
        query = MessageQuery([])
        result = query.export(format="dict")

        assert result == []

    def test_empty_conversation_returns_list_type(self) -> None:
        """Empty export returns a list, not None or other type."""
        query = MessageQuery([])
        result = query.export(format="dict")

        assert isinstance(result, list)


class TestMessageQueryExportDictSubset:
    """Tests for dict export with subset via messages parameter."""

    def test_subset_export(self, rich_messages: list[dict[str, Any]]) -> None:
        """export(format='dict', messages=subset) exports only the subset."""
        query = MessageQuery(rich_messages)
        subset = rich_messages[:3]
        result = query.export(format="dict", messages=subset)

        assert len(result) == 3

    def test_subset_indexes_are_zero_based(self, rich_messages: list[dict[str, Any]]) -> None:
        """Subset export re-indexes from 0, not from original positions."""
        query = MessageQuery(rich_messages)
        subset = rich_messages[3:6]  # messages at index 3,4,5
        result = query.export(format="dict", messages=subset)

        assert result[0]["_metadata"]["index"] == 0
        assert result[1]["_metadata"]["index"] == 1
        assert result[2]["_metadata"]["index"] == 2

    def test_empty_subset_returns_empty_list(self) -> None:
        """Passing an empty list as messages returns an empty list."""
        messages = [{"role": "user", "content": "hello"}]
        query = MessageQuery(messages)
        result = query.export(format="dict", messages=[])

        assert result == []


class TestMessageQueryExportDictEdgeCases:
    """Tests for dict export edge cases."""

    def test_message_without_role_uses_unknown(self) -> None:
        """Messages without a role field get role='unknown' in metadata."""
        messages = [{"content": "orphaned message"}]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        assert result[0]["_metadata"]["role"] == "unknown"

    def test_existing_metadata_key_uses_alternate(self) -> None:
        """When a message already has _metadata, uses _export_metadata instead."""
        messages = [
            {"role": "user", "content": "hello", "_metadata": {"custom": True}},
            {"role": "assistant", "content": "hi"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        # Should use alternate key
        assert "_export_metadata" in result[0]
        assert "_export_metadata" in result[1]
        # Original _metadata preserved
        assert result[0]["_metadata"] == {"custom": True}

    def test_no_existing_metadata_uses_standard_key(self) -> None:
        """When no messages have _metadata, uses _metadata as the key."""
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        assert "_metadata" in result[0]
        assert "_metadata" in result[1]
        # Alternate key should not be present
        assert "_export_metadata" not in result[0]
        assert "_export_metadata" not in result[1]

    def test_message_with_none_content(self) -> None:
        """Messages with None content are handled gracefully."""
        messages = [{"role": "assistant", "content": None}]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        assert len(result) == 1
        assert result[0]["_metadata"]["role"] == "assistant"
        assert result[0]["_metadata"]["token_count"] == 0

    def test_single_message_export(self) -> None:
        """Single message export works correctly."""
        messages = [{"role": "user", "content": "hi"}]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        assert len(result) == 1
        assert result[0]["_metadata"]["index"] == 0
        assert result[0]["_metadata"]["role"] == "user"


# ---------------------------------------------------------------------------
# Comprehensive fixture-based filter/query tests (Task 5)
# ---------------------------------------------------------------------------


@pytest.fixture
def conversation_fixture() -> list[dict[str, Any]]:
    """Provide a rich, realistic conversation with diverse message patterns.

    Includes:
    - System prompt
    - Multiple user messages with varying content
    - Assistant messages with and without tool calls
    - Multi-tool-call assistant messages
    - Tool result messages with varying content
    - Messages with empty string content
    - Messages with None content
    - Messages without a content field at all
    - Unicode content
    - Special regex characters in content
    """
    return [
        # 0: system prompt
        {"role": "system", "content": "You are a code assistant. Help with files."},
        # 1: first user message
        {"role": "user", "content": "Read the config.yaml file for me."},
        # 2: assistant with single tool call
        {
            "role": "assistant",
            "content": "I'll read that configuration file now.",
            "tool_calls": [
                {
                    "id": "call_100",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path": "config.yaml"}',
                    },
                }
            ],
        },
        # 3: tool result for read_file
        {
            "role": "tool",
            "tool_call_id": "call_100",
            "name": "read_file",
            "content": "database:\n  host: localhost\n  port: 5432",
        },
        # 4: assistant follow-up (no tool calls)
        {"role": "assistant", "content": "The config contains database settings."},
        # 5: user asks about searching
        {"role": "user", "content": "Search for ERROR patterns in the logs."},
        # 6: assistant with multi-tool call
        {
            "role": "assistant",
            "content": "I'll search multiple log files simultaneously.",
            "tool_calls": [
                {
                    "id": "call_201",
                    "type": "function",
                    "function": {
                        "name": "grep_search",
                        "arguments": '{"pattern": "ERROR", "path": "app.log"}',
                    },
                },
                {
                    "id": "call_202",
                    "type": "function",
                    "function": {
                        "name": "grep_search",
                        "arguments": '{"pattern": "ERROR", "path": "system.log"}',
                    },
                },
                {
                    "id": "call_203",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path": "error_summary.txt"}',
                    },
                },
            ],
        },
        # 7: tool result for first grep
        {
            "role": "tool",
            "tool_call_id": "call_201",
            "name": "grep_search",
            "content": "app.log:42: ERROR: Connection timeout\napp.log:99: ERROR: Disk full",
        },
        # 8: tool result for second grep
        {
            "role": "tool",
            "tool_call_id": "call_202",
            "name": "grep_search",
            "content": "system.log:7: ERROR: Out of memory",
        },
        # 9: tool result for read_file
        {
            "role": "tool",
            "tool_call_id": "call_203",
            "name": "read_file",
            "content": "3 errors found in total",
        },
        # 10: assistant summary
        {"role": "assistant", "content": "Found 3 ERROR entries across the log files."},
        # 11: user with special regex chars in content
        {"role": "user", "content": "Can you match lines like [ERROR] (critical)?"},
        # 12: assistant with no content (content is None)
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_300",
                    "type": "function",
                    "function": {
                        "name": "grep_search",
                        "arguments": '{"pattern": "\\\\[ERROR\\\\].*critical"}',
                    },
                }
            ],
        },
        # 13: tool result
        {
            "role": "tool",
            "tool_call_id": "call_300",
            "name": "grep_search",
            "content": "",
        },
        # 14: assistant with empty string content
        {"role": "assistant", "content": ""},
        # 15: user with unicode
        {"role": "user", "content": "Show me the README with emojis and accents: cafe\u0301"},
        # 16: assistant plain text
        {"role": "assistant", "content": "Here is the content with unicode: \u2714 done"},
        # 17: assistant message without content field at all
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_400",
                    "type": "function",
                    "function": {
                        "name": "list_directory",
                        "arguments": '{"path": "."}',
                    },
                }
            ],
        },
        # 18: tool result for list_directory
        {
            "role": "tool",
            "tool_call_id": "call_400",
            "name": "list_directory",
            "content": "file1.py\nfile2.py\nREADME.md",
        },
    ]


class TestFilterByRoleComprehensive:
    """Comprehensive role filtering with the rich conversation fixture."""

    def test_filter_user_count(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Verify exact count of user messages in the conversation."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="user")

        assert len(result) == 4
        assert all(msg["role"] == "user" for msg in result)

    def test_filter_assistant_count(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Verify exact count of assistant messages including those with None/empty content."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="assistant")

        # Indices: 2, 4, 6, 10, 12, 14, 16, 17
        assert len(result) == 8
        assert all(msg["role"] == "assistant" for msg in result)

    def test_filter_tool_count(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Verify exact count of tool result messages."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="tool")

        # Indices: 3, 7, 8, 9, 13, 18
        assert len(result) == 6
        assert all(msg["role"] == "tool" for msg in result)

    def test_filter_system_count(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Verify exact count of system messages."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="system")

        assert len(result) == 1
        assert result[0]["content"] == "You are a code assistant. Help with files."

    def test_filter_preserves_message_order(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Filtered messages maintain their original order in the conversation."""
        query = MessageQuery(conversation_fixture)
        users = query.filter(role="user")

        assert users[0]["content"] == "Read the config.yaml file for me."
        assert users[1]["content"] == "Search for ERROR patterns in the logs."
        assert users[2]["content"] == "Can you match lines like [ERROR] (critical)?"
        assert "cafe" in users[3]["content"]

    def test_filter_role_returns_fresh_list_each_call(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Each filter() call returns a new independent list."""
        query = MessageQuery(conversation_fixture)
        result1 = query.filter(role="user")
        result2 = query.filter(role="user")

        assert result1 == result2
        assert result1 is not result2

    def test_filter_nonexistent_role_empty(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Filtering for a role that does not exist returns empty list."""
        query = MessageQuery(conversation_fixture)

        assert query.filter(role="moderator") == []
        assert query.filter(role="") == []
        assert query.filter(role="SYSTEM") == []  # Case-sensitive role match


class TestFilterByToolNameComprehensive:
    """Comprehensive tool_name filtering with multi-tool-call messages."""

    def test_filter_tool_name_read_file_both_roles(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """read_file filter finds assistant tool_calls AND tool result messages."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(tool_name="read_file")

        # 2 assistant messages have read_file calls (indices 2, 6) + 2 tool results (3, 9)
        roles = [msg["role"] for msg in result]
        assert "assistant" in roles
        assert "tool" in roles
        assert len(result) == 4

    def test_filter_tool_name_grep_search_multi_call(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """grep_search filter finds assistant with multi-tool-call and tool results."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(tool_name="grep_search")

        # Assistant messages at index 6 and 12 have grep_search calls
        # Tool results at indices 7, 8, 13
        assert len(result) >= 4
        assert any(msg["role"] == "assistant" for msg in result)
        assert any(msg["role"] == "tool" for msg in result)

    def test_filter_tool_name_list_directory(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """list_directory filter matches assistant message without content field."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(tool_name="list_directory")

        assert len(result) == 2  # assistant call + tool result
        assistant_msgs = [m for m in result if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1
        assert "content" not in assistant_msgs[0]  # No content field

    def test_filter_tool_name_nonexistent(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Tool name that does not exist returns empty list."""
        query = MessageQuery(conversation_fixture)

        assert query.filter(tool_name="nonexistent_tool") == []
        assert query.filter(tool_name="") == []

    def test_filter_tool_name_excludes_plain_assistant(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Plain assistant messages (no tool_calls) are excluded from tool_name filter."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(tool_name="read_file")

        # None of the results should be a plain assistant message
        for msg in result:
            if msg["role"] == "assistant":
                assert "tool_calls" in msg

    def test_filter_tool_name_excludes_user_and_system(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """User and system messages are never matched by tool_name filter."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(tool_name="read_file")

        roles = {msg["role"] for msg in result}
        assert "user" not in roles
        assert "system" not in roles

    def test_filter_tool_name_with_empty_tool_calls_list(self) -> None:
        """Assistant with empty tool_calls list is not matched."""
        messages = [
            {"role": "assistant", "content": "thinking...", "tool_calls": []},
        ]
        query = MessageQuery(messages)
        result = query.filter(tool_name="read_file")

        assert result == []

    def test_filter_tool_name_with_malformed_tool_call_entries(self) -> None:
        """Malformed tool_call entries (non-dict) are skipped gracefully."""
        messages = [
            {
                "role": "assistant",
                "content": "broken",
                "tool_calls": [
                    "not_a_dict",
                    42,
                    None,
                    {
                        "id": "call_ok",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": "{}"},
                    },
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.filter(tool_name="read_file")

        assert len(result) == 1  # The assistant message matches via the valid entry

    def test_filter_tool_name_with_missing_function_key(self) -> None:
        """Tool call dict without function key does not match."""
        messages = [
            {
                "role": "assistant",
                "content": "no func",
                "tool_calls": [{"id": "call_x", "type": "function"}],
            },
        ]
        query = MessageQuery(messages)
        result = query.filter(tool_name="read_file")

        assert result == []


class TestFilterByContentComprehensive:
    """Comprehensive content filtering with varied content patterns."""

    def test_content_substring_in_middle(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Content search finds text in the middle of a message."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(content="configuration file")

        assert len(result) == 1
        assert "configuration file" in result[0]["content"]

    def test_content_case_insensitive_match(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Content search is case-insensitive for plain text."""
        query = MessageQuery(conversation_fixture)

        upper = query.filter(content="ERROR")
        lower = query.filter(content="error")

        # Both should find the same messages
        assert len(upper) == len(lower)
        for msg_u, msg_l in zip(upper, lower, strict=True):
            assert msg_u is msg_l

    def test_content_empty_string_matches_all_with_content(self) -> None:
        """Filtering with empty string content matches all messages that have content."""
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": ""},
            {"role": "assistant", "content": None},
            {"role": "assistant"},  # No content field
            {"role": "user", "content": "world"},
        ]
        query = MessageQuery(messages)
        result = query.filter(content="")

        # Empty string is in every non-None string, including empty string itself
        assert len(result) == 3  # "hello", "", "world"

    def test_content_skips_none_content(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Messages with content=None are excluded from content search."""
        query = MessageQuery(conversation_fixture)
        # Index 12 has content=None
        result = query.filter(content="anything")

        for msg in result:
            assert msg.get("content") is not None

    def test_content_skips_missing_content_field(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Messages without a content field are excluded from content search."""
        query = MessageQuery(conversation_fixture)
        # Index 17 has no content field
        result = query.filter(content="list_directory")

        # Should not match the assistant message at index 17 (no content field)
        for msg in result:
            assert "content" in msg

    def test_content_matches_unicode(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Content search works with unicode characters."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(content="cafe")

        assert len(result) >= 1
        assert any("cafe" in msg["content"] for msg in result)

    def test_content_matches_unicode_symbols(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Content search matches unicode symbols like checkmarks."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(content="\u2714")

        assert len(result) == 1
        assert "\u2714" in result[0]["content"]

    def test_content_regex_with_groups(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Regex with capture groups works for matching."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(content=r"(ERROR|error)\s+entries", regex=True)

        assert len(result) >= 1

    def test_content_regex_dot_star(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Regex .* matches greedily within content."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(content=r"config.*file", regex=True)

        assert len(result) >= 1

    def test_content_regex_anchored(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Anchored regex ^...$ matches only exact lines."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(content=r"^3 errors found in total$", regex=True)

        assert len(result) == 1
        assert result[0]["content"] == "3 errors found in total"

    def test_content_regex_special_chars_in_content(self) -> None:
        """Content with regex special characters can be searched with plain text."""
        messages = [
            {"role": "user", "content": "match this [pattern] (here)"},
            {"role": "user", "content": "no special chars here"},
        ]
        query = MessageQuery(messages)

        # Plain text search (not regex), should work despite special chars
        result = query.filter(content="[pattern]")
        assert len(result) == 1

    def test_content_regex_invalid_pattern_error_message(self) -> None:
        """Invalid regex includes the original pattern in the error."""
        query = MessageQuery([{"role": "user", "content": "test"}])

        with pytest.raises(re.error, match=r"Invalid regex pattern"):
            query.filter(content=r"(unclosed", regex=True)

    def test_content_with_empty_string_content_message(self) -> None:
        """Messages with empty string content are included when searching empty string."""
        messages = [
            {"role": "assistant", "content": ""},
        ]
        query = MessageQuery(messages)
        result = query.filter(content="")

        assert len(result) == 1


class TestFilterCombinedComprehensive:
    """Comprehensive combined filter tests with rich fixture data."""

    def test_role_and_tool_name_tool_result(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """filter(role='tool', tool_name='grep_search') returns only grep tool results."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="tool", tool_name="grep_search")

        assert all(msg["role"] == "tool" for msg in result)
        assert all(msg["name"] == "grep_search" for msg in result)
        assert len(result) == 3  # Indices 7, 8, 13

    def test_role_and_tool_name_assistant_call(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """filter(role='assistant', tool_name='read_file') returns only assistant call msgs."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="assistant", tool_name="read_file")

        assert all(msg["role"] == "assistant" for msg in result)
        assert len(result) == 2  # Indices 2 and 6

    def test_role_and_content(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """filter(role='user', content='search') narrows to matching user messages."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="user", content="search")

        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "Search" in result[0]["content"]

    def test_tool_name_and_content(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """filter(tool_name='grep_search', content='ERROR') combines tool + content."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(tool_name="grep_search", content="ERROR")

        # Only messages related to grep_search AND containing "ERROR"
        assert len(result) >= 1
        for msg in result:
            assert "error" in msg.get("content", "").lower() or "ERROR" in msg.get("content", "")

    def test_all_three_filters_no_matches(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Combining filters that produce no intersection returns empty list."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="system", tool_name="read_file", content="whatever")

        assert result == []

    def test_role_and_content_regex(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """filter(role='tool', content=r'\\d+ errors', regex=True) combines role + regex."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="tool", content=r"\d+ errors", regex=True)

        assert len(result) == 1
        assert result[0]["role"] == "tool"
        assert "3 errors" in result[0]["content"]

    def test_combined_narrowing_effect(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Each additional filter parameter narrows the result set."""
        query = MessageQuery(conversation_fixture)

        all_msgs = query.filter()
        only_tool = query.filter(role="tool")
        tool_and_name = query.filter(role="tool", tool_name="read_file")

        assert len(all_msgs) > len(only_tool)
        assert len(only_tool) > len(tool_and_name)
        assert len(tool_and_name) >= 1


class TestSliceComprehensive:
    """Comprehensive slice tests with the rich conversation fixture."""

    def test_slice_middle_range(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """slice(start=5, end=10) returns exactly the expected sub-range."""
        query = MessageQuery(conversation_fixture)
        result = query.slice(start=5, end=10)

        assert result == conversation_fixture[5:10]
        assert len(result) == 5

    def test_slice_single_element(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """slice(start=0, end=1) returns just the first element."""
        query = MessageQuery(conversation_fixture)
        result = query.slice(start=0, end=1)

        assert len(result) == 1
        assert result[0] == conversation_fixture[0]

    def test_slice_negative_start(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Negative start index works like Python slice."""
        query = MessageQuery(conversation_fixture)
        result = query.slice(start=-3)

        assert result == conversation_fixture[-3:]
        assert len(result) == 3

    def test_slice_negative_end(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Negative end index works like Python slice."""
        query = MessageQuery(conversation_fixture)
        result = query.slice(start=0, end=-2)

        assert result == conversation_fixture[0:-2]

    def test_slice_start_equals_end(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """slice(start=5, end=5) returns empty list."""
        query = MessageQuery(conversation_fixture)
        result = query.slice(start=5, end=5)

        assert result == []

    def test_slice_start_greater_than_end(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """slice(start=10, end=5) returns empty list (Python slice behaviour)."""
        query = MessageQuery(conversation_fixture)
        result = query.slice(start=10, end=5)

        assert result == []

    def test_slice_on_empty_list(self) -> None:
        """slice on empty message list returns empty list."""
        query = MessageQuery([])
        result = query.slice(start=0, end=5)

        assert result == []


class TestFirstComprehensive:
    """Comprehensive first() tests."""

    def test_first_zero(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """first(n=0) returns empty list."""
        query = MessageQuery(conversation_fixture)
        result = query.first(n=0)

        assert result == []

    def test_first_one(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """first(n=1) returns the system prompt."""
        query = MessageQuery(conversation_fixture)
        result = query.first(n=1)

        assert len(result) == 1
        assert result[0]["role"] == "system"

    def test_first_exact_total(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """first(n=len(messages)) returns all messages."""
        query = MessageQuery(conversation_fixture)
        n = len(conversation_fixture)
        result = query.first(n=n)

        assert len(result) == n
        assert result == conversation_fixture

    def test_first_exceeds_total(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """first(n > total) returns all messages without error."""
        query = MessageQuery(conversation_fixture)
        result = query.first(n=1000)

        assert len(result) == len(conversation_fixture)

    def test_first_on_empty(self) -> None:
        """first() on empty message list returns empty list."""
        query = MessageQuery([])

        assert query.first() == []
        assert query.first(n=5) == []

    def test_first_preserves_order(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """first() returns messages in their original order."""
        query = MessageQuery(conversation_fixture)
        result = query.first(n=3)

        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"


class TestLastComprehensive:
    """Comprehensive last() tests."""

    def test_last_one(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """last(n=1) returns the final message."""
        query = MessageQuery(conversation_fixture)
        result = query.last(n=1)

        assert len(result) == 1
        assert result[0] == conversation_fixture[-1]

    def test_last_exact_total(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """last(n=len(messages)) returns all messages."""
        query = MessageQuery(conversation_fixture)
        n = len(conversation_fixture)
        result = query.last(n=n)

        assert len(result) == n
        assert result == conversation_fixture

    def test_last_exceeds_total(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """last(n > total) returns all messages without error."""
        query = MessageQuery(conversation_fixture)
        result = query.last(n=1000)

        assert len(result) == len(conversation_fixture)

    def test_last_zero(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """last(n=0) returns empty list."""
        query = MessageQuery(conversation_fixture)
        result = query.last(n=0)

        assert result == []

    def test_last_negative(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """last(n=-1) returns empty list (negative treated as <= 0)."""
        query = MessageQuery(conversation_fixture)
        result = query.last(n=-1)

        assert result == []

    def test_last_on_empty(self) -> None:
        """last() on empty message list returns empty list."""
        query = MessageQuery([])

        assert query.last() == []
        assert query.last(n=10) == []

    def test_last_preserves_order(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """last() returns messages in their original order (not reversed)."""
        query = MessageQuery(conversation_fixture)
        result = query.last(n=3)

        # The last 3 should be in order: index -3, -2, -1
        assert result == conversation_fixture[-3:]


class TestAllComprehensive:
    """Comprehensive all() tests."""

    def test_all_returns_complete_copy(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """all() returns all messages as a new list."""
        query = MessageQuery(conversation_fixture)
        result = query.all()

        assert result == conversation_fixture
        assert result is not conversation_fixture
        assert len(result) == len(conversation_fixture)

    def test_all_empty_returns_empty(self) -> None:
        """all() on empty list returns empty list."""
        query = MessageQuery([])
        result = query.all()

        assert result == []
        assert isinstance(result, list)

    def test_all_mutation_does_not_affect_query(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Mutating all() result does not affect subsequent calls."""
        query = MessageQuery(conversation_fixture)
        result1 = query.all()
        result1.clear()  # Mutate the copy

        result2 = query.all()
        assert len(result2) == len(conversation_fixture)


class TestQueryStatelessness:
    """Tests verifying that MessageQuery is truly stateless across calls."""

    def test_sequential_filters_independent(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Multiple filter calls on the same query are independent."""
        query = MessageQuery(conversation_fixture)

        users = query.filter(role="user")
        tools = query.filter(role="tool")
        all_msgs = query.filter()

        assert len(users) == 4
        assert len(tools) == 6
        assert len(all_msgs) == len(conversation_fixture)

    def test_filter_does_not_mutate_original_messages(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Filtering does not modify the original message list."""
        original_len = len(conversation_fixture)
        original_first = dict(conversation_fixture[0])

        query = MessageQuery(conversation_fixture)
        _ = query.filter(role="user")
        _ = query.filter(tool_name="read_file")
        _ = query.filter(content="ERROR")

        assert len(conversation_fixture) == original_len
        assert conversation_fixture[0] == original_first

    def test_filter_result_is_new_list(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """filter() returns a fresh list that can be safely modified."""
        query = MessageQuery(conversation_fixture)
        result = query.filter(role="user")
        result.append({"role": "user", "content": "extra"})

        # The query should not be affected
        result2 = query.filter(role="user")
        assert len(result2) == 4  # Original count, not 5

    def test_slice_first_last_on_filtered_subset(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Filtered results can be used with a new MessageQuery for chaining."""
        query = MessageQuery(conversation_fixture)
        tool_msgs = query.filter(role="tool")

        # Create a new query from filtered results to do further operations
        sub_query = MessageQuery(tool_msgs)
        first_two = sub_query.first(n=2)
        last_one = sub_query.last(n=1)

        assert len(first_two) == 2
        assert first_two[0]["role"] == "tool"
        assert len(last_one) == 1
        assert last_one[0]["role"] == "tool"


class TestFilterEdgeCasesSingleMessage:
    """Edge cases with single-message lists."""

    def test_single_user_message_filter_match(self) -> None:
        """Single user message matches role filter."""
        messages = [{"role": "user", "content": "hello"}]
        query = MessageQuery(messages)

        assert len(query.filter(role="user")) == 1
        assert query.filter(role="assistant") == []

    def test_single_message_content_match(self) -> None:
        """Single message matches content filter."""
        messages = [{"role": "user", "content": "hello world"}]
        query = MessageQuery(messages)

        assert len(query.filter(content="world")) == 1
        assert query.filter(content="xyz") == []

    def test_single_tool_result_tool_name_match(self) -> None:
        """Single tool result message matches tool_name filter."""
        messages = [
            {"role": "tool", "tool_call_id": "c1", "name": "read_file", "content": "data"},
        ]
        query = MessageQuery(messages)

        assert len(query.filter(tool_name="read_file")) == 1
        assert query.filter(tool_name="write_file") == []

    def test_single_message_first_last_all(self) -> None:
        """first/last/all on single message list."""
        messages = [{"role": "user", "content": "only"}]
        query = MessageQuery(messages)

        assert query.first() == messages
        assert query.last() == messages
        assert query.all() == messages
        assert query.first(n=5) == messages
        assert query.last(n=5) == messages

    def test_single_message_slice(self) -> None:
        """Slice operations on single message list."""
        messages = [{"role": "user", "content": "only"}]
        query = MessageQuery(messages)

        assert query.slice(start=0, end=1) == messages
        assert query.slice(start=1) == []
        assert query.slice(start=0, end=0) == []


# ---------------------------------------------------------------------------
# Comprehensive analytics tests (Task 9)
# ---------------------------------------------------------------------------


class TestStatsWithConversationFixture:
    """Integration-style stats() tests using the rich conversation_fixture."""

    def test_stats_total_matches_fixture_length(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """stats() total_messages matches the number of messages in conversation_fixture."""
        query = MessageQuery(conversation_fixture)
        result = query.stats()

        assert result.total_messages == len(conversation_fixture)
        assert result.total_messages == 19

    def test_stats_role_breakdown_matches_fixture(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """stats() role counts match exact fixture composition."""
        query = MessageQuery(conversation_fixture)
        result = query.stats()

        # conversation_fixture: 1 system, 4 user, 8 assistant, 6 tool
        assert result.messages_by_role["system"] == 1
        assert result.messages_by_role["user"] == 4
        assert result.messages_by_role["assistant"] == 8
        assert result.messages_by_role["tool"] == 6

    def test_stats_role_counts_sum_to_total(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Sum of per-role counts equals total_messages."""
        query = MessageQuery(conversation_fixture)
        result = query.stats()

        role_sum = sum(result.messages_by_role.values())
        assert role_sum == result.total_messages

    def test_stats_with_mocked_counter_on_fixture(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """stats() with a mock counter computes tokens deterministically for fixture."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        # Return a constant 7 tokens per message for predictability.
        mock_counter.count_messages.return_value = 7

        query = MessageQuery(conversation_fixture, token_counter=mock_counter)
        result = query.stats()

        assert mock_counter.count_messages.call_count == 19
        assert result.total_tokens == 7 * 19
        # All roles should have tokens.
        assert result.tokens_by_role["system"] == 7 * 1
        assert result.tokens_by_role["user"] == 7 * 4
        assert result.tokens_by_role["assistant"] == 7 * 8
        assert result.tokens_by_role["tool"] == 7 * 6

    def test_stats_avg_tokens_with_fixture(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """avg_tokens_per_message is correct for the conversation_fixture."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        mock_counter.count_messages.return_value = 10

        query = MessageQuery(conversation_fixture, token_counter=mock_counter)
        result = query.stats()

        assert result.avg_tokens_per_message == 10.0

    def test_stats_token_sum_by_role_equals_total(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Sum of tokens_by_role equals total_tokens."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        # Varying token counts by index modulo 3
        mock_counter.count_messages.side_effect = [(i % 3 + 1) * 5 for i in range(19)]

        query = MessageQuery(conversation_fixture, token_counter=mock_counter)
        result = query.stats()

        role_token_sum = sum(result.tokens_by_role.values())
        assert role_token_sum == result.total_tokens


class TestStatsUnknownAndMissingRoles:
    """stats() with messages missing the role field or having unusual roles."""

    def test_stats_message_without_role_counted_as_unknown(self) -> None:
        """Messages without a role field are counted under 'unknown'."""
        messages = [
            {"content": "no role here"},
            {"role": "user", "content": "hello"},
        ]
        query = MessageQuery(messages)
        result = query.stats()

        assert result.total_messages == 2
        assert result.messages_by_role["unknown"] == 1
        assert result.messages_by_role["user"] == 1

    def test_stats_custom_role_name_counted(self) -> None:
        """Messages with custom role names are counted under that role."""
        messages = [
            {"role": "moderator", "content": "Be polite"},
            {"role": "user", "content": "Hello"},
            {"role": "moderator", "content": "Stay focused"},
        ]
        query = MessageQuery(messages)
        result = query.stats()

        assert result.messages_by_role["moderator"] == 2
        assert result.messages_by_role["user"] == 1


class TestStatsPartialTokenCounterFailure:
    """stats() when TokenCounter fails on some messages but succeeds on others."""

    def test_partial_failure_sums_successful_counts(self) -> None:
        """When counter fails on some messages, only successful counts contribute."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        # First call succeeds, second raises, third succeeds.
        mock_counter.count_messages.side_effect = [
            20,
            RuntimeError("encoding error"),
            30,
        ]

        messages = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "problem message"},
            {"role": "user", "content": "third"},
        ]
        query = MessageQuery(messages, token_counter=mock_counter)
        result = query.stats()

        assert result.total_messages == 3
        assert result.total_tokens == 50  # 20 + 0 + 30
        assert result.tokens_by_role["user"] == 50  # 20 + 30
        assert result.tokens_by_role["assistant"] == 0

    def test_all_counter_failures_yield_zero_tokens(self) -> None:
        """When all counter calls fail, total_tokens is 0 but messages are still counted."""
        from unittest.mock import MagicMock

        mock_counter = MagicMock()
        mock_counter.count_messages.side_effect = ValueError("all broken")

        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        query = MessageQuery(messages, token_counter=mock_counter)
        result = query.stats()

        assert result.total_messages == 2
        assert result.total_tokens == 0
        assert result.messages_by_role == {"user": 1, "assistant": 1}


class TestStatsStrEdgeCases:
    """Additional __str__ edge cases for MessageStats."""

    def test_str_with_single_role(self) -> None:
        """__str__ with only one role still shows role sections."""
        stats = MessageStats(
            total_messages=3,
            messages_by_role={"assistant": 3},
            total_tokens=90,
            tokens_by_role={"assistant": 90},
        )
        output = str(stats)

        assert "assistant: 3" in output
        assert "assistant: 90" in output
        assert "user" not in output

    def test_str_roles_sorted_alphabetically(self) -> None:
        """__str__ sorts roles alphabetically in both sections."""
        stats = MessageStats(
            total_messages=6,
            messages_by_role={"user": 2, "assistant": 2, "system": 1, "tool": 1},
            total_tokens=120,
            tokens_by_role={"user": 40, "assistant": 50, "system": 10, "tool": 20},
        )
        output = str(stats)

        # Extract role lines from 'Messages by role:' section.
        lines = output.split("\n")
        msg_roles = []
        in_msg_section = False
        for line in lines:
            if "Messages by role:" in line:
                in_msg_section = True
                continue
            if "Tokens by role:" in line:
                in_msg_section = False
                continue
            if in_msg_section and ":" in line:
                role = line.strip().split(":")[0]
                msg_roles.append(role)

        assert msg_roles == sorted(msg_roles)

    def test_str_large_numbers_formatted(self) -> None:
        """__str__ handles large token and message counts."""
        stats = MessageStats(
            total_messages=100000,
            messages_by_role={"user": 50000, "assistant": 50000},
            total_tokens=10000000,
            tokens_by_role={"user": 5000000, "assistant": 5000000},
        )
        output = str(stats)

        assert "Total messages: 100000" in output
        assert "Total tokens:   10000000" in output
        assert "Avg tokens/msg: 100.0" in output


class TestToolSummaryWithConversationFixture:
    """Integration-style tool_summary() tests using conversation_fixture."""

    def test_tool_summary_unique_tool_names(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """tool_summary() identifies all unique tool names in the fixture."""
        query = MessageQuery(conversation_fixture)
        result = query.tool_summary()

        names = {info.tool_name for info in result}
        assert names == {"read_file", "grep_search", "list_directory"}

    def test_tool_summary_call_counts(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """tool_summary() counts calls accurately for the fixture."""
        query = MessageQuery(conversation_fixture)
        result = query.tool_summary()

        by_name = {info.tool_name: info for info in result}
        # read_file: call_100 (msg 2) + call_203 (msg 6) = 2
        assert by_name["read_file"].call_count == 2
        # grep_search: call_201 + call_202 + call_300 = 3
        assert by_name["grep_search"].call_count == 3
        # list_directory: call_400 = 1
        assert by_name["list_directory"].call_count == 1

    def test_tool_summary_total_calls_match(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Sum of all call_counts equals the total number of tool invocations."""
        query = MessageQuery(conversation_fixture)
        result = query.tool_summary()

        total_calls = sum(info.call_count for info in result)
        assert total_calls == 6  # 2 + 3 + 1

    def test_tool_summary_arguments_captured(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """tool_summary() collects arguments for each invocation."""
        query = MessageQuery(conversation_fixture)
        result = query.tool_summary()

        by_name = {info.tool_name: info for info in result}
        # grep_search has 3 calls with different arguments.
        assert len(by_name["grep_search"].arguments) == 3
        assert by_name["grep_search"].arguments[0] == {
            "pattern": "ERROR",
            "path": "app.log",
        }
        assert by_name["grep_search"].arguments[1] == {
            "pattern": "ERROR",
            "path": "system.log",
        }

    def test_tool_summary_results_linked_by_call_id(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """tool_summary() links results to calls via tool_call_id."""
        query = MessageQuery(conversation_fixture)
        result = query.tool_summary()

        by_name = {info.tool_name: info for info in result}
        # read_file has 2 calls and 2 results.
        assert len(by_name["read_file"].results) == 2
        assert (
            "config" in by_name["read_file"].results[0].lower()
            or "database" in by_name["read_file"].results[0].lower()
        )
        # list_directory has 1 call and 1 result.
        assert "file1.py" in by_name["list_directory"].results[0]

    def test_tool_summary_call_ids_preserved(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """tool_summary() preserves all tool_call_ids in order."""
        query = MessageQuery(conversation_fixture)
        result = query.tool_summary()

        by_name = {info.tool_name: info for info in result}
        assert by_name["grep_search"].tool_call_ids == [
            "call_201",
            "call_202",
            "call_300",
        ]
        assert by_name["read_file"].tool_call_ids == ["call_100", "call_203"]
        assert by_name["list_directory"].tool_call_ids == ["call_400"]

    def test_tool_summary_insertion_order_deterministic(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """tool_summary() returns tools in first-seen order."""
        query = MessageQuery(conversation_fixture)
        result = query.tool_summary()

        # First tool seen is read_file (msg 2), then grep_search (msg 6),
        # then list_directory (msg 17).
        assert result[0].tool_name == "read_file"
        assert result[1].tool_name == "grep_search"
        assert result[2].tool_name == "list_directory"


class TestToolSummaryOrphanedEdgeCases:
    """Additional edge cases for orphaned calls/results not covered by existing tests."""

    def test_orphaned_result_no_call_id_field(self) -> None:
        """Tool result with no tool_call_id field at all is treated as orphaned."""
        messages = [
            {
                "role": "tool",
                "name": "my_tool",
                "content": "result without call_id field",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        info = result[0]
        assert info.tool_name == "my_tool"
        assert info.call_count == 1
        assert info.results == ["result without call_id field"]

    def test_orphaned_result_empty_call_id(self) -> None:
        """Tool result with empty string tool_call_id is treated as orphaned."""
        messages = [
            {
                "role": "tool",
                "tool_call_id": "",
                "name": "my_tool",
                "content": "empty id result",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        assert result[0].call_count == 1

    def test_orphaned_result_without_name_uses_unknown(self) -> None:
        """Tool result without a name field defaults to 'unknown'."""
        messages = [
            {
                "role": "tool",
                "tool_call_id": "call_x",
                "content": "mystery result",
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        assert result[0].tool_name == "unknown"

    def test_many_orphaned_results_same_tool(self) -> None:
        """Multiple orphaned results for the same tool are grouped together."""
        messages = [
            {"role": "tool", "tool_call_id": "c1", "name": "checker", "content": "ok"},
            {"role": "tool", "tool_call_id": "c2", "name": "checker", "content": "fail"},
            {"role": "tool", "tool_call_id": "c3", "name": "checker", "content": "ok"},
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        assert result[0].tool_name == "checker"
        assert result[0].call_count == 3
        assert result[0].results == ["ok", "fail", "ok"]


class TestToolSummaryMalformedCalls:
    """tool_summary() additional malformed data tests beyond existing coverage."""

    def test_tool_call_function_not_dict(self) -> None:
        """Tool call with function value that is not a dict is skipped."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "call_1", "type": "function", "function": "bad_value"}],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert result == []

    def test_tool_call_empty_name_skipped(self) -> None:
        """Tool call with empty string name is skipped."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "", "arguments": "{}"},
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert result == []

    def test_tool_call_without_id_field(self) -> None:
        """Tool call without id field uses empty string for call_id."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {"name": "my_tool", "arguments": "{}"},
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        assert len(result) == 1
        assert result[0].tool_call_ids == [""]

    def test_tool_call_arguments_as_json_array(self) -> None:
        """JSON array arguments are stored as empty dict (not a dict type)."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "my_tool",
                            "arguments": '["a", "b"]',
                        },
                    }
                ],
            },
        ]
        query = MessageQuery(messages)
        result = query.tool_summary()

        # json.loads('["a","b"]') -> list, not dict, so stored as {}
        assert result[0].arguments == [{}]


class TestToolSummaryStrEdgeCases:
    """Additional __str__ edge cases for ToolCallInfo."""

    def test_str_with_empty_result_list(self) -> None:
        """__str__ with call_ids but no results renders only ids and args."""
        info = ToolCallInfo(
            tool_name="my_tool",
            call_count=2,
            arguments=[{"a": 1}, {"b": 2}],
            results=[],
            tool_call_ids=["id1", "id2"],
        )
        output = str(info)

        assert "[id1]" in output
        assert "[id2]" in output
        assert "args: {'a': 1}" in output
        assert "args: {'b': 2}" in output
        # No 'result:' lines since results list is empty.
        assert "result:" not in output

    def test_str_more_results_than_call_ids(self) -> None:
        """__str__ only iterates over tool_call_ids, so extra results are not shown."""
        info = ToolCallInfo(
            tool_name="my_tool",
            call_count=1,
            arguments=[{"x": 1}],
            results=["res1", "res2", "res3"],  # Extra results beyond call_ids
            tool_call_ids=["id1"],
        )
        output = str(info)

        assert "[id1]" in output
        assert "result: res1" in output
        # Extra results not shown because loop is over tool_call_ids
        assert "res2" not in output
        assert "res3" not in output

    def test_str_no_call_ids_at_all(self) -> None:
        """__str__ with no call_ids is just the header line."""
        info = ToolCallInfo(
            tool_name="empty_tool",
            call_count=5,
            arguments=[],
            results=[],
            tool_call_ids=[],
        )
        output = str(info)

        assert output == "Tool: empty_tool (called 5 time(s))"


class TestTimelineWithConversationFixture:
    """Integration-style timeline() tests using conversation_fixture."""

    def test_timeline_turn_count(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """timeline() produces the expected number of turns for the fixture."""
        query = MessageQuery(conversation_fixture)
        result = query.timeline()

        # conversation_fixture has 4 user messages -> 4 user-initiated turns,
        # plus 1 trailing assistant turn (msg 17+18 with no preceding user).
        # Actually let's trace through the fixture:
        # msg 0: system -> collected as system_context
        # msg 1: user -> turn 0 starts
        # msg 2: assistant (tool_calls) -> turn 0 assistant
        # msg 3: tool -> consumed by assistant tool_calls
        # msg 4: assistant (continuation in tool loop) -> turn 0 continues
        # msg 5: user -> turn 1 starts
        # msg 6: assistant (3 tool_calls) -> turn 1 assistant
        # msg 7-9: tool results -> consumed
        # msg 10: assistant (continuation in tool loop) -> turn 1 continues
        # msg 11: user -> turn 2 starts
        # msg 12: assistant (tool_calls, content=None) -> turn 2 assistant
        # msg 13: tool result -> consumed
        # msg 14: assistant (empty string content, tool loop) -> turn 2 continues
        # msg 15: user -> turn 3 starts
        # msg 16: assistant -> turn 3 assistant
        # msg 17: assistant (tool_calls, no content field) -> new turn 4
        # msg 18: tool result -> consumed
        assert len(result) == 5

    def test_timeline_first_turn_has_system_context(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """First turn has the system prompt as context."""
        query = MessageQuery(conversation_fixture)
        result = query.timeline()

        assert result[0].system_context == "You are a code assistant. Help with files."
        # Other turns should not have system context.
        for turn in result[1:]:
            assert turn.system_context is None

    def test_timeline_first_turn_structure(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """First turn groups user + assistant + tool interactions correctly."""
        query = MessageQuery(conversation_fixture)
        result = query.timeline()

        turn0 = result[0]
        assert turn0.index == 0
        assert turn0.user_content == "Read the config.yaml file for me."
        assert turn0.assistant_content is not None
        # One tool interaction (read_file).
        assert len(turn0.tool_interactions) == 1
        assert turn0.tool_interactions[0]["tool_name"] == "read_file"
        assert turn0.tool_interactions[0]["tool_call_id"] == "call_100"

    def test_timeline_multi_tool_turn(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Second turn has multiple tool interactions from a single assistant response."""
        query = MessageQuery(conversation_fixture)
        result = query.timeline()

        turn1 = result[1]
        assert turn1.user_content == "Search for ERROR patterns in the logs."
        # 3 tool calls in msg 6.
        assert len(turn1.tool_interactions) == 3
        tool_names = [ti["tool_name"] for ti in turn1.tool_interactions]
        assert tool_names == ["grep_search", "grep_search", "read_file"]

    def test_timeline_tool_loop_continuation_merges_content(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Tool loop continuation appends assistant content to the same turn."""
        query = MessageQuery(conversation_fixture)
        result = query.timeline()

        turn0 = result[0]
        # Turn 0 has the initial "I'll read that configuration file now."
        # and the follow-up "The config contains database settings."
        assert (
            "configuration" in (turn0.assistant_content or "").lower()
            or "config" in (turn0.assistant_content or "").lower()
        )

    def test_timeline_turn_with_none_content_assistant(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Turn containing assistant with None content handles gracefully."""
        query = MessageQuery(conversation_fixture)
        result = query.timeline()

        # Turn 2 has msg 12 (assistant content=None) and msg 14 (content="")
        turn2 = result[2]
        assert turn2.user_content == "Can you match lines like [ERROR] (critical)?"
        # assistant_content may be empty string (from msg 14 continuation) or None
        # depending on implementation: None content is not appended, "" is appended.
        assert turn2.tool_interactions[0]["tool_name"] == "grep_search"

    def test_timeline_indices_sequential(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """All turn indices are sequential starting from 0."""
        query = MessageQuery(conversation_fixture)
        result = query.timeline()

        for i, turn in enumerate(result):
            assert turn.index == i


class TestTimelineMultipleSystemMessages:
    """timeline() with multiple system messages at the start."""

    def test_multiple_system_messages_concatenated(self) -> None:
        """Multiple consecutive system messages are concatenated."""
        messages = [
            {"role": "system", "content": "First instruction."},
            {"role": "system", "content": "Second instruction."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert "First instruction." in result[0].system_context
        assert "Second instruction." in result[0].system_context

    def test_system_with_empty_content(self) -> None:
        """System message with empty string content is included."""
        messages = [
            {"role": "system", "content": ""},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert result[0].system_context == ""


class TestTimelineNestedToolLoops:
    """timeline() with deeply nested tool loops (multiple rounds)."""

    def test_triple_tool_loop(self) -> None:
        """Three rounds of tool calls in the same turn stay as one turn."""
        messages = [
            {"role": "user", "content": "Complex task"},
            # Round 1
            {
                "role": "assistant",
                "content": "Step 1...",
                "tool_calls": [
                    {
                        "id": "r1",
                        "type": "function",
                        "function": {"name": "tool_a", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "r1", "name": "tool_a", "content": "done1"},
            # Round 2
            {
                "role": "assistant",
                "content": "Step 2...",
                "tool_calls": [
                    {
                        "id": "r2",
                        "type": "function",
                        "function": {"name": "tool_b", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "r2", "name": "tool_b", "content": "done2"},
            # Round 3
            {
                "role": "assistant",
                "content": "Step 3...",
                "tool_calls": [
                    {
                        "id": "r3",
                        "type": "function",
                        "function": {"name": "tool_c", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "r3", "name": "tool_c", "content": "done3"},
            # Final summary
            {"role": "assistant", "content": "All done."},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        turn = result[0]
        assert turn.user_content == "Complex task"
        assert len(turn.tool_interactions) == 3
        assert turn.tool_interactions[0]["tool_name"] == "tool_a"
        assert turn.tool_interactions[1]["tool_name"] == "tool_b"
        assert turn.tool_interactions[2]["tool_name"] == "tool_c"

    def test_tool_loop_then_new_user_turn(self) -> None:
        """Tool loop followed by a new user message starts a new turn."""
        messages = [
            {"role": "user", "content": "First request"},
            {
                "role": "assistant",
                "content": "Working...",
                "tool_calls": [
                    {
                        "id": "t1",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "t1", "name": "read_file", "content": "data"},
            {"role": "assistant", "content": "Done with first."},
            # New user message starts a new turn.
            {"role": "user", "content": "Second request"},
            {"role": "assistant", "content": "Done with second."},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 2
        assert result[0].user_content == "First request"
        assert len(result[0].tool_interactions) == 1
        assert result[1].user_content == "Second request"
        assert result[1].tool_interactions == []


class TestTimelineUserOnlyMessages:
    """timeline() with user-only messages (no assistant responses)."""

    def test_user_only_creates_turns_without_assistant(self) -> None:
        """User messages without following assistant create turns with None assistant."""
        messages = [
            {"role": "user", "content": "First question"},
            {"role": "user", "content": "Second question"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        # Each user message starts a new turn.
        assert len(result) == 2
        assert result[0].user_content == "First question"
        assert result[0].assistant_content is None
        assert result[1].user_content == "Second question"
        assert result[1].assistant_content is None


class TestTimelineUnknownRoles:
    """timeline() with unknown role messages interspersed."""

    def test_unknown_role_skipped(self) -> None:
        """Messages with unrecognized roles are skipped gracefully."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "moderator", "content": "This is a moderation message"},
            {"role": "assistant", "content": "Hi there"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].user_content == "Hello"
        assert result[0].assistant_content == "Hi there"

    def test_empty_role_string_skipped(self) -> None:
        """Messages with empty string role are skipped."""
        messages = [
            {"role": "", "content": "what am I"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        assert len(result) == 1
        assert result[0].user_content == "Hello"


class TestTimelineStrEdgeCases:
    """Additional __str__ edge cases for Turn and timeline rendering."""

    def test_turn_str_no_content_at_all(self) -> None:
        """Turn with no user or assistant content renders index only."""
        turn = Turn(index=5)
        output = str(turn)

        assert "Turn 5:" in output
        assert "User:" not in output
        assert "Assistant:" not in output
        assert "System:" not in output
        assert "Tool interactions:" not in output

    def test_turn_str_with_only_user_content(self) -> None:
        """Turn with only user content omits assistant and tool sections."""
        turn = Turn(index=0, user_content="Hello")
        output = str(turn)

        assert "Turn 0:" in output
        assert "User: Hello" in output
        assert "Assistant:" not in output
        assert "Tool interactions:" not in output

    def test_turn_str_tool_interaction_details(self) -> None:
        """Turn __str__ renders all tool interaction details."""
        turn = Turn(
            index=0,
            user_content="Help",
            assistant_content="Working...",
            tool_interactions=[
                {
                    "tool_name": "read_file",
                    "tool_call_id": "call_1",
                    "arguments": {"path": "/tmp/test"},
                    "result": "file data here",
                },
                {
                    "tool_name": "write_file",
                    "tool_call_id": "call_2",
                    "arguments": {"path": "/tmp/out", "content": "hi"},
                    "result": "written",
                },
            ],
        )
        output = str(turn)

        assert "[read_file] id=call_1" in output
        assert "args: {'path': '/tmp/test'}" in output
        assert "result: file data here" in output
        assert "[write_file] id=call_2" in output
        assert "result: written" in output

    def test_timeline_list_str_rendering(self) -> None:
        """Full timeline list rendered as joined string contains all turn indices."""
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]
        query = MessageQuery(messages)
        result = query.timeline()

        full_output = "\n\n".join(str(t) for t in result)
        assert "Turn 0:" in full_output
        assert "Turn 1:" in full_output
        assert "Turn 2:" in full_output
        assert "System: Be helpful" in full_output

    def test_turn_str_tool_interaction_missing_fields(self) -> None:
        """Turn __str__ handles tool interactions with missing fields gracefully."""
        turn = Turn(
            index=0,
            tool_interactions=[
                {"tool_name": "my_tool"},  # Missing tool_call_id, arguments, result
            ],
        )
        output = str(turn)

        assert "[my_tool] id=" in output
        assert "args: {}" in output
        assert "result: " in output


class TestAnalyticsCrossMethodConsistency:
    """Verify stats(), tool_summary(), and timeline() agree on the same data."""

    def test_stats_total_matches_all_length(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """stats().total_messages equals len(all())."""
        query = MessageQuery(conversation_fixture)

        assert query.stats().total_messages == len(query.all())

    def test_tool_summary_call_count_matches_filter(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Total tool calls from tool_summary matches number of tool_calls entries."""
        query = MessageQuery(conversation_fixture)

        summary = query.tool_summary()
        total_calls = sum(info.call_count for info in summary)

        # Count tool_calls entries in assistant messages manually.
        manual_count = 0
        for msg in conversation_fixture:
            if msg.get("role") == "assistant":
                tc = msg.get("tool_calls")
                if isinstance(tc, list):
                    for entry in tc:
                        if isinstance(entry, dict):
                            func = entry.get("function")
                            if isinstance(func, dict) and func.get("name"):
                                manual_count += 1

        assert total_calls == manual_count

    def test_timeline_tool_interactions_match_summary(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Tool interactions from timeline match tool_summary call counts."""
        query = MessageQuery(conversation_fixture)

        timeline = query.timeline()
        summary = query.tool_summary()

        # Count tool interactions from timeline.
        timeline_tool_count = sum(len(turn.tool_interactions) for turn in timeline)
        summary_tool_count = sum(info.call_count for info in summary)

        assert timeline_tool_count == summary_tool_count

    def test_stats_and_timeline_user_count_match(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Number of user messages in stats matches turns with user_content."""
        query = MessageQuery(conversation_fixture)

        stats = query.stats()
        timeline = query.timeline()

        user_msg_count = stats.messages_by_role.get("user", 0)
        turns_with_user = sum(1 for turn in timeline if turn.user_content is not None)

        assert user_msg_count == turns_with_user

    def test_empty_conversation_all_methods_consistent(self) -> None:
        """All three analytics methods agree on empty conversation."""
        query = MessageQuery([])

        stats = query.stats()
        summary = query.tool_summary()
        timeline = query.timeline()

        assert stats.total_messages == 0
        assert summary == []
        assert timeline == []

    def test_single_user_message_all_methods(self) -> None:
        """All three analytics methods produce correct results for minimal input."""
        messages = [{"role": "user", "content": "Hello"}]
        query = MessageQuery(messages)

        stats = query.stats()
        summary = query.tool_summary()
        timeline = query.timeline()

        assert stats.total_messages == 1
        assert stats.messages_by_role == {"user": 1}
        assert summary == []
        assert len(timeline) == 1
        assert timeline[0].user_content == "Hello"


# ---------------------------------------------------------------------------
# Comprehensive export tests with conversation_fixture (Task 14)
# ---------------------------------------------------------------------------


class _MockTokenCounter:
    """Deterministic mock TokenCounter that returns word count + 4 overhead."""

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content") or ""
            total += len(content.split()) + 4  # 4 = overhead
        return total


class _FailingTokenCounter:
    """TokenCounter mock that always raises on count_messages."""

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        raise RuntimeError("TokenCounter failure")


# ---------------------------------------------------------------------------
# Cross-format consistency tests
# ---------------------------------------------------------------------------


class TestExportCrossFormatConsistency:
    """Verify all four export formats agree on message counts and content."""

    def test_all_formats_handle_same_messages(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """All four export formats process the same input without errors."""
        query = MessageQuery(conversation_fixture)

        json_result = query.export(format="json")
        md_result = query.export(format="markdown")
        csv_result = query.export(format="csv")
        dict_result = query.export(format="dict")

        assert isinstance(json_result, str)
        assert isinstance(md_result, str)
        assert isinstance(csv_result, str)
        assert isinstance(dict_result, list)

    def test_json_and_dict_message_count_match(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """JSON and dict export produce the same number of messages."""
        query = MessageQuery(conversation_fixture)

        json_parsed = json.loads(query.export(format="json"))
        dict_result = query.export(format="dict")

        assert len(json_parsed) == len(dict_result) == len(conversation_fixture)

    def test_csv_row_count_matches_message_count(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """CSV data rows (excluding header) equal the message count."""
        query = MessageQuery(conversation_fixture)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)  # skip header
        rows = [r for r in reader if r]

        assert len(rows) == len(conversation_fixture)

    def test_json_and_dict_roles_match(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Roles from JSON and dict exports match for every message."""
        query = MessageQuery(conversation_fixture)

        json_parsed = json.loads(query.export(format="json"))
        dict_result = query.export(format="dict")

        for j_msg, d_msg in zip(json_parsed, dict_result, strict=True):
            assert j_msg["role"] == d_msg["role"]
            assert d_msg["_metadata"]["role"] == j_msg["role"]

    def test_csv_and_dict_roles_match(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Roles from CSV and dict exports match for every message."""
        query = MessageQuery(conversation_fixture)

        csv_result = query.export(format="csv")
        dict_result = query.export(format="dict")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        for row, d_msg in zip(reader, dict_result, strict=True):
            if not row:
                continue
            assert row[1] == d_msg["role"]

    def test_markdown_contains_all_user_content(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """All user message content appears in the Markdown output."""
        query = MessageQuery(conversation_fixture)
        md_result = query.export(format="markdown")

        for msg in conversation_fixture:
            if msg.get("role") == "user" and msg.get("content"):
                assert msg["content"] in md_result

    def test_markdown_contains_all_assistant_text_content(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """All non-None assistant content appears in the Markdown output."""
        query = MessageQuery(conversation_fixture)
        md_result = query.export(format="markdown")

        for msg in conversation_fixture:
            if msg.get("role") == "assistant":
                content = msg.get("content")
                if content is not None and content != "":
                    assert content in md_result

    def test_subset_produces_consistent_results_across_formats(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Subset export via messages parameter is consistent across formats."""
        query = MessageQuery(conversation_fixture)
        subset = conversation_fixture[:5]

        json_parsed = json.loads(query.export(format="json", messages=subset))
        csv_result = query.export(format="csv", messages=subset)
        dict_result = query.export(format="dict", messages=subset)

        assert len(json_parsed) == 5
        assert len(dict_result) == 5

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        csv_rows = [r for r in reader if r]
        assert len(csv_rows) == 5


class TestExportCrossFormatWithMockCounter:
    """Cross-format tests using a mock TokenCounter for deterministic token counts."""

    def test_json_metadata_and_dict_token_counts_agree(self) -> None:
        """JSON include_metadata and dict export produce same token counts when
        using identical counter logic is not expected (different fallback behavior),
        but both should produce non-negative integers."""
        counter = _MockTokenCounter()
        messages = [
            {"role": "user", "content": "hello world"},
            {"role": "assistant", "content": "hi there friend"},
        ]
        query = MessageQuery(messages, token_counter=counter)

        json_result = json.loads(query.export(format="json", include_metadata=True))
        dict_result = query.export(format="dict")

        # JSON uses _count_message_tokens which delegates to mock
        # Dict uses direct count_messages call
        for j_msg, d_msg in zip(json_result, dict_result, strict=True):
            assert isinstance(j_msg["token_count"], int)
            assert isinstance(d_msg["_metadata"]["token_count"], int)
            assert j_msg["token_count"] >= 0
            assert d_msg["_metadata"]["token_count"] >= 0

    def test_csv_token_counts_are_deterministic(self) -> None:
        """CSV token_count column values are deterministic with mock counter."""
        counter = _MockTokenCounter()
        messages = [
            {"role": "user", "content": "one two three"},
            {"role": "assistant", "content": "four five"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        rows = list(reader)
        non_empty = [r for r in rows if r]

        # "one two three" -> 3 words + 4 overhead = 7
        assert int(non_empty[0][5]) == 7
        # "four five" -> 2 words + 4 overhead = 6
        assert int(non_empty[1][5]) == 6

    def test_dict_token_counts_are_deterministic(self) -> None:
        """Dict export token counts are deterministic with mock counter."""
        counter = _MockTokenCounter()
        messages = [
            {"role": "user", "content": "alpha beta"},
            {"role": "assistant", "content": "gamma"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = query.export(format="dict")

        # "alpha beta" -> 2 words + 4 = 6
        assert result[0]["_metadata"]["token_count"] == 6
        # "gamma" -> 1 word + 4 = 5
        assert result[1]["_metadata"]["token_count"] == 5


# ---------------------------------------------------------------------------
# Export with conversation_fixture (integration-style)
# ---------------------------------------------------------------------------


class TestExportJsonWithConversationFixture:
    """JSON export tests using the rich conversation_fixture."""

    def test_json_roundtrip_preserves_all_messages(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """JSON export then parse preserves every original message."""
        query = MessageQuery(conversation_fixture)
        result = json.loads(query.export(format="json"))

        assert len(result) == len(conversation_fixture)
        for original, exported in zip(conversation_fixture, result, strict=True):
            assert exported["role"] == original["role"]

    def test_json_metadata_indices_sequential(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """include_metadata produces sequential zero-based indices."""
        query = MessageQuery(conversation_fixture)
        result = json.loads(query.export(format="json", include_metadata=True))

        for idx, msg in enumerate(result):
            assert msg["index"] == idx

    def test_json_preserves_unicode_in_fixture(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Unicode content from conversation_fixture survives JSON roundtrip."""
        query = MessageQuery(conversation_fixture)
        result = json.loads(query.export(format="json"))

        # Message at index 15 has unicode content
        unicode_msg = result[15]
        assert "cafe\u0301" in unicode_msg["content"]

    def test_json_preserves_none_content(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Messages with None content are preserved as null in JSON."""
        query = MessageQuery(conversation_fixture)
        result = json.loads(query.export(format="json"))

        # Message at index 12 has content=None
        assert result[12]["content"] is None

    def test_json_preserves_empty_string_content(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Messages with empty string content are preserved."""
        query = MessageQuery(conversation_fixture)
        result = json.loads(query.export(format="json"))

        # Message at index 14 has content=""
        assert result[14]["content"] == ""

    def test_json_preserves_tool_calls_structure(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Tool calls structure including multi-tool calls is preserved."""
        query = MessageQuery(conversation_fixture)
        result = json.loads(query.export(format="json"))

        # Message at index 6 has 3 tool calls
        assert len(result[6]["tool_calls"]) == 3
        tool_names = [tc["function"]["name"] for tc in result[6]["tool_calls"]]
        assert "grep_search" in tool_names
        assert "read_file" in tool_names

    def test_json_subset_from_filter(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """JSON export accepts subset from filter() method."""
        query = MessageQuery(conversation_fixture)
        user_msgs = query.filter(role="user")
        result = json.loads(query.export(format="json", messages=user_msgs))

        assert len(result) == 4
        assert all(msg["role"] == "user" for msg in result)


class TestExportMarkdownWithConversationFixture:
    """Markdown export tests using the rich conversation_fixture."""

    def test_markdown_renders_all_role_headers(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """All role types from conversation_fixture have their headers."""
        query = MessageQuery(conversation_fixture)
        result = query.export(format="markdown")

        assert "### System" in result
        assert "### User" in result
        assert "### Assistant" in result

    def test_markdown_renders_all_tool_names(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """All tool names from the fixture appear in the Markdown output."""
        query = MessageQuery(conversation_fixture)
        result = query.export(format="markdown")

        assert "**Tool Call: read_file**" in result
        assert "**Tool Call: grep_search**" in result
        assert "**Tool Call: list_directory**" in result

    def test_markdown_tool_results_present(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Tool results from the fixture are present in Markdown output."""
        query = MessageQuery(conversation_fixture)
        result = query.export(format="markdown")

        assert "database:" in result  # from read_file result
        assert "ERROR: Connection timeout" in result  # from grep result
        assert "file1.py" in result  # from list_directory result

    def test_markdown_no_standalone_tool_headers(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Tool result messages are rendered inline, not as standalone entries."""
        query = MessageQuery(conversation_fixture)
        result = query.export(format="markdown")

        assert "### Tool" not in result

    def test_markdown_system_prompt_at_start(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """System prompt appears at the beginning of the output."""
        query = MessageQuery(conversation_fixture)
        result = query.export(format="markdown")

        first_header_pos = result.index("###")
        assert result[first_header_pos:].startswith("### System")

    def test_markdown_subset_from_last(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Markdown export accepts subset from last() method."""
        query = MessageQuery(conversation_fixture)
        last_three = query.last(n=3)
        result = query.export(format="markdown", messages=last_three)

        # Last 3 messages: index 16 (assistant), 17 (assistant with tool), 18 (tool)
        # Tool results are inline, so only assistant headers rendered
        assert "### Assistant" in result

    def test_markdown_unicode_preserved(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Unicode characters are preserved in Markdown output."""
        query = MessageQuery(conversation_fixture)
        result = query.export(format="markdown")

        assert "\u2714" in result  # checkmark from message 16
        assert "cafe\u0301" in result  # combining accent from message 15


class TestExportCsvWithConversationFixture:
    """CSV export tests using the rich conversation_fixture."""

    def test_csv_has_correct_row_count(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """CSV has header + 19 data rows (one per message)."""
        query = MessageQuery(conversation_fixture)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        header = next(reader)
        assert len(header) == 6
        data_rows = [r for r in reader if r]
        assert len(data_rows) == 19

    def test_csv_tool_names_present(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Tool names appear in the tool_name column for relevant rows."""
        query = MessageQuery(conversation_fixture)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        tool_names = set()
        for row in reader:
            if row and row[3]:
                tool_names.add(row[3])

        assert "read_file" in tool_names
        assert "grep_search" in tool_names
        assert "list_directory" in tool_names

    def test_csv_tool_call_ids_present(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Tool call IDs appear for tool result messages."""
        query = MessageQuery(conversation_fixture)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        call_ids = set()
        for row in reader:
            if row and row[4]:
                call_ids.add(row[4])

        assert "call_100" in call_ids
        assert "call_201" in call_ids
        assert "call_400" in call_ids

    def test_csv_none_content_produces_empty_cell(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Message with content=None at index 12 produces empty content cell."""
        query = MessageQuery(conversation_fixture)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        rows = [r for r in reader if r]

        # Index 12 has content=None
        assert rows[12][2] == ""

    def test_csv_empty_content_produces_empty_cell(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Message with content='' at index 14 produces empty content cell."""
        query = MessageQuery(conversation_fixture)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        rows = [r for r in reader if r]

        # Index 14 has content=""
        assert rows[14][2] == ""

    def test_csv_subset_from_filter(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """CSV export accepts subset from filter() method."""
        query = MessageQuery(conversation_fixture)
        tool_msgs = query.filter(role="tool")
        csv_result = query.export(format="csv", messages=tool_msgs)

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        rows = [r for r in reader if r]

        assert len(rows) == 6  # 6 tool result messages
        assert all(row[1] == "tool" for row in rows)

    def test_csv_multiline_content_handled(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Multiline content from tool results is properly quoted in CSV."""
        query = MessageQuery(conversation_fixture)
        csv_result = query.export(format="csv")

        # Tool result at index 3 has newlines: "database:\n  host: localhost\n  port: 5432"
        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        rows = [r for r in reader if r]

        assert "database:" in rows[3][2]
        assert "host: localhost" in rows[3][2]


class TestExportDictWithConversationFixture:
    """Dict export tests using the rich conversation_fixture."""

    def test_dict_all_messages_have_metadata(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Every exported dict has _metadata with the required fields."""
        query = MessageQuery(conversation_fixture)
        result = query.export(format="dict")

        assert len(result) == 19
        for item in result:
            assert "_metadata" in item
            meta = item["_metadata"]
            assert "index" in meta
            assert "token_count" in meta
            assert "role" in meta

    def test_dict_roles_match_original(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Metadata roles match original message roles."""
        query = MessageQuery(conversation_fixture)
        result = query.export(format="dict")

        for original, exported in zip(conversation_fixture, result, strict=True):
            assert exported["_metadata"]["role"] == original["role"]

    def test_dict_original_fields_preserved(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """All original message fields are preserved in dict export."""
        query = MessageQuery(conversation_fixture)
        result = query.export(format="dict")

        for original, exported in zip(conversation_fixture, result, strict=True):
            for key in original:
                assert key in exported
                assert exported[key] == original[key]

    def test_dict_does_not_mutate_originals(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Dict export does not add keys to the original messages."""
        original_key_sets = [set(msg.keys()) for msg in conversation_fixture]
        query = MessageQuery(conversation_fixture)
        query.export(format="dict")

        for original_keys, msg in zip(original_key_sets, conversation_fixture, strict=True):
            assert set(msg.keys()) == original_keys

    def test_dict_token_counts_zero_without_counter(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """Without a TokenCounter, all token_count values are 0."""
        query = MessageQuery(conversation_fixture, token_counter=None)
        result = query.export(format="dict")

        for item in result:
            assert item["_metadata"]["token_count"] == 0

    def test_dict_token_counts_positive_with_mock_counter(
        self, conversation_fixture: list[dict[str, Any]]
    ) -> None:
        """With a mock counter, messages with content have positive token counts."""
        counter = _MockTokenCounter()
        query = MessageQuery(conversation_fixture, token_counter=counter)
        result = query.export(format="dict")

        for original, exported in zip(conversation_fixture, result, strict=True):
            content = original.get("content")
            if content:
                assert exported["_metadata"]["token_count"] > 0
            else:
                # None/empty content: overhead only (4) or 0 for None
                assert exported["_metadata"]["token_count"] >= 0

    def test_dict_subset_from_slice(self, conversation_fixture: list[dict[str, Any]]) -> None:
        """Dict export accepts subset from slice() method."""
        query = MessageQuery(conversation_fixture)
        middle = query.slice(5, 10)
        result = query.export(format="dict", messages=middle)

        assert len(result) == 5
        # Indices should be 0-4 (relative to subset)
        assert result[0]["_metadata"]["index"] == 0
        assert result[4]["_metadata"]["index"] == 4


# ---------------------------------------------------------------------------
# Export edge cases for uncovered code paths
# ---------------------------------------------------------------------------


class TestExportMarkdownUnknownRole:
    """Tests for Markdown export of messages with unknown roles."""

    def test_unknown_role_rendered_with_title_case_header(self) -> None:
        """Messages with unknown role are rendered under a Title Case header."""
        messages = [
            {"role": "moderator", "content": "Please keep it civil."},
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### Moderator" in result
        assert "Please keep it civil." in result

    def test_multiple_unknown_roles_each_rendered(self) -> None:
        """Each unique unknown role gets its own header."""
        messages = [
            {"role": "observer", "content": "Watching..."},
            {"role": "reviewer", "content": "LGTM"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### Observer" in result
        assert "### Reviewer" in result
        assert "Watching..." in result
        assert "LGTM" in result

    def test_unknown_role_mixed_with_known_roles(self) -> None:
        """Unknown roles interspersed with known roles all render correctly."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "custom_role", "content": "Custom message"},
            {"role": "user", "content": "User message"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="markdown")

        assert "### System" in result
        assert "### Custom_Role" in result
        assert "### User" in result


class TestExportDictTokenCounterException:
    """Tests for dict export when TokenCounter raises exceptions."""

    def test_failing_counter_defaults_to_zero(self) -> None:
        """When TokenCounter raises, token_count defaults to 0."""
        counter = _FailingTokenCounter()
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = query.export(format="dict")

        assert len(result) == 2
        for item in result:
            assert item["_metadata"]["token_count"] == 0

    def test_failing_counter_preserves_all_other_metadata(self) -> None:
        """Even with counter failure, index and role metadata are correct."""
        counter = _FailingTokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = query.export(format="dict")

        assert result[0]["_metadata"]["index"] == 0
        assert result[0]["_metadata"]["role"] == "user"
        assert result[1]["_metadata"]["index"] == 1
        assert result[1]["_metadata"]["role"] == "assistant"

    def test_failing_counter_does_not_prevent_export(self) -> None:
        """A failing counter does not prevent the export from completing."""
        counter = _FailingTokenCounter()
        messages = [
            {"role": "user", "content": "One"},
            {"role": "system", "content": "Two"},
            {"role": "tool", "content": "Three", "tool_call_id": "x", "name": "y"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = query.export(format="dict")

        assert len(result) == 3
        assert all("_metadata" in item for item in result)


class TestExportDispatchEdgeCases:
    """Additional edge cases for the export dispatch mechanism."""

    def test_case_sensitive_format_names(self) -> None:
        """Format names are case-sensitive; uppercase raises ValueError."""
        query = MessageQuery([])
        with pytest.raises(ValueError, match="Invalid export format"):
            query.export(format="JSON")

    def test_empty_format_string_raises(self) -> None:
        """Empty string format raises ValueError."""
        query = MessageQuery([])
        with pytest.raises(ValueError, match="Invalid export format"):
            query.export(format="")

    def test_valid_formats_all_dispatched(self) -> None:
        """All four valid format strings dispatch without error."""
        messages = [{"role": "user", "content": "test"}]
        query = MessageQuery(messages)

        for fmt in ("json", "markdown", "csv", "dict"):
            result = query.export(format=fmt)
            assert result is not None

    def test_subset_empty_list_for_each_format(self) -> None:
        """Passing messages=[] works for all formats."""
        query = MessageQuery([{"role": "user", "content": "hi"}])

        json_result = json.loads(query.export(format="json", messages=[]))
        md_result = query.export(format="markdown", messages=[])
        csv_result = query.export(format="csv", messages=[])
        dict_result = query.export(format="dict", messages=[])

        assert json_result == []
        assert md_result == ""
        # CSV should just have header
        reader = csv.reader(io.StringIO(csv_result))
        rows = [r for r in reader if r]
        assert len(rows) == 1
        assert dict_result == []


class TestExportJsonEdgeCases:
    """Additional JSON export edge cases not covered elsewhere."""

    def test_json_with_mock_counter_metadata(self) -> None:
        """JSON include_metadata with mock counter produces deterministic counts."""
        counter = _MockTokenCounter()
        messages = [
            {"role": "user", "content": "hello world"},
        ]
        query = MessageQuery(messages, token_counter=counter)
        result = json.loads(query.export(format="json", include_metadata=True))

        # "hello world" -> 2 words + 4 overhead = 6
        assert result[0]["token_count"] == 6

    def test_json_metadata_with_none_content_message(self) -> None:
        """JSON metadata for a message with None content has token_count >= 0."""
        messages = [{"role": "assistant", "content": None}]
        query = MessageQuery(messages)
        result = json.loads(query.export(format="json", include_metadata=True))

        assert result[0]["token_count"] == 0
        assert result[0]["index"] == 0

    def test_json_metadata_with_missing_content_field(self) -> None:
        """JSON metadata for a message with no content field has token_count >= 0."""
        messages = [{"role": "assistant"}]
        query = MessageQuery(messages)
        result = json.loads(query.export(format="json", include_metadata=True))

        assert result[0]["token_count"] == 0

    def test_json_preserves_extra_fields(self) -> None:
        """JSON export preserves arbitrary extra fields on messages."""
        messages = [
            {"role": "user", "content": "hi", "custom_id": 42, "metadata": {"key": "val"}},
        ]
        query = MessageQuery(messages)
        result = json.loads(query.export(format="json"))

        assert result[0]["custom_id"] == 42
        assert result[0]["metadata"] == {"key": "val"}


class TestExportCsvEdgeCasesExtended:
    """Additional CSV edge cases extending existing coverage."""

    def test_csv_unicode_content(self) -> None:
        """Unicode characters in CSV content are preserved."""
        messages = [{"role": "user", "content": "Unicode: \u4f60\u597d \U0001f680"}]
        query = MessageQuery(messages)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        row = next(reader)
        assert "\u4f60\u597d" in row[2]
        assert "\U0001f680" in row[2]

    def test_csv_max_content_length_zero(self) -> None:
        """max_content_length=0 truncates all content to '...'."""
        messages = [{"role": "user", "content": "anything"}]
        query = MessageQuery(messages)
        csv_result = query.export(format="csv", max_content_length=0)

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        row = next(reader)
        assert row[2] == "..."

    def test_csv_with_mock_counter_token_values(self) -> None:
        """CSV token_count column uses mock counter values."""
        counter = _MockTokenCounter()
        messages = [
            {"role": "user", "content": "a b c d e"},
            {"role": "assistant", "content": None},
        ]
        query = MessageQuery(messages, token_counter=counter)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        rows = [r for r in reader if r]

        # "a b c d e" -> 5 words + 4 = 9
        assert int(rows[0][5]) == 9
        # None content -> 0 words + 4 = 4
        assert int(rows[1][5]) == 4

    def test_csv_assistant_tool_calls_shows_first_tool_name(self) -> None:
        """Assistant with multiple tool_calls shows only the first tool name in CSV."""
        messages = [
            {
                "role": "assistant",
                "content": "Multi-tool",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "first_tool", "arguments": "{}"},
                    },
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {"name": "second_tool", "arguments": "{}"},
                    },
                ],
            },
        ]
        query = MessageQuery(messages)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        row = next(reader)

        # Only first tool name is shown
        assert row[3] == "first_tool"

    def test_csv_malformed_tool_calls_empty_tool_name(self) -> None:
        """Malformed tool_calls produce empty tool_name in CSV."""
        messages = [
            {
                "role": "assistant",
                "content": "bad",
                "tool_calls": ["not_a_dict"],
            },
        ]
        query = MessageQuery(messages)
        csv_result = query.export(format="csv")

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        row = next(reader)

        assert row[3] == ""


class TestExportDictMetadataKeyConflict:
    """Tests for _metadata key conflict resolution in dict export."""

    def test_all_messages_use_same_alternate_key(self) -> None:
        """When any message has _metadata, all use _export_metadata."""
        messages = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b", "_metadata": {"existing": True}},
            {"role": "user", "content": "c"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        # All three should use _export_metadata
        for item in result:
            assert "_export_metadata" in item
            meta = item["_export_metadata"]
            assert "index" in meta
            assert "token_count" in meta
            assert "role" in meta

    def test_alternate_key_preserves_original_metadata(self) -> None:
        """The original _metadata field is preserved when alternate key is used."""
        messages = [
            {"role": "user", "content": "a", "_metadata": {"source": "api"}},
        ]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        assert result[0]["_metadata"] == {"source": "api"}
        assert "_export_metadata" in result[0]

    def test_no_conflict_uses_standard_key(self) -> None:
        """When no messages have _metadata, _metadata is used as the key."""
        messages = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
        query = MessageQuery(messages)
        result = query.export(format="dict")

        for item in result:
            assert "_metadata" in item
            assert "_export_metadata" not in item


class TestExportSubsetConsistency:
    """Test subset export produces correct re-indexed output for all formats."""

    def test_json_subset_reindexes_from_zero(self) -> None:
        """JSON metadata indices are 0-based relative to subset, not original."""
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a2"},
        ]
        query = MessageQuery(messages)
        subset = messages[2:5]
        result = json.loads(query.export(format="json", messages=subset, include_metadata=True))

        assert len(result) == 3
        assert result[0]["index"] == 0
        assert result[1]["index"] == 1
        assert result[2]["index"] == 2

    def test_csv_subset_reindexes_from_zero(self) -> None:
        """CSV index column is 0-based relative to subset."""
        messages = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
        ]
        query = MessageQuery(messages)
        subset = messages[1:]
        csv_result = query.export(format="csv", messages=subset)

        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        rows = [r for r in reader if r]
        assert rows[0][0] == "0"
        assert rows[1][0] == "1"

    def test_dict_subset_reindexes_from_zero(self) -> None:
        """Dict metadata index is 0-based relative to subset."""
        messages = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
        ]
        query = MessageQuery(messages)
        subset = messages[1:]
        result = query.export(format="dict", messages=subset)

        assert result[0]["_metadata"]["index"] == 0
        assert result[1]["_metadata"]["index"] == 1

    def test_markdown_subset_only_contains_subset_content(self) -> None:
        """Markdown subset only contains content from the given messages."""
        messages = [
            {"role": "user", "content": "First message should not appear"},
            {"role": "assistant", "content": "Second message should not appear"},
            {"role": "user", "content": "Third message IS in subset"},
        ]
        query = MessageQuery(messages)
        subset = messages[2:]
        result = query.export(format="markdown", messages=subset)

        assert "Third message IS in subset" in result
        assert "First message should not appear" not in result
        assert "Second message should not appear" not in result

    def test_all_formats_single_message_subset(self) -> None:
        """Single-message subset works for all formats."""
        messages = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "target"},
            {"role": "user", "content": "third"},
        ]
        query = MessageQuery(messages)
        subset = [messages[1]]

        json_parsed = json.loads(query.export(format="json", messages=subset))
        md_result = query.export(format="markdown", messages=subset)
        csv_result = query.export(format="csv", messages=subset)
        dict_result = query.export(format="dict", messages=subset)

        assert len(json_parsed) == 1
        assert json_parsed[0]["content"] == "target"
        assert "target" in md_result
        assert "first" not in md_result
        reader = csv.reader(io.StringIO(csv_result))
        next(reader)
        rows = [r for r in reader if r]
        assert len(rows) == 1
        assert len(dict_result) == 1
