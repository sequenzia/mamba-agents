"""Display preset definitions for message rendering.

Provides the ``DisplayPreset`` dataclass and three named presets that
control how much detail renderers include in their output.

Named presets:
    compact: Minimal output -- counts only, short truncation, no tool details.
    detailed: Balanced output -- full tables, moderate truncation, no tool details.
    verbose: Maximum output -- expanded content, no truncation, full tool args/results.

Functions:
    get_preset: Factory function to retrieve a named preset with optional overrides.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class DisplayPreset:
    """Configuration controlling how much detail renderers include.

    Attributes:
        show_tokens: Whether to show token counts in stats output.
        max_content_length: Content truncation length in characters.
            ``None`` disables truncation, showing full content.
        expand: Whether to show full content (overrides truncation).
        show_tool_details: Whether to show tool arguments and results.
        max_tool_arg_length: Truncation length for tool argument strings.
        limit: Maximum items to display (e.g., turns in timeline).
            ``None`` means no limit.
    """

    show_tokens: bool = True
    max_content_length: int | None = 300
    expand: bool = False
    show_tool_details: bool = False
    max_tool_arg_length: int = 200
    limit: int | None = None


# ---------------------------------------------------------------------------
# Named presets
# ---------------------------------------------------------------------------

COMPACT = DisplayPreset(
    show_tokens=False,
    max_content_length=100,
    expand=False,
    show_tool_details=False,
    max_tool_arg_length=50,
    limit=None,
)
"""Minimal output: counts only, short truncation, no tool details."""

DETAILED = DisplayPreset(
    show_tokens=True,
    max_content_length=300,
    expand=False,
    show_tool_details=False,
    max_tool_arg_length=200,
    limit=None,
)
"""Balanced output: full tables, moderate truncation, no tool details."""

VERBOSE = DisplayPreset(
    show_tokens=True,
    max_content_length=None,
    expand=True,
    show_tool_details=True,
    max_tool_arg_length=500,
    limit=None,
)
"""Maximum output: expanded content, no truncation, full tool args/results."""

#: Registry of named presets.
_PRESETS: dict[str, DisplayPreset] = {
    "compact": COMPACT,
    "detailed": DETAILED,
    "verbose": VERBOSE,
}


def get_preset(name: str = "detailed", **overrides: Any) -> DisplayPreset:
    """Retrieve a named preset, optionally overriding individual fields.

    Args:
        name: Preset name. Must be one of ``"compact"``, ``"detailed"``,
            or ``"verbose"``.
        **overrides: Keyword arguments matching ``DisplayPreset`` fields.
            These take precedence over the preset's default values.

    Returns:
        A ``DisplayPreset`` instance with the requested configuration.

    Raises:
        ValueError: If *name* is not a recognised preset name. The error
            message includes the list of valid preset names.

    Examples:
        Get the default preset::

            preset = get_preset()  # returns 'detailed'

        Get compact with token display enabled::

            preset = get_preset("compact", show_tokens=True)
    """
    base = _PRESETS.get(name)
    if base is None:
        valid = ", ".join(sorted(_PRESETS))
        raise ValueError(f"Unknown preset name: {name!r}. Valid presets: {valid}")

    if not overrides:
        return base

    return replace(base, **overrides)
