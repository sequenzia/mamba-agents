"""Abstract base class for message renderers.

Defines the ``MessageRenderer`` ABC that all format-specific renderers
(Rich, plain text, HTML) must implement. Each renderer produces a string
representation of analytics data using a given ``DisplayPreset``.

Classes:
    MessageRenderer: ABC defining render_stats, render_timeline, render_tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mamba_agents.agent.display.presets import DisplayPreset
    from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn


class MessageRenderer(ABC):
    """Abstract base class for message display renderers.

    Implementations produce formatted string output for three data types:
    message statistics, conversation timeline, and tool call summaries.
    Each method receives the data and a ``DisplayPreset`` that controls
    how much detail to include.

    Concrete implementations include ``RichRenderer``, ``PlainTextRenderer``,
    and ``HtmlRenderer``.
    """

    @abstractmethod
    def render_stats(self, stats: MessageStats, preset: DisplayPreset) -> str:
        """Render message statistics as a formatted string.

        Args:
            stats: Token and message count statistics to render.
            preset: Display configuration controlling detail level.

        Returns:
            Formatted string representation of the statistics.
        """
        ...

    @abstractmethod
    def render_timeline(self, turns: list[Turn], preset: DisplayPreset) -> str:
        """Render a conversation timeline as a formatted string.

        Args:
            turns: List of conversation turns to render.
            preset: Display configuration controlling detail level.

        Returns:
            Formatted string representation of the timeline.
        """
        ...

    @abstractmethod
    def render_tools(self, tools: list[ToolCallInfo], preset: DisplayPreset) -> str:
        """Render a tool usage summary as a formatted string.

        Args:
            tools: List of tool call summaries to render.
            preset: Display configuration controlling detail level.

        Returns:
            Formatted string representation of the tool summary.
        """
        ...
