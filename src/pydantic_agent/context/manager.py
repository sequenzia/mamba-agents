"""Context window manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic_agent.context.compaction.base import CompactionResult, CompactionStrategy
from pydantic_agent.context.compaction.hybrid import HybridStrategy
from pydantic_agent.context.compaction.importance import ImportanceScoringStrategy
from pydantic_agent.context.compaction.selective import SelectivePruningStrategy
from pydantic_agent.context.compaction.sliding_window import SlidingWindowStrategy
from pydantic_agent.context.compaction.summarize import SummarizeOlderStrategy
from pydantic_agent.context.config import CompactionConfig
from pydantic_agent.context.history import MessageHistory
from pydantic_agent.tokens import TokenCounter

if TYPE_CHECKING:
    from pydantic_ai import Agent


@dataclass
class ContextState:
    """Current state of the context.

    Attributes:
        token_count: Current token count.
        message_count: Number of messages.
        system_prompt: The system prompt.
        compaction_history: History of compactions performed.
    """

    token_count: int
    message_count: int
    system_prompt: str | None
    compaction_history: list[CompactionResult] = field(default_factory=list)


class ContextManager:
    """Manages conversation context and compaction.

    Tracks message history, monitors token usage, and applies
    compaction strategies when thresholds are reached.
    """

    def __init__(
        self,
        config: CompactionConfig | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        """Initialize the context manager.

        Args:
            config: Compaction configuration.
            token_counter: Token counter instance.
        """
        self._config = config or CompactionConfig()
        self._counter = token_counter or TokenCounter()
        self._history = MessageHistory()
        self._compaction_history: list[CompactionResult] = []
        self._strategy = self._create_strategy()

    def _create_strategy(self) -> CompactionStrategy:
        """Create the compaction strategy from config.

        Returns:
            CompactionStrategy instance.
        """
        strategy_map = {
            "sliding_window": SlidingWindowStrategy,
            "summarize_older": SummarizeOlderStrategy,
            "selective_pruning": SelectivePruningStrategy,
            "importance_scoring": ImportanceScoringStrategy,
            "hybrid": HybridStrategy,
        }

        strategy_class = strategy_map.get(self._config.strategy, SlidingWindowStrategy)
        return strategy_class()

    def add_messages(self, messages: list[dict[str, Any]]) -> None:
        """Add messages to the history.

        Args:
            messages: Messages to add.
        """
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system" and self._config.preserve_system_prompt:
                self._history.system_prompt = content
            else:
                self._history.messages.append(msg)

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages.

        Returns:
            List of messages.
        """
        return self._history.get_messages()

    def get_token_count(self) -> int:
        """Get current token count.

        Returns:
            Approximate token count.
        """
        messages = self.get_messages()
        count = self._counter.count_messages(messages)

        if self._history.system_prompt:
            count += self._counter.count(self._history.system_prompt)

        return count

    def should_compact(self) -> bool:
        """Check if compaction threshold is reached.

        Returns:
            True if compaction should be triggered.
        """
        return self.get_token_count() >= self._config.trigger_threshold_tokens

    async def compact(self) -> CompactionResult:
        """Apply compaction strategy to reduce context size.

        Returns:
            CompactionResult with details of what was done.
        """
        messages = self.get_messages()

        result = await self._strategy.compact(
            messages,
            self._config.target_tokens,
            self._config.preserve_recent_turns,
        )

        # Update history with compacted messages
        self._history.messages = result.messages
        self._compaction_history.append(result)

        return result

    def get_context_state(self) -> ContextState:
        """Get the current context state.

        Returns:
            ContextState with current information.
        """
        return ContextState(
            token_count=self.get_token_count(),
            message_count=len(self._history),
            system_prompt=self._history.system_prompt,
            compaction_history=self._compaction_history.copy(),
        )

    def get_system_prompt(self) -> str | None:
        """Get the system prompt.

        Returns:
            The system prompt or None.
        """
        return self._history.system_prompt

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt.

        Args:
            prompt: The system prompt.
        """
        self._history.system_prompt = prompt

    def clear(self) -> None:
        """Clear all context."""
        self._history.clear()
        self._compaction_history.clear()

    def get_compaction_history(self) -> list[CompactionResult]:
        """Get history of compactions.

        Returns:
            List of CompactionResult objects.
        """
        return self._compaction_history.copy()
