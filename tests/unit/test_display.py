"""Cross-cutting display module tests.

Comprehensive tests covering cross-renderer comparisons, edge cases not covered
by individual renderer test files, coverage gaps, and integration scenarios across
the full display pipeline.

This file complements the per-renderer test files (test_rich_renderer.py,
test_plain_renderer.py, test_html_renderer.py) and the per-feature test files
(test_display_presets.py, test_display_functions.py, test_display_exports.py,
test_message_query_print_*.py, test_rich_console_protocol.py).
"""

from __future__ import annotations

import io

import pytest
from rich.console import Console

from mamba_agents.agent.display import (
    COMPACT,
    DETAILED,
    VERBOSE,
    print_stats,
    print_timeline,
    print_tools,
)
from mamba_agents.agent.display.html_renderer import HtmlRenderer
from mamba_agents.agent.display.plain_renderer import PlainTextRenderer
from mamba_agents.agent.display.presets import DisplayPreset, get_preset
from mamba_agents.agent.display.rich_renderer import RichRenderer
from mamba_agents.agent.messages import MessageQuery, MessageStats, ToolCallInfo, Turn

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rich_renderer() -> RichRenderer:
    """Provide a RichRenderer instance."""
    return RichRenderer()


@pytest.fixture
def plain_renderer() -> PlainTextRenderer:
    """Provide a PlainTextRenderer instance."""
    return PlainTextRenderer()


@pytest.fixture
def html_renderer() -> HtmlRenderer:
    """Provide an HtmlRenderer instance."""
    return HtmlRenderer()


@pytest.fixture
def sample_stats() -> MessageStats:
    """Provide a populated MessageStats for cross-renderer testing."""
    return MessageStats(
        total_messages=8,
        messages_by_role={"user": 3, "assistant": 4, "system": 1},
        total_tokens=2400,
        tokens_by_role={"user": 600, "assistant": 1200, "system": 600},
    )


@pytest.fixture
def sample_turns() -> list[Turn]:
    """Provide populated turns for cross-renderer testing."""
    return [
        Turn(
            index=0,
            system_context="You are a helpful assistant.",
            user_content="Hello, can you help me?",
            assistant_content="Of course! What do you need?",
        ),
        Turn(
            index=1,
            user_content="Read the file test.txt",
            assistant_content="Here is the content.",
            tool_interactions=[
                {
                    "tool_name": "read_file",
                    "tool_call_id": "call_abc",
                    "arguments": {"path": "test.txt"},
                    "result": "File contents here",
                },
            ],
        ),
    ]


@pytest.fixture
def sample_tools() -> list[ToolCallInfo]:
    """Provide populated ToolCallInfo for cross-renderer testing."""
    return [
        ToolCallInfo(
            tool_name="read_file",
            call_count=2,
            arguments=[{"path": "a.txt"}, {"path": "b.txt"}],
            results=["content a", "content b"],
            tool_call_ids=["call_1", "call_2"],
        ),
        ToolCallInfo(
            tool_name="write_file",
            call_count=1,
            arguments=[{"path": "out.txt", "content": "hello"}],
            results=["OK"],
            tool_call_ids=["call_3"],
        ),
    ]


# ---------------------------------------------------------------------------
# Cross-renderer consistency: same data produces format-appropriate output
# ---------------------------------------------------------------------------


class TestCrossRendererStatsConsistency:
    """Verify all three renderers produce semantically equivalent stats output."""

    def test_all_renderers_show_role_names(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_stats: MessageStats,
    ) -> None:
        """All renderers include role names in stats output."""
        rich_out = rich_renderer.render_stats(sample_stats, DETAILED)
        plain_out = plain_renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_stats(sample_stats, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "user" in output
            assert "assistant" in output
            assert "system" in output

    def test_all_renderers_show_total(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_stats: MessageStats,
    ) -> None:
        """All renderers include a Total row in stats output."""
        rich_out = rich_renderer.render_stats(sample_stats, DETAILED)
        plain_out = plain_renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_stats(sample_stats, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "Total" in output

    def test_all_renderers_show_message_statistics_title(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_stats: MessageStats,
    ) -> None:
        """All renderers include 'Message Statistics' title."""
        rich_out = rich_renderer.render_stats(sample_stats, DETAILED)
        plain_out = plain_renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_stats(sample_stats, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "Message Statistics" in output

    def test_all_renderers_show_averages_when_tokens_enabled(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_stats: MessageStats,
    ) -> None:
        """All renderers show average tokens/message with show_tokens=True."""
        rich_out = rich_renderer.render_stats(sample_stats, DETAILED)
        plain_out = plain_renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_stats(sample_stats, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "Average tokens/message" in output

    def test_compact_hides_tokens_across_all_renderers(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_stats: MessageStats,
    ) -> None:
        """Compact preset hides token information across all renderers."""
        rich_out = rich_renderer.render_stats(sample_stats, COMPACT)
        plain_out = plain_renderer.render_stats(sample_stats, COMPACT, file=io.StringIO())
        html_out = html_renderer.render_stats(sample_stats, COMPACT)

        for output in (rich_out, plain_out, html_out):
            assert "Average tokens/message" not in output

    def test_format_types_are_distinguishable(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_stats: MessageStats,
    ) -> None:
        """Each renderer produces output in its own format."""
        html_out = html_renderer.render_stats(sample_stats, DETAILED)
        plain_out = plain_renderer.render_stats(sample_stats, DETAILED, file=io.StringIO())
        rich_out = rich_renderer.render_stats(sample_stats, DETAILED)

        # HTML uses tags
        assert "<table>" in html_out
        assert "<table>" not in plain_out
        assert "<table>" not in rich_out

        # Plain text has no ANSI escape codes
        assert "\x1b[" not in plain_out


class TestCrossRendererTimelineConsistency:
    """Verify all three renderers produce semantically equivalent timeline output."""

    def test_all_renderers_show_turn_labels(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_turns: list[Turn],
    ) -> None:
        """All renderers show turn numbers and role labels."""
        rich_out = rich_renderer.render_timeline(sample_turns, DETAILED)
        plain_out = plain_renderer.render_timeline(sample_turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(sample_turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "Turn 0" in output
            assert "Turn 1" in output
            assert "[User]" in output
            assert "[Assistant]" in output

    def test_all_renderers_show_tool_names(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_turns: list[Turn],
    ) -> None:
        """All renderers include tool names from interactions."""
        rich_out = rich_renderer.render_timeline(sample_turns, DETAILED)
        plain_out = plain_renderer.render_timeline(sample_turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(sample_turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "read_file" in output

    def test_all_renderers_truncate_consistently(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """All renderers truncate long content at the same boundary."""
        long_content = "X" * 500
        turns = [Turn(index=0, user_content=long_content)]

        rich_out = rich_renderer.render_timeline(turns, DETAILED)
        plain_out = plain_renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, DETAILED)

        # All should truncate at 300 (DETAILED.max_content_length) with indicator.
        for output in (rich_out, plain_out, html_out):
            assert "200 more characters)" in output

    def test_limit_applies_consistently(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_turns: list[Turn],
    ) -> None:
        """All renderers apply the limit parameter identically."""
        preset = get_preset("detailed", limit=1)

        rich_out = rich_renderer.render_timeline(sample_turns, preset)
        plain_out = plain_renderer.render_timeline(sample_turns, preset, file=io.StringIO())
        html_out = html_renderer.render_timeline(sample_turns, preset)

        for output in (rich_out, plain_out, html_out):
            assert "Turn 0" in output
            assert "1 more turn(s) not shown" in output


class TestCrossRendererToolsConsistency:
    """Verify all three renderers produce semantically equivalent tools output."""

    def test_all_renderers_show_tool_names_and_counts(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_tools: list[ToolCallInfo],
    ) -> None:
        """All renderers include tool name and call count."""
        rich_out = rich_renderer.render_tools(sample_tools, DETAILED)
        plain_out = plain_renderer.render_tools(sample_tools, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_tools(sample_tools, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "read_file" in output
            assert "write_file" in output
            assert "2" in output
            assert "1" in output

    def test_verbose_shows_details_across_all_renderers(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
        sample_tools: list[ToolCallInfo],
    ) -> None:
        """Verbose preset shows tool details across all renderers."""
        wide_console = Console(record=True, width=200)
        rich_out = rich_renderer.render_tools(sample_tools, VERBOSE, console=wide_console)
        plain_out = plain_renderer.render_tools(sample_tools, VERBOSE, file=io.StringIO())
        html_out = html_renderer.render_tools(sample_tools, VERBOSE)

        for output in (rich_out, plain_out, html_out):
            assert "a.txt" in output
            assert "content a" in output


class TestCrossRendererEmptyStates:
    """Verify all three renderers produce consistent empty-state messages."""

    def test_empty_stats_message_consistent(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """All renderers produce 'No messages recorded' for empty stats."""
        empty_stats = MessageStats()

        rich_out = rich_renderer.render_stats(empty_stats, DETAILED)
        plain_out = plain_renderer.render_stats(empty_stats, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_stats(empty_stats, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "No messages recorded" in output

    def test_empty_timeline_message_consistent(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """All renderers produce 'No conversation turns found' for empty timeline."""
        rich_out = rich_renderer.render_timeline([], DETAILED)
        plain_out = plain_renderer.render_timeline([], DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline([], DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "No conversation turns found" in output

    def test_empty_tools_message_consistent(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """All renderers produce 'No tool calls recorded' for empty tools."""
        rich_out = rich_renderer.render_tools([], DETAILED)
        plain_out = plain_renderer.render_tools([], DETAILED, file=io.StringIO())
        html_out = html_renderer.render_tools([], DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "No tool calls recorded" in output

    def test_empty_state_same_across_all_presets(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Empty state messages are the same regardless of preset."""
        empty_stats = MessageStats()

        for preset in (COMPACT, DETAILED, VERBOSE):
            rich_out = rich_renderer.render_stats(empty_stats, preset)
            plain_out = plain_renderer.render_stats(empty_stats, preset, file=io.StringIO())
            html_out = html_renderer.render_stats(empty_stats, preset)

            for output in (rich_out, plain_out, html_out):
                assert "No messages recorded" in output


# ---------------------------------------------------------------------------
# Edge cases: unusual Turn configurations
# ---------------------------------------------------------------------------


class TestTurnEdgeCases:
    """Edge cases for unusual Turn configurations not covered by individual tests."""

    def test_turn_with_only_assistant_content(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Turn with only assistant content (no user or system) renders cleanly."""
        turns = [Turn(index=0, assistant_content="I have a thought.")]

        rich_out = rich_renderer.render_timeline(turns, DETAILED)
        plain_out = plain_renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "Turn 0" in output
            assert "[Assistant]" in output
            assert "I have a thought." in output
            # Should not include other role labels.
            assert "[User]" not in output
            assert "[System]" not in output

    def test_turn_with_no_content(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Turn with no content at all (empty Turn) renders just the turn header."""
        turns = [Turn(index=0)]

        rich_out = rich_renderer.render_timeline(turns, DETAILED)
        plain_out = plain_renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "Turn 0" in output
            assert "[User]" not in output
            assert "[Assistant]" not in output
            assert "[System]" not in output

    def test_turn_with_only_tool_interactions(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Turn with only tool interactions and no text content."""
        turns = [
            Turn(
                index=0,
                tool_interactions=[
                    {
                        "tool_name": "search",
                        "tool_call_id": "call_1",
                        "arguments": {"q": "test"},
                        "result": "found",
                    },
                ],
            ),
        ]

        rich_out = rich_renderer.render_timeline(turns, DETAILED)
        plain_out = plain_renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "Turn 0" in output
            assert "search" in output

    def test_content_at_exact_truncation_boundary(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Content exactly at max_content_length should not be truncated."""
        exact_content = "A" * 300  # DETAILED.max_content_length = 300
        turns = [Turn(index=0, user_content=exact_content)]

        rich_out = rich_renderer.render_timeline(turns, DETAILED)
        plain_out = plain_renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "more characters)" not in output

    def test_content_one_char_over_boundary_is_truncated(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Content one char over max_content_length should be truncated."""
        over_content = "A" * 301  # One more than DETAILED max of 300
        turns = [Turn(index=0, user_content=over_content)]

        rich_out = rich_renderer.render_timeline(turns, DETAILED)
        plain_out = plain_renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "1 more characters)" in output


# ---------------------------------------------------------------------------
# Edge cases: unusual Stats configurations
# ---------------------------------------------------------------------------


class TestStatsEdgeCases:
    """Edge cases for unusual MessageStats configurations."""

    def test_single_role_stats(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Stats with a single role render correctly across all renderers."""
        stats = MessageStats(
            total_messages=5,
            messages_by_role={"assistant": 5},
            total_tokens=1000,
            tokens_by_role={"assistant": 1000},
        )

        rich_out = rich_renderer.render_stats(stats, DETAILED)
        plain_out = plain_renderer.render_stats(stats, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_stats(stats, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "assistant" in output
            assert "Total" in output
            # Should not contain other role names.
            assert "user" not in output.lower().replace("total", "").replace("average", "")

    def test_many_roles_stats(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Stats with 15 roles render without error."""
        roles = {f"role_{i}": i + 1 for i in range(15)}
        tokens = {f"role_{i}": (i + 1) * 100 for i in range(15)}
        total_msgs = sum(roles.values())
        total_toks = sum(tokens.values())

        stats = MessageStats(
            total_messages=total_msgs,
            messages_by_role=roles,
            total_tokens=total_toks,
            tokens_by_role=tokens,
        )

        rich_out = rich_renderer.render_stats(stats, DETAILED)
        plain_out = plain_renderer.render_stats(stats, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_stats(stats, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "role_0" in output
            assert "role_14" in output
            assert "Total" in output

    def test_zero_total_tokens_with_messages(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Stats with messages but zero tokens display correctly."""
        stats = MessageStats(
            total_messages=4,
            messages_by_role={"user": 2, "assistant": 2},
            total_tokens=0,
            tokens_by_role={"user": 0, "assistant": 0},
        )

        rich_out = rich_renderer.render_stats(stats, DETAILED)
        plain_out = plain_renderer.render_stats(stats, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_stats(stats, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "user" in output
            assert "assistant" in output
            assert "Average tokens/message" in output
            assert "0.0" in output

    def test_missing_token_role_defaults_to_zero(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Role present in messages_by_role but missing from tokens_by_role shows 0."""
        stats = MessageStats(
            total_messages=3,
            messages_by_role={"user": 1, "assistant": 2},
            total_tokens=500,
            tokens_by_role={"assistant": 500},  # user missing
        )

        rich_out = rich_renderer.render_stats(stats, DETAILED)
        plain_out = plain_renderer.render_stats(stats, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_stats(stats, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "user" in output
            assert "assistant" in output


# ---------------------------------------------------------------------------
# Edge cases: tool interactions
# ---------------------------------------------------------------------------


class TestToolInteractionEdgeCases:
    """Edge cases for tool interactions in timeline and tools rendering."""

    def test_tool_interaction_missing_tool_name_defaults_to_unknown(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Tool interaction without tool_name key defaults to 'unknown'."""
        turns = [
            Turn(
                index=0,
                user_content="Do something",
                tool_interactions=[
                    {
                        "tool_call_id": "call_1",
                        "arguments": {"x": 1},
                        "result": "done",
                    },
                ],
            ),
        ]

        rich_out = rich_renderer.render_timeline(turns, DETAILED)
        plain_out = plain_renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "unknown" in output

    def test_tool_interaction_with_empty_arguments(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Tool interaction with empty arguments dict renders without error."""
        turns = [
            Turn(
                index=0,
                user_content="Do something",
                tool_interactions=[
                    {
                        "tool_name": "simple_tool",
                        "tool_call_id": "call_1",
                        "arguments": {},
                        "result": "done",
                    },
                ],
            ),
        ]

        rich_out = rich_renderer.render_timeline(turns, VERBOSE)
        plain_out = plain_renderer.render_timeline(turns, VERBOSE, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, VERBOSE)

        for output in (rich_out, plain_out, html_out):
            assert "simple_tool" in output

    def test_tool_interaction_with_empty_result(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Tool interaction with empty result string renders without error."""
        turns = [
            Turn(
                index=0,
                user_content="Do something",
                tool_interactions=[
                    {
                        "tool_name": "void_tool",
                        "tool_call_id": "call_1",
                        "arguments": {"action": "run"},
                        "result": "",
                    },
                ],
            ),
        ]

        rich_out = rich_renderer.render_timeline(turns, VERBOSE)
        plain_out = plain_renderer.render_timeline(turns, VERBOSE, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, VERBOSE)

        for output in (rich_out, plain_out, html_out):
            assert "void_tool" in output
            assert "args:" in output

    def test_ten_tool_interactions_show_summary(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Exactly 10 tool interactions trigger the summary view."""
        interactions = [
            {
                "tool_name": f"tool_{i % 2}",
                "tool_call_id": f"call_{i}",
                "arguments": {"n": i},
                "result": f"result_{i}",
            }
            for i in range(10)
        ]
        turns = [
            Turn(
                index=0,
                user_content="Run many tools",
                tool_interactions=interactions,
            ),
        ]

        rich_out = rich_renderer.render_timeline(turns, DETAILED)
        plain_out = plain_renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "10 calls" in output

    def test_nine_tool_interactions_show_individual(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """Nine tool interactions should show individual tool names, not summary."""
        interactions = [
            {
                "tool_name": "my_tool",
                "tool_call_id": f"call_{i}",
                "arguments": {"n": i},
                "result": f"result_{i}",
            }
            for i in range(9)
        ]
        turns = [
            Turn(
                index=0,
                user_content="Run tools",
                tool_interactions=interactions,
            ),
        ]

        rich_out = rich_renderer.render_timeline(turns, DETAILED)
        plain_out = plain_renderer.render_timeline(turns, DETAILED, file=io.StringIO())
        html_out = html_renderer.render_timeline(turns, DETAILED)

        for output in (rich_out, plain_out, html_out):
            assert "my_tool" in output
            # Should not have summary format "N calls"
            assert "9 calls" not in output


# ---------------------------------------------------------------------------
# Edge cases: _format_tool_details with missing call IDs
# ---------------------------------------------------------------------------


class TestToolDetailsFallbacks:
    """Tests for tool detail rendering when call IDs are missing."""

    def test_rich_format_tool_details_missing_call_ids(self, rich_renderer: RichRenderer) -> None:
        """RichRenderer._format_tool_details uses [call N] fallback."""
        tool = ToolCallInfo(
            tool_name="test_tool",
            call_count=3,
            arguments=[{"a": 1}, {"a": 2}, {"a": 3}],
            results=["r1", "r2", "r3"],
            tool_call_ids=["id_0"],  # Only one ID for 3 calls
        )

        details = RichRenderer._format_tool_details(tool, VERBOSE)

        assert "[id_0]" in details
        assert "[call 1]" in details
        assert "[call 2]" in details

    def test_plain_tools_missing_call_ids_uses_fallback(
        self, plain_renderer: PlainTextRenderer
    ) -> None:
        """PlainTextRenderer uses [call N] fallback when tool_call_ids is short."""
        tool = ToolCallInfo(
            tool_name="test_tool",
            call_count=3,
            arguments=[{"a": 1}, {"a": 2}, {"a": 3}],
            results=["r1", "r2", "r3"],
            tool_call_ids=["id_0"],  # Only one ID for 3 calls
        )

        output = plain_renderer.render_tools([tool], VERBOSE, file=io.StringIO())

        assert "[id_0]" in output
        assert "[call 1]" in output
        assert "[call 2]" in output

    def test_html_tools_missing_call_ids_uses_fallback(self, html_renderer: HtmlRenderer) -> None:
        """HtmlRenderer uses [call N] fallback when tool_call_ids is short."""
        tool = ToolCallInfo(
            tool_name="test_tool",
            call_count=3,
            arguments=[{"a": 1}, {"a": 2}, {"a": 3}],
            results=["r1", "r2", "r3"],
            tool_call_ids=["id_0"],  # Only one ID for 3 calls
        )

        output = html_renderer.render_tools([tool], VERBOSE)

        assert "[id_0]" in output
        assert "[call 1]" in output
        assert "[call 2]" in output

    def test_rich_format_tool_details_empty_call_ids_list(
        self, rich_renderer: RichRenderer
    ) -> None:
        """RichRenderer._format_tool_details handles empty tool_call_ids list."""
        tool = ToolCallInfo(
            tool_name="test_tool",
            call_count=2,
            arguments=[{"a": 1}, {"a": 2}],
            results=["r1", "r2"],
            tool_call_ids=[],
        )

        details = RichRenderer._format_tool_details(tool, VERBOSE)

        assert "[call 0]" in details
        assert "[call 1]" in details


# ---------------------------------------------------------------------------
# Edge cases: tool arg truncation
# ---------------------------------------------------------------------------


class TestToolArgTruncation:
    """Tests for tool argument truncation at boundaries."""

    def test_arg_at_exact_max_tool_arg_length_not_truncated(
        self, plain_renderer: PlainTextRenderer
    ) -> None:
        """Tool arg string exactly at max_tool_arg_length is not truncated."""
        exact_arg = "x" * 200  # DETAILED.max_tool_arg_length = 200
        tool = ToolCallInfo(
            tool_name="test_tool",
            call_count=1,
            arguments=[{"data": exact_arg}],
            results=["ok"],
            tool_call_ids=["call_1"],
        )

        output = plain_renderer.render_tools([tool], VERBOSE, file=io.StringIO())

        # The JSON-serialized arg will be longer than 200 due to {"data": "..."}
        # But test that truncation indicator appears only when over the limit
        assert "test_tool" in output

    def test_arg_over_max_tool_arg_length_shows_truncation(
        self, plain_renderer: PlainTextRenderer
    ) -> None:
        """Tool arg string over max_tool_arg_length shows truncation indicator."""
        long_arg = "x" * 600
        tool = ToolCallInfo(
            tool_name="test_tool",
            call_count=1,
            arguments=[{"data": long_arg}],
            results=["ok"],
            tool_call_ids=["call_1"],
        )

        # Use VERBOSE (max_tool_arg_length=500) with details enabled
        output = plain_renderer.render_tools([tool], VERBOSE, file=io.StringIO())

        assert "more characters)" in output


# ---------------------------------------------------------------------------
# Edge cases: _truncate_str helper
# ---------------------------------------------------------------------------


class TestTruncateStrHelper:
    """Tests for the _truncate_str static method on renderers."""

    def test_rich_truncate_str_none_max_returns_full(self) -> None:
        """RichRenderer._truncate_str with max_length=None returns full text."""
        result = RichRenderer._truncate_str("hello world", None)
        assert result == "hello world"

    def test_rich_truncate_str_at_boundary(self) -> None:
        """RichRenderer._truncate_str at exact boundary returns full text."""
        result = RichRenderer._truncate_str("hello", 5)
        assert result == "hello"

    def test_rich_truncate_str_over_boundary(self) -> None:
        """RichRenderer._truncate_str over boundary truncates with indicator."""
        result = RichRenderer._truncate_str("hello world", 5)
        assert result == "hello... (6 more characters)"

    def test_plain_truncate_str_none_max_returns_full(self) -> None:
        """PlainTextRenderer._truncate_str with max_length=None returns full text."""
        result = PlainTextRenderer._truncate_str("hello world", None)
        assert result == "hello world"

    def test_plain_truncate_str_at_boundary(self) -> None:
        """PlainTextRenderer._truncate_str at exact boundary returns full text."""
        result = PlainTextRenderer._truncate_str("hello", 5)
        assert result == "hello"

    def test_plain_truncate_str_over_boundary(self) -> None:
        """PlainTextRenderer._truncate_str over boundary truncates with indicator."""
        result = PlainTextRenderer._truncate_str("hello world", 5)
        assert result == "hello... (6 more characters)"

    def test_html_truncate_str_none_max_returns_full(self) -> None:
        """HtmlRenderer._truncate_str with max_length=None returns full text."""
        result = HtmlRenderer._truncate_str("hello world", None)
        assert result == "hello world"

    def test_html_truncate_str_over_boundary(self) -> None:
        """HtmlRenderer._truncate_str over boundary truncates with indicator."""
        result = HtmlRenderer._truncate_str("hello world", 5)
        assert result == "hello... (6 more characters)"

    def test_truncate_str_empty_text(self) -> None:
        """_truncate_str with empty text returns empty string."""
        result = RichRenderer._truncate_str("", 10)
        assert result == ""


# ---------------------------------------------------------------------------
# Edge cases: _truncate content helper
# ---------------------------------------------------------------------------


class TestTruncateContentHelper:
    """Tests for the _truncate method on renderers."""

    def test_expand_true_bypasses_truncation(self, rich_renderer: RichRenderer) -> None:
        """_truncate returns full content when expand=True."""
        preset = get_preset("verbose")  # expand=True
        result = rich_renderer._truncate("A" * 1000, preset)
        assert len(result) == 1000
        assert "more characters)" not in result

    def test_max_content_length_none_bypasses_truncation(self, rich_renderer: RichRenderer) -> None:
        """_truncate returns full content when max_content_length=None."""
        preset = get_preset("detailed", max_content_length=None)
        result = rich_renderer._truncate("A" * 1000, preset)
        assert len(result) == 1000
        assert "more characters)" not in result

    def test_short_content_not_truncated(self, rich_renderer: RichRenderer) -> None:
        """_truncate returns full content when shorter than limit."""
        result = rich_renderer._truncate("short", DETAILED)
        assert result == "short"


# ---------------------------------------------------------------------------
# Standalone function: format routing through all paths
# ---------------------------------------------------------------------------


class TestStandaloneFunctionFullRouting:
    """Tests for standalone function format/renderer routing."""

    def test_print_stats_routes_to_plain_renderer(self) -> None:
        """print_stats with format='plain' uses PlainTextRenderer."""
        stats = MessageStats(
            total_messages=1,
            messages_by_role={"user": 1},
            total_tokens=10,
            tokens_by_role={"user": 10},
        )
        result = print_stats(stats, format="plain")
        assert isinstance(result, str)
        assert "Message Statistics" in result
        # Plain text should not contain HTML tags
        assert "<table>" not in result

    def test_print_timeline_routes_to_html_renderer(self) -> None:
        """print_timeline with format='html' uses HtmlRenderer."""
        turns = [Turn(index=0, user_content="Hello")]
        result = print_timeline(turns, format="html")
        assert "<section>" in result
        assert "<h3>Turn 0</h3>" in result

    def test_print_tools_routes_to_rich_renderer(self) -> None:
        """print_tools with default format uses RichRenderer."""
        tools = [ToolCallInfo(tool_name="test_tool", call_count=1)]
        result = print_tools(tools)
        assert isinstance(result, str)
        assert "test_tool" in result

    def test_print_stats_preset_override_integration(self) -> None:
        """print_stats preset override affects output content."""
        stats = MessageStats(
            total_messages=2,
            messages_by_role={"user": 1, "assistant": 1},
            total_tokens=100,
            tokens_by_role={"user": 50, "assistant": 50},
        )
        # Compact hides tokens, but override to show them.
        result = print_stats(stats, preset="compact", format="html", show_tokens=True)
        assert "<th>Tokens</th>" in result

    def test_print_timeline_with_all_options(self) -> None:
        """print_timeline with preset, format, and options all specified."""
        turns = [
            Turn(index=0, user_content="A" * 500),
            Turn(index=1, user_content="B" * 500),
        ]
        result = print_timeline(
            turns, preset="compact", format="html", limit=1, max_content_length=50
        )
        assert "Turn 0" in result
        assert "1 more turn(s) not shown" in result
        assert "more characters)" in result

    def test_print_tools_with_all_options(self) -> None:
        """print_tools with preset, format, and options all specified."""
        tools = [
            ToolCallInfo(
                tool_name="search",
                call_count=2,
                arguments=[{"q": "a"}, {"q": "b"}],
                results=["found a", "found b"],
                tool_call_ids=["c1", "c2"],
            ),
        ]
        result = print_tools(tools, preset="compact", format="html", show_tool_details=True)
        assert "search" in result
        assert "<th>Details</th>" in result


# ---------------------------------------------------------------------------
# Standalone function: error handling
# ---------------------------------------------------------------------------


class TestStandaloneFunctionErrors:
    """Error handling tests for standalone functions."""

    def test_invalid_format_in_print_stats(self) -> None:
        """print_stats raises ValueError for unknown format."""
        stats = MessageStats(total_messages=1, messages_by_role={"user": 1})
        with pytest.raises(ValueError, match="Unknown format"):
            print_stats(stats, format="pdf")

    def test_invalid_format_in_print_timeline(self) -> None:
        """print_timeline raises ValueError for unknown format."""
        with pytest.raises(ValueError, match="Unknown format"):
            print_timeline([], format="latex")

    def test_invalid_format_in_print_tools(self) -> None:
        """print_tools raises ValueError for unknown format."""
        with pytest.raises(ValueError, match="Unknown format"):
            print_tools([], format="yaml")

    def test_invalid_preset_in_print_stats(self) -> None:
        """print_stats raises ValueError for unknown preset."""
        stats = MessageStats(total_messages=1, messages_by_role={"user": 1})
        with pytest.raises(ValueError, match="Unknown preset name"):
            print_stats(stats, preset="ultra")

    def test_invalid_preset_in_print_timeline(self) -> None:
        """print_timeline raises ValueError for unknown preset."""
        with pytest.raises(ValueError, match="Unknown preset name"):
            print_timeline([], preset="minimal")

    def test_invalid_preset_in_print_tools(self) -> None:
        """print_tools raises ValueError for unknown preset."""
        with pytest.raises(ValueError, match="Unknown preset name"):
            print_tools([], preset="extra-detailed")


# ---------------------------------------------------------------------------
# Integration: MessageQuery end-to-end
# ---------------------------------------------------------------------------


class TestMessageQueryIntegration:
    """End-to-end integration tests for MessageQuery print methods."""

    def test_message_query_print_stats_all_formats(self) -> None:
        """MessageQuery.print_stats works with all three formats."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        mq = MessageQuery(messages)

        for fmt in ("rich", "plain", "html"):
            result = mq.print_stats(format=fmt)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_message_query_print_timeline_all_formats(self) -> None:
        """MessageQuery.print_timeline works with all three formats."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        mq = MessageQuery(messages)

        for fmt in ("rich", "plain", "html"):
            result = mq.print_timeline(format=fmt)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_message_query_print_tools_all_formats(self) -> None:
        """MessageQuery.print_tools works with all three formats."""
        messages = [
            {"role": "user", "content": "Read file.txt"},
            {
                "role": "assistant",
                "content": "Reading...",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "file.txt"}',
                        },
                    },
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": "File contents",
            },
            {"role": "assistant", "content": "Here are the contents."},
        ]
        mq = MessageQuery(messages)

        for fmt in ("rich", "plain", "html"):
            result = mq.print_tools(format=fmt)
            assert isinstance(result, str)

    def test_message_query_print_all_presets(self) -> None:
        """MessageQuery print methods work with all presets."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        mq = MessageQuery(messages)

        for preset_name in ("compact", "detailed", "verbose"):
            stats_result = mq.print_stats(preset=preset_name, format="html")
            timeline_result = mq.print_timeline(preset=preset_name, format="html")
            tools_result = mq.print_tools(preset=preset_name, format="html")

            assert isinstance(stats_result, str)
            assert isinstance(timeline_result, str)
            assert isinstance(tools_result, str)

    def test_message_query_print_stats_matches_standalone(self) -> None:
        """MessageQuery.print_stats output matches standalone function output."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        mq = MessageQuery(messages)
        stats = mq.stats()

        for fmt in ("rich", "plain", "html"):
            method_result = mq.print_stats(format=fmt)
            standalone_result = print_stats(stats, format=fmt)
            assert method_result == standalone_result

    def test_empty_message_query_print_methods(self) -> None:
        """All print methods work on empty MessageQuery."""
        mq = MessageQuery([])

        stats_result = mq.print_stats(format="html")
        timeline_result = mq.print_timeline(format="html")
        tools_result = mq.print_tools(format="html")

        assert "No messages recorded" in stats_result
        assert "No conversation turns found" in timeline_result
        assert "No tool calls recorded" in tools_result


# ---------------------------------------------------------------------------
# Preset system: additional edge cases
# ---------------------------------------------------------------------------


class TestPresetEdgeCases:
    """Additional preset system edge cases."""

    def test_get_preset_returns_frozen_instance(self) -> None:
        """get_preset returns a frozen (immutable) DisplayPreset."""
        preset = get_preset("compact")
        with pytest.raises(AttributeError):
            preset.show_tokens = True  # type: ignore[misc]

    def test_get_preset_override_returns_frozen_instance(self) -> None:
        """get_preset with overrides returns a frozen (immutable) DisplayPreset."""
        preset = get_preset("compact", show_tokens=True)
        with pytest.raises(AttributeError):
            preset.expand = True  # type: ignore[misc]

    def test_all_preset_fields_overridable(self) -> None:
        """Every field of DisplayPreset can be overridden via get_preset."""
        preset = get_preset(
            "compact",
            show_tokens=True,
            max_content_length=999,
            expand=True,
            show_tool_details=True,
            max_tool_arg_length=888,
            limit=77,
        )

        assert preset.show_tokens is True
        assert preset.max_content_length == 999
        assert preset.expand is True
        assert preset.show_tool_details is True
        assert preset.max_tool_arg_length == 888
        assert preset.limit == 77

    def test_custom_preset_object_works_with_renderers(
        self,
        rich_renderer: RichRenderer,
        plain_renderer: PlainTextRenderer,
        html_renderer: HtmlRenderer,
    ) -> None:
        """A manually constructed DisplayPreset works with all renderers."""
        custom = DisplayPreset(
            show_tokens=True,
            max_content_length=50,
            expand=False,
            show_tool_details=False,
            max_tool_arg_length=100,
            limit=5,
        )

        stats = MessageStats(
            total_messages=2,
            messages_by_role={"user": 1, "assistant": 1},
            total_tokens=100,
            tokens_by_role={"user": 50, "assistant": 50},
        )

        rich_out = rich_renderer.render_stats(stats, custom)
        plain_out = plain_renderer.render_stats(stats, custom, file=io.StringIO())
        html_out = html_renderer.render_stats(stats, custom)

        for output in (rich_out, plain_out, html_out):
            assert "Message Statistics" in output


# ---------------------------------------------------------------------------
# RichRenderer: renderable methods (for __rich_console__ protocol)
# ---------------------------------------------------------------------------


class TestRenderablesMethods:
    """Tests for RichRenderer renderable helper methods."""

    def test_render_stats_renderables_returns_list(
        self, rich_renderer: RichRenderer, sample_stats: MessageStats
    ) -> None:
        """render_stats_renderables returns a list of Rich objects."""
        renderables = rich_renderer.render_stats_renderables(sample_stats, DETAILED)
        assert isinstance(renderables, list)
        assert len(renderables) > 0

    def test_render_stats_renderables_empty(self, rich_renderer: RichRenderer) -> None:
        """render_stats_renderables returns Panel for empty stats."""
        renderables = rich_renderer.render_stats_renderables(MessageStats(), DETAILED)
        assert isinstance(renderables, list)
        assert len(renderables) == 1

    def test_render_tools_renderables_returns_list(
        self, rich_renderer: RichRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """render_tools_renderables returns a list of Rich objects."""
        renderables = rich_renderer.render_tools_renderables(sample_tools, DETAILED)
        assert isinstance(renderables, list)
        assert len(renderables) > 0

    def test_render_tools_renderables_empty(self, rich_renderer: RichRenderer) -> None:
        """render_tools_renderables returns Panel for empty tools."""
        renderables = rich_renderer.render_tools_renderables([], DETAILED)
        assert isinstance(renderables, list)
        assert len(renderables) == 1

    def test_render_turn_renderable_returns_panel(self, rich_renderer: RichRenderer) -> None:
        """render_turn_renderable returns a Rich Panel."""
        from rich.panel import Panel

        turn = Turn(index=0, user_content="Hello")
        renderable = rich_renderer.render_turn_renderable(turn, DETAILED)
        assert isinstance(renderable, Panel)


# ---------------------------------------------------------------------------
# RichRenderer: _ensure_console helper
# ---------------------------------------------------------------------------


class TestEnsureConsole:
    """Tests for RichRenderer._ensure_console static method."""

    def test_none_creates_new_console(self) -> None:
        """Passing None creates a new recording Console."""
        console = RichRenderer._ensure_console(None)
        assert isinstance(console, Console)

    def test_provided_console_creates_new_with_same_width(self) -> None:
        """Passing an existing console creates a new one with matching width."""
        original = Console(record=True, width=150)
        result = RichRenderer._ensure_console(original)

        assert result is not original
        assert result.width == 150

    def test_returned_console_is_recording(self) -> None:
        """Returned console always has record=True."""
        console = RichRenderer._ensure_console(None)
        # Can call export_text without error = recording is enabled
        text = console.export_text()
        assert isinstance(text, str)


# ---------------------------------------------------------------------------
# PlainTextRenderer: file parameter behavior
# ---------------------------------------------------------------------------


class TestPlainTextRendererFileParam:
    """Tests for PlainTextRenderer file parameter handling."""

    def test_stats_writes_to_custom_file(self, plain_renderer: PlainTextRenderer) -> None:
        """render_stats writes to provided file object."""
        buf = io.StringIO()
        stats = MessageStats(
            total_messages=2,
            messages_by_role={"user": 1, "assistant": 1},
        )
        result = plain_renderer.render_stats(stats, COMPACT, file=buf)

        # Return value and file contents should match
        file_contents = buf.getvalue()
        assert result in file_contents

    def test_timeline_writes_to_custom_file(self, plain_renderer: PlainTextRenderer) -> None:
        """render_timeline writes to provided file object."""
        buf = io.StringIO()
        turns = [Turn(index=0, user_content="Hello")]
        result = plain_renderer.render_timeline(turns, DETAILED, file=buf)

        file_contents = buf.getvalue()
        assert result in file_contents

    def test_tools_writes_to_custom_file(self, plain_renderer: PlainTextRenderer) -> None:
        """render_tools writes to provided file object."""
        buf = io.StringIO()
        tools = [ToolCallInfo(tool_name="test", call_count=1)]
        result = plain_renderer.render_tools(tools, DETAILED, file=buf)

        file_contents = buf.getvalue()
        assert result in file_contents


# ---------------------------------------------------------------------------
# HtmlRenderer: additional HTML structure tests
# ---------------------------------------------------------------------------


class TestHtmlStructureAdditional:
    """Additional HTML structure tests not covered by test_html_renderer.py."""

    def test_tools_verbose_uses_code_elements(self, html_renderer: HtmlRenderer) -> None:
        """Verbose tool details use <code> elements for args and results."""
        tools = [
            ToolCallInfo(
                tool_name="test_tool",
                call_count=1,
                arguments=[{"key": "value"}],
                results=["result_value"],
                tool_call_ids=["call_1"],
            ),
        ]
        output = html_renderer.render_tools(tools, VERBOSE)
        assert "<code>" in output
        assert "</code>" in output

    def test_timeline_verbose_uses_code_for_tool_args(self, html_renderer: HtmlRenderer) -> None:
        """Verbose timeline tool details use <code> elements."""
        turns = [
            Turn(
                index=0,
                user_content="Do it",
                tool_interactions=[
                    {
                        "tool_name": "my_tool",
                        "tool_call_id": "call_1",
                        "arguments": {"key": "value"},
                        "result": "done",
                    },
                ],
            ),
        ]
        output = html_renderer.render_timeline(turns, VERBOSE)
        assert "<code>" in output

    def test_tools_verbose_escapes_detail_content(self, html_renderer: HtmlRenderer) -> None:
        """Verbose tool details escape HTML in args and results."""
        tools = [
            ToolCallInfo(
                tool_name="safe_tool",
                call_count=1,
                arguments=[{"html": "<b>bold</b>"}],
                results=["<script>alert(1)</script>"],
                tool_call_ids=["call_1"],
            ),
        ]
        output = html_renderer.render_tools(tools, VERBOSE)
        assert "<b>bold</b>" not in output
        assert "&lt;b&gt;bold&lt;/b&gt;" in output
        assert "<script>" not in output

    def test_timeline_section_per_turn(self, html_renderer: HtmlRenderer) -> None:
        """Each turn gets its own <section> element."""
        turns = [
            Turn(index=0, user_content="First"),
            Turn(index=1, user_content="Second"),
            Turn(index=2, user_content="Third"),
        ]
        output = html_renderer.render_timeline(turns, DETAILED)

        assert output.count("<section>") == 3
        assert output.count("</section>") == 3
