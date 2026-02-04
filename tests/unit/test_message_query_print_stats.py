"""Tests for MessageQuery.print_stats() convenience method."""

from __future__ import annotations

import pytest
from rich.console import Console

from mamba_agents.agent.display.functions import print_stats as standalone_print_stats
from mamba_agents.agent.messages import MessageQuery

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_messages() -> list[dict]:
    """Build a sample message list for testing."""
    return [
        {"role": "user", "content": "Hello there"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."},
    ]


def _make_empty_messages() -> list[dict]:
    """Build an empty message list."""
    return []


# ---------------------------------------------------------------------------
# Unit: Delegation to standalone function
# ---------------------------------------------------------------------------


class TestPrintStatsDelegation:
    """Tests that print_stats() delegates to the standalone print_stats function."""

    def test_delegates_to_standalone_function(self) -> None:
        """Test that method calls the standalone print_stats with stats result."""
        mq = MessageQuery(_make_messages())
        stats = mq.stats()

        # Verify outputs match between method and standalone call.
        standalone_result = standalone_print_stats(stats)
        method_result = mq.print_stats()
        assert method_result == standalone_result

    def test_returns_string(self) -> None:
        """Test that print_stats returns a string."""
        mq = MessageQuery(_make_messages())
        result = mq.print_stats()
        assert isinstance(result, str)

    def test_returns_non_empty_string(self) -> None:
        """Test that print_stats returns a non-empty string for non-empty messages."""
        mq = MessageQuery(_make_messages())
        result = mq.print_stats()
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Unit: Parameter forwarding
# ---------------------------------------------------------------------------


class TestPrintStatsParameterForwarding:
    """Tests that all parameters are forwarded correctly."""

    def test_preset_forwarded(self) -> None:
        """Test that the preset parameter is forwarded."""
        mq = MessageQuery(_make_messages())
        stats = mq.stats()

        # Compare compact preset output between method and standalone.
        method_result = mq.print_stats(preset="compact")
        standalone_result = standalone_print_stats(stats, preset="compact")
        assert method_result == standalone_result

    def test_format_plain_forwarded(self) -> None:
        """Test that format='plain' is forwarded."""
        mq = MessageQuery(_make_messages())
        stats = mq.stats()

        method_result = mq.print_stats(format="plain")
        standalone_result = standalone_print_stats(stats, format="plain")
        assert method_result == standalone_result

    def test_format_html_forwarded(self) -> None:
        """Test that format='html' is forwarded."""
        mq = MessageQuery(_make_messages())
        stats = mq.stats()

        method_result = mq.print_stats(format="html")
        standalone_result = standalone_print_stats(stats, format="html")
        assert method_result == standalone_result

    def test_console_forwarded(self) -> None:
        """Test that the console parameter is forwarded to the renderer."""
        mq = MessageQuery(_make_messages())
        console = Console(record=True, width=120)

        # Should not raise and should return a string.
        result = mq.print_stats(console=console)
        assert isinstance(result, str)
        assert "Message Statistics" in result

    def test_options_override_forwarded(self) -> None:
        """Test that **options overrides are forwarded."""
        mq = MessageQuery(_make_messages())
        stats = mq.stats()

        # Override compact preset to show tokens.
        method_result = mq.print_stats(preset="compact", format="html", show_tokens=True)
        standalone_result = standalone_print_stats(
            stats, preset="compact", format="html", show_tokens=True
        )
        assert method_result == standalone_result

    def test_options_hide_tokens_forwarded(self) -> None:
        """Test that show_tokens=False override is forwarded."""
        mq = MessageQuery(_make_messages())
        stats = mq.stats()

        method_result = mq.print_stats(format="html", show_tokens=False)
        standalone_result = standalone_print_stats(stats, format="html", show_tokens=False)
        assert method_result == standalone_result

    def test_all_presets_produce_identical_output(self) -> None:
        """Test that all preset names produce identical output between method and standalone."""
        mq = MessageQuery(_make_messages())
        stats = mq.stats()

        for preset_name in ("compact", "detailed", "verbose"):
            method_result = mq.print_stats(preset=preset_name, format="html")
            standalone_result = standalone_print_stats(stats, preset=preset_name, format="html")
            assert method_result == standalone_result, f"Mismatch for preset={preset_name!r}"

    def test_all_formats_produce_identical_output(self) -> None:
        """Test that all formats produce identical output between method and standalone."""
        mq = MessageQuery(_make_messages())
        stats = mq.stats()

        for fmt in ("rich", "plain", "html"):
            method_result = mq.print_stats(format=fmt)
            standalone_result = standalone_print_stats(stats, format=fmt)
            assert method_result == standalone_result, f"Mismatch for format={fmt!r}"


# ---------------------------------------------------------------------------
# Functional: Output content
# ---------------------------------------------------------------------------


class TestPrintStatsOutput:
    """Tests that print_stats() outputs correctly formatted content."""

    def test_contains_message_statistics_header(self) -> None:
        """Test that the output contains the Message Statistics header."""
        mq = MessageQuery(_make_messages())
        result = mq.print_stats()
        assert "Message Statistics" in result

    def test_contains_role_data(self) -> None:
        """Test that the output contains role information."""
        mq = MessageQuery(_make_messages())
        result = mq.print_stats(format="html")
        assert "user" in result
        assert "assistant" in result

    def test_contains_total_row(self) -> None:
        """Test that the output contains a total row."""
        mq = MessageQuery(_make_messages())
        result = mq.print_stats(format="html")
        assert "Total" in result

    def test_rich_format_produces_formatted_table(self) -> None:
        """Test that the default Rich format outputs a formatted stats table."""
        mq = MessageQuery(_make_messages())
        result = mq.print_stats()

        assert isinstance(result, str)
        assert "Message Statistics" in result
        assert "user" in result
        assert "assistant" in result

    def test_plain_format_produces_readable_output(self) -> None:
        """Test that plain format produces readable ASCII output."""
        mq = MessageQuery(_make_messages())
        result = mq.print_stats(format="plain")

        assert isinstance(result, str)
        assert "Message Statistics" in result

    def test_html_format_produces_html_table(self) -> None:
        """Test that HTML format produces an HTML table."""
        mq = MessageQuery(_make_messages())
        result = mq.print_stats(format="html")

        assert "<table>" in result
        assert "Message Statistics" in result


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestPrintStatsEdgeCases:
    """Edge case tests for print_stats()."""

    def test_empty_message_history_shows_no_messages(self) -> None:
        """Test that empty message history shows 'No messages recorded'."""
        mq = MessageQuery(_make_empty_messages())
        result = mq.print_stats(format="html")

        assert "No messages recorded" in result

    def test_empty_message_history_rich_format(self) -> None:
        """Test that empty message history in Rich format shows appropriate message."""
        mq = MessageQuery(_make_empty_messages())
        result = mq.print_stats(format="rich")

        assert isinstance(result, str)
        assert "No messages recorded" in result

    def test_empty_message_history_plain_format(self) -> None:
        """Test that empty message history in plain format shows appropriate message."""
        mq = MessageQuery(_make_empty_messages())
        result = mq.print_stats(format="plain")

        assert isinstance(result, str)
        assert "No messages recorded" in result

    def test_invalid_preset_raises_value_error(self) -> None:
        """Test that an invalid preset raises ValueError."""
        mq = MessageQuery(_make_messages())
        with pytest.raises(ValueError, match="Unknown preset name"):
            mq.print_stats(preset="nonexistent")

    def test_invalid_format_raises_value_error(self) -> None:
        """Test that an invalid format raises ValueError."""
        mq = MessageQuery(_make_messages())
        with pytest.raises(ValueError, match="Unknown format"):
            mq.print_stats(format="xml")

    def test_single_message(self) -> None:
        """Test that a single message produces valid output."""
        mq = MessageQuery([{"role": "user", "content": "Hi"}])
        result = mq.print_stats(format="html")

        assert isinstance(result, str)
        assert "user" in result

    def test_no_token_counter(self) -> None:
        """Test that print_stats works without a TokenCounter."""
        mq = MessageQuery(_make_messages(), token_counter=None)
        result = mq.print_stats()
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Integration: agent.messages.print_stats()
# ---------------------------------------------------------------------------


class TestPrintStatsIntegration:
    """Integration tests verifying agent.messages.print_stats() works end-to-end."""

    def test_method_and_standalone_identical_output(self) -> None:
        """Test that method and standalone produce identical output (core contract)."""
        messages = _make_messages()
        mq = MessageQuery(messages)
        stats = mq.stats()

        # Verify across all format/preset combinations.
        for fmt in ("rich", "plain", "html"):
            for preset_name in ("compact", "detailed", "verbose"):
                method_result = mq.print_stats(preset=preset_name, format=fmt)
                standalone_result = standalone_print_stats(stats, preset=preset_name, format=fmt)
                assert method_result == standalone_result, (
                    f"Mismatch for format={fmt!r}, preset={preset_name!r}"
                )

    def test_method_returns_rendered_string(self) -> None:
        """Test that print_stats returns the rendered string, not None."""
        mq = MessageQuery(_make_messages())
        result = mq.print_stats()

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
