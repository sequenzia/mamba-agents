"""Tests for MessageQuery.print_tools() convenience method."""

from __future__ import annotations

import pytest
from rich.console import Console

from mamba_agents.agent.display.functions import print_tools as standalone_print_tools
from mamba_agents.agent.messages import MessageQuery

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_messages_with_tools() -> list[dict]:
    """Build a sample message list that includes tool calls."""
    return [
        {"role": "user", "content": "Search for Python"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "search",
                        "arguments": '{"query": "Python"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "name": "search",
            "content": "Python is a language",
        },
        {"role": "assistant", "content": "I found that Python is a language."},
    ]


def _make_messages_with_multiple_tools() -> list[dict]:
    """Build a sample message list with multiple tool calls."""
    return [
        {"role": "user", "content": "Search and calculate"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "search",
                        "arguments": '{"query": "Python"}',
                    },
                },
                {
                    "id": "call_2",
                    "function": {
                        "name": "calculator",
                        "arguments": '{"expression": "2+2"}',
                    },
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "name": "search",
            "content": "Python is a language",
        },
        {
            "role": "tool",
            "tool_call_id": "call_2",
            "name": "calculator",
            "content": "4",
        },
        {"role": "assistant", "content": "Done."},
    ]


def _make_messages_no_tools() -> list[dict]:
    """Build a sample message list with no tool calls."""
    return [
        {"role": "user", "content": "Hello there"},
        {"role": "assistant", "content": "Hi! How can I help?"},
    ]


def _make_empty_messages() -> list[dict]:
    """Build an empty message list."""
    return []


# ---------------------------------------------------------------------------
# Unit: Delegation to standalone function
# ---------------------------------------------------------------------------


class TestPrintToolsDelegation:
    """Tests that print_tools() delegates to the standalone print_tools function."""

    def test_delegates_to_standalone_function(self) -> None:
        """Test that method calls the standalone print_tools with tool_summary result."""
        mq = MessageQuery(_make_messages_with_tools())
        tools = mq.tool_summary()

        # Verify outputs match between method and standalone call.
        standalone_result = standalone_print_tools(tools)
        method_result = mq.print_tools()
        assert method_result == standalone_result

    def test_returns_string(self) -> None:
        """Test that print_tools returns a string."""
        mq = MessageQuery(_make_messages_with_tools())
        result = mq.print_tools()
        assert isinstance(result, str)

    def test_returns_non_empty_string(self) -> None:
        """Test that print_tools returns a non-empty string for messages with tools."""
        mq = MessageQuery(_make_messages_with_tools())
        result = mq.print_tools()
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Unit: Parameter forwarding
# ---------------------------------------------------------------------------


class TestPrintToolsParameterForwarding:
    """Tests that all parameters are forwarded correctly."""

    def test_preset_forwarded(self) -> None:
        """Test that the preset parameter is forwarded."""
        mq = MessageQuery(_make_messages_with_tools())
        tools = mq.tool_summary()

        # Compare compact preset output between method and standalone.
        method_result = mq.print_tools(preset="compact")
        standalone_result = standalone_print_tools(tools, preset="compact")
        assert method_result == standalone_result

    def test_format_plain_forwarded(self) -> None:
        """Test that format='plain' is forwarded."""
        mq = MessageQuery(_make_messages_with_tools())
        tools = mq.tool_summary()

        method_result = mq.print_tools(format="plain")
        standalone_result = standalone_print_tools(tools, format="plain")
        assert method_result == standalone_result

    def test_format_html_forwarded(self) -> None:
        """Test that format='html' is forwarded."""
        mq = MessageQuery(_make_messages_with_tools())
        tools = mq.tool_summary()

        method_result = mq.print_tools(format="html")
        standalone_result = standalone_print_tools(tools, format="html")
        assert method_result == standalone_result

    def test_console_forwarded(self) -> None:
        """Test that the console parameter is forwarded to the renderer."""
        mq = MessageQuery(_make_messages_with_tools())
        console = Console(record=True, width=120)

        # Should not raise and should return a string.
        result = mq.print_tools(console=console)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_options_override_forwarded(self) -> None:
        """Test that **options overrides are forwarded."""
        mq = MessageQuery(_make_messages_with_tools())
        tools = mq.tool_summary()

        # Override preset option via **options.
        method_result = mq.print_tools(preset="compact", format="html", show_tool_details=True)
        standalone_result = standalone_print_tools(
            tools, preset="compact", format="html", show_tool_details=True
        )
        assert method_result == standalone_result

    def test_all_presets_produce_identical_output(self) -> None:
        """Test that all preset names produce identical output between method and standalone."""
        mq = MessageQuery(_make_messages_with_tools())
        tools = mq.tool_summary()

        for preset_name in ("compact", "detailed", "verbose"):
            method_result = mq.print_tools(preset=preset_name, format="html")
            standalone_result = standalone_print_tools(tools, preset=preset_name, format="html")
            assert method_result == standalone_result, f"Mismatch for preset={preset_name!r}"

    def test_all_formats_produce_identical_output(self) -> None:
        """Test that all formats produce identical output between method and standalone."""
        mq = MessageQuery(_make_messages_with_tools())
        tools = mq.tool_summary()

        for fmt in ("rich", "plain", "html"):
            method_result = mq.print_tools(format=fmt)
            standalone_result = standalone_print_tools(tools, format=fmt)
            assert method_result == standalone_result, f"Mismatch for format={fmt!r}"


# ---------------------------------------------------------------------------
# Functional: Output content
# ---------------------------------------------------------------------------


class TestPrintToolsOutput:
    """Tests that print_tools() outputs correctly formatted content."""

    def test_contains_tool_name(self) -> None:
        """Test that the output contains the tool name."""
        mq = MessageQuery(_make_messages_with_tools())
        result = mq.print_tools(format="html")
        assert "search" in result

    def test_contains_multiple_tool_names(self) -> None:
        """Test that multiple tools are listed in the output."""
        mq = MessageQuery(_make_messages_with_multiple_tools())
        result = mq.print_tools(format="html")
        assert "search" in result
        assert "calculator" in result

    def test_contains_call_count(self) -> None:
        """Test that the output contains call count information."""
        mq = MessageQuery(_make_messages_with_tools())
        result = mq.print_tools(format="html")
        assert "1" in result

    def test_rich_format_produces_formatted_table(self) -> None:
        """Test that the default Rich format outputs a formatted tools table."""
        mq = MessageQuery(_make_messages_with_tools())
        result = mq.print_tools()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_plain_format_produces_readable_output(self) -> None:
        """Test that plain format produces readable ASCII output."""
        mq = MessageQuery(_make_messages_with_tools())
        result = mq.print_tools(format="plain")

        assert isinstance(result, str)
        assert "search" in result

    def test_html_format_produces_html(self) -> None:
        """Test that HTML format produces HTML content."""
        mq = MessageQuery(_make_messages_with_tools())
        result = mq.print_tools(format="html")

        assert "<" in result
        assert "search" in result


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestPrintToolsEdgeCases:
    """Edge case tests for print_tools()."""

    def test_no_tool_calls_shows_message(self) -> None:
        """Test that no tool calls shows 'No tool calls recorded'."""
        mq = MessageQuery(_make_messages_no_tools())
        result = mq.print_tools(format="html")

        assert "No tool calls recorded" in result

    def test_empty_messages_shows_no_tools(self) -> None:
        """Test that empty message list shows 'No tool calls recorded'."""
        mq = MessageQuery(_make_empty_messages())
        result = mq.print_tools(format="html")

        assert "No tool calls recorded" in result

    def test_empty_messages_rich_format(self) -> None:
        """Test that empty messages in Rich format shows appropriate message."""
        mq = MessageQuery(_make_empty_messages())
        result = mq.print_tools(format="rich")

        assert isinstance(result, str)
        assert "No tool calls recorded" in result

    def test_empty_messages_plain_format(self) -> None:
        """Test that empty messages in plain format shows appropriate message."""
        mq = MessageQuery(_make_empty_messages())
        result = mq.print_tools(format="plain")

        assert isinstance(result, str)
        assert "No tool calls recorded" in result

    def test_invalid_preset_raises_value_error(self) -> None:
        """Test that an invalid preset raises ValueError."""
        mq = MessageQuery(_make_messages_with_tools())
        with pytest.raises(ValueError, match="Unknown preset name"):
            mq.print_tools(preset="nonexistent")

    def test_invalid_format_raises_value_error(self) -> None:
        """Test that an invalid format raises ValueError."""
        mq = MessageQuery(_make_messages_with_tools())
        with pytest.raises(ValueError, match="Unknown format"):
            mq.print_tools(format="xml")

    def test_no_token_counter(self) -> None:
        """Test that print_tools works without a TokenCounter."""
        mq = MessageQuery(_make_messages_with_tools(), token_counter=None)
        result = mq.print_tools()
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Integration: agent.messages.print_tools()
# ---------------------------------------------------------------------------


class TestPrintToolsIntegration:
    """Integration tests verifying agent.messages.print_tools() works end-to-end."""

    def test_method_and_standalone_identical_output(self) -> None:
        """Test that method and standalone produce identical output (core contract)."""
        messages = _make_messages_with_tools()
        mq = MessageQuery(messages)
        tools = mq.tool_summary()

        # Verify across all format/preset combinations.
        for fmt in ("rich", "plain", "html"):
            for preset_name in ("compact", "detailed", "verbose"):
                method_result = mq.print_tools(preset=preset_name, format=fmt)
                standalone_result = standalone_print_tools(tools, preset=preset_name, format=fmt)
                assert method_result == standalone_result, (
                    f"Mismatch for format={fmt!r}, preset={preset_name!r}"
                )

    def test_method_returns_rendered_string(self) -> None:
        """Test that print_tools returns the rendered string, not None."""
        mq = MessageQuery(_make_messages_with_tools())
        result = mq.print_tools()

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_multiple_tools_identical_output(self) -> None:
        """Test that multiple-tool messages produce identical output."""
        messages = _make_messages_with_multiple_tools()
        mq = MessageQuery(messages)
        tools = mq.tool_summary()

        for fmt in ("rich", "plain", "html"):
            method_result = mq.print_tools(format=fmt)
            standalone_result = standalone_print_tools(tools, format=fmt)
            assert method_result == standalone_result, f"Mismatch for format={fmt!r}"

    def test_no_tools_identical_output(self) -> None:
        """Test that no-tool messages produce identical output."""
        messages = _make_messages_no_tools()
        mq = MessageQuery(messages)
        tools = mq.tool_summary()

        for fmt in ("rich", "plain", "html"):
            method_result = mq.print_tools(format=fmt)
            standalone_result = standalone_print_tools(tools, format=fmt)
            assert method_result == standalone_result, f"Mismatch for format={fmt!r}"
