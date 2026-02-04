"""HTML renderer for message analytics display.

Implements the ``MessageRenderer`` ABC using semantic HTML tables and
sections. Produces self-contained HTML suitable for display in Jupyter
notebooks via ``IPython.display.HTML``, without any external CSS or
JavaScript dependencies.

Classes:
    HtmlRenderer: Concrete renderer producing HTML string output.
"""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING, Any

from mamba_agents.agent.display.renderer import MessageRenderer

if TYPE_CHECKING:
    from mamba_agents.agent.display.presets import DisplayPreset
    from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn


class HtmlRenderer(MessageRenderer):
    """HTML renderer for message analytics data.

    Produces self-contained HTML string output with semantic markup
    (``<table>``, ``<th>``, ``<td>``, ``<caption>``) for message statistics,
    conversation timelines, and tool call summaries. Output detail is
    controlled by a ``DisplayPreset``.

    The generated HTML uses no external CSS or JavaScript dependencies and
    is designed to render cleanly in Jupyter notebooks via
    ``IPython.display.HTML``.

    Example::

        from mamba_agents.agent.display.html_renderer import HtmlRenderer
        from mamba_agents.agent.display.presets import DETAILED

        renderer = HtmlRenderer()
        html_str = renderer.render_stats(stats, DETAILED)
        # In Jupyter: IPython.display.HTML(html_str)
    """

    # ------------------------------------------------------------------
    # render_stats
    # ------------------------------------------------------------------

    def render_stats(self, stats: MessageStats, preset: DisplayPreset) -> str:
        """Render message statistics as an HTML table.

        Produces a ``<table>`` with columns for Role, Messages, and Tokens
        (when ``preset.show_tokens`` is True). Includes a totals row and
        an average tokens-per-message summary paragraph beneath the table.

        Token numbers are formatted with thousands separators (e.g.,
        ``1,234``).

        Args:
            stats: Token and message count statistics to render.
            preset: Display configuration controlling detail level.

        Returns:
            A self-contained HTML string.
        """
        # Empty state.
        if stats.total_messages == 0:
            return "<p>No messages recorded</p>"

        parts: list[str] = []
        parts.append("<table>")
        parts.append("<caption>Message Statistics</caption>")

        # Header row.
        parts.append("<thead>")
        parts.append("<tr>")
        parts.append("<th>Role</th>")
        parts.append("<th>Messages</th>")
        if preset.show_tokens:
            parts.append("<th>Tokens</th>")
        parts.append("</tr>")
        parts.append("</thead>")

        # Body rows, sorted alphabetically by role.
        parts.append("<tbody>")
        for role in sorted(stats.messages_by_role):
            msg_count = stats.messages_by_role[role]
            parts.append("<tr>")
            parts.append(f"<td>{html.escape(role)}</td>")
            parts.append(f"<td>{msg_count}</td>")
            if preset.show_tokens:
                token_count = stats.tokens_by_role.get(role, 0)
                parts.append(f"<td>{token_count:,}</td>")
            parts.append("</tr>")
        parts.append("</tbody>")

        # Totals row in tfoot.
        parts.append("<tfoot>")
        parts.append("<tr>")
        parts.append("<td><strong>Total</strong></td>")
        parts.append(f"<td><strong>{stats.total_messages}</strong></td>")
        if preset.show_tokens:
            parts.append(f"<td><strong>{stats.total_tokens:,}</strong></td>")
        parts.append("</tr>")
        parts.append("</tfoot>")

        parts.append("</table>")

        # Average tokens/message summary.
        if preset.show_tokens:
            avg = stats.avg_tokens_per_message
            parts.append(f"<p>Average tokens/message: {avg:,.1f}</p>")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # render_timeline
    # ------------------------------------------------------------------

    def render_timeline(self, turns: list[Turn], preset: DisplayPreset) -> str:
        """Render a conversation timeline as HTML sections.

        Each turn is rendered as a ``<section>`` containing role-labelled
        content. Tool interactions are shown as nested summaries.
        Content is truncated according to the preset's
        ``max_content_length`` unless ``expand`` is True or
        ``max_content_length`` is None.

        Args:
            turns: List of conversation turns to render.
            preset: Display configuration controlling detail level.

        Returns:
            A self-contained HTML string.
        """
        # Empty state.
        if not turns:
            return "<p>No conversation turns found</p>"

        # Apply limit for pagination.
        display_turns = turns
        if preset.limit is not None:
            display_turns = turns[: preset.limit]

        parts: list[str] = []
        for turn in display_turns:
            parts.append(self._render_turn(turn, preset))

        # Show pagination indicator when turns were limited.
        if preset.limit is not None and len(turns) > preset.limit:
            remaining = len(turns) - preset.limit
            parts.append(f"<p><em>... {remaining} more turn(s) not shown</em></p>")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # render_tools
    # ------------------------------------------------------------------

    def render_tools(self, tools: list[ToolCallInfo], preset: DisplayPreset) -> str:
        """Render a tool usage summary as an HTML table.

        Default (collapsed) view shows tool name and call count only.
        When ``preset.show_tool_details`` is True, a third Details column
        shows arguments and results per call.

        Args:
            tools: List of tool call summaries to render.
            preset: Display configuration controlling detail level.

        Returns:
            A self-contained HTML string.
        """
        # Empty state.
        if not tools:
            return "<p>No tool calls recorded</p>"

        parts: list[str] = []
        parts.append("<table>")
        parts.append("<caption>Tool Summary</caption>")

        # Header row.
        parts.append("<thead>")
        parts.append("<tr>")
        parts.append("<th>Tool Name</th>")
        parts.append("<th>Calls</th>")
        if preset.show_tool_details:
            parts.append("<th>Details</th>")
        parts.append("</tr>")
        parts.append("</thead>")

        # Body rows.
        parts.append("<tbody>")
        for tool in tools:
            parts.append("<tr>")
            parts.append(f"<td>{html.escape(tool.tool_name)}</td>")
            parts.append(f"<td>{tool.call_count}</td>")
            if preset.show_tool_details:
                details = self._format_tool_details(tool, preset)
                parts.append(f"<td>{details}</td>")
            parts.append("</tr>")
        parts.append("</tbody>")

        parts.append("</table>")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render_turn(self, turn: Any, preset: DisplayPreset) -> str:
        """Render a single conversation turn as an HTML section.

        Args:
            turn: A ``Turn`` instance.
            preset: Display configuration controlling detail level.

        Returns:
            An HTML ``<section>`` string for this turn.
        """
        parts: list[str] = []
        parts.append("<section>")
        parts.append(f"<h3>Turn {turn.index}</h3>")

        # System context.
        if turn.system_context is not None:
            content = self._truncate(turn.system_context, preset)
            parts.append(f"<p><strong>[System]</strong> {html.escape(content)}</p>")

        # User content.
        if turn.user_content is not None:
            content = self._truncate(turn.user_content, preset)
            parts.append(f"<p><strong>[User]</strong> {html.escape(content)}</p>")

        # Assistant content.
        if turn.assistant_content is not None:
            content = self._truncate(turn.assistant_content, preset)
            parts.append(f"<p><strong>[Assistant]</strong> {html.escape(content)}</p>")

        # Tool interactions.
        if turn.tool_interactions:
            parts.append(self._render_tool_interactions(turn.tool_interactions, preset))

        parts.append("</section>")
        return "\n".join(parts)

    def _render_tool_interactions(
        self,
        interactions: list[dict[str, Any]],
        preset: DisplayPreset,
    ) -> str:
        """Render tool interaction lines as HTML.

        For 10+ interactions, shows a summary count. For fewer
        interactions or when ``show_tool_details`` is True, shows
        each tool individually.

        Args:
            interactions: List of tool interaction dicts.
            preset: Display configuration.

        Returns:
            An HTML string with tool interaction details.
        """
        parts: list[str] = []

        # Count tools by name for summary.
        tool_counts: dict[str, int] = {}
        for interaction in interactions:
            name = interaction.get("tool_name", "unknown")
            tool_counts[name] = tool_counts.get(name, 0) + 1

        # Show summary count for many interactions.
        if len(interactions) >= 10 and not preset.show_tool_details:
            summary_parts = [f"{html.escape(name)} x{count}" for name, count in tool_counts.items()]
            parts.append(
                f"<p><strong>[Tools]</strong> "
                f"{len(interactions)} calls: {', '.join(summary_parts)}</p>"
            )
            return "\n".join(parts)

        if preset.show_tool_details:
            # Detailed view: show args and results for each call.
            parts.append("<ul>")
            for interaction in interactions:
                name = interaction.get("tool_name", "unknown")
                parts.append(f"<li><strong>{html.escape(name)}</strong>")

                args = interaction.get("arguments", {})
                if args:
                    args_str = json.dumps(args, indent=2, ensure_ascii=False)
                    args_str = self._truncate_str(args_str, preset.max_tool_arg_length)
                    parts.append(f"<br>args: <code>{html.escape(args_str)}</code>")

                result = interaction.get("result", "")
                if result:
                    result_str = self._truncate_str(str(result), preset.max_tool_arg_length)
                    parts.append(f"<br>result: <code>{html.escape(result_str)}</code>")

                parts.append("</li>")
            parts.append("</ul>")
        else:
            # Collapsed view: show tool name and call count per tool.
            summary_parts = [f"{html.escape(name)} x{count}" for name, count in tool_counts.items()]
            parts.append(f"<p><strong>[Tools]</strong> {', '.join(summary_parts)}</p>")

        return "\n".join(parts)

    @staticmethod
    def _format_tool_details(tool: Any, preset: DisplayPreset) -> str:
        """Format detailed tool call information as HTML.

        Args:
            tool: A ``ToolCallInfo`` instance.
            preset: Display configuration with truncation settings.

        Returns:
            An HTML fragment with args and results per call.
        """
        lines: list[str] = []
        for i in range(tool.call_count):
            call_id = tool.tool_call_ids[i] if i < len(tool.tool_call_ids) else ""
            header = f"[{html.escape(call_id)}]" if call_id else f"[call {i}]"
            lines.append(f"<strong>{header}</strong>")

            if i < len(tool.arguments):
                args_str = json.dumps(tool.arguments[i], indent=2, ensure_ascii=False)
                max_len = preset.max_tool_arg_length
                if max_len is not None and len(args_str) > max_len:
                    remaining = len(args_str) - max_len
                    args_str = args_str[:max_len] + f"... ({remaining} more characters)"
                lines.append(f"<br>args: <code>{html.escape(args_str)}</code>")

            if i < len(tool.results):
                result_str = str(tool.results[i])
                max_len = preset.max_tool_arg_length
                if max_len is not None and len(result_str) > max_len:
                    remaining = len(result_str) - max_len
                    result_str = result_str[:max_len] + f"... ({remaining} more characters)"
                lines.append(f"<br>result: <code>{html.escape(result_str)}</code>")

        return "<br>".join(lines)

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
