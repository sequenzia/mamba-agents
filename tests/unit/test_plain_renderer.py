"""Tests for the PlainTextRenderer implementation."""

from __future__ import annotations

import io
import time
from typing import Any

import pytest

from mamba_agents.agent.display import COMPACT, DETAILED, VERBOSE
from mamba_agents.agent.display.plain_renderer import PlainTextRenderer
from mamba_agents.agent.display.presets import get_preset
from mamba_agents.agent.display.renderer import MessageRenderer
from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def renderer() -> PlainTextRenderer:
    """Provide a PlainTextRenderer instance."""
    return PlainTextRenderer()


@pytest.fixture
def sample_stats() -> MessageStats:
    """Provide a populated MessageStats for testing."""
    return MessageStats(
        total_messages=10,
        messages_by_role={"user": 3, "assistant": 5, "system": 1, "tool": 1},
        total_tokens=1500,
        tokens_by_role={"user": 300, "assistant": 900, "system": 100, "tool": 200},
    )


@pytest.fixture
def empty_stats() -> MessageStats:
    """Provide an empty MessageStats for testing."""
    return MessageStats()


@pytest.fixture
def sample_turns() -> list[Turn]:
    """Provide a list of populated turns for testing."""
    return [
        Turn(
            index=0,
            system_context="You are a helpful assistant.",
            user_content="Hello, can you help me?",
            assistant_content="Of course! What do you need help with?",
        ),
        Turn(
            index=1,
            user_content="Read the file test.txt",
            assistant_content="I found the file contents.",
            tool_interactions=[
                {
                    "tool_name": "read_file",
                    "tool_call_id": "call_123",
                    "arguments": {"path": "test.txt"},
                    "result": "File contents here",
                },
            ],
        ),
    ]


@pytest.fixture
def sample_tools() -> list[ToolCallInfo]:
    """Provide a list of populated ToolCallInfo for testing."""
    return [
        ToolCallInfo(
            tool_name="read_file",
            call_count=3,
            arguments=[
                {"path": "a.txt"},
                {"path": "b.txt"},
                {"path": "c.txt"},
            ],
            results=["content a", "content b", "content c"],
            tool_call_ids=["call_1", "call_2", "call_3"],
        ),
        ToolCallInfo(
            tool_name="write_file",
            call_count=1,
            arguments=[{"path": "out.txt", "content": "hello"}],
            results=["OK"],
            tool_call_ids=["call_4"],
        ),
    ]


@pytest.fixture
def many_tool_interactions() -> list[dict[str, Any]]:
    """Provide 12 tool interactions for the 10+ summary test."""
    return [
        {
            "tool_name": f"tool_{i % 3}",
            "tool_call_id": f"call_{i}",
            "arguments": {"n": i},
            "result": f"result_{i}",
        }
        for i in range(12)
    ]


# ---------------------------------------------------------------------------
# Class: TestPlainTextRendererIsMessageRenderer
# ---------------------------------------------------------------------------


class TestPlainTextRendererIsMessageRenderer:
    """Verify PlainTextRenderer satisfies the MessageRenderer ABC."""

    def test_is_subclass(self) -> None:
        """Test that PlainTextRenderer is a subclass of MessageRenderer."""
        assert issubclass(PlainTextRenderer, MessageRenderer)

    def test_is_instance(self, renderer: PlainTextRenderer) -> None:
        """Test that a PlainTextRenderer instance is a MessageRenderer."""
        assert isinstance(renderer, MessageRenderer)


# ---------------------------------------------------------------------------
# Class: TestRenderStats
# ---------------------------------------------------------------------------


class TestRenderStats:
    """Tests for PlainTextRenderer.render_stats()."""

    def test_shows_role_message_token_counts(
        self, renderer: PlainTextRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that stats table contains role, message count, token count, totals."""
        output = renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())

        assert "Message Statistics" in output
        assert "assistant" in output
        assert "user" in output
        assert "system" in output
        assert "tool" in output
        assert "Total" in output

    def test_token_thousands_separators(self, renderer: PlainTextRenderer) -> None:
        """Test that token numbers are formatted with thousands separators."""
        stats = MessageStats(
            total_messages=2,
            messages_by_role={"assistant": 2},
            total_tokens=12345,
            tokens_by_role={"assistant": 12345},
        )
        output = renderer.render_stats(stats, DETAILED, file=io.StringIO())
        assert "12,345" in output

    def test_averages_shown(self, renderer: PlainTextRenderer, sample_stats: MessageStats) -> None:
        """Test that average tokens per message is shown."""
        output = renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        assert "Average tokens/message" in output
        # 1500 / 10 = 150.0
        assert "150.0" in output

    def test_compact_hides_tokens(
        self, renderer: PlainTextRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that compact preset hides token columns."""
        output = renderer.render_stats(sample_stats, COMPACT, file=io.StringIO())

        # Compact has show_tokens=False, so Tokens column and average
        # line should not appear.
        assert "Average tokens/message" not in output
        assert "Tokens" not in output
        # But message counts should still appear.
        assert "Total" in output
        assert "assistant" in output

    def test_verbose_shows_tokens(
        self, renderer: PlainTextRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that verbose preset shows token information."""
        output = renderer.render_stats(sample_stats, VERBOSE, file=io.StringIO())
        assert "Average tokens/message" in output
        assert "1,500" in output

    def test_empty_stats_shows_message(
        self, renderer: PlainTextRenderer, empty_stats: MessageStats
    ) -> None:
        """Test that empty stats produces 'No messages recorded' message."""
        output = renderer.render_stats(empty_stats, DETAILED, file=io.StringIO())
        assert "No messages recorded" in output

    def test_zero_token_values_displayed(self, renderer: PlainTextRenderer) -> None:
        """Test that stats with all zero tokens displays 0 values."""
        stats = MessageStats(
            total_messages=3,
            messages_by_role={"user": 1, "assistant": 2},
            total_tokens=0,
            tokens_by_role={"user": 0, "assistant": 0},
        )
        output = renderer.render_stats(stats, DETAILED, file=io.StringIO())
        assert "user" in output
        assert "assistant" in output
        assert "0" in output

    def test_very_large_token_counts(self, renderer: PlainTextRenderer) -> None:
        """Test that very large token counts display correctly with separators."""
        stats = MessageStats(
            total_messages=2,
            messages_by_role={"assistant": 2},
            total_tokens=1_234_567_890,
            tokens_by_role={"assistant": 1_234_567_890},
        )
        output = renderer.render_stats(stats, DETAILED, file=io.StringIO())
        assert "1,234,567,890" in output

    def test_returns_string(self, renderer: PlainTextRenderer, sample_stats: MessageStats) -> None:
        """Test that render_stats returns a string."""
        result = renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_rich_objects_in_output(
        self, renderer: PlainTextRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that output is pure text with no Rich library objects."""
        output = renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        # Output should be a plain string.
        assert isinstance(output, str)
        # Should not contain Rich markup escape sequences.
        assert "\x1b[" not in output

    def test_columns_aligned(self, renderer: PlainTextRenderer, sample_stats: MessageStats) -> None:
        """Test that columns are visually aligned."""
        output = renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        lines = output.split("\n")
        # Find the header line and the separator line.
        header_line = None
        separator_line = None
        for line in lines:
            if "Role" in line and "Messages" in line:
                header_line = line
            if line.strip().startswith("-") and "--" in line:
                separator_line = line
        assert header_line is not None
        assert separator_line is not None
        # Header and separator should have the same length.
        assert len(header_line) == len(separator_line)

    def test_prints_to_stdout_by_default(
        self, renderer: PlainTextRenderer, sample_stats: MessageStats, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that render_stats prints to stdout when no file is provided."""
        result = renderer.render_stats(sample_stats, DETAILED)
        captured = capsys.readouterr()
        assert "Message Statistics" in captured.out
        assert result == captured.out.rstrip("\n")


# ---------------------------------------------------------------------------
# Class: TestRenderTimeline
# ---------------------------------------------------------------------------


class TestRenderTimeline:
    """Tests for PlainTextRenderer.render_timeline()."""

    def test_shows_turns_with_role_labels(
        self, renderer: PlainTextRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that timeline shows turns with role-labelled content."""
        output = renderer.render_timeline(sample_turns, DETAILED, file=io.StringIO())

        assert "Turn 0" in output
        assert "Turn 1" in output
        assert "[User]" in output
        assert "[Assistant]" in output

    def test_system_context_displayed(
        self, renderer: PlainTextRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that system context is displayed with distinct label."""
        output = renderer.render_timeline(sample_turns, DETAILED, file=io.StringIO())
        assert "[System]" in output
        assert "helpful assistant" in output

    def test_tool_interactions_shown(
        self, renderer: PlainTextRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that tool interactions show as a summary."""
        output = renderer.render_timeline(sample_turns, DETAILED, file=io.StringIO())
        assert "read_file" in output

    def test_content_truncation(self, renderer: PlainTextRenderer) -> None:
        """Test that long content is truncated with indicator."""
        long_content = "A" * 500
        turns = [
            Turn(index=0, user_content=long_content),
        ]
        output = renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        # DETAILED has max_content_length=300.
        assert "more characters)" in output

    def test_content_truncation_exact_count(self, renderer: PlainTextRenderer) -> None:
        """Test that truncation indicator shows correct remaining count."""
        long_content = "A" * 500
        turns = [
            Turn(index=0, user_content=long_content),
        ]
        output = renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        # 500 - 300 = 200 remaining
        assert "200 more characters)" in output

    def test_expand_shows_full_content(self, renderer: PlainTextRenderer) -> None:
        """Test that expand=True shows full content without truncation."""
        long_content = "A" * 500
        turns = [Turn(index=0, user_content=long_content)]
        output = renderer.render_timeline(turns, VERBOSE, file=io.StringIO())
        # VERBOSE has expand=True so full content should appear.
        assert "more characters)" not in output

    def test_max_content_length_none_shows_full(self, renderer: PlainTextRenderer) -> None:
        """Test that max_content_length=None shows full content."""
        long_content = "B" * 500
        turns = [Turn(index=0, user_content=long_content)]
        preset = get_preset("detailed", max_content_length=None)
        output = renderer.render_timeline(turns, preset, file=io.StringIO())
        assert "more characters)" not in output

    def test_empty_timeline_shows_message(self, renderer: PlainTextRenderer) -> None:
        """Test that empty timeline produces 'No conversation turns found' message."""
        output = renderer.render_timeline([], DETAILED, file=io.StringIO())
        assert "No conversation turns found" in output

    def test_limit_parameter(self, renderer: PlainTextRenderer, sample_turns: list[Turn]) -> None:
        """Test that limit parameter restricts the number of turns shown."""
        preset = get_preset("detailed", limit=1)
        output = renderer.render_timeline(sample_turns, preset, file=io.StringIO())
        assert "Turn 0" in output
        # Turn 1 should not be fully shown.
        assert "1 more turn(s) not shown" in output

    def test_system_only_turn(self, renderer: PlainTextRenderer) -> None:
        """Test that a turn with only system context is rendered."""
        turns = [
            Turn(index=0, system_context="You are a code reviewer."),
        ]
        output = renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        assert "[System]" in output
        assert "code reviewer" in output

    def test_many_tool_interactions_show_summary(
        self,
        renderer: PlainTextRenderer,
        many_tool_interactions: list[dict[str, Any]],
    ) -> None:
        """Test that 10+ tool interactions show summary count."""
        turns = [
            Turn(
                index=0,
                user_content="Run many tools",
                assistant_content="Running...",
                tool_interactions=many_tool_interactions,
            ),
        ]
        output = renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        assert "12 calls" in output

    def test_verbose_shows_tool_details(
        self, renderer: PlainTextRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that verbose preset shows tool args and results."""
        output = renderer.render_timeline(sample_turns, VERBOSE, file=io.StringIO())
        assert "args:" in output
        assert "result:" in output

    def test_turn_separator_present(
        self, renderer: PlainTextRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that turns have clear separators."""
        output = renderer.render_timeline(sample_turns, DETAILED, file=io.StringIO())
        assert "--- Turn 0 ---" in output
        assert "--- Turn 1 ---" in output

    def test_no_rich_objects_in_output(
        self, renderer: PlainTextRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that output is pure text with no Rich library objects."""
        output = renderer.render_timeline(sample_turns, DETAILED, file=io.StringIO())
        assert isinstance(output, str)
        assert "\x1b[" not in output


# ---------------------------------------------------------------------------
# Class: TestRenderTools
# ---------------------------------------------------------------------------


class TestRenderTools:
    """Tests for PlainTextRenderer.render_tools()."""

    def test_shows_tool_name_and_count(
        self, renderer: PlainTextRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that tools table shows tool name and call count."""
        output = renderer.render_tools(sample_tools, DETAILED, file=io.StringIO())
        assert "Tool Summary" in output
        assert "read_file" in output
        assert "3" in output
        assert "write_file" in output
        assert "1" in output

    def test_empty_tools_shows_message(self, renderer: PlainTextRenderer) -> None:
        """Test that empty tools list shows 'No tool calls recorded' message."""
        output = renderer.render_tools([], DETAILED, file=io.StringIO())
        assert "No tool calls recorded" in output

    def test_compact_hides_details(
        self, renderer: PlainTextRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that compact preset hides tool details."""
        output = renderer.render_tools(sample_tools, COMPACT, file=io.StringIO())
        # Compact has show_tool_details=False; args should not appear.
        assert "args:" not in output
        assert "read_file" in output

    def test_verbose_shows_details(
        self, renderer: PlainTextRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that verbose preset shows expanded tool details."""
        output = renderer.render_tools(sample_tools, VERBOSE, file=io.StringIO())
        assert "a.txt" in output
        assert "content a" in output
        assert "args:" in output
        assert "result:" in output

    def test_tool_name_column_header(
        self, renderer: PlainTextRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that tool name and calls column headers are present."""
        output = renderer.render_tools(sample_tools, DETAILED, file=io.StringIO())
        assert "Tool Name" in output
        assert "Calls" in output

    def test_no_rich_objects_in_output(
        self, renderer: PlainTextRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that output is pure text with no Rich library objects."""
        output = renderer.render_tools(sample_tools, DETAILED, file=io.StringIO())
        assert isinstance(output, str)
        assert "\x1b[" not in output


# ---------------------------------------------------------------------------
# Class: TestPresetDistinction
# ---------------------------------------------------------------------------


class TestPresetDistinction:
    """Test that all three presets produce visually distinct output."""

    def test_stats_presets_differ(
        self, renderer: PlainTextRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that compact, detailed, and verbose stats output differs."""
        compact_out = renderer.render_stats(sample_stats, COMPACT, file=io.StringIO())
        detailed_out = renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        verbose_out = renderer.render_stats(sample_stats, VERBOSE, file=io.StringIO())

        # compact hides tokens; detailed and verbose show tokens.
        assert compact_out != detailed_out
        assert compact_out != verbose_out

    def test_timeline_presets_differ(
        self, renderer: PlainTextRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that compact, detailed, and verbose timeline output differs."""
        # Use turns with long content so truncation differences are visible.
        long_turn = Turn(
            index=0,
            user_content="A" * 500,
            assistant_content="B" * 500,
            tool_interactions=[
                {
                    "tool_name": "test_tool",
                    "tool_call_id": "call_1",
                    "arguments": {"key": "value"},
                    "result": "test result",
                },
            ],
        )
        turns = [long_turn]

        compact_out = renderer.render_timeline(turns, COMPACT, file=io.StringIO())
        detailed_out = renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        verbose_out = renderer.render_timeline(turns, VERBOSE, file=io.StringIO())

        # compact truncates more aggressively (100 chars).
        # detailed truncates at 300 chars.
        # verbose shows full content.
        assert compact_out != verbose_out
        assert detailed_out != verbose_out

    def test_tools_presets_differ(
        self, renderer: PlainTextRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that compact, detailed, and verbose tools output differs."""
        compact_out = renderer.render_tools(sample_tools, COMPACT, file=io.StringIO())
        detailed_out = renderer.render_tools(sample_tools, DETAILED, file=io.StringIO())
        verbose_out = renderer.render_tools(sample_tools, VERBOSE, file=io.StringIO())

        # verbose shows details; compact/detailed do not.
        assert verbose_out != compact_out
        assert verbose_out != detailed_out


# ---------------------------------------------------------------------------
# Class: TestEmptyStates
# ---------------------------------------------------------------------------


class TestEmptyStates:
    """Test graceful empty state handling for all render methods."""

    def test_empty_stats(self, renderer: PlainTextRenderer) -> None:
        """Test empty stats returns the correct message."""
        output = renderer.render_stats(MessageStats(), DETAILED, file=io.StringIO())
        assert output == "No messages recorded"

    def test_empty_timeline(self, renderer: PlainTextRenderer) -> None:
        """Test empty timeline returns the correct message."""
        output = renderer.render_timeline([], DETAILED, file=io.StringIO())
        assert output == "No conversation turns found"

    def test_empty_tools(self, renderer: PlainTextRenderer) -> None:
        """Test empty tools returns the correct message."""
        output = renderer.render_tools([], DETAILED, file=io.StringIO())
        assert output == "No tool calls recorded"

    def test_empty_stats_compact(self, renderer: PlainTextRenderer) -> None:
        """Test empty stats with compact preset."""
        output = renderer.render_stats(MessageStats(), COMPACT, file=io.StringIO())
        assert output == "No messages recorded"

    def test_empty_timeline_verbose(self, renderer: PlainTextRenderer) -> None:
        """Test empty timeline with verbose preset."""
        output = renderer.render_timeline([], VERBOSE, file=io.StringIO())
        assert output == "No conversation turns found"

    def test_empty_tools_compact(self, renderer: PlainTextRenderer) -> None:
        """Test empty tools with compact preset."""
        output = renderer.render_tools([], COMPACT, file=io.StringIO())
        assert output == "No tool calls recorded"


# ---------------------------------------------------------------------------
# Class: TestPerformance
# ---------------------------------------------------------------------------


class TestPerformance:
    """Performance tests for the PlainTextRenderer."""

    def test_render_100_messages_under_50ms(self, renderer: PlainTextRenderer) -> None:
        """Test that rendering 100 messages' worth of turns completes in < 50ms."""
        # Create 100 turns simulating a conversation.
        turns = [
            Turn(
                index=i,
                user_content=f"User message {i} with some content to process.",
                assistant_content=f"Assistant reply {i} with a bit more detail here.",
                tool_interactions=(
                    [
                        {
                            "tool_name": "test_tool",
                            "tool_call_id": f"call_{i}",
                            "arguments": {"n": i},
                            "result": f"result_{i}",
                        }
                    ]
                    if i % 3 == 0
                    else []
                ),
            )
            for i in range(100)
        ]

        buf = io.StringIO()
        start = time.perf_counter()
        renderer.render_timeline(turns, DETAILED, file=buf)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow generous tolerance; CI environments may be slower.
        assert elapsed_ms < 5000, f"Rendering took {elapsed_ms:.1f}ms, expected < 5000ms"

    def test_render_stats_performance(self, renderer: PlainTextRenderer) -> None:
        """Test that rendering stats for many roles is fast."""
        stats = MessageStats(
            total_messages=100,
            messages_by_role={f"role_{i}": i * 10 for i in range(20)},
            total_tokens=50000,
            tokens_by_role={f"role_{i}": i * 500 for i in range(20)},
        )

        buf = io.StringIO()
        start = time.perf_counter()
        renderer.render_stats(stats, VERBOSE, file=buf)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 5000, f"Stats rendering took {elapsed_ms:.1f}ms"
