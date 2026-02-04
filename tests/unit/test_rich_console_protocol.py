"""Tests for __rich_console__ protocol on MessageStats, ToolCallInfo, and Turn."""

from __future__ import annotations

import pytest
from rich.console import Console

from mamba_agents.agent.display import DETAILED
from mamba_agents.agent.display.rich_renderer import RichRenderer
from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def sample_tool() -> ToolCallInfo:
    """Provide a populated ToolCallInfo for testing."""
    return ToolCallInfo(
        tool_name="read_file",
        call_count=3,
        arguments=[
            {"path": "a.txt"},
            {"path": "b.txt"},
            {"path": "c.txt"},
        ],
        results=["content a", "content b", "content c"],
        tool_call_ids=["call_1", "call_2", "call_3"],
    )


@pytest.fixture
def sample_turn() -> Turn:
    """Provide a populated Turn for testing."""
    return Turn(
        index=0,
        system_context="You are a helpful assistant.",
        user_content="Hello, can you help me?",
        assistant_content="Of course! What do you need help with?",
        tool_interactions=[
            {
                "tool_name": "search",
                "tool_call_id": "call_1",
                "arguments": {"query": "test"},
                "result": "found it",
            },
        ],
    )


@pytest.fixture
def simple_turn() -> Turn:
    """Provide a simple Turn without tools for testing."""
    return Turn(
        index=1,
        user_content="What is Python?",
        assistant_content="Python is a programming language.",
    )


# ---------------------------------------------------------------------------
# Class: TestMessageStatsRichConsole
# ---------------------------------------------------------------------------


class TestMessageStatsRichConsole:
    """Tests for MessageStats.__rich_console__ protocol."""

    def test_has_rich_console_method(self) -> None:
        """Test that MessageStats has __rich_console__ method."""
        assert hasattr(MessageStats, "__rich_console__")

    def test_rich_print_produces_output(self, sample_stats: MessageStats) -> None:
        """Test that rich.print(stats) produces formatted output."""
        console = Console(record=True)
        console.print(sample_stats)
        output = console.export_text()

        assert "Message Statistics" in output
        assert "assistant" in output
        assert "user" in output
        assert "Total" in output

    def test_output_matches_render_stats(self, sample_stats: MessageStats) -> None:
        """Test that __rich_console__ output matches RichRenderer.render_stats()."""
        # Get output from render_stats with DETAILED preset.
        renderer = RichRenderer()
        render_output = renderer.render_stats(sample_stats, DETAILED)

        # Get output from __rich_console__ protocol.
        console = Console(record=True)
        console.print(sample_stats)
        protocol_output = console.export_text()

        assert render_output == protocol_output

    def test_uses_detailed_preset(self, sample_stats: MessageStats) -> None:
        """Test that __rich_console__ uses the detailed preset by default."""
        console = Console(record=True)
        console.print(sample_stats)
        output = console.export_text()

        # DETAILED preset has show_tokens=True.
        assert "Tokens" in output
        assert "Average tokens/message" in output

    def test_shows_token_counts(self, sample_stats: MessageStats) -> None:
        """Test that token counts appear in output."""
        console = Console(record=True)
        console.print(sample_stats)
        output = console.export_text()

        assert "1,500" in output
        assert "150.0" in output

    def test_empty_stats(self, empty_stats: MessageStats) -> None:
        """Test that empty stats produce 'No messages recorded' panel."""
        console = Console(record=True)
        console.print(empty_stats)
        output = console.export_text()

        assert "No messages recorded" in output

    def test_works_with_rich_print(self, sample_stats: MessageStats) -> None:
        """Integration: rich.print(stats) does not raise."""
        # This test exercises the full rich.print() path.
        console = Console(record=True, file=None)
        console.print(sample_stats)
        output = console.export_text()
        assert len(output) > 0


# ---------------------------------------------------------------------------
# Class: TestToolCallInfoRichConsole
# ---------------------------------------------------------------------------


class TestToolCallInfoRichConsole:
    """Tests for ToolCallInfo.__rich_console__ protocol."""

    def test_has_rich_console_method(self) -> None:
        """Test that ToolCallInfo has __rich_console__ method."""
        assert hasattr(ToolCallInfo, "__rich_console__")

    def test_rich_print_produces_output(self, sample_tool: ToolCallInfo) -> None:
        """Test that rich.print(tool_info) produces formatted output."""
        console = Console(record=True)
        console.print(sample_tool)
        output = console.export_text()

        assert "Tool Summary" in output
        assert "read_file" in output
        assert "3" in output

    def test_compact_tool_summary(self, sample_tool: ToolCallInfo) -> None:
        """Test that output is a compact tool summary table."""
        console = Console(record=True)
        console.print(sample_tool)
        output = console.export_text()

        assert "Tool Name" in output
        assert "Calls" in output
        # DETAILED preset has show_tool_details=False, so no args.
        assert "args:" not in output

    def test_single_tool_rendered(self) -> None:
        """Test that a single ToolCallInfo renders one row."""
        tool = ToolCallInfo(
            tool_name="bash",
            call_count=1,
            arguments=[{"command": "ls"}],
            results=["file1.txt"],
            tool_call_ids=["call_x"],
        )
        console = Console(record=True)
        console.print(tool)
        output = console.export_text()

        assert "bash" in output
        assert "1" in output

    def test_works_with_console_print(self, sample_tool: ToolCallInfo) -> None:
        """Test that Console.print(tool_info) works."""
        console = Console(record=True)
        console.print(sample_tool)
        output = console.export_text()
        assert len(output) > 0
        assert "read_file" in output


# ---------------------------------------------------------------------------
# Class: TestTurnRichConsole
# ---------------------------------------------------------------------------


class TestTurnRichConsole:
    """Tests for Turn.__rich_console__ protocol."""

    def test_has_rich_console_method(self) -> None:
        """Test that Turn has __rich_console__ method."""
        assert hasattr(Turn, "__rich_console__")

    def test_rich_print_produces_output(self, sample_turn: Turn) -> None:
        """Test that rich.print(turn) produces formatted output."""
        console = Console(record=True)
        console.print(sample_turn)
        output = console.export_text()

        assert "Turn 0" in output
        assert "[User]" in output
        assert "[Assistant]" in output

    def test_shows_system_context(self, sample_turn: Turn) -> None:
        """Test that system context appears in turn display."""
        console = Console(record=True)
        console.print(sample_turn)
        output = console.export_text()

        assert "[System]" in output
        assert "helpful assistant" in output

    def test_shows_tool_interactions(self, sample_turn: Turn) -> None:
        """Test that tool interactions appear in turn display."""
        console = Console(record=True)
        console.print(sample_turn)
        output = console.export_text()

        assert "search" in output

    def test_simple_turn_without_tools(self, simple_turn: Turn) -> None:
        """Test that a turn without tools renders cleanly."""
        console = Console(record=True)
        console.print(simple_turn)
        output = console.export_text()

        assert "Turn 1" in output
        assert "[User]" in output
        assert "What is Python?" in output
        assert "[Assistant]" in output
        assert "programming language" in output

    def test_works_with_console_print(self, sample_turn: Turn) -> None:
        """Test that Console.print(turn) works."""
        console = Console(record=True)
        console.print(sample_turn)
        output = console.export_text()
        assert len(output) > 0


# ---------------------------------------------------------------------------
# Class: TestStrMethodsPreserved
# ---------------------------------------------------------------------------


class TestStrMethodsPreserved:
    """Test that existing __str__ methods are not affected by __rich_console__."""

    def test_stats_str_unchanged(self, sample_stats: MessageStats) -> None:
        """Test that MessageStats.__str__ still produces plain text output."""
        output = str(sample_stats)

        assert output.startswith("Message Statistics")
        assert "Total messages: 10" in output
        assert "Total tokens:   1500" in output
        assert "Avg tokens/msg: 150.0" in output

    def test_tool_str_unchanged(self, sample_tool: ToolCallInfo) -> None:
        """Test that ToolCallInfo.__str__ still produces plain text output."""
        output = str(sample_tool)

        assert output.startswith("Tool: read_file")
        assert "called 3 time(s)" in output
        assert "[call_1]" in output

    def test_turn_str_unchanged(self, sample_turn: Turn) -> None:
        """Test that Turn.__str__ still produces plain text output."""
        output = str(sample_turn)

        assert output.startswith("Turn 0:")
        assert "System:" in output
        assert "User:" in output
        assert "Assistant:" in output

    def test_stats_str_not_rich_formatted(self, sample_stats: MessageStats) -> None:
        """Test that str() does not contain Rich formatting characters."""
        output = str(sample_stats)

        # Should not contain Rich table characters.
        assert "\u2500" not in output  # horizontal line
        assert "\u2502" not in output  # vertical line
        assert "\u250c" not in output  # corner

    def test_tool_str_not_rich_formatted(self, sample_tool: ToolCallInfo) -> None:
        """Test that str() does not contain Rich formatting characters."""
        output = str(sample_tool)
        assert "\u2500" not in output
        assert "\u2502" not in output

    def test_turn_str_not_rich_formatted(self, sample_turn: Turn) -> None:
        """Test that str() does not contain Rich formatting characters."""
        output = str(sample_turn)
        assert "\u2500" not in output
        assert "\u2502" not in output


# ---------------------------------------------------------------------------
# Class: TestNoImportSideEffects
# ---------------------------------------------------------------------------


class TestNoImportSideEffects:
    """Test that Rich imports are conditional and don't affect normal usage."""

    def test_rich_types_in_type_checking_only(self) -> None:
        """Test that Rich types are imported under TYPE_CHECKING only."""
        import mamba_agents.agent.messages as mod

        # The module should NOT have Console, ConsoleOptions, or RenderResult
        # as runtime attributes (they are TYPE_CHECKING only).
        # At runtime with from __future__ import annotations, these are
        # only strings, not actual imports.
        assert "Console" not in dir(mod)
        assert "ConsoleOptions" not in dir(mod)
        assert "RenderResult" not in dir(mod)

    def test_dataclass_creation_without_rich(self) -> None:
        """Test that dataclass instances can be created without Rich usage."""
        # These should work without any Rich imports at the call site.
        stats = MessageStats(total_messages=5)
        tool = ToolCallInfo(tool_name="test")
        turn = Turn(index=0)

        assert stats.total_messages == 5
        assert tool.tool_name == "test"
        assert turn.index == 0


# ---------------------------------------------------------------------------
# Class: TestIntegrationRichPrint
# ---------------------------------------------------------------------------


class TestIntegrationRichPrint:
    """Integration tests for rich.print() end-to-end."""

    def test_rich_print_stats_end_to_end(self, sample_stats: MessageStats) -> None:
        """End-to-end: rich.print(stats) runs without error and produces output."""
        console = Console(record=True)
        console.print(sample_stats)
        output = console.export_text()

        # Verify the output has expected structure.
        assert "Message Statistics" in output
        assert "Role" in output
        assert "Messages" in output
        assert "Tokens" in output

    def test_rich_print_tool_end_to_end(self, sample_tool: ToolCallInfo) -> None:
        """End-to-end: rich.print(tool_info) runs without error and produces output."""
        console = Console(record=True)
        console.print(sample_tool)
        output = console.export_text()

        assert "Tool Summary" in output
        assert "read_file" in output

    def test_rich_print_turn_end_to_end(self, sample_turn: Turn) -> None:
        """End-to-end: rich.print(turn) runs without error and produces output."""
        console = Console(record=True)
        console.print(sample_turn)
        output = console.export_text()

        assert "Turn 0" in output
        assert "[User]" in output
        assert "[Assistant]" in output

    def test_rich_print_multiple_objects(
        self,
        sample_stats: MessageStats,
        sample_tool: ToolCallInfo,
        sample_turn: Turn,
    ) -> None:
        """End-to-end: printing multiple objects to the same console."""
        console = Console(record=True)
        console.print(sample_stats)
        console.print(sample_tool)
        console.print(sample_turn)
        output = console.export_text()

        assert "Message Statistics" in output
        assert "Tool Summary" in output
        assert "Turn 0" in output
