"""Sliding window compaction strategy."""

from __future__ import annotations

from typing import Any

from mamba_agents.context.compaction.base import CompactionStrategy


class SlidingWindowStrategy(CompactionStrategy):
    """Remove oldest messages beyond a count threshold.

    This is the simplest compaction strategy. It removes messages
    from the beginning of the conversation until the token count
    is below the target.
    """

    @property
    def name(self) -> str:
        return "sliding_window"

    async def _do_compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int,
        tokens_before: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Compact by removing oldest messages.

        Args:
            messages: Messages to compact.
            target_tokens: Target token count.
            preserve_recent: Number of recent messages to always keep.
            tokens_before: Token count before compaction (unused here).

        Returns:
            Tuple of (compacted_messages, removed_count).
        """
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

        return removable + preserved, removed_count
