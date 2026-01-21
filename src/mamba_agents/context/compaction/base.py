"""Base class for compaction strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class CompactionResult:
    """Result of a compaction operation.

    Attributes:
        messages: The compacted messages.
        removed_count: Number of messages removed.
        tokens_before: Token count before compaction.
        tokens_after: Token count after compaction.
        strategy: Strategy that was used.
    """

    messages: list[dict[str, Any]]
    removed_count: int
    tokens_before: int
    tokens_after: int
    strategy: str


class CompactionStrategy(ABC):
    """Abstract base class for context compaction strategies.

    Subclasses implement different approaches to reducing context size
    while preserving relevant information.

    This class uses the Template Method pattern. Subclasses implement
    `_do_compact()` with strategy-specific logic, while the base class
    handles common operations like threshold checking and result building.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the strategy name.

        Returns:
            Strategy identifier.
        """
        ...

    async def compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int = 0,
    ) -> CompactionResult:
        """Compact messages to fit within target token count.

        This is a template method that handles common operations:
        1. Early return if already under target
        2. Delegates to _do_compact for strategy-specific logic
        3. Builds the final CompactionResult

        Args:
            messages: Messages to compact.
            target_tokens: Target token count after compaction.
            preserve_recent: Number of recent turns to preserve.

        Returns:
            CompactionResult with compacted messages.
        """
        tokens_before = self._count_tokens(messages)

        if tokens_before <= target_tokens:
            return self._no_compaction_result(messages, tokens_before)

        compacted, removed_count = await self._do_compact(
            messages, target_tokens, preserve_recent, tokens_before
        )

        tokens_after = self._count_tokens(compacted)

        return CompactionResult(
            messages=compacted,
            removed_count=removed_count,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            strategy=self.name,
        )

    @abstractmethod
    async def _do_compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int,
        tokens_before: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Strategy-specific compaction logic.

        Subclasses implement this method with their compaction algorithm.

        Args:
            messages: Messages to compact.
            target_tokens: Target token count after compaction.
            preserve_recent: Number of recent turns to preserve.
            tokens_before: Token count before compaction (pre-computed).

        Returns:
            Tuple of (compacted_messages, removed_count).
        """
        ...

    def _no_compaction_result(
        self, messages: list[dict[str, Any]], tokens: int
    ) -> CompactionResult:
        """Build a result when no compaction is needed.

        Args:
            messages: Original messages (unchanged).
            tokens: Token count of messages.

        Returns:
            CompactionResult indicating no change.
        """
        return CompactionResult(
            messages=messages,
            removed_count=0,
            tokens_before=tokens,
            tokens_after=tokens,
            strategy=self.name,
        )

    def _count_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens in messages.

        Args:
            messages: Messages to count.

        Returns:
            Approximate token count.
        """
        from mamba_agents.tokens import TokenCounter

        counter = TokenCounter()
        return counter.count_messages(messages)
