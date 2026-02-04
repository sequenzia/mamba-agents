"""Standalone helper functions for formatted message display.

Provides ``print_stats``, ``print_timeline``, and ``print_tools`` as the
public convenience API for the display system.  Each function resolves a
named preset, applies caller overrides, selects a renderer by format
name, and delegates to the renderer's corresponding method.

Functions:
    print_stats: Render message statistics in the chosen format.
    print_timeline: Render a conversation timeline in the chosen format.
    print_tools: Render a tool usage summary in the chosen format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mamba_agents.agent.display.html_renderer import HtmlRenderer
from mamba_agents.agent.display.plain_renderer import PlainTextRenderer
from mamba_agents.agent.display.presets import get_preset
from mamba_agents.agent.display.rich_renderer import RichRenderer

if TYPE_CHECKING:
    from rich.console import Console

    from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn

#: Supported format names mapped to their renderer classes.
_FORMATS: dict[str, type] = {
    "rich": RichRenderer,
    "plain": PlainTextRenderer,
    "html": HtmlRenderer,
}


def _resolve_renderer(format: str) -> RichRenderer | PlainTextRenderer | HtmlRenderer:
    """Create a renderer instance for the given format name.

    Args:
        format: One of ``"rich"``, ``"plain"``, or ``"html"``.

    Returns:
        A renderer instance matching the requested format.

    Raises:
        ValueError: If *format* is not a recognised format name.  The error
            message includes the list of valid format names.
    """
    cls = _FORMATS.get(format)
    if cls is None:
        valid = ", ".join(sorted(_FORMATS))
        raise ValueError(f"Unknown format: {format!r}. Valid formats: {valid}")
    return cls()


def print_stats(
    stats: MessageStats,
    *,
    preset: str = "detailed",
    format: str = "rich",
    console: Console | None = None,
    **options: Any,
) -> str:
    """Render message statistics in the chosen format.

    Resolves the named *preset*, applies any keyword *options* as
    overrides, selects the renderer matching *format*, and delegates
    to its ``render_stats`` method.

    Args:
        stats: Token and message count statistics to render.
        preset: Named preset (``"compact"``, ``"detailed"``, or
            ``"verbose"``).
        format: Output format (``"rich"``, ``"plain"``, or ``"html"``).
        console: Optional Rich ``Console`` instance. Only used when
            *format* is ``"rich"``.
        **options: Keyword overrides applied to the resolved preset
            (e.g., ``show_tokens=False``).

    Returns:
        The rendered string.

    Raises:
        ValueError: If *preset* or *format* is not recognised.

    Example::

        from mamba_agents.agent.display import print_stats

        output = print_stats(stats)  # Rich table to terminal
        output = print_stats(stats, format="plain")  # ASCII table
        output = print_stats(stats, preset="compact", show_tokens=True)
    """
    resolved_preset = get_preset(preset, **options)
    renderer = _resolve_renderer(format)

    if isinstance(renderer, RichRenderer):
        return renderer.render_stats(stats, resolved_preset, console=console)
    return renderer.render_stats(stats, resolved_preset)


def print_timeline(
    turns: list[Turn],
    *,
    preset: str = "detailed",
    format: str = "rich",
    console: Console | None = None,
    **options: Any,
) -> str:
    """Render a conversation timeline in the chosen format.

    Resolves the named *preset*, applies any keyword *options* as
    overrides, selects the renderer matching *format*, and delegates
    to its ``render_timeline`` method.

    Args:
        turns: List of conversation turns to render.
        preset: Named preset (``"compact"``, ``"detailed"``, or
            ``"verbose"``).
        format: Output format (``"rich"``, ``"plain"``, or ``"html"``).
        console: Optional Rich ``Console`` instance. Only used when
            *format* is ``"rich"``.
        **options: Keyword overrides applied to the resolved preset
            (e.g., ``limit=10``).

    Returns:
        The rendered string.

    Raises:
        ValueError: If *preset* or *format* is not recognised.

    Example::

        from mamba_agents.agent.display import print_timeline

        output = print_timeline(turns)  # Rich panels to terminal
        output = print_timeline(turns, format="html")  # HTML sections
        output = print_timeline(turns, preset="verbose", limit=5)
    """
    resolved_preset = get_preset(preset, **options)
    renderer = _resolve_renderer(format)

    if isinstance(renderer, RichRenderer):
        return renderer.render_timeline(turns, resolved_preset, console=console)
    return renderer.render_timeline(turns, resolved_preset)


def print_tools(
    tools: list[ToolCallInfo],
    *,
    preset: str = "detailed",
    format: str = "rich",
    console: Console | None = None,
    **options: Any,
) -> str:
    """Render a tool usage summary in the chosen format.

    Resolves the named *preset*, applies any keyword *options* as
    overrides, selects the renderer matching *format*, and delegates
    to its ``render_tools`` method.

    Args:
        tools: List of tool call summaries to render.
        preset: Named preset (``"compact"``, ``"detailed"``, or
            ``"verbose"``).
        format: Output format (``"rich"``, ``"plain"``, or ``"html"``).
        console: Optional Rich ``Console`` instance. Only used when
            *format* is ``"rich"``.
        **options: Keyword overrides applied to the resolved preset
            (e.g., ``show_tool_details=True``).

    Returns:
        The rendered string.

    Raises:
        ValueError: If *preset* or *format* is not recognised.

    Example::

        from mamba_agents.agent.display import print_tools

        output = print_tools(tools)  # Rich table to terminal
        output = print_tools(tools, format="plain")  # ASCII table
        output = print_tools(tools, preset="verbose")
    """
    resolved_preset = get_preset(preset, **options)
    renderer = _resolve_renderer(format)

    if isinstance(renderer, RichRenderer):
        return renderer.render_tools(tools, resolved_preset, console=console)
    return renderer.render_tools(tools, resolved_preset)
