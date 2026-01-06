"""Summarization-based compaction strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic_agent.context.compaction.base import CompactionResult, CompactionStrategy

if TYPE_CHECKING:
    from pydantic_ai import Agent


class SummarizeOlderStrategy(CompactionStrategy):
    """Summarize older messages while keeping recent ones verbatim.

    Uses an LLM to create a summary of older conversation turns,
    replacing them with a single summary message.
    """

    def __init__(
        self,
        summarization_agent: "Agent[Any, str] | None" = None,
    ) -> None:
        """Initialize the summarization strategy.

        Args:
            summarization_agent: Agent to use for summarization.
                                If None, a default will be created.
        """
        self._agent = summarization_agent

    @property
    def name(self) -> str:
        return "summarize_older"

    async def compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int = 0,
    ) -> CompactionResult:
        """Compact by summarizing older messages.

        Args:
            messages: Messages to compact.
            target_tokens: Target token count.
            preserve_recent: Number of recent messages to keep verbatim.

        Returns:
            CompactionResult with compacted messages.
        """
        tokens_before = self._count_tokens(messages)

        if tokens_before <= target_tokens:
            return CompactionResult(
                messages=messages,
                removed_count=0,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                strategy=self.name,
            )

        # Separate messages to preserve and summarize
        if preserve_recent > 0 and len(messages) > preserve_recent:
            to_preserve = messages[-preserve_recent:]
            to_summarize = messages[:-preserve_recent]
        else:
            to_preserve = messages.copy()
            to_summarize = []

        if not to_summarize:
            # Nothing to summarize, fall back to sliding window
            return CompactionResult(
                messages=to_preserve,
                removed_count=0,
                tokens_before=tokens_before,
                tokens_after=self._count_tokens(to_preserve),
                strategy=self.name,
            )

        # Create summary
        summary = await self._create_summary(to_summarize)

        # Create summary message
        summary_message = {
            "role": "system",
            "content": f"[Previous conversation summary: {summary}]",
        }

        result_messages = [summary_message] + to_preserve
        tokens_after = self._count_tokens(result_messages)

        return CompactionResult(
            messages=result_messages,
            removed_count=len(to_summarize),
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            strategy=self.name,
        )

    async def _create_summary(self, messages: list[dict[str, Any]]) -> str:
        """Create a summary of messages.

        Args:
            messages: Messages to summarize.

        Returns:
            Summary text.
        """
        if self._agent is None:
            # Create a simple summary without LLM
            return self._simple_summary(messages)

        # Format messages for summarization
        formatted = self._format_for_summary(messages)

        # Use agent to summarize
        result = await self._agent.run(
            f"Summarize this conversation concisely:\n\n{formatted}"
        )
        return result.output

    def _simple_summary(self, messages: list[dict[str, Any]]) -> str:
        """Create a simple summary without LLM.

        Args:
            messages: Messages to summarize.

        Returns:
            Simple summary.
        """
        user_messages = [m for m in messages if m.get("role") == "user"]
        tool_calls = [
            m for m in messages if m.get("role") == "assistant" and m.get("tool_calls")
        ]

        summary_parts = [f"Conversation with {len(messages)} messages."]

        if user_messages:
            topics = [m.get("content", "")[:50] for m in user_messages[:3]]
            summary_parts.append(f"Topics discussed: {', '.join(topics)}...")

        if tool_calls:
            tool_names = []
            for m in tool_calls:
                for tc in m.get("tool_calls", []):
                    if isinstance(tc, dict):
                        name = tc.get("function", {}).get("name", "")
                        if name and name not in tool_names:
                            tool_names.append(name)
            if tool_names:
                summary_parts.append(f"Tools used: {', '.join(tool_names[:5])}")

        return " ".join(summary_parts)

    def _format_for_summary(self, messages: list[dict[str, Any]]) -> str:
        """Format messages for summarization prompt.

        Args:
            messages: Messages to format.

        Returns:
            Formatted text.
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
