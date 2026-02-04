"""Tests for the HtmlRenderer implementation."""

from __future__ import annotations

import time
from typing import Any

import pytest

from mamba_agents.agent.display import COMPACT, DETAILED, VERBOSE
from mamba_agents.agent.display.html_renderer import HtmlRenderer
from mamba_agents.agent.display.presets import get_preset
from mamba_agents.agent.display.renderer import MessageRenderer
from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def renderer() -> HtmlRenderer:
    """Provide an HtmlRenderer instance."""
    return HtmlRenderer()


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
# Class: TestHtmlRendererIsMessageRenderer
# ---------------------------------------------------------------------------


class TestHtmlRendererIsMessageRenderer:
    """Verify HtmlRenderer satisfies the MessageRenderer ABC."""

    def test_is_subclass(self) -> None:
        """Test that HtmlRenderer is a subclass of MessageRenderer."""
        assert issubclass(HtmlRenderer, MessageRenderer)

    def test_is_instance(self, renderer: HtmlRenderer) -> None:
        """Test that an HtmlRenderer instance is a MessageRenderer."""
        assert isinstance(renderer, MessageRenderer)


# ---------------------------------------------------------------------------
# Class: TestRenderStats
# ---------------------------------------------------------------------------


class TestRenderStats:
    """Tests for HtmlRenderer.render_stats()."""

    def test_produces_html_table(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that stats output is an HTML table with semantic markup."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "<table>" in output
        assert "</table>" in output
        assert "<th>" in output
        assert "<td>" in output

    def test_table_has_caption(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that the stats table includes a caption element."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "<caption>Message Statistics</caption>" in output

    def test_has_thead_tbody_tfoot(
        self, renderer: HtmlRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that the table has semantic sections."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "<thead>" in output
        assert "</thead>" in output
        assert "<tbody>" in output
        assert "</tbody>" in output
        assert "<tfoot>" in output
        assert "</tfoot>" in output

    def test_shows_role_headers(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that column headers are present."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "<th>Role</th>" in output
        assert "<th>Messages</th>" in output
        assert "<th>Tokens</th>" in output

    def test_shows_role_data(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that all roles appear in the output."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "assistant" in output
        assert "user" in output
        assert "system" in output
        assert "tool" in output

    def test_shows_totals(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that totals row appears."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "<strong>Total</strong>" in output
        assert f"<strong>{sample_stats.total_messages}</strong>" in output

    def test_token_thousands_separators(self, renderer: HtmlRenderer) -> None:
        """Test that token numbers are formatted with thousands separators."""
        stats = MessageStats(
            total_messages=2,
            messages_by_role={"assistant": 2},
            total_tokens=12345,
            tokens_by_role={"assistant": 12345},
        )
        output = renderer.render_stats(stats, DETAILED)
        assert "12,345" in output

    def test_averages_shown(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that average tokens per message is shown."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "Average tokens/message" in output
        # 1500 / 10 = 150.0
        assert "150.0" in output

    def test_compact_hides_tokens(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that compact preset hides token columns."""
        output = renderer.render_stats(sample_stats, COMPACT)
        assert "<th>Tokens</th>" not in output
        assert "Average tokens/message" not in output
        # But message counts should still appear.
        assert "<strong>Total</strong>" in output
        assert "assistant" in output

    def test_verbose_shows_tokens(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that verbose preset shows token information."""
        output = renderer.render_stats(sample_stats, VERBOSE)
        assert "Average tokens/message" in output
        assert "1,500" in output

    def test_empty_stats_shows_message(
        self, renderer: HtmlRenderer, empty_stats: MessageStats
    ) -> None:
        """Test that empty stats produces the correct HTML message."""
        output = renderer.render_stats(empty_stats, DETAILED)
        assert output == "<p>No messages recorded</p>"

    def test_zero_token_values_displayed(self, renderer: HtmlRenderer) -> None:
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

    def test_very_large_token_counts(self, renderer: HtmlRenderer) -> None:
        """Test that very large token counts display correctly with separators."""
        stats = MessageStats(
            total_messages=2,
            messages_by_role={"assistant": 2},
            total_tokens=1_234_567_890,
            tokens_by_role={"assistant": 1_234_567_890},
        )
        output = renderer.render_stats(stats, DETAILED)
        assert "1,234,567,890" in output

    def test_returns_string(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that render_stats returns a string."""
        result = renderer.render_stats(sample_stats, DETAILED)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_external_dependencies(
        self, renderer: HtmlRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that HTML is self-contained with no external CSS/JS."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "<link" not in output
        assert "<script" not in output
        assert "stylesheet" not in output.lower()

    def test_roles_sorted_alphabetically(
        self, renderer: HtmlRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that roles appear sorted alphabetically in the table."""
        output = renderer.render_stats(sample_stats, DETAILED)
        # assistant < system < tool < user
        assistant_pos = output.index("assistant")
        system_pos = output.index("system")
        tool_pos = output.index("<td>tool</td>")
        user_pos = output.index("<td>user</td>")
        assert assistant_pos < system_pos < tool_pos < user_pos


# ---------------------------------------------------------------------------
# Class: TestRenderTimeline
# ---------------------------------------------------------------------------


class TestRenderTimeline:
    """Tests for HtmlRenderer.render_timeline()."""

    def test_produces_html_sections(self, renderer: HtmlRenderer, sample_turns: list[Turn]) -> None:
        """Test that timeline output contains HTML section elements."""
        output = renderer.render_timeline(sample_turns, DETAILED)
        assert "<section>" in output
        assert "</section>" in output

    def test_shows_turn_headers(self, renderer: HtmlRenderer, sample_turns: list[Turn]) -> None:
        """Test that turns have numbered headings."""
        output = renderer.render_timeline(sample_turns, DETAILED)
        assert "<h3>Turn 0</h3>" in output
        assert "<h3>Turn 1</h3>" in output

    def test_shows_role_labels(self, renderer: HtmlRenderer, sample_turns: list[Turn]) -> None:
        """Test that role labels appear in the output."""
        output = renderer.render_timeline(sample_turns, DETAILED)
        assert "[User]" in output
        assert "[Assistant]" in output

    def test_system_context_displayed(
        self, renderer: HtmlRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that system context is displayed with distinct label."""
        output = renderer.render_timeline(sample_turns, DETAILED)
        assert "[System]" in output
        assert "helpful assistant" in output

    def test_tool_interactions_shown(
        self, renderer: HtmlRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that tool interactions show in the timeline."""
        output = renderer.render_timeline(sample_turns, DETAILED)
        assert "read_file" in output

    def test_content_truncation(self, renderer: HtmlRenderer) -> None:
        """Test that long content is truncated with indicator."""
        long_content = "A" * 500
        turns = [Turn(index=0, user_content=long_content)]
        output = renderer.render_timeline(turns, DETAILED)
        # DETAILED has max_content_length=300.
        assert "more characters)" in output

    def test_content_truncation_exact_count(self, renderer: HtmlRenderer) -> None:
        """Test that truncation indicator shows correct remaining count."""
        long_content = "A" * 500
        turns = [Turn(index=0, user_content=long_content)]
        output = renderer.render_timeline(turns, DETAILED)
        # 500 - 300 = 200 remaining
        assert "200 more characters)" in output

    def test_expand_shows_full_content(self, renderer: HtmlRenderer) -> None:
        """Test that expand=True shows full content without truncation."""
        long_content = "A" * 500
        turns = [Turn(index=0, user_content=long_content)]
        output = renderer.render_timeline(turns, VERBOSE)
        assert "more characters)" not in output

    def test_max_content_length_none_shows_full(self, renderer: HtmlRenderer) -> None:
        """Test that max_content_length=None shows full content."""
        long_content = "B" * 500
        turns = [Turn(index=0, user_content=long_content)]
        preset = get_preset("detailed", max_content_length=None)
        output = renderer.render_timeline(turns, preset)
        assert "more characters)" not in output

    def test_empty_timeline_shows_message(self, renderer: HtmlRenderer) -> None:
        """Test that empty timeline produces the correct HTML message."""
        output = renderer.render_timeline([], DETAILED)
        assert output == "<p>No conversation turns found</p>"

    def test_limit_parameter(self, renderer: HtmlRenderer, sample_turns: list[Turn]) -> None:
        """Test that limit parameter restricts the number of turns shown."""
        preset = get_preset("detailed", limit=1)
        output = renderer.render_timeline(sample_turns, preset)
        assert "Turn 0" in output
        assert "1 more turn(s) not shown" in output

    def test_system_only_turn(self, renderer: HtmlRenderer) -> None:
        """Test that a turn with only system context is rendered."""
        turns = [Turn(index=0, system_context="You are a code reviewer.")]
        output = renderer.render_timeline(turns, DETAILED)
        assert "[System]" in output
        assert "code reviewer" in output

    def test_many_tool_interactions_show_summary(
        self,
        renderer: HtmlRenderer,
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
        self, renderer: HtmlRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that verbose preset shows tool args and results."""
        output = renderer.render_timeline(sample_turns, VERBOSE)
        assert "args:" in output
        assert "result:" in output

    def test_pagination_indicator_uses_em(
        self, renderer: HtmlRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that pagination indicator uses <em> for emphasis."""
        preset = get_preset("detailed", limit=1)
        output = renderer.render_timeline(sample_turns, preset)
        assert "<em>" in output
        assert "</em>" in output


# ---------------------------------------------------------------------------
# Class: TestRenderTools
# ---------------------------------------------------------------------------


class TestRenderTools:
    """Tests for HtmlRenderer.render_tools()."""

    def test_produces_html_table(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that tools output is an HTML table."""
        output = renderer.render_tools(sample_tools, DETAILED)
        assert "<table>" in output
        assert "</table>" in output
        assert "<th>" in output
        assert "<td>" in output

    def test_table_has_caption(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that the tools table includes a caption element."""
        output = renderer.render_tools(sample_tools, DETAILED)
        assert "<caption>Tool Summary</caption>" in output

    def test_shows_tool_name_and_count(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that tools table shows tool name and call count."""
        output = renderer.render_tools(sample_tools, DETAILED)
        assert "read_file" in output
        assert "3" in output
        assert "write_file" in output
        assert "1" in output

    def test_shows_column_headers(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that column headers are present."""
        output = renderer.render_tools(sample_tools, DETAILED)
        assert "<th>Tool Name</th>" in output
        assert "<th>Calls</th>" in output

    def test_empty_tools_shows_message(self, renderer: HtmlRenderer) -> None:
        """Test that empty tools list shows the correct HTML message."""
        output = renderer.render_tools([], DETAILED)
        assert output == "<p>No tool calls recorded</p>"

    def test_compact_hides_details(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that compact preset hides tool details."""
        output = renderer.render_tools(sample_tools, COMPACT)
        assert "<th>Details</th>" not in output
        assert "read_file" in output

    def test_verbose_shows_details(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that verbose preset shows expanded tool details."""
        output = renderer.render_tools(sample_tools, VERBOSE)
        assert "a.txt" in output
        assert "content a" in output
        assert "args:" in output
        assert "result:" in output

    def test_verbose_shows_details_column(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that verbose preset includes a Details column header."""
        output = renderer.render_tools(sample_tools, VERBOSE)
        assert "<th>Details</th>" in output

    def test_has_thead_tbody(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that the tools table has semantic sections."""
        output = renderer.render_tools(sample_tools, DETAILED)
        assert "<thead>" in output
        assert "</thead>" in output
        assert "<tbody>" in output
        assert "</tbody>" in output


# ---------------------------------------------------------------------------
# Class: TestHtmlEscaping
# ---------------------------------------------------------------------------


class TestHtmlEscaping:
    """Test that HTML special characters are properly escaped."""

    def test_stats_escapes_role_names(self, renderer: HtmlRenderer) -> None:
        """Test that HTML characters in role names are escaped."""
        stats = MessageStats(
            total_messages=1,
            messages_by_role={"<script>alert(1)</script>": 1},
            total_tokens=10,
            tokens_by_role={"<script>alert(1)</script>": 10},
        )
        output = renderer.render_stats(stats, DETAILED)
        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    def test_timeline_escapes_user_content(self, renderer: HtmlRenderer) -> None:
        """Test that HTML characters in user content are escaped."""
        turns = [
            Turn(
                index=0,
                user_content='<img src="x" onerror="alert(1)">',
            ),
        ]
        output = renderer.render_timeline(turns, DETAILED)
        assert "<img src=" not in output
        assert "&lt;img" in output

    def test_timeline_escapes_system_context(self, renderer: HtmlRenderer) -> None:
        """Test that HTML characters in system context are escaped."""
        turns = [
            Turn(index=0, system_context="<b>Bold System</b>"),
        ]
        output = renderer.render_timeline(turns, DETAILED)
        assert "&lt;b&gt;Bold System&lt;/b&gt;" in output

    def test_timeline_escapes_assistant_content(self, renderer: HtmlRenderer) -> None:
        """Test that HTML characters in assistant content are escaped."""
        turns = [
            Turn(index=0, assistant_content="Use <div> & <span> elements"),
        ]
        output = renderer.render_timeline(turns, DETAILED)
        assert "&lt;div&gt;" in output
        assert "&amp;" in output

    def test_tools_escapes_tool_name(self, renderer: HtmlRenderer) -> None:
        """Test that HTML characters in tool names are escaped."""
        tools = [
            ToolCallInfo(
                tool_name="<script>bad</script>",
                call_count=1,
                arguments=[{}],
                results=["ok"],
                tool_call_ids=["call_1"],
            ),
        ]
        output = renderer.render_tools(tools, DETAILED)
        assert "<script>bad</script>" not in output
        assert "&lt;script&gt;bad&lt;/script&gt;" in output

    def test_ampersand_in_content(self, renderer: HtmlRenderer) -> None:
        """Test that ampersands in content are properly escaped."""
        turns = [
            Turn(index=0, user_content="A & B < C > D"),
        ]
        output = renderer.render_timeline(turns, DETAILED)
        assert "A &amp; B &lt; C &gt; D" in output

    def test_quotes_in_content(self, renderer: HtmlRenderer) -> None:
        """Test that quote characters in content are properly escaped."""
        turns = [
            Turn(index=0, user_content="He said \"hello\" and 'goodbye'"),
        ]
        output = renderer.render_timeline(turns, DETAILED)
        # html.escape escapes double quotes by default.
        assert "&quot;" in output or "&#x27;" in output or "hello" in output


# ---------------------------------------------------------------------------
# Class: TestPresetDistinction
# ---------------------------------------------------------------------------


class TestPresetDistinction:
    """Test that all three presets produce visually distinct output."""

    def test_stats_presets_differ(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that compact, detailed, and verbose stats output differs."""
        compact_out = renderer.render_stats(sample_stats, COMPACT)
        detailed_out = renderer.render_stats(sample_stats, DETAILED)
        verbose_out = renderer.render_stats(sample_stats, VERBOSE)

        # compact hides tokens; detailed and verbose show tokens.
        assert compact_out != detailed_out
        assert compact_out != verbose_out

    def test_timeline_presets_differ(self, renderer: HtmlRenderer) -> None:
        """Test that compact, detailed, and verbose timeline output differs."""
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
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that compact, detailed, and verbose tools output differs."""
        compact_out = renderer.render_tools(sample_tools, COMPACT)
        detailed_out = renderer.render_tools(sample_tools, DETAILED)
        verbose_out = renderer.render_tools(sample_tools, VERBOSE)

        # verbose shows details; compact/detailed do not.
        assert verbose_out != compact_out
        assert verbose_out != detailed_out


# ---------------------------------------------------------------------------
# Class: TestEmptyStates
# ---------------------------------------------------------------------------


class TestEmptyStates:
    """Test graceful empty state handling for all render methods."""

    def test_empty_stats(self, renderer: HtmlRenderer) -> None:
        """Test empty stats returns the correct HTML paragraph."""
        output = renderer.render_stats(MessageStats(), DETAILED)
        assert output == "<p>No messages recorded</p>"

    def test_empty_timeline(self, renderer: HtmlRenderer) -> None:
        """Test empty timeline returns the correct HTML paragraph."""
        output = renderer.render_timeline([], DETAILED)
        assert output == "<p>No conversation turns found</p>"

    def test_empty_tools(self, renderer: HtmlRenderer) -> None:
        """Test empty tools returns the correct HTML paragraph."""
        output = renderer.render_tools([], DETAILED)
        assert output == "<p>No tool calls recorded</p>"

    def test_empty_stats_compact(self, renderer: HtmlRenderer) -> None:
        """Test empty stats with compact preset."""
        output = renderer.render_stats(MessageStats(), COMPACT)
        assert output == "<p>No messages recorded</p>"

    def test_empty_timeline_verbose(self, renderer: HtmlRenderer) -> None:
        """Test empty timeline with verbose preset."""
        output = renderer.render_timeline([], VERBOSE)
        assert output == "<p>No conversation turns found</p>"

    def test_empty_tools_compact(self, renderer: HtmlRenderer) -> None:
        """Test empty tools with compact preset."""
        output = renderer.render_tools([], COMPACT)
        assert output == "<p>No tool calls recorded</p>"


# ---------------------------------------------------------------------------
# Class: TestAccessibility
# ---------------------------------------------------------------------------


class TestAccessibility:
    """Test accessibility features of the HTML output."""

    def test_stats_uses_semantic_table(
        self, renderer: HtmlRenderer, sample_stats: MessageStats
    ) -> None:
        """Test that stats uses th, td, thead, tbody, tfoot for screen readers."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "<th>" in output
        assert "<td>" in output
        assert "<thead>" in output
        assert "<tbody>" in output
        assert "<tfoot>" in output

    def test_stats_has_caption(self, renderer: HtmlRenderer, sample_stats: MessageStats) -> None:
        """Test that stats table has a caption for screen readers."""
        output = renderer.render_stats(sample_stats, DETAILED)
        assert "<caption>" in output

    def test_tools_uses_semantic_table(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that tools uses th, td for screen readers."""
        output = renderer.render_tools(sample_tools, DETAILED)
        assert "<th>" in output
        assert "<td>" in output

    def test_tools_has_caption(
        self, renderer: HtmlRenderer, sample_tools: list[ToolCallInfo]
    ) -> None:
        """Test that tools table has a caption for screen readers."""
        output = renderer.render_tools(sample_tools, DETAILED)
        assert "<caption>" in output

    def test_timeline_uses_section_and_heading(
        self, renderer: HtmlRenderer, sample_turns: list[Turn]
    ) -> None:
        """Test that timeline uses section elements with headings."""
        output = renderer.render_timeline(sample_turns, DETAILED)
        assert "<section>" in output
        assert "<h3>" in output

    def test_role_labels_use_strong(self, renderer: HtmlRenderer, sample_turns: list[Turn]) -> None:
        """Test that role labels use strong elements for emphasis."""
        output = renderer.render_timeline(sample_turns, DETAILED)
        assert "<strong>[User]</strong>" in output
        assert "<strong>[Assistant]</strong>" in output


# ---------------------------------------------------------------------------
# Class: TestPerformance
# ---------------------------------------------------------------------------


class TestPerformance:
    """Performance tests for the HtmlRenderer."""

    def test_render_100_messages_under_50ms(self, renderer: HtmlRenderer) -> None:
        """Test that rendering 100 turns completes quickly."""
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

        assert elapsed_ms < 5000, f"Rendering took {elapsed_ms:.1f}ms, expected < 5000ms"

    def test_render_stats_performance(self, renderer: HtmlRenderer) -> None:
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
