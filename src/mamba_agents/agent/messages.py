"""Data models and query interface for the MessageQuery system.

Provides structured types for message analytics, tool call summaries,
and conversation timeline views. Also provides the ``MessageQuery`` class
for filtering and querying message histories.

Models:
    MessageStats: Token and message count statistics.
    ToolCallInfo: Summary of a tool's usage across a conversation.
    Turn: A logical conversation turn grouping user/assistant/tool messages.

Classes:
    MessageQuery: Stateless query interface over a list of message dicts.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderResult

    from mamba_agents.tokens.counter import TokenCounter

logger = logging.getLogger(__name__)


@dataclass
class MessageStats:
    """Token and message count statistics for a conversation.

    Attributes:
        total_messages: Total number of messages in the conversation.
        messages_by_role: Count of messages grouped by role (user, assistant, tool, system).
        total_tokens: Total estimated token count across all messages.
        tokens_by_role: Token counts grouped by role.
    """

    total_messages: int = 0
    messages_by_role: dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0
    tokens_by_role: dict[str, int] = field(default_factory=dict)

    @property
    def avg_tokens_per_message(self) -> float:
        """Average tokens per message.

        Returns:
            The average, or 0.0 if there are no messages.
        """
        if self.total_messages == 0:
            return 0.0
        return self.total_tokens / self.total_messages

    def __str__(self) -> str:
        """Render a readable summary of message statistics.

        Returns:
            Multi-line string with counts and averages.
        """
        lines = [
            "Message Statistics",
            f"  Total messages: {self.total_messages}",
            f"  Total tokens:   {self.total_tokens}",
            f"  Avg tokens/msg: {self.avg_tokens_per_message:.1f}",
        ]
        if self.messages_by_role:
            lines.append("  Messages by role:")
            for role, count in sorted(self.messages_by_role.items()):
                lines.append(f"    {role}: {count}")
        if self.tokens_by_role:
            lines.append("  Tokens by role:")
            for role, tokens in sorted(self.tokens_by_role.items()):
                lines.append(f"    {role}: {tokens}")
        return "\n".join(lines)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Render as a Rich table when passed to ``rich.print()`` or ``Console.print()``.

        Delegates to ``RichRenderer.render_stats()`` with the ``detailed`` preset,
        yielding the same Rich objects so formatting is preserved.

        Args:
            console: The Rich Console performing the rendering.
            options: Console options controlling width and other settings.

        Yields:
            Rich renderable objects (Table, Text) for console display.
        """
        from mamba_agents.agent.display.presets import DETAILED
        from mamba_agents.agent.display.rich_renderer import RichRenderer

        renderer = RichRenderer()
        yield from renderer.render_stats_renderables(self, DETAILED)


@dataclass
class ToolCallInfo:
    """Summary of a single tool's usage across a conversation.

    Attributes:
        tool_name: Name of the tool.
        call_count: Number of times the tool was called.
        arguments: List of argument dicts passed to each invocation.
        results: List of result summary strings from each invocation.
        tool_call_ids: List of tool_call_id strings linking calls to results.
    """

    tool_name: str
    call_count: int = 0
    arguments: list[dict[str, Any]] = field(default_factory=list)
    results: list[str] = field(default_factory=list)
    tool_call_ids: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Render a readable summary of tool call information.

        Returns:
            Multi-line string with tool name, call count, and details.
        """
        lines = [
            f"Tool: {self.tool_name} (called {self.call_count} time(s))",
        ]
        for i, call_id in enumerate(self.tool_call_ids):
            lines.append(f"  [{call_id}]")
            if i < len(self.arguments):
                lines.append(f"    args: {self.arguments[i]}")
            if i < len(self.results):
                lines.append(f"    result: {self.results[i]}")
        return "\n".join(lines)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Render as a Rich table when passed to ``rich.print()`` or ``Console.print()``.

        Delegates to ``RichRenderer.render_tools_renderables()`` with the ``detailed``
        preset, yielding a compact tool summary table.

        Args:
            console: The Rich Console performing the rendering.
            options: Console options controlling width and other settings.

        Yields:
            Rich renderable objects (Table) for console display.
        """
        from mamba_agents.agent.display.presets import DETAILED
        from mamba_agents.agent.display.rich_renderer import RichRenderer

        renderer = RichRenderer()
        yield from renderer.render_tools_renderables([self], DETAILED)


@dataclass
class Turn:
    """A logical conversation turn grouping related messages.

    A turn represents one exchange cycle: a user prompt, the assistant's
    response, and any tool call/result pairs that occurred.

    Attributes:
        index: Zero-based position of this turn in the conversation.
        user_content: The user's message content, or None if absent.
        assistant_content: The assistant's text response, or None if absent.
        tool_interactions: List of dicts, each containing tool call and result pairs.
        system_context: System prompt content attached to this turn, or None.
    """

    index: int = 0
    user_content: str | None = None
    assistant_content: str | None = None
    tool_interactions: list[dict[str, Any]] = field(default_factory=list)
    system_context: str | None = None

    def __str__(self) -> str:
        """Render a readable timeline entry for this turn.

        Returns:
            Multi-line string showing the turn's contents.
        """
        lines = [f"Turn {self.index}:"]
        if self.system_context is not None:
            lines.append(f"  System: {self.system_context}")
        if self.user_content is not None:
            lines.append(f"  User: {self.user_content}")
        if self.assistant_content is not None:
            lines.append(f"  Assistant: {self.assistant_content}")
        if self.tool_interactions:
            lines.append("  Tool interactions:")
            for interaction in self.tool_interactions:
                tool_name = interaction.get("tool_name", "unknown")
                call_id = interaction.get("tool_call_id", "")
                args = interaction.get("arguments", {})
                result = interaction.get("result", "")
                lines.append(f"    [{tool_name}] id={call_id}")
                lines.append(f"      args: {args}")
                lines.append(f"      result: {result}")
        return "\n".join(lines)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Render as a Rich panel when passed to ``rich.print()`` or ``Console.print()``.

        Delegates to ``RichRenderer.render_turn_renderable()`` with the ``detailed``
        preset, yielding a formatted turn display panel.

        Args:
            console: The Rich Console performing the rendering.
            options: Console options controlling width and other settings.

        Yields:
            Rich renderable objects (Panel) for console display.
        """
        from mamba_agents.agent.display.presets import DETAILED
        from mamba_agents.agent.display.rich_renderer import RichRenderer

        renderer = RichRenderer()
        yield renderer.render_turn_renderable(self, DETAILED)


class MessageQuery:
    """Stateless query interface for filtering and slicing message histories.

    ``MessageQuery`` operates on a provided list of message dicts (OpenAI
    compatible format) without copying or caching between calls. All filter
    methods return ``list[dict[str, Any]]``.

    Args:
        messages: List of message dicts to query.
        token_counter: Optional ``TokenCounter`` instance for token-aware
            analytics (used by analytics methods in later phases).

    Example::

        query = MessageQuery(messages)
        tool_msgs = query.filter(role="tool")
        recent = query.last(n=5)
    """

    def __init__(
        self,
        messages: list[dict[str, Any]],
        token_counter: TokenCounter | None = None,
    ) -> None:
        self._messages = messages
        self._token_counter = token_counter

    def filter(
        self,
        *,
        role: str | None = None,
        tool_name: str | None = None,
        content: str | None = None,
        regex: bool = False,
    ) -> list[dict[str, Any]]:
        """Filter messages by role, tool name, and/or content.

        Multiple keyword arguments combine with AND logic. Calling with
        no arguments returns all messages.

        Args:
            role: Filter by message role (user, assistant, tool, system).
            tool_name: Filter for messages related to a specific tool. Checks
                ``tool_calls[].function.name`` on assistant messages **and**
                the ``name`` field on tool result messages.
            content: Search message content. Case-insensitive plain text match
                by default; interpreted as a regex pattern when *regex* is True.
            regex: When True, treat *content* as a regular expression pattern.

        Returns:
            List of matching message dicts. Empty list if no matches.

        Raises:
            re.error: If *regex* is True and *content* is not a valid regex.
        """
        results = list(self._messages)

        if role is not None:
            results = [msg for msg in results if msg.get("role") == role]

        if tool_name is not None:
            results = [msg for msg in results if self._matches_tool_name(msg, tool_name)]

        if content is not None:
            if regex:
                try:
                    pattern = re.compile(content)
                except re.error as exc:
                    raise re.error(
                        f"Invalid regex pattern: {content!r} - {exc.msg}",
                        pattern=content,
                    ) from exc
                results = [
                    msg
                    for msg in results
                    if "content" in msg
                    and msg["content"] is not None
                    and pattern.search(msg["content"])
                ]
            else:
                lower_content = content.lower()
                results = [
                    msg
                    for msg in results
                    if "content" in msg
                    and msg["content"] is not None
                    and lower_content in msg["content"].lower()
                ]

        return results

    def slice(self, start: int = 0, end: int | None = None) -> list[dict[str, Any]]:
        """Return messages at indices *start* through *end*-1.

        Uses standard Python slice semantics so out-of-range indices
        are handled gracefully.

        Args:
            start: Start index (inclusive). Defaults to 0.
            end: End index (exclusive). Defaults to None (end of list).

        Returns:
            Sliced list of message dicts.
        """
        return self._messages[start:end]

    def first(self, n: int = 1) -> list[dict[str, Any]]:
        """Return the first *n* messages.

        Args:
            n: Number of messages to return. Defaults to 1.

        Returns:
            List of the first *n* message dicts (or all if fewer exist).
        """
        return self._messages[:n]

    def last(self, n: int = 1) -> list[dict[str, Any]]:
        """Return the last *n* messages.

        Args:
            n: Number of messages to return. Defaults to 1.

        Returns:
            List of the last *n* message dicts (or all if fewer exist).
        """
        if n <= 0:
            return []
        return self._messages[-n:]

    def all(self) -> list[dict[str, Any]]:
        """Return all messages.

        Equivalent to ``get_messages()`` on the Agent.

        Returns:
            Complete list of message dicts.
        """
        return list(self._messages)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def stats(self) -> MessageStats:
        """Compute token and message count statistics.

        Counts messages by role and computes token totals using the
        Agent's configured ``TokenCounter``. Token counts are computed
        on demand and cached within this single call to avoid redundant
        computation. When no ``TokenCounter`` is available, all token
        fields default to zero.

        Returns:
            A ``MessageStats`` instance with counts and token statistics.
        """
        if not self._messages:
            return MessageStats()

        # Count messages by role.
        messages_by_role: dict[str, int] = {}
        for msg in self._messages:
            role = msg.get("role", "unknown")
            messages_by_role[role] = messages_by_role.get(role, 0) + 1

        # Compute token counts, caching per-message values within this call.
        tokens_by_role: dict[str, int] = {}
        total_tokens = 0

        if self._token_counter is not None:
            for msg in self._messages:
                role = msg.get("role", "unknown")
                try:
                    count = self._token_counter.count_messages([msg])
                except Exception:
                    logger.debug(
                        "TokenCounter error for message role=%s, defaulting to 0",
                        role,
                    )
                    count = 0
                tokens_by_role[role] = tokens_by_role.get(role, 0) + count
                total_tokens += count

        return MessageStats(
            total_messages=len(self._messages),
            messages_by_role=messages_by_role,
            total_tokens=total_tokens,
            tokens_by_role=tokens_by_role,
        )

    def tool_summary(self) -> list[ToolCallInfo]:
        """Compute tool call analytics grouped by tool name.

        Scans all messages for tool calls (from assistant messages with
        ``tool_calls`` arrays) and tool results (from tool role messages),
        groups them by tool name, and links calls to their results via
        ``tool_call_id``.

        Returns:
            A list of ``ToolCallInfo`` instances, one per unique tool name.
            Returns an empty list if no tool calls are found.
        """
        if not self._messages:
            return []

        # Build a lookup of tool results by tool_call_id.
        result_by_call_id: dict[str, str] = {}
        matched_call_ids: set[str] = set()

        for msg in self._messages:
            if msg.get("role") == "tool":
                call_id = msg.get("tool_call_id")
                if call_id is not None:
                    result_by_call_id[call_id] = msg.get("content", "")

        # Collect tool calls from assistant messages, grouped by tool name.
        # Preserves insertion order so output is deterministic.
        tools: dict[str, ToolCallInfo] = {}

        for msg in self._messages:
            if msg.get("role") != "assistant":
                continue

            raw_tool_calls = msg.get("tool_calls")
            if not isinstance(raw_tool_calls, list):
                continue

            for tc in raw_tool_calls:
                if not isinstance(tc, dict):
                    continue

                func = tc.get("function")
                if not isinstance(func, dict):
                    continue

                name = func.get("name")
                if not name:
                    continue

                call_id = tc.get("id", "")

                # Parse arguments JSON; fall back to raw string on failure.
                raw_args = func.get("arguments", "")
                try:
                    parsed_args = json.loads(raw_args) if raw_args else {}
                except (json.JSONDecodeError, TypeError):
                    parsed_args = raw_args

                if name not in tools:
                    tools[name] = ToolCallInfo(tool_name=name)

                info = tools[name]
                info.call_count += 1
                info.tool_call_ids.append(call_id)
                info.arguments.append(parsed_args if isinstance(parsed_args, dict) else {})

                # Link to the matching tool result if available.
                if call_id and call_id in result_by_call_id:
                    info.results.append(result_by_call_id[call_id])
                    matched_call_ids.add(call_id)

        # Handle orphaned tool results (results without matching calls).
        for msg in self._messages:
            if msg.get("role") != "tool":
                continue

            call_id = msg.get("tool_call_id", "")
            if call_id in matched_call_ids:
                continue

            name = msg.get("name", "unknown")
            if name not in tools:
                tools[name] = ToolCallInfo(tool_name=name)

            info = tools[name]
            info.call_count += 1
            info.tool_call_ids.append(call_id)
            info.results.append(msg.get("content", ""))

        return list(tools.values())

    def timeline(self) -> list[Turn]:
        """Parse the message list into a structured conversation timeline.

        Groups messages into logical turns. Each turn contains a user
        prompt, the assistant's response, and any tool call/result pairs
        that occurred during the exchange. System prompts at the start
        of the conversation are attached as context on the first turn
        rather than appearing as separate turns.

        **Turn grouping logic:**

        1. Start a new turn on each user message.
        2. Associate the following assistant message with that turn.
        3. If the assistant message has ``tool_calls``, group subsequent
           tool result messages into the turn's ``tool_interactions``.
        4. If the next message after tool results is another assistant
           message, it is part of the same turn (tool loop continuation).
        5. Consecutive assistant messages without a preceding user message
           each get their own turn.
        6. System messages at the start attach to the first turn as context.

        Returns:
            A list of ``Turn`` objects in conversation order. Returns an
            empty list if there are no messages.
        """
        if not self._messages:
            return []

        turns: list[Turn] = []
        current_turn: Turn | None = None
        system_context: str | None = None
        turn_index = 0
        # Tracks whether the current turn is in a tool loop (assistant
        # called tools and we expect either more tool results or a
        # follow-up assistant message that continues the same turn).
        in_tool_loop = False

        # Build a lookup of tool results by tool_call_id for pairing.
        result_by_call_id: dict[str, dict[str, Any]] = {}
        for msg in self._messages:
            if msg.get("role") == "tool":
                call_id = msg.get("tool_call_id")
                if call_id is not None:
                    result_by_call_id[call_id] = msg

        i = 0
        while i < len(self._messages):
            msg = self._messages[i]
            role = msg.get("role", "")

            if role == "system":
                # Collect system context; attach to first turn later.
                content = msg.get("content", "")
                if system_context is None:
                    system_context = content
                else:
                    system_context += "\n" + (content or "")
                i += 1
                continue

            if role == "user":
                # Start a new turn.
                in_tool_loop = False
                current_turn = Turn(
                    index=turn_index,
                    user_content=msg.get("content"),
                )
                # Attach accumulated system context to the first turn.
                if system_context is not None and turn_index == 0:
                    current_turn.system_context = system_context
                    system_context = None
                turn_index += 1
                turns.append(current_turn)
                i += 1
                continue

            if role == "assistant":
                # Decide whether to continue the current turn or start a
                # new one. Continue if: (a) the turn has no assistant
                # content yet, or (b) we are in a tool loop (assistant
                # called tools, tool results came back, next assistant
                # continues the same exchange).
                needs_new_turn = current_turn is None or (
                    current_turn.assistant_content is not None and not in_tool_loop
                )
                if needs_new_turn:
                    current_turn = Turn(index=turn_index)
                    # Attach system context if it hasn't been used yet.
                    if system_context is not None and turn_index == 0:
                        current_turn.system_context = system_context
                        system_context = None
                    turn_index += 1
                    turns.append(current_turn)

                # Reset tool loop flag; it will be set again below if
                # this assistant message also has tool_calls.
                in_tool_loop = False

                content = msg.get("content")
                if content is not None:
                    if current_turn.assistant_content is None:
                        current_turn.assistant_content = content
                    else:
                        current_turn.assistant_content += "\n" + content

                # Process tool calls if present.
                raw_tool_calls = msg.get("tool_calls")
                has_tool_calls = isinstance(raw_tool_calls, list) and len(raw_tool_calls) > 0
                if has_tool_calls:
                    for tc in raw_tool_calls:
                        if not isinstance(tc, dict):
                            continue
                        func = tc.get("function")
                        if not isinstance(func, dict):
                            continue
                        name = func.get("name", "unknown")
                        call_id = tc.get("id", "")
                        raw_args = func.get("arguments", "")
                        try:
                            parsed_args = json.loads(raw_args) if raw_args else {}
                        except (json.JSONDecodeError, TypeError):
                            parsed_args = {}
                        # Find the matching tool result.
                        result_content = ""
                        if call_id and call_id in result_by_call_id:
                            result_content = result_by_call_id[call_id].get("content", "")
                        current_turn.tool_interactions.append(
                            {
                                "tool_name": name,
                                "tool_call_id": call_id,
                                "arguments": parsed_args if isinstance(parsed_args, dict) else {},
                                "result": result_content,
                            }
                        )

                i += 1

                # After processing tool calls, consume any following tool
                # result messages (they were already paired via lookup).
                if has_tool_calls:
                    while i < len(self._messages) and self._messages[i].get("role") == "tool":
                        i += 1
                    # Mark that we are in a tool loop so the next
                    # assistant message continues this turn.
                    in_tool_loop = True

                continue

            if role == "tool":
                # Orphaned tool message not preceded by an assistant.
                # Skip it; it was already indexed in the lookup.
                i += 1
                continue

            # Unknown role; skip gracefully.
            i += 1

        # If system context was never attached (e.g., only system messages),
        # create a turn for it.
        if system_context is not None:
            turn = Turn(index=turn_index, system_context=system_context)
            turns.append(turn)

        return turns

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    #: Supported export format names.
    _VALID_FORMATS: tuple[str, ...] = ("json", "markdown", "csv", "dict")

    def export(
        self,
        format: str = "json",
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str | list[dict[str, Any]]:
        """Export messages in the specified format.

        Args:
            format: Export format. One of ``"json"``, ``"markdown"``,
                ``"csv"``, or ``"dict"``.
            messages: Optional subset of messages to export. When *None*,
                all messages held by this query instance are exported.
            **kwargs: Format-specific options forwarded to the
                underlying exporter.

        Returns:
            A JSON, Markdown, or CSV string for string-based formats,
            or ``list[dict]`` for the ``"dict"`` format.

        Raises:
            ValueError: If *format* is not one of the supported formats.
        """
        if format not in self._VALID_FORMATS:
            raise ValueError(
                f"Invalid export format: {format!r}. "
                f"Valid formats: {', '.join(self._VALID_FORMATS)}"
            )

        target_messages = messages if messages is not None else self._messages

        dispatch: dict[str, Any] = {
            "json": self._export_json,
            "markdown": self._export_markdown,
            "csv": self._export_csv,
            "dict": self._export_dict,
        }

        exporter = dispatch.get(format)
        if exporter is None:
            raise NotImplementedError(f"Export format {format!r} is not yet implemented.")
        return exporter(target_messages, **kwargs)

    # ------------------------------------------------------------------
    # Export format implementations
    # ------------------------------------------------------------------

    def _export_json(
        self,
        messages: list[dict[str, Any]],
        *,
        include_metadata: bool = False,
        indent: int = 2,
    ) -> str:
        """Export messages as a JSON string.

        Args:
            messages: The messages to export.
            include_metadata: When True, each message dict is wrapped with
                an ``index`` and ``token_count`` field.
            indent: JSON indentation level. Defaults to 2.

        Returns:
            A JSON string parseable by ``json.loads()``.
        """
        if not include_metadata:
            return json.dumps(messages, indent=indent, ensure_ascii=False)

        enriched: list[dict[str, Any]] = []
        for idx, msg in enumerate(messages):
            entry: dict[str, Any] = dict(msg)
            entry["index"] = idx
            entry["token_count"] = self._count_message_tokens(msg)
            enriched.append(entry)

        return json.dumps(enriched, indent=indent, ensure_ascii=False)

    def _export_markdown(
        self,
        messages: list[dict[str, Any]],
    ) -> str:
        """Export messages as a formatted Markdown string.

        Renders each message under a role-specific header (``### User``,
        ``### Assistant``, ``### System``). Tool calls are displayed with
        the tool name, arguments formatted as JSON in fenced code blocks,
        and results in fenced code blocks. Tool result messages (role
        ``"tool"``) are rendered inline under the preceding assistant's
        tool call section, so they are not emitted as standalone entries.

        Args:
            messages: The messages to export.

        Returns:
            A Markdown-formatted string. Returns an empty string when
            *messages* is empty.
        """
        if not messages:
            return ""

        # Pre-index tool results by tool_call_id for pairing with calls.
        result_by_call_id: dict[str, str] = {}
        for msg in messages:
            if msg.get("role") == "tool":
                call_id = msg.get("tool_call_id")
                if call_id is not None:
                    result_by_call_id[call_id] = msg.get("content") or ""

        parts: list[str] = []

        for msg in messages:
            role = msg.get("role", "unknown")

            if role == "user":
                parts.append(self._md_render_text_message("User", msg.get("content")))

            elif role == "system":
                parts.append(self._md_render_text_message("System", msg.get("content")))

            elif role == "assistant":
                parts.append(
                    self._md_render_assistant(msg, result_by_call_id),
                )

            elif role == "tool":
                # Tool results are rendered inline with assistant tool
                # calls above; skip standalone rendering.
                continue

            else:
                # Unknown role -- render generically.
                parts.append(self._md_render_text_message(role.title(), msg.get("content")))

        return "\n\n---\n\n".join(parts)

    # ------------------------------------------------------------------
    # Markdown rendering helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _md_escape_code_fence(text: str) -> str:
        """Escape triple-backtick sequences inside Markdown code blocks.

        Replaces bare ````` ``` ````` with zero-width space separated
        backticks so they do not break fenced code blocks.

        Args:
            text: The raw text to escape.

        Returns:
            Escaped text safe for use inside fenced code blocks.
        """
        return text.replace("```", "`\u200b`\u200b`")

    @classmethod
    def _md_render_text_message(cls, header: str, content: str | None) -> str:
        """Render a simple text message with a role header.

        Args:
            header: The role header label (e.g. ``"User"``).
            content: The message content, or None.

        Returns:
            A Markdown fragment with a ``### {header}`` heading.
        """
        lines = [f"### {header}"]
        if content is not None:
            lines.append("")
            lines.append(content)
        return "\n".join(lines)

    @classmethod
    def _md_render_assistant(
        cls,
        msg: dict[str, Any],
        result_by_call_id: dict[str, str],
    ) -> str:
        """Render an assistant message, including any tool calls.

        Args:
            msg: The assistant message dict.
            result_by_call_id: Lookup of tool result content by call ID.

        Returns:
            A Markdown fragment with the assistant content and tool calls.
        """
        lines = ["### Assistant"]

        content = msg.get("content")
        if content is not None:
            lines.append("")
            lines.append(content)

        raw_tool_calls = msg.get("tool_calls")
        if isinstance(raw_tool_calls, list):
            for tc in raw_tool_calls:
                tc_lines = cls._md_render_tool_call(tc, result_by_call_id)
                if tc_lines:
                    lines.append("")
                    lines.extend(tc_lines)

        return "\n".join(lines)

    @classmethod
    def _md_render_tool_call(
        cls,
        tc: Any,
        result_by_call_id: dict[str, str],
    ) -> list[str]:
        """Render a single tool call entry as Markdown lines.

        Args:
            tc: A tool call dict from the ``tool_calls`` array.
            result_by_call_id: Lookup of tool result content by call ID.

        Returns:
            A list of Markdown lines for this tool call, or an empty list
            if the entry is malformed.
        """
        if not isinstance(tc, dict):
            return []

        func = tc.get("function")
        if not isinstance(func, dict):
            return []

        name = func.get("name", "unknown")
        call_id = tc.get("id", "")

        # Parse arguments.
        raw_args = func.get("arguments", "")
        try:
            parsed_args = json.loads(raw_args) if raw_args else {}
        except (json.JSONDecodeError, TypeError):
            parsed_args = raw_args

        # Format arguments as indented JSON for the code block.
        if isinstance(parsed_args, dict):
            args_display = json.dumps(parsed_args, indent=2, ensure_ascii=False)
        else:
            args_display = str(parsed_args)

        lines: list[str] = [f"**Tool Call: {name}**"]

        # Arguments in a fenced code block.
        lines.append("")
        lines.append("```json")
        lines.append(cls._md_escape_code_fence(args_display))
        lines.append("```")

        # Result in a fenced code block (if available).
        if call_id and call_id in result_by_call_id:
            result_text = result_by_call_id[call_id]
            lines.append("")
            lines.append("**Result:**")
            lines.append("")
            lines.append("```")
            lines.append(cls._md_escape_code_fence(result_text))
            lines.append("```")

        return lines

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    #: Column headers for CSV export.
    _CSV_COLUMNS: tuple[str, ...] = (
        "index",
        "role",
        "content",
        "tool_name",
        "tool_call_id",
        "token_count",
    )

    def _export_csv(
        self,
        messages: list[dict[str, Any]],
        *,
        max_content_length: int = 500,
    ) -> str:
        """Export messages as a CSV string.

        Columns: ``index, role, content, tool_name, tool_call_id, token_count``.
        Content is truncated to *max_content_length* characters with a ``...``
        suffix when it exceeds the limit.

        Uses the stdlib :mod:`csv` module so commas, newlines, and quotes
        inside cell values are properly escaped.

        Args:
            messages: The messages to export.
            max_content_length: Maximum character length for the content
                column before truncation. Defaults to 500.

        Returns:
            A CSV string with a header row followed by one row per message.
            An empty conversation returns the header row only.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row.
        writer.writerow(self._CSV_COLUMNS)

        for idx, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content") or ""

            # Truncate content if it exceeds the limit.
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."

            # Extract tool_name: from tool result messages or assistant tool_calls.
            tool_name = self._csv_extract_tool_name(msg)

            # Extract tool_call_id from tool result messages.
            tool_call_id = msg.get("tool_call_id", "")

            token_count = self._count_message_tokens(msg)

            writer.writerow([idx, role, content, tool_name, tool_call_id, token_count])

        return output.getvalue()

    @staticmethod
    def _csv_extract_tool_name(msg: dict[str, Any]) -> str:
        """Extract the tool name from a message dict for CSV export.

        For tool result messages (role ``"tool"``), uses the ``name`` field.
        For assistant messages with ``tool_calls``, uses the first tool call's
        function name. For other roles, returns an empty string.

        Args:
            msg: A single message dict.

        Returns:
            The tool name, or an empty string if not applicable.
        """
        role = msg.get("role", "")

        # Tool result messages have a top-level 'name' field.
        if role == "tool":
            return msg.get("name", "")

        # Assistant messages may have tool_calls.
        if role == "assistant":
            tool_calls = msg.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                first_tc = tool_calls[0]
                if isinstance(first_tc, dict):
                    func = first_tc.get("function")
                    if isinstance(func, dict):
                        return func.get("name", "")

        return ""

    # ------------------------------------------------------------------
    # Dict export
    # ------------------------------------------------------------------

    def _export_dict(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Export messages as a list of dicts with added ``_metadata``.

        Each message dict is shallow-copied and enriched with a ``_metadata``
        key containing ``index``, ``token_count``, and ``role``.  Original
        message fields are never modified.

        If a message already contains a ``_metadata`` key, the export uses
        ``_export_metadata`` instead to avoid overwriting the existing value.

        When no ``TokenCounter`` is available, ``token_count`` defaults to 0.

        Args:
            messages: The messages to export.

        Returns:
            A list of enriched message dicts.
        """
        if not messages:
            return []

        # Determine the metadata key name.  If any message already uses
        # ``_metadata``, fall back to ``_export_metadata`` to avoid conflicts.
        meta_key = "_metadata"
        for msg in messages:
            if "_metadata" in msg:
                meta_key = "_export_metadata"
                break

        result: list[dict[str, Any]] = []
        for idx, msg in enumerate(messages):
            entry: dict[str, Any] = dict(msg)

            role = msg.get("role", "unknown")

            # Compute token count; default to 0 when counter is unavailable.
            if self._token_counter is not None:
                try:
                    token_count = self._token_counter.count_messages([msg])
                except Exception:
                    logger.debug(
                        "TokenCounter error for message index=%d, defaulting to 0",
                        idx,
                    )
                    token_count = 0
            else:
                token_count = 0

            entry[meta_key] = {
                "index": idx,
                "token_count": token_count,
                "role": role,
            }
            result.append(entry)

        return result

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def print_stats(
        self,
        *,
        preset: str = "detailed",
        format: str = "rich",
        console: Console | None = None,
        **options: Any,
    ) -> str:
        """Render message statistics as a formatted table.

        Computes statistics via :meth:`stats` and delegates to the
        standalone :func:`~mamba_agents.agent.display.print_stats` function
        for rendering. All parameters are forwarded directly.

        Args:
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

            agent.messages.print_stats()  # Rich table to terminal
            agent.messages.print_stats(format="plain")  # ASCII table
            agent.messages.print_stats(preset="compact", show_tokens=True)
        """
        from mamba_agents.agent.display.functions import (
            print_stats as _print_stats,
        )

        stats = self.stats()
        return _print_stats(stats, preset=preset, format=format, console=console, **options)

    def print_timeline(
        self,
        *,
        preset: str = "detailed",
        format: str = "rich",
        console: Console | None = None,
        **options: Any,
    ) -> str:
        """Render the conversation timeline as a formatted display.

        Parses messages into turns via :meth:`timeline` and delegates to the
        standalone :func:`~mamba_agents.agent.display.print_timeline` function
        for rendering. All parameters are forwarded directly.

        Args:
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

            agent.messages.print_timeline()  # Rich panels to terminal
            agent.messages.print_timeline(format="plain")  # ASCII timeline
            agent.messages.print_timeline(preset="compact", limit=5)
        """
        from mamba_agents.agent.display.functions import (
            print_timeline as _print_timeline,
        )

        turns = self.timeline()
        return _print_timeline(turns, preset=preset, format=format, console=console, **options)

    def print_tools(
        self,
        *,
        preset: str = "detailed",
        format: str = "rich",
        console: Console | None = None,
        **options: Any,
    ) -> str:
        """Render a tool usage summary as a formatted table.

        Computes tool call summaries via :meth:`tool_summary` and delegates to
        the standalone :func:`~mamba_agents.agent.display.print_tools` function
        for rendering. All parameters are forwarded directly.

        Args:
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

            agent.messages.print_tools()  # Rich table to terminal
            agent.messages.print_tools(format="plain")  # ASCII table
            agent.messages.print_tools(preset="verbose", show_tool_details=True)
        """
        from mamba_agents.agent.display.functions import (
            print_tools as _print_tools,
        )

        tools = self.tool_summary()
        return _print_tools(tools, preset=preset, format=format, console=console, **options)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _count_message_tokens(self, msg: dict[str, Any]) -> int:
        """Compute the token count for a single message dict.

        Uses the configured ``TokenCounter`` when available; otherwise
        falls back to a rough whitespace-split estimate.

        Args:
            msg: A single message dict.

        Returns:
            Estimated token count for the message.
        """
        if self._token_counter is not None:
            return self._token_counter.count_messages([msg])

        # Rough fallback: count whitespace-delimited words as ~1 token each.
        content = msg.get("content") or ""
        return len(content.split())

    @staticmethod
    def _matches_tool_name(msg: dict[str, Any], tool_name: str) -> bool:
        """Check whether a message relates to a given tool name.

        For assistant messages, checks ``tool_calls[].function.name``.
        For tool result messages, checks the ``name`` field.

        Args:
            msg: A single message dict.
            tool_name: The tool name to match.

        Returns:
            True if the message is associated with *tool_name*.
        """
        role = msg.get("role")

        # Assistant messages with tool_calls
        if role == "assistant":
            for tc in msg.get("tool_calls", []):
                if isinstance(tc, dict):
                    func = tc.get("function", {})
                    if func.get("name") == tool_name:
                        return True

        # Tool result messages
        return role == "tool" and msg.get("name") == tool_name
