"""Tests for the standalone display helper functions."""

from __future__ import annotations

import pytest
from rich.console import Console

from mamba_agents.agent.display import (
    print_stats,
    print_timeline,
    print_tools,
)
from mamba_agents.agent.display.functions import _resolve_renderer
from mamba_agents.agent.display.html_renderer import HtmlRenderer
from mamba_agents.agent.display.plain_renderer import PlainTextRenderer
from mamba_agents.agent.display.rich_renderer import RichRenderer
from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_stats() -> MessageStats:
    """Build a sample MessageStats with data for testing."""
    return MessageStats(
        total_messages=10,
        messages_by_role={"user": 5, "assistant": 5},
        total_tokens=500,
        tokens_by_role={"user": 200, "assistant": 300},
    )


def _make_turns() -> list[Turn]:
    """Build a sample list of Turns for testing."""
    return [
        Turn(index=0, user_content="Hello", assistant_content="Hi there"),
        Turn(index=1, user_content="How?", assistant_content="Like this"),
    ]


def _make_tools() -> list[ToolCallInfo]:
    """Build a sample list of ToolCallInfo for testing."""
    return [
        ToolCallInfo(tool_name="search", call_count=3),
        ToolCallInfo(tool_name="read_file", call_count=1),
    ]


# ---------------------------------------------------------------------------
# Renderer selection tests
# ---------------------------------------------------------------------------


class TestResolveRenderer:
    """Tests for the _resolve_renderer internal function."""

    def test_rich_format_returns_rich_renderer(self) -> None:
        """Test that 'rich' returns a RichRenderer instance."""
        renderer = _resolve_renderer("rich")
        assert isinstance(renderer, RichRenderer)

    def test_plain_format_returns_plain_renderer(self) -> None:
        """Test that 'plain' returns a PlainTextRenderer instance."""
        renderer = _resolve_renderer("plain")
        assert isinstance(renderer, PlainTextRenderer)

    def test_html_format_returns_html_renderer(self) -> None:
        """Test that 'html' returns an HtmlRenderer instance."""
        renderer = _resolve_renderer("html")
        assert isinstance(renderer, HtmlRenderer)

    def test_unknown_format_raises_value_error(self) -> None:
        """Test that an unknown format raises ValueError."""
        with pytest.raises(ValueError, match="Unknown format: 'csv'"):
            _resolve_renderer("csv")

    def test_unknown_format_error_lists_valid_formats(self) -> None:
        """Test that the error message includes all valid format names."""
        with pytest.raises(ValueError) as exc_info:
            _resolve_renderer("invalid")

        error_msg = str(exc_info.value)
        assert "html" in error_msg
        assert "plain" in error_msg
        assert "rich" in error_msg


# ---------------------------------------------------------------------------
# print_stats tests
# ---------------------------------------------------------------------------


class TestPrintStats:
    """Tests for the print_stats standalone function."""

    def test_default_produces_rich_output(self) -> None:
        """Test that print_stats() defaults to Rich format output."""
        stats = _make_stats()
        result = print_stats(stats)

        assert isinstance(result, str)
        assert len(result) > 0
        # Rich output includes the table title.
        assert "Message Statistics" in result

    def test_returns_string(self) -> None:
        """Test that print_stats returns the rendered string."""
        stats = _make_stats()
        result = print_stats(stats)

        assert isinstance(result, str)

    def test_plain_format(self) -> None:
        """Test that format='plain' selects PlainTextRenderer."""
        stats = _make_stats()
        result = print_stats(stats, format="plain", console=None)

        assert isinstance(result, str)
        assert "Message Statistics" in result
        # Plain text output includes role names in a table.
        assert "user" in result
        assert "assistant" in result

    def test_html_format(self) -> None:
        """Test that format='html' selects HtmlRenderer."""
        stats = _make_stats()
        result = print_stats(stats, format="html")

        assert isinstance(result, str)
        assert "<table>" in result
        assert "Message Statistics" in result

    def test_preset_selection(self) -> None:
        """Test that preset parameter selects the named preset."""
        stats = _make_stats()

        # compact preset does not show tokens.
        result = print_stats(stats, preset="compact")
        assert isinstance(result, str)

    def test_compact_preset_hides_tokens(self) -> None:
        """Test that compact preset suppresses token display."""
        stats = _make_stats()
        # Use html format for easier assertion (no Rich formatting noise).
        result = print_stats(stats, preset="compact", format="html")
        assert "<th>Tokens</th>" not in result

    def test_verbose_preset_shows_tokens(self) -> None:
        """Test that verbose preset includes token display."""
        stats = _make_stats()
        result = print_stats(stats, preset="verbose", format="html")
        assert "<th>Tokens</th>" in result

    def test_options_override_preset(self) -> None:
        """Test that **options override preset values."""
        stats = _make_stats()
        # compact preset has show_tokens=False; override to True.
        result = print_stats(stats, preset="compact", format="html", show_tokens=True)
        assert "<th>Tokens</th>" in result

    def test_options_override_detailed_preset(self) -> None:
        """Test overriding detailed preset to hide tokens."""
        stats = _make_stats()
        # detailed preset has show_tokens=True; override to False.
        result = print_stats(stats, preset="detailed", format="html", show_tokens=False)
        assert "<th>Tokens</th>" not in result

    def test_invalid_preset_raises_value_error(self) -> None:
        """Test that an invalid preset name raises ValueError."""
        stats = _make_stats()
        with pytest.raises(ValueError, match="Unknown preset name"):
            print_stats(stats, preset="nonexistent")

    def test_invalid_format_raises_value_error(self) -> None:
        """Test that an invalid format raises ValueError."""
        stats = _make_stats()
        with pytest.raises(ValueError, match="Unknown format"):
            print_stats(stats, format="xml")

    def test_console_parameter_accepted(self) -> None:
        """Test that console parameter is passed to RichRenderer."""
        stats = _make_stats()
        console = Console(record=True, width=120)
        result = print_stats(stats, console=console)

        assert isinstance(result, str)
        assert "Message Statistics" in result

    def test_empty_stats(self) -> None:
        """Test that empty stats are handled gracefully."""
        stats = MessageStats()
        result = print_stats(stats, format="html")

        assert isinstance(result, str)
        assert "No messages recorded" in result


# ---------------------------------------------------------------------------
# print_timeline tests
# ---------------------------------------------------------------------------


class TestPrintTimeline:
    """Tests for the print_timeline standalone function."""

    def test_default_produces_rich_output(self) -> None:
        """Test that print_timeline() defaults to Rich format output."""
        turns = _make_turns()
        result = print_timeline(turns)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Turn 0" in result

    def test_returns_string(self) -> None:
        """Test that print_timeline returns the rendered string."""
        turns = _make_turns()
        result = print_timeline(turns)

        assert isinstance(result, str)

    def test_plain_format(self) -> None:
        """Test that format='plain' selects PlainTextRenderer."""
        turns = _make_turns()
        result = print_timeline(turns, format="plain")

        assert isinstance(result, str)
        assert "Turn 0" in result
        assert "Hello" in result

    def test_html_format(self) -> None:
        """Test that format='html' selects HtmlRenderer."""
        turns = _make_turns()
        result = print_timeline(turns, format="html")

        assert isinstance(result, str)
        assert "<section>" in result
        assert "Turn 0" in result

    def test_preset_selection(self) -> None:
        """Test that preset parameter selects the named preset."""
        turns = _make_turns()
        result = print_timeline(turns, preset="compact")
        assert isinstance(result, str)

    def test_options_override_preset(self) -> None:
        """Test that **options override preset values (e.g., limit)."""
        turns = _make_turns()
        result = print_timeline(turns, format="html", limit=1)

        # Should show only 1 turn with a "more" indicator.
        assert "Turn 0" in result
        assert "1 more turn(s) not shown" in result

    def test_invalid_preset_raises_value_error(self) -> None:
        """Test that an invalid preset name raises ValueError."""
        turns = _make_turns()
        with pytest.raises(ValueError, match="Unknown preset name"):
            print_timeline(turns, preset="nonexistent")

    def test_invalid_format_raises_value_error(self) -> None:
        """Test that an invalid format raises ValueError."""
        turns = _make_turns()
        with pytest.raises(ValueError, match="Unknown format"):
            print_timeline(turns, format="xml")

    def test_console_parameter_accepted(self) -> None:
        """Test that console parameter is passed to RichRenderer."""
        turns = _make_turns()
        console = Console(record=True, width=120)
        result = print_timeline(turns, console=console)

        assert isinstance(result, str)
        assert "Turn 0" in result

    def test_empty_turns(self) -> None:
        """Test that empty turns list is handled gracefully."""
        result = print_timeline([], format="html")

        assert isinstance(result, str)
        assert "No conversation turns found" in result


# ---------------------------------------------------------------------------
# print_tools tests
# ---------------------------------------------------------------------------


class TestPrintTools:
    """Tests for the print_tools standalone function."""

    def test_default_produces_rich_output(self) -> None:
        """Test that print_tools() defaults to Rich format output."""
        tools = _make_tools()
        result = print_tools(tools)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Tool Summary" in result

    def test_returns_string(self) -> None:
        """Test that print_tools returns the rendered string."""
        tools = _make_tools()
        result = print_tools(tools)

        assert isinstance(result, str)

    def test_plain_format(self) -> None:
        """Test that format='plain' selects PlainTextRenderer."""
        tools = _make_tools()
        result = print_tools(tools, format="plain")

        assert isinstance(result, str)
        assert "Tool Summary" in result
        assert "search" in result

    def test_html_format(self) -> None:
        """Test that format='html' selects HtmlRenderer."""
        tools = _make_tools()
        result = print_tools(tools, format="html")

        assert isinstance(result, str)
        assert "<table>" in result
        assert "search" in result

    def test_preset_selection(self) -> None:
        """Test that preset parameter selects the named preset."""
        tools = _make_tools()
        result = print_tools(tools, preset="verbose")
        assert isinstance(result, str)

    def test_options_override_preset(self) -> None:
        """Test that **options override preset values."""
        tools = _make_tools()
        # verbose preset has show_tool_details=True; override to False.
        result = print_tools(tools, preset="verbose", format="html", show_tool_details=False)
        assert "<th>Details</th>" not in result

    def test_show_tool_details_override(self) -> None:
        """Test enabling show_tool_details via options override."""
        tools = _make_tools()
        result = print_tools(tools, format="html", show_tool_details=True)
        assert "<th>Details</th>" in result

    def test_invalid_preset_raises_value_error(self) -> None:
        """Test that an invalid preset name raises ValueError."""
        tools = _make_tools()
        with pytest.raises(ValueError, match="Unknown preset name"):
            print_tools(tools, preset="nonexistent")

    def test_invalid_format_raises_value_error(self) -> None:
        """Test that an invalid format raises ValueError."""
        tools = _make_tools()
        with pytest.raises(ValueError, match="Unknown format"):
            print_tools(tools, format="xml")

    def test_console_parameter_accepted(self) -> None:
        """Test that console parameter is passed to RichRenderer."""
        tools = _make_tools()
        console = Console(record=True, width=120)
        result = print_tools(tools, console=console)

        assert isinstance(result, str)
        assert "Tool Summary" in result

    def test_empty_tools(self) -> None:
        """Test that empty tools list is handled gracefully."""
        result = print_tools([], format="html")

        assert isinstance(result, str)
        assert "No tool calls recorded" in result


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """End-to-end integration tests for standalone functions."""

    def test_stats_rich_end_to_end(self) -> None:
        """Test full stats rendering with Rich format end-to-end."""
        stats = _make_stats()
        result = print_stats(stats, preset="detailed")

        # Should contain table structure.
        assert "Message Statistics" in result
        assert "user" in result
        assert "assistant" in result
        assert "Total" in result

    def test_timeline_plain_end_to_end(self) -> None:
        """Test full timeline rendering with plain format end-to-end."""
        turns = _make_turns()
        # Use a StringIO file parameter to suppress stdout via the plain renderer.
        result = print_timeline(turns, format="plain", preset="detailed")

        assert "Turn 0" in result
        assert "Turn 1" in result
        assert "[User] Hello" in result
        assert "[Assistant] Hi there" in result

    def test_tools_html_end_to_end(self) -> None:
        """Test full tools rendering with HTML format end-to-end."""
        tools = _make_tools()
        result = print_tools(tools, format="html", preset="verbose")

        assert "<table>" in result
        assert "search" in result
        assert "read_file" in result

    def test_all_formats_produce_non_empty_output(self) -> None:
        """Test that all format/function combinations produce non-empty strings."""
        stats = _make_stats()
        turns = _make_turns()
        tools = _make_tools()

        for fmt in ("rich", "plain", "html"):
            assert len(print_stats(stats, format=fmt)) > 0
            assert len(print_timeline(turns, format=fmt)) > 0
            assert len(print_tools(tools, format=fmt)) > 0

    def test_all_presets_work_with_all_formats(self) -> None:
        """Test that every preset/format combination works without error."""
        stats = _make_stats()

        for preset_name in ("compact", "detailed", "verbose"):
            for fmt in ("rich", "plain", "html"):
                result = print_stats(stats, preset=preset_name, format=fmt)
                assert isinstance(result, str)
                assert len(result) > 0


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


class TestImports:
    """Tests that functions are importable from the display module."""

    def test_print_stats_importable_from_display(self) -> None:
        """Test that print_stats is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import print_stats as fn

        assert callable(fn)

    def test_print_timeline_importable_from_display(self) -> None:
        """Test that print_timeline is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import print_timeline as fn

        assert callable(fn)

    def test_print_tools_importable_from_display(self) -> None:
        """Test that print_tools is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import print_tools as fn

        assert callable(fn)

    def test_all_three_in_display_all(self) -> None:
        """Test that all three functions are in the display module __all__."""
        import mamba_agents.agent.display as display_module

        assert "print_stats" in display_module.__all__
        assert "print_timeline" in display_module.__all__
        assert "print_tools" in display_module.__all__
