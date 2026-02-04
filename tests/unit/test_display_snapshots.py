"""Snapshot (golden file) tests for display renderers.

Compares rendered output from all renderer x preset x data type combinations
against stored expected output files. This catches visual regressions that
unit tests on data alone would miss.

Set ``UPDATE_SNAPSHOTS=1`` in the environment to regenerate golden files::

    UPDATE_SNAPSHOTS=1 uv run pytest tests/unit/test_display_snapshots.py

Snapshot files live in ``tests/unit/snapshots/display/``.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from rich.console import Console

from mamba_agents.agent.display.html_renderer import HtmlRenderer
from mamba_agents.agent.display.plain_renderer import PlainTextRenderer
from mamba_agents.agent.display.presets import COMPACT, DETAILED, VERBOSE, DisplayPreset
from mamba_agents.agent.display.rich_renderer import RichRenderer
from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "display"
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"

# Rich console width fixed for deterministic output across environments.
RICH_CONSOLE_WIDTH = 100

# ---------------------------------------------------------------------------
# Deterministic test data
# ---------------------------------------------------------------------------


def _make_stats() -> MessageStats:
    """Create fixed MessageStats with deterministic values."""
    return MessageStats(
        total_messages=10,
        messages_by_role={"assistant": 4, "system": 1, "tool": 2, "user": 3},
        total_tokens=3500,
        tokens_by_role={"assistant": 1500, "system": 200, "tool": 800, "user": 1000},
    )


def _make_empty_stats() -> MessageStats:
    """Create an empty MessageStats."""
    return MessageStats()


def _make_turns() -> list[Turn]:
    """Create fixed Turn list with deterministic values."""
    return [
        Turn(
            index=0,
            system_context="You are a helpful coding assistant.",
            user_content="Please read the config file.",
            assistant_content="I will read the config file for you.",
        ),
        Turn(
            index=1,
            user_content="What does it contain?",
            assistant_content="The config file contains database settings.",
            tool_interactions=[
                {
                    "tool_name": "read_file",
                    "tool_call_id": "call_001",
                    "arguments": {"path": "config.yaml"},
                    "result": "database:\n  host: localhost\n  port: 5432",
                },
            ],
        ),
        Turn(
            index=2,
            user_content="Now write a summary to output.txt.",
            assistant_content="Done! I wrote the summary.",
            tool_interactions=[
                {
                    "tool_name": "read_file",
                    "tool_call_id": "call_002",
                    "arguments": {"path": "config.yaml"},
                    "result": "database:\n  host: localhost\n  port: 5432",
                },
                {
                    "tool_name": "write_file",
                    "tool_call_id": "call_003",
                    "arguments": {"path": "output.txt", "content": "Summary of config."},
                    "result": "OK",
                },
            ],
        ),
    ]


def _make_empty_turns() -> list[Turn]:
    """Create an empty Turn list."""
    return []


def _make_tools() -> list[ToolCallInfo]:
    """Create fixed ToolCallInfo list with deterministic values."""
    return [
        ToolCallInfo(
            tool_name="read_file",
            call_count=3,
            arguments=[
                {"path": "config.yaml"},
                {"path": "config.yaml"},
                {"path": "README.md"},
            ],
            results=[
                "database:\n  host: localhost\n  port: 5432",
                "database:\n  host: localhost\n  port: 5432",
                "# Project README\nWelcome to the project.",
            ],
            tool_call_ids=["call_001", "call_002", "call_004"],
        ),
        ToolCallInfo(
            tool_name="write_file",
            call_count=1,
            arguments=[{"path": "output.txt", "content": "Summary of config."}],
            results=["OK"],
            tool_call_ids=["call_003"],
        ),
    ]


def _make_empty_tools() -> list[ToolCallInfo]:
    """Create an empty ToolCallInfo list."""
    return []


# ---------------------------------------------------------------------------
# Renderer helpers
# ---------------------------------------------------------------------------

_RENDERERS = {
    "rich": "rich",
    "plain": "plain",
    "html": "html",
}

_PRESETS: dict[str, DisplayPreset] = {
    "compact": COMPACT,
    "detailed": DETAILED,
    "verbose": VERBOSE,
}


def _render(
    renderer_name: str,
    data_type: str,
    preset: DisplayPreset,
    data: MessageStats | list[Turn] | list[ToolCallInfo],
) -> str:
    """Render the given data with the specified renderer and preset.

    Args:
        renderer_name: One of ``"rich"``, ``"plain"``, ``"html"``.
        data_type: One of ``"stats"``, ``"timeline"``, ``"tools"``.
        preset: The display preset to use.
        data: The data to render.

    Returns:
        The rendered string output.
    """
    if renderer_name == "rich":
        renderer = RichRenderer()
        # Use a fixed-width, non-terminal console to avoid ANSI codes
        # and ensure deterministic output.
        console = Console(
            record=True,
            width=RICH_CONSOLE_WIDTH,
            force_terminal=False,
        )
        if data_type == "stats":
            return renderer.render_stats(data, preset, console=console)  # type: ignore[arg-type]
        elif data_type == "timeline":
            return renderer.render_timeline(data, preset, console=console)  # type: ignore[arg-type]
        else:
            return renderer.render_tools(data, preset, console=console)  # type: ignore[arg-type]

    elif renderer_name == "plain":
        renderer_plain = PlainTextRenderer()
        sink = io.StringIO()
        if data_type == "stats":
            return renderer_plain.render_stats(data, preset, file=sink)  # type: ignore[arg-type]
        elif data_type == "timeline":
            return renderer_plain.render_timeline(data, preset, file=sink)  # type: ignore[arg-type]
        else:
            return renderer_plain.render_tools(data, preset, file=sink)  # type: ignore[arg-type]

    else:  # html
        renderer_html = HtmlRenderer()
        if data_type == "stats":
            return renderer_html.render_stats(data, preset)  # type: ignore[arg-type]
        elif data_type == "timeline":
            return renderer_html.render_timeline(data, preset)  # type: ignore[arg-type]
        else:
            return renderer_html.render_tools(data, preset)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------


def _snapshot_path(renderer_name: str, data_type: str, preset_name: str) -> Path:
    """Build the golden file path for a given combination.

    HTML renderer uses ``.html`` extension; others use ``.txt``.
    """
    ext = "html" if renderer_name == "html" else "txt"
    return SNAPSHOT_DIR / f"{renderer_name}_{data_type}_{preset_name}.{ext}"


def _assert_snapshot(
    renderer_name: str,
    data_type: str,
    preset_name: str,
    actual: str,
) -> None:
    """Compare rendered output against the golden file.

    When ``UPDATE_SNAPSHOTS`` is set, writes the actual output as the new
    golden file instead of comparing.
    """
    path = _snapshot_path(renderer_name, data_type, preset_name)

    if UPDATE_SNAPSHOTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return

    assert path.exists(), (
        f"Snapshot file not found: {path}\n"
        f"Run with UPDATE_SNAPSHOTS=1 to generate golden files."
    )
    expected = path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"Snapshot mismatch for {path.name}.\n"
        f"Run with UPDATE_SNAPSHOTS=1 to update golden files.\n"
        f"--- Expected (first 500 chars) ---\n{expected[:500]}\n"
        f"--- Actual (first 500 chars) ---\n{actual[:500]}"
    )


# ---------------------------------------------------------------------------
# Data factory lookup
# ---------------------------------------------------------------------------

_DATA_FACTORIES = {
    "stats": _make_stats,
    "timeline": _make_turns,
    "tools": _make_tools,
}

_EMPTY_DATA_FACTORIES = {
    "stats": _make_empty_stats,
    "timeline": _make_empty_turns,
    "tools": _make_empty_tools,
}


# ---------------------------------------------------------------------------
# Tests: 27 normal snapshots (3 renderers x 3 presets x 3 data types)
# ---------------------------------------------------------------------------

_RENDERER_NAMES = ["rich", "plain", "html"]
_PRESET_NAMES = ["compact", "detailed", "verbose"]
_DATA_TYPES = ["stats", "timeline", "tools"]


class TestNormalSnapshots:
    """Snapshot tests for all renderer x preset x data type combinations."""

    @pytest.mark.parametrize("renderer_name", _RENDERER_NAMES)
    @pytest.mark.parametrize("preset_name", _PRESET_NAMES)
    @pytest.mark.parametrize("data_type", _DATA_TYPES)
    def test_snapshot(
        self,
        renderer_name: str,
        preset_name: str,
        data_type: str,
    ) -> None:
        """Rendered output matches golden file for {renderer}_{data}_{preset}."""
        data = _DATA_FACTORIES[data_type]()
        preset = _PRESETS[preset_name]
        actual = _render(renderer_name, data_type, preset, data)
        _assert_snapshot(renderer_name, data_type, preset_name, actual)


# ---------------------------------------------------------------------------
# Tests: 9 empty state snapshots (3 renderers x 3 data types)
# ---------------------------------------------------------------------------


class TestEmptyStateSnapshots:
    """Snapshot tests for empty data across all renderers."""

    @pytest.mark.parametrize("renderer_name", _RENDERER_NAMES)
    @pytest.mark.parametrize("data_type", _DATA_TYPES)
    def test_empty_snapshot(
        self,
        renderer_name: str,
        data_type: str,
    ) -> None:
        """Empty-state rendered output matches golden file for {renderer}_{data}_empty."""
        data = _EMPTY_DATA_FACTORIES[data_type]()
        # Use DETAILED preset for empty state snapshots (matches default behaviour).
        preset = _PRESETS["detailed"]
        actual = _render(renderer_name, data_type, preset, data)
        _assert_snapshot(renderer_name, data_type, "empty", actual)


# ---------------------------------------------------------------------------
# Tests: Determinism verification
# ---------------------------------------------------------------------------


class TestDeterministicOutput:
    """Verify that rendering the same data twice produces identical output."""

    @pytest.mark.parametrize("renderer_name", _RENDERER_NAMES)
    @pytest.mark.parametrize("data_type", _DATA_TYPES)
    def test_deterministic_output(
        self,
        renderer_name: str,
        data_type: str,
    ) -> None:
        """Same data + same renderer + same preset always yields the same string."""
        data = _DATA_FACTORIES[data_type]()
        preset = _PRESETS["detailed"]
        first = _render(renderer_name, data_type, preset, data)
        second = _render(renderer_name, data_type, preset, data)
        assert first == second, (
            f"Non-deterministic output from {renderer_name} renderer "
            f"for {data_type} data."
        )
