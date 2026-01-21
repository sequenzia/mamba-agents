"""Hybrid compaction strategy."""

from __future__ import annotations

from typing import Any

from mamba_agents.context.compaction.base import CompactionResult, CompactionStrategy
from mamba_agents.context.compaction.selective import SelectivePruningStrategy
from mamba_agents.context.compaction.sliding_window import SlidingWindowStrategy


class HybridStrategy(CompactionStrategy):
    """Combination of strategies with configurable weights.

    Applies multiple strategies in sequence, using each one
    to progressively reduce context size.

    Note: This strategy overrides `compact()` rather than implementing
    `_do_compact()` because it needs to track which sub-strategies were
    used and build a composite strategy name.
    """

    def __init__(
        self,
        strategies: list[CompactionStrategy] | None = None,
    ) -> None:
        """Initialize the hybrid strategy.

        Args:
            strategies: Strategies to apply in order.
                       If None, uses default combination.
        """
        if strategies is None:
            self._strategies = [
                SelectivePruningStrategy(),
                SlidingWindowStrategy(),
            ]
        else:
            self._strategies = strategies

    @property
    def name(self) -> str:
        return "hybrid"

    async def compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int = 0,
    ) -> CompactionResult:
        """Compact using multiple strategies.

        Args:
            messages: Messages to compact.
            target_tokens: Target token count.
            preserve_recent: Number of recent messages to preserve.

        Returns:
            CompactionResult with compacted messages.
        """
        tokens_before = self._count_tokens(messages)

        if tokens_before <= target_tokens:
            return self._no_compaction_result(messages, tokens_before)

        current_messages = messages
        total_removed = 0
        strategies_used: list[str] = []

        for strategy in self._strategies:
            if self._count_tokens(current_messages) <= target_tokens:
                break

            result = await strategy.compact(
                current_messages,
                target_tokens,
                preserve_recent,
            )

            current_messages = result.messages
            total_removed += result.removed_count
            strategies_used.append(strategy.name)

        tokens_after = self._count_tokens(current_messages)

        return CompactionResult(
            messages=current_messages,
            removed_count=total_removed,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            strategy=f"{self.name}({'+'.join(strategies_used)})",
        )

    async def _do_compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int,
        tokens_before: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Not used - HybridStrategy overrides compact() directly.

        This method exists only to satisfy the abstract base class requirement.
        HybridStrategy needs custom logic to track sub-strategies used.
        """
        raise NotImplementedError("HybridStrategy overrides compact() directly")
