"""Rich Console renderer for message analytics display.

Implements the ``MessageRenderer`` ABC using Rich tables, panels, and
styled text to produce formatted terminal output for message statistics,
conversation timelines, and tool call summaries.

Classes:
    RichRenderer: Concrete renderer producing Rich Console output.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mamba_agents.agent.display.renderer import MessageRenderer

if TYPE_CHECKING:
    from mamba_agents.agent.display.presets import DisplayPreset
    from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn


class RichRenderer(MessageRenderer):
    """Rich Console renderer for message analytics data.

    Produces formatted Rich Console output with tables, panels, and styled
    text for message statistics, conversation timelines, and tool call
    summaries. Output detail is controlled by a ``DisplayPreset``.

    Each render method accepts an optional ``console`` parameter. When
    provided, the method prints to that console and captures the output.
    When omitted, a new ``Console(record=True)`` is created internally.

    Example::

        from mamba_agents.agent.display.rich_renderer import RichRenderer
        from mamba_agents.agent.display.presets import DETAILED

        renderer = RichRenderer()
        output = renderer.render_stats(stats, DETAILED)
        print(output)  # already printed to console; string also returned
    """

    # ------------------------------------------------------------------
    # render_stats
    # ------------------------------------------------------------------

    def render_stats(
        self,
        stats: MessageStats,
        preset: DisplayPreset,
        *,
        console: Console | None = None,
    ) -> str:
        """Render message statistics as a Rich table.

        Produces a table with columns for Role, Messages, and Tokens (when
        ``preset.show_tokens`` is True). Includes a totals row and an
        average tokens-per-message summary line beneath the table.

        Token numbers are formatted with thousands separators (e.g.,
        ``1,234``).

        Args:
            stats: Token and message count statistics to render.
            preset: Display configuration controlling detail level.
            console: Optional Rich Console instance. When provided, output
                is printed to this console. When omitted, a new recording
                console is created.

        Returns:
            The rendered string captured from the console.
        """
        console = self._ensure_console(console)

        for renderable in self.render_stats_renderables(stats, preset):
            console.print(renderable)

        return console.export_text()

    # ------------------------------------------------------------------
    # render_timeline
    # ------------------------------------------------------------------

    def render_timeline(
        self,
        turns: list[Turn],
        preset: DisplayPreset,
        *,
        console: Console | None = None,
    ) -> str:
        """Render a conversation timeline as Rich panels.

        Each turn is rendered as a Rich Panel containing role-labelled
        content sections. Tool interactions are shown as a nested summary
        (tool name and call count). Content is truncated according to the
        preset's ``max_content_length`` unless ``expand`` is True or
        ``max_content_length`` is None.

        Args:
            turns: List of conversation turns to render.
            preset: Display configuration controlling detail level.
            console: Optional Rich Console instance.

        Returns:
            The rendered string captured from the console.
        """
        console = self._ensure_console(console)

        # Empty state.
        if not turns:
            panel = Panel("No conversation turns found", title="Timeline", expand=False)
            console.print(panel)
            return console.export_text()

        # Apply limit for pagination.
        display_turns = turns
        if preset.limit is not None:
            display_turns = turns[: preset.limit]

        for turn in display_turns:
            console.print(self.render_turn_renderable(turn, preset))

        # Show pagination indicator when turns were limited.
        if preset.limit is not None and len(turns) > preset.limit:
            remaining = len(turns) - preset.limit
            console.print(
                Text(f"... {remaining} more turn(s) not shown", style="dim italic"),
            )

        return console.export_text()

    # ------------------------------------------------------------------
    # render_tools
    # ------------------------------------------------------------------

    def render_tools(
        self,
        tools: list[ToolCallInfo],
        preset: DisplayPreset,
        *,
        console: Console | None = None,
    ) -> str:
        """Render a tool usage summary as a Rich table.

        Default (collapsed) view shows tool name and call count only.
        When ``preset.show_tool_details`` is True, expanded rows show
        arguments and results per call.

        Args:
            tools: List of tool call summaries to render.
            preset: Display configuration controlling detail level.
            console: Optional Rich Console instance.

        Returns:
            The rendered string captured from the console.
        """
        console = self._ensure_console(console)

        for renderable in self.render_tools_renderables(tools, preset):
            console.print(renderable)

        return console.export_text()

    # ------------------------------------------------------------------
    # Renderable helpers (for __rich_console__ protocol)
    # ------------------------------------------------------------------

    def render_stats_renderables(
        self,
        stats: MessageStats,
        preset: DisplayPreset,
    ) -> list[Table | Panel | Text]:
        """Build Rich renderable objects for message statistics.

        Used by ``MessageStats.__rich_console__`` to yield Rich objects
        directly to the console without creating an intermediate recording
        console.

        Args:
            stats: Token and message count statistics to render.
            preset: Display configuration controlling detail level.

        Returns:
            A list of Rich renderable objects (Table, Panel, or Text).
        """
        # Empty state.
        if stats.total_messages == 0:
            return [Panel("No messages recorded", title="Message Statistics", expand=False)]

        # Build the table.
        table = Table(title="Message Statistics")
        table.add_column("Role", style="bold cyan")
        table.add_column("Messages", justify="right")

        if preset.show_tokens:
            table.add_column("Tokens", justify="right")

        for role in sorted(stats.messages_by_role):
            msg_count = str(stats.messages_by_role[role])
            if preset.show_tokens:
                token_count = f"{stats.tokens_by_role.get(role, 0):,}"
                table.add_row(role, msg_count, token_count)
            else:
                table.add_row(role, msg_count)

        # Totals row.
        table.add_section()
        if preset.show_tokens:
            table.add_row(
                "Total",
                str(stats.total_messages),
                f"{stats.total_tokens:,}",
                style="bold",
            )
        else:
            table.add_row(
                "Total",
                str(stats.total_messages),
                style="bold",
            )

        renderables: list[Table | Panel | Text] = [table]

        # Average tokens/message summary.
        if preset.show_tokens:
            avg = stats.avg_tokens_per_message
            renderables.append(
                Text(f"Average tokens/message: {avg:,.1f}", style="dim"),
            )

        return renderables

    def render_tools_renderables(
        self,
        tools: list[ToolCallInfo],
        preset: DisplayPreset,
    ) -> list[Table | Panel]:
        """Build Rich renderable objects for a tool usage summary.

        Used by ``ToolCallInfo.__rich_console__`` to yield Rich objects
        directly to the console.

        Args:
            tools: List of tool call summaries to render.
            preset: Display configuration controlling detail level.

        Returns:
            A list of Rich renderable objects (Table or Panel).
        """
        # Empty state.
        if not tools:
            return [Panel("No tool calls recorded", title="Tool Summary", expand=False)]

        table = Table(title="Tool Summary")
        table.add_column("Tool Name", style="bold green")
        table.add_column("Calls", justify="right")

        if preset.show_tool_details:
            table.add_column("Details", no_wrap=False)

        for tool in tools:
            if preset.show_tool_details:
                details = self._format_tool_details(tool, preset)
                table.add_row(tool.tool_name, str(tool.call_count), details)
            else:
                table.add_row(tool.tool_name, str(tool.call_count))

        return [table]

    def render_turn_renderable(
        self,
        turn: Turn,
        preset: DisplayPreset,
    ) -> Panel:
        """Build a Rich Panel for a single conversation turn.

        Used by ``Turn.__rich_console__`` to yield a Panel directly to
        the console.

        Args:
            turn: A ``Turn`` instance to render.
            preset: Display configuration controlling detail level.

        Returns:
            A Rich Panel containing the formatted turn display.
        """
        sections = Text()

        # System context.
        if turn.system_context is not None:
            sections.append("[System] ", style="bold magenta")
            content = self._truncate(turn.system_context, preset)
            sections.append(content)
            sections.append("\n")

        # User content.
        if turn.user_content is not None:
            sections.append("[User] ", style="bold blue")
            content = self._truncate(turn.user_content, preset)
            sections.append(content)
            sections.append("\n")

        # Assistant content.
        if turn.assistant_content is not None:
            sections.append("[Assistant] ", style="bold yellow")
            content = self._truncate(turn.assistant_content, preset)
            sections.append(content)
            sections.append("\n")

        # Tool interactions.
        if turn.tool_interactions:
            self._render_tool_interactions(sections, turn.tool_interactions, preset)

        # Trim trailing newline if present.
        plain = sections.plain
        if plain.endswith("\n"):
            sections.truncate(len(plain) - 1)

        return Panel(sections, title=f"Turn {turn.index}", expand=False)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_console(console: Console | None) -> Console:
        """Return a recording console, wrapping a user-provided one if needed.

        If the caller supplies a console, we create a *new* recording
        console that shares the same width so the output formatting is
        consistent, then return it. This lets us always call
        ``export_text()`` on the returned console.

        Args:
            console: An optional user-supplied console.

        Returns:
            A ``Console`` instance with ``record=True``.
        """
        if console is not None:
            return Console(record=True, width=console.width)
        return Console(record=True)

    def _render_tool_interactions(
        self,
        text: Text,
        interactions: list[dict[str, Any]],
        preset: DisplayPreset,
    ) -> None:
        """Append tool interaction lines to a ``Text`` object.

        For 10+ interactions, shows a summary count. For fewer
        interactions or when ``show_tool_details`` is True, shows
        each tool individually.

        Args:
            text: The ``Text`` object to append to.
            interactions: List of tool interaction dicts.
            preset: Display configuration.
        """
        # Count tools by name for summary.
        tool_counts: dict[str, int] = {}
        for interaction in interactions:
            name = interaction.get("tool_name", "unknown")
            tool_counts[name] = tool_counts.get(name, 0) + 1

        # Show summary count for many interactions.
        if len(interactions) >= 10 and not preset.show_tool_details:
            text.append("[Tools] ", style="bold red")
            summary_parts = [f"{name} x{count}" for name, count in tool_counts.items()]
            text.append(f"{len(interactions)} calls: {', '.join(summary_parts)}")
            text.append("\n")
            return

        if preset.show_tool_details:
            # Detailed view: show args and results for each call.
            for interaction in interactions:
                name = interaction.get("tool_name", "unknown")
                text.append(f"  [Tool: {name}]\n", style="bold red")

                args = interaction.get("arguments", {})
                if args:
                    args_str = json.dumps(args, indent=2, ensure_ascii=False)
                    args_str = self._truncate_str(args_str, preset.max_tool_arg_length)
                    text.append(f"    args: {args_str}\n", style="dim")

                result = interaction.get("result", "")
                if result:
                    result_str = self._truncate_str(str(result), preset.max_tool_arg_length)
                    text.append(f"    result: {result_str}\n", style="dim")
        else:
            # Collapsed view: show tool name and call count per tool.
            text.append("[Tools] ", style="bold red")
            summary_parts = [f"{name} x{count}" for name, count in tool_counts.items()]
            text.append(", ".join(summary_parts))
            text.append("\n")

    def _truncate(self, content: str, preset: DisplayPreset) -> str:
        """Truncate content based on preset settings.

        Returns the full content when ``preset.expand`` is True or
        ``preset.max_content_length`` is None. Otherwise truncates at
        ``max_content_length`` with a ``"... (N more characters)"``
        indicator.

        Args:
            content: The text to possibly truncate.
            preset: Display configuration with truncation settings.

        Returns:
            The (possibly truncated) content string.
        """
        if preset.expand or preset.max_content_length is None:
            return content

        if len(content) <= preset.max_content_length:
            return content

        remaining = len(content) - preset.max_content_length
        return content[: preset.max_content_length] + f"... ({remaining} more characters)"

    @staticmethod
    def _truncate_str(text: str, max_length: int | None) -> str:
        """Truncate a plain string to a maximum length.

        Args:
            text: The text to truncate.
            max_length: Maximum character length, or None for no limit.

        Returns:
            The (possibly truncated) string with ``"..."`` suffix.
        """
        if max_length is None or len(text) <= max_length:
            return text
        remaining = len(text) - max_length
        return text[:max_length] + f"... ({remaining} more characters)"

    @staticmethod
    def _format_tool_details(tool: Any, preset: DisplayPreset) -> str:
        """Format detailed tool call information as a multi-line string.

        Args:
            tool: A ``ToolCallInfo`` instance.
            preset: Display configuration with truncation settings.

        Returns:
            A multi-line string with args and results per call.
        """
        lines: list[str] = []
        for i in range(tool.call_count):
            call_id = tool.tool_call_ids[i] if i < len(tool.tool_call_ids) else ""
            header = f"[{call_id}]" if call_id else f"[call {i}]"
            lines.append(header)

            if i < len(tool.arguments):
                args_str = json.dumps(tool.arguments[i], indent=2, ensure_ascii=False)
                max_len = preset.max_tool_arg_length
                if max_len is not None and len(args_str) > max_len:
                    remaining = len(args_str) - max_len
                    args_str = args_str[:max_len] + f"... ({remaining} more characters)"
                lines.append(f"  args: {args_str}")

            if i < len(tool.results):
                result_str = str(tool.results[i])
                max_len = preset.max_tool_arg_length
                if max_len is not None and len(result_str) > max_len:
                    remaining = len(result_str) - max_len
                    result_str = result_str[:max_len] + f"... ({remaining} more characters)"
                lines.append(f"  result: {result_str}")

        return "\n".join(lines)
