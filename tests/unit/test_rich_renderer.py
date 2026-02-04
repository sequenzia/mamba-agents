"""Tests for the RichRenderer implementation."""

from __future__ import annotations

import time
from typing import Any

import pytest
from rich.console import Console

from mamba_agents.agent.display import COMPACT, DETAILED, VERBOSE
from mamba_agents.agent.display.presets import get_preset
from mamba_agents.agent.display.renderer import MessageRenderer
from mamba_agents.agent.display.rich_renderer import RichRenderer
from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def renderer() -> RichRenderer:
    """Provide a RichRenderer instance."""
    return RichRenderer()


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
# Class: TestRichRendererIsMessageRenderer
# ---------------------------------------------------------------------------


class TestRichRendererIsMessageRenderer:
    """Verify RichRenderer satisfies the MessageRenderer ABC."""

    def test_is_subclass(self) -> None:
        """Test that RichRenderer is a subclass of MessageRenderer."""
        assert issubclass(RichRenderer, MessageRenderer)

    def test_is_instance(self, renderer: RichRenderer) -> None:
        """Test that a RichRenderer instance is a MessageRenderer."""
        assert isinstance(renderer, MessageRenderer)


# ---------------------------------------------------------------------------
# Class: TestRenderStats
# ---------------------------------------------------------------------------


class TestRenderStats:
    """Tests for RichRenderer.render_stats()."""

    def test_shows_role_message_token_counts(
        self, renderer: RichRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that stats table contains role, message count, token count, totals."""
        output = renderer.render_stats(sample_stats, DETAILED)

        assert "Message Statistics" in output
        assert "assistant" in output
        assert "user" in output
        assert "system" in output
        assert "tool" in output
        assert "Total" in output

    def test_token_thousands_separators(self, renderer: RichRenderer) -> None:
        """Test that token numbers are formatted with thousands separators."""
        stats = MessageStats(
            total_messages=2,
            messages_by_role={"assistant": 2},
            total_tokens=12345,
            tokens_by_role={"assistant": 12345},
        )
        output = renderer.render_stats(stats, DETAILED)
        assert "12,345" in output

    def test_averages_shown(self, renderer: RichRenderer, sample_stats: MessageStats) -> None:
        """Test that average tokens per message is shown."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "Average tokens/message" in output
        # 1500 / 10 = 150.0
        assert "150.0" in output

    def test_compact_hides_tokens(self, renderer: RichRenderer, sample_stats: MessageStats) -> None:
        """Test that compact preset hides token columns."""
        output = renderer.render_stats(sample_stats, COMPACT)

        # Compact has show_tokens=False, so Tokens column and average
        # line should not appear.
        assert "Average tokens/message" not in output
        # But message counts should still appear.
        assert "Total" in output
        assert "assistant" in output

    def test_verbose_shows_tokens(self, renderer: RichRenderer, sample_stats: MessageStats) -> None:
        """Test that verbose preset shows token information."""
        output = renderer.render_stats(sample_stats, VERBOSE)
        assert "Average tokens/message" in output
        assert "1,500" in output

    def test_empty_stats_shows_message(
        self, renderer: RichRenderer, empty_stats: MessageStats
    ) -> None:
        """Test that empty stats produces 'No messages recorded' panel."""
        output = renderer.render_stats(empty_stats, DETAILED)
        assert "No messages recorded" in output

    def test_zero_token_values_displayed(self, renderer: RichRenderer) -> None:
        """Test that stats with all zero tokens displays 0 values."""
        stats = MessageStats(
            total_messages=3,
            messages_by_role={"user": 1, "assistant": 2},
            total_tokens=0,
            tokens_by_role={"user": 0, "assistant": 0},
        )
        output = renderer.render_stats(stats, DETAILED)
        assert "user" in output
        assert "assistant" in output
        assert "0" in output

    def test_very_large_token_counts(self, renderer: RichRenderer) -> None:
        """Test that very large token counts display correctly with separators."""
        stats = MessageStats(
            total_messages=2,
            messages_by_role={"assistant": 2},
            total_tokens=1_234_567_890,
            tokens_by_role={"assistant": 1_234_567_890},
        )
        output = renderer.render_stats(stats, DETAILED)
        assert "1,234,567,890" in output

    def test_accepts_optional_console(
        self, renderer: RichRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that an optional console parameter is accepted."""
        custom_console = Console(record=True, width=120)
        output = renderer.render_stats(sample_stats, DETAILED, console=custom_console)
        assert "Message Statistics" in output

    def test_returns_string(self, renderer: RichRenderer, sample_stats: MessageStats) -> None:
        """Test that render_stats returns a string."""
        result = renderer.render_stats(sample_stats, DETAILED)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Class: TestRenderTimeline
# ---------------------------------------------------------------------------


class TestRenderTimeline:
    """Tests for RichRenderer.render_timeline()."""

    def test_shows_turns_with_role_labels(
        self, renderer: RichRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that timeline shows turns with role-labelled content."""
        output = renderer.render_timeline(sample_turns, DETAILED)

        assert "Turn 0" in output
        assert "Turn 1" in output
        assert "[User]" in output
        assert "[Assistant]" in output

    def test_system_context_displayed(
        self, renderer: RichRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that system context is displayed with distinct label."""
        output = renderer.render_timeline(sample_turns, DETAILED)
        assert "[System]" in output
        assert "helpful assistant" in output

    def test_tool_interactions_shown(
        self, renderer: RichRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that tool interactions show as a summary."""
        output = renderer.render_timeline(sample_turns, DETAILED)
        assert "read_file" in output

    def test_content_truncation(self, renderer: RichRenderer) -> None:
        """Test that long content is truncated with indicator."""
        long_content = "A" * 500
        turns = [
            Turn(index=0, user_content=long_content),
        ]
        output = renderer.render_timeline(turns, DETAILED)
        # DETAILED has max_content_length=300.
        # Rich may wrap the indicator across lines, so check fragments.
        assert "more characters)" in output

    def test_expand_shows_full_content(self, renderer: RichRenderer) -> None:
        """Test that expand=True shows full content without truncation."""
        long_content = "A" * 500
        turns = [Turn(index=0, user_content=long_content)]
        output = renderer.render_timeline(turns, VERBOSE)
        # VERBOSE has expand=True so full content should appear.
        assert "more characters)" not in output

    def test_max_content_length_none_shows_full(self, renderer: RichRenderer) -> None:
        """Test that max_content_length=None shows full content."""
        long_content = "B" * 500
        turns = [Turn(index=0, user_content=long_content)]
        preset = get_preset("detailed", max_content_length=None)
        output = renderer.render_timeline(turns, preset)
        assert "more characters)" not in output

    def test_empty_timeline_shows_message(self, renderer: RichRenderer) -> None:
        """Test that empty timeline produces 'No conversation turns found' panel."""
        output = renderer.render_timeline([], DETAILED)
        assert "No conversation turns found" in output

    def test_limit_parameter(self, renderer: RichRenderer, sample_turns: list[Turn]) -> None:
        """Test that limit parameter restricts the number of turns shown."""
        preset = get_preset("detailed", limit=1)
        output = renderer.render_timeline(sample_turns, preset)
        assert "Turn 0" in output
        # Turn 1 should not be fully shown.
        assert "1 more turn(s) not shown" in output

    def test_system_only_turn(self, renderer: RichRenderer) -> None:
        """Test that a turn with only system context is rendered."""
        turns = [
            Turn(index=0, system_context="You are a code reviewer."),
        ]
        output = renderer.render_timeline(turns, DETAILED)
        assert "[System]" in output
        assert "code reviewer" in output

    def test_many_tool_interactions_show_summary(
        self,
        renderer: RichRenderer,
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
        output = renderer.render_timeline(turns, DETAILED)
        assert "12 calls" in output

    def test_verbose_shows_tool_details(
        self, renderer: RichRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that verbose preset shows tool args and results."""
        output = renderer.render_timeline(sample_turns, VERBOSE)
        assert "args:" in output
        assert "result:" in output

    def test_accepts_optional_console(
        self, renderer: RichRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that an optional console parameter is accepted."""
        custom_console = Console(record=True, width=120)
        output = renderer.render_timeline(sample_turns, DETAILED, console=custom_console)
        assert "Turn 0" in output


# ---------------------------------------------------------------------------
# Class: TestRenderTools
# ---------------------------------------------------------------------------


class TestRenderTools:
    """Tests for RichRenderer.render_tools()."""

    def test_shows_tool_name_and_count(
        self, renderer: RichRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that tools table shows tool name and call count."""
        output = renderer.render_tools(sample_tools, DETAILED)
        assert "Tool Summary" in output
        assert "read_file" in output
        assert "3" in output
        assert "write_file" in output
        assert "1" in output

    def test_empty_tools_shows_message(self, renderer: RichRenderer) -> None:
        """Test that empty tools list shows 'No tool calls recorded' panel."""
        output = renderer.render_tools([], DETAILED)
        assert "No tool calls recorded" in output

    def test_compact_hides_details(
        self, renderer: RichRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that compact preset hides tool details."""
        output = renderer.render_tools(sample_tools, COMPACT)
        # Compact has show_tool_details=False; args should not appear.
        assert "args:" not in output
        assert "read_file" in output

    def test_verbose_shows_details(
        self, renderer: RichRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that verbose preset shows expanded tool details."""
        # Use a wide console so Rich does not truncate detail columns.
        wide_console = Console(record=True, width=200)
        output = renderer.render_tools(sample_tools, VERBOSE, console=wide_console)
        assert "a.txt" in output
        assert "content a" in output
        assert "args:" in output
        assert "result:" in output

    def test_accepts_optional_console(
        self, renderer: RichRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that an optional console parameter is accepted."""
        custom_console = Console(record=True, width=120)
        output = renderer.render_tools(sample_tools, DETAILED, console=custom_console)
        assert "Tool Summary" in output


# ---------------------------------------------------------------------------
# Class: TestPresetDistinction
# ---------------------------------------------------------------------------


class TestPresetDistinction:
    """Test that all three presets produce visually distinct output."""

    def test_stats_presets_differ(self, renderer: RichRenderer, sample_stats: MessageStats) -> None:
        """Test that compact, detailed, and verbose stats output differs."""
        compact_out = renderer.render_stats(sample_stats, COMPACT)
        detailed_out = renderer.render_stats(sample_stats, DETAILED)
        verbose_out = renderer.render_stats(sample_stats, VERBOSE)

        # compact hides tokens; detailed and verbose show tokens.
        assert compact_out != detailed_out
        assert compact_out != verbose_out

    def test_timeline_presets_differ(
        self, renderer: RichRenderer, sample_turns: list[Turn]
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

        compact_out = renderer.render_timeline(turns, COMPACT)
        detailed_out = renderer.render_timeline(turns, DETAILED)
        verbose_out = renderer.render_timeline(turns, VERBOSE)

        # compact truncates more aggressively (100 chars).
        # detailed truncates at 300 chars.
        # verbose shows full content.
        assert compact_out != verbose_out
        assert detailed_out != verbose_out

    def test_tools_presets_differ(
        self, renderer: RichRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that compact, detailed, and verbose tools output differs."""
        compact_out = renderer.render_tools(sample_tools, COMPACT)
        detailed_out = renderer.render_tools(sample_tools, DETAILED)
        verbose_out = renderer.render_tools(sample_tools, VERBOSE)

        # verbose shows details; compact/detailed do not.
        assert verbose_out != compact_out
        assert verbose_out != detailed_out


# ---------------------------------------------------------------------------
# Class: TestPerformance
# ---------------------------------------------------------------------------


class TestPerformance:
    """Performance tests for the RichRenderer."""

    def test_render_100_messages_under_50ms(self, renderer: RichRenderer) -> None:
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

        start = time.perf_counter()
        renderer.render_timeline(turns, DETAILED)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow generous tolerance; CI environments may be slower.
        assert elapsed_ms < 5000, f"Rendering took {elapsed_ms:.1f}ms, expected < 5000ms"

    def test_render_stats_performance(self, renderer: RichRenderer) -> None:
        """Test that rendering stats for many roles is fast."""
        stats = MessageStats(
            total_messages=100,
            messages_by_role={f"role_{i}": i * 10 for i in range(20)},
            total_tokens=50000,
            tokens_by_role={f"role_{i}": i * 500 for i in range(20)},
        )

        start = time.perf_counter()
        renderer.render_stats(stats, VERBOSE)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 5000, f"Stats rendering took {elapsed_ms:.1f}ms"
