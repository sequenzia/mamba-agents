"""Plain text renderer for message analytics display.

Implements the ``MessageRenderer`` ABC using pure ASCII text with aligned
columns. Produces clean formatted output suitable for terminals, log files,
and screen readers without any Rich library dependency in the output.

Classes:
    PlainTextRenderer: Concrete renderer producing ASCII text output.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any

from mamba_agents.agent.display.renderer import MessageRenderer

if TYPE_CHECKING:
    from mamba_agents.agent.display.presets import DisplayPreset
    from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn


class PlainTextRenderer(MessageRenderer):
    """Plain text renderer for message analytics data.

    Produces formatted ASCII text output with aligned columns for message
    statistics, conversation timelines, and tool call summaries. Output
    detail is controlled by a ``DisplayPreset``.

    Each render method prints to stdout and returns the output as a string.
    An optional ``file`` parameter can redirect output to a different stream.

    Example::

        from mamba_agents.agent.display.plain_renderer import PlainTextRenderer
        from mamba_agents.agent.display.presets import DETAILED

        renderer = PlainTextRenderer()
        output = renderer.render_stats(stats, DETAILED)
        # Output has already been printed to stdout; string also returned.
    """

    # ------------------------------------------------------------------
    # render_stats
    # ------------------------------------------------------------------

    def render_stats(
        self,
        stats: MessageStats,
        preset: DisplayPreset,
        *,
        file: Any | None = None,
    ) -> str:
        """Render message statistics as an ASCII table.

        Produces a table with columns for Role, Messages, and Tokens (when
        ``preset.show_tokens`` is True). Includes a totals row and an
        average tokens-per-message summary line beneath the table.

        Token numbers are formatted with thousands separators (e.g.,
        ``1,234``).

        Args:
            stats: Token and message count statistics to render.
            preset: Display configuration controlling detail level.
            file: Optional output stream. Defaults to ``sys.stdout``.

        Returns:
            The rendered string.
        """
        output_file = file if file is not None else sys.stdout

        # Empty state.
        if stats.total_messages == 0:
            text = "No messages recorded"
            print(text, file=output_file)
            return text

        lines: list[str] = []
        lines.append("Message Statistics")
        lines.append("")

        # Collect rows: (role, message_count, token_count).
        rows: list[tuple[str, str, str]] = []
        for role in sorted(stats.messages_by_role):
            msg_count = str(stats.messages_by_role[role])
            token_count = f"{stats.tokens_by_role.get(role, 0):,}"
            rows.append((role, msg_count, token_count))

        # Totals row.
        total_msg = str(stats.total_messages)
        total_tok = f"{stats.total_tokens:,}"

        # Calculate column widths.
        role_header = "Role"
        msg_header = "Messages"
        tok_header = "Tokens"

        role_width = max(
            len(role_header),
            max((len(r[0]) for r in rows), default=0),
            len("Total"),
        )
        msg_width = max(
            len(msg_header),
            max((len(r[1]) for r in rows), default=0),
            len(total_msg),
        )

        if preset.show_tokens:
            tok_width = max(
                len(tok_header),
                max((len(r[2]) for r in rows), default=0),
                len(total_tok),
            )
            header = (
                f"  {role_header:<{role_width}}"
                f"  {msg_header:>{msg_width}}"
                f"  {tok_header:>{tok_width}}"
            )
            separator = f"  {'-' * role_width}  {'-' * msg_width}  {'-' * tok_width}"
        else:
            header = f"  {role_header:<{role_width}}  {msg_header:>{msg_width}}"
            separator = f"  {'-' * role_width}  {'-' * msg_width}"

        lines.append(header)
        lines.append(separator)

        # Data rows.
        for role, msg_count, token_count in rows:
            if preset.show_tokens:
                lines.append(
                    f"  {role:<{role_width}}"
                    f"  {msg_count:>{msg_width}}"
                    f"  {token_count:>{tok_width}}"
                )
            else:
                lines.append(
                    f"  {role:<{role_width}}  {msg_count:>{msg_width}}"
                )

        # Totals separator and row.
        lines.append(separator)
        if preset.show_tokens:
            lines.append(
                f"  {'Total':<{role_width}}"
                f"  {total_msg:>{msg_width}}"
                f"  {total_tok:>{tok_width}}"
            )
        else:
            lines.append(
                f"  {'Total':<{role_width}}  {total_msg:>{msg_width}}"
            )

        # Average tokens/message summary.
        if preset.show_tokens:
            avg = stats.avg_tokens_per_message
            lines.append("")
            lines.append(f"Average tokens/message: {avg:,.1f}")

        text = "\n".join(lines)
        print(text, file=output_file)
        return text

    # ------------------------------------------------------------------
    # render_timeline
    # ------------------------------------------------------------------

    def render_timeline(
        self,
        turns: list[Turn],
        preset: DisplayPreset,
        *,
        file: Any | None = None,
    ) -> str:
        """Render a conversation timeline as formatted text.

        Each turn is rendered with role-labelled content sections and
        separators. Tool interactions are shown as a summary (tool name
        and call count). Content is truncated according to the preset's
        ``max_content_length`` unless ``expand`` is True or
        ``max_content_length`` is None.

        Args:
            turns: List of conversation turns to render.
            preset: Display configuration controlling detail level.
            file: Optional output stream. Defaults to ``sys.stdout``.

        Returns:
            The rendered string.
        """
        output_file = file if file is not None else sys.stdout

        # Empty state.
        if not turns:
            text = "No conversation turns found"
            print(text, file=output_file)
            return text

        # Apply limit for pagination.
        display_turns = turns
        if preset.limit is not None:
            display_turns = turns[: preset.limit]

        parts: list[str] = []
        for turn in display_turns:
            parts.append(self._format_turn(turn, preset))

        # Show pagination indicator when turns were limited.
        if preset.limit is not None and len(turns) > preset.limit:
            remaining = len(turns) - preset.limit
            parts.append(f"... {remaining} more turn(s) not shown")

        text = "\n".join(parts)
        print(text, file=output_file)
        return text

    # ------------------------------------------------------------------
    # render_tools
    # ------------------------------------------------------------------

    def render_tools(
        self,
        tools: list[ToolCallInfo],
        preset: DisplayPreset,
        *,
        file: Any | None = None,
    ) -> str:
        """Render a tool usage summary as an ASCII table.

        Default (collapsed) view shows tool name and call count only.
        When ``preset.show_tool_details`` is True, expanded rows show
        arguments and results per call.

        Args:
            tools: List of tool call summaries to render.
            preset: Display configuration controlling detail level.
            file: Optional output stream. Defaults to ``sys.stdout``.

        Returns:
            The rendered string.
        """
        output_file = file if file is not None else sys.stdout

        # Empty state.
        if not tools:
            text = "No tool calls recorded"
            print(text, file=output_file)
            return text

        lines: list[str] = []
        lines.append("Tool Summary")
        lines.append("")

        # Calculate column widths.
        name_header = "Tool Name"
        calls_header = "Calls"

        name_width = max(
            len(name_header),
            max((len(t.tool_name) for t in tools), default=0),
        )
        calls_width = max(
            len(calls_header),
            max((len(str(t.call_count)) for t in tools), default=0),
        )

        header = f"  {name_header:<{name_width}}  {calls_header:>{calls_width}}"
        separator = f"  {'-' * name_width}  {'-' * calls_width}"

        lines.append(header)
        lines.append(separator)

        for tool in tools:
            lines.append(
                f"  {tool.tool_name:<{name_width}}"
                f"  {tool.call_count!s:>{calls_width}}"
            )

            if preset.show_tool_details:
                detail_lines = self._format_tool_details(tool, preset)
                lines.extend(detail_lines)

        text = "\n".join(lines)
        print(text, file=output_file)
        return text

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _format_turn(self, turn: Any, preset: DisplayPreset) -> str:
        """Format a single conversation turn as text.

        Args:
            turn: A ``Turn`` instance.
            preset: Display configuration controlling detail level.

        Returns:
            Formatted string for this turn.
        """
        lines: list[str] = []

        # Turn header with separator.
        lines.append(f"--- Turn {turn.index} ---")

        # System context.
        if turn.system_context is not None:
            content = self._truncate(turn.system_context, preset)
            lines.append(f"[System] {content}")

        # User content.
        if turn.user_content is not None:
            content = self._truncate(turn.user_content, preset)
            lines.append(f"[User] {content}")

        # Assistant content.
        if turn.assistant_content is not None:
            content = self._truncate(turn.assistant_content, preset)
            lines.append(f"[Assistant] {content}")

        # Tool interactions.
        if turn.tool_interactions:
            tool_lines = self._format_tool_interactions(turn.tool_interactions, preset)
            lines.extend(tool_lines)

        return "\n".join(lines)

    def _format_tool_interactions(
        self,
        interactions: list[dict[str, Any]],
        preset: DisplayPreset,
    ) -> list[str]:
        """Format tool interaction lines.

        For 10+ interactions, shows a summary count. For fewer
        interactions or when ``show_tool_details`` is True, shows
        each tool individually.

        Args:
            interactions: List of tool interaction dicts.
            preset: Display configuration.

        Returns:
            List of formatted text lines.
        """
        lines: list[str] = []

        # Count tools by name for summary.
        tool_counts: dict[str, int] = {}
        for interaction in interactions:
            name = interaction.get("tool_name", "unknown")
            tool_counts[name] = tool_counts.get(name, 0) + 1

        # Show summary count for many interactions.
        if len(interactions) >= 10 and not preset.show_tool_details:
            summary_parts = [f"{name} x{count}" for name, count in tool_counts.items()]
            lines.append(f"[Tools] {len(interactions)} calls: {', '.join(summary_parts)}")
            return lines

        if preset.show_tool_details:
            # Detailed view: show args and results for each call.
            for interaction in interactions:
                name = interaction.get("tool_name", "unknown")
                lines.append(f"  [Tool: {name}]")

                args = interaction.get("arguments", {})
                if args:
                    args_str = json.dumps(args, indent=2, ensure_ascii=False)
                    args_str = self._truncate_str(args_str, preset.max_tool_arg_length)
                    lines.append(f"    args: {args_str}")

                result = interaction.get("result", "")
                if result:
                    result_str = self._truncate_str(str(result), preset.max_tool_arg_length)
                    lines.append(f"    result: {result_str}")
        else:
            # Collapsed view: show tool name and call count per tool.
            summary_parts = [f"{name} x{count}" for name, count in tool_counts.items()]
            lines.append(f"[Tools] {', '.join(summary_parts)}")

        return lines

    @staticmethod
    def _format_tool_details(tool: Any, preset: DisplayPreset) -> list[str]:
        """Format detailed tool call information as indented text lines.

        Args:
            tool: A ``ToolCallInfo`` instance.
            preset: Display configuration with truncation settings.

        Returns:
            List of indented detail lines for this tool.
        """
        lines: list[str] = []
        for i in range(tool.call_count):
            call_id = tool.tool_call_ids[i] if i < len(tool.tool_call_ids) else ""
            header = f"[{call_id}]" if call_id else f"[call {i}]"
            lines.append(f"    {header}")

            if i < len(tool.arguments):
                args_str = json.dumps(tool.arguments[i], indent=2, ensure_ascii=False)
                max_len = preset.max_tool_arg_length
                if max_len is not None and len(args_str) > max_len:
                    remaining = len(args_str) - max_len
                    args_str = args_str[:max_len] + f"... ({remaining} more characters)"
                lines.append(f"      args: {args_str}")

            if i < len(tool.results):
                result_str = str(tool.results[i])
                max_len = preset.max_tool_arg_length
                if max_len is not None and len(result_str) > max_len:
                    remaining = len(result_str) - max_len
                    result_str = result_str[:max_len] + f"... ({remaining} more characters)"
                lines.append(f"      result: {result_str}")

        return lines

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
