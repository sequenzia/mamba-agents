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
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the strategy name.

        Returns:
            Strategy identifier.
        """
        ...

    @abstractmethod
    async def compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int = 0,
    ) -> CompactionResult:
        """Compact messages to fit within target token count.

        Args:
            messages: Messages to compact.
            target_tokens: Target token count after compaction.
            preserve_recent: Number of recent turns to preserve.

        Returns:
            CompactionResult with compacted messages.
        """
        ...

    def _count_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens in messages.

        Args:
            messages: Messages to count.

        Returns:
            Approximate token count.
        """
        from pydantic_agent.tokens import TokenCounter

        counter = TokenCounter()
        return counter.count_messages(messages)
