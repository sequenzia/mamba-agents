"""Tests for MessageQuery.print_timeline() convenience method."""

from __future__ import annotations

import pytest
from rich.console import Console

from mamba_agents.agent.display.functions import print_timeline as standalone_print_timeline
from mamba_agents.agent.messages import MessageQuery

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_messages() -> list[dict]:
    """Build a sample message list with user/assistant turns."""
    return [
        {"role": "user", "content": "Hello there"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."},
    ]


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


def _make_empty_messages() -> list[dict]:
    """Build an empty message list."""
    return []


# ---------------------------------------------------------------------------
# Unit: Delegation to standalone function
# ---------------------------------------------------------------------------


class TestPrintTimelineDelegation:
    """Tests that print_timeline() delegates to the standalone print_timeline function."""

    def test_delegates_to_standalone_function(self) -> None:
        """Test that method calls the standalone print_timeline with timeline result."""
        mq = MessageQuery(_make_messages())
        turns = mq.timeline()

        # Verify outputs match between method and standalone call.
        standalone_result = standalone_print_timeline(turns)
        method_result = mq.print_timeline()
        assert method_result == standalone_result

    def test_returns_string(self) -> None:
        """Test that print_timeline returns a string."""
        mq = MessageQuery(_make_messages())
        result = mq.print_timeline()
        assert isinstance(result, str)

    def test_returns_non_empty_string(self) -> None:
        """Test that print_timeline returns a non-empty string for non-empty messages."""
        mq = MessageQuery(_make_messages())
        result = mq.print_timeline()
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Unit: Parameter forwarding
# ---------------------------------------------------------------------------


class TestPrintTimelineParameterForwarding:
    """Tests that all parameters are forwarded correctly."""

    def test_preset_forwarded(self) -> None:
        """Test that the preset parameter is forwarded."""
        mq = MessageQuery(_make_messages())
        turns = mq.timeline()

        # Compare compact preset output between method and standalone.
        method_result = mq.print_timeline(preset="compact")
        standalone_result = standalone_print_timeline(turns, preset="compact")
        assert method_result == standalone_result

    def test_format_plain_forwarded(self) -> None:
        """Test that format='plain' is forwarded."""
        mq = MessageQuery(_make_messages())
        turns = mq.timeline()

        method_result = mq.print_timeline(format="plain")
        standalone_result = standalone_print_timeline(turns, format="plain")
        assert method_result == standalone_result

    def test_format_html_forwarded(self) -> None:
        """Test that format='html' is forwarded."""
        mq = MessageQuery(_make_messages())
        turns = mq.timeline()

        method_result = mq.print_timeline(format="html")
        standalone_result = standalone_print_timeline(turns, format="html")
        assert method_result == standalone_result

    def test_console_forwarded(self) -> None:
        """Test that the console parameter is forwarded to the renderer."""
        mq = MessageQuery(_make_messages())
        console = Console(record=True, width=120)

        # Should not raise and should return a string.
        result = mq.print_timeline(console=console)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_options_override_forwarded(self) -> None:
        """Test that **options overrides are forwarded."""
        mq = MessageQuery(_make_messages())
        turns = mq.timeline()

        # Override preset option via **options.
        method_result = mq.print_timeline(preset="compact", format="html", show_tool_details=True)
        standalone_result = standalone_print_timeline(
            turns, preset="compact", format="html", show_tool_details=True
        )
        assert method_result == standalone_result

    def test_all_presets_produce_identical_output(self) -> None:
        """Test that all preset names produce identical output between method and standalone."""
        mq = MessageQuery(_make_messages())
        turns = mq.timeline()

        for preset_name in ("compact", "detailed", "verbose"):
            method_result = mq.print_timeline(preset=preset_name, format="html")
            standalone_result = standalone_print_timeline(turns, preset=preset_name, format="html")
            assert method_result == standalone_result, f"Mismatch for preset={preset_name!r}"

    def test_all_formats_produce_identical_output(self) -> None:
        """Test that all formats produce identical output between method and standalone."""
        mq = MessageQuery(_make_messages())
        turns = mq.timeline()

        for fmt in ("rich", "plain", "html"):
            method_result = mq.print_timeline(format=fmt)
            standalone_result = standalone_print_timeline(turns, format=fmt)
            assert method_result == standalone_result, f"Mismatch for format={fmt!r}"


# ---------------------------------------------------------------------------
# Functional: Output content
# ---------------------------------------------------------------------------


class TestPrintTimelineOutput:
    """Tests that print_timeline() outputs correctly formatted content."""

    def test_contains_user_content(self) -> None:
        """Test that the output contains user message content."""
        mq = MessageQuery(_make_messages())
        result = mq.print_timeline(format="html")
        assert "Hello there" in result

    def test_contains_assistant_content(self) -> None:
        """Test that the output contains assistant response content."""
        mq = MessageQuery(_make_messages())
        result = mq.print_timeline(format="html")
        assert "How can I help" in result

    def test_contains_turn_structure(self) -> None:
        """Test that the output has a multi-turn structure."""
        mq = MessageQuery(_make_messages())
        result = mq.print_timeline(format="html")

        # Two user messages means two turns.
        assert "Hello there" in result
        assert "What is Python" in result

    def test_rich_format_produces_formatted_output(self) -> None:
        """Test that the default Rich format outputs formatted timeline."""
        mq = MessageQuery(_make_messages())
        result = mq.print_timeline()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_plain_format_produces_readable_output(self) -> None:
        """Test that plain format produces readable ASCII output."""
        mq = MessageQuery(_make_messages())
        result = mq.print_timeline(format="plain")

        assert isinstance(result, str)
        assert "Hello there" in result

    def test_html_format_produces_html(self) -> None:
        """Test that HTML format produces HTML content."""
        mq = MessageQuery(_make_messages())
        result = mq.print_timeline(format="html")

        assert "<" in result
        assert "Hello there" in result

    def test_tool_interactions_included(self) -> None:
        """Test that tool call details appear in the output."""
        mq = MessageQuery(_make_messages_with_tools())
        result = mq.print_timeline(format="html")

        assert "search" in result


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestPrintTimelineEdgeCases:
    """Edge case tests for print_timeline()."""

    def test_empty_timeline_shows_no_turns_message(self) -> None:
        """Test that empty timeline shows 'No conversation turns found'."""
        mq = MessageQuery(_make_empty_messages())
        result = mq.print_timeline(format="html")

        assert "No conversation turns found" in result

    def test_empty_timeline_rich_format(self) -> None:
        """Test that empty timeline in Rich format shows appropriate message."""
        mq = MessageQuery(_make_empty_messages())
        result = mq.print_timeline(format="rich")

        assert isinstance(result, str)
        assert "No conversation turns found" in result

    def test_empty_timeline_plain_format(self) -> None:
        """Test that empty timeline in plain format shows appropriate message."""
        mq = MessageQuery(_make_empty_messages())
        result = mq.print_timeline(format="plain")

        assert isinstance(result, str)
        assert "No conversation turns found" in result

    def test_invalid_preset_raises_value_error(self) -> None:
        """Test that an invalid preset raises ValueError."""
        mq = MessageQuery(_make_messages())
        with pytest.raises(ValueError, match="Unknown preset name"):
            mq.print_timeline(preset="nonexistent")

    def test_invalid_format_raises_value_error(self) -> None:
        """Test that an invalid format raises ValueError."""
        mq = MessageQuery(_make_messages())
        with pytest.raises(ValueError, match="Unknown format"):
            mq.print_timeline(format="xml")

    def test_single_message(self) -> None:
        """Test that a single message produces valid output."""
        mq = MessageQuery([{"role": "user", "content": "Hi"}])
        result = mq.print_timeline(format="html")

        assert isinstance(result, str)
        assert "Hi" in result

    def test_no_token_counter(self) -> None:
        """Test that print_timeline works without a TokenCounter."""
        mq = MessageQuery(_make_messages(), token_counter=None)
        result = mq.print_timeline()
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Integration: agent.messages.print_timeline()
# ---------------------------------------------------------------------------


class TestPrintTimelineIntegration:
    """Integration tests verifying agent.messages.print_timeline() works end-to-end."""

    def test_method_and_standalone_identical_output(self) -> None:
        """Test that method and standalone produce identical output (core contract)."""
        messages = _make_messages()
        mq = MessageQuery(messages)
        turns = mq.timeline()

        # Verify across all format/preset combinations.
        for fmt in ("rich", "plain", "html"):
            for preset_name in ("compact", "detailed", "verbose"):
                method_result = mq.print_timeline(preset=preset_name, format=fmt)
                standalone_result = standalone_print_timeline(turns, preset=preset_name, format=fmt)
                assert method_result == standalone_result, (
                    f"Mismatch for format={fmt!r}, preset={preset_name!r}"
                )

    def test_method_returns_rendered_string(self) -> None:
        """Test that print_timeline returns the rendered string, not None."""
        mq = MessageQuery(_make_messages())
        result = mq.print_timeline()

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tool_interactions_identical_output(self) -> None:
        """Test that tool-containing messages produce identical output."""
        messages = _make_messages_with_tools()
        mq = MessageQuery(messages)
        turns = mq.timeline()

        for fmt in ("rich", "plain", "html"):
            method_result = mq.print_timeline(format=fmt)
            standalone_result = standalone_print_timeline(turns, format=fmt)
            assert method_result == standalone_result, f"Mismatch for format={fmt!r}"
