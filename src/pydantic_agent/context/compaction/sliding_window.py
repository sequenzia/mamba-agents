"""Sliding window compaction strategy."""

from __future__ import annotations

from typing import Any

from pydantic_agent.context.compaction.base import CompactionResult, CompactionStrategy


class SlidingWindowStrategy(CompactionStrategy):
    """Remove oldest messages beyond a count threshold.

    This is the simplest compaction strategy. It removes messages
    from the beginning of the conversation until the token count
    is below the target.
    """

    @property
    def name(self) -> str:
        return "sliding_window"

    async def compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int = 0,
    ) -> CompactionResult:
        """Compact by removing oldest messages.

        Args:
            messages: Messages to compact.
            target_tokens: Target token count.
            preserve_recent: Number of recent messages to always keep.

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

        # Separate preserved and removable messages
        if preserve_recent > 0 and len(messages) > preserve_recent:
            preserved = messages[-preserve_recent:]
            removable = messages[:-preserve_recent]
        else:
            preserved = []
            removable = messages.copy()

        # Remove from the beginning until we're under target
        removed_count = 0
        while removable and self._count_tokens(removable + preserved) > target_tokens:
            removable.pop(0)
            removed_count += 1

        result_messages = removable + preserved
        tokens_after = self._count_tokens(result_messages)

        return CompactionResult(
            messages=result_messages,
            removed_count=removed_count,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            strategy=self.name,
        )
